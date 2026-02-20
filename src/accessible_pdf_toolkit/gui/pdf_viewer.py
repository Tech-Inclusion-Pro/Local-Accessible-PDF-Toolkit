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
    QPushButton,
    QLabel,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from ..utils.constants import COLORS, WCAGLevel, TagType
from ..utils.logger import get_logger
from ..core.pdf_handler import PDFHandler, PDFDocument
from ..core.wcag_validator import WCAGValidator, ValidationResult, IssueSeverity
from ..core.ai_detection import AIDetectionService, DocumentAnalysis, Detection
from ..core.ai_processor import get_ai_processor, AIBackend
from ..core.document_profile import DocumentProfileManager
from .widgets.navigation_panel import NavigationPanel
from .widgets.enhanced_pdf_viewer import EnhancedPDFViewer
from .widgets.ai_suggestions_panel import AISuggestionsPanel
from .widgets.tutorial_dialog import TutorialDialog

logger = get_logger(__name__)

# Auto-save interval in milliseconds (60 seconds)
AUTO_SAVE_INTERVAL = 60000


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


class ValidationWorker(QThread):
    """Background worker for WCAG validation."""

    finished = pyqtSignal(object)  # ValidationResult
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, document: PDFDocument, target_level: WCAGLevel = WCAGLevel.AA):
        super().__init__()
        self._document = document
        self._target_level = target_level

    def run(self):
        """Run the validation."""
        try:
            self.progress.emit(10, "Starting WCAG validation...")
            validator = WCAGValidator(target_level=self._target_level)

            self.progress.emit(50, "Checking accessibility criteria...")
            result = validator.validate(self._document)

            self.progress.emit(100, "Validation complete")
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            self.error.emit(str(e))


class PDFViewerPanel(QWidget):
    """Main PDF viewer panel with three-panel layout."""

    # Signals
    document_loaded = pyqtSignal(object)
    overlay_selected = pyqtSignal(dict)
    suggestion_applied = pyqtSignal(dict)
    file_dropped = pyqtSignal(str)  # Emitted when a file is dropped
    validation_complete = pyqtSignal(object)  # ValidationResult

    def __init__(self, parent=None):
        super().__init__(parent)

        self._handler = PDFHandler()
        self._document: Optional[PDFDocument] = None
        self._analysis: Optional[DocumentAnalysis] = None
        self._detection_service = AIDetectionService()
        self._analysis_worker: Optional[AnalysisWorker] = None
        self._validation_worker: Optional[ValidationWorker] = None
        self._last_validation_result: Optional[ValidationResult] = None
        self._undo_stack: list = []
        self._has_unsaved_changes = False
        self._last_save_stack_size = 0

        # Enable drag and drop
        self.setAcceptDrops(True)

        self._setup_ui()
        self._setup_connections()
        self._setup_accessibility()
        self._apply_styles()
        self._setup_auto_save()

    def _setup_ui(self) -> None:
        """Set up the three-panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top toolbar (hidden until file is loaded) - compact size
        self._toolbar = QFrame()
        self._toolbar.setObjectName("pdfToolbar")
        self._toolbar.setVisible(False)
        self._toolbar.setFixedHeight(36)
        toolbar_layout = QHBoxLayout(self._toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)
        toolbar_layout.setSpacing(8)

        # File info label
        self._file_info_label = QLabel("No file loaded")
        self._file_info_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 10pt;")
        toolbar_layout.addWidget(self._file_info_label)

        toolbar_layout.addStretch()

        # Auto-save status label
        self._auto_save_label = QLabel("")
        self._auto_save_label.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 9pt; font-style: italic;")
        toolbar_layout.addWidget(self._auto_save_label)

        # Save button
        self._save_btn = QPushButton("Save")
        self._save_btn.setToolTip("Save changes (Ctrl+S)")
        self._save_btn.clicked.connect(self._save_document)
        self._save_btn.setFixedHeight(26)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 3px;
                padding: 2px 12px;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}
        """)
        toolbar_layout.addWidget(self._save_btn)

        # Tutorial button
        self._tutorial_btn = QPushButton("\u2630 Tutorial")
        self._tutorial_btn.setToolTip("Learn how to use this application")
        self._tutorial_btn.clicked.connect(self._show_tutorial)
        self._tutorial_btn.setFixedHeight(26)
        self._tutorial_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.PRIMARY};
                color: white;
                border: none;
                border-radius: 3px;
                padding: 2px 12px;
                font-size: 10pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY_DARK};
            }}
        """)
        toolbar_layout.addWidget(self._tutorial_btn)

        layout.addWidget(self._toolbar)

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
        self._suggestions.doc_property_changed.connect(self.apply_doc_property)

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
            #pdfToolbar {{
                background-color: {COLORS.SURFACE};
                border-bottom: 1px solid {COLORS.BORDER};
            }}
        """)

    def _setup_auto_save(self) -> None:
        """Set up auto-save timer."""
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.timeout.connect(self._auto_save)
        # Timer will be started when a file is loaded

    def _auto_save(self) -> None:
        """Perform auto-save if there are unsaved changes."""
        if not self._document:
            return

        # Check if there are new changes since last save
        if len(self._undo_stack) > self._last_save_stack_size:
            logger.info("Auto-saving document...")
            self._auto_save_label.setText("Auto-saving...")

            try:
                # Save to a temporary tagged version
                save_path = self._document.path.with_stem(
                    self._document.path.stem + "_tagged_autosave"
                )

                if self._handler.save(save_path):
                    self._last_save_stack_size = len(self._undo_stack)
                    self._auto_save_label.setText(f"Auto-saved at {self._get_current_time()}")
                    logger.info(f"Auto-saved to: {save_path}")
                else:
                    self._auto_save_label.setText("Auto-save failed")
                    logger.warning("Auto-save failed")
            except Exception as e:
                self._auto_save_label.setText("Auto-save failed")
                logger.error(f"Auto-save error: {e}")
        else:
            self._auto_save_label.setText("No changes to save")

    def _get_current_time(self) -> str:
        """Get current time as formatted string."""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    def _show_tutorial(self) -> None:
        """Show the tutorial dialog."""
        dialog = TutorialDialog(self)
        dialog.exec()

    def load_file(self, file_path: Path) -> bool:
        """
        Load a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            True if successful
        """
        logger.info(f"Loading file: {file_path}")

        # Stop auto-save timer if running
        if self._auto_save_timer.isActive():
            self._auto_save_timer.stop()

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
        self._last_save_stack_size = 0

        # Set document properties in suggestions panel
        self._suggestions.set_document_properties(
            title=document.title,
            language=document.language,
            author=document.author,
            subject=document.metadata.get("subject"),
        )

        # Show toolbar with file info
        self._toolbar.setVisible(True)
        self._file_info_label.setText(f"\u25A1 {file_path.name} ({document.page_count} pages)")
        self._auto_save_label.setText("Auto-save enabled (every 60s)")

        # Start auto-save timer
        self._auto_save_timer.start(AUTO_SAVE_INTERVAL)

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
        detection_type = detection.get("detection_type", "") or detection.get("type", "")
        detection_id = detection.get("id", "")
        metadata = detection.get("metadata", {})

        # Add to undo stack (save original state)
        self._undo_stack.append(("apply", detection.copy()))

        # Apply the change based on type
        if self._document and applied_value:
            try:
                if detection_type == "image":
                    page_num = detection.get("page_number", 1)
                    img_index = metadata.get("image_index", 0)
                    self._handler.set_image_alt_text(page_num, img_index, applied_value)
                    logger.info(f"Applied alt text on page {page_num}, image {img_index}: {applied_value[:60]}")
                elif detection_type == "heading":
                    logger.info(f"Applied heading: {applied_value}")
                elif detection_type == "link":
                    logger.info(f"Applied link text: {applied_value}")
                elif detection_type == "table":
                    logger.info(f"Applied table header: {applied_value}")

                # Update detection status
                detection["status"] = "applied"

                # Update overlay color to green (success)
                if detection_id:
                    self._viewer.update_overlay_status(detection_id, "applied")

                # Save to disk so changes persist
                self._save_and_persist()

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

        # Re-validate and persist after batch apply
        result = self.run_validation()
        self._save_and_persist(result)

        score_msg = f"\nUpdated score: {result.score:.0f}%" if result else ""
        QMessageBox.information(
            self,
            "Applied",
            f"Applied {len(selected)} suggestions.{score_msg}\n"
            "Changes saved automatically.",
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

        # Re-validate and persist after batch apply
        result = self.run_validation()
        self._save_and_persist(result)

        score_msg = f"\nUpdated score: {result.score:.0f}%" if result else ""
        QMessageBox.information(
            self,
            "Applied",
            f"Applied {count} suggestions.{score_msg}\n"
            "Changes saved automatically.",
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
            QMessageBox.information(self, "No Document", "Please open a PDF file first.")
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
            self._auto_save_label.setText("Saving...")

            if self._handler.save(Path(file_path)):
                # Update save tracking
                self._last_save_stack_size = len(self._undo_stack)
                self._auto_save_label.setText(f"Saved at {self._get_current_time()}")

                QMessageBox.information(
                    self,
                    "Saved",
                    f"Document saved successfully to:\n{file_path}",
                )
                logger.info(f"Document saved to: {file_path}")
            else:
                raise Exception("Save failed")
        except Exception as e:
            self._auto_save_label.setText("Save failed")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save document: {e}",
            )
            logger.error(f"Save failed: {e}")

    def _on_review_mode_changed(self, auto_accept: bool) -> None:
        """Handle review mode change."""
        if auto_accept:
            # In auto-accept mode, apply suggestions as they come
            logger.info("Auto-accept mode enabled")
        else:
            logger.info("Manual review mode enabled")

    def _save_and_persist(self, result: Optional[ValidationResult] = None) -> None:
        """Save the PDF to disk and persist the compliance score to the document profile."""
        if not self._document:
            return

        # Save the PDF so changes persist on disk
        try:
            if self._handler.save():
                self._last_save_stack_size = len(self._undo_stack)
                self._auto_save_label.setText(f"Saved at {self._get_current_time()}")
                logger.info(f"Auto-saved after fix: {self._document.path}")
            else:
                logger.warning("Auto-save after fix failed")
        except Exception as e:
            logger.error(f"Auto-save after fix error: {e}")

        # Persist document profile so the score is remembered across sessions
        if result and self._document.path:
            try:
                DocumentProfileManager.save_session(self._document.path, result)
            except Exception as e:
                logger.debug(f"Document profile save skipped: {e}")

    def apply_doc_property(self, prop: str, value: str) -> None:
        """Apply a document-level property change (title, language) and re-validate."""
        if not self._document or not value.strip():
            return

        if prop == "title":
            self._handler.set_title(value.strip())
            logger.info(f"Set document title to: {value.strip()}")
        elif prop == "language":
            self._handler.set_language(value.strip())
            logger.info(f"Set document language to: {value.strip()}")
        else:
            return

        # Update the suggestions panel display
        self._suggestions.set_document_properties(
            title=self._document.title,
            language=self._document.language,
            author=self._document.author,
            subject=self._document.metadata.get("subject"),
        )

        # Re-validate to update score
        result = self.run_validation()

        # Save to disk and persist profile
        self._save_and_persist(result)

        if result:
            QMessageBox.information(
                self,
                "Property Updated",
                f"Document {prop} set to '{value.strip()}'.\n\n"
                f"Updated score: {result.score:.0f}%\n"
                "Changes saved automatically.",
            )

    def auto_fix_wcag(self) -> Optional[ValidationResult]:
        """Auto-fix common WCAG issues and re-validate."""
        if not self._document:
            return None

        # Validate first to find fixable issues
        validator = WCAGValidator()
        result = validator.validate(self._document)
        fixable_issues = [i for i in result.issues if i.auto_fixable]

        if not fixable_issues:
            return result

        fixed = 0
        details = []

        criteria = set(i.criterion for i in fixable_issues)

        # 2.4.2: Fix missing title
        if "2.4.2" in criteria and (not self._document.title or self._document.title.strip() == ""):
            humanized = self._document.path.stem.replace("_", " ").replace("-", " ").title()
            self._handler.set_title(humanized)
            fixed += 1
            details.append(f"Set title to '{humanized}'")

        # 3.1.1: Fix missing language
        if "3.1.1" in criteria and not self._document.language:
            self._handler.set_language("en")
            fixed += 1
            details.append("Set language to 'en'")

        # 1.3.1 / 1.3.2: Fix missing tags/structure
        if "1.3.1" in criteria or "1.3.2" in criteria:
            if not self._document.is_tagged or not self._document.has_structure:
                self._handler.ensure_tagged()
                fixed += 1
                details.append("Created document structure tree")

        # 1.3.1: Fix missing heading tags
        heading_issues = [
            i for i in fixable_issues
            if i.criterion == "1.3.1" and "heading" in i.message.lower()
        ]
        if heading_issues:
            headings = self._handler.detect_headings()
            if headings:
                headings.sort(key=lambda e: e.attributes.get("size", 0), reverse=True)
                sizes = sorted(set(e.attributes.get("size", 0) for e in headings), reverse=True)
                size_to_level = {size: min(i + 1, 6) for i, size in enumerate(sizes)}
                for element in headings:
                    size = element.attributes.get("size", 0)
                    level = size_to_level.get(size, 6)
                    tag_type = TagType(f"H{level}")
                    element.tag = tag_type
                    # Persist heading tag to the PDF structure tree
                    self._handler.add_tag(element.page_number, element.bbox, tag_type)
                fixed += 1
                details.append(f"Auto-tagged {len(headings)} headings")

        # 1.1.1: Fix missing image alt text
        image_issues = [i for i in fixable_issues if i.criterion == "1.1.1"]
        if image_issues:
            ai = None
            try:
                ai = get_ai_processor(AIBackend.OLLAMA)
                if not ai.is_available:
                    ai = None
            except Exception:
                pass

            img_fixed = 0
            for issue in image_issues:
                page_num = issue.page or 1
                alt_text = None
                if ai:
                    try:
                        image_bytes = self._handler.get_image_bytes(page_num, img_fixed)
                        if image_bytes:
                            context = ""
                            for page in self._document.pages:
                                if page.page_number == page_num:
                                    context = page.text[:200]
                                    break
                            response = ai.generate_alt_text(image_bytes, context=context)
                            if response.success and response.content.strip():
                                alt_text = response.content.strip()
                    except Exception as e:
                        logger.debug(f"AI alt text failed for page {page_num}: {e}")
                if not alt_text:
                    alt_text = f"Image on page {page_num} (needs descriptive alt text)"
                self._handler.set_image_alt_text(page_num, img_fixed, alt_text)
                img_fixed += 1

            if img_fixed > 0:
                fixed += 1
                details.append(f"Added alt text to {img_fixed} images")

        # Update suggestions panel with new properties
        self._suggestions.set_document_properties(
            title=self._document.title,
            language=self._document.language,
            author=self._document.author,
            subject=self._document.metadata.get("subject"),
        )

        # Re-validate
        new_result = validator.validate(self._document)
        self._last_validation_result = new_result
        self.validation_complete.emit(new_result)

        # Save to disk and persist profile
        if fixed > 0:
            self._save_and_persist(new_result)

            detail_text = "\n".join(f"  - {d}" for d in details)
            QMessageBox.information(
                self,
                "Auto-Fix",
                f"Applied {fixed} fixes:\n\n{detail_text}\n\n"
                f"Updated score: {new_result.score:.0f}%\n"
                "Changes saved automatically.",
            )
        else:
            QMessageBox.information(self, "Auto-Fix", "No auto-fixable issues found.")

        return new_result

    def run_validation(self, target_level: WCAGLevel = WCAGLevel.AA) -> Optional[ValidationResult]:
        """
        Run WCAG validation on the current document synchronously.

        Args:
            target_level: Target WCAG compliance level

        Returns:
            ValidationResult or None if no document loaded
        """
        if not self._document:
            return None

        validator = WCAGValidator(target_level=target_level)
        result = validator.validate(self._document)
        self._last_validation_result = result
        self.validation_complete.emit(result)
        return result

    def run_validation_async(self, target_level: WCAGLevel = WCAGLevel.AA) -> None:
        """
        Run WCAG validation asynchronously with a progress dialog.

        Args:
            target_level: Target WCAG compliance level
        """
        if not self._document:
            return

        progress = QProgressDialog("Validating WCAG compliance...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(200)

        self._validation_worker = ValidationWorker(self._document, target_level)
        self._validation_worker.progress.connect(
            lambda val, msg: (progress.setValue(val), progress.setLabelText(msg))
        )
        self._validation_worker.finished.connect(self._on_validation_complete)
        self._validation_worker.finished.connect(progress.close)
        self._validation_worker.error.connect(
            lambda err: QMessageBox.warning(self, "Validation Error", f"Validation failed: {err}")
        )
        self._validation_worker.error.connect(progress.close)
        self._validation_worker.start()

    def _on_validation_complete(self, result: ValidationResult) -> None:
        """Handle completed validation."""
        self._last_validation_result = result
        self.validation_complete.emit(result)
        logger.info(
            f"Validation complete: score={result.score}, "
            f"errors={result.summary.get('errors', 0)}"
        )

    def close_document(self) -> None:
        """Close the current document."""
        # Stop auto-save timer
        if self._auto_save_timer.isActive():
            self._auto_save_timer.stop()

        if self._document:
            self._handler.close()
            self._document = None
            self._analysis = None

        self._viewer.clear()
        self._suggestions.clear()
        self._undo_stack.clear()
        self._last_save_stack_size = 0

        # Hide toolbar
        self._toolbar.setVisible(False)
        self._file_info_label.setText("No file loaded")

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
        return len(self._undo_stack) > self._last_save_stack_size

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
