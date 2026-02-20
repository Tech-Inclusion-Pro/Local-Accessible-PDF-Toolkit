"""
Guided Fix Wizard for walking users through non-auto-fixable accessibility issues.
"""

from typing import List, Dict, Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QProgressBar,
    QScrollArea,
    QLineEdit,
    QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...utils.constants import COLORS, WCAG_EXPLAINER
from ...utils.logger import get_logger
from ...core.wcag_validator import ValidationIssue, IssueSeverity, WCAGValidator
from .show_me_walkthrough import CRITERION_TO_WALKTHROUGH, WALKTHROUGHS

logger = get_logger(__name__)


# Guidance content keyed by WCAG criterion ID
ISSUE_GUIDANCE: Dict[str, Dict] = {
    "1.4.3": {
        "title": "Color Contrast (Minimum)",
        "why_it_matters": (
            "People with low vision or color blindness may not be able to read text "
            "that does not have sufficient contrast against its background. WCAG AA "
            "requires a contrast ratio of at least 4.5:1 for normal text and 3:1 for large text."
        ),
        "fix_steps": [
            "Open the source document in the application that created the PDF (Word, InDesign, etc.)",
            "Identify the low-contrast text and change its color to a darker shade",
            "Use a contrast checker tool (e.g. WebAIM Contrast Checker) to verify the ratio meets 4.5:1",
            "Re-export the PDF and re-validate",
        ],
        "has_inline_tool": False,
    },
    "1.4.6": {
        "title": "Color Contrast (Enhanced)",
        "why_it_matters": (
            "AAA-level contrast (7:1 for normal text, 4.5:1 for large text) provides "
            "better readability for users with moderately low vision who do not use "
            "assistive technology."
        ),
        "fix_steps": [
            "Open the source document in the authoring application",
            "Change text colors to achieve higher contrast (7:1 for normal, 4.5:1 for large text)",
            "Use a contrast checker to verify AAA thresholds are met",
            "Re-export the PDF and re-validate",
        ],
        "has_inline_tool": False,
    },
    "1.3.2": {
        "title": "Reading Order",
        "why_it_matters": (
            "Screen readers read content in the order it appears in the document structure. "
            "If the reading order does not match the visual layout, users may hear content "
            "in a confusing sequence, especially in multi-column layouts."
        ),
        "fix_steps": [
            "Open the PDF in Adobe Acrobat Pro (or a similar tool with Order panel support)",
            "Open the Order panel (View > Show/Hide > Navigation Panes > Order)",
            "Drag content blocks to reorder them to match the visual reading flow",
            "For multi-column layouts, ensure each column is read top-to-bottom before moving to the next",
            "Save and re-validate the PDF",
        ],
        "has_inline_tool": False,
    },
    "2.4.4": {
        "title": "Link Purpose (In Context)",
        "why_it_matters": (
            "Screen reader users often navigate by jumping between links. Generic link text "
            "like 'click here' or 'read more' provides no context about where the link leads. "
            "Descriptive link text helps all users understand the link's destination."
        ),
        "fix_steps": [
            "Identify what the link points to (its destination or purpose)",
            "Type a descriptive replacement in the text field below",
            "Click 'Apply Fix' to update the link text",
        ],
        "has_inline_tool": True,
    },
    "3.1.2": {
        "title": "Language of Parts",
        "why_it_matters": (
            "When a passage is in a different language from the document's main language, "
            "screen readers need a language attribute to switch pronunciation rules. "
            "Without it, foreign words will be mispronounced."
        ),
        "fix_steps": [
            "Open the PDF in Adobe Acrobat Pro",
            "Select the foreign-language passage in the Tags panel",
            "Right-click the tag and choose Properties",
            "Set the Language attribute to the correct BCP 47 code (e.g., 'fr' for French, 'es' for Spanish)",
            "Save and re-validate",
        ],
        "has_inline_tool": False,
    },
    "2.4.1": {
        "title": "Bypass Blocks",
        "why_it_matters": (
            "Long documents need a way for keyboard and screen reader users to skip "
            "repeated content and navigate directly to sections of interest. "
            "Bookmarks and a table of contents serve this purpose in PDFs."
        ),
        "fix_steps": [
            "Add bookmarks for each major section in the PDF",
            "In Acrobat: View > Show/Hide > Navigation Panes > Bookmarks",
            "Alternatively, add a Table of Contents page with internal links",
            "Ensure heading tags (H1-H6) are present, as many readers use them for navigation",
        ],
        "has_inline_tool": False,
    },
    "2.4.6": {
        "title": "Headings and Labels",
        "why_it_matters": (
            "Headings help users understand the organization of a document and navigate "
            "to specific sections. Without headings, screen reader users must listen to "
            "the entire document to find what they need."
        ),
        "fix_steps": [
            "Open the source document in the authoring application",
            "Apply heading styles (Heading 1, Heading 2, etc.) instead of bold/large text",
            "Ensure headings follow a logical hierarchy (H1 > H2 > H3, no skipping)",
            "Re-export the PDF with the 'Tagged PDF' option enabled",
        ],
        "has_inline_tool": False,
    },
    "1.3.1": {
        "title": "Info and Relationships",
        "why_it_matters": (
            "Structure conveyed through visual formatting (tables, lists, sections) must "
            "also be conveyed programmatically through proper tags. Without this, screen "
            "readers cannot communicate the document's structure to users."
        ),
        "fix_steps": [
            "For tables: ensure header cells use TH tags with scope attributes",
            "For lists: use L, LI, Lbl, and LBody tags",
            "For sections: use appropriate tags (Part, Sect, Art) to group related content",
            "Open the Tags panel in Acrobat to review and correct the tag structure",
            "Save and re-validate",
        ],
        "has_inline_tool": False,
    },
}


def _default_guidance(issue: ValidationIssue) -> Dict:
    """Generate fallback guidance for issues not in ISSUE_GUIDANCE."""
    return {
        "title": f"WCAG {issue.criterion}",
        "why_it_matters": (
            "This criterion ensures that the document is accessible to users with "
            "disabilities. Fixing this issue improves the overall accessibility and "
            "compliance of your PDF."
        ),
        "fix_steps": [
            issue.suggestion or "Review and address this issue manually",
            "Consult the WCAG documentation for criterion " + issue.criterion,
            "Re-validate the document after making changes",
        ],
        "has_inline_tool": False,
    }


class GuidedFixWizard(QDialog):
    """Step-by-step wizard for guiding users through non-auto-fixable issues."""

    # Signals
    navigate_to_page = pyqtSignal(int)
    inline_fix_applied = pyqtSignal(object, str)  # (ValidationIssue, fix_value)
    open_reading_order = pyqtSignal(int)  # page number
    open_walkthrough = pyqtSignal(str)  # walkthrough_id

    def __init__(self, issues: List[ValidationIssue], parent=None):
        super().__init__(parent)
        self._issues = WCAGValidator.prioritize_issues(issues)
        self._current_index = 0

        self._setup_ui()
        if self._issues:
            self._update_content()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Guided Fix Wizard - Accessible PDF Toolkit")
        self.setMinimumSize(650, 550)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS.BACKGROUND};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setMinimum(0)
        self._progress.setMaximum(max(len(self._issues), 1))
        self._progress.setValue(1)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(8)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS.SURFACE};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS.PRIMARY};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self._progress)

        # Step counter
        self._step_label = QLabel()
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._step_label.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 11pt;")
        layout.addWidget(self._step_label)

        # Issue header row: severity badge + criterion + "Go to Page" button
        header_row = QHBoxLayout()

        self._severity_badge = QLabel()
        self._severity_badge.setFixedWidth(80)
        self._severity_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._severity_badge.setStyleSheet(f"""
            font-size: 10pt;
            font-weight: bold;
            border-radius: 4px;
            padding: 4px 8px;
        """)
        header_row.addWidget(self._severity_badge)

        self._criterion_label = QLabel()
        self._criterion_label.setStyleSheet(f"""
            color: {COLORS.TEXT_PRIMARY};
            font-size: 14pt;
            font-weight: bold;
        """)
        header_row.addWidget(self._criterion_label, 1)

        self._go_to_page_btn = QPushButton("Go to Page")
        self._go_to_page_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}
        """)
        self._go_to_page_btn.clicked.connect(self._on_navigate)
        header_row.addWidget(self._go_to_page_btn)

        layout.addLayout(header_row)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {COLORS.BORDER};
                border-radius: 8px;
                background-color: {COLORS.SURFACE};
            }}
        """)

        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(20, 20, 20, 20)
        self._content_layout.setSpacing(14)

        # "What is wrong" section
        what_header = QLabel("What is wrong")
        what_header.setStyleSheet(f"color: {COLORS.ERROR}; font-size: 13pt; font-weight: bold;")
        self._content_layout.addWidget(what_header)

        self._what_label = QLabel()
        self._what_label.setWordWrap(True)
        self._what_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 12pt; padding-left: 8px;")
        self._content_layout.addWidget(self._what_label)

        # "Why it matters" section
        why_header = QLabel("Why it matters")
        why_header.setStyleSheet(f"color: {COLORS.INFO}; font-size: 13pt; font-weight: bold; padding-top: 8px;")
        self._content_layout.addWidget(why_header)

        self._why_label = QLabel()
        self._why_label.setWordWrap(True)
        self._why_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 11pt; padding-left: 8px; line-height: 1.4;")
        self._content_layout.addWidget(self._why_label)

        # "How to fix it" section
        how_header = QLabel("How to fix it")
        how_header.setStyleSheet(f"color: {COLORS.SUCCESS}; font-size: 13pt; font-weight: bold; padding-top: 8px;")
        self._content_layout.addWidget(how_header)

        self._how_label = QLabel()
        self._how_label.setWordWrap(True)
        self._how_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 11pt; padding-left: 8px; line-height: 1.4;")
        self._content_layout.addWidget(self._how_label)

        # Inline fix tool (conditional, hidden by default)
        self._inline_frame = QFrame()
        self._inline_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND_ALT};
                border: 1px solid {COLORS.PRIMARY};
                border-radius: 6px;
                padding: 12px;
            }}
        """)
        inline_layout = QVBoxLayout(self._inline_frame)
        inline_layout.setSpacing(8)

        inline_title = QLabel("Quick Fix")
        inline_title.setStyleSheet(f"color: {COLORS.PRIMARY_LIGHT}; font-size: 12pt; font-weight: bold;")
        inline_layout.addWidget(inline_title)

        self._inline_description = QLabel("Enter replacement link text:")
        self._inline_description.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 11pt;")
        inline_layout.addWidget(self._inline_description)

        input_row = QHBoxLayout()
        self._inline_input = QLineEdit()
        self._inline_input.setPlaceholderText("Enter descriptive text...")
        self._inline_input.setStyleSheet(f"""
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
        """)
        input_row.addWidget(self._inline_input, 1)

        self._apply_fix_btn = QPushButton("Apply Fix")
        self._apply_fix_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.SUCCESS};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #16A34A;
            }}
        """)
        self._apply_fix_btn.clicked.connect(self._on_inline_fix_apply)
        input_row.addWidget(self._apply_fix_btn)

        inline_layout.addLayout(input_row)
        self._inline_frame.setVisible(False)
        self._content_layout.addWidget(self._inline_frame)

        # Reading order fix tool (conditional, hidden by default)
        self._reading_order_frame = QFrame()
        self._reading_order_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND_ALT};
                border: 1px solid {COLORS.PRIMARY};
                border-radius: 6px;
                padding: 12px;
            }}
        """)
        ro_layout = QVBoxLayout(self._reading_order_frame)
        ro_layout.setSpacing(8)

        ro_title = QLabel("Fix Reading Order")
        ro_title.setStyleSheet(
            f"color: {COLORS.PRIMARY_LIGHT}; font-size: 12pt; font-weight: bold;"
        )
        ro_layout.addWidget(ro_title)

        ro_desc = QLabel(
            "Open the Reading Order Editor to visually reorder elements on this page."
        )
        ro_desc.setWordWrap(True)
        ro_desc.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 11pt;")
        ro_layout.addWidget(ro_desc)

        self._fix_reading_order_btn = QPushButton("Fix Reading Order")
        self._fix_reading_order_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY_DARK};
            }}
        """)
        self._fix_reading_order_btn.clicked.connect(self._on_open_reading_order)
        ro_layout.addWidget(self._fix_reading_order_btn)

        self._reading_order_frame.setVisible(False)
        self._content_layout.addWidget(self._reading_order_frame)

        # Walkthrough frame (for Show Me walkthroughs)
        self._walkthrough_frame = QFrame()
        self._walkthrough_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND_ALT};
                border: 1px solid {COLORS.ACCENT};
                border-radius: 6px;
                padding: 12px;
            }}
        """)
        wt_layout = QVBoxLayout(self._walkthrough_frame)
        wt_layout.setSpacing(8)

        wt_title = QLabel("External Tool Required")
        wt_title.setStyleSheet(
            f"color: {COLORS.ACCENT}; font-size: 12pt; font-weight: bold;"
        )
        wt_layout.addWidget(wt_title)

        wt_desc = QLabel("This issue requires hands-on work in an external tool.")
        wt_desc.setWordWrap(True)
        wt_desc.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 11pt;")
        wt_layout.addWidget(wt_desc)

        self._walkthrough_buttons_layout = QVBoxLayout()
        wt_layout.addLayout(self._walkthrough_buttons_layout)

        self._walkthrough_frame.setVisible(False)
        self._content_layout.addWidget(self._walkthrough_frame)

        self._content_layout.addStretch()
        scroll.setWidget(self._content_widget)
        layout.addWidget(scroll, 1)

        # Navigation row: Close | spacer | Previous | Next/Finish | Skip
        nav_layout = QHBoxLayout()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: none;
                border: none;
                color: {COLORS.TEXT_SECONDARY};
                text-decoration: underline;
                font-size: 11pt;
                padding: 8px;
            }}
            QPushButton:hover {{
                color: {COLORS.PRIMARY};
            }}
        """)
        nav_layout.addWidget(close_btn)

        nav_layout.addStretch()

        self._prev_btn = QPushButton("\u2190 Previous")
        self._prev_btn.clicked.connect(self._on_prev)
        self._prev_btn.setStyleSheet(self._nav_button_style(primary=False))
        self._prev_btn.setFixedWidth(120)
        nav_layout.addWidget(self._prev_btn)

        self._next_btn = QPushButton("Next \u2192")
        self._next_btn.clicked.connect(self._on_next)
        self._next_btn.setStyleSheet(self._nav_button_style(primary=True))
        self._next_btn.setFixedWidth(120)
        nav_layout.addWidget(self._next_btn)

        self._skip_btn = QPushButton("Skip")
        self._skip_btn.clicked.connect(self._on_next)
        self._skip_btn.setStyleSheet(self._nav_button_style(primary=False))
        self._skip_btn.setFixedWidth(80)
        nav_layout.addWidget(self._skip_btn)

        layout.addLayout(nav_layout)

    @staticmethod
    def _nav_button_style(primary: bool = False) -> str:
        """Get navigation button stylesheet."""
        if primary:
            return f"""
                QPushButton {{
                    background-color: {COLORS.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 12pt;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.PRIMARY_DARK};
                }}
                QPushButton:disabled {{
                    background-color: {COLORS.SURFACE};
                    color: {COLORS.TEXT_DISABLED};
                }}
            """
        return f"""
            QPushButton {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.BACKGROUND_ALT};
            }}
            QPushButton:disabled {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_DISABLED};
            }}
        """

    def _update_content(self) -> None:
        """Refresh all UI elements for the current issue."""
        if not self._issues:
            return

        issue = self._issues[self._current_index]
        guidance = ISSUE_GUIDANCE.get(issue.criterion) or _default_guidance(issue)

        # Progress
        self._progress.setValue(self._current_index + 1)
        self._step_label.setText(f"Issue {self._current_index + 1} of {len(self._issues)}")

        # Severity badge
        severity_colors = {
            IssueSeverity.ERROR: (COLORS.ERROR, "ERROR"),
            IssueSeverity.WARNING: (COLORS.WARNING, "WARNING"),
            IssueSeverity.INFO: (COLORS.INFO, "INFO"),
        }
        color, label = severity_colors.get(issue.severity, (COLORS.INFO, "INFO"))
        self._severity_badge.setText(label)
        self._severity_badge.setStyleSheet(f"""
            background-color: {color};
            color: white;
            font-size: 10pt;
            font-weight: bold;
            border-radius: 4px;
            padding: 4px 8px;
        """)

        # Criterion label
        title = guidance.get("title", f"WCAG {issue.criterion}")
        self._criterion_label.setText(f"[{issue.criterion}] {title}")

        # Go to Page button
        if issue.page:
            self._go_to_page_btn.setText(f"Go to Page {issue.page}")
            self._go_to_page_btn.setVisible(True)
        else:
            self._go_to_page_btn.setVisible(False)

        # Content sections
        self._what_label.setText(issue.message)
        self._why_label.setText(guidance.get("why_it_matters", ""))

        # Numbered fix steps
        steps = guidance.get("fix_steps", [])
        steps_text = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(steps))
        self._how_label.setText(steps_text)

        # Enrich "Why it matters" with WCAG_EXPLAINER if available
        explainer = WCAG_EXPLAINER.get(issue.criterion)
        if explainer:
            why_text = guidance.get("why_it_matters", "")
            why_text += (
                f"\n\nWhat this means: {explainer['plain_language']}"
                f"\nWho it affects: {explainer['who_it_affects']}"
                f"\nReal-world barrier: {explainer['real_world_barrier']}"
            )
            self._why_label.setText(why_text)

        # Inline fix tool
        has_inline = guidance.get("has_inline_tool", False)
        self._inline_frame.setVisible(has_inline)
        if has_inline:
            self._inline_input.clear()
            if issue.element:
                self._inline_input.setPlaceholderText(
                    f"Replace '{issue.element}' with descriptive text..."
                )

        # Reading order fix tool (for 1.3.2 issues with a page)
        self._reading_order_frame.setVisible(
            issue.criterion == "1.3.2" and bool(issue.page)
        )

        # Walkthrough buttons (Show Me)
        # Clear previous buttons
        while self._walkthrough_buttons_layout.count() > 0:
            item = self._walkthrough_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        wt_ids = CRITERION_TO_WALKTHROUGH.get(issue.criterion, [])
        self._walkthrough_frame.setVisible(bool(wt_ids))
        for wt_id in wt_ids:
            wt = WALKTHROUGHS.get(wt_id)
            if not wt:
                continue
            btn = QPushButton(f"Show Me: {wt.title}")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.ACCENT};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 11pt;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.ACCENT_DARK};
                }}
            """)
            current_wt_id = wt_id
            btn.clicked.connect(lambda checked, wid=current_wt_id: self._on_open_walkthrough(wid))
            self._walkthrough_buttons_layout.addWidget(btn)

        # Navigation buttons
        self._prev_btn.setEnabled(self._current_index > 0)
        if self._current_index >= len(self._issues) - 1:
            self._next_btn.setText("Finish \u2713")
            self._skip_btn.setVisible(False)
        else:
            self._next_btn.setText("Next \u2192")
            self._skip_btn.setVisible(True)

    def _on_navigate(self) -> None:
        """Emit navigate_to_page for the current issue's page."""
        if not self._issues:
            return
        issue = self._issues[self._current_index]
        if issue.page:
            self.navigate_to_page.emit(issue.page)

    def _on_next(self) -> None:
        """Advance to the next issue or finish."""
        if self._current_index >= len(self._issues) - 1:
            self.accept()
        else:
            self._current_index += 1
            self._update_content()

    def _on_prev(self) -> None:
        """Go back to the previous issue."""
        if self._current_index > 0:
            self._current_index -= 1
            self._update_content()

    def _on_inline_fix_apply(self) -> None:
        """Emit inline_fix_applied with the current issue and input value."""
        if not self._issues:
            return
        value = self._inline_input.text().strip()
        if not value:
            return
        issue = self._issues[self._current_index]
        self.inline_fix_applied.emit(issue, value)
        logger.info(f"Inline fix applied for [{issue.criterion}]: '{value}'")
        # Auto-advance to next issue
        self._on_next()

    def _on_open_reading_order(self) -> None:
        """Emit open_reading_order for the current issue's page."""
        if not self._issues:
            return
        issue = self._issues[self._current_index]
        if issue.page:
            self.open_reading_order.emit(issue.page)

    def _on_open_walkthrough(self, walkthrough_id: str) -> None:
        """Emit open_walkthrough signal."""
        self.open_walkthrough.emit(walkthrough_id)
