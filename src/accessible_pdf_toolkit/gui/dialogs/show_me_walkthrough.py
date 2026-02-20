"""
Show Me walkthrough dialog — step-by-step guided walkthroughs for tasks
requiring external tools like Adobe Acrobat Pro.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QProgressBar,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...utils.constants import COLORS


@dataclass
class WalkthroughStep:
    """A single step in a walkthrough."""
    title: str
    body: str
    is_done: bool = False


@dataclass
class Walkthrough:
    """A complete walkthrough with metadata."""
    id: str
    title: str
    steps: List[WalkthroughStep] = field(default_factory=list)


# ── 7 Walkthroughs ──────────────────────────────────────────────────────────

WALKTHROUGHS: Dict[str, Walkthrough] = {

    "tag_structure": Walkthrough(
        id="tag_structure",
        title="Tag the Document Structure",
        steps=[
            WalkthroughStep(
                title="Open the Tags Panel",
                body="In Adobe Acrobat Pro, go to <b>View → Show/Hide → Navigation Panes → Tags</b>. "
                     "The Tags panel will open on the left side. If it is empty or says "
                     "\"No Tags Available,\" this document needs to be tagged from scratch.",
            ),
            WalkthroughStep(
                title="Run the Accessibility Check First",
                body="Go to <b>Tools → Accessibility → Full Check</b>. Run the check with all "
                     "options selected. This gives you a list of every issue before you begin "
                     "tagging so you work through them in order.",
            ),
            WalkthroughStep(
                title="Add Tags Automatically (Starting Point)",
                body="Go to <b>Tools → Accessibility → Autotag Document</b>. This gives you a "
                     "rough tag structure to work from. It will not be perfect — you will fix it "
                     "in the next steps.",
            ),
            WalkthroughStep(
                title="Open the Reading Order Tool",
                body="Go to <b>Tools → Accessibility → Reading Order</b>. Use this tool to click "
                     "on each content region and assign the correct tag type (Text, Figure, Table, "
                     "etc.). Work top-to-bottom, left-to-right.",
            ),
            WalkthroughStep(
                title="Fix the Tags Tree Manually",
                body="In the Tags panel, expand the tree. Right-click any tag to change its type. "
                     "Drag tags to reorder them. Use the tag types your AI report identified as "
                     "incorrect and apply the corrections from your heading outline.",
            ),
            WalkthroughStep(
                title="Save and Re-Run the Checker",
                body="Save your file (<b>File → Save</b>) and run <b>Tools → Accessibility → "
                     "Full Check</b> again. Confirm the structure errors are resolved before "
                     "moving to the next remediation task.",
            ),
        ],
    ),

    "reading_order": Walkthrough(
        id="reading_order",
        title="Fix Reading Order",
        steps=[
            WalkthroughStep(
                title="Open the Order Panel",
                body="Go to <b>View → Show/Hide → Navigation Panes → Order</b>. This panel "
                     "shows the order in which a screen reader will read the content — not the "
                     "visual layout.",
            ),
            WalkthroughStep(
                title="Compare to the Visual Layout",
                body="Scroll through the Order panel while looking at the page. Every numbered "
                     "region should flow top-to-bottom and left-to-right the way you intend it "
                     "to be read. If sidebars, callout boxes, or multi-column content appears "
                     "out of sequence, note which region numbers need to move.",
            ),
            WalkthroughStep(
                title="Drag to Reorder",
                body="In the Order panel, click and drag content regions into the correct "
                     "sequence. The AI-generated reading order map from your report shows the "
                     "target order — use it as your guide.",
            ),
            WalkthroughStep(
                title="Verify with Read Out Loud",
                body="Go to <b>View → Read Out Loud → Activate Read Out Loud</b>, then press "
                     "<b>Shift + Ctrl + B</b> to read the page from the beginning. Listen for "
                     "any content that sounds out of place. Fix and repeat until the spoken "
                     "order matches your intent.",
            ),
        ],
    ),

    "artifacts": Walkthrough(
        id="artifacts",
        title="Apply Artifacts",
        steps=[
            WalkthroughStep(
                title="Open the Reading Order Tool",
                body="Go to <b>Tools → Accessibility → Reading Order</b>. On the right side of "
                     "this panel you will see a \"Background/Artifact\" button.",
            ),
            WalkthroughStep(
                title="Select the Decorative Element",
                body="Click and drag a rectangle around the decorative element on the page — "
                     "the border, logo repetition, background graphic, or design line. It will "
                     "highlight in blue.",
            ),
            WalkthroughStep(
                title="Apply the Artifact Tag",
                body="Click <b>Background/Artifact</b> in the Reading Order panel. The element "
                     "will no longer appear in the Tags tree and screen readers will skip it. "
                     "Repeat for each decorative element flagged in your AI report.",
            ),
        ],
    ),

    "table_headers": Walkthrough(
        id="table_headers",
        title="Table Headers and Scope",
        steps=[
            WalkthroughStep(
                title="Select the Table in the Tags Panel",
                body="In the Tags panel, expand the tree until you find the <b>&lt;Table&gt;</b> "
                     "tag for the table you are fixing. Expand it to see the row "
                     "(<b>&lt;TR&gt;</b>) and cell (<b>&lt;TD&gt;</b> or <b>&lt;TH&gt;</b>) "
                     "tags inside.",
            ),
            WalkthroughStep(
                title="Change TD to TH for Header Cells",
                body="Right-click the <b>&lt;TD&gt;</b> tag for a header cell. Choose "
                     "<b>Properties</b>. In the Tag tab, change the Type from TD to TH. "
                     "Repeat for every header cell in the header row or column.",
            ),
            WalkthroughStep(
                title="Set the Scope Attribute",
                body="With the <b>&lt;TH&gt;</b> tag selected, go to <b>Options → Properties → "
                     "Tag Tab → Edit Attribute Objects</b>. Add a <b>Scope</b> attribute: use "
                     "\"Column\" for column headers, \"Row\" for row headers. Use the scope "
                     "values from your AI report.",
            ),
            WalkthroughStep(
                title="Verify the Table Summary",
                body="If the table is complex, right-click the <b>&lt;Table&gt;</b> tag, open "
                     "Properties, and add a <b>Summary</b> attribute that briefly describes "
                     "the table's structure. This helps screen reader users understand what "
                     "they are navigating before entering the table.",
            ),
        ],
    ),

    "tab_order": Walkthrough(
        id="tab_order",
        title="Set Tab Order for Forms",
        steps=[
            WalkthroughStep(
                title="Open Page Properties",
                body="Right-click the page thumbnail in the Pages panel on the left. Select "
                     "<b>Page Properties</b>. Go to the <b>Tab Order</b> tab.",
            ),
            WalkthroughStep(
                title="Set to Use Document Structure",
                body="Select <b>Use Document Structure</b> from the tab order options. This "
                     "ties keyboard navigation to your logical reading order rather than the "
                     "visual position of fields on the page.",
            ),
            WalkthroughStep(
                title="Test with Tab Key",
                body="Close properties and go to <b>Tools → Prepare Form</b>. Click into the "
                     "first form field and press Tab repeatedly. Confirm that focus moves "
                     "through fields in the order shown in your AI report. Fix any fields that "
                     "appear in the wrong position by dragging them in the Fields panel.",
            ),
        ],
    ),

    "security": Walkthrough(
        id="security",
        title="Security Settings for Screen Readers",
        steps=[
            WalkthroughStep(
                title="Open Document Security",
                body="Go to <b>File → Properties → Security tab</b>. Check what security method "
                     "is applied. If it says \"No Security,\" screen readers already have full "
                     "access — skip to your next task. If it shows Password Security or "
                     "Certificate Security, continue.",
            ),
            WalkthroughStep(
                title="Edit the Security Settings",
                body="Click <b>Change Settings</b>. In the Permissions section, scroll to find "
                     "<b>\"Enable text access for screen reader devices for the visually "
                     "impaired.\"</b> Make sure this checkbox is selected even if other editing "
                     "permissions are restricted.",
            ),
            WalkthroughStep(
                title="Save the File",
                body="Click OK, apply the password if required, and save the file. Re-open "
                     "the file and re-run the Accessibility Checker to confirm \"Document is "
                     "not image-only\" and \"Permission Flag\" now pass.",
            ),
        ],
    ),

    "screen_reader_testing": Walkthrough(
        id="screen_reader_testing",
        title="Run Screen Reader Testing",
        steps=[
            WalkthroughStep(
                title="Download and Open NVDA (Free, Windows)",
                body="Download NVDA at nvaccess.org and install it. Open your PDF in Adobe "
                     "Acrobat. Press <b>NVDA + Spacebar</b> to enter browse mode.",
            ),
            WalkthroughStep(
                title="Navigate by Headings",
                body="Press <b>H</b> to jump heading by heading through the document. Confirm "
                     "that all headings from your AI outline are announced correctly and in "
                     "the right order. Press <b>Shift + H</b> to move backwards. Note any "
                     "headings that are skipped or announced incorrectly.",
            ),
            WalkthroughStep(
                title="Navigate by Links and Form Fields",
                body="Press <b>K</b> to jump between links. Press <b>F</b> to jump between "
                     "form fields. Confirm that each link and field announces a descriptive "
                     "label matching your AI-generated text. Note anything announced as "
                     "\"blank,\" \"link,\" or a raw URL.",
            ),
            WalkthroughStep(
                title="Read the Full Document",
                body="Press <b>NVDA + Down Arrow</b> to read from the beginning. Listen for "
                     "the full document flow. Log any content that sounds out of order, "
                     "skipped, garbled, or confusing. Return to the relevant Show Me guide "
                     "for any issue you find.",
            ),
        ],
    ),
}


# ── Mapping from WCAG criterion to relevant walkthroughs ─────────────────────

CRITERION_TO_WALKTHROUGH: Dict[str, List[str]] = {
    "1.3.1": ["tag_structure", "table_headers", "artifacts"],
    "1.3.2": ["reading_order"],
    "2.4.1": ["tag_structure"],
    "2.4.4": [],  # AI-handled
    "2.4.6": ["tag_structure"],
    "4.1.2": ["tab_order"],
    "_security": ["security"],
    "_testing": ["screen_reader_testing"],
}


# ── ShowMeWalkthroughDialog ──────────────────────────────────────────────────

class ShowMeWalkthroughDialog(QDialog):
    """Step-by-step walkthrough dialog for external tool tasks."""

    walkthrough_completed = pyqtSignal(str)  # walkthrough_id

    def __init__(self, walkthrough: Walkthrough, parent=None):
        super().__init__(parent)
        self._walkthrough = walkthrough
        self._current_step = 0

        self.setWindowTitle(f"Show Me — {walkthrough.title}")
        self.setMinimumSize(600, 450)
        self.setStyleSheet(f"QDialog {{ background-color: {COLORS.BACKGROUND}; }}")

        self._setup_ui()
        self._update_step()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setMinimum(0)
        self._progress.setMaximum(len(self._walkthrough.steps))
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
        self._counter_label = QLabel()
        self._counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._counter_label.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 11pt;")
        layout.addWidget(self._counter_label)

        # Step title
        self._title_label = QLabel()
        self._title_label.setStyleSheet(f"""
            color: {COLORS.TEXT_PRIMARY};
            font-size: 16pt;
            font-weight: bold;
        """)
        layout.addWidget(self._title_label)

        # Content frame
        content_frame = QFrame()
        content_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.SURFACE};
                border: 1px solid {COLORS.BORDER};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        content_layout = QVBoxLayout(content_frame)

        self._body_label = QLabel()
        self._body_label.setWordWrap(True)
        self._body_label.setTextFormat(Qt.TextFormat.RichText)
        self._body_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 12pt; line-height: 1.5;")
        content_layout.addWidget(self._body_label)

        layout.addWidget(content_frame, 1)

        # Mark done / continue button
        self._action_btn = QPushButton("Mark Done and Continue")
        self._action_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 12pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY_DARK};
            }}
        """)
        self._action_btn.clicked.connect(self._on_mark_done)
        layout.addWidget(self._action_btn)

        # Close link
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: none;
                border: none;
                color: {COLORS.TEXT_SECONDARY};
                text-decoration: underline;
                font-size: 11pt;
                padding: 4px;
            }}
            QPushButton:hover {{ color: {COLORS.PRIMARY}; }}
        """)
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _update_step(self) -> None:
        """Refresh UI for the current step."""
        steps = self._walkthrough.steps
        idx = self._current_step

        self._progress.setValue(idx + 1)
        self._counter_label.setText(
            f"Step {idx + 1} of {len(steps)} — {self._walkthrough.title}"
        )
        self._title_label.setText(steps[idx].title)
        self._body_label.setText(steps[idx].body)

        if idx >= len(steps) - 1:
            self._action_btn.setText("Finish \u2713")
        else:
            self._action_btn.setText("Mark Done and Continue")

    def _on_mark_done(self) -> None:
        """Mark current step done and advance or finish."""
        steps = self._walkthrough.steps
        steps[self._current_step].is_done = True

        if self._current_step >= len(steps) - 1:
            self.walkthrough_completed.emit(self._walkthrough.id)
            self.accept()
        else:
            self._current_step += 1
            self._update_step()


# ── WalkthroughPickerDialog ──────────────────────────────────────────────────

class WalkthroughPickerDialog(QDialog):
    """Small dialog for choosing a walkthrough from a list."""

    def __init__(self, walkthrough_ids: List[str], parent=None):
        super().__init__(parent)
        self.selected_walkthrough_id: Optional[str] = None

        self.setWindowTitle("Choose a Walkthrough")
        self.setMinimumWidth(400)
        self.setStyleSheet(f"QDialog {{ background-color: {COLORS.BACKGROUND}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Choose a Walkthrough")
        title.setStyleSheet(f"""
            color: {COLORS.TEXT_PRIMARY};
            font-size: 16pt;
            font-weight: bold;
        """)
        layout.addWidget(title)

        for wt_id in walkthrough_ids:
            wt = WALKTHROUGHS.get(wt_id)
            if not wt:
                continue
            btn = QPushButton(f"{wt.title}  ({len(wt.steps)} steps)")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.SURFACE};
                    color: {COLORS.TEXT_PRIMARY};
                    border: 1px solid {COLORS.BORDER};
                    border-radius: 6px;
                    padding: 12px;
                    font-size: 12pt;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.PRIMARY};
                    color: white;
                }}
            """)
            current_id = wt_id
            btn.clicked.connect(lambda checked, wid=current_id: self._select(wid))
            layout.addWidget(btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: none;
                border: none;
                color: {COLORS.TEXT_SECONDARY};
                text-decoration: underline;
                font-size: 11pt;
                padding: 8px;
            }}
            QPushButton:hover {{ color: {COLORS.PRIMARY}; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _select(self, walkthrough_id: str) -> None:
        self.selected_walkthrough_id = walkthrough_id
        self.accept()
