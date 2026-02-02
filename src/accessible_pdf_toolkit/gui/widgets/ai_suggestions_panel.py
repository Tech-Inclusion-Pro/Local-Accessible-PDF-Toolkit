"""
AI Suggestions panel with accordion sections for accessibility improvements.
"""

from typing import Optional, List, Dict, Any, Callable

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QFrame,
    QScrollArea,
    QCheckBox,
    QRadioButton,
    QButtonGroup,
    QSizePolicy,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...utils.constants import COLORS
from ...utils.logger import get_logger
from .accordion_section import AccordionSection

logger = get_logger(__name__)


class SuggestionItem(QFrame):
    """Widget representing a single AI suggestion."""

    applied = pyqtSignal(object)
    edited = pyqtSignal(object, str)
    skipped = pyqtSignal(object)
    selected = pyqtSignal(object)

    STATUS_ICONS = {
        "correct": "\u2705",      # Green checkmark
        "needs_attention": "\u26A0\uFE0F",  # Warning
        "missing": "\u274C",      # Red X
        "applied": "\u2714",      # Checkmark
        "skipped": "\u23E9",      # Fast forward
    }

    def __init__(
        self,
        detection: Dict[str, Any],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._detection = detection
        self._is_selected = False

        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header row with status, text, and checkbox
        header = QHBoxLayout()

        # Checkbox for batch selection
        self._checkbox = QCheckBox()
        self._checkbox.stateChanged.connect(self._on_checkbox_changed)
        header.addWidget(self._checkbox)

        # Status icon
        status = self._detection.get("status", "needs_attention")
        self._status_label = QLabel(self.STATUS_ICONS.get(status, "\u2753"))
        self._status_label.setFixedWidth(24)
        header.addWidget(self._status_label)

        # Current value
        current = self._detection.get("current_value", "")
        if current:
            current_label = QLabel(f"Current: {current[:50]}{'...' if len(current) > 50 else ''}")
            current_label.setWordWrap(True)
            header.addWidget(current_label, 1)
        else:
            header.addStretch()

        layout.addLayout(header)

        # Suggestion row
        suggested = self._detection.get("suggested_value", "")
        if suggested:
            suggestion_row = QHBoxLayout()
            suggestion_row.addWidget(QLabel("AI Suggestion:"))

            self._suggestion_edit = QLineEdit(suggested)
            self._suggestion_edit.setPlaceholderText("Edit suggestion...")
            suggestion_row.addWidget(self._suggestion_edit, 1)

            layout.addLayout(suggestion_row)
        else:
            self._suggestion_edit = None

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._apply_btn = QPushButton("Apply")
        self._apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(self._apply_btn)

        self._edit_btn = QPushButton("Edit")
        self._edit_btn.clicked.connect(self._on_edit)
        btn_row.addWidget(self._edit_btn)

        self._skip_btn = QPushButton("Skip")
        self._skip_btn.clicked.connect(self._on_skip)
        btn_row.addWidget(self._skip_btn)

        layout.addLayout(btn_row)

        # Clickable for selection
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _apply_styles(self) -> None:
        """Apply styles."""
        status = self._detection.get("status", "needs_attention")

        border_color = {
            "correct": COLORS.SUCCESS,
            "needs_attention": COLORS.WARNING,
            "missing": COLORS.ERROR,
            "applied": COLORS.SUCCESS,
            "skipped": COLORS.TEXT_DISABLED,
        }.get(status, COLORS.BORDER)

        self.setStyleSheet(f"""
            SuggestionItem {{
                background-color: {COLORS.SURFACE};
                border: 1px solid {border_color};
                border-radius: 4px;
                border-left: 4px solid {border_color};
            }}
            SuggestionItem:hover {{
                background-color: {COLORS.BACKGROUND_ALT};
            }}
            QLabel {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 11pt;
            }}
            QLineEdit {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 4px;
                font-size: 11pt;
            }}
            QPushButton {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}
            QCheckBox {{
                color: {COLORS.TEXT_PRIMARY};
            }}
        """)

    def _on_checkbox_changed(self, state: int) -> None:
        """Handle checkbox change."""
        self._is_selected = state == Qt.CheckState.Checked.value

    def _on_apply(self) -> None:
        """Handle apply button."""
        if self._suggestion_edit:
            self._detection["applied_value"] = self._suggestion_edit.text()
        self.applied.emit(self._detection)

    def _on_edit(self) -> None:
        """Handle edit button."""
        if self._suggestion_edit:
            self._suggestion_edit.setFocus()
            self._suggestion_edit.selectAll()

    def _on_skip(self) -> None:
        """Handle skip button."""
        self.skipped.emit(self._detection)

    def mousePressEvent(self, event) -> None:
        """Handle mouse press for selection."""
        self.selected.emit(self._detection)
        super().mousePressEvent(event)

    @property
    def detection(self) -> Dict[str, Any]:
        """Get the detection data."""
        return self._detection

    @property
    def is_checked(self) -> bool:
        """Check if item is selected."""
        return self._checkbox.isChecked()

    def set_checked(self, checked: bool) -> None:
        """Set checked state."""
        self._checkbox.setChecked(checked)


class AISuggestionsPanel(QWidget):
    """Right panel with AI suggestions and actions."""

    # Signals
    suggestion_applied = pyqtSignal(object)
    suggestion_edited = pyqtSignal(object, str)
    suggestion_skipped = pyqtSignal(object)
    apply_selected_requested = pyqtSignal()
    apply_all_requested = pyqtSignal()
    element_selected = pyqtSignal(str)
    review_mode_changed = pyqtSignal(bool)
    undo_requested = pyqtSignal()
    save_requested = pyqtSignal()
    preview_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._auto_accept_mode = False
        self._suggestion_items: List[SuggestionItem] = []

        self._setup_ui()
        self._setup_accessibility()
        self._apply_styles()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with review mode toggle
        header = QFrame()
        header.setObjectName("header")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("AI Suggestions")
        title.setStyleSheet(f"font-size: 16pt; font-weight: bold; color: {COLORS.TEXT_PRIMARY};")
        header_layout.addWidget(title)

        # Review mode toggle
        mode_frame = QFrame()
        mode_layout = QVBoxLayout(mode_frame)
        mode_layout.setContentsMargins(0, 8, 0, 0)

        mode_label = QLabel("Review Mode:")
        mode_label.setStyleSheet(f"font-size: 11pt; color: {COLORS.TEXT_SECONDARY};")
        mode_layout.addWidget(mode_label)

        self._mode_group = QButtonGroup(self)

        self._auto_radio = QRadioButton("Auto-Accept (Apply all AI suggestions automatically)")
        self._auto_radio.toggled.connect(self._on_mode_changed)
        self._mode_group.addButton(self._auto_radio)
        mode_layout.addWidget(self._auto_radio)

        self._manual_radio = QRadioButton("Manual Review (Review each suggestion individually)")
        self._manual_radio.setChecked(True)
        self._mode_group.addButton(self._manual_radio)
        mode_layout.addWidget(self._manual_radio)

        header_layout.addWidget(mode_frame)
        layout.addWidget(header)

        # Scroll area for accordion sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        self._scroll_layout = QVBoxLayout(scroll_content)
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll_layout.setSpacing(0)

        # Document Properties section
        self._doc_section = AccordionSection("Document Properties", icon="\uD83D\uDCC4", expanded=True)
        self._doc_content = QWidget()
        self._doc_layout = QVBoxLayout(self._doc_content)
        self._doc_section.set_content(self._doc_content)
        self._scroll_layout.addWidget(self._doc_section)

        # Headings section
        self._headings_section = AccordionSection("Headings", icon="\uD83D\uDCDD", badge_count=0)
        self._headings_content = QWidget()
        self._headings_layout = QVBoxLayout(self._headings_content)
        self._headings_section.set_content(self._headings_content)
        self._scroll_layout.addWidget(self._headings_section)

        # Images section
        self._images_section = AccordionSection("Images", icon="\uD83D\uDDBC", badge_count=0)
        self._images_content = QWidget()
        self._images_layout = QVBoxLayout(self._images_content)
        self._images_section.set_content(self._images_content)
        self._scroll_layout.addWidget(self._images_section)

        # Tables section
        self._tables_section = AccordionSection("Tables", icon="\uD83D\uDCCA", badge_count=0)
        self._tables_content = QWidget()
        self._tables_layout = QVBoxLayout(self._tables_content)
        self._tables_section.set_content(self._tables_content)
        self._scroll_layout.addWidget(self._tables_section)

        # Links section
        self._links_section = AccordionSection("Links", icon="\uD83D\uDD17", badge_count=0)
        self._links_content = QWidget()
        self._links_layout = QVBoxLayout(self._links_content)
        self._links_section.set_content(self._links_content)
        self._scroll_layout.addWidget(self._links_section)

        # Reading Order section
        self._order_section = AccordionSection("Reading Order", icon="\uD83D\uDD22", badge_count=0)
        self._order_content = QWidget()
        self._order_layout = QVBoxLayout(self._order_content)
        self._order_section.set_content(self._order_content)
        self._scroll_layout.addWidget(self._order_section)

        self._scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        # Bottom action buttons
        actions = QFrame()
        actions.setObjectName("actions")
        actions_layout = QVBoxLayout(actions)
        actions_layout.setContentsMargins(12, 12, 12, 12)
        actions_layout.setSpacing(8)

        # Selection controls
        selection_row = QHBoxLayout()
        self._select_all_btn = QPushButton("Select All")
        self._select_all_btn.clicked.connect(self._select_all)
        selection_row.addWidget(self._select_all_btn)

        self._deselect_all_btn = QPushButton("Deselect All")
        self._deselect_all_btn.clicked.connect(self._deselect_all)
        selection_row.addWidget(self._deselect_all_btn)

        selection_row.addStretch()
        actions_layout.addLayout(selection_row)

        # Primary actions
        primary_row = QHBoxLayout()

        self._apply_selected_btn = QPushButton("\u2713 Apply Selected")
        self._apply_selected_btn.clicked.connect(self.apply_selected_requested.emit)
        self._apply_selected_btn.setObjectName("primaryBtn")
        primary_row.addWidget(self._apply_selected_btn)

        self._apply_all_btn = QPushButton("\u2713 Apply All Remaining")
        self._apply_all_btn.clicked.connect(self.apply_all_requested.emit)
        primary_row.addWidget(self._apply_all_btn)

        actions_layout.addLayout(primary_row)

        # Secondary actions
        secondary_row = QHBoxLayout()

        self._preview_btn = QPushButton("\uD83D\uDC41 Preview Changes")
        self._preview_btn.clicked.connect(self.preview_requested.emit)
        secondary_row.addWidget(self._preview_btn)

        self._undo_btn = QPushButton("\u21A9 Undo Last")
        self._undo_btn.clicked.connect(self.undo_requested.emit)
        secondary_row.addWidget(self._undo_btn)

        actions_layout.addLayout(secondary_row)

        # Save button
        self._save_btn = QPushButton("\uD83D\uDCBE Save & Export PDF")
        self._save_btn.clicked.connect(self.save_requested.emit)
        self._save_btn.setObjectName("saveBtn")
        actions_layout.addWidget(self._save_btn)

        layout.addWidget(actions)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self.setAccessibleName("AI Suggestions Panel")
        self.setAccessibleDescription("Review and apply AI-generated accessibility suggestions")

        self._auto_radio.setAccessibleName("Auto-accept mode")
        self._manual_radio.setAccessibleName("Manual review mode")

    def _apply_styles(self) -> None:
        """Apply widget styles."""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
            }}

            #header {{
                background-color: {COLORS.SURFACE};
                border-bottom: 1px solid {COLORS.BORDER};
            }}

            #actions {{
                background-color: {COLORS.SURFACE};
                border-top: 1px solid {COLORS.BORDER};
            }}

            QRadioButton {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 11pt;
                spacing: 8px;
            }}

            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
            }}

            QPushButton {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11pt;
            }}

            QPushButton:hover {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}

            #primaryBtn {{
                background-color: {COLORS.PRIMARY};
                color: white;
                border: none;
            }}

            #primaryBtn:hover {{
                background-color: {COLORS.PRIMARY_DARK};
            }}

            #saveBtn {{
                background-color: {COLORS.SECONDARY};
                color: white;
                border: none;
                font-weight: bold;
            }}

            #saveBtn:hover {{
                background-color: {COLORS.SECONDARY_DARK};
            }}

            QScrollArea {{
                border: none;
            }}
        """)

    def _on_mode_changed(self, auto_checked: bool) -> None:
        """Handle review mode change."""
        self._auto_accept_mode = auto_checked
        self.review_mode_changed.emit(auto_checked)

    def _select_all(self) -> None:
        """Select all suggestion items."""
        for item in self._suggestion_items:
            item.set_checked(True)

    def _deselect_all(self) -> None:
        """Deselect all suggestion items."""
        for item in self._suggestion_items:
            item.set_checked(False)

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        """Clear all items from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def set_document_properties(
        self,
        title: Optional[str],
        language: Optional[str],
        author: Optional[str],
        subject: Optional[str],
    ) -> None:
        """
        Set document properties display.

        Args:
            title: Document title
            language: Document language
            author: Document author
            subject: Document subject
        """
        self._clear_layout(self._doc_layout)

        props = [
            ("Title", title, "Add a descriptive title"),
            ("Language", language, "Set document language (e.g., 'en')"),
            ("Author", author, None),
            ("Subject", subject, None),
        ]

        issues = 0
        for label, value, suggestion in props:
            row = QHBoxLayout()

            status_icon = "\u2705" if value else "\u26A0\uFE0F"
            row.addWidget(QLabel(f"{status_icon} {label}:"))

            if value:
                row.addWidget(QLabel(value))
            else:
                edit = QLineEdit()
                edit.setPlaceholderText(suggestion or f"Enter {label.lower()}")
                row.addWidget(edit)
                issues += 1

            container = QWidget()
            container.setLayout(row)
            self._doc_layout.addWidget(container)

        self._doc_section.set_badge_count(issues)

    def set_headings(self, detections: List[Dict[str, Any]]) -> None:
        """Set heading suggestions."""
        self._clear_layout(self._headings_layout)

        for detection in detections:
            item = self._create_suggestion_item(detection)
            self._headings_layout.addWidget(item)
            self._suggestion_items.append(item)

        self._headings_section.set_badge_count(len(detections))

    def set_images(self, detections: List[Dict[str, Any]]) -> None:
        """Set image suggestions."""
        self._clear_layout(self._images_layout)

        for detection in detections:
            item = self._create_suggestion_item(detection)
            self._images_layout.addWidget(item)
            self._suggestion_items.append(item)

        self._images_section.set_badge_count(len(detections))

    def set_tables(self, detections: List[Dict[str, Any]]) -> None:
        """Set table suggestions."""
        self._clear_layout(self._tables_layout)

        for detection in detections:
            item = self._create_suggestion_item(detection)
            self._tables_layout.addWidget(item)
            self._suggestion_items.append(item)

        self._tables_section.set_badge_count(len(detections))

    def set_links(self, detections: List[Dict[str, Any]]) -> None:
        """Set link suggestions."""
        self._clear_layout(self._links_layout)

        for detection in detections:
            item = self._create_suggestion_item(detection)
            self._links_layout.addWidget(item)
            self._suggestion_items.append(item)

        self._links_section.set_badge_count(len(detections))

    def set_reading_order(self, detections: List[Dict[str, Any]]) -> None:
        """Set reading order suggestions."""
        self._clear_layout(self._order_layout)

        for detection in detections:
            item = self._create_suggestion_item(detection)
            self._order_layout.addWidget(item)
            self._suggestion_items.append(item)

        self._order_section.set_badge_count(len(detections))

    def _create_suggestion_item(self, detection: Dict[str, Any]) -> SuggestionItem:
        """Create a suggestion item widget."""
        item = SuggestionItem(detection)
        item.applied.connect(self._on_item_applied)
        item.skipped.connect(self._on_item_skipped)
        item.selected.connect(self._on_item_selected)
        return item

    def _on_item_applied(self, detection: Dict[str, Any]) -> None:
        """Handle item applied."""
        self.suggestion_applied.emit(detection)

    def _on_item_skipped(self, detection: Dict[str, Any]) -> None:
        """Handle item skipped."""
        self.suggestion_skipped.emit(detection)

    def _on_item_selected(self, detection: Dict[str, Any]) -> None:
        """Handle item selected."""
        element_id = detection.get("id", "")
        if element_id:
            self.element_selected.emit(element_id)

    def get_selected_items(self) -> List[Dict[str, Any]]:
        """Get all selected suggestion items."""
        return [item.detection for item in self._suggestion_items if item.is_checked]

    def clear(self) -> None:
        """Clear all suggestions."""
        self._suggestion_items.clear()
        self._clear_layout(self._doc_layout)
        self._clear_layout(self._headings_layout)
        self._clear_layout(self._images_layout)
        self._clear_layout(self._tables_layout)
        self._clear_layout(self._links_layout)
        self._clear_layout(self._order_layout)

        self._doc_section.set_badge_count(0)
        self._headings_section.set_badge_count(0)
        self._images_section.set_badge_count(0)
        self._tables_section.set_badge_count(0)
        self._links_section.set_badge_count(0)
        self._order_section.set_badge_count(0)

    @property
    def auto_accept_mode(self) -> bool:
        """Check if auto-accept mode is enabled."""
        return self._auto_accept_mode

    def scroll_to_detection(self, detection_id: str) -> None:
        """
        Scroll to and highlight a specific detection by ID.

        Args:
            detection_id: The ID of the detection to scroll to
        """
        for item in self._suggestion_items:
            if item.detection.get("id") == detection_id:
                # Highlight this item
                item.setStyleSheet(f"""
                    SuggestionItem {{
                        background-color: {COLORS.PRIMARY}30;
                        border: 2px solid {COLORS.PRIMARY};
                        border-radius: 4px;
                        border-left: 4px solid {COLORS.PRIMARY};
                    }}
                    QLabel {{
                        color: {COLORS.TEXT_PRIMARY};
                        font-size: 11pt;
                    }}
                    QLineEdit {{
                        background-color: {COLORS.INPUT_BG};
                        color: {COLORS.INPUT_TEXT};
                        border: 1px solid {COLORS.INPUT_BORDER};
                        border-radius: 4px;
                        padding: 4px;
                        font-size: 11pt;
                    }}
                    QPushButton {{
                        background-color: {COLORS.SURFACE};
                        color: {COLORS.TEXT_PRIMARY};
                        border: 1px solid {COLORS.BORDER};
                        border-radius: 4px;
                        padding: 4px 12px;
                        font-size: 10pt;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS.PRIMARY};
                        color: white;
                    }}
                    QCheckBox {{
                        color: {COLORS.TEXT_PRIMARY};
                    }}
                """)

                # Expand the parent section
                detection_type = item.detection.get("type", "")
                if detection_type == "heading":
                    self._headings_section.set_expanded(True)
                elif detection_type == "image":
                    self._images_section.set_expanded(True)
                elif detection_type == "table":
                    self._tables_section.set_expanded(True)
                elif detection_type == "link":
                    self._links_section.set_expanded(True)
                elif detection_type == "reading_order":
                    self._order_section.set_expanded(True)

                # Scroll to make visible
                item.setFocus()

                # Reset highlight after 3 seconds
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(3000, lambda i=item: i._apply_styles())

                break
            else:
                # Reset other items to normal style
                item._apply_styles()

    def highlight_detection(self, detection_data: dict) -> None:
        """
        Highlight a detection based on overlay click data from the viewer.

        Args:
            detection_data: Dictionary containing detection information
        """
        detection_id = detection_data.get("id", "")
        if detection_id:
            self.scroll_to_detection(detection_id)
