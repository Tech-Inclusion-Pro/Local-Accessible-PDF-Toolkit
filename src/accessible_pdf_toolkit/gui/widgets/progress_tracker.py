"""
Remediation progress tracker widget.
"""

from typing import Optional, Dict

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QProgressBar,
)
from PyQt6.QtCore import Qt

from ...utils.constants import (
    COLORS,
    RemediationStatus,
    REMEDIATION_CATEGORIES,
)
from ...core.wcag_validator import ValidationResult, IssueSeverity


class CategoryStatusWidget(QFrame):
    """Single row showing status of one remediation category."""

    _STATUS_ICONS = {
        RemediationStatus.NOT_STARTED: ("\u2022\u2022\u2022", COLORS.TEXT_DISABLED),  # bullet dots
        RemediationStatus.IN_PROGRESS: ("\u2699", COLORS.WARNING),  # gear/wrench
        RemediationStatus.COMPLETE: ("\u2713", COLORS.SUCCESS),  # checkmark
    }

    def __init__(self, category_id: str, label: str, description: str, parent=None):
        super().__init__(parent)
        self._category_id = category_id
        self._status = RemediationStatus.NOT_STARTED

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.SURFACE};
                border-radius: 4px;
                padding: 4px 8px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self._icon_label = QLabel()
        self._icon_label.setFixedWidth(24)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet("font-size: 14pt;")
        layout.addWidget(self._icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)

        self._name_label = QLabel(label)
        self._name_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 10pt; font-weight: bold;")
        text_layout.addWidget(self._name_label)

        self._desc_label = QLabel(description)
        self._desc_label.setStyleSheet(f"color: {COLORS.TEXT_DISABLED}; font-size: 9pt;")
        self._desc_label.setWordWrap(True)
        text_layout.addWidget(self._desc_label)

        layout.addLayout(text_layout, 1)

        self._update_icon()

    def set_status(self, status: RemediationStatus) -> None:
        """Update the category status."""
        self._status = status
        self._update_icon()

    def _update_icon(self) -> None:
        icon, color = self._STATUS_ICONS.get(
            self._status,
            ("\u2022\u2022\u2022", COLORS.TEXT_DISABLED),
        )
        self._icon_label.setText(icon)
        self._icon_label.setStyleSheet(f"color: {color}; font-size: 14pt;")

    @property
    def status(self) -> RemediationStatus:
        return self._status


class ProgressTrackerWidget(QWidget):
    """Remediation progress tracker showing status per category."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._category_widgets: Dict[str, CategoryStatusWidget] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(8)

        title = QLabel("Remediation Progress")
        title.setStyleSheet(f"""
            font-size: 14pt;
            font-weight: bold;
            color: {COLORS.TEXT_PRIMARY};
        """)
        layout.addWidget(title)

        # Overall progress bar
        self._overall_bar = QProgressBar()
        self._overall_bar.setMinimum(0)
        self._overall_bar.setMaximum(100)
        self._overall_bar.setValue(0)
        self._overall_bar.setFixedHeight(12)
        self._overall_bar.setTextVisible(True)
        self._overall_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS.SURFACE};
                border: none;
                border-radius: 6px;
                text-align: center;
                color: {COLORS.TEXT_PRIMARY};
                font-size: 9pt;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS.SUCCESS};
                border-radius: 6px;
            }}
        """)
        layout.addWidget(self._overall_bar)

        # Scrollable category list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)

        for cat_id, cat_info in REMEDIATION_CATEGORIES.items():
            widget = CategoryStatusWidget(
                cat_id, cat_info["label"], cat_info["description"]
            )
            self._category_widgets[cat_id] = widget
            container_layout.addWidget(widget)

        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

    def update_from_validation(self, result: ValidationResult) -> None:
        """
        Derive status per category from validation results.

        Logic:
        - No matching issues → COMPLETE
        - Only INFO-level issues → COMPLETE
        - WARNING-level issues → IN_PROGRESS
        - ERROR-level issues → NOT_STARTED
        """
        # Build criterion → max severity map
        criterion_severity: Dict[str, IssueSeverity] = {}
        for issue in result.issues:
            current = criterion_severity.get(issue.criterion)
            if current is None or _severity_rank(issue.severity) < _severity_rank(current):
                criterion_severity[issue.criterion] = issue.severity

        for cat_id, cat_info in REMEDIATION_CATEGORIES.items():
            criteria = cat_info["criteria"]
            if not criteria:
                # No WCAG criteria (e.g. security) — default to COMPLETE
                self._category_widgets[cat_id].set_status(RemediationStatus.COMPLETE)
                continue

            max_severity = None
            for crit in criteria:
                sev = criterion_severity.get(crit)
                if sev is not None:
                    if max_severity is None or _severity_rank(sev) < _severity_rank(max_severity):
                        max_severity = sev

            if max_severity is None or max_severity == IssueSeverity.INFO:
                self._category_widgets[cat_id].set_status(RemediationStatus.COMPLETE)
            elif max_severity == IssueSeverity.WARNING:
                self._category_widgets[cat_id].set_status(RemediationStatus.IN_PROGRESS)
            else:
                self._category_widgets[cat_id].set_status(RemediationStatus.NOT_STARTED)

        # Update overall progress bar
        progress = self.get_overall_progress()
        self._overall_bar.setValue(int(progress))

    def get_overall_progress(self) -> float:
        """Get the percentage of categories at COMPLETE status."""
        if not self._category_widgets:
            return 0.0
        complete = sum(
            1 for w in self._category_widgets.values()
            if w.status == RemediationStatus.COMPLETE
        )
        return (complete / len(self._category_widgets)) * 100


def _severity_rank(severity: IssueSeverity) -> int:
    """Lower is more severe."""
    return {IssueSeverity.ERROR: 0, IssueSeverity.WARNING: 1, IssueSeverity.INFO: 2}.get(severity, 2)
