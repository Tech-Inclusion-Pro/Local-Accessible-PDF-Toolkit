"""
PDF preview widget for displaying PDF pages.
"""

from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QPushButton,
    QSpinBox,
    QSlider,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QImage

from ...utils.constants import COLORS
from ...utils.logger import get_logger
from ...core.pdf_handler import PDFHandler, PDFDocument

logger = get_logger(__name__)


class PDFPreview(QWidget):
    """Widget for previewing PDF pages."""

    # Signals
    page_changed = pyqtSignal(int)
    zoom_changed = pyqtSignal(float)
    element_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._handler: Optional[PDFHandler] = None
        self._document: Optional[PDFDocument] = None
        self._current_page = 1
        self._zoom = 1.0
        self._min_zoom = 0.25
        self._max_zoom = 4.0

        self._setup_ui()
        self._setup_accessibility()

    def _setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND_ALT};
                border-bottom: 1px solid {COLORS.BORDER};
                padding: 4px;
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)

        # Page navigation
        self.prev_btn = QPushButton("<")
        self.prev_btn.setFixedWidth(30)
        self.prev_btn.setToolTip("Previous page")
        self.prev_btn.clicked.connect(self.previous_page)
        toolbar_layout.addWidget(self.prev_btn)

        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.valueChanged.connect(self._on_page_spin_changed)
        self.page_spin.setAccessibleName("Current page")
        toolbar_layout.addWidget(self.page_spin)

        self.page_label = QLabel("of 1")
        toolbar_layout.addWidget(self.page_label)

        self.next_btn = QPushButton(">")
        self.next_btn.setFixedWidth(30)
        self.next_btn.setToolTip("Next page")
        self.next_btn.clicked.connect(self.next_page)
        toolbar_layout.addWidget(self.next_btn)

        toolbar_layout.addStretch()

        # Zoom controls
        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setFixedWidth(30)
        zoom_out_btn.setToolTip("Zoom out")
        zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar_layout.addWidget(zoom_out_btn)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(25)
        self.zoom_slider.setMaximum(400)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(100)
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        self.zoom_slider.setAccessibleName("Zoom level")
        toolbar_layout.addWidget(self.zoom_slider)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedWidth(30)
        zoom_in_btn.setToolTip("Zoom in")
        zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar_layout.addWidget(zoom_in_btn)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        toolbar_layout.addWidget(self.zoom_label)

        fit_btn = QPushButton("Fit")
        fit_btn.setToolTip("Fit to width")
        fit_btn.clicked.connect(self.fit_to_width)
        toolbar_layout.addWidget(fit_btn)

        layout.addWidget(toolbar)

        # Scroll area for page display
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLORS.BACKGROUND_ALT};
                border: none;
            }}
        """)

        # Page container
        self.page_container = QLabel()
        self.page_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_container.setStyleSheet("background-color: white;")
        self.page_container.setText("No document loaded")

        self.scroll_area.setWidget(self.page_container)
        layout.addWidget(self.scroll_area)

        # Apply button styles - dark theme with white text
        button_style = f"""
            QPushButton {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY_LIGHT};
                color: white;
            }}
            QPushButton:focus {{
                outline: 2px solid {COLORS.PRIMARY};
            }}
            QPushButton:disabled {{
                background-color: {COLORS.BACKGROUND_ALT};
                color: {COLORS.TEXT_DISABLED};
            }}
        """
        for btn in [self.prev_btn, self.next_btn, zoom_out_btn, zoom_in_btn, fit_btn]:
            btn.setStyleSheet(button_style)

        # Style the page label and other labels
        self.page_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 12pt;")
        self.zoom_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 12pt;")

        # Style the spin box
        self.page_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 4px;
                font-size: 12pt;
            }}
        """)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self.setAccessibleName("PDF Preview")
        self.setAccessibleDescription("Displays the current PDF page")
        self.scroll_area.setAccessibleName("Page view")

    def set_handler(self, handler: PDFHandler) -> None:
        """Set the PDF handler."""
        self._handler = handler

    def load_document(self, document: PDFDocument) -> None:
        """
        Load a PDF document for preview.

        Args:
            document: PDFDocument to display
        """
        self._document = document
        self._current_page = 1

        # Update page controls
        self.page_spin.setMaximum(document.page_count)
        self.page_label.setText(f"of {document.page_count}")

        # Update button states
        self._update_navigation_buttons()

        # Render first page
        self._render_current_page()

        logger.debug(f"Loaded document with {document.page_count} pages")

    def _render_current_page(self) -> None:
        """Render the current page."""
        if not self._handler or not self._document:
            return

        try:
            # Get page image
            image_bytes = self._handler.get_page_image(self._current_page, self._zoom)
            if not image_bytes:
                self.page_container.setText("Failed to render page")
                return

            # Convert to QPixmap
            image = QImage.fromData(image_bytes)
            pixmap = QPixmap.fromImage(image)

            self.page_container.setPixmap(pixmap)
            self.page_container.adjustSize()

        except Exception as e:
            logger.error(f"Failed to render page: {e}")
            self.page_container.setText("Error rendering page")

    def _update_navigation_buttons(self) -> None:
        """Update navigation button states."""
        if not self._document:
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return

        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < self._document.page_count)

    def _on_page_spin_changed(self, value: int) -> None:
        """Handle page spin box value change."""
        if value != self._current_page:
            self.go_to_page(value)

    def _on_zoom_slider_changed(self, value: int) -> None:
        """Handle zoom slider change."""
        zoom = value / 100.0
        self.set_zoom(zoom)

    def go_to_page(self, page: int) -> None:
        """
        Go to a specific page.

        Args:
            page: Page number (1-indexed)
        """
        if not self._document:
            return

        page = max(1, min(page, self._document.page_count))
        if page == self._current_page:
            return

        self._current_page = page
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(page)
        self.page_spin.blockSignals(False)

        self._update_navigation_buttons()
        self._render_current_page()
        self.page_changed.emit(page)

    def next_page(self) -> None:
        """Go to the next page."""
        if self._document and self._current_page < self._document.page_count:
            self.go_to_page(self._current_page + 1)

    def previous_page(self) -> None:
        """Go to the previous page."""
        if self._current_page > 1:
            self.go_to_page(self._current_page - 1)

    def set_zoom(self, zoom: float) -> None:
        """
        Set the zoom level.

        Args:
            zoom: Zoom factor (e.g., 1.0 = 100%)
        """
        zoom = max(self._min_zoom, min(zoom, self._max_zoom))
        if zoom == self._zoom:
            return

        self._zoom = zoom

        # Update slider
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(int(zoom * 100))
        self.zoom_slider.blockSignals(False)

        # Update label
        self.zoom_label.setText(f"{int(zoom * 100)}%")

        # Re-render
        self._render_current_page()
        self.zoom_changed.emit(zoom)

    def zoom_in(self) -> None:
        """Zoom in by 25%."""
        self.set_zoom(self._zoom + 0.25)

    def zoom_out(self) -> None:
        """Zoom out by 25%."""
        self.set_zoom(self._zoom - 0.25)

    def fit_to_width(self) -> None:
        """Fit the page to the scroll area width."""
        if not self._document:
            return

        # Get scroll area width
        available_width = self.scroll_area.viewport().width() - 40

        # Get page width at zoom 1.0
        page = self._document.pages[self._current_page - 1]
        page_width = page.width

        # Calculate zoom to fit
        zoom = available_width / page_width
        self.set_zoom(zoom)

    @property
    def current_page(self) -> int:
        """Get the current page number."""
        return self._current_page

    @property
    def zoom(self) -> float:
        """Get the current zoom level."""
        return self._zoom

    def clear(self) -> None:
        """Clear the preview."""
        self._document = None
        self._current_page = 1
        self.page_container.setPixmap(QPixmap())
        self.page_container.setText("No document loaded")
        self.page_spin.setMaximum(1)
        self.page_label.setText("of 1")
        self._update_navigation_buttons()
