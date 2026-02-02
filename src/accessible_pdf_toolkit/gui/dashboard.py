"""
Dashboard panel for file organization and analytics.
"""

from typing import Optional, List
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QFrame,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFileDialog,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QGroupBox,
    QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from ..utils.constants import COLORS, ComplianceStatus
from ..utils.logger import get_logger
from ..database.models import User, Course, File, get_session, init_db
from ..database.queries import DatabaseQueries

logger = get_logger(__name__)


class CourseDialog(QDialog):
    """Dialog for creating/editing courses."""

    def __init__(self, parent=None, course: Optional[Course] = None):
        super().__init__(parent)
        self.course = course
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Edit Course" if self.course else "New Course")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g., CS101")
        if self.course:
            self.code_input.setText(self.course.code)
        form.addRow("Course Code:", self.code_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Introduction to Computer Science")
        if self.course:
            self.name_input.setText(self.course.name)
        form.addRow("Course Name:", self.name_input)

        self.semester_input = QLineEdit()
        self.semester_input.setPlaceholderText("e.g., Fall 2024")
        if self.course:
            self.semester_input.setText(self.course.semester or "")
        form.addRow("Semester:", self.semester_input)

        layout.addLayout(form)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> dict:
        """Get the form data."""
        return {
            "code": self.code_input.text().strip(),
            "name": self.name_input.text().strip(),
            "semester": self.semester_input.text().strip() or None,
        }


class StatsCard(QFrame):
    """Card widget for displaying statistics."""

    def __init__(self, title: str, value: str, color: str = COLORS.PRIMARY, parent=None):
        super().__init__(parent)
        self._setup_ui(title, value, color)

    def _setup_ui(self, title: str, value: str, color: str) -> None:
        """Set up the card UI."""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.SURFACE};
                border: 1px solid {COLORS.BORDER};
                border-radius: 8px;
                padding: 16px;
            }}
        """)

        layout = QVBoxLayout(self)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"""
            color: {COLORS.TEXT_SECONDARY};
            font-size: 12pt;
        """)
        layout.addWidget(self.title_label)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"""
            color: {color};
            font-size: 24px;
            font-weight: bold;
        """)
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        """Update the displayed value."""
        self.value_label.setText(value)


class FileTable(QTableWidget):
    """Table widget for displaying files."""

    file_selected = pyqtSignal(int)  # file_id
    file_double_clicked = pyqtSignal(int)  # file_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the table."""
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels([
            "Name", "Course", "Status", "Score", "Modified"
        ])

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)

        self.cellClicked.connect(self._on_cell_clicked)
        self.cellDoubleClicked.connect(self._on_cell_double_clicked)

        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                font-size: 12pt;
            }}
            QTableWidget::item {{
                padding: 8px;
                color: {COLORS.TEXT_PRIMARY};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}
            QTableWidget::item:alternate {{
                background-color: {COLORS.SURFACE};
            }}
            QHeaderView::section {{
                background-color: {COLORS.BACKGROUND_ALT};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                padding: 8px;
                font-weight: bold;
                font-size: 12pt;
            }}
        """)

    def load_files(self, files: List[File]) -> None:
        """Load files into the table."""
        self.setRowCount(len(files))

        for row, file in enumerate(files):
            # Name
            name_item = QTableWidgetItem(file.original_name)
            name_item.setData(Qt.ItemDataRole.UserRole, file.id)
            self.setItem(row, 0, name_item)

            # Course
            course_name = file.course.code if file.course else "—"
            self.setItem(row, 1, QTableWidgetItem(course_name))

            # Status
            status = ComplianceStatus[file.compliance_status]
            status_item = QTableWidgetItem(status.name.replace("_", " ").title())

            if status == ComplianceStatus.COMPLIANT:
                status_item.setForeground(QColor(COLORS.SUCCESS))
            elif status == ComplianceStatus.NON_COMPLIANT:
                status_item.setForeground(QColor(COLORS.ERROR))
            elif status == ComplianceStatus.PARTIAL:
                status_item.setForeground(QColor(COLORS.WARNING))
            else:
                status_item.setForeground(QColor(COLORS.TEXT_SECONDARY))

            self.setItem(row, 2, status_item)

            # Score
            score = f"{file.compliance_score:.0f}%" if file.compliance_score else "—"
            self.setItem(row, 3, QTableWidgetItem(score))

            # Modified
            modified = file.modified_at.strftime("%Y-%m-%d %H:%M")
            self.setItem(row, 4, QTableWidgetItem(modified))

    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Handle cell click."""
        item = self.item(row, 0)
        if item:
            file_id = item.data(Qt.ItemDataRole.UserRole)
            self.file_selected.emit(file_id)

    def _on_cell_double_clicked(self, row: int, col: int) -> None:
        """Handle cell double-click."""
        item = self.item(row, 0)
        if item:
            file_id = item.data(Qt.ItemDataRole.UserRole)
            self.file_double_clicked.emit(file_id)


class Dashboard(QWidget):
    """Dashboard panel for file organization and analytics."""

    # Signals
    file_opened = pyqtSignal(str)  # file path
    course_selected = pyqtSignal(int)  # course_id

    def __init__(self, user: Optional[User] = None, parent=None):
        super().__init__(parent)

        self._user = user
        self._db = DatabaseQueries()

        self._setup_ui()
        self._setup_accessibility()
        self._load_data()

    def _setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()

        title = QLabel("Dashboard")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {COLORS.TEXT_PRIMARY};
        """)
        header.addWidget(title)

        header.addStretch()

        # Import button
        import_btn = QPushButton("Import PDF")
        import_btn.clicked.connect(self.import_file)
        import_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY_DARK};
            }}
        """)
        header.addWidget(import_btn)

        layout.addLayout(header)

        # Stats cards
        stats_layout = QHBoxLayout()

        self.total_files_card = StatsCard("Total Files", "0")
        stats_layout.addWidget(self.total_files_card)

        self.compliant_card = StatsCard("Compliant", "0", COLORS.SUCCESS)
        stats_layout.addWidget(self.compliant_card)

        self.needs_work_card = StatsCard("Needs Work", "0", COLORS.WARNING)
        stats_layout.addWidget(self.needs_work_card)

        self.avg_score_card = StatsCard("Avg. Score", "—", COLORS.PRIMARY)
        stats_layout.addWidget(self.avg_score_card)

        layout.addLayout(stats_layout)

        # Main content
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Courses
        courses_panel = QFrame()
        courses_panel.setFixedWidth(250)
        courses_layout = QVBoxLayout(courses_panel)
        courses_layout.setContentsMargins(0, 0, 0, 0)

        courses_header = QHBoxLayout()
        courses_title = QLabel("Courses")
        courses_title.setStyleSheet(f"font-weight: bold; font-size: 14pt; color: {COLORS.TEXT_PRIMARY};")
        courses_header.addWidget(courses_title)

        add_course_btn = QPushButton("+")
        add_course_btn.setFixedSize(24, 24)
        add_course_btn.clicked.connect(self.add_course)
        add_course_btn.setToolTip("Add new course")
        courses_header.addWidget(add_course_btn)

        courses_layout.addLayout(courses_header)

        self.course_list = QComboBox()
        self.course_list.addItem("All Courses", None)
        self.course_list.currentIndexChanged.connect(self._on_course_changed)
        self.course_list.setAccessibleName("Select course")
        self.course_list.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}
            QComboBox:focus {{
                border: 2px solid {COLORS.INPUT_FOCUS};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                selection-background-color: {COLORS.PRIMARY};
            }}
        """)
        courses_layout.addWidget(self.course_list)

        # Course info
        self.course_info = QLabel("Select a course to view details")
        self.course_info.setWordWrap(True)
        self.course_info.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY};")
        courses_layout.addWidget(self.course_info)

        courses_layout.addStretch()

        content_splitter.addWidget(courses_panel)

        # Right panel: Files
        files_panel = QFrame()
        files_layout = QVBoxLayout(files_panel)
        files_layout.setContentsMargins(0, 0, 0, 0)

        # Search and filter
        filter_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search files...")
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.setAccessibleName("Search files")
        self.search_input.setStyleSheet(f"""
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
            QLineEdit::placeholder {{
                color: {COLORS.TEXT_SECONDARY};
            }}
        """)
        filter_layout.addWidget(self.search_input)

        self.status_filter = QComboBox()
        self.status_filter.addItem("All Status", None)
        self.status_filter.addItem("Compliant", ComplianceStatus.COMPLIANT)
        self.status_filter.addItem("Needs Work", ComplianceStatus.PARTIAL)
        self.status_filter.addItem("Non-compliant", ComplianceStatus.NON_COMPLIANT)
        self.status_filter.addItem("Not Checked", ComplianceStatus.NOT_CHECKED)
        self.status_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.status_filter.setAccessibleName("Filter by status")
        self.status_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}
            QComboBox:focus {{
                border: 2px solid {COLORS.INPUT_FOCUS};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                selection-background-color: {COLORS.PRIMARY};
            }}
        """)
        filter_layout.addWidget(self.status_filter)

        files_layout.addLayout(filter_layout)

        # File table
        self.file_table = FileTable()
        self.file_table.file_double_clicked.connect(self._on_file_double_clicked)
        files_layout.addWidget(self.file_table)

        content_splitter.addWidget(files_panel)
        content_splitter.setSizes([250, 750])

        layout.addWidget(content_splitter)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self.setAccessibleName("Dashboard")
        self.setAccessibleDescription("View and manage PDF files and courses")

    def _load_data(self) -> None:
        """Load data from database."""
        if not self._user:
            return

        try:
            # Load courses
            courses = self._db.get_courses(self._user.id)
            self.course_list.clear()
            self.course_list.addItem("All Courses", None)
            for course in courses:
                self.course_list.addItem(f"{course.code} - {course.name}", course.id)

            # Load files
            self._load_files()

            # Update stats
            self._update_stats()

        except Exception as e:
            logger.error(f"Failed to load data: {e}")

    def _load_files(self) -> None:
        """Load files based on current filters."""
        if not self._user:
            return

        course_id = self.course_list.currentData()
        status = self.status_filter.currentData()
        search = self.search_input.text().strip() or None

        files = self._db.get_files(
            course_id=course_id,
            compliance_status=status,
            search_query=search,
        )

        self.file_table.load_files(files)

    def _update_stats(self) -> None:
        """Update statistics cards."""
        if not self._user:
            return

        stats = self._db.get_compliance_stats(self._user.id)

        self.total_files_card.set_value(str(stats["total_files"]))

        compliant = stats["status_counts"].get(ComplianceStatus.COMPLIANT.name, 0)
        self.compliant_card.set_value(str(compliant))

        needs_work = (
            stats["status_counts"].get(ComplianceStatus.PARTIAL.name, 0) +
            stats["status_counts"].get(ComplianceStatus.NON_COMPLIANT.name, 0)
        )
        self.needs_work_card.set_value(str(needs_work))

        if stats["average_score"] is not None:
            self.avg_score_card.set_value(f"{stats['average_score']:.0f}%")
        else:
            self.avg_score_card.set_value("—")

    def _on_course_changed(self) -> None:
        """Handle course selection change."""
        course_id = self.course_list.currentData()

        if course_id:
            course = self._db.get_course(course_id)
            if course:
                stats = self._db.get_course_stats(course_id)
                self.course_info.setText(
                    f"<b>{course.name}</b><br>"
                    f"Semester: {course.semester or 'N/A'}<br>"
                    f"Files: {stats['total_files']}<br>"
                    f"Compliance: {stats['compliance_rate']:.0f}%"
                )
                self.course_selected.emit(course_id)
        else:
            self.course_info.setText("Showing all courses")

        self._load_files()

    def _on_search(self) -> None:
        """Handle search input."""
        self._load_files()

    def _on_filter_changed(self) -> None:
        """Handle filter change."""
        self._load_files()

    def _on_file_double_clicked(self, file_id: int) -> None:
        """Handle file double-click."""
        file = self._db.get_file(file_id)
        if file:
            self.file_opened.emit(file.file_path)

    def import_file(self) -> None:
        """Import a PDF file."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import PDF Files",
            "",
            "PDF Files (*.pdf);;All Files (*.*)",
        )

        if not file_paths:
            return

        imported = 0
        for file_path in file_paths:
            try:
                path = Path(file_path)
                from ..utils.file_operations import FileOperations

                file_hash = FileOperations.calculate_hash(path)
                file_size = path.stat().st_size

                course_id = self.course_list.currentData()

                self._db.create_file(
                    original_name=path.name,
                    file_path=str(path),
                    file_hash=file_hash,
                    file_size=file_size,
                    course_id=course_id,
                )
                imported += 1
            except Exception as e:
                logger.error(f"Failed to import {file_path}: {e}")

        if imported > 0:
            self._load_files()
            self._update_stats()
            QMessageBox.information(
                self,
                "Import Complete",
                f"Imported {imported} file(s)",
            )

    def add_course(self) -> None:
        """Add a new course."""
        if not self._user:
            QMessageBox.warning(self, "Error", "Please log in first")
            return

        dialog = CourseDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data["code"] or not data["name"]:
                QMessageBox.warning(self, "Error", "Course code and name are required")
                return

            try:
                self._db.create_course(
                    user_id=self._user.id,
                    **data,
                )
                self._load_data()
            except Exception as e:
                logger.error(f"Failed to create course: {e}")
                QMessageBox.critical(self, "Error", f"Failed to create course: {e}")

    def set_user(self, user: User) -> None:
        """Set the current user."""
        self._user = user
        self._load_data()

    def refresh(self) -> None:
        """Refresh the dashboard data."""
        self._load_data()
