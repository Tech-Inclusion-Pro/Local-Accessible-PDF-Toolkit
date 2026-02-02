"""
HTML converter panel for exporting PDFs to accessible HTML.
"""

from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QFrame,
    QLabel,
    QPushButton,
    QComboBox,
    QCheckBox,
    QLineEdit,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ..utils.constants import COLORS
from ..utils.logger import get_logger
from ..core.pdf_handler import PDFHandler, PDFDocument
from ..core.html_generator import HTMLGenerator, HTMLOptions, GeneratedHTML

logger = get_logger(__name__)


class HTMLPreview(QTextEdit):
    """HTML preview widget with syntax highlighting."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Fira Code", 12))
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}
        """)
        self.setAccessibleName("HTML preview")

    def setHTML(self, html: str) -> None:
        """Set the HTML content."""
        self.setPlainText(html)


class HTMLConverter(QWidget):
    """HTML converter panel for PDF to HTML conversion."""

    # Signals
    conversion_complete = pyqtSignal(object)  # GeneratedHTML

    def __init__(self, parent=None):
        super().__init__(parent)

        self._handler = PDFHandler()
        self._document: Optional[PDFDocument] = None
        self._result: Optional[GeneratedHTML] = None

        self._setup_ui()
        self._setup_accessibility()

    def _setup_ui(self) -> None:
        """Set up the UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Options
        options_panel = QFrame()
        options_panel.setFixedWidth(300)
        options_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND};
                border-right: 1px solid {COLORS.BORDER};
            }}
        """)

        options_scroll = QScrollArea()
        options_scroll.setWidget(options_panel)
        options_scroll.setWidgetResizable(True)
        options_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        options_layout = QVBoxLayout(options_panel)
        options_layout.setContentsMargins(16, 16, 16, 16)
        options_layout.setSpacing(16)

        # File section
        file_group = QGroupBox("Source File")
        file_layout = QVBoxLayout(file_group)

        self.file_label = QLabel("No file loaded")
        self.file_label.setWordWrap(True)
        file_layout.addWidget(self.file_label)

        open_btn = QPushButton("Open PDF...")
        open_btn.clicked.connect(self.open_file)
        file_layout.addWidget(open_btn)

        options_layout.addWidget(file_group)

        # Theme section
        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout(theme_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Brand (Default)", "brand")
        self.theme_combo.addItem("High Contrast", "high_contrast")
        self.theme_combo.addItem("Dark Mode", "dark")
        self.theme_combo.currentIndexChanged.connect(self._on_options_changed)
        self.theme_combo.setAccessibleName("Select theme")
        theme_layout.addWidget(self.theme_combo)

        options_layout.addWidget(theme_group)

        # Content options
        content_group = QGroupBox("Content Options")
        content_layout = QVBoxLayout(content_group)

        self.include_styles_cb = QCheckBox("Include CSS Styles")
        self.include_styles_cb.setChecked(True)
        self.include_styles_cb.stateChanged.connect(self._on_options_changed)
        content_layout.addWidget(self.include_styles_cb)

        self.include_toc_cb = QCheckBox("Include Table of Contents")
        self.include_toc_cb.setChecked(True)
        self.include_toc_cb.stateChanged.connect(self._on_options_changed)
        content_layout.addWidget(self.include_toc_cb)

        self.include_images_cb = QCheckBox("Include Images")
        self.include_images_cb.setChecked(True)
        self.include_images_cb.stateChanged.connect(self._on_options_changed)
        content_layout.addWidget(self.include_images_cb)

        self.embed_images_cb = QCheckBox("Embed Images (Base64)")
        self.embed_images_cb.stateChanged.connect(self._on_options_changed)
        content_layout.addWidget(self.embed_images_cb)

        self.responsive_cb = QCheckBox("Responsive Layout")
        self.responsive_cb.setChecked(True)
        self.responsive_cb.stateChanged.connect(self._on_options_changed)
        content_layout.addWidget(self.responsive_cb)

        self.dividers_cb = QCheckBox("Page Dividers")
        self.dividers_cb.setChecked(True)
        self.dividers_cb.stateChanged.connect(self._on_options_changed)
        content_layout.addWidget(self.dividers_cb)

        self.aria_cb = QCheckBox("Add ARIA Attributes")
        self.aria_cb.setChecked(True)
        self.aria_cb.stateChanged.connect(self._on_options_changed)
        content_layout.addWidget(self.aria_cb)

        options_layout.addWidget(content_group)

        # Language
        lang_group = QGroupBox("Language")
        lang_layout = QHBoxLayout(lang_group)

        lang_label = QLabel("Language Code:")
        lang_layout.addWidget(lang_label)

        self.lang_input = QLineEdit("en")
        self.lang_input.setMaximumWidth(80)
        self.lang_input.setAccessibleName("Language code")
        lang_layout.addWidget(self.lang_input)
        lang_layout.addStretch()

        options_layout.addWidget(lang_group)

        # Section extraction
        section_group = QGroupBox("Section Extraction")
        section_layout = QVBoxLayout(section_group)

        section_label = QLabel("Extract specific section:")
        section_layout.addWidget(section_label)

        self.section_start = QLineEdit()
        self.section_start.setPlaceholderText("Start heading text...")
        self.section_start.setAccessibleName("Section start heading")
        section_layout.addWidget(self.section_start)

        self.section_end = QLineEdit()
        self.section_end.setPlaceholderText("End heading text (optional)...")
        self.section_end.setAccessibleName("Section end heading")
        section_layout.addWidget(self.section_end)

        options_layout.addWidget(section_group)

        # Action buttons
        actions_layout = QVBoxLayout()

        convert_btn = QPushButton("Convert to HTML")
        convert_btn.clicked.connect(self.convert)
        convert_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY_DARK};
            }}
        """)
        actions_layout.addWidget(convert_btn)

        save_btn = QPushButton("Save HTML...")
        save_btn.clicked.connect(self.save)
        save_btn.setStyleSheet(f"""
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
        actions_layout.addWidget(save_btn)

        options_layout.addLayout(actions_layout)
        options_layout.addStretch()

        splitter.addWidget(options_scroll)

        # Right panel: Preview
        preview_panel = QFrame()
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        # Preview toolbar
        preview_toolbar = QFrame()
        preview_toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND_ALT};
                border-bottom: 1px solid {COLORS.BORDER};
            }}
        """)
        toolbar_layout = QHBoxLayout(preview_toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)

        preview_label = QLabel("HTML Preview")
        preview_label.setStyleSheet(f"font-weight: bold; color: {COLORS.TEXT_PRIMARY}; font-size: 12pt;")
        toolbar_layout.addWidget(preview_label)

        toolbar_layout.addStretch()

        # View mode toggle
        self.view_source_btn = QPushButton("Source")
        self.view_source_btn.setCheckable(True)
        self.view_source_btn.setChecked(True)
        self.view_source_btn.clicked.connect(self._toggle_view)
        toolbar_layout.addWidget(self.view_source_btn)

        self.view_render_btn = QPushButton("Rendered")
        self.view_render_btn.setCheckable(True)
        self.view_render_btn.clicked.connect(self._toggle_view)
        toolbar_layout.addWidget(self.view_render_btn)

        for btn in [self.view_source_btn, self.view_render_btn]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.SURFACE};
                    color: {COLORS.TEXT_PRIMARY};
                    border: 1px solid {COLORS.BORDER};
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 12pt;
                }}
                QPushButton:checked {{
                    background-color: {COLORS.PRIMARY};
                    color: white;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.PRIMARY_LIGHT};
                }}
            """)

        preview_layout.addWidget(preview_toolbar)

        # Preview content
        self.source_preview = HTMLPreview()
        preview_layout.addWidget(self.source_preview)

        self.rendered_preview = QTextEdit()
        self.rendered_preview.setReadOnly(True)
        self.rendered_preview.setAccessibleName("Rendered HTML preview")
        self.rendered_preview.hide()
        preview_layout.addWidget(self.rendered_preview)

        splitter.addWidget(preview_panel)

        # Set splitter sizes
        splitter.setSizes([300, 700])

        layout.addWidget(splitter)

        # Apply general styles
        self._apply_styles()

    def _apply_styles(self) -> None:
        """Apply common styles - dark theme with white text."""
        checkbox_style = f"""
            QCheckBox {{
                spacing: 8px;
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS.PRIMARY};
                border: 2px solid {COLORS.PRIMARY};
                border-radius: 3px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {COLORS.INPUT_BG};
                border: 2px solid {COLORS.BORDER};
                border-radius: 3px;
            }}
        """

        for cb in [
            self.include_styles_cb,
            self.include_toc_cb,
            self.include_images_cb,
            self.embed_images_cb,
            self.responsive_cb,
            self.dividers_cb,
            self.aria_cb,
        ]:
            cb.setStyleSheet(checkbox_style)

        # Apply styles to labels
        for label in [self.file_label]:
            label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 12pt;")

        # Apply styles to inputs
        input_style = f"""
            QLineEdit {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS.INPUT_FOCUS};
            }}
        """
        for line_edit in [self.lang_input, self.section_start, self.section_end]:
            line_edit.setStyleSheet(input_style)

        # Apply styles to combo box
        self.theme_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                selection-background-color: {COLORS.PRIMARY};
            }}
        """)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self.setAccessibleName("HTML Converter")
        self.setAccessibleDescription("Convert PDF documents to accessible HTML")

    def _get_options(self) -> HTMLOptions:
        """Get current conversion options."""
        return HTMLOptions(
            theme=self.theme_combo.currentData(),
            include_styles=self.include_styles_cb.isChecked(),
            include_toc=self.include_toc_cb.isChecked(),
            responsive=self.responsive_cb.isChecked(),
            include_images=self.include_images_cb.isChecked(),
            embed_images=self.embed_images_cb.isChecked(),
            section_dividers=self.dividers_cb.isChecked(),
            add_aria=self.aria_cb.isChecked(),
            language=self.lang_input.text() or "en",
        )

    def _on_options_changed(self) -> None:
        """Handle options change."""
        # Auto-regenerate if we have a document
        if self._document and self._result:
            self.convert()

    def _toggle_view(self) -> None:
        """Toggle between source and rendered view."""
        sender = self.sender()

        if sender == self.view_source_btn:
            self.view_source_btn.setChecked(True)
            self.view_render_btn.setChecked(False)
            self.source_preview.show()
            self.rendered_preview.hide()
        else:
            self.view_source_btn.setChecked(False)
            self.view_render_btn.setChecked(True)
            self.source_preview.hide()
            self.rendered_preview.show()

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
            self.file_label.setText(f"File: {file_path.name}\nPages: {document.page_count}")

            # Clear previous result
            self._result = None
            self.source_preview.clear()
            self.rendered_preview.clear()

            logger.info(f"Loaded document: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load document: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load PDF: {e}")
            return False

    def convert(self) -> None:
        """Convert the document to HTML."""
        if not self._document:
            QMessageBox.information(self, "No Document", "Please open a PDF first")
            return

        try:
            generator = HTMLGenerator(self._get_options())

            # Check for section extraction
            start_heading = self.section_start.text().strip()
            if start_heading:
                end_heading = self.section_end.text().strip() or None
                self._result = generator.generate_section(
                    self._document,
                    start_heading,
                    end_heading,
                )
            else:
                self._result = generator.generate(self._document)

            # Update previews
            self.source_preview.setHTML(self._result.html)
            self.rendered_preview.setHtml(self._result.html)

            self.conversion_complete.emit(self._result)

            # Show any warnings
            if self._result.warnings:
                QMessageBox.warning(
                    self,
                    "Conversion Warnings",
                    "\n".join(self._result.warnings),
                )

            logger.info("Conversion complete")

        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            QMessageBox.critical(self, "Error", f"Conversion failed: {e}")

    def save(self) -> None:
        """Save the generated HTML."""
        if not self._result:
            QMessageBox.information(
                self,
                "No Content",
                "Please convert a PDF first",
            )
            return

        # Suggest filename based on document
        suggested_name = ""
        if self._document:
            suggested_name = self._document.path.stem + ".html"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save HTML File",
            suggested_name,
            "HTML Files (*.html);;All Files (*.*)",
        )

        if file_path:
            generator = HTMLGenerator(self._get_options())
            if generator.save(self._result, Path(file_path)):
                QMessageBox.information(
                    self,
                    "Saved",
                    f"HTML saved to:\n{file_path}",
                )
            else:
                QMessageBox.warning(self, "Error", "Failed to save HTML file")

    @property
    def current_document(self) -> Optional[PDFDocument]:
        """Get the current document."""
        return self._document

    @property
    def generated_html(self) -> Optional[GeneratedHTML]:
        """Get the generated HTML."""
        return self._result
