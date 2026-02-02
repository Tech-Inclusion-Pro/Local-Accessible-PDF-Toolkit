"""
Tag tree widget for displaying and editing PDF structure tags.
"""

from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QComboBox,
    QLineEdit,
    QLabel,
    QMenu,
    QMessageBox,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor

from ...utils.constants import COLORS, TagType
from ...utils.logger import get_logger
from ...core.pdf_handler import PDFDocument, PDFElement

logger = get_logger(__name__)


class TagTreeItem(QTreeWidgetItem):
    """Custom tree item for PDF tags."""

    def __init__(self, element: PDFElement, parent=None):
        super().__init__(parent)
        self.element = element
        self._setup_display()

    def _setup_display(self) -> None:
        """Set up the item display."""
        # Tag type
        tag_text = self.element.tag.value if self.element.tag else "Untagged"
        self.setText(0, tag_text)

        # Content preview
        content = self.element.text[:50] + "..." if len(self.element.text) > 50 else self.element.text
        self.setText(1, content)

        # Page number
        self.setText(2, str(self.element.page_number))

        # Set color based on tag status
        if not self.element.tag:
            self.setForeground(0, QColor(COLORS.ERROR))
        elif self.element.tag in [TagType.FIGURE] and not self.element.alt_text:
            self.setForeground(0, QColor(COLORS.WARNING))
        else:
            self.setForeground(0, QColor(COLORS.SUCCESS))

    def update_tag(self, tag_type: TagType) -> None:
        """Update the element's tag."""
        self.element.tag = tag_type
        self._setup_display()


class TagTreeWidget(QWidget):
    """Widget for displaying and editing PDF structure tags."""

    # Signals
    tag_selected = pyqtSignal(object)  # PDFElement
    tag_changed = pyqtSignal(object, object)  # element, new_tag
    tag_deleted = pyqtSignal(object)  # element

    def __init__(self, parent=None):
        super().__init__(parent)

        self._document: Optional[PDFDocument] = None
        self._items: Dict[int, TagTreeItem] = {}

        self._setup_ui()
        self._setup_accessibility()

    def _setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

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

        # Filter
        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 12pt;")
        toolbar_layout.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All", None)
        self.filter_combo.addItem("Untagged", "untagged")
        self.filter_combo.addItem("Headings", "headings")
        self.filter_combo.addItem("Images", "images")
        self.filter_combo.addItem("Tables", "tables")
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        self.filter_combo.setAccessibleName("Filter tags")
        self.filter_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 6px;
                font-size: 12pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                selection-background-color: {COLORS.PRIMARY};
            }}
        """)
        toolbar_layout.addWidget(self.filter_combo)

        toolbar_layout.addStretch()

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.setAccessibleName("Search tags")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 6px;
                font-size: 12pt;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS.INPUT_FOCUS};
            }}
            QLineEdit::placeholder {{
                color: {COLORS.TEXT_SECONDARY};
            }}
        """)
        toolbar_layout.addWidget(self.search_input)

        layout.addWidget(toolbar)

        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Tag", "Content", "Page"])
        self.tree.setColumnWidth(0, 100)
        self.tree.setColumnWidth(1, 250)
        self.tree.setColumnWidth(2, 50)

        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)

        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                font-size: 12pt;
            }}
            QTreeWidget::item {{
                padding: 4px;
                color: {COLORS.TEXT_PRIMARY};
            }}
            QTreeWidget::item:selected {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}
            QTreeWidget::item:hover {{
                background-color: {COLORS.PRIMARY_LIGHT};
            }}
            QHeaderView::section {{
                background-color: {COLORS.BACKGROUND_ALT};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                padding: 4px;
                font-size: 12pt;
            }}
        """)

        layout.addWidget(self.tree)

        # Tag editor panel
        self.editor_frame = QFrame()
        self.editor_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND_ALT};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 8px;
            }}
            QLabel {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}
        """)
        editor_layout = QVBoxLayout(self.editor_frame)

        # Tag type selector
        tag_row = QHBoxLayout()
        tag_label = QLabel("Tag Type:")
        tag_row.addWidget(tag_label)

        self.tag_combo = QComboBox()
        for tag_type in TagType:
            self.tag_combo.addItem(tag_type.value, tag_type)
        self.tag_combo.setAccessibleName("Select tag type")
        self.tag_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 6px;
                font-size: 12pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                selection-background-color: {COLORS.PRIMARY};
            }}
        """)
        tag_row.addWidget(self.tag_combo)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply_tag)
        apply_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY_DARK};
            }}
        """)
        tag_row.addWidget(apply_btn)

        editor_layout.addLayout(tag_row)

        # Alt text input (for images)
        alt_row = QHBoxLayout()
        alt_label = QLabel("Alt Text:")
        alt_row.addWidget(alt_label)

        self.alt_input = QLineEdit()
        self.alt_input.setPlaceholderText("Enter alt text for images...")
        self.alt_input.setAccessibleName("Alt text")
        self.alt_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 6px;
                font-size: 12pt;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS.INPUT_FOCUS};
            }}
        """)
        alt_row.addWidget(self.alt_input)

        editor_layout.addLayout(alt_row)

        # Hide editor initially
        self.editor_frame.hide()
        layout.addWidget(self.editor_frame)

        # Stats bar
        self.stats_label = QLabel("No document loaded")
        self.stats_label.setStyleSheet(f"""
            color: {COLORS.TEXT_SECONDARY};
            padding: 4px;
            font-size: 12pt;
        """)
        layout.addWidget(self.stats_label)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self.setAccessibleName("Tag tree")
        self.setAccessibleDescription("View and edit PDF structure tags")
        self.tree.setAccessibleName("Document structure tree")

    def load_document(self, document: PDFDocument) -> None:
        """
        Load a document's structure into the tree.

        Args:
            document: PDFDocument to display
        """
        self._document = document
        self.tree.clear()
        self._items.clear()

        # Add elements
        untagged_count = 0
        for page in document.pages:
            for i, element in enumerate(page.elements):
                item = TagTreeItem(element)
                self.tree.addTopLevelItem(item)
                self._items[id(element)] = item

                if not element.tag:
                    untagged_count += 1

        # Update stats
        total = sum(len(p.elements) for p in document.pages)
        self.stats_label.setText(
            f"Total elements: {total} | Untagged: {untagged_count}"
        )

        logger.debug(f"Loaded {total} elements into tag tree")

    def _apply_filter(self) -> None:
        """Apply the selected filter."""
        filter_type = self.filter_combo.currentData()

        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if not isinstance(item, TagTreeItem):
                continue

            visible = True
            element = item.element

            if filter_type == "untagged":
                visible = element.tag is None
            elif filter_type == "headings":
                visible = element.tag and element.tag.value.startswith("H")
            elif filter_type == "images":
                visible = element.tag == TagType.FIGURE
            elif filter_type == "tables":
                visible = element.tag in [TagType.TABLE, TagType.TABLE_ROW, TagType.TABLE_HEADER, TagType.TABLE_DATA]

            item.setHidden(not visible)

    def _on_search(self, text: str) -> None:
        """Handle search input."""
        text = text.lower()

        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if not isinstance(item, TagTreeItem):
                continue

            visible = not text or text in item.element.text.lower()
            item.setHidden(not visible)

    def _on_selection_changed(self) -> None:
        """Handle selection change."""
        items = self.tree.selectedItems()
        if items and isinstance(items[0], TagTreeItem):
            element = items[0].element
            self.editor_frame.show()

            # Set current tag in combo
            if element.tag:
                index = self.tag_combo.findData(element.tag)
                if index >= 0:
                    self.tag_combo.setCurrentIndex(index)

            # Set alt text
            self.alt_input.setText(element.alt_text or "")

            self.tag_selected.emit(element)
        else:
            self.editor_frame.hide()

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle double-click on item."""
        if isinstance(item, TagTreeItem):
            self.tag_selected.emit(item.element)

    def _show_context_menu(self, pos) -> None:
        """Show context menu for tree items."""
        item = self.tree.itemAt(pos)
        if not isinstance(item, TagTreeItem):
            return

        menu = QMenu(self)

        # Tag submenu
        tag_menu = menu.addMenu("Set Tag")
        for tag_type in TagType:
            action = tag_menu.addAction(tag_type.value)
            action.setData(tag_type)
            action.triggered.connect(lambda checked, t=tag_type: self._set_tag(item, t))

        menu.addSeparator()

        # Delete tag
        delete_action = menu.addAction("Remove Tag")
        delete_action.triggered.connect(lambda: self._remove_tag(item))

        # AI suggest
        menu.addSeparator()
        ai_action = menu.addAction("AI Suggest Tag")
        ai_action.triggered.connect(lambda: self._ai_suggest(item))

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _apply_tag(self) -> None:
        """Apply the selected tag to the current item."""
        items = self.tree.selectedItems()
        if not items or not isinstance(items[0], TagTreeItem):
            return

        tag_type = self.tag_combo.currentData()
        self._set_tag(items[0], tag_type)

        # Also save alt text
        if tag_type == TagType.FIGURE:
            items[0].element.alt_text = self.alt_input.text()

    def _set_tag(self, item: TagTreeItem, tag_type: TagType) -> None:
        """Set a tag on an item."""
        old_tag = item.element.tag
        item.update_tag(tag_type)
        self.tag_changed.emit(item.element, tag_type)

        # Update stats
        self._update_stats()

        logger.debug(f"Changed tag from {old_tag} to {tag_type.value}")

    def _remove_tag(self, item: TagTreeItem) -> None:
        """Remove a tag from an item."""
        item.element.tag = None
        item._setup_display()
        self.tag_deleted.emit(item.element)
        self._update_stats()

    def _ai_suggest(self, item: TagTreeItem) -> None:
        """Request AI suggestion for tag."""
        # This would integrate with the AI processor
        QMessageBox.information(
            self,
            "AI Suggestion",
            f"AI would analyze: '{item.element.text[:50]}...'\n\n"
            "This feature requires an AI backend to be configured.",
        )

    def _update_stats(self) -> None:
        """Update the stats display."""
        if not self._document:
            return

        total = sum(len(p.elements) for p in self._document.pages)
        untagged = sum(
            1 for p in self._document.pages
            for e in p.elements if not e.tag
        )
        self.stats_label.setText(
            f"Total elements: {total} | Untagged: {untagged}"
        )

    def get_selected_element(self) -> Optional[PDFElement]:
        """Get the currently selected element."""
        items = self.tree.selectedItems()
        if items and isinstance(items[0], TagTreeItem):
            return items[0].element
        return None

    def clear(self) -> None:
        """Clear the tree."""
        self._document = None
        self.tree.clear()
        self._items.clear()
        self.editor_frame.hide()
        self.stats_label.setText("No document loaded")
