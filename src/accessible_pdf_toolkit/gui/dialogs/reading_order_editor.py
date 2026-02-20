"""
Reading Order Editor dialog for viewing and reordering PDF page elements.
"""

from typing import List, Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QFrame,
    QWidget,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QBrush

from ...utils.constants import COLORS
from ...utils.logger import get_logger
from ...core.pdf_handler import PDFHandler, PDFDocument, PDFElement

logger = get_logger(__name__)


class _PagePreviewWidget(QLabel):
    """Widget that renders a PDF page image with numbered element overlays."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._base_pixmap: Optional[QPixmap] = None
        self._elements: List[PDFElement] = []
        self._zoom: float = 1.0
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_page_image(self, image_bytes: Optional[bytes]) -> None:
        if image_bytes:
            self._base_pixmap = QPixmap()
            self._base_pixmap.loadFromData(image_bytes)
        else:
            self._base_pixmap = None
        self._render()

    def set_elements(self, elements: List[PDFElement]) -> None:
        self._elements = elements
        self._render()

    def _render(self) -> None:
        if not self._base_pixmap:
            self.clear()
            self.setText("No page image available")
            return

        # Create a copy to paint on
        canvas = self._base_pixmap.copy()
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        circle_radius = 14
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)

        for idx, elem in enumerate(self._elements):
            bbox = elem.bbox
            # Center of the element bbox
            cx = (bbox[0] + bbox[2]) / 2 * self._zoom
            cy = (bbox[1] + bbox[3]) / 2 * self._zoom

            # Clamp to image bounds
            cx = max(circle_radius, min(cx, canvas.width() - circle_radius))
            cy = max(circle_radius, min(cy, canvas.height() - circle_radius))

            # Draw filled circle
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(COLORS.PRIMARY)))
            painter.drawEllipse(
                int(cx - circle_radius),
                int(cy - circle_radius),
                circle_radius * 2,
                circle_radius * 2,
            )

            # Draw number
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(
                int(cx - circle_radius),
                int(cy - circle_radius),
                circle_radius * 2,
                circle_radius * 2,
                Qt.AlignmentFlag.AlignCenter,
                str(idx + 1),
            )

        painter.end()
        self.setPixmap(canvas)
        self.setMinimumSize(QSize(canvas.width(), canvas.height()))


class ReadingOrderEditor(QDialog):
    """Dialog for viewing and reordering PDF page reading order."""

    order_changed = pyqtSignal(int, list)  # (page_number, reordered_elements_list)

    def __init__(
        self,
        handler: PDFHandler,
        document: PDFDocument,
        page_number: int = 1,
        parent=None,
    ):
        super().__init__(parent)
        self._handler = handler
        self._document = document
        self._page_num = page_number
        self._elements: List[PDFElement] = []

        self._setup_ui()
        self._load_page(self._page_num)

    def _setup_ui(self) -> None:
        self.setWindowTitle("Reading Order Editor - Accessible PDF Toolkit")
        self.setMinimumSize(900, 600)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS.BACKGROUND};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Main splitter: preview (left) | list (right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Left panel: page preview ---
        preview_frame = QFrame()
        preview_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.SURFACE};
                border: 1px solid {COLORS.BORDER};
                border-radius: 8px;
            }}
        """)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(8, 8, 8, 8)

        preview_title = QLabel("Page Preview")
        preview_title.setStyleSheet(
            f"color: {COLORS.TEXT_PRIMARY}; font-size: 13pt; font-weight: bold;"
        )
        preview_layout.addWidget(preview_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {COLORS.BACKGROUND_ALT};
            }}
        """)
        self._preview = _PagePreviewWidget()
        scroll.setWidget(self._preview)
        preview_layout.addWidget(scroll, 1)

        splitter.addWidget(preview_frame)

        # --- Right panel: reorderable element list ---
        list_frame = QFrame()
        list_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.SURFACE};
                border: 1px solid {COLORS.BORDER};
                border-radius: 8px;
            }}
        """)
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(12, 12, 12, 12)
        list_layout.setSpacing(8)

        list_title = QLabel("Element Order")
        list_title.setStyleSheet(
            f"color: {COLORS.TEXT_PRIMARY}; font-size: 13pt; font-weight: bold;"
        )
        list_layout.addWidget(list_title)

        self._list_widget = QListWidget()
        self._list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS.BACKGROUND_ALT};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                font-size: 11pt;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 6px 8px;
                border-bottom: 1px solid {COLORS.BORDER};
            }}
            QListWidget::item:selected {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}
            QListWidget::item:hover {{
                background-color: {COLORS.PRIMARY_LIGHT};
                color: white;
            }}
        """)
        self._list_widget.model().rowsMoved.connect(self._on_list_reordered)
        list_layout.addWidget(self._list_widget, 1)

        # Action buttons row
        actions_row = QHBoxLayout()

        move_up_btn = QPushButton("Move Up")
        move_up_btn.clicked.connect(self._on_move_up)
        actions_row.addWidget(move_up_btn)

        move_down_btn = QPushButton("Move Down")
        move_down_btn.clicked.connect(self._on_move_down)
        actions_row.addWidget(move_down_btn)

        auto_sort_btn = QPushButton("Auto-Sort")
        auto_sort_btn.setToolTip("Reset to visual order (top-to-bottom, column-by-column)")
        auto_sort_btn.clicked.connect(self._on_auto_sort)
        actions_row.addWidget(auto_sort_btn)

        for btn in [move_up_btn, move_down_btn, auto_sort_btn]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.SURFACE};
                    color: {COLORS.TEXT_PRIMARY};
                    border: 1px solid {COLORS.BORDER};
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 11pt;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.PRIMARY_LIGHT};
                    color: white;
                }}
            """)

        list_layout.addLayout(actions_row)

        # Apply / Cancel buttons
        bottom_btns = QHBoxLayout()
        bottom_btns.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 12pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.BACKGROUND_ALT};
            }}
        """)
        bottom_btns.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._on_apply)
        apply_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 12pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY_DARK};
            }}
        """)
        bottom_btns.addWidget(apply_btn)

        list_layout.addLayout(bottom_btns)

        splitter.addWidget(list_frame)
        splitter.setSizes([500, 400])
        layout.addWidget(splitter, 1)

        # --- Bottom bar: page navigation ---
        nav_bar = QHBoxLayout()
        nav_bar.addStretch()

        self._prev_page_btn = QPushButton("<")
        self._prev_page_btn.setFixedWidth(36)
        self._prev_page_btn.clicked.connect(self._on_prev_page)
        nav_bar.addWidget(self._prev_page_btn)

        self._page_label = QLabel()
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_label.setStyleSheet(
            f"color: {COLORS.TEXT_PRIMARY}; font-size: 12pt;"
        )
        nav_bar.addWidget(self._page_label)

        self._next_page_btn = QPushButton(">")
        self._next_page_btn.setFixedWidth(36)
        self._next_page_btn.clicked.connect(self._on_next_page)
        nav_bar.addWidget(self._next_page_btn)

        for btn in [self._prev_page_btn, self._next_page_btn]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.SURFACE};
                    color: {COLORS.TEXT_PRIMARY};
                    border: 1px solid {COLORS.BORDER};
                    border-radius: 4px;
                    font-size: 14pt;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.PRIMARY};
                    color: white;
                }}
                QPushButton:disabled {{
                    color: {COLORS.TEXT_DISABLED};
                }}
            """)

        nav_bar.addStretch()
        layout.addLayout(nav_bar)

    # ---- Data loading ----

    def _load_page(self, page_num: int) -> None:
        self._page_num = page_num
        page = self._document.pages[page_num - 1]
        self._elements = list(page.elements)  # working copy

        self._render_page_preview()
        self._populate_list()
        self._update_nav()

    def _render_page_preview(self) -> None:
        image_bytes = self._handler.get_page_image(self._page_num, zoom=1.0)
        self._preview.set_page_image(image_bytes)
        self._preview.set_elements(self._elements)

    def _populate_list(self) -> None:
        self._list_widget.clear()
        for idx, elem in enumerate(self._elements):
            text_preview = elem.text[:40].replace("\n", " ") if elem.text else ""
            label = f"#{idx + 1}  \"{text_preview}\"  ({elem.element_type})"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self._list_widget.addItem(item)

    def _update_numbers(self) -> None:
        """Refresh list item labels and preview overlay after any reorder."""
        # Rebuild _elements from list order
        new_elements: List[PDFElement] = []
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            orig_idx = item.data(Qt.ItemDataRole.UserRole)
            page = self._document.pages[self._page_num - 1]
            new_elements.append(page.elements[orig_idx])

        self._elements = new_elements

        # Update list labels
        for i in range(self._list_widget.count()):
            elem = self._elements[i]
            text_preview = elem.text[:40].replace("\n", " ") if elem.text else ""
            label = f"#{i + 1}  \"{text_preview}\"  ({elem.element_type})"
            self._list_widget.item(i).setText(label)

        # Update preview overlay
        self._preview.set_elements(self._elements)

    def _update_nav(self) -> None:
        total = self._document.page_count
        self._page_label.setText(f"Page {self._page_num} of {total}")
        self._prev_page_btn.setEnabled(self._page_num > 1)
        self._next_page_btn.setEnabled(self._page_num < total)

    # ---- Reorder actions ----

    def _on_move_up(self) -> None:
        row = self._list_widget.currentRow()
        if row <= 0:
            return
        item = self._list_widget.takeItem(row)
        self._list_widget.insertItem(row - 1, item)
        self._list_widget.setCurrentRow(row - 1)
        self._update_numbers()

    def _on_move_down(self) -> None:
        row = self._list_widget.currentRow()
        if row < 0 or row >= self._list_widget.count() - 1:
            return
        item = self._list_widget.takeItem(row)
        self._list_widget.insertItem(row + 1, item)
        self._list_widget.setCurrentRow(row + 1)
        self._update_numbers()

    def _on_auto_sort(self) -> None:
        """Sort elements by visual position: group by column, then top-to-bottom."""
        page = self._document.pages[self._page_num - 1]
        elements = list(page.elements)

        # Column clustering: group by left edge rounded to 50pt grid
        sorted_elements = sorted(
            elements,
            key=lambda e: (round(e.bbox[0] / 50), e.bbox[1]),
        )

        self._elements = sorted_elements

        # Rebuild list widget
        self._list_widget.clear()
        for idx, elem in enumerate(self._elements):
            text_preview = elem.text[:40].replace("\n", " ") if elem.text else ""
            label = f"#{idx + 1}  \"{text_preview}\"  ({elem.element_type})"
            item = QListWidgetItem(label)
            # Store the original index from page.elements
            orig_idx = page.elements.index(elem)
            item.setData(Qt.ItemDataRole.UserRole, orig_idx)
            self._list_widget.addItem(item)

        self._preview.set_elements(self._elements)

    def _on_list_reordered(self) -> None:
        self._update_numbers()

    # ---- Apply / Navigation ----

    def _on_apply(self) -> None:
        self.order_changed.emit(self._page_num, list(self._elements))
        self.accept()

    def _on_prev_page(self) -> None:
        if self._page_num > 1:
            self._load_page(self._page_num - 1)

    def _on_next_page(self) -> None:
        if self._page_num < self._document.page_count:
            self._load_page(self._page_num + 1)
