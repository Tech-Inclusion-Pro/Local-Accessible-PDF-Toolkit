"""
Enhanced PDF viewer with AI detection overlay support.
"""

from typing import Optional, List, Dict, Any, Tuple

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QLabel,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint, QSize
from PyQt6.QtGui import (
    QPixmap,
    QImage,
    QPainter,
    QColor,
    QPen,
    QBrush,
    QMouseEvent,
    QPaintEvent,
    QResizeEvent,
    QFont,
)

from ...utils.constants import COLORS, OVERLAY_COLORS
from ...utils.logger import get_logger
from ...core.pdf_handler import PDFHandler, PDFDocument

logger = get_logger(__name__)


class OverlayItem:
    """Represents an overlay on the PDF page."""

    def __init__(
        self,
        id: str,
        bbox: Tuple[float, float, float, float],
        color: Tuple[int, int, int, int],
        label: str = "",
        detection_type: str = "",
        data: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize an overlay item.

        Args:
            id: Unique identifier
            bbox: Bounding box (x0, y0, x1, y1) in PDF coordinates
            color: RGBA color tuple
            label: Label to display
            detection_type: Type of detection
            data: Additional data
        """
        self.id = id
        self.bbox = bbox
        self.color = color
        self.label = label
        self.detection_type = detection_type
        self.data = data or {}

    def get_scaled_rect(self, zoom: float, page_offset: QPoint = QPoint(0, 0)) -> QRect:
        """
        Get the scaled QRect for rendering.

        Args:
            zoom: Current zoom level
            page_offset: Offset of the page in the viewport

        Returns:
            QRect for the overlay
        """
        x0, y0, x1, y1 = self.bbox
        return QRect(
            int(x0 * zoom) + page_offset.x(),
            int(y0 * zoom) + page_offset.y(),
            int((x1 - x0) * zoom),
            int((y1 - y0) * zoom),
        )


class PDFPageWidget(QLabel):
    """Widget that displays a PDF page with overlays."""

    overlay_clicked = pyqtSignal(object)
    overlay_hovered = pyqtSignal(object)
    overlay_left = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._overlays: List[OverlayItem] = []
        self._zoom = 1.0
        self._hovered_overlay: Optional[OverlayItem] = None
        self._selected_overlay: Optional[OverlayItem] = None

        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_overlays(self, overlays: List[OverlayItem]) -> None:
        """Set the overlays to display."""
        self._overlays = overlays
        self.update()

    def add_overlay(self, overlay: OverlayItem) -> None:
        """Add an overlay."""
        self._overlays.append(overlay)
        self.update()

    def remove_overlay(self, overlay_id: str) -> None:
        """Remove an overlay by ID."""
        self._overlays = [o for o in self._overlays if o.id != overlay_id]
        self.update()

    def clear_overlays(self) -> None:
        """Clear all overlays."""
        self._overlays.clear()
        self.update()

    def set_zoom(self, zoom: float) -> None:
        """Set the zoom level for overlay scaling."""
        self._zoom = zoom
        self.update()

    def set_selected_overlay(self, overlay_id: Optional[str]) -> None:
        """Set the selected overlay."""
        self._selected_overlay = None
        if overlay_id:
            for overlay in self._overlays:
                if overlay.id == overlay_id:
                    self._selected_overlay = overlay
                    break
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the page and overlays."""
        super().paintEvent(event)

        if not self._overlays:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate page offset (centering)
        pixmap = self.pixmap()
        if pixmap:
            page_offset = QPoint(
                (self.width() - pixmap.width()) // 2,
                (self.height() - pixmap.height()) // 2,
            )
        else:
            page_offset = QPoint(0, 0)

        # Draw overlays
        for overlay in self._overlays:
            rect = overlay.get_scaled_rect(self._zoom, page_offset)

            # Fill color
            color = QColor(*overlay.color)
            painter.fillRect(rect, QBrush(color))

            # Border
            is_selected = self._selected_overlay and self._selected_overlay.id == overlay.id
            is_hovered = self._hovered_overlay and self._hovered_overlay.id == overlay.id

            if is_selected:
                pen = QPen(QColor(255, 255, 255), 3)
            elif is_hovered:
                pen = QPen(QColor(*overlay.color[:3]), 2)
            else:
                pen = QPen(QColor(*overlay.color[:3], 180), 1)

            painter.setPen(pen)
            painter.drawRect(rect)

            # Label (if visible and room)
            if overlay.label and rect.height() > 20:
                painter.setPen(QPen(QColor(255, 255, 255)))
                font = painter.font()
                font.setPointSize(9)
                font.setBold(True)
                painter.setFont(font)

                text_rect = rect.adjusted(4, 2, -4, -2)
                painter.drawText(
                    text_rect,
                    Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                    overlay.label[:20],
                )

        painter.end()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move for hover detection."""
        pos = event.position().toPoint()

        # Calculate page offset
        pixmap = self.pixmap()
        if pixmap:
            page_offset = QPoint(
                (self.width() - pixmap.width()) // 2,
                (self.height() - pixmap.height()) // 2,
            )
        else:
            page_offset = QPoint(0, 0)

        # Check if hovering over any overlay
        hovered = None
        for overlay in self._overlays:
            rect = overlay.get_scaled_rect(self._zoom, page_offset)
            if rect.contains(pos):
                hovered = overlay
                break

        if hovered != self._hovered_overlay:
            self._hovered_overlay = hovered
            self.update()

            if hovered:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
                self.overlay_hovered.emit(hovered)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self.overlay_left.emit()

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse click on overlays."""
        if event.button() == Qt.MouseButton.LeftButton and self._hovered_overlay:
            self._selected_overlay = self._hovered_overlay
            self.update()
            self.overlay_clicked.emit(self._hovered_overlay)

        super().mousePressEvent(event)


class EnhancedPDFViewer(QWidget):
    """Enhanced PDF viewer with overlay support."""

    # Signals
    page_changed = pyqtSignal(int)
    overlay_clicked = pyqtSignal(dict)
    overlay_hovered = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._handler: Optional[PDFHandler] = None
        self._document: Optional[PDFDocument] = None
        self._current_page = 1
        self._zoom = 1.0
        self._overlays_by_page: Dict[int, List[OverlayItem]] = {}

        self._setup_ui()
        self._setup_accessibility()
        self._apply_styles()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area for page display
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Page widget
        self._page_widget = PDFPageWidget()
        self._page_widget.overlay_clicked.connect(self._on_overlay_clicked)
        self._page_widget.overlay_hovered.connect(self._on_overlay_hovered)

        self._scroll_area.setWidget(self._page_widget)
        layout.addWidget(self._scroll_area)

        # No document message
        self._page_widget.setText("No document loaded")

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self.setAccessibleName("PDF Viewer")
        self.setAccessibleDescription("Displays PDF page with accessibility detection overlays")

    def _apply_styles(self) -> None:
        """Apply widget styles."""
        self._scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLORS.BACKGROUND_ALT};
                border: none;
            }}
        """)

        self._page_widget.setStyleSheet(f"""
            QLabel {{
                background-color: white;
            }}
        """)

    def set_handler(self, handler: PDFHandler) -> None:
        """Set the PDF handler."""
        self._handler = handler

    def load_document(self, document: PDFDocument) -> None:
        """
        Load a document for viewing.

        Args:
            document: PDFDocument to display
        """
        self._document = document
        self._current_page = 1
        self._overlays_by_page.clear()

        self._render_current_page()

    def _render_current_page(self) -> None:
        """Render the current page."""
        if not self._handler or not self._document:
            self._page_widget.setText("No document loaded")
            return

        try:
            image_bytes = self._handler.get_page_image(self._current_page, self._zoom)
            if not image_bytes:
                self._page_widget.setText("Failed to render page")
                return

            image = QImage.fromData(image_bytes)
            pixmap = QPixmap.fromImage(image)

            self._page_widget.setPixmap(pixmap)
            self._page_widget.set_zoom(self._zoom)

            # Apply overlays for current page
            overlays = self._overlays_by_page.get(self._current_page, [])
            self._page_widget.set_overlays(overlays)

            self._page_widget.adjustSize()

        except Exception as e:
            logger.error(f"Failed to render page: {e}")
            self._page_widget.setText("Error rendering page")

    def go_to_page(self, page: int) -> None:
        """
        Navigate to a specific page.

        Args:
            page: Page number (1-indexed)
        """
        if not self._document:
            return

        page = max(1, min(page, self._document.page_count))
        if page == self._current_page:
            return

        self._current_page = page
        self._render_current_page()
        self.page_changed.emit(page)

    def set_zoom(self, zoom: float) -> None:
        """
        Set the zoom level.

        Args:
            zoom: Zoom factor (e.g., 1.0 = 100%)
        """
        if zoom == -1:
            # Fit to width
            self._fit_to_width()
            return
        elif zoom == -2:
            # Fit to page
            self._fit_to_page()
            return

        zoom = max(0.25, min(zoom, 4.0))
        if zoom == self._zoom:
            return

        self._zoom = zoom
        self._render_current_page()

    def _fit_to_width(self) -> None:
        """Fit the page to the viewport width."""
        if not self._document:
            return

        available_width = self._scroll_area.viewport().width() - 40
        page = self._document.pages[self._current_page - 1]
        self._zoom = available_width / page.width
        self._render_current_page()

    def _fit_to_page(self) -> None:
        """Fit the whole page in the viewport."""
        if not self._document:
            return

        viewport = self._scroll_area.viewport()
        available_width = viewport.width() - 40
        available_height = viewport.height() - 40

        page = self._document.pages[self._current_page - 1]

        zoom_w = available_width / page.width
        zoom_h = available_height / page.height

        self._zoom = min(zoom_w, zoom_h)
        self._render_current_page()

    def add_overlays(self, page: int, overlays: List[Dict[str, Any]]) -> None:
        """
        Add overlays for a specific page.

        Args:
            page: Page number (1-indexed)
            overlays: List of overlay definitions
        """
        if page not in self._overlays_by_page:
            self._overlays_by_page[page] = []

        for overlay_data in overlays:
            overlay = OverlayItem(
                id=overlay_data["id"],
                bbox=overlay_data["bbox"],
                color=overlay_data.get("color", OVERLAY_COLORS.get("issue", (239, 68, 68, 102))),
                label=overlay_data.get("label", ""),
                detection_type=overlay_data.get("detection_type", ""),
                data=overlay_data.get("data", {}),
            )
            self._overlays_by_page[page].append(overlay)

        if page == self._current_page:
            self._page_widget.set_overlays(self._overlays_by_page[page])

    def add_overlay_from_detection(self, detection: Any) -> None:
        """
        Add an overlay from a Detection object.

        Args:
            detection: Detection object with bbox, type, etc.
        """
        page = detection.page_number

        if page not in self._overlays_by_page:
            self._overlays_by_page[page] = []

        overlay = OverlayItem(
            id=detection.id,
            bbox=detection.bbox,
            color=detection.overlay_color,
            label=detection.detection_type.value.title(),
            detection_type=detection.detection_type.value,
            data=detection.to_dict(),
        )
        self._overlays_by_page[page].append(overlay)

        if page == self._current_page:
            self._page_widget.set_overlays(self._overlays_by_page[page])

    def clear_overlays(self, page: Optional[int] = None) -> None:
        """
        Clear overlays.

        Args:
            page: Specific page to clear, or None for all
        """
        if page is None:
            self._overlays_by_page.clear()
        elif page in self._overlays_by_page:
            del self._overlays_by_page[page]

        if page is None or page == self._current_page:
            self._page_widget.clear_overlays()

    def highlight_overlay(self, overlay_id: str) -> None:
        """
        Highlight a specific overlay.

        Args:
            overlay_id: ID of the overlay to highlight
        """
        self._page_widget.set_selected_overlay(overlay_id)

    def update_overlay_status(self, overlay_id: str, status: str) -> None:
        """
        Update the status/color of an overlay.

        Args:
            overlay_id: ID of the overlay to update
            status: New status ('applied', 'skipped', etc.)
        """
        # Define colors for different statuses
        status_colors = {
            "applied": (34, 197, 94, 150),    # Green - success
            "skipped": (156, 163, 175, 100),  # Gray - skipped
            "error": (239, 68, 68, 150),      # Red - error
        }

        new_color = status_colors.get(status)
        if not new_color:
            return

        # Update the overlay color in all pages
        for page_overlays in self._overlays_by_page.values():
            for overlay in page_overlays:
                if overlay.id == overlay_id:
                    overlay.color = new_color
                    break

        # Refresh current page if overlay is on it
        if self._current_page in self._overlays_by_page:
            self._page_widget.set_overlays(self._overlays_by_page[self._current_page])

    def _on_overlay_clicked(self, overlay: OverlayItem) -> None:
        """Handle overlay click."""
        self.overlay_clicked.emit(overlay.data)

    def _on_overlay_hovered(self, overlay: OverlayItem) -> None:
        """Handle overlay hover."""
        self.overlay_hovered.emit(overlay.data)

    @property
    def current_page(self) -> int:
        """Get current page number."""
        return self._current_page

    @property
    def zoom(self) -> float:
        """Get current zoom level."""
        return self._zoom

    def clear(self) -> None:
        """Clear the viewer."""
        self._document = None
        self._current_page = 1
        self._overlays_by_page.clear()
        self._page_widget.setPixmap(QPixmap())
        self._page_widget.setText("No document loaded")
        self._page_widget.clear_overlays()
