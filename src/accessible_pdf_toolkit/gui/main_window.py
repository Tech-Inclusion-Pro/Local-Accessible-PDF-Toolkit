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
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QFont, QCursor, QPixmap, QColor, QPainter

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
from ..core.pdf_handler import PDFHandler
from ..core.html_generator import HTMLGenerator, HTMLOptions
from ..core.report_generator import ComplianceReportGenerator
from .pdf_viewer import PDFViewerPanel
from .settings import SettingsPanel, ToggleSwitch
from .dashboard_panel import DashboardPanel
from .dialogs.batch_dialog import BatchDialog
from .dialogs.guided_fix_wizard import GuidedFixWizard
from .dialogs.show_me_walkthrough import ShowMeWalkthroughDialog, WALKTHROUGHS

logger = get_logger(__name__)


class CursorTrailOverlay(QWidget):
    """Transparent overlay that draws a fading trail of dots behind the cursor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self._trail_points = []  # list of (QPoint, float timestamp)
        self._max_age = 0.4  # seconds before dots fade out
        self._max_points = 20
        self._dot_size = 10
        self._color = QColor(COLORS.PRIMARY)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_trail)

    def _update_trail(self):
        import time
        now = time.time()
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)
        if self.rect().contains(local_pos):
            if not self._trail_points:
                self._trail_points.append((local_pos, now))
            else:
                last = self._trail_points[-1][0]
                if abs(local_pos.x() - last.x()) + abs(local_pos.y() - last.y()) > 3:
                    self._trail_points.append((local_pos, now))
        self._trail_points = [(p, t) for p, t in self._trail_points if now - t < self._max_age]
        if len(self._trail_points) > self._max_points:
            self._trail_points = self._trail_points[-self._max_points:]
        self.update()

    def paintEvent(self, event):
        import time
        now = time.time()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for point, timestamp in self._trail_points:
            age = now - timestamp
            opacity = max(0.0, 1.0 - age / self._max_age)
            radius = max(1, int(self._dot_size * opacity / 2))
            color = QColor(self._color)
            color.setAlphaF(opacity * 0.6)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(point, radius, radius)
        painter.end()

    def start(self):
        self.show()
        self.raise_()
        self._timer.start(33)  # ~30fps

    def stop(self):
        self._timer.stop()
        self._trail_points.clear()
        self.hide()


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
        self._cursor_trail: Optional[CursorTrailOverlay] = None

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

        # Persist compliance results to dashboard whenever validation completes
        self.pdf_viewer_tab.validation_complete.connect(self._persist_compliance_to_dashboard)

        # Connect settings changes to apply accessibility preferences
        self.settings_tab.settings_changed.connect(self._on_settings_changed)
        # Connect live preview (same handler, triggered on toggle/change)
        self.settings_tab.preview_requested.connect(self._on_settings_changed)

        # Add tabs (3 tabs: Dashboard, PDF Viewer, Settings)
        self.tab_widget.addTab(self.dashboard_tab, "Dashboard")
        self.tab_widget.addTab(self.pdf_viewer_tab, "PDF Viewer")
        self.tab_widget.addTab(self.settings_tab, "Settings")

        # Refresh dashboard when switching back to it
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

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

        tools_menu.addSeparator()

        report_action = QAction("Generate Compliance &Report...", self)
        report_action.triggered.connect(self.generate_compliance_report)
        tools_menu.addAction(report_action)

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
        """Export to accessible HTML."""
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

        if not file_path:
            return

        handler = PDFHandler()
        try:
            self.status_bar.showMessage("Exporting to HTML...", 0)

            document = handler.open(self.current_file)
            if not document:
                QMessageBox.warning(self, "Error", "Failed to open PDF for export")
                return

            options = HTMLOptions(
                theme="brand",
                include_styles=True,
                include_toc=True,
                responsive=True,
                include_images=True,
                add_aria=True,
                language=document.language or "en",
            )
            generator = HTMLGenerator(options)
            result = generator.generate(document)

            output_path = Path(file_path)
            if generator.save(result, output_path):
                self.status_bar.showMessage(f"Exported: {output_path.name}", 5000)
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"HTML exported successfully to:\n{file_path}",
                )
            else:
                QMessageBox.warning(self, "Error", "Failed to save HTML file")

        except Exception as e:
            logger.error(f"HTML export failed: {e}")
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export HTML:\n{e}",
            )
        finally:
            handler.close()

    # ==================== Tool Actions ====================

    def validate_wcag(self) -> None:
        """Run WCAG validation."""
        if not self.current_file:
            QMessageBox.information(self, "No File", "Please open a PDF file first")
            return

        # Switch to PDF Viewer tab
        self.tab_widget.setCurrentIndex(1)

        # Ensure file is loaded in viewer
        if not self.pdf_viewer_tab.current_document:
            self.pdf_viewer_tab.load_file(self.current_file)

        self.status_bar.showMessage("Validating WCAG compliance...", 0)

        result = self.pdf_viewer_tab.run_validation()

        if result is None:
            self.status_bar.showMessage("Validation failed - no document loaded", 5000)
            return

        # Update status bar
        if result.is_compliant:
            self.compliance_status.setText(
                f"WCAG {result.level.value}: Compliant ({result.score:.0f}%)"
            )
            self.compliance_status.setStyleSheet(f"color: #22C55E; font-size: 12pt;")
        else:
            self.compliance_status.setText(
                f"WCAG {result.level.value}: Non-compliant ({result.score:.0f}%)"
            )
            self.compliance_status.setStyleSheet(f"color: #EF4444; font-size: 12pt;")

        self.status_bar.showMessage(
            f"Validation complete: {result.summary['errors']} errors, "
            f"{result.summary['warnings']} warnings",
            5000,
        )

        # Show result dialog with "Show Me" option when there are issues
        if result.is_compliant and not result.issues:
            QMessageBox.information(
                self,
                "WCAG Validation",
                f"Document is WCAG {result.level.value} compliant!\n\n"
                f"Score: {result.score:.0f}%\n"
                f"Warnings: {result.summary['warnings']}",
            )
        elif result.issues:
            msg = QMessageBox(self)
            msg.setWindowTitle("WCAG Validation")
            if result.is_compliant:
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setText(
                    f"Document is WCAG {result.level.value} compliant!\n\n"
                    f"Score: {result.score:.0f}%\n"
                    f"Warnings: {result.summary['warnings']}\n\n"
                    f"There are {len(result.issues)} items to review."
                )
            else:
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.setText(
                    f"Document is NOT WCAG {result.level.value} compliant.\n\n"
                    f"Score: {result.score:.0f}%\n"
                    f"Errors: {result.summary['errors']}\n"
                    f"Warnings: {result.summary['warnings']}\n\n"
                    f"There are {len(result.issues)} issues to address."
                )
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            auto_fix_btn = msg.addButton("Auto-Fix", QMessageBox.ButtonRole.ActionRole)
            show_me_btn = msg.addButton("Show Me", QMessageBox.ButtonRole.ActionRole)
            msg.exec()

            clicked = msg.clickedButton()
            if clicked == auto_fix_btn:
                new_result = self.pdf_viewer_tab.auto_fix_wcag()
                if new_result:
                    result = new_result
                    # Update status bar with new score
                    if result.is_compliant:
                        self.compliance_status.setText(
                            f"WCAG {result.level.value}: Compliant ({result.score:.0f}%)"
                        )
                        self.compliance_status.setStyleSheet(f"color: #22C55E; font-size: 12pt;")
                    else:
                        self.compliance_status.setText(
                            f"WCAG {result.level.value}: Non-compliant ({result.score:.0f}%)"
                        )
                        self.compliance_status.setStyleSheet(f"color: #EF4444; font-size: 12pt;")
            elif clicked == show_me_btn:
                wizard = GuidedFixWizard(result.issues, parent=self)
                if self.pdf_viewer_tab.current_document:
                    viewer = self.pdf_viewer_tab._viewer
                    wizard.navigate_to_page.connect(viewer.go_to_page)
                wizard.inline_fix_applied.connect(self._on_wizard_inline_fix)
                wizard.open_walkthrough.connect(self._open_walkthrough_from_wizard)
                wizard.exec()

                # Re-validate after wizard closes to update the score
                new_result = self.pdf_viewer_tab.run_validation()
                if new_result:
                    result = new_result
                    # Save and persist so changes survive reopening
                    self.pdf_viewer_tab._save_and_persist(new_result)
                    if result.is_compliant:
                        self.compliance_status.setText(
                            f"WCAG {result.level.value}: Compliant ({result.score:.0f}%)"
                        )
                        self.compliance_status.setStyleSheet(f"color: #22C55E; font-size: 12pt;")
                    else:
                        self.compliance_status.setText(
                            f"WCAG {result.level.value}: Non-compliant ({result.score:.0f}%)"
                        )
                        self.compliance_status.setStyleSheet(f"color: #EF4444; font-size: 12pt;")
        else:
            QMessageBox.information(
                self,
                "WCAG Validation",
                f"Document is WCAG {result.level.value} compliant!\n\n"
                f"Score: {result.score:.0f}%",
            )

        logger.info(f"WCAG validation complete: score={result.score}")

        # Persist to dashboard
        self._persist_compliance_to_dashboard(result)

    def _persist_compliance_to_dashboard(self, result) -> None:
        """Save compliance score to the dashboard's recent files list."""
        if self.current_file:
            self.dashboard_tab.update_file_compliance(
                str(self.current_file),
                result.score,
                result.is_compliant,
            )

    def get_ai_suggestions(self) -> None:
        """Get AI-powered suggestions."""
        if not self.current_file:
            QMessageBox.information(self, "No File", "Please open a PDF file first")
            return

        # Switch to PDF Viewer tab
        self.tab_widget.setCurrentIndex(1)

        # Ensure file is loaded in viewer
        if not self.pdf_viewer_tab.current_document:
            self.pdf_viewer_tab.load_file(self.current_file)

        self.status_bar.showMessage("Getting AI suggestions...", 0)
        self.pdf_viewer_tab.refresh_analysis()
        logger.info("AI suggestions triggered")

    def show_batch_dialog(self) -> None:
        """Show batch processing dialog."""
        dialog = BatchDialog(self)
        dialog.exec()

    def generate_compliance_report(self) -> None:
        """Generate an HTML compliance report for the current document."""
        if not self.current_file:
            QMessageBox.information(self, "No File", "Please open a PDF file first")
            return

        # Get current validation result from the viewer
        result = self.pdf_viewer_tab.run_validation()
        if result is None:
            QMessageBox.warning(self, "Error", "Could not validate the document. Please load it first.")
            return

        # Ask where to save
        default_path = self.current_file.with_name(
            self.current_file.stem + "_compliance_report.html"
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Compliance Report",
            str(default_path),
            "HTML Files (*.html)",
        )

        if not file_path:
            return

        generator = ComplianceReportGenerator(
            document_name=self.current_file.name,
            result=result,
        )

        if generator.generate_report(Path(file_path)):
            self.status_bar.showMessage(f"Report saved: {Path(file_path).name}", 5000)
            QMessageBox.information(
                self,
                "Report Generated",
                f"Compliance report saved to:\n{file_path}",
            )
        else:
            QMessageBox.warning(self, "Error", "Failed to generate compliance report.")

    def _on_wizard_inline_fix(self, issue, fix_value: str) -> None:
        """Handle an inline fix from the Guided Fix Wizard (main window context)."""
        handler = self.pdf_viewer_tab._handler
        document = self.pdf_viewer_tab.current_document
        if not handler or not document:
            return

        criterion = issue.criterion
        logger.info(f"Wizard inline fix for [{criterion}]: '{fix_value}'")

        if criterion == "2.4.2":
            handler.set_title(fix_value)
        elif criterion == "3.1.1":
            handler.set_language(fix_value)
        elif criterion in ("1.3.1", "1.3.2"):
            if not document.is_tagged or not document.has_structure:
                handler.ensure_tagged()
        elif criterion == "1.1.1":
            page_num = issue.page or 1
            handler.set_image_alt_text(page_num, 0, fix_value)

        # Save to disk so changes persist
        self.pdf_viewer_tab._save_and_persist()

    def _open_walkthrough_from_wizard(self, walkthrough_id: str) -> None:
        """Launch a Show Me walkthrough dialog from the main window."""
        wt = WALKTHROUGHS.get(walkthrough_id)
        if not wt:
            return
        dialog = ShowMeWalkthroughDialog(wt, parent=self)
        dialog.exec()

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

    def _on_settings_changed(self, config: dict) -> None:
        """Apply accessibility preferences when settings are saved."""
        ui = config.get("ui", {})

        # High contrast
        self.toggle_high_contrast(ui.get("high_contrast", False))

        # Reduced motion
        self._apply_reduced_motion(ui.get("reduced_motion", False))

        # Large text mode
        self._apply_large_text(ui.get("large_text_mode", False))

        # Enhanced focus
        self._apply_enhanced_focus(ui.get("enhanced_focus", False))

        # Dyslexia font
        self._apply_dyslexia_font(ui.get("dyslexia_font", False))

        # Color blindness mode
        self._apply_color_blind_mode(ui.get("color_blind_mode", "none"))

        # Custom cursor
        self._apply_custom_cursor(ui.get("custom_cursor", "default"))

        logger.info("Accessibility settings applied")

    def _apply_reduced_motion(self, enabled: bool) -> None:
        """Disable or enable animations application-wide."""
        ToggleSwitch.reduced_motion = enabled
        if enabled:
            self.status_bar.showMessage("Reduced Motion enabled — animations disabled", 3000)
        logger.debug(f"Reduced motion: {enabled}")

    def _apply_large_text(self, enabled: bool) -> None:
        """Scale all fonts by 125% — updates stylesheet and QApplication font."""
        import re
        from PyQt6.QtWidgets import QApplication

        if enabled:
            # Proportionally scale every font-size in the stylesheet
            def _scale(m):
                val = int(m.group(1))
                unit = m.group(2)
                return f"font-size: {int(val * 1.25)}{unit}"
            updated = re.sub(r"font-size:\s*(\d+)(pt|px)", _scale, self.styleSheet())
            self.setStyleSheet(updated)

        # Update QApplication font so widgets without stylesheet inherit it
        size = 15 if enabled else 12
        font = QApplication.instance().font()
        font.setPointSize(size)
        QApplication.instance().setFont(font)

        logger.debug(f"Large text mode: {enabled} (font {size}pt)")

    def _apply_enhanced_focus(self, enabled: bool) -> None:
        """Apply thicker, more visible focus indicators.

        Makes an immediately-visible change (brighter borders on all
        interactive widgets) plus very obvious yellow focus rings.
        """
        ToggleSwitch.enhanced_focus = enabled
        if enabled:
            self.setStyleSheet(
                self.styleSheet()
                + """
                QPushButton, QComboBox, QSpinBox, QLineEdit {
                    border: 2px solid #888888;
                }
                QPushButton:focus, QComboBox:focus, QSpinBox:focus,
                QLineEdit:focus, QListWidget:focus, QTreeWidget:focus,
                QTableWidget:focus {
                    border: 4px solid #FFFF00;
                }
                QTabBar::tab:focus {
                    border: 4px solid #FFFF00;
                }
                """
            )
        # Repaint all toggles so their focus rings update
        for toggle in self.findChildren(ToggleSwitch):
            toggle.update()
        logger.debug(f"Enhanced focus: {enabled}")

    def _apply_dyslexia_font(self, enabled: bool) -> None:
        """Switch to a dyslexia-friendly font.

        Uses QFontDatabase to pick the best available dyslexia-friendly font,
        then applies it via both QApplication.setFont() AND stylesheet
        font-family so it overrides all styled widgets.
        """
        import re
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFontDatabase

        if enabled:
            available = QFontDatabase.families()
            # Preference chain: OpenDyslexic > Comic Sans MS > Arial
            chosen = None
            for candidate in ("OpenDyslexic", "Comic Sans MS", "Arial"):
                if candidate in available:
                    chosen = candidate
                    break
            if not chosen:
                chosen = "Arial"  # last resort

            # Apply via QApplication so it reaches every widget
            app_font = QApplication.instance().font()
            app_font.setFamily(chosen)
            app_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 105)
            app_font.setWordSpacing(2.0)
            QApplication.instance().setFont(app_font)

            # Inject font-family into stylesheet so styled widgets also pick it up
            ss = self.styleSheet()
            # Remove any previous injection
            ss = re.sub(r'/\* dyslexia-font-start \*/.*?/\* dyslexia-font-end \*/', '', ss, flags=re.DOTALL)
            ss += f'\n/* dyslexia-font-start */ * {{ font-family: "{chosen}"; }} /* dyslexia-font-end */'
            self.setStyleSheet(ss)
        else:
            # Reset to system default
            app_font = QApplication.instance().font()
            app_font.setFamily("")
            app_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 100)
            app_font.setWordSpacing(0.0)
            QApplication.instance().setFont(app_font)

            # Remove font-family injection from stylesheet
            ss = self.styleSheet()
            ss = re.sub(r'/\* dyslexia-font-start \*/.*?/\* dyslexia-font-end \*/', '', ss, flags=re.DOTALL)
            self.setStyleSheet(ss)

        logger.debug(f"Dyslexia font: {enabled}")

    def _apply_color_blind_mode(self, mode: str) -> None:
        """Remap ALL brand accent colours for colour-blind accommodation.

        Replaces every occurrence of the brand hex colors in the main window
        stylesheet AND in all child widget stylesheets so the entire app
        updates, not just a handful of selectors.
        """
        from PyQt6.QtWidgets import QWidget as _QW

        # Map: original brand color -> replacement per mode
        # (PRIMARY, PRIMARY_DARK, PRIMARY_LIGHT, INPUT_FOCUS/selection-blue)
        _mode_colors = {
            "deuteranopia": ("#1976D2", "#1565C0", "#42A5F5", "#1976D2"),  # Blue
            "protanopia":   ("#1976D2", "#1565C0", "#42A5F5", "#1976D2"),  # Blue
            "tritanopia":   ("#E91E63", "#C2185B", "#F06292", "#E91E63"),  # Pink
            "monochrome":   ("#9E9E9E", "#757575", "#BDBDBD", "#9E9E9E"),  # Gray
        }

        # Brand colors to replace (case-insensitive matching via lower())
        _brand_map_keys = [
            COLORS.PRIMARY.lower(),        # #a23b84
            COLORS.PRIMARY_DARK.lower(),   # #8a3270
            COLORS.PRIMARY_LIGHT.lower(),  # #b85a9a
            COLORS.INPUT_FOCUS.lower(),    # #3B82F6 -> #3b82f6
        ]

        def _replace_colors(stylesheet: str, replacements: list) -> str:
            """Replace all brand color hex codes in a stylesheet string."""
            result = stylesheet
            for original, replacement in zip(_brand_map_keys, replacements):
                # Replace both lower and original casing
                result = result.replace(original, replacement)
                result = result.replace(original.upper(), replacement)
                # Also handle mixed case (#3B82F6 vs #3b82f6)
                orig_upper = original.upper()
                if orig_upper != original:
                    result = result.replace(orig_upper, replacement)
            return result

        def _restore_colors(stylesheet: str) -> str:
            """Restore original brand colors in a stylesheet string."""
            originals = [
                COLORS.PRIMARY, COLORS.PRIMARY_DARK,
                COLORS.PRIMARY_LIGHT, COLORS.INPUT_FOCUS,
            ]
            return stylesheet  # originals are baked in by _apply_styles()

        colors = _mode_colors.get(mode)
        if colors:
            primary, dark, light, focus = colors
            replacements = [primary, dark, light, focus]
            ToggleSwitch.on_color = QColor(primary)

            # Replace in main window stylesheet
            ss = _replace_colors(self.styleSheet(), replacements)
            self.setStyleSheet(ss)

            # Replace in ALL child widget stylesheets
            for child in self.findChildren(_QW):
                child_ss = child.styleSheet()
                if child_ss:
                    # Store original stylesheet for restoration
                    if not hasattr(child, '_orig_stylesheet'):
                        child._orig_stylesheet = child_ss
                    child.setStyleSheet(_replace_colors(child_ss, replacements))
        else:
            # "none" — reset to default
            ToggleSwitch.on_color = None

            # Restore original child stylesheets
            for child in self.findChildren(_QW):
                if hasattr(child, '_orig_stylesheet'):
                    child.setStyleSheet(child._orig_stylesheet)
                    del child._orig_stylesheet

        # Repaint all toggles so they pick up the new on_color
        for toggle in self.findChildren(ToggleSwitch):
            toggle.update()

        logger.debug(f"Color blind mode: {mode}")

    def _apply_custom_cursor(self, style: str) -> None:
        """Set a custom cursor style for the entire application."""
        from PyQt6.QtCore import QByteArray
        from PyQt6.QtSvg import QSvgRenderer

        # Stop cursor trail if switching away from it
        if self._cursor_trail and style != "cursor-trail":
            self._cursor_trail.stop()

        if style == "cursor-trail":
            self.unsetCursor()
            if not self._cursor_trail:
                self._cursor_trail = CursorTrailOverlay(self)
            self._cursor_trail.setGeometry(self.rect())
            self._cursor_trail.start()
            return

        if style == "default":
            self.unsetCursor()
            return

        size = 32
        hot_x, hot_y = 4, 4

        svg_map = {
            "large-black": (
                '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
                '<polygon points="4,4 4,28 12,20 20,28" '
                'fill="black" stroke="white" stroke-width="2"/></svg>'
            ),
            "large-white": (
                '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
                '<polygon points="4,4 4,28 12,20 20,28" '
                'fill="white" stroke="black" stroke-width="2"/></svg>'
            ),
            "large-crosshair": (
                '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
                '<line x1="16" y1="0" x2="16" y2="32" stroke="red" stroke-width="2"/>'
                '<line x1="0" y1="16" x2="32" y2="16" stroke="red" stroke-width="2"/>'
                '<circle cx="16" cy="16" r="6" fill="none" stroke="black" stroke-width="1.5"/>'
                '</svg>'
            ),
            "high-visibility": (
                '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">'
                '<polygon points="4,4 4,36 14,26 24,36" '
                'fill="#FFD700" stroke="black" stroke-width="2.5"/></svg>'
            ),
        }

        svg_data = svg_map.get(style)
        if not svg_data:
            self.unsetCursor()
            return

        if style == "high-visibility":
            size = 40

        try:
            renderer = QSvgRenderer(QByteArray(svg_data.encode()))
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            from PyQt6.QtGui import QPainter
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            self.setCursor(QCursor(pixmap, hot_x, hot_y))
        except Exception as e:
            logger.warning(f"Failed to apply custom cursor '{style}': {e}")
            self.unsetCursor()

        logger.debug(f"Custom cursor: {style}")

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

    def _on_tab_changed(self, index: int) -> None:
        """Refresh dashboard when switching back to it."""
        if index == 0:  # Dashboard tab
            self.dashboard_tab.refresh()

    def resizeEvent(self, event) -> None:
        """Keep cursor trail overlay sized to window."""
        super().resizeEvent(event)
        if self._cursor_trail and self._cursor_trail.isVisible():
            self._cursor_trail.setGeometry(self.rect())

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        has_changes = self.pdf_viewer_tab.has_unsaved_changes

        if has_changes:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

        logger.info("Application closing")
        event.accept()

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
