"""
Navigation panel for PDF viewer with thumbnails, zoom, outline, and search.
"""

from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QLineEdit,
    QComboBox,
    QSlider,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QPixmap, QImage, QIcon

from ...utils.constants import COLORS
from ...utils.logger import get_logger
from ...core.pdf_handler import PDFHandler, PDFDocument

logger = get_logger(__name__)


class ThumbnailListWidget(QListWidget):
    """Custom list widget for page thumbnails."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(100, 130))
        self.setSpacing(4)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setWrapping(False)
        self.setFlow(QListWidget.Flow.TopToBottom)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)


class NavigationPanel(QWidget):
    """Left panel with thumbnails, navigation, zoom, outline, search."""

    # Signals
    page_requested = pyqtSignal(int)
    zoom_changed = pyqtSignal(float)
    search_requested = pyqtSignal(str)
    search_result_selected = pyqtSignal(dict)

    # Zoom presets
    ZOOM_PRESETS = [
        ("50%", 0.5),
        ("75%", 0.75),
        ("100%", 1.0),
        ("125%", 1.25),
        ("150%", 1.5),
        ("200%", 2.0),
        ("Fit Width", -1),
        ("Fit Page", -2),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self._handler: Optional[PDFHandler] = None
        self._document: Optional[PDFDocument] = None
        self._current_page = 1
        self._current_zoom = 1.0
        self._search_results: List[Dict[str, Any]] = []
        self._thumbnail_cache: Dict[int, QPixmap] = {}

        self._setup_ui()
        self._setup_accessibility()
        self._apply_styles()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Page Navigation Controls
        nav_frame = QFrame()
        nav_frame.setObjectName("navFrame")
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(8)

        # Page number row
        page_row = QHBoxLayout()

        self._first_btn = QPushButton("<<")
        self._first_btn.setFixedWidth(32)
        self._first_btn.setToolTip("First page")
        self._first_btn.clicked.connect(lambda: self.page_requested.emit(1))
        page_row.addWidget(self._first_btn)

        self._prev_btn = QPushButton("<")
        self._prev_btn.setFixedWidth(32)
        self._prev_btn.setToolTip("Previous page")
        self._prev_btn.clicked.connect(self._go_previous)
        page_row.addWidget(self._prev_btn)

        page_row.addWidget(QLabel("Page"))

        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(1)
        self._page_spin.setMaximum(1)
        self._page_spin.valueChanged.connect(self._on_page_changed)
        page_row.addWidget(self._page_spin)

        self._page_count_label = QLabel("of 1")
        page_row.addWidget(self._page_count_label)

        self._next_btn = QPushButton(">")
        self._next_btn.setFixedWidth(32)
        self._next_btn.setToolTip("Next page")
        self._next_btn.clicked.connect(self._go_next)
        page_row.addWidget(self._next_btn)

        self._last_btn = QPushButton(">>")
        self._last_btn.setFixedWidth(32)
        self._last_btn.setToolTip("Last page")
        self._last_btn.clicked.connect(self._go_last)
        page_row.addWidget(self._last_btn)

        nav_layout.addLayout(page_row)

        # Zoom controls
        zoom_row = QHBoxLayout()

        zoom_row.addWidget(QLabel("Zoom:"))

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setMinimum(50)
        self._zoom_slider.setMaximum(200)
        self._zoom_slider.setValue(100)
        self._zoom_slider.setTickInterval(25)
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        zoom_row.addWidget(self._zoom_slider)

        self._zoom_combo = QComboBox()
        for label, value in self.ZOOM_PRESETS:
            self._zoom_combo.addItem(label, value)
        self._zoom_combo.setCurrentIndex(2)  # 100%
        self._zoom_combo.currentIndexChanged.connect(self._on_zoom_preset_changed)
        zoom_row.addWidget(self._zoom_combo)

        nav_layout.addLayout(zoom_row)

        layout.addWidget(nav_frame)

        # Tab widget for thumbnails, outline, search
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)

        # Thumbnails tab
        thumbnails_widget = QWidget()
        thumbnails_layout = QVBoxLayout(thumbnails_widget)
        thumbnails_layout.setContentsMargins(4, 4, 4, 4)

        self._thumbnail_list = ThumbnailListWidget()
        self._thumbnail_list.itemClicked.connect(self._on_thumbnail_clicked)
        thumbnails_layout.addWidget(self._thumbnail_list)

        self._tabs.addTab(thumbnails_widget, "Pages")

        # Outline tab
        outline_widget = QWidget()
        outline_layout = QVBoxLayout(outline_widget)
        outline_layout.setContentsMargins(4, 4, 4, 4)

        self._outline_tree = QTreeWidget()
        self._outline_tree.setHeaderHidden(True)
        self._outline_tree.itemClicked.connect(self._on_outline_clicked)
        outline_layout.addWidget(self._outline_tree)

        self._no_outline_label = QLabel("No bookmarks in this document")
        self._no_outline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_outline_label.setWordWrap(True)
        outline_layout.addWidget(self._no_outline_label)

        self._tabs.addTab(outline_widget, "Outline")

        # Search tab
        search_widget = QWidget()
        search_layout = QVBoxLayout(search_widget)
        search_layout.setContentsMargins(4, 4, 4, 4)

        search_input_row = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search in document...")
        self._search_input.returnPressed.connect(self._on_search)
        search_input_row.addWidget(self._search_input)

        self._search_btn = QPushButton("Find")
        self._search_btn.clicked.connect(self._on_search)
        search_input_row.addWidget(self._search_btn)

        search_layout.addLayout(search_input_row)

        self._search_results_label = QLabel("")
        search_layout.addWidget(self._search_results_label)

        self._search_results_list = QListWidget()
        self._search_results_list.itemClicked.connect(self._on_search_result_clicked)
        search_layout.addWidget(self._search_results_list)

        self._tabs.addTab(search_widget, "Search")

        layout.addWidget(self._tabs, 1)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self.setAccessibleName("Navigation Panel")
        self.setAccessibleDescription("Navigate pages, zoom, and search the document")

        self._page_spin.setAccessibleName("Current page number")
        self._zoom_slider.setAccessibleName("Zoom level slider")
        self._zoom_combo.setAccessibleName("Zoom presets")
        self._thumbnail_list.setAccessibleName("Page thumbnails")
        self._outline_tree.setAccessibleName("Document outline")
        self._search_input.setAccessibleName("Search text")
        self._search_results_list.setAccessibleName("Search results")

    def _apply_styles(self) -> None:
        """Apply widget styles."""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
            }}

            #navFrame {{
                background-color: {COLORS.SURFACE};
                border-bottom: 1px solid {COLORS.BORDER};
            }}

            QPushButton {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11pt;
            }}

            QPushButton:hover {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}

            QPushButton:disabled {{
                background-color: {COLORS.BACKGROUND_ALT};
                color: {COLORS.TEXT_DISABLED};
            }}

            QSpinBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 4px;
                font-size: 11pt;
            }}

            QComboBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 4px;
                font-size: 11pt;
            }}

            QComboBox QAbstractItemView {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                selection-background-color: {COLORS.PRIMARY};
            }}

            QLineEdit {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 6px;
                font-size: 11pt;
            }}

            QListWidget {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
                border: none;
            }}

            QListWidget::item {{
                padding: 4px;
                border-radius: 4px;
            }}

            QListWidget::item:selected {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}

            QListWidget::item:hover {{
                background-color: {COLORS.BACKGROUND_ALT};
            }}

            QTreeWidget {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
                border: none;
            }}

            QTreeWidget::item {{
                padding: 4px;
            }}

            QTreeWidget::item:selected {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}

            QTabWidget::pane {{
                border: none;
                background-color: {COLORS.BACKGROUND};
            }}

            QTabBar::tab {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                padding: 6px 12px;
                border: 1px solid {COLORS.BORDER};
                border-bottom: none;
                border-radius: 4px 4px 0 0;
                font-size: 10pt;
            }}

            QTabBar::tab:selected {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}

            QLabel {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 11pt;
            }}

            QSlider::groove:horizontal {{
                border: 1px solid {COLORS.BORDER};
                height: 6px;
                background: {COLORS.INPUT_BG};
                border-radius: 3px;
            }}

            QSlider::handle:horizontal {{
                background: {COLORS.PRIMARY};
                border: none;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
        """)

    def set_handler(self, handler: PDFHandler) -> None:
        """Set the PDF handler."""
        self._handler = handler

    def load_document(self, document: PDFDocument) -> None:
        """
        Load a document into the navigation panel.

        Args:
            document: PDFDocument to display
        """
        self._document = document
        self._current_page = 1
        self._thumbnail_cache.clear()

        # Update page controls
        self._page_spin.setMaximum(document.page_count)
        self._page_spin.setValue(1)
        self._page_count_label.setText(f"of {document.page_count}")
        self._update_nav_buttons()

        # Load thumbnails
        self._load_thumbnails()

        # Load outline
        self._load_outline()

        # Clear search
        self._search_input.clear()
        self._search_results_list.clear()
        self._search_results_label.setText("")

    def _load_thumbnails(self) -> None:
        """Load page thumbnails."""
        self._thumbnail_list.clear()

        if not self._handler or not self._document:
            return

        for page_num in range(1, self._document.page_count + 1):
            item = QListWidgetItem()
            item.setText(f"Page {page_num}")
            item.setData(Qt.ItemDataRole.UserRole, page_num)
            item.setSizeHint(QSize(110, 150))

            # Load thumbnail asynchronously would be better, but for now sync
            thumbnail_bytes = self._handler.get_thumbnail(page_num, 100, 130)
            if thumbnail_bytes:
                image = QImage.fromData(thumbnail_bytes)
                pixmap = QPixmap.fromImage(image)
                item.setIcon(QIcon(pixmap))
                self._thumbnail_cache[page_num] = pixmap

            self._thumbnail_list.addItem(item)

        # Select first page
        if self._thumbnail_list.count() > 0:
            self._thumbnail_list.setCurrentRow(0)

    def _load_outline(self) -> None:
        """Load document outline/bookmarks."""
        self._outline_tree.clear()

        if not self._handler:
            self._no_outline_label.show()
            self._outline_tree.hide()
            return

        outline = self._handler.get_outline()

        if not outline:
            self._no_outline_label.show()
            self._outline_tree.hide()
            return

        self._no_outline_label.hide()
        self._outline_tree.show()

        # Build tree structure
        parent_stack = [(0, self._outline_tree.invisibleRootItem())]

        for item in outline:
            level = item["level"]
            title = item["title"]
            page = item["page"]

            # Find appropriate parent
            while parent_stack and parent_stack[-1][0] >= level:
                parent_stack.pop()

            parent = parent_stack[-1][1] if parent_stack else self._outline_tree.invisibleRootItem()

            tree_item = QTreeWidgetItem(parent, [title])
            tree_item.setData(0, Qt.ItemDataRole.UserRole, page)

            parent_stack.append((level, tree_item))

        self._outline_tree.expandAll()

    def _on_page_changed(self, page: int) -> None:
        """Handle page spin box change."""
        if page != self._current_page:
            self._current_page = page
            self._update_nav_buttons()
            self._update_thumbnail_selection()
            self.page_requested.emit(page)

    def _go_previous(self) -> None:
        """Go to previous page."""
        if self._current_page > 1:
            self._page_spin.setValue(self._current_page - 1)

    def _go_next(self) -> None:
        """Go to next page."""
        if self._document and self._current_page < self._document.page_count:
            self._page_spin.setValue(self._current_page + 1)

    def _go_last(self) -> None:
        """Go to last page."""
        if self._document:
            self._page_spin.setValue(self._document.page_count)

    def _update_nav_buttons(self) -> None:
        """Update navigation button states."""
        if not self._document:
            self._first_btn.setEnabled(False)
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)
            self._last_btn.setEnabled(False)
            return

        self._first_btn.setEnabled(self._current_page > 1)
        self._prev_btn.setEnabled(self._current_page > 1)
        self._next_btn.setEnabled(self._current_page < self._document.page_count)
        self._last_btn.setEnabled(self._current_page < self._document.page_count)

    def _update_thumbnail_selection(self) -> None:
        """Update thumbnail selection to match current page."""
        if self._current_page > 0 and self._current_page <= self._thumbnail_list.count():
            self._thumbnail_list.setCurrentRow(self._current_page - 1)

    def _on_thumbnail_clicked(self, item: QListWidgetItem) -> None:
        """Handle thumbnail click."""
        page = item.data(Qt.ItemDataRole.UserRole)
        if page:
            self._page_spin.setValue(page)

    def _on_outline_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle outline item click."""
        page = item.data(0, Qt.ItemDataRole.UserRole)
        if page:
            self._page_spin.setValue(int(page))

    def _on_zoom_slider_changed(self, value: int) -> None:
        """Handle zoom slider change."""
        zoom = value / 100.0
        self._current_zoom = zoom
        self.zoom_changed.emit(zoom)

        # Update combo box to show custom value
        self._zoom_combo.blockSignals(True)
        self._zoom_combo.setCurrentIndex(-1)
        self._zoom_combo.setEditText(f"{value}%")
        self._zoom_combo.blockSignals(False)

    def _on_zoom_preset_changed(self, index: int) -> None:
        """Handle zoom preset selection."""
        if index < 0:
            return

        value = self._zoom_combo.currentData()
        if value == -1:
            # Fit width - signal special value
            self.zoom_changed.emit(-1)
        elif value == -2:
            # Fit page - signal special value
            self.zoom_changed.emit(-2)
        elif value:
            self._current_zoom = value
            self._zoom_slider.blockSignals(True)
            self._zoom_slider.setValue(int(value * 100))
            self._zoom_slider.blockSignals(False)
            self.zoom_changed.emit(value)

    def _on_search(self) -> None:
        """Handle search request."""
        query = self._search_input.text().strip()
        if not query or not self._handler:
            return

        self._search_results_list.clear()
        self._search_results = self._handler.search_text(query)

        if not self._search_results:
            self._search_results_label.setText("No results found")
            return

        self._search_results_label.setText(f"Found {len(self._search_results)} results")

        for result in self._search_results:
            item = QListWidgetItem()
            item.setText(f"Page {result['page']}: {result['context'][:50]}...")
            item.setData(Qt.ItemDataRole.UserRole, result)
            self._search_results_list.addItem(item)

        self.search_requested.emit(query)

    def _on_search_result_clicked(self, item: QListWidgetItem) -> None:
        """Handle search result click."""
        result = item.data(Qt.ItemDataRole.UserRole)
        if result:
            self._page_spin.setValue(result["page"])
            self.search_result_selected.emit(result)

    def set_current_page(self, page: int) -> None:
        """
        Set the current page (external call).

        Args:
            page: Page number (1-indexed)
        """
        self._page_spin.blockSignals(True)
        self._page_spin.setValue(page)
        self._page_spin.blockSignals(False)
        self._current_page = page
        self._update_nav_buttons()
        self._update_thumbnail_selection()

    def set_zoom(self, zoom: float) -> None:
        """
        Set the zoom level (external call).

        Args:
            zoom: Zoom factor
        """
        self._current_zoom = zoom
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(int(zoom * 100))
        self._zoom_slider.blockSignals(False)

    @property
    def current_page(self) -> int:
        """Get current page number."""
        return self._current_page

    @property
    def current_zoom(self) -> float:
        """Get current zoom level."""
        return self._current_zoom
