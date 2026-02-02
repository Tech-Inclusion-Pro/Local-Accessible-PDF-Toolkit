"""
Main application window for Accessible PDF Toolkit.
"""

from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QToolBar,
    QStatusBar,
    QMenuBar,
    QMenu,
    QFileDialog,
    QMessageBox,
    QLabel,
    QSplitter,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QFont

from ..utils.constants import (
    APP_NAME,
    APP_VERSION,
    COLORS,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    SUPPORTED_INPUT_FORMATS,
)
from ..utils.logger import get_logger
from ..database.models import User, init_db
from .pdf_viewer import PDFViewerPanel
from .settings import SettingsPanel
from .dashboard_panel import DashboardPanel

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    # Signals
    file_opened = pyqtSignal(str)
    file_saved = pyqtSignal(str)
    user_logged_in = pyqtSignal(object)
    user_logged_out = pyqtSignal()

    def __init__(self, user: Optional[User] = None):
        super().__init__()

        self.current_user = user
        self.current_file: Optional[Path] = None

        self._setup_ui()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_shortcuts()
        self._apply_styles()
        self._setup_accessibility()

        logger.info("Main window initialized")

    def _setup_ui(self) -> None:
        """Set up the main UI layout."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(800, 600)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Tab widget for main navigation
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.West)
        self.tab_widget.setDocumentMode(True)

        # Create tab pages
        self.dashboard_tab = DashboardPanel()
        self.pdf_viewer_tab = PDFViewerPanel()
        self.settings_tab = SettingsPanel()

        # Connect dashboard signals to open files in PDF viewer
        self.dashboard_tab.file_selected.connect(self._open_file_in_viewer)
        self.dashboard_tab.file_dropped.connect(self._open_file_in_viewer)

        # Connect PDF viewer file_dropped signal to add to recent files
        self.pdf_viewer_tab.file_dropped.connect(
            lambda path: self.dashboard_tab.add_recent_file(path)
        )

        # Add tabs (3 tabs: Dashboard, PDF Viewer, Settings)
        self.tab_widget.addTab(self.dashboard_tab, "Dashboard")
        self.tab_widget.addTab(self.pdf_viewer_tab, "PDF Viewer")
        self.tab_widget.addTab(self.settings_tab, "Settings")

        main_layout.addWidget(self.tab_widget)

    def _setup_menu_bar(self) -> None:
        """Set up the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_action = QAction("&Open PDF...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        open_viewer_action = QAction("Open in PDF &Viewer...", self)
        open_viewer_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        open_viewer_action.triggered.connect(self.open_in_pdf_viewer)
        file_menu.addAction(open_viewer_action)

        file_menu.addSeparator()

        export_html_action = QAction("&Export to HTML...", self)
        export_html_action.setShortcut(QKeySequence("Ctrl+E"))
        export_html_action.triggered.connect(self.export_html)
        file_menu.addAction(export_html_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        preferences_action = QAction("&Preferences...", self)
        preferences_action.setShortcut(QKeySequence.StandardKey.Preferences)
        preferences_action.triggered.connect(self.show_settings)
        edit_menu.addAction(preferences_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        dashboard_action = QAction("&Dashboard", self)
        dashboard_action.setShortcut(QKeySequence("Ctrl+1"))
        dashboard_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(0))
        view_menu.addAction(dashboard_action)

        viewer_action = QAction("PDF &Viewer", self)
        viewer_action.setShortcut(QKeySequence("Ctrl+2"))
        viewer_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(1))
        view_menu.addAction(viewer_action)

        settings_action = QAction("&Settings", self)
        settings_action.setShortcut(QKeySequence("Ctrl+3"))
        settings_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(2))
        view_menu.addAction(settings_action)

        view_menu.addSeparator()

        high_contrast_action = QAction("&High Contrast Mode", self)
        high_contrast_action.setCheckable(True)
        high_contrast_action.triggered.connect(self.toggle_high_contrast)
        view_menu.addAction(high_contrast_action)
        self.high_contrast_action = high_contrast_action

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        validate_action = QAction("&Validate WCAG...", self)
        validate_action.setShortcut(QKeySequence("Ctrl+Shift+V"))
        validate_action.triggered.connect(self.validate_wcag)
        tools_menu.addAction(validate_action)

        ai_suggest_action = QAction("&AI Suggestions", self)
        ai_suggest_action.setShortcut(QKeySequence("Ctrl+Space"))
        ai_suggest_action.triggered.connect(self.get_ai_suggestions)
        tools_menu.addAction(ai_suggest_action)

        tools_menu.addSeparator()

        batch_action = QAction("&Batch Process...", self)
        batch_action.triggered.connect(self.show_batch_dialog)
        tools_menu.addAction(batch_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        docs_action = QAction("&Documentation", self)
        docs_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        help_menu.addAction(docs_action)

        keyboard_action = QAction("&Keyboard Shortcuts", self)
        keyboard_action.triggered.connect(self.show_keyboard_shortcuts)
        help_menu.addAction(keyboard_action)

    def _setup_toolbar(self) -> None:
        """Set up the main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # Open button
        open_btn = QAction("Open", self)
        open_btn.setToolTip("Open PDF file (Ctrl+O)")
        open_btn.triggered.connect(self.open_file_dialog)
        toolbar.addAction(open_btn)

        # Save button
        save_btn = QAction("Save", self)
        save_btn.setToolTip("Save changes (Ctrl+S)")
        save_btn.triggered.connect(self.save_file)
        toolbar.addAction(save_btn)

        toolbar.addSeparator()

        # Validate button
        validate_btn = QAction("Validate", self)
        validate_btn.setToolTip("Validate WCAG compliance (Ctrl+Shift+V)")
        validate_btn.triggered.connect(self.validate_wcag)
        toolbar.addAction(validate_btn)

        # AI button
        ai_btn = QAction("AI Assist", self)
        ai_btn.setToolTip("Get AI suggestions (Ctrl+Space)")
        ai_btn.triggered.connect(self.get_ai_suggestions)
        toolbar.addAction(ai_btn)

        toolbar.addSeparator()

        # Export button
        export_btn = QAction("Export HTML", self)
        export_btn.setToolTip("Export to accessible HTML (Ctrl+E)")
        export_btn.triggered.connect(self.export_html)
        toolbar.addAction(export_btn)

    def _setup_status_bar(self) -> None:
        """Set up the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # File status label
        self.file_status = QLabel("No file loaded")
        self.status_bar.addWidget(self.file_status)

        # Compliance status label
        self.compliance_status = QLabel("")
        self.status_bar.addPermanentWidget(self.compliance_status)

        # User status label
        self.user_status = QLabel("")
        self.status_bar.addPermanentWidget(self.user_status)
        self._update_user_status()

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        # Tab navigation (3 tabs: Dashboard, PDF Viewer, Settings)
        for i in range(3):
            shortcut_key = f"Ctrl+{i + 1}"
            action = QAction(self)
            action.setShortcut(QKeySequence(shortcut_key))
            action.triggered.connect(lambda checked, idx=i: self.tab_widget.setCurrentIndex(idx))
            self.addAction(action)

    def _setup_accessibility(self) -> None:
        """Configure accessibility features."""
        # Set accessible names for main components
        self.tab_widget.setAccessibleName("Main navigation tabs")
        self.tab_widget.setAccessibleDescription("Use Ctrl+1 through Ctrl+3 to switch tabs")

        # Dashboard tab
        self.dashboard_tab.setAccessibleName("Dashboard")
        self.dashboard_tab.setAccessibleDescription("View files, courses, and compliance statistics")

        # PDF Viewer tab
        self.pdf_viewer_tab.setAccessibleName("PDF Viewer")
        self.pdf_viewer_tab.setAccessibleDescription("View PDFs with AI accessibility suggestions")

        # Settings tab
        self.settings_tab.setAccessibleName("Settings")
        self.settings_tab.setAccessibleDescription("Configure application preferences")

        # Set focus policy for keyboard navigation
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _apply_styles(self) -> None:
        """Apply application styles - Dark theme with white text."""
        self.setStyleSheet(f"""
            * {{
                font-size: 12pt;
            }}

            QMainWindow {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
            }}

            QWidget {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}

            QLabel {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}

            QTabWidget::pane {{
                border: 1px solid {COLORS.BORDER};
                background-color: {COLORS.BACKGROUND};
            }}

            QTabBar::tab {{
                padding: 12px 20px;
                margin: 2px;
                background-color: {COLORS.SURFACE};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}

            QTabBar::tab:selected {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}

            QTabBar::tab:hover:!selected {{
                background-color: {COLORS.PRIMARY_LIGHT};
                color: white;
            }}

            QTabBar::tab:focus {{
                outline: 2px solid {COLORS.PRIMARY};
                outline-offset: 2px;
            }}

            QToolBar {{
                background-color: {COLORS.SURFACE};
                border-bottom: 1px solid {COLORS.BORDER};
                padding: 4px;
                spacing: 4px;
            }}

            QToolBar QToolButton {{
                padding: 8px 12px;
                border-radius: 4px;
                border: none;
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}

            QToolBar QToolButton:hover {{
                background-color: {COLORS.PRIMARY_LIGHT};
                color: white;
            }}

            QToolBar QToolButton:focus {{
                outline: 2px solid {COLORS.PRIMARY};
                outline-offset: 2px;
            }}

            QStatusBar {{
                background-color: {COLORS.SURFACE};
                border-top: 1px solid {COLORS.BORDER};
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}

            QStatusBar QLabel {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}

            QMenuBar {{
                background-color: {COLORS.BACKGROUND};
                border-bottom: 1px solid {COLORS.BORDER};
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}

            QMenuBar::item {{
                color: {COLORS.TEXT_PRIMARY};
                padding: 6px 12px;
            }}

            QMenuBar::item:selected {{
                background-color: {COLORS.PRIMARY_LIGHT};
                color: white;
            }}

            QMenu {{
                background-color: {COLORS.SURFACE};
                border: 1px solid {COLORS.BORDER};
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}

            QMenu::item {{
                color: {COLORS.TEXT_PRIMARY};
                padding: 8px 24px;
            }}

            QMenu::item:selected {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}

            QLineEdit {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}

            QLineEdit:focus {{
                border: 2px solid {COLORS.INPUT_FOCUS};
            }}

            QTextEdit {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}

            QComboBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}

            QComboBox::drop-down {{
                border: none;
            }}

            QComboBox QAbstractItemView {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                selection-background-color: {COLORS.PRIMARY};
                selection-color: white;
            }}

            QSpinBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}

            QPushButton {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12pt;
            }}

            QPushButton:hover {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}

            QCheckBox {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
                spacing: 8px;
            }}

            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}

            QGroupBox {{
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
                font-size: 12pt;
            }}

            QGroupBox::title {{
                color: {COLORS.TEXT_PRIMARY};
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}

            QScrollArea {{
                background-color: {COLORS.BACKGROUND};
                border: none;
            }}

            QScrollBar:vertical {{
                background-color: {COLORS.BACKGROUND};
                width: 12px;
            }}

            QScrollBar::handle:vertical {{
                background-color: {COLORS.BORDER};
                border-radius: 6px;
                min-height: 20px;
            }}

            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS.PRIMARY};
            }}

            QTableWidget {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                font-size: 12pt;
            }}

            QTableWidget::item {{
                color: {COLORS.TEXT_PRIMARY};
                padding: 8px;
            }}

            QTableWidget::item:selected {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}

            QHeaderView::section {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                padding: 8px;
                font-size: 12pt;
            }}

            QTreeWidget {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                font-size: 12pt;
            }}

            QTreeWidget::item {{
                color: {COLORS.TEXT_PRIMARY};
                padding: 4px;
            }}

            QTreeWidget::item:selected {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}
        """)

    def _update_user_status(self) -> None:
        """Update the user status display."""
        if self.current_user:
            self.user_status.setText(f"User: {self.current_user.username}")
        else:
            self.user_status.setText("Not logged in")

    # ==================== File Operations ====================

    def open_file_dialog(self) -> None:
        """Show file open dialog."""
        file_filter = "PDF Files (*.pdf);;All Files (*.*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF File",
            "",
            file_filter,
        )

        if file_path:
            self.open_file(Path(file_path))

    def open_file(self, file_path: Path, open_in_viewer: bool = False) -> bool:
        """
        Open a PDF file.

        Args:
            file_path: Path to the PDF file
            open_in_viewer: If True, open in PDF Viewer tab

        Returns:
            True if successful
        """
        if not file_path.exists():
            QMessageBox.warning(self, "Error", f"File not found: {file_path}")
            return False

        if file_path.suffix.lower() not in SUPPORTED_INPUT_FORMATS:
            QMessageBox.warning(self, "Error", "Unsupported file format")
            return False

        self.current_file = file_path
        self.file_status.setText(f"File: {file_path.name}")
        self.file_opened.emit(str(file_path))
        self.status_bar.showMessage(f"Opened: {file_path.name}", 3000)

        # Optionally open in PDF Viewer
        if open_in_viewer:
            self.tab_widget.setCurrentIndex(1)  # PDF Viewer is now tab index 1
            self.pdf_viewer_tab.load_file(file_path)

        logger.info(f"Opened file: {file_path}")
        return True

    def save_file(self) -> bool:
        """Save the current file."""
        if not self.current_file:
            return self.save_file_as()

        # Emit signal for saving
        self.file_saved.emit(str(self.current_file))
        self.status_bar.showMessage(f"Saved: {self.current_file.name}", 3000)
        return True

    def save_file_as(self) -> bool:
        """Show save as dialog."""
        file_filter = "PDF Files (*.pdf)"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF File",
            "",
            file_filter,
        )

        if file_path:
            self.current_file = Path(file_path)
            return self.save_file()
        return False

    def export_html(self) -> None:
        """Export to HTML."""
        if not self.current_file:
            QMessageBox.information(self, "No File", "Please open a PDF file first")
            return

        file_filter = "HTML Files (*.html)"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to HTML",
            str(self.current_file.with_suffix(".html")),
            file_filter,
        )

        if file_path:
            self.status_bar.showMessage(f"Exporting to: {file_path}", 3000)
            # TODO: Implement HTML export functionality
            QMessageBox.information(
                self,
                "Export",
                f"HTML export will be saved to:\n{file_path}"
            )

    # ==================== Tool Actions ====================

    def validate_wcag(self) -> None:
        """Run WCAG validation."""
        if not self.current_file:
            QMessageBox.information(self, "No File", "Please open a PDF file first")
            return

        self.status_bar.showMessage("Validating WCAG compliance...", 0)
        # Validation will be handled by the tag editor or core module
        logger.info("WCAG validation triggered")

    def get_ai_suggestions(self) -> None:
        """Get AI-powered suggestions."""
        if not self.current_file:
            QMessageBox.information(self, "No File", "Please open a PDF file first")
            return

        self.status_bar.showMessage("Getting AI suggestions...", 0)
        logger.info("AI suggestions triggered")

    def show_batch_dialog(self) -> None:
        """Show batch processing dialog."""
        QMessageBox.information(
            self,
            "Batch Processing",
            "Batch processing allows you to process multiple PDFs at once.\n\n"
            "Configure batch limit in Settings (1-10 files).",
        )

    # ==================== View Actions ====================

    def toggle_high_contrast(self, enabled: bool) -> None:
        """Toggle high contrast mode."""
        if enabled:
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-color: {COLORS.HC_BACKGROUND};
                    color: {COLORS.HC_TEXT};
                }}

                QWidget {{
                    background-color: {COLORS.HC_BACKGROUND};
                    color: {COLORS.HC_TEXT};
                }}

                QTabBar::tab {{
                    background-color: {COLORS.HC_BACKGROUND};
                    color: {COLORS.HC_TEXT};
                    border: 2px solid {COLORS.HC_TEXT};
                }}

                QTabBar::tab:selected {{
                    background-color: {COLORS.HC_TEXT};
                    color: {COLORS.HC_BACKGROUND};
                }}

                *:focus {{
                    outline: 3px solid {COLORS.HC_FOCUS};
                }}
            """)
        else:
            self._apply_styles()

        logger.info(f"High contrast mode: {enabled}")

    def show_settings(self) -> None:
        """Switch to settings tab."""
        self.tab_widget.setCurrentIndex(2)  # Settings is now tab index 2

    def open_in_pdf_viewer(self) -> None:
        """Open a PDF in the PDF Viewer tab."""
        file_filter = "PDF Files (*.pdf);;All Files (*.*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF in Viewer",
            "",
            file_filter,
        )

        if file_path:
            self._open_file_in_viewer(file_path)

    def _open_file_in_viewer(self, file_path: str) -> None:
        """Open a file in the PDF Viewer tab (internal helper)."""
        path = Path(file_path)
        if not path.exists():
            QMessageBox.warning(self, "Error", f"File not found: {file_path}")
            return

        # Switch to PDF Viewer tab
        self.tab_widget.setCurrentIndex(1)  # PDF Viewer is now tab index 1
        # Load the file
        self.pdf_viewer_tab.load_file(path)
        self.current_file = path
        self.file_status.setText(f"File: {path.name}")
        self.file_opened.emit(str(file_path))
        # Add to dashboard recent files
        self.dashboard_tab.add_recent_file(str(path))
        logger.info(f"Opened file in viewer: {file_path}")

    # ==================== Help Actions ====================

    def show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h2>{APP_NAME}</h2>"
            f"<p>Version {APP_VERSION}</p>"
            "<p>A privacy-first desktop application for making PDFs "
            "WCAG 2.1/2.2 compliant using local AI models.</p>"
            "<p>Designed for educators needing FERPA/HIPAA compliance.</p>"
            "<hr>"
            "<p><b>License:</b> MIT</p>",
        )

    def show_keyboard_shortcuts(self) -> None:
        """Show keyboard shortcuts dialog."""
        shortcuts = """
<h3>Keyboard Shortcuts</h3>

<b>File Operations</b>
<table>
<tr><td>Ctrl+O</td><td>Open PDF</td></tr>
<tr><td>Ctrl+S</td><td>Save</td></tr>
<tr><td>Ctrl+Shift+S</td><td>Save As</td></tr>
</table>

<b>Navigation</b>
<table>
<tr><td>Ctrl+1</td><td>Dashboard</td></tr>
<tr><td>Ctrl+2</td><td>PDF Viewer</td></tr>
<tr><td>Ctrl+3</td><td>Settings</td></tr>
<tr><td>Tab</td><td>Next element</td></tr>
<tr><td>Shift+Tab</td><td>Previous element</td></tr>
</table>

<b>Tools</b>
<table>
<tr><td>Ctrl+Shift+V</td><td>Validate WCAG</td></tr>
<tr><td>Ctrl+Space</td><td>AI Suggestions</td></tr>
</table>
"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Keyboard Shortcuts")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(shortcuts)
        msg.exec()

    # ==================== Event Handlers ====================

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        # Check for unsaved changes
        reply = QMessageBox.question(
            self,
            "Exit",
            "Are you sure you want to exit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            logger.info("Application closing")
            event.accept()
        else:
            event.ignore()

    def set_user(self, user: User) -> None:
        """Set the current user."""
        self.current_user = user
        self._update_user_status()
        self.user_logged_in.emit(user)
        logger.info(f"User logged in: {user.username}")

    def logout(self) -> None:
        """Log out the current user."""
        self.current_user = None
        self._update_user_status()
        self.user_logged_out.emit()
        logger.info("User logged out")
