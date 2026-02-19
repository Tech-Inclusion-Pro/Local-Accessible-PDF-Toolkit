"""
Privacy warning dialog for cloud AI usage.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QCheckBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ...utils.constants import COLORS
from ...utils.logger import get_logger

logger = get_logger(__name__)


class PrivacyWarningDialog(QDialog):
    """Modal dialog warning about cloud AI privacy implications."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._accepted = False
        self._dont_show_again = False

        self._setup_ui()
        self._setup_accessibility()
        self._apply_styles()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Privacy & Compliance Warning")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMaximumWidth(600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Warning icon and title
        header = QHBoxLayout()

        warning_icon = QLabel("\u25B3")
        warning_icon.setFont(QFont("", 32))
        header.addWidget(warning_icon)

        title = QLabel("PRIVACY & COMPLIANCE WARNING")
        title.setFont(QFont("", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS.WARNING};")
        header.addWidget(title)
        header.addStretch()

        layout.addLayout(header)

        # Main message
        message = QLabel(
            "You are about to switch to <b>CLOUD-BASED AI</b>."
        )
        message.setWordWrap(True)
        message.setStyleSheet(f"font-size: 14pt; color: {COLORS.TEXT_PRIMARY};")
        layout.addWidget(message)

        # Warning section
        warning_frame = QFrame()
        warning_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #FEE2E2;
                border: 2px solid {COLORS.ERROR};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        warning_layout = QVBoxLayout(warning_frame)

        not_recommended = QLabel(
            "<b>\u2717 This is NOT recommended for:</b>"
        )
        not_recommended.setStyleSheet(f"color: {COLORS.ERROR}; font-size: 12pt;")
        warning_layout.addWidget(not_recommended)

        warnings = [
            "\u2022 Student records (FERPA protected)",
            "\u2022 Patient information (HIPAA protected)",
            "\u2022 Any personally identifiable information (PII)",
        ]
        for warning in warnings:
            label = QLabel(warning)
            label.setStyleSheet(f"color: #991B1B; font-size: 11pt; margin-left: 16px;")
            warning_layout.addWidget(label)

        layout.addWidget(warning_frame)

        # Required section
        required_frame = QFrame()
        required_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #FEF3C7;
                border: 2px solid {COLORS.WARNING};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        required_layout = QVBoxLayout(required_frame)

        required_title = QLabel(
            "<b>\u2713 REQUIRED BEFORE UPLOAD:</b>"
        )
        required_title.setStyleSheet(f"color: #92400E; font-size: 12pt;")
        required_layout.addWidget(required_title)

        required_text = QLabel(
            "You MUST remove all student/patient names, IDs, SSNs, "
            "dates of birth, and protected health information."
        )
        required_text.setWordWrap(True)
        required_text.setStyleSheet(f"color: #92400E; font-size: 11pt;")
        required_layout.addWidget(required_text)

        layout.addWidget(required_frame)

        # Recommendation section
        recommend_frame = QFrame()
        recommend_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #DBEAFE;
                border: 2px solid {COLORS.PRIMARY};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        recommend_layout = QVBoxLayout(recommend_frame)

        recommend_title = QLabel(
            "<b>\u2022 RECOMMENDATION:</b>"
        )
        recommend_title.setStyleSheet(f"color: #1E40AF; font-size: 12pt;")
        recommend_layout.addWidget(recommend_title)

        recommend_text = QLabel(
            "Use <b>LOCAL models</b> (Ollama, LM Studio, etc.) "
            "for complete privacy and compliance."
        )
        recommend_text.setWordWrap(True)
        recommend_text.setStyleSheet(f"color: #1E40AF; font-size: 11pt;")
        recommend_layout.addWidget(recommend_text)

        layout.addWidget(recommend_frame)

        # Don't show again checkbox
        self._dont_show_checkbox = QCheckBox("Don't show this warning again")
        self._dont_show_checkbox.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 10pt;")
        layout.addWidget(self._dont_show_checkbox)

        # Buttons
        button_row = QHBoxLayout()
        button_row.addStretch()

        self._back_btn = QPushButton("Go Back to Local")
        self._back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.SECONDARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 12pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS.SECONDARY_DARK};
            }}
        """)
        self._back_btn.clicked.connect(self._on_back)
        button_row.addWidget(self._back_btn)

        self._continue_btn = QPushButton("I Understand, Continue")
        self._continue_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 2px solid {COLORS.BORDER};
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 12pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.WARNING};
                color: white;
                border-color: {COLORS.WARNING};
            }}
        """)
        self._continue_btn.clicked.connect(self._on_continue)
        button_row.addWidget(self._continue_btn)

        layout.addLayout(button_row)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self.setAccessibleName("Privacy Warning Dialog")
        self.setAccessibleDescription(
            "Warning about using cloud AI services with potentially sensitive data"
        )

        self._back_btn.setAccessibleName("Go back to local AI")
        self._back_btn.setAccessibleDescription("Cancel and use local AI instead")

        self._continue_btn.setAccessibleName("Continue with cloud AI")
        self._continue_btn.setAccessibleDescription(
            "Accept the privacy risks and continue with cloud AI"
        )

    def _apply_styles(self) -> None:
        """Apply dialog styles."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS.BACKGROUND};
            }}
        """)

    def _on_back(self) -> None:
        """Handle back button click."""
        self._accepted = False
        self._dont_show_again = self._dont_show_checkbox.isChecked()
        self.reject()

    def _on_continue(self) -> None:
        """Handle continue button click."""
        self._accepted = True
        self._dont_show_again = self._dont_show_checkbox.isChecked()
        self.accept()

    @property
    def was_accepted(self) -> bool:
        """Check if user accepted the warning."""
        return self._accepted

    @property
    def dont_show_again(self) -> bool:
        """Check if user doesn't want to see warning again."""
        return self._dont_show_again

    @staticmethod
    def show_warning(parent=None, already_accepted: bool = False) -> tuple:
        """
        Show the privacy warning dialog.

        Args:
            parent: Parent widget
            already_accepted: If True, skip showing the dialog

        Returns:
            Tuple of (accepted: bool, dont_show_again: bool)
        """
        if already_accepted:
            return True, True

        dialog = PrivacyWarningDialog(parent)
        dialog.exec()

        return dialog.was_accepted, dialog.dont_show_again
