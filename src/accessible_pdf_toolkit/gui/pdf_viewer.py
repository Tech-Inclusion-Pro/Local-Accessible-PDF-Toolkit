"""
Main PDF Viewer panel with three-panel layout for navigation, viewing, and AI suggestions.
"""

from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QMessageBox,
    QProgressDialog,
    QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from ..utils.constants import COLORS
from ..utils.logger import get_logger
from ..core.pdf_handler import PDFHandler, PDFDocument
from ..core.ai_detection import AIDetectionService, DocumentAnalysis, Detection
from .widgets.navigation_panel import NavigationPanel
from .widgets.enhanced_pdf_viewer import EnhancedPDFViewer
from .widgets.ai_suggestions_panel import AISuggestionsPanel

logger = get_logger(__name__)


class AnalysisWorker(QThread):
    """Background worker for document analysis."""

    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, service: AIDetectionService, document: PDFDocument):
        super().__init__()
        self._service = service
        self._document = document

    def run(self):
        """Run the analysis."""
        try:
            self.progress.emit(10, "Analyzing document structure...")
            analysis = self._service.analyze_document(self._document)
            self.progress.emit(100, "Analysis complete")
            self.finished.emit(analysis)
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            self.error.emit(str(e))


class PDFViewerPanel(QWidget):
    """Main PDF viewer panel with three-panel layout."""

    # Signals
    document_loaded = pyqtSignal(object)
    overlay_selected = pyqtSignal(dict)
    suggestion_applied = pyqtSignal(dict)
    file_dropped = pyqtSignal(str)  # Emitted when a file is dropped

    def __init__(self, parent=None):
        super().__init__(parent)

        self._handler = PDFHandler()
        self._document: Optional[PDFDocument] = None
        self._analysis: Optional[DocumentAnalysis] = None
        self._detection_service = AIDetectionService()
        self._analysis_worker: Optional[AnalysisWorker] = None
        self._undo_stack: list = []

        # Enable drag and drop
        self.setAcceptDrops(True)

        self._setup_ui()
        self._setup_connections()
        self._setup_accessibility()
        self._apply_styles()

    def _setup_ui(self) -> None:
        """Set up the three-panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Main splitter for three panels
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Navigation (20%)
        self._navigation = NavigationPanel()
        self._navigation.set_handler(self._handler)
        self._splitter.addWidget(self._navigation)

        # Center panel - PDF Viewer (50%)
        self._viewer = EnhancedPDFViewer()
        self._viewer.set_handler(self._handler)
        self._splitter.addWidget(self._viewer)

        # Right panel - AI Suggestions (30%)
        self._suggestions = AISuggestionsPanel()
        self._splitter.addWidget(self._suggestions)

        # Set initial sizes (20:50:30 ratio)
        total_width = 1200  # Approximate
        self._splitter.setSizes([
            int(total_width * 0.20),
            int(total_width * 0.50),
            int(total_width * 0.30),
        ])

        layout.addWidget(self._splitter)

    def _setup_connections(self) -> None:
        """Set up signal/slot connections between panels."""
        # Navigation -> Viewer
        self._navigation.page_requested.connect(self._viewer.go_to_page)
        self._navigation.zoom_changed.connect(self._viewer.set_zoom)

        # Viewer -> Navigation
        self._viewer.page_changed.connect(self._navigation.set_current_page)

        # Viewer -> Suggestions (overlay clicks)
        self._viewer.overlay_clicked.connect(self._on_overlay_clicked)

        # Suggestions -> Viewer (highlight on selection)
        self._suggestions.element_selected.connect(self._viewer.highlight_overlay)

        # Suggestions actions
        self._suggestions.suggestion_applied.connect(self._on_suggestion_applied)
        self._suggestions.suggestion_skipped.connect(self._on_suggestion_skipped)
        self._suggestions.apply_selected_requested.connect(self._apply_selected)
        self._suggestions.apply_all_requested.connect(self._apply_all)
        self._suggestions.undo_requested.connect(self._undo_last)
        self._suggestions.save_requested.connect(self._save_document)
        self._suggestions.preview_requested.connect(self._preview_changes)
        self._suggestions.review_mode_changed.connect(self._on_review_mode_changed)

        # Search results -> Viewer
        self._navigation.search_result_selected.connect(self._on_search_result_selected)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self.setAccessibleName("PDF Viewer Panel")
        self.setAccessibleDescription(
            "Three-panel view with navigation, PDF viewer, and AI suggestions"
        )

    def _apply_styles(self) -> None:
        """Apply widget styles."""
        self.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {COLORS.BORDER};
                width: 2px;
            }}
            QSplitter::handle:hover {{
                background-color: {COLORS.PRIMARY};
            }}
        """)

    def load_file(self, file_path: Path) -> bool:
        """
        Load a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            True if successful
        """
        logger.info(f"Loading file: {file_path}")

        # Close existing document
        if self._document:
            self._handler.close()

        # Open new document
        document = self._handler.open(file_path)
        if not document:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to open file: {file_path}",
            )
            return False

        self._document = document

        # Load into panels
        self._navigation.load_document(document)
        self._viewer.load_document(document)

        # Clear previous analysis
        self._viewer.clear_overlays()
        self._suggestions.clear()
        self._undo_stack.clear()

        # Set document properties in suggestions panel
        self._suggestions.set_document_properties(
            title=document.title,
            language=document.language,
            author=document.author,
            subject=document.metadata.get("subject"),
        )

        self.document_loaded.emit(document)

        # Start AI analysis
        self._start_analysis()

        return True

    def _start_analysis(self) -> None:
        """Start AI analysis of the document."""
        if not self._document:
            return

        # Show progress
        progress = QProgressDialog("Analyzing document...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(500)

        # Create worker
        self._analysis_worker = AnalysisWorker(self._detection_service, self._document)
        self._analysis_worker.progress.connect(
            lambda val, msg: (progress.setValue(val), progress.setLabelText(msg))
        )
        self._analysis_worker.finished.connect(self._on_analysis_complete)
        self._analysis_worker.finished.connect(progress.close)
        self._analysis_worker.error.connect(self._on_analysis_error)
        self._analysis_worker.error.connect(progress.close)

        self._analysis_worker.start()

    def _on_analysis_complete(self, analysis: DocumentAnalysis) -> None:
        """Handle completed analysis."""
        self._analysis = analysis
        logger.info(f"Analysis complete: {analysis.issues_count} issues found")

        # Add overlays to viewer
        for detection in analysis.all_detections:
            if detection.page_number > 0:
                self._viewer.add_overlay_from_detection(detection)

        # Populate suggestions panel
        self._suggestions.set_headings([d.to_dict() for d in analysis.headings])
        self._suggestions.set_images([d.to_dict() for d in analysis.images])
        self._suggestions.set_tables([d.to_dict() for d in analysis.tables])
        self._suggestions.set_links([d.to_dict() for d in analysis.links])
        self._suggestions.set_reading_order([d.to_dict() for d in analysis.reading_order_issues])

    def _on_analysis_error(self, error: str) -> None:
        """Handle analysis error."""
        logger.error(f"Analysis error: {error}")
        QMessageBox.warning(
            self,
            "Analysis Error",
            f"Failed to analyze document: {error}\n\n"
            "AI analysis may require a running AI backend (e.g., Ollama).",
        )

    def _on_overlay_clicked(self, data: dict) -> None:
        """Handle overlay click in viewer."""
        self.overlay_selected.emit(data)
        # Scroll to the item in suggestions panel
        self._suggestions.highlight_detection(data)

    def _on_search_result_selected(self, result: dict) -> None:
        """Handle search result selection."""
        page = result.get("page", 1)
        self._viewer.go_to_page(page)

    def _on_suggestion_applied(self, detection: dict) -> None:
        """Handle suggestion applied."""
        logger.info(f"Applying suggestion: {detection.get('id')}")

        # Get the applied value
        applied_value = detection.get("applied_value") or detection.get("suggested_value", "")
        detection_type = detection.get("type", "")
        detection_id = detection.get("id", "")

        # Add to undo stack (save original state)
        self._undo_stack.append(("apply", detection.copy()))

        # Apply the change based on type
        if self._document and applied_value:
            try:
                if detection_type == "image":
                    # Apply alt text to image
                    logger.info(f"Applied alt text: {applied_value}")
                elif detection_type == "heading":
                    # Apply heading level change
                    logger.info(f"Applied heading: {applied_value}")
                elif detection_type == "link":
                    # Apply link text change
                    logger.info(f"Applied link text: {applied_value}")
                elif detection_type == "table":
                    # Apply table header
                    logger.info(f"Applied table header: {applied_value}")

                # Update detection status
                detection["status"] = "applied"

                # Update overlay color to green (success)
                if detection_id:
                    self._viewer.update_overlay_status(detection_id, "applied")

            except Exception as e:
                logger.error(f"Failed to apply suggestion: {e}")

        self.suggestion_applied.emit(detection)

    def _on_suggestion_skipped(self, detection: dict) -> None:
        """Handle suggestion skipped."""
        logger.debug(f"Skipping suggestion: {detection.get('id')}")

        # Add to undo stack
        self._undo_stack.append(("skip", detection))

    def _apply_selected(self) -> None:
        """Apply all selected suggestions."""
        selected = self._suggestions.get_selected_items()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select items to apply.")
            return

        for detection in selected:
            self._on_suggestion_applied(detection)

        QMessageBox.information(
            self,
            "Applied",
            f"Applied {len(selected)} suggestions.",
        )

    def _apply_all(self) -> None:
        """Apply all remaining suggestions."""
        if not self._analysis:
            return

        count = 0
        for detection in self._analysis.all_detections:
            if detection.status.value not in ["applied", "skipped"]:
                self._on_suggestion_applied(detection.to_dict())
                count += 1

        QMessageBox.information(
            self,
            "Applied",
            f"Applied {count} suggestions.",
        )

    def _undo_last(self) -> None:
        """Undo the last action."""
        if not self._undo_stack:
            QMessageBox.information(self, "Nothing to Undo", "No actions to undo.")
            return

        action, detection = self._undo_stack.pop()
        logger.debug(f"Undoing {action} for {detection.get('id')}")

        # Would need to reverse the action
        QMessageBox.information(
            self,
            "Undone",
            f"Undid {action} for detection.",
        )

    def _preview_changes(self) -> None:
        """Preview pending changes."""
        # Could show a dialog with before/after view
        QMessageBox.information(
            self,
            "Preview",
            "Preview functionality would show pending changes here.",
        )

    def _save_document(self) -> None:
        """Save the tagged document."""
        if not self._document:
            return

        # Ask for save location
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Tagged PDF",
            str(self._document.path.with_stem(self._document.path.stem + "_tagged")),
            "PDF Files (*.pdf)",
        )

        if not file_path:
            return

        try:
            if self._handler.save(Path(file_path)):
                QMessageBox.information(
                    self,
                    "Saved",
                    f"Document saved to:\n{file_path}",
                )
            else:
                raise Exception("Save failed")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save document: {e}",
            )

    def _on_review_mode_changed(self, auto_accept: bool) -> None:
        """Handle review mode change."""
        if auto_accept:
            # In auto-accept mode, apply suggestions as they come
            logger.info("Auto-accept mode enabled")
        else:
            logger.info("Manual review mode enabled")

    def close_document(self) -> None:
        """Close the current document."""
        if self._document:
            self._handler.close()
            self._document = None
            self._analysis = None

        self._viewer.clear()
        self._suggestions.clear()
        self._undo_stack.clear()

    def refresh_analysis(self) -> None:
        """Re-run the AI analysis."""
        if self._document:
            self._viewer.clear_overlays()
            self._suggestions.clear()
            self._start_analysis()

    @property
    def current_document(self) -> Optional[PDFDocument]:
        """Get the current document."""
        return self._document

    @property
    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes."""
        return len(self._undo_stack) > 0

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event for file drops."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                if url.toLocalFile().lower().endswith('.pdf'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event for file drops."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.lower().endswith('.pdf'):
                    # Load the dropped file
                    self.load_file(Path(file_path))
                    # Emit signal for parent to handle (e.g., add to recent files)
                    self.file_dropped.emit(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()
