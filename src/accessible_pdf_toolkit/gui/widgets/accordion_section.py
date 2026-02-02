"""
Collapsible accordion section widget with animation.
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QPropertyAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
)
from PyQt6.QtGui import QIcon, QFont

from ...utils.constants import COLORS
from ...utils.logger import get_logger

logger = get_logger(__name__)


class AccordionSection(QWidget):
    """Collapsible section widget with smooth animation."""

    # Signals
    expanded = pyqtSignal()
    collapsed = pyqtSignal()
    toggled = pyqtSignal(bool)

    def __init__(
        self,
        title: str,
        icon: Optional[str] = None,
        badge_count: int = 0,
        expanded: bool = False,
        parent: Optional[QWidget] = None,
    ):
        """
        Initialize the accordion section.

        Args:
            title: Section title text
            icon: Optional icon character/emoji
            badge_count: Number to display in badge (0 = hidden)
            expanded: Initial expanded state
            parent: Parent widget
        """
        super().__init__(parent)

        self._title = title
        self._icon = icon
        self._badge_count = badge_count
        self._is_expanded = expanded
        self._animation_duration = 200

        self._setup_ui()
        self._setup_accessibility()
        self._apply_styles()

        # Set initial state
        if not expanded:
            self._content_area.setMaximumHeight(0)

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        # Header button
        self._header = QPushButton()
        self._header.setCheckable(True)
        self._header.setChecked(self._is_expanded)
        self._header.clicked.connect(self._on_header_clicked)
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(12, 10, 12, 10)

        # Expand/collapse indicator
        self._expand_indicator = QLabel()
        self._expand_indicator.setFixedWidth(20)
        self._update_expand_indicator()
        header_layout.addWidget(self._expand_indicator)

        # Icon (if provided)
        if self._icon:
            icon_label = QLabel(self._icon)
            icon_label.setFixedWidth(24)
            header_layout.addWidget(icon_label)

        # Title
        self._title_label = QLabel(self._title)
        self._title_label.setFont(QFont("", 11, QFont.Weight.Medium))
        header_layout.addWidget(self._title_label)

        header_layout.addStretch()

        # Badge
        self._badge_label = QLabel()
        self._badge_label.setFixedSize(24, 24)
        self._badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_badge()
        header_layout.addWidget(self._badge_label)

        self.layout().addWidget(self._header)

        # Content area with animation support
        self._content_area = QFrame()
        self._content_area.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._content_area.setMaximumHeight(0 if not self._is_expanded else 16777215)

        self._content_layout = QVBoxLayout(self._content_area)
        self._content_layout.setContentsMargins(12, 8, 12, 8)
        self._content_layout.setSpacing(4)

        self.layout().addWidget(self._content_area)

        # Animation
        self._animation = QPropertyAnimation(self._content_area, b"maximumHeight")
        self._animation.setDuration(self._animation_duration)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self._header.setAccessibleName(f"{self._title} section")
        self._header.setAccessibleDescription(
            f"{'Expanded' if self._is_expanded else 'Collapsed'}. "
            f"Click to {'collapse' if self._is_expanded else 'expand'}."
        )
        self.setAccessibleName(f"{self._title} accordion section")

    def _apply_styles(self) -> None:
        """Apply widget styles."""
        self._header.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: none;
                border-bottom: 1px solid {COLORS.BORDER};
                text-align: left;
                font-size: 12pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.BACKGROUND_ALT};
            }}
            QPushButton:checked {{
                background-color: {COLORS.BACKGROUND_ALT};
            }}
            QPushButton:focus {{
                outline: 2px solid {COLORS.PRIMARY};
                outline-offset: -2px;
            }}
        """)

        self._content_area.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND};
                border: none;
                border-bottom: 1px solid {COLORS.BORDER};
            }}
        """)

        self._title_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY};")
        self._expand_indicator.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY};")

        self._badge_label.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS.PRIMARY};
                color: white;
                border-radius: 12px;
                font-size: 10pt;
                font-weight: bold;
            }}
        """)

    def _update_expand_indicator(self) -> None:
        """Update the expand/collapse indicator."""
        if self._is_expanded:
            self._expand_indicator.setText("\u25BC")  # Down arrow
        else:
            self._expand_indicator.setText("\u25B6")  # Right arrow

    def _update_badge(self) -> None:
        """Update the badge display."""
        if self._badge_count > 0:
            self._badge_label.setText(str(self._badge_count))
            self._badge_label.show()
        else:
            self._badge_label.hide()

    def _on_header_clicked(self) -> None:
        """Handle header click to toggle expansion."""
        self.toggle()

    def toggle(self) -> None:
        """Toggle the expanded/collapsed state."""
        self._is_expanded = not self._is_expanded
        self._header.setChecked(self._is_expanded)
        self._update_expand_indicator()

        # Animate
        if self._is_expanded:
            # Calculate content height
            content_height = self._content_layout.sizeHint().height()
            if content_height == 0:
                content_height = 100  # Default minimum

            self._animation.setStartValue(0)
            self._animation.setEndValue(content_height + 20)
            self.expanded.emit()
        else:
            self._animation.setStartValue(self._content_area.height())
            self._animation.setEndValue(0)
            self.collapsed.emit()

        self._animation.start()
        self.toggled.emit(self._is_expanded)

        # Update accessibility
        self._header.setAccessibleDescription(
            f"{'Expanded' if self._is_expanded else 'Collapsed'}. "
            f"Click to {'collapse' if self._is_expanded else 'expand'}."
        )

    def expand(self) -> None:
        """Expand the section."""
        if not self._is_expanded:
            self.toggle()

    def collapse(self) -> None:
        """Collapse the section."""
        if self._is_expanded:
            self.toggle()

    def set_content(self, widget: QWidget) -> None:
        """
        Set the content widget.

        Args:
            widget: Widget to display in the content area
        """
        # Clear existing content
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._content_layout.addWidget(widget)

        # Update animation end value if expanded
        if self._is_expanded:
            self._content_area.setMaximumHeight(16777215)

    def add_widget(self, widget: QWidget) -> None:
        """
        Add a widget to the content area.

        Args:
            widget: Widget to add
        """
        self._content_layout.addWidget(widget)

        if self._is_expanded:
            self._content_area.setMaximumHeight(16777215)

    def set_title(self, title: str) -> None:
        """Set the section title."""
        self._title = title
        self._title_label.setText(title)
        self._header.setAccessibleName(f"{title} section")

    def set_badge_count(self, count: int) -> None:
        """
        Set the badge count.

        Args:
            count: Number to display (0 = hidden)
        """
        self._badge_count = count
        self._update_badge()

    def set_icon(self, icon: str) -> None:
        """Set the section icon."""
        self._icon = icon
        # Would need to update the icon label

    @property
    def is_expanded(self) -> bool:
        """Check if section is expanded."""
        return self._is_expanded

    @property
    def title(self) -> str:
        """Get the section title."""
        return self._title

    @property
    def badge_count(self) -> int:
        """Get the badge count."""
        return self._badge_count

    @property
    def content_layout(self) -> QVBoxLayout:
        """Get the content layout for adding widgets."""
        return self._content_layout
