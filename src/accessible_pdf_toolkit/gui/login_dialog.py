"""
Login dialog for user authentication.
"""

import json
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QWidget,
    QMessageBox,
    QCheckBox,
    QFrame,
    QComboBox,
    QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

from ..utils.constants import COLORS, APP_NAME, ASSETS_DIR, APP_DATA_DIR
from ..utils.logger import get_logger
from ..database.models import User, init_db
from ..database.queries import DatabaseQueries
from ..database.encryption import EncryptionManager

logger = get_logger(__name__)

# File to store saved credentials (encrypted)
SAVED_CREDENTIALS_FILE = APP_DATA_DIR / ".saved_credentials"

# Predefined security questions
SECURITY_QUESTIONS = [
    "What is the name of your first pet?",
    "What city were you born in?",
    "What is your mother's maiden name?",
    "What was the name of your elementary school?",
    "What is your favorite movie?",
    "What is your favorite book?",
    "What was the make of your first car?",
    "What is your favorite food?",
    "What street did you grow up on?",
    "What is your oldest sibling's middle name?",
]


class LoginDialog(QDialog):
    """Login/Registration dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._user: Optional[User] = None
        self._db = DatabaseQueries()
        self._encryption = EncryptionManager()

        # Initialize database
        init_db()

        self._setup_ui()
        self._setup_accessibility()
        self._load_saved_credentials()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle(f"{APP_NAME} - Login")
        self.setFixedSize(480, 850)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS.BACKGROUND};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        # Logo image
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = ASSETS_DIR / "logo.png"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            # Scale to reasonable size while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                150, 150,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(scaled_pixmap)
        else:
            logo_label.setText("Logo")
            logo_label.setStyleSheet(f"color: {COLORS.PRIMARY}; font-size: 48px;")
        layout.addWidget(logo_label)

        # App Title
        title = QLabel(APP_NAME)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {COLORS.PRIMARY};
            margin-bottom: 16px;
        """)
        layout.addWidget(title)

        subtitle = QLabel("Privacy-first PDF accessibility")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 12pt;")
        layout.addWidget(subtitle)

        # Tab widget for login/register
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                background-color: {COLORS.BACKGROUND};
                padding: 16px;
            }}
            QTabBar::tab {{
                padding: 8px 24px;
                margin-right: 4px;
                background-color: {COLORS.BACKGROUND_ALT};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-bottom: none;
                border-radius: 4px 4px 0 0;
                font-size: 12pt;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}
        """)

        # Login tab
        login_tab = QWidget()
        login_layout = QVBoxLayout(login_tab)
        login_layout.setSpacing(2)
        login_layout.setContentsMargins(16, 16, 16, 16)

        # Username field
        login_layout.addWidget(self._create_field_label("Username"))
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Username")
        self.login_username.setAccessibleName("Login username")
        self.login_username.setFixedHeight(40)
        login_layout.addWidget(self.login_username)
        login_layout.addSpacing(18)

        # Password field
        login_layout.addWidget(self._create_field_label("Password"))
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Password")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password.setAccessibleName("Login password")
        self.login_password.setFixedHeight(40)
        self.login_password.returnPressed.connect(self._login)
        login_layout.addWidget(self.login_password)
        login_layout.addSpacing(16)

        # Save password checkbox
        self.save_password_cb = QCheckBox("Save password (so you don't have to type it every time)")
        self.save_password_cb.setAccessibleName("Save password checkbox")
        login_layout.addWidget(self.save_password_cb)
        login_layout.addSpacing(12)

        # Login button
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self._login)
        login_btn.setStyleSheet(self._get_button_style(primary=True))
        login_btn.setFixedHeight(44)
        login_layout.addWidget(login_btn)
        login_layout.addSpacing(12)

        # Forgot password link
        forgot_password_btn = QPushButton("Forgot Password?")
        forgot_password_btn.clicked.connect(self._show_password_recovery)
        forgot_password_btn.setStyleSheet(f"""
            QPushButton {{
                background: none;
                border: none;
                color: {COLORS.PRIMARY_LIGHT};
                text-decoration: underline;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                color: {COLORS.PRIMARY};
            }}
        """)
        forgot_password_btn.setAccessibleName("Forgot password link")
        login_layout.addWidget(forgot_password_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        login_layout.addStretch()
        self.tabs.addTab(login_tab, "Login")

        # Register tab with scroll area for security questions
        register_tab = QWidget()
        register_scroll = QScrollArea()
        register_scroll.setWidgetResizable(True)
        register_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {COLORS.BACKGROUND};
            }}
            QScrollBar:vertical {{
                background-color: {COLORS.BACKGROUND_ALT};
                width: 12px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS.BORDER};
                border-radius: 6px;
                min-height: 20px;
            }}
        """)

        register_content = QWidget()
        register_layout = QVBoxLayout(register_content)
        register_layout.setSpacing(2)
        register_layout.setContentsMargins(16, 8, 16, 8)

        # Username field
        username_label = self._create_field_label("Username")
        register_layout.addWidget(username_label)
        self.reg_username = QLineEdit()
        self.reg_username.setPlaceholderText("Username")
        self.reg_username.setAccessibleName("Registration username")
        self.reg_username.setFixedHeight(40)
        register_layout.addWidget(self.reg_username)
        register_layout.addSpacing(12)

        # Email field
        email_label = self._create_field_label("Email (optional)")
        register_layout.addWidget(email_label)
        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Email (optional)")
        self.reg_email.setAccessibleName("Registration email")
        self.reg_email.setFixedHeight(40)
        register_layout.addWidget(self.reg_email)
        register_layout.addSpacing(12)

        # Password field
        password_label = self._create_field_label("Password")
        register_layout.addWidget(password_label)
        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Password")
        self.reg_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_password.setAccessibleName("Registration password")
        self.reg_password.setFixedHeight(40)
        register_layout.addWidget(self.reg_password)
        register_layout.addSpacing(12)

        # Confirm Password field
        confirm_label = self._create_field_label("Confirm Password")
        register_layout.addWidget(confirm_label)
        self.reg_confirm = QLineEdit()
        self.reg_confirm.setPlaceholderText("Confirm password")
        self.reg_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_confirm.setAccessibleName("Confirm password")
        self.reg_confirm.setFixedHeight(40)
        register_layout.addWidget(self.reg_confirm)
        register_layout.addSpacing(16)

        # Security Questions Section
        security_header = QLabel("Security Questions (for password recovery)")
        security_header.setStyleSheet(f"""
            font-weight: bold;
            font-size: 13pt;
            color: {COLORS.PRIMARY_LIGHT};
            padding-top: 8px;
            padding-bottom: 4px;
        """)
        register_layout.addWidget(security_header)

        security_note = QLabel("Answers are NOT case sensitive")
        security_note.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 10pt; font-style: italic;")
        register_layout.addWidget(security_note)
        register_layout.addSpacing(8)

        # Security Question 1
        self.sec_q1_combo = self._create_security_question_combo("Security question 1")
        register_layout.addWidget(self._create_field_label("Security Question 1"))
        register_layout.addWidget(self.sec_q1_combo)
        self.sec_a1_input = QLineEdit()
        self.sec_a1_input.setPlaceholderText("Your answer")
        self.sec_a1_input.setAccessibleName("Security answer 1")
        self.sec_a1_input.setFixedHeight(40)
        register_layout.addWidget(self.sec_a1_input)
        register_layout.addSpacing(10)

        # Security Question 2
        self.sec_q2_combo = self._create_security_question_combo("Security question 2")
        register_layout.addWidget(self._create_field_label("Security Question 2"))
        register_layout.addWidget(self.sec_q2_combo)
        self.sec_a2_input = QLineEdit()
        self.sec_a2_input.setPlaceholderText("Your answer")
        self.sec_a2_input.setAccessibleName("Security answer 2")
        self.sec_a2_input.setFixedHeight(40)
        register_layout.addWidget(self.sec_a2_input)
        register_layout.addSpacing(10)

        # Security Question 3
        self.sec_q3_combo = self._create_security_question_combo("Security question 3")
        register_layout.addWidget(self._create_field_label("Security Question 3"))
        register_layout.addWidget(self.sec_q3_combo)
        self.sec_a3_input = QLineEdit()
        self.sec_a3_input.setPlaceholderText("Your answer")
        self.sec_a3_input.setAccessibleName("Security answer 3")
        self.sec_a3_input.setFixedHeight(40)
        self.sec_a3_input.returnPressed.connect(self._register)
        register_layout.addWidget(self.sec_a3_input)
        register_layout.addSpacing(20)

        # Create Account button
        register_btn = QPushButton("Create Account")
        register_btn.clicked.connect(self._register)
        register_btn.setStyleSheet(self._get_button_style(primary=True))
        register_btn.setFixedHeight(44)
        register_layout.addWidget(register_btn)

        register_layout.addStretch()

        register_scroll.setWidget(register_content)
        register_tab_layout = QVBoxLayout(register_tab)
        register_tab_layout.setContentsMargins(0, 0, 0, 0)
        register_tab_layout.addWidget(register_scroll)
        self.tabs.addTab(register_tab, "Register")

        layout.addWidget(self.tabs)

        # Skip login button (for development)
        skip_layout = QHBoxLayout()
        skip_layout.addStretch()

        skip_btn = QPushButton("Continue without login")
        skip_btn.clicked.connect(self._skip_login)
        skip_btn.setStyleSheet(f"""
            QPushButton {{
                background: none;
                border: none;
                color: {COLORS.TEXT_SECONDARY};
                text-decoration: underline;
            }}
            QPushButton:hover {{
                color: {COLORS.PRIMARY};
            }}
        """)
        skip_layout.addWidget(skip_btn)

        layout.addLayout(skip_layout)

        # Apply input styles - dark theme with white text, larger boxes
        for input_widget in [
            self.login_username, self.login_password,
            self.reg_username, self.reg_email, self.reg_password, self.reg_confirm,
            self.sec_a1_input, self.sec_a2_input, self.sec_a3_input
        ]:
            input_widget.setMinimumHeight(44)
            input_widget.setFont(QFont("Arial", 14))
            input_widget.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {COLORS.INPUT_BG};
                    color: {COLORS.INPUT_TEXT};
                    border: 1px solid {COLORS.INPUT_BORDER};
                    border-radius: 6px;
                    padding: 12px 14px;
                    font-size: 14pt;
                    min-height: 24px;
                }}
                QLineEdit:focus {{
                    border: 2px solid {COLORS.INPUT_FOCUS};
                }}
                QLineEdit::placeholder {{
                    color: {COLORS.TEXT_SECONDARY};
                }}
            """)

        # Apply checkbox style
        self.save_password_cb.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
                spacing: 8px;
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
        """)

    def _create_field_label(self, text: str) -> QLabel:
        """Create a styled field label."""
        label = QLabel(text)
        label.setStyleSheet(f"""
            font-weight: bold;
            font-size: 12pt;
            color: {COLORS.TEXT_PRIMARY};
        """)
        return label

    def _create_security_question_combo(self, accessible_name: str) -> QComboBox:
        """Create a styled security question combo box."""
        combo = QComboBox()
        combo.addItems(SECURITY_QUESTIONS)
        combo.setAccessibleName(accessible_name)
        combo.setFixedHeight(40)
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12pt;
            }}
            QComboBox:focus {{
                border: 2px solid {COLORS.INPUT_FOCUS};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {COLORS.TEXT_PRIMARY};
                margin-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                selection-background-color: {COLORS.PRIMARY};
                selection-color: white;
                border: 1px solid {COLORS.INPUT_BORDER};
            }}
        """)
        return combo

    def _get_button_style(self, primary: bool = False) -> str:
        """Get button stylesheet."""
        if primary:
            return f"""
                QPushButton {{
                    background-color: {COLORS.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 12px;
                    font-size: 14px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.PRIMARY_DARK};
                }}
                QPushButton:focus {{
                    outline: 2px solid {COLORS.PRIMARY_LIGHT};
                    outline-offset: 2px;
                }}
            """
        return f"""
            QPushButton {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 12px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {COLORS.BACKGROUND_ALT};
            }}
        """

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self.setAccessibleName("Login dialog")
        self.setAccessibleDescription("Login or create an account to continue")

    def _login(self) -> None:
        """Handle login attempt."""
        username = self.login_username.text().strip()
        password = self.login_password.text()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password")
            return

        user = self._db.authenticate_user(username, password)
        if user:
            self._user = user
            logger.info(f"User logged in: {username}")

            # Save credentials if checkbox is checked
            if self.save_password_cb.isChecked():
                self._save_credentials(username, password)
            else:
                # Clear saved credentials if unchecked
                self._clear_saved_credentials()

            self.accept()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password")
            self.login_password.clear()
            self.login_password.setFocus()

    def _register(self) -> None:
        """Handle registration attempt."""
        username = self.reg_username.text().strip()
        email = self.reg_email.text().strip() or None
        password = self.reg_password.text()
        confirm = self.reg_confirm.text()

        # Get security questions and answers
        q1 = self.sec_q1_combo.currentText()
        a1 = self.sec_a1_input.text().strip()
        q2 = self.sec_q2_combo.currentText()
        a2 = self.sec_a2_input.text().strip()
        q3 = self.sec_q3_combo.currentText()
        a3 = self.sec_a3_input.text().strip()

        # Validation
        if not username:
            QMessageBox.warning(self, "Error", "Username is required")
            return

        if len(username) < 3:
            QMessageBox.warning(self, "Error", "Username must be at least 3 characters")
            return

        if not password:
            QMessageBox.warning(self, "Error", "Password is required")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "Error", "Password must be at least 6 characters")
            return

        if password != confirm:
            QMessageBox.warning(self, "Error", "Passwords do not match")
            return

        # Validate security questions
        if not all([a1, a2, a3]):
            QMessageBox.warning(self, "Error", "Please answer all three security questions")
            return

        # Check for duplicate questions
        if len({q1, q2, q3}) < 3:
            QMessageBox.warning(self, "Error", "Please select three different security questions")
            return

        # Check if username exists
        existing = self._db.get_user_by_username(username)
        if existing:
            QMessageBox.warning(self, "Error", "Username already exists")
            return

        try:
            user = self._db.create_user(username, password, email)

            # Set security questions
            self._db.set_security_questions(
                user.id, q1, a1, q2, a2, q3, a3
            )

            self._user = user
            logger.info(f"User registered: {username}")
            QMessageBox.information(
                self, "Success",
                "Account created successfully!\n\n"
                "Your security questions have been saved for password recovery."
            )
            self.accept()
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            QMessageBox.critical(self, "Error", f"Registration failed: {e}")

    def _skip_login(self) -> None:
        """Skip login (for development)."""
        # Create or get a default user
        default_user = self._db.get_user_by_username("default")
        if not default_user:
            default_user = self._db.create_user("default", "default123")

        self._user = default_user
        logger.info("Skipped login, using default user")
        self.accept()

    def get_user(self) -> Optional[User]:
        """Get the authenticated user."""
        return self._user

    def _save_credentials(self, username: str, password: str) -> None:
        """Save encrypted credentials for auto-login."""
        try:
            credentials = json.dumps({"username": username, "password": password})
            encrypted = self._encryption.encrypt_string(credentials)

            with open(SAVED_CREDENTIALS_FILE, "w") as f:
                f.write(encrypted)

            logger.info(f"Saved credentials for user: {username}")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def _load_saved_credentials(self) -> None:
        """Load saved credentials and populate fields."""
        try:
            if SAVED_CREDENTIALS_FILE.exists():
                with open(SAVED_CREDENTIALS_FILE, "r") as f:
                    encrypted = f.read()

                decrypted = self._encryption.decrypt_string(encrypted)
                credentials = json.loads(decrypted)

                self.login_username.setText(credentials.get("username", ""))
                self.login_password.setText(credentials.get("password", ""))
                self.save_password_cb.setChecked(True)

                logger.info("Loaded saved credentials")
        except Exception as e:
            logger.debug(f"No saved credentials loaded: {e}")
            # Remove corrupted file
            if SAVED_CREDENTIALS_FILE.exists():
                SAVED_CREDENTIALS_FILE.unlink()

    def _clear_saved_credentials(self) -> None:
        """Clear saved credentials."""
        try:
            if SAVED_CREDENTIALS_FILE.exists():
                SAVED_CREDENTIALS_FILE.unlink()
                logger.info("Cleared saved credentials")
        except Exception as e:
            logger.error(f"Failed to clear credentials: {e}")

    def _show_password_recovery(self) -> None:
        """Show the password recovery dialog."""
        dialog = PasswordRecoveryDialog(self._db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Password was reset, clear any saved credentials
            self._clear_saved_credentials()
            self.login_password.clear()
            QMessageBox.information(
                self, "Password Reset",
                "Your password has been reset successfully.\n"
                "Please log in with your new password."
            )


class PasswordRecoveryDialog(QDialog):
    """Dialog for recovering password using security questions."""

    def __init__(self, db: DatabaseQueries, parent=None):
        super().__init__(parent)
        self._db = db
        self._username = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Password Recovery")
        self.setFixedSize(450, 550)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS.BACKGROUND};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        # Title
        title = QLabel("Password Recovery")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {COLORS.PRIMARY};
            margin-bottom: 8px;
        """)
        layout.addWidget(title)

        # Instructions
        instructions = QLabel(
            "Enter your username and answer your security questions.\n"
            "Answers are NOT case sensitive."
        )
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 11pt;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        layout.addSpacing(8)

        # Username field
        layout.addWidget(self._create_label("Username"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setAccessibleName("Recovery username")
        self._apply_input_style(self.username_input)
        layout.addWidget(self.username_input)

        # Lookup button
        lookup_btn = QPushButton("Look Up Security Questions")
        lookup_btn.clicked.connect(self._lookup_questions)
        lookup_btn.setStyleSheet(self._get_button_style(primary=False))
        lookup_btn.setFixedHeight(40)
        layout.addWidget(lookup_btn)
        layout.addSpacing(8)

        # Security questions container (hidden initially)
        self.questions_container = QWidget()
        self.questions_container.setVisible(False)
        questions_layout = QVBoxLayout(self.questions_container)
        questions_layout.setContentsMargins(0, 0, 0, 0)
        questions_layout.setSpacing(8)

        # Question labels and answer fields
        self.q1_label = QLabel("")
        self.q1_label.setWordWrap(True)
        self.q1_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 11pt; font-weight: bold;")
        questions_layout.addWidget(self.q1_label)
        self.a1_input = QLineEdit()
        self.a1_input.setPlaceholderText("Your answer")
        self._apply_input_style(self.a1_input)
        questions_layout.addWidget(self.a1_input)
        questions_layout.addSpacing(8)

        self.q2_label = QLabel("")
        self.q2_label.setWordWrap(True)
        self.q2_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 11pt; font-weight: bold;")
        questions_layout.addWidget(self.q2_label)
        self.a2_input = QLineEdit()
        self.a2_input.setPlaceholderText("Your answer")
        self._apply_input_style(self.a2_input)
        questions_layout.addWidget(self.a2_input)
        questions_layout.addSpacing(8)

        self.q3_label = QLabel("")
        self.q3_label.setWordWrap(True)
        self.q3_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 11pt; font-weight: bold;")
        questions_layout.addWidget(self.q3_label)
        self.a3_input = QLineEdit()
        self.a3_input.setPlaceholderText("Your answer")
        self._apply_input_style(self.a3_input)
        questions_layout.addWidget(self.a3_input)

        layout.addWidget(self.questions_container)

        # New password container (hidden initially)
        self.password_container = QWidget()
        self.password_container.setVisible(False)
        password_layout = QVBoxLayout(self.password_container)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(8)

        password_layout.addWidget(self._create_label("New Password"))
        self.new_password = QLineEdit()
        self.new_password.setPlaceholderText("Enter new password (min 6 characters)")
        self.new_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._apply_input_style(self.new_password)
        password_layout.addWidget(self.new_password)

        password_layout.addWidget(self._create_label("Confirm New Password"))
        self.confirm_password = QLineEdit()
        self.confirm_password.setPlaceholderText("Confirm new password")
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._apply_input_style(self.confirm_password)
        password_layout.addWidget(self.confirm_password)

        layout.addWidget(self.password_container)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(self._get_button_style(primary=False))
        cancel_btn.setFixedHeight(44)
        button_layout.addWidget(cancel_btn)

        self.verify_btn = QPushButton("Verify Answers")
        self.verify_btn.clicked.connect(self._verify_answers)
        self.verify_btn.setStyleSheet(self._get_button_style(primary=True))
        self.verify_btn.setFixedHeight(44)
        self.verify_btn.setVisible(False)
        button_layout.addWidget(self.verify_btn)

        self.reset_btn = QPushButton("Reset Password")
        self.reset_btn.clicked.connect(self._reset_password)
        self.reset_btn.setStyleSheet(self._get_button_style(primary=True))
        self.reset_btn.setFixedHeight(44)
        self.reset_btn.setVisible(False)
        button_layout.addWidget(self.reset_btn)

        layout.addLayout(button_layout)

    def _create_label(self, text: str) -> QLabel:
        """Create a styled label."""
        label = QLabel(text)
        label.setStyleSheet(f"font-weight: bold; font-size: 11pt; color: {COLORS.TEXT_PRIMARY};")
        return label

    def _apply_input_style(self, widget: QLineEdit) -> None:
        """Apply input field styling."""
        widget.setFixedHeight(40)
        widget.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12pt;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS.INPUT_FOCUS};
            }}
        """)

    def _get_button_style(self, primary: bool = False) -> str:
        """Get button stylesheet."""
        if primary:
            return f"""
                QPushButton {{
                    background-color: {COLORS.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 12px;
                    font-size: 13px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.PRIMARY_DARK};
                }}
            """
        return f"""
            QPushButton {{
                background-color: {COLORS.BACKGROUND_ALT};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 12px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {COLORS.SURFACE};
            }}
        """

    def _lookup_questions(self) -> None:
        """Look up security questions for the username."""
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "Error", "Please enter your username")
            return

        # Check if user exists and has security questions
        if not self._db.has_security_questions(username):
            QMessageBox.warning(
                self, "Error",
                "Username not found or no security questions set up.\n\n"
                "If you don't have security questions, please contact support."
            )
            return

        # Get security questions
        q1, q2, q3 = self._db.get_security_questions(username)
        if not all([q1, q2, q3]):
            QMessageBox.warning(self, "Error", "Could not retrieve security questions")
            return

        self._username = username
        self.q1_label.setText(f"1. {q1}")
        self.q2_label.setText(f"2. {q2}")
        self.q3_label.setText(f"3. {q3}")

        # Show questions and verify button
        self.questions_container.setVisible(True)
        self.verify_btn.setVisible(True)
        self.username_input.setEnabled(False)

    def _verify_answers(self) -> None:
        """Verify the security question answers."""
        a1 = self.a1_input.text().strip()
        a2 = self.a2_input.text().strip()
        a3 = self.a3_input.text().strip()

        if not all([a1, a2, a3]):
            QMessageBox.warning(self, "Error", "Please answer all security questions")
            return

        # Verify answers
        if self._db.verify_security_answers(self._username, a1, a2, a3):
            # Show password reset fields
            self.password_container.setVisible(True)
            self.reset_btn.setVisible(True)
            self.verify_btn.setVisible(False)

            # Disable answer fields
            self.a1_input.setEnabled(False)
            self.a2_input.setEnabled(False)
            self.a3_input.setEnabled(False)

            QMessageBox.information(
                self, "Verified",
                "Security answers verified!\n"
                "Please enter your new password."
            )
        else:
            QMessageBox.warning(
                self, "Verification Failed",
                "One or more answers are incorrect.\n"
                "Please try again."
            )

    def _reset_password(self) -> None:
        """Reset the password after verification."""
        new_pass = self.new_password.text()
        confirm_pass = self.confirm_password.text()

        if not new_pass:
            QMessageBox.warning(self, "Error", "Please enter a new password")
            return

        if len(new_pass) < 6:
            QMessageBox.warning(self, "Error", "Password must be at least 6 characters")
            return

        if new_pass != confirm_pass:
            QMessageBox.warning(self, "Error", "Passwords do not match")
            return

        # Reset the password
        user = self._db.get_user_by_username(self._username)
        if user and self._db.update_password(user.id, new_pass):
            logger.info(f"Password reset for user: {self._username}")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to reset password")
