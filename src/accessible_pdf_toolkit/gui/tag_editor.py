"""
Tag editor panel for editing PDF accessibility tags.
"""

from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, field

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QFrame,
    QLabel,
    QPushButton,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from ..utils.constants import COLORS, TagType
from ..utils.logger import get_logger
from ..core.pdf_handler import PDFHandler, PDFDocument, PDFElement
from ..core.wcag_validator import WCAGValidator, ValidationResult
from ..core.ai_processor import AIProcessor, get_ai_processor, AIBackend
from .widgets.pdf_preview import PDFPreview
from .widgets.tag_tree import TagTreeWidget
from .widgets.compliance_meter import ComplianceMeter

logger = get_logger(__name__)


class _TagEditorValidationWorker(QThread):
    """Small inline worker for non-blocking validation in the tag editor."""

    finished = pyqtSignal(object)  # ValidationResult
    error = pyqtSignal(str)

    def __init__(self, validator: WCAGValidator, document):
        super().__init__()
        self._validator = validator
        self._document = document

    def run(self):
        try:
            result = self._validator.validate(self._document)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


@dataclass
class _UndoEntry:
    """Snapshot of element tag states for undo/redo."""
    description: str
    # List of (page_number, element_index, old_tag, old_alt_text) tuples
    changes: List[Tuple[int, int, Any, Any]] = field(default_factory=list)
    # Document-level metadata at time of snapshot
    title: Optional[str] = None
    language: Optional[str] = None
    is_tagged: bool = False
    has_structure: bool = False


class TagEditor(QWidget):
    """Tag editor panel with PDF preview and tag tree."""

    # Signals
    document_loaded = pyqtSignal(object)  # PDFDocument
    document_saved = pyqtSignal(str)  # path
    validation_complete = pyqtSignal(object)  # ValidationResult

    def __init__(self, parent=None):
        super().__init__(parent)

        self._handler = PDFHandler()
        self._validator = WCAGValidator()
        self._ai_processor: Optional[AIProcessor] = None
        self._document: Optional[PDFDocument] = None
        self._modified = False
        self._validation_worker: Optional[_TagEditorValidationWorker] = None
        self._undo_stack: List[_UndoEntry] = []
        self._redo_stack: List[_UndoEntry] = []
        self._max_undo = 50

        self._setup_ui()
        self._setup_connections()
        self._setup_accessibility()

    def _setup_ui(self) -> None:
        """Set up the UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: PDF preview
        preview_panel = QFrame()
        preview_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND};
                border-right: 1px solid {COLORS.BORDER};
            }}
        """)
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        self.preview = PDFPreview()
        self.preview.set_handler(self._handler)
        preview_layout.addWidget(self.preview)

        splitter.addWidget(preview_panel)

        # Center panel: Tag tree
        tree_panel = QFrame()
        tree_layout = QVBoxLayout(tree_panel)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = self._create_toolbar()
        tree_layout.addWidget(toolbar)

        self.tag_tree = TagTreeWidget()
        tree_layout.addWidget(self.tag_tree)

        splitter.addWidget(tree_panel)

        # Right panel: Compliance meter
        compliance_panel = QFrame()
        compliance_panel.setFixedWidth(250)
        compliance_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND_ALT};
                border-left: 1px solid {COLORS.BORDER};
            }}
            QLabel {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}
        """)
        compliance_layout = QVBoxLayout(compliance_panel)
        compliance_layout.setContentsMargins(16, 16, 16, 16)

        self.compliance_meter = ComplianceMeter()
        compliance_layout.addWidget(self.compliance_meter)

        # Action buttons
        validate_btn = QPushButton("Validate")
        validate_btn.clicked.connect(self.validate)
        validate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY_DARK};
            }}
        """)
        compliance_layout.addWidget(validate_btn)

        auto_fix_btn = QPushButton("Auto-Fix Issues")
        auto_fix_btn.clicked.connect(self.auto_fix)
        auto_fix_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.SECONDARY};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {COLORS.SECONDARY_DARK};
            }}
        """)
        compliance_layout.addWidget(auto_fix_btn)

        ai_suggest_btn = QPushButton("AI Suggestions")
        ai_suggest_btn.clicked.connect(self.get_ai_suggestions)
        ai_suggest_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.ACCENT};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {COLORS.ACCENT_DARK};
            }}
        """)
        compliance_layout.addWidget(ai_suggest_btn)

        compliance_layout.addStretch()

        splitter.addWidget(compliance_panel)

        # Set splitter sizes
        splitter.setSizes([400, 400, 250])

        layout.addWidget(splitter)

    def _create_toolbar(self) -> QFrame:
        """Create the toolbar."""
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND_ALT};
                border-bottom: 1px solid {COLORS.BORDER};
            }}
        """)
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(8, 4, 8, 4)

        # Open button
        open_btn = QPushButton("Open PDF")
        open_btn.clicked.connect(self.open_file)
        layout.addWidget(open_btn)

        # Save button
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)

        # Save As button
        save_as_btn = QPushButton("Save As...")
        save_as_btn.clicked.connect(self.save_as)
        layout.addWidget(save_as_btn)

        # Undo / Redo buttons
        undo_btn = QPushButton("\u21B6 Undo")
        undo_btn.setShortcut("Ctrl+Z")
        undo_btn.clicked.connect(self.undo)
        layout.addWidget(undo_btn)

        redo_btn = QPushButton("Redo \u21B7")
        redo_btn.setShortcut("Ctrl+Shift+Z")
        redo_btn.clicked.connect(self.redo)
        layout.addWidget(redo_btn)

        layout.addStretch()

        # Tag all headings
        auto_headings_btn = QPushButton("Auto-Tag Headings")
        auto_headings_btn.clicked.connect(self.auto_tag_headings)
        layout.addWidget(auto_headings_btn)

        # Button style - dark theme with white text
        for btn in [open_btn, save_btn, save_as_btn, undo_btn, redo_btn, auto_headings_btn]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.SURFACE};
                    color: {COLORS.TEXT_PRIMARY};
                    border: 1px solid {COLORS.BORDER};
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 12pt;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.PRIMARY_LIGHT};
                    color: white;
                }}
                QPushButton:focus {{
                    border: 2px solid {COLORS.PRIMARY};
                }}
            """)

        return toolbar

    def _setup_connections(self) -> None:
        """Set up signal connections."""
        self.tag_tree.tag_selected.connect(self._on_tag_selected)
        self.tag_tree.tag_changed.connect(self._on_tag_changed)
        self.preview.page_changed.connect(self._on_page_changed)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self.setAccessibleName("Tag Editor")
        self.setAccessibleDescription("Edit PDF accessibility tags")

    # ==================== Undo / Redo ====================

    def _snapshot_state(self, description: str) -> None:
        """Take a snapshot of current document state for undo."""
        if not self._document:
            return

        changes = []
        for page in self._document.pages:
            for idx, elem in enumerate(page.elements):
                changes.append((
                    page.page_number,
                    idx,
                    elem.tag,
                    elem.alt_text,
                ))

        entry = _UndoEntry(
            description=description,
            changes=changes,
            title=self._document.title,
            language=self._document.language,
            is_tagged=self._document.is_tagged,
            has_structure=self._document.has_structure,
        )

        self._undo_stack.append(entry)
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)

        # Clear redo stack on new action
        self._redo_stack.clear()

    def _restore_state(self, entry: _UndoEntry) -> None:
        """Restore document state from a snapshot."""
        if not self._document:
            return

        # Restore document-level metadata
        if entry.title != self._document.title and entry.title is not None:
            self._handler.set_title(entry.title)
        if entry.language != self._document.language and entry.language is not None:
            self._handler.set_language(entry.language)

        # Restore element tags
        elem_map: Dict[Tuple[int, int], Tuple[Any, Any]] = {}
        for page_num, idx, tag, alt_text in entry.changes:
            elem_map[(page_num, idx)] = (tag, alt_text)

        for page in self._document.pages:
            for idx, elem in enumerate(page.elements):
                key = (page.page_number, idx)
                if key in elem_map:
                    elem.tag, elem.alt_text = elem_map[key]

        self.tag_tree.load_document(self._document)
        self._modified = True

    def undo(self) -> None:
        """Undo the last action."""
        if not self._undo_stack or not self._document:
            return

        # Save current state for redo
        redo_changes = []
        for page in self._document.pages:
            for idx, elem in enumerate(page.elements):
                redo_changes.append((page.page_number, idx, elem.tag, elem.alt_text))

        redo_entry = _UndoEntry(
            description="redo",
            changes=redo_changes,
            title=self._document.title,
            language=self._document.language,
            is_tagged=self._document.is_tagged,
            has_structure=self._document.has_structure,
        )
        self._redo_stack.append(redo_entry)

        # Restore previous state
        entry = self._undo_stack.pop()
        self._restore_state(entry)
        logger.debug(f"Undo: {entry.description}")

    def redo(self) -> None:
        """Redo the last undone action."""
        if not self._redo_stack or not self._document:
            return

        # Save current state for undo
        undo_changes = []
        for page in self._document.pages:
            for idx, elem in enumerate(page.elements):
                undo_changes.append((page.page_number, idx, elem.tag, elem.alt_text))

        undo_entry = _UndoEntry(
            description="undo",
            changes=undo_changes,
            title=self._document.title,
            language=self._document.language,
            is_tagged=self._document.is_tagged,
            has_structure=self._document.has_structure,
        )
        self._undo_stack.append(undo_entry)

        entry = self._redo_stack.pop()
        self._restore_state(entry)
        logger.debug("Redo applied")

    def open_file(self) -> None:
        """Open a PDF file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF File",
            "",
            "PDF Files (*.pdf);;All Files (*.*)",
        )

        if file_path:
            self.load_document(Path(file_path))

    def load_document(self, file_path: Path) -> bool:
        """
        Load a PDF document.

        Args:
            file_path: Path to PDF file

        Returns:
            True if successful
        """
        try:
            document = self._handler.open(file_path)
            if not document:
                QMessageBox.warning(self, "Error", "Failed to open PDF file")
                return False

            self._document = document
            self._modified = False
            self._undo_stack.clear()
            self._redo_stack.clear()

            # Update UI
            self.preview.load_document(document)
            self.tag_tree.load_document(document)
            self.compliance_meter.reset()

            self.document_loaded.emit(document)
            logger.info(f"Loaded document: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load document: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load PDF: {e}")
            return False

    def save(self) -> bool:
        """Save the current document."""
        if not self._document:
            return False

        if self._handler.save():
            self._modified = False
            self.document_saved.emit(str(self._document.path))
            return True

        QMessageBox.warning(self, "Error", "Failed to save document")
        return False

    def save_as(self) -> bool:
        """Save the document with a new name."""
        if not self._document:
            return False

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF File",
            str(self._document.path),
            "PDF Files (*.pdf)",
        )

        if file_path:
            if self._handler.save(Path(file_path)):
                self._modified = False
                self.document_saved.emit(file_path)
                return True

            QMessageBox.warning(self, "Error", "Failed to save document")

        return False

    def validate(self) -> None:
        """Validate the document for WCAG compliance (async)."""
        if not self._document:
            QMessageBox.information(self, "No Document", "Please open a PDF first")
            return

        self._validation_worker = _TagEditorValidationWorker(self._validator, self._document)
        self._validation_worker.finished.connect(self._on_validation_done)
        self._validation_worker.error.connect(
            lambda err: QMessageBox.warning(self, "Validation Error", f"Validation failed: {err}")
        )
        self._validation_worker.start()

    def _on_validation_done(self, result) -> None:
        """Handle validation completion."""
        self.compliance_meter.set_result(result)
        self.validation_complete.emit(result)

    def _auto_tag_headings_internal(self) -> int:
        """Detect headings and tag them. Returns number of headings tagged."""
        headings = self._handler.detect_headings()
        if not headings:
            return 0

        # Sort by font size (largest = H1)
        headings.sort(
            key=lambda e: e.attributes.get("size", 0),
            reverse=True,
        )

        # Assign heading levels
        sizes = sorted(set(e.attributes.get("size", 0) for e in headings), reverse=True)
        size_to_level = {size: min(i + 1, 6) for i, size in enumerate(sizes)}

        for element in headings:
            size = element.attributes.get("size", 0)
            level = size_to_level.get(size, 6)
            tag = TagType(f"H{level}")
            element.tag = tag

        return len(headings)

    def auto_fix(self) -> None:
        """Auto-fix common accessibility issues."""
        if not self._document:
            return

        self._snapshot_state("Auto-fix")

        # Validate first
        result = self._validator.validate(self._document)
        fixable_issues = [i for i in result.issues if i.auto_fixable]

        if not fixable_issues:
            QMessageBox.information(self, "Auto-Fix", "No auto-fixable issues found")
            return

        fixed = 0
        details = []

        # Group issues by criterion for efficient fixing
        criteria = set(i.criterion for i in fixable_issues)

        # 2.4.2: Fix missing title
        if "2.4.2" in criteria and (not self._document.title or self._document.title.strip() == ""):
            # Humanize the filename: "my_doc_v2" -> "My Doc V2"
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
        if ("1.3.1" in criteria or "1.3.2" in criteria):
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
            num_headings = self._auto_tag_headings_internal()
            if num_headings > 0:
                fixed += 1
                details.append(f"Auto-tagged {num_headings} headings")

        # 1.1.1: Fix missing image alt text (try AI, fallback to placeholder)
        image_issues = [i for i in fixable_issues if i.criterion == "1.1.1"]
        if image_issues:
            # Try to get an AI processor for better alt text
            ai = self._ai_processor
            if not ai:
                try:
                    ai = get_ai_processor(AIBackend.OLLAMA)
                    if not ai.is_available:
                        ai = None
                except Exception:
                    ai = None

            img_fixed = 0
            ai_generated = 0
            for issue in image_issues:
                page_num = issue.page or 1
                alt_text = None

                # Try AI-generated alt text
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
                                ai_generated += 1
                    except Exception as e:
                        logger.debug(f"AI alt text failed for page {page_num}: {e}")

                if not alt_text:
                    alt_text = f"Image on page {page_num} (needs descriptive alt text)"

                self._handler.set_image_alt_text(page_num, img_fixed, alt_text)
                img_fixed += 1

            if img_fixed > 0:
                fixed += 1
                if ai_generated > 0:
                    details.append(
                        f"Added alt text to {img_fixed} images "
                        f"({ai_generated} AI-generated, {img_fixed - ai_generated} placeholder)"
                    )
                else:
                    details.append(
                        f"Added placeholder alt text to {img_fixed} images "
                        "(configure AI for better descriptions)"
                    )

        # Mark document as modified
        if fixed > 0:
            self._modified = True
            self.tag_tree.load_document(self._document)

            detail_text = "\n".join(f"  - {d}" for d in details)
            QMessageBox.information(
                self,
                "Auto-Fix",
                f"Applied {fixed} fixes:\n\n{detail_text}\n\n"
                "Please review changes and save the document.",
            )

            # Re-validate synchronously to update the compliance meter immediately
            result = self._validator.validate(self._document)
            self.compliance_meter.set_result(result)
            self.validation_complete.emit(result)

    def auto_tag_headings(self) -> None:
        """Auto-detect and tag headings."""
        if not self._document:
            return

        self._snapshot_state("Auto-tag headings")

        headings = self._handler.detect_headings()
        if not headings:
            QMessageBox.information(self, "Auto-Tag", "No headings detected")
            return

        # Sort by font size (largest = H1)
        headings.sort(
            key=lambda e: e.attributes.get("size", 0),
            reverse=True,
        )

        # Assign heading levels
        sizes = sorted(set(e.attributes.get("size", 0) for e in headings), reverse=True)
        size_to_level = {size: min(i + 1, 6) for i, size in enumerate(sizes)}

        for element in headings:
            size = element.attributes.get("size", 0)
            level = size_to_level.get(size, 6)
            tag = TagType(f"H{level}")
            element.tag = tag

        self._modified = True
        self.tag_tree.load_document(self._document)

        QMessageBox.information(
            self,
            "Auto-Tag",
            f"Tagged {len(headings)} headings",
        )

    def get_ai_suggestions(self) -> None:
        """Get AI suggestions for accessibility improvements."""
        if not self._document:
            QMessageBox.information(self, "No Document", "Please open a PDF first")
            return

        # Try to get AI processor
        if not self._ai_processor:
            try:
                self._ai_processor = get_ai_processor(AIBackend.OLLAMA)
            except Exception as e:
                logger.warning(f"Failed to initialize AI processor: {e}")

        if not self._ai_processor or not self._ai_processor.is_available:
            QMessageBox.warning(
                self,
                "AI Not Available",
                "No AI backend is available.\n\n"
                "Please configure Ollama, LM Studio, or GPT4All in Settings.",
            )
            return

        # Get suggestions
        text = self._handler.get_full_text()
        response = self._ai_processor.suggest_headings(text[:4000])

        if response.success:
            QMessageBox.information(
                self,
                "AI Suggestions",
                f"AI Analysis:\n\n{response.content[:500]}...",
            )
        else:
            QMessageBox.warning(
                self,
                "AI Error",
                f"Failed to get AI suggestions:\n{response.error}",
            )

    def _on_tag_selected(self, element: PDFElement) -> None:
        """Handle tag selection."""
        # Scroll to element in preview
        if element.page_number != self.preview.current_page:
            self.preview.go_to_page(element.page_number)

    def _on_tag_changed(self, element: PDFElement, new_tag: TagType) -> None:
        """Handle tag change."""
        self._snapshot_state(f"Change tag to {new_tag.value}")
        self._modified = True
        # Apply tag to PDF
        self._handler.add_tag(
            element.page_number,
            element.bbox,
            new_tag,
            element.alt_text,
        )

    def _on_page_changed(self, page: int) -> None:
        """Handle page change in preview."""
        # Could filter tag tree to show current page
        pass

    @property
    def is_modified(self) -> bool:
        """Check if document has unsaved changes."""
        return self._modified

    @property
    def current_document(self) -> Optional[PDFDocument]:
        """Get the current document."""
        return self._document
