"""
Batch processing dialog for processing multiple PDFs.
"""

from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QProgressBar,
    QFrame,
    QComboBox,
    QCheckBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from ...utils.constants import COLORS, WCAGLevel
from ...utils.logger import get_logger
from ...core.pdf_handler import PDFHandler
from ...core.wcag_validator import WCAGValidator, ValidationResult

logger = get_logger(__name__)


class _BatchWorker(QThread):
    """Worker thread for batch PDF processing."""

    progress = pyqtSignal(int, str)  # (index, filename)
    file_done = pyqtSignal(int, object)  # (index, ValidationResult)
    file_error = pyqtSignal(int, str)  # (index, error message)
    all_done = pyqtSignal()

    def __init__(
        self,
        files: List[Path],
        level: WCAGLevel,
        auto_fix: bool,
    ):
        super().__init__()
        self._files = files
        self._level = level
        self._auto_fix = auto_fix

    def run(self):
        for idx, file_path in enumerate(self._files):
            self.progress.emit(idx, file_path.name)
            handler = PDFHandler()
            try:
                doc = handler.open(file_path)
                if not doc:
                    self.file_error.emit(idx, "Failed to open PDF")
                    continue

                if self._auto_fix:
                    # Apply basic fixes
                    if not doc.title or doc.title.strip() == "":
                        humanized = file_path.stem.replace("_", " ").replace("-", " ").title()
                        handler.set_title(humanized)
                    if not doc.language:
                        handler.set_language("en")
                    if not doc.is_tagged:
                        handler.ensure_tagged()
                    handler.save()

                validator = WCAGValidator(target_level=self._level)
                result = validator.validate(doc)
                self.file_done.emit(idx, result)
            except Exception as e:
                self.file_error.emit(idx, str(e))
            finally:
                handler.close()

        self.all_done.emit()


class BatchDialog(QDialog):
    """Dialog for batch processing multiple PDF files."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: List[Path] = []
        self._results: List[Optional[ValidationResult]] = []
        self._worker: Optional[_BatchWorker] = None

        self._setup_ui()
        self._setup_accessibility()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Batch Process PDFs")
        self.setModal(True)
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        title = QLabel("Batch Processing")
        title.setStyleSheet(f"font-size: 16pt; font-weight: bold; color: {COLORS.TEXT_PRIMARY};")
        layout.addWidget(title)

        desc = QLabel("Validate (and optionally auto-fix) multiple PDF files at once.")
        desc.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 11pt;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # File list
        file_header = QHBoxLayout()
        file_label = QLabel("Files:")
        file_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-weight: bold;")
        file_header.addWidget(file_label)
        file_header.addStretch()

        add_btn = QPushButton("Add Files...")
        add_btn.clicked.connect(self._add_files)
        file_header.addWidget(add_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected)
        file_header.addWidget(remove_btn)

        for btn in [add_btn, remove_btn]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.SURFACE};
                    color: {COLORS.TEXT_PRIMARY};
                    border: 1px solid {COLORS.BORDER};
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 10pt;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.PRIMARY_LIGHT};
                    color: white;
                }}
            """)

        layout.addLayout(file_header)

        self._file_list = QListWidget()
        self._file_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                font-size: 10pt;
            }}
            QListWidget::item {{
                padding: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}
        """)
        self._file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self._file_list, 1)

        # Options row
        options_frame = QFrame()
        options_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND_ALT};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        options_layout = QHBoxLayout(options_frame)

        level_label = QLabel("Target Level:")
        level_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY};")
        options_layout.addWidget(level_label)

        self._level_combo = QComboBox()
        self._level_combo.addItems(["A", "AA", "AAA"])
        self._level_combo.setCurrentIndex(1)  # Default AA
        self._level_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 4px 8px;
            }}
        """)
        options_layout.addWidget(self._level_combo)

        options_layout.addStretch()

        self._auto_fix_check = QCheckBox("Auto-fix common issues")
        self._auto_fix_check.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY};")
        self._auto_fix_check.setChecked(True)
        options_layout.addWidget(self._auto_fix_check)

        layout.addWidget(options_frame)

        # Progress
        self._progress_bar = QProgressBar()
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                text-align: center;
                color: {COLORS.TEXT_PRIMARY};
                background-color: {COLORS.SURFACE};
            }}
            QProgressBar::chunk {{
                background-color: {COLORS.PRIMARY};
                border-radius: 3px;
            }}
        """)
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 10pt;")
        layout.addWidget(self._status_label)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._run_btn = QPushButton("Run Batch")
        self._run_btn.clicked.connect(self._run_batch)
        self._run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 24px;
                font-weight: bold;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY_DARK};
            }}
            QPushButton:disabled {{
                background-color: {COLORS.BORDER};
            }}
        """)
        btn_row.addWidget(self._run_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 8px 24px;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.BACKGROUND_ALT};
            }}
        """)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _setup_accessibility(self) -> None:
        self.setAccessibleName("Batch Processing Dialog")
        self.setAccessibleDescription("Process multiple PDF files for accessibility compliance")

    def _add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select PDF Files",
            "",
            "PDF Files (*.pdf);;All Files (*.*)",
        )
        for f in files:
            path = Path(f)
            if path not in self._files:
                self._files.append(path)
                self._file_list.addItem(path.name)

    def _remove_selected(self) -> None:
        for item in reversed(self._file_list.selectedItems()):
            idx = self._file_list.row(item)
            self._file_list.takeItem(idx)
            del self._files[idx]

    def _run_batch(self) -> None:
        if not self._files:
            return

        level_map = {"A": WCAGLevel.A, "AA": WCAGLevel.AA, "AAA": WCAGLevel.AAA}
        level = level_map.get(self._level_combo.currentText(), WCAGLevel.AA)
        auto_fix = self._auto_fix_check.isChecked()

        self._results = [None] * len(self._files)
        self._progress_bar.setMaximum(len(self._files))
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._run_btn.setEnabled(False)

        self._worker = _BatchWorker(self._files, level, auto_fix)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.file_error.connect(self._on_file_error)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()

    def _on_progress(self, idx: int, filename: str) -> None:
        self._progress_bar.setValue(idx)
        self._status_label.setText(f"Processing {idx + 1}/{len(self._files)}: {filename}")

    def _on_file_done(self, idx: int, result: ValidationResult) -> None:
        self._results[idx] = result
        item = self._file_list.item(idx)
        if item:
            score = result.score
            status = "\u2713" if result.is_compliant else "\u2717"
            item.setText(f"{status} {self._files[idx].name}  ({score:.0f}%)")

    def _on_file_error(self, idx: int, error: str) -> None:
        item = self._file_list.item(idx)
        if item:
            item.setText(f"\u2717 {self._files[idx].name}  (Error: {error})")

    def _on_all_done(self) -> None:
        self._progress_bar.setValue(len(self._files))
        self._run_btn.setEnabled(True)

        total = len(self._results)
        compliant = sum(1 for r in self._results if r and r.is_compliant)
        errors = sum(1 for r in self._results if r is None)

        self._status_label.setText(
            f"Done: {compliant}/{total} compliant"
            + (f", {errors} errors" if errors else "")
        )
