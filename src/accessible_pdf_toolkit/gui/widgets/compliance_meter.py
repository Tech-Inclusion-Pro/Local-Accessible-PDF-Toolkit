"""
Compliance meter widget for displaying WCAG compliance status.
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QFrame,
    QScrollArea,
    QPushButton,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtProperty, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

from ...utils.constants import COLORS, WCAGLevel, ComplianceStatus
from ...core.wcag_validator import ValidationResult, ValidationIssue, IssueSeverity


class CircularProgress(QWidget):
    """Circular progress indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._max_value = 100
        self._width = 8
        self._color = QColor(COLORS.PRIMARY)
        self._background_color = QColor(COLORS.BORDER)

        self.setMinimumSize(100, 100)
        self.setAccessibleName("Compliance score")

    @pyqtProperty(int)
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, val: int) -> None:
        self._value = max(0, min(val, self._max_value))
        self.setAccessibleDescription(f"{self._value}% compliance")
        self.update()

    def setValue(self, value: int) -> None:
        """Set the progress value with animation."""
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(500)
        self._animation.setStartValue(self._value)
        self._animation.setEndValue(value)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()

    def setColor(self, color: str) -> None:
        """Set the progress color."""
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the circular progress."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate dimensions
        side = min(self.width(), self.height())
        rect_size = side - self._width * 2
        x = (self.width() - rect_size) // 2
        y = (self.height() - rect_size) // 2

        # Draw background circle
        pen = QPen(self._background_color)
        pen.setWidth(self._width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(x, y, rect_size, rect_size, 0, 360 * 16)

        # Draw progress arc
        if self._value > 0:
            pen.setColor(self._color)
            painter.setPen(pen)
            span_angle = int(-self._value / self._max_value * 360 * 16)
            painter.drawArc(x, y, rect_size, rect_size, 90 * 16, span_angle)

        # Draw text
        painter.setPen(QColor(COLORS.TEXT_PRIMARY))
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            f"{self._value}%"
        )


class ComplianceMeter(QWidget):
    """Widget displaying WCAG compliance status and score."""

    # Signals for issue interaction
    issue_fix_requested = pyqtSignal(object)  # ValidationIssue
    issue_navigate_requested = pyqtSignal(int)  # page number

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result: Optional[ValidationResult] = None
        self._setup_ui()
        self._setup_accessibility()

    def _setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Title
        title = QLabel("WCAG Compliance")
        title.setStyleSheet(f"""
            font-size: 16pt;
            font-weight: bold;
            color: {COLORS.TEXT_PRIMARY};
        """)
        layout.addWidget(title)

        # Circular progress
        self.progress = CircularProgress()
        layout.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status label
        self.status_label = QLabel("Not validated")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            font-size: 14pt;
            color: {COLORS.TEXT_SECONDARY};
            padding: 8px;
        """)
        layout.addWidget(self.status_label)

        # Level indicator
        level_frame = QFrame()
        level_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND_ALT};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        level_layout = QHBoxLayout(level_frame)

        level_label = QLabel("Target Level:")
        level_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 12pt;")
        self.level_value = QLabel("AA")
        self.level_value.setStyleSheet(f"font-weight: bold; color: {COLORS.TEXT_PRIMARY}; font-size: 12pt;")
        level_layout.addWidget(level_label)
        level_layout.addWidget(self.level_value)
        level_layout.addStretch()

        layout.addWidget(level_frame)

        # Issue summary
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND_ALT};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        summary_layout = QVBoxLayout(self.summary_frame)

        summary_title = QLabel("Issues")
        summary_title.setStyleSheet(f"font-weight: bold; color: {COLORS.TEXT_PRIMARY}; font-size: 12pt;")
        summary_layout.addWidget(summary_title)

        self.errors_label = QLabel("Errors: 0")
        self.errors_label.setStyleSheet(f"color: {COLORS.ERROR}; font-size: 12pt;")
        summary_layout.addWidget(self.errors_label)

        self.warnings_label = QLabel("Warnings: 0")
        self.warnings_label.setStyleSheet(f"color: {COLORS.WARNING}; font-size: 12pt;")
        summary_layout.addWidget(self.warnings_label)

        self.info_label = QLabel("Info: 0")
        self.info_label.setStyleSheet(f"color: {COLORS.INFO}; font-size: 12pt;")
        summary_layout.addWidget(self.info_label)

        layout.addWidget(self.summary_frame)

        # Issues list (scrollable)
        issues_label = QLabel("Issue Details")
        issues_label.setStyleSheet(f"font-weight: bold; color: {COLORS.TEXT_PRIMARY}; font-size: 12pt;")
        layout.addWidget(issues_label)

        self._issues_scroll = QScrollArea()
        self._issues_scroll.setWidgetResizable(True)
        self._issues_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                background-color: {COLORS.BACKGROUND};
            }}
        """)
        self._issues_container = QWidget()
        self._issues_layout = QVBoxLayout(self._issues_container)
        self._issues_layout.setContentsMargins(4, 4, 4, 4)
        self._issues_layout.setSpacing(4)
        self._issues_layout.addStretch()
        self._issues_scroll.setWidget(self._issues_container)

        layout.addWidget(self._issues_scroll, 1)  # stretch factor 1 to fill space

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self.setAccessibleName("Compliance meter")
        self.setAccessibleDescription("Displays WCAG compliance score and issues")

    def set_result(self, result: ValidationResult) -> None:
        """
        Set the validation result.

        Args:
            result: ValidationResult to display
        """
        self._result = result

        # Update progress
        self.progress.setValue(int(result.score))

        # Update color based on score
        if result.score >= 90:
            self.progress.setColor(COLORS.SUCCESS)
            status = "Excellent"
        elif result.score >= 70:
            self.progress.setColor(COLORS.WARNING)
            status = "Needs Improvement"
        else:
            self.progress.setColor(COLORS.ERROR)
            status = "Non-compliant"

        if result.is_compliant:
            self.status_label.setText(f"Compliant - {status}")
            self.status_label.setStyleSheet(f"""
                font-size: 14px;
                color: {COLORS.SUCCESS};
                font-weight: bold;
            """)
        else:
            self.status_label.setText(f"Non-compliant - {status}")
            self.status_label.setStyleSheet(f"""
                font-size: 14px;
                color: {COLORS.ERROR};
                font-weight: bold;
            """)

        # Update level
        self.level_value.setText(result.level.value)

        # Update summary
        summary = result.summary
        self.errors_label.setText(f"Errors: {summary.get('errors', 0)}")
        self.warnings_label.setText(f"Warnings: {summary.get('warnings', 0)}")
        self.info_label.setText(f"Info: {summary.get('info', 0)}")

        # Update accessibility
        self.setAccessibleDescription(
            f"Compliance score: {result.score}%. "
            f"{summary.get('errors', 0)} errors, "
            f"{summary.get('warnings', 0)} warnings."
        )

        # Populate clickable issues list
        self._populate_issues(result)

    def _clear_issues(self) -> None:
        """Remove all issue widgets from the issues list."""
        while self._issues_layout.count() > 0:
            item = self._issues_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _populate_issues(self, result: ValidationResult) -> None:
        """Populate the scrollable issues list with clickable issue widgets."""
        self._clear_issues()

        if not result.issues:
            no_issues = QLabel("No issues found!")
            no_issues.setStyleSheet(f"color: {COLORS.SUCCESS}; font-size: 11pt; padding: 8px;")
            no_issues.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._issues_layout.addWidget(no_issues)
            self._issues_layout.addStretch()
            return

        # Color map for severity border
        severity_colors = {
            IssueSeverity.ERROR: COLORS.ERROR,
            IssueSeverity.WARNING: COLORS.WARNING,
            IssueSeverity.INFO: COLORS.INFO,
        }

        for issue in result.issues:
            border_color = severity_colors.get(issue.severity, COLORS.INFO)

            issue_frame = QFrame()
            issue_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS.SURFACE};
                    border-left: 4px solid {border_color};
                    border-radius: 2px;
                    padding: 4px;
                }}
            """)
            issue_layout = QVBoxLayout(issue_frame)
            issue_layout.setContentsMargins(8, 4, 4, 4)
            issue_layout.setSpacing(2)

            # Criterion + severity
            header = QLabel(f"[{issue.criterion}] {issue.severity.value.upper()}")
            header.setStyleSheet(f"color: {border_color}; font-size: 9pt; font-weight: bold;")
            issue_layout.addWidget(header)

            # Message
            msg = QLabel(issue.message)
            msg.setWordWrap(True)
            msg.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 10pt;")
            issue_layout.addWidget(msg)

            # Action buttons row
            btn_row = QHBoxLayout()
            btn_row.setSpacing(4)

            if issue.page:
                page_btn = QPushButton(f"Page {issue.page}")
                page_btn.setFixedHeight(22)
                page_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS.BACKGROUND_ALT};
                        color: {COLORS.TEXT_SECONDARY};
                        border: 1px solid {COLORS.BORDER};
                        border-radius: 2px;
                        padding: 1px 6px;
                        font-size: 9pt;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS.PRIMARY};
                        color: white;
                    }}
                """)
                page_num = issue.page
                page_btn.clicked.connect(lambda checked, p=page_num: self.issue_navigate_requested.emit(p))
                btn_row.addWidget(page_btn)

            if issue.auto_fixable:
                fix_btn = QPushButton("Fix")
                fix_btn.setFixedHeight(22)
                fix_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS.SUCCESS};
                        color: white;
                        border: none;
                        border-radius: 2px;
                        padding: 1px 8px;
                        font-size: 9pt;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: #16A34A;
                    }}
                """)
                current_issue = issue
                fix_btn.clicked.connect(lambda checked, i=current_issue: self.issue_fix_requested.emit(i))
                btn_row.addWidget(fix_btn)

            btn_row.addStretch()
            issue_layout.addLayout(btn_row)

            self._issues_layout.addWidget(issue_frame)

        self._issues_layout.addStretch()

    def set_level(self, level: WCAGLevel) -> None:
        """Set the target WCAG level."""
        self.level_value.setText(level.value)

    def reset(self) -> None:
        """Reset the meter to initial state."""
        self._result = None
        self.progress._value = 0
        self.progress.update()
        self.status_label.setText("Not validated")
        self.status_label.setStyleSheet(f"""
            font-size: 14px;
            color: {COLORS.TEXT_SECONDARY};
        """)
        self.errors_label.setText("Errors: 0")
        self.warnings_label.setText("Warnings: 0")
        self.info_label.setText("Info: 0")
        self._clear_issues()
