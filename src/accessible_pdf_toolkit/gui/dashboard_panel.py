"""
Dashboard panel with recent files and drag-drop support.
"""

import json
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QGridLayout,
    QFileDialog,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QMimeData
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QPainter, QColor, QPen, QFont

from ..utils.constants import COLORS, APP_DATA_DIR
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Recent files storage path
RECENT_FILES_PATH = APP_DATA_DIR / "recent_files.json"
MAX_RECENT_FILES = 20


class RecentFileCard(QFrame):
    """Card widget for displaying a recent PDF file."""

    clicked = pyqtSignal(str)  # file_path
    remove_requested = pyqtSignal(str)  # file_path

    def __init__(self, file_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self._file_path = file_info.get("path", "")
        self._file_name = file_info.get("name", "Unknown")
        self._last_opened = file_info.get("last_opened", "")
        self._thumbnail = file_info.get("thumbnail")

        self._setup_ui()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_ui(self) -> None:
        """Set up the card UI."""
        self.setFixedSize(180, 220)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.SURFACE};
                border: 1px solid {COLORS.BORDER};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border: 2px solid {COLORS.PRIMARY};
                background-color: {COLORS.BACKGROUND_ALT};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Thumbnail placeholder
        thumbnail_frame = QFrame()
        thumbnail_frame.setFixedSize(160, 120)
        thumbnail_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND_ALT};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
            }}
        """)

        thumb_layout = QVBoxLayout(thumbnail_frame)
        thumb_layout.setContentsMargins(0, 0, 0, 0)

        # PDF icon or thumbnail
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setText("PDF")
        icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                font-weight: bold;
                color: {COLORS.PRIMARY};
            }}
        """)
        thumb_layout.addWidget(icon_label)

        layout.addWidget(thumbnail_frame)

        # File name
        name_label = QLabel(self._file_name)
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(40)
        name_label.setStyleSheet(f"""
            QLabel {{
                font-size: 11pt;
                font-weight: bold;
                color: {COLORS.TEXT_PRIMARY};
            }}
        """)
        name_label.setToolTip(self._file_path)
        layout.addWidget(name_label)

        # Last opened
        if self._last_opened:
            try:
                dt = datetime.fromisoformat(self._last_opened)
                date_str = dt.strftime("%b %d, %Y")
            except (ValueError, TypeError):
                date_str = "Unknown"
        else:
            date_str = "Unknown"

        date_label = QLabel(date_str)
        date_label.setStyleSheet(f"""
            QLabel {{
                font-size: 10pt;
                color: {COLORS.TEXT_SECONDARY};
            }}
        """)
        layout.addWidget(date_label)

    def mousePressEvent(self, event) -> None:
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._file_path)
        super().mousePressEvent(event)

    @property
    def file_path(self) -> str:
        return self._file_path


class DropZone(QFrame):
    """Drop zone widget for drag-and-drop PDF files."""

    file_dropped = pyqtSignal(str)  # file_path
    browse_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._setup_ui()
        self._dragging = False

    def _setup_ui(self) -> None:
        """Set up the drop zone UI."""
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._update_style(False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        # Icon
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setText("Drop PDF Here")
        icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 32px;
                font-weight: bold;
                color: {COLORS.PRIMARY};
            }}
        """)
        layout.addWidget(icon_label)
        self._icon_label = icon_label

        # Instructions
        text_label = QLabel("Drag and drop a PDF file here\nor click Browse to select")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setStyleSheet(f"""
            QLabel {{
                font-size: 12pt;
                color: {COLORS.TEXT_SECONDARY};
            }}
        """)
        layout.addWidget(text_label)

        # Browse button
        browse_btn = QPushButton("Browse Files")
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 32px;
                font-weight: bold;
                font-size: 12pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY_DARK};
            }}
        """)
        browse_btn.clicked.connect(self.browse_clicked.emit)
        layout.addWidget(browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _update_style(self, dragging: bool) -> None:
        """Update the style based on drag state."""
        if dragging:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS.PRIMARY}20;
                    border: 3px dashed {COLORS.PRIMARY};
                    border-radius: 12px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS.SURFACE};
                    border: 2px dashed {COLORS.BORDER};
                    border-radius: 12px;
                }}
                QFrame:hover {{
                    border: 2px dashed {COLORS.PRIMARY};
                    background-color: {COLORS.BACKGROUND_ALT};
                }}
            """)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                if url.toLocalFile().lower().endswith('.pdf'):
                    event.acceptProposedAction()
                    self._dragging = True
                    self._update_style(True)
                    return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        """Handle drag leave event."""
        self._dragging = False
        self._update_style(False)

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event."""
        self._dragging = False
        self._update_style(False)

        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.lower().endswith('.pdf'):
                    self.file_dropped.emit(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()


class DashboardPanel(QWidget):
    """Dashboard panel with recent files and drag-drop support."""

    # Signals
    file_selected = pyqtSignal(str)  # file_path - when a recent file is clicked
    file_dropped = pyqtSignal(str)   # file_path - when a file is dropped

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recent_files: List[Dict[str, Any]] = []

        self._setup_ui()
        self._load_recent_files()
        self._setup_accessibility()

    def _setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Dashboard")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: 28px;
                font-weight: bold;
                color: {COLORS.TEXT_PRIMARY};
            }}
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Import button
        import_btn = QPushButton("Import PDF")
        import_btn.clicked.connect(self._browse_files)
        import_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 12pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY_DARK};
            }}
        """)
        header_layout.addWidget(import_btn)

        layout.addLayout(header_layout)

        # Drop zone
        self._drop_zone = DropZone()
        self._drop_zone.file_dropped.connect(self._on_file_dropped)
        self._drop_zone.browse_clicked.connect(self._browse_files)
        layout.addWidget(self._drop_zone)

        # Recent files section
        recent_header = QHBoxLayout()
        recent_title = QLabel("Recent Files")
        recent_title.setStyleSheet(f"""
            QLabel {{
                font-size: 18px;
                font-weight: bold;
                color: {COLORS.TEXT_PRIMARY};
            }}
        """)
        recent_header.addWidget(recent_title)
        recent_header.addStretch()

        clear_btn = QPushButton("Clear History")
        clear_btn.clicked.connect(self._clear_recent_files)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS.TEXT_SECONDARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.BACKGROUND_ALT};
                color: {COLORS.TEXT_PRIMARY};
            }}
        """)
        recent_header.addWidget(clear_btn)

        layout.addLayout(recent_header)

        # Recent files grid (scrollable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
        """)

        self._recent_container = QWidget()
        self._recent_layout = QGridLayout(self._recent_container)
        self._recent_layout.setSpacing(16)
        self._recent_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll_area.setWidget(self._recent_container)
        layout.addWidget(scroll_area)

        # No files message
        self._no_files_label = QLabel("No recent files. Drop a PDF above or click Browse.")
        self._no_files_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_files_label.setStyleSheet(f"""
            QLabel {{
                font-size: 12pt;
                color: {COLORS.TEXT_SECONDARY};
                padding: 40px;
            }}
        """)
        self._recent_layout.addWidget(self._no_files_label, 0, 0)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self.setAccessibleName("Dashboard")
        self.setAccessibleDescription("View and manage recent PDF files")

    def _load_recent_files(self) -> None:
        """Load recent files from storage."""
        try:
            if RECENT_FILES_PATH.exists():
                with open(RECENT_FILES_PATH, 'r') as f:
                    self._recent_files = json.load(f)
                    # Filter out files that no longer exist
                    self._recent_files = [
                        f for f in self._recent_files
                        if Path(f.get("path", "")).exists()
                    ]
            self._update_recent_files_ui()
        except Exception as e:
            logger.error(f"Failed to load recent files: {e}")
            self._recent_files = []

    def _save_recent_files(self) -> None:
        """Save recent files to storage."""
        try:
            RECENT_FILES_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(RECENT_FILES_PATH, 'w') as f:
                json.dump(self._recent_files, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save recent files: {e}")

    def _update_recent_files_ui(self) -> None:
        """Update the recent files grid."""
        # Clear existing items
        while self._recent_layout.count():
            item = self._recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._recent_files:
            self._no_files_label = QLabel("No recent files. Drop a PDF above or click Browse.")
            self._no_files_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._no_files_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 12pt;
                    color: {COLORS.TEXT_SECONDARY};
                    padding: 40px;
                }}
            """)
            self._recent_layout.addWidget(self._no_files_label, 0, 0)
            return

        # Add file cards
        columns = 5  # Cards per row
        for i, file_info in enumerate(self._recent_files[:MAX_RECENT_FILES]):
            row = i // columns
            col = i % columns

            card = RecentFileCard(file_info)
            card.clicked.connect(self._on_recent_file_clicked)
            self._recent_layout.addWidget(card, row, col)

        # Add stretch at the end
        self._recent_layout.setRowStretch(len(self._recent_files) // columns + 1, 1)

    def add_recent_file(self, file_path: str) -> None:
        """Add a file to recent files list."""
        path = Path(file_path)
        if not path.exists():
            return

        # Remove if already exists
        self._recent_files = [
            f for f in self._recent_files
            if f.get("path") != str(path)
        ]

        # Add to front
        file_info = {
            "path": str(path),
            "name": path.name,
            "last_opened": datetime.now().isoformat(),
        }
        self._recent_files.insert(0, file_info)

        # Limit to max
        self._recent_files = self._recent_files[:MAX_RECENT_FILES]

        self._save_recent_files()
        self._update_recent_files_ui()

    def _on_file_dropped(self, file_path: str) -> None:
        """Handle file dropped on drop zone."""
        self.add_recent_file(file_path)
        self.file_dropped.emit(file_path)

    def _on_recent_file_clicked(self, file_path: str) -> None:
        """Handle recent file card clicked."""
        if Path(file_path).exists():
            self.add_recent_file(file_path)  # Update last opened
            self.file_selected.emit(file_path)
        else:
            QMessageBox.warning(
                self,
                "File Not Found",
                f"The file no longer exists:\n{file_path}"
            )
            # Remove from recent files
            self._recent_files = [
                f for f in self._recent_files
                if f.get("path") != file_path
            ]
            self._save_recent_files()
            self._update_recent_files_ui()

    def _browse_files(self) -> None:
        """Open file browser."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF File",
            "",
            "PDF Files (*.pdf);;All Files (*.*)"
        )

        if file_path:
            self._on_file_dropped(file_path)

    def _clear_recent_files(self) -> None:
        """Clear recent files history."""
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear the recent files history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._recent_files = []
            self._save_recent_files()
            self._update_recent_files_ui()

    def refresh(self) -> None:
        """Refresh the dashboard."""
        self._load_recent_files()
