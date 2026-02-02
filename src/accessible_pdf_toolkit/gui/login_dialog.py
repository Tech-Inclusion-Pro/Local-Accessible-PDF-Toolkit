"""
Login dialog for user authentication.
"""

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
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

from ..utils.constants import COLORS, APP_NAME, ASSETS_DIR
from ..utils.logger import get_logger
from ..database.models import User, init_db
from ..database.queries import DatabaseQueries

logger = get_logger(__name__)


class LoginDialog(QDialog):
    """Login/Registration dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._user: Optional[User] = None
        self._db = DatabaseQueries()

        # Initialize database
        init_db()

        self._setup_ui()
        self._setup_accessibility()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle(f"{APP_NAME} - Login")
        self.setFixedSize(450, 750)
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

        # Remember me checkbox
        self.remember_cb = QCheckBox("Remember me")
        login_layout.addWidget(self.remember_cb)
        login_layout.addSpacing(20)

        # Login button
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self._login)
        login_btn.setStyleSheet(self._get_button_style(primary=True))
        login_btn.setFixedHeight(44)
        login_layout.addWidget(login_btn)

        login_layout.addStretch()
        self.tabs.addTab(login_tab, "Login")

        # Register tab
        register_tab = QWidget()
        register_layout = QVBoxLayout(register_tab)
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
        register_layout.addSpacing(18)

        # Email field
        email_label = self._create_field_label("Email (optional)")
        register_layout.addWidget(email_label)
        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Email (optional)")
        self.reg_email.setAccessibleName("Registration email")
        self.reg_email.setFixedHeight(40)
        register_layout.addWidget(self.reg_email)
        register_layout.addSpacing(18)

        # Password field
        password_label = self._create_field_label("Password")
        register_layout.addWidget(password_label)
        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Password")
        self.reg_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_password.setAccessibleName("Registration password")
        self.reg_password.setFixedHeight(40)
        register_layout.addWidget(self.reg_password)
        register_layout.addSpacing(18)

        # Confirm Password field
        confirm_label = self._create_field_label("Confirm Password")
        register_layout.addWidget(confirm_label)
        self.reg_confirm = QLineEdit()
        self.reg_confirm.setPlaceholderText("Confirm password")
        self.reg_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_confirm.setAccessibleName("Confirm password")
        self.reg_confirm.setFixedHeight(40)
        self.reg_confirm.returnPressed.connect(self._register)
        register_layout.addWidget(self.reg_confirm)
        register_layout.addSpacing(24)

        # Create Account button
        register_btn = QPushButton("Create Account")
        register_btn.clicked.connect(self._register)
        register_btn.setStyleSheet(self._get_button_style(primary=True))
        register_btn.setFixedHeight(44)
        register_layout.addWidget(register_btn)

        register_layout.addStretch()
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
            self.reg_username, self.reg_email, self.reg_password, self.reg_confirm
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
        self.remember_cb.setStyleSheet(f"""
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

        # Check if username exists
        existing = self._db.get_user_by_username(username)
        if existing:
            QMessageBox.warning(self, "Error", "Username already exists")
            return

        try:
            user = self._db.create_user(username, password, email)
            self._user = user
            logger.info(f"User registered: {username}")
            QMessageBox.information(self, "Success", "Account created successfully!")
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
