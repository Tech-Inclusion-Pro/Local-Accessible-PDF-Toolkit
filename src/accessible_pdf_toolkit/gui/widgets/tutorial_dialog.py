"""
Tutorial dialog for guiding users through the application features.
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
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ...utils.constants import COLORS
from ...utils.logger import get_logger

logger = get_logger(__name__)


# Tutorial steps with detailed instructions
TUTORIAL_STEPS: List[Dict[str, str]] = [
    {
        "title": "Welcome to Accessible PDF Toolkit!",
        "description": (
            "This tutorial will guide you through the main features of the application. "
            "You'll learn how to make your PDFs WCAG compliant and accessible to everyone."
        ),
        "how_to_use": (
            "Click 'Next' to continue through the tutorial, or 'Skip' to close it at any time. "
            "You can always access this tutorial again by clicking the 'Tutorial' button."
        ),
        "icon": "\u2630",  # trigram / menu lines
    },
    {
        "title": "Navigation Panel (Left Side)",
        "description": (
            "The Navigation Panel shows a thumbnail view of all pages in your PDF. "
            "It also includes page controls, zoom settings, and a search feature to find text in your document."
        ),
        "how_to_use": (
            "\u2022 Click on a page thumbnail to jump to that page\n"
            "\u2022 Use the zoom slider or +/- buttons to change zoom level\n"
            "\u2022 Type in the search box to find text in your PDF\n"
            "\u2022 Use the page number input to go to a specific page"
        ),
        "icon": "\u2750",  # upper right drop-shadowed square
    },
    {
        "title": "PDF Viewer (Center)",
        "description": (
            "The PDF Viewer displays your document with colored overlays highlighting accessibility issues. "
            "Different colors indicate different types of issues that need attention."
        ),
        "how_to_use": (
            "\u2022 Purple overlays = Headings\n"
            "\u2022 Yellow overlays = Images needing alt text\n"
            "\u2022 Green overlays = Tables\n"
            "\u2022 Orange overlays = Links\n"
            "\u2022 Red overlays = Issues needing immediate attention\n\n"
            "Click on any overlay to see its details in the AI Suggestions panel."
        ),
        "icon": "\u25A2",  # white square with rounded corners
    },
    {
        "title": "AI Suggestions Panel (Right Side)",
        "description": (
            "The AI Suggestions Panel shows automatically detected accessibility issues and suggested fixes. "
            "Issues are organized into categories: Document Properties, Headings, Images, Tables, Links, and Reading Order."
        ),
        "how_to_use": (
            "\u2022 Expand each section by clicking its header\n"
            "\u2022 Review each suggestion - the AI will propose fixes for issues\n"
            "\u2022 You can edit the AI's suggestion before applying it\n"
            "\u2022 Click 'Apply' to accept a fix, 'Edit' to modify it, or 'Skip' to ignore it"
        ),
        "icon": "\u2662",  # white diamond suit
    },
    {
        "title": "Review Mode Options",
        "description": (
            "Choose how you want to review AI suggestions:\n\n"
            "\u2022 Auto-Accept Mode: Automatically applies all AI suggestions (faster but less control)\n"
            "\u2022 Manual Review Mode: Review each suggestion individually (recommended for important documents)"
        ),
        "how_to_use": (
            "Select your preferred mode at the top of the AI Suggestions panel. "
            "Manual Review is selected by default for maximum control over changes."
        ),
        "icon": "\u2699",  # gear
    },
    {
        "title": "Adding Alt Text to Images",
        "description": (
            "Images without alt text are a major accessibility barrier. "
            "The AI will suggest descriptive alt text for each image in your document."
        ),
        "how_to_use": (
            "1. Open the 'Images' section in AI Suggestions\n"
            "2. Review the AI-generated alt text suggestion\n"
            "3. Edit the text if needed (make it descriptive but concise)\n"
            "4. Click 'Apply' to add the alt text to the image\n\n"
            "Good alt text describes the image's content and purpose, not just 'an image'."
        ),
        "icon": "\u29C9",  # two joined squares
    },
    {
        "title": "Fixing Heading Structure",
        "description": (
            "Proper heading structure helps screen reader users navigate your document. "
            "Headings should be hierarchical (H1 \u2192 H2 \u2192 H3) without skipping levels."
        ),
        "how_to_use": (
            "1. Open the 'Headings' section in AI Suggestions\n"
            "2. Review detected heading issues (wrong levels, skipped levels)\n"
            "3. The AI will suggest the correct heading level\n"
            "4. Apply the fix or manually adjust the heading level"
        ),
        "icon": "\u2261",  # identical to (triple bar)
    },
    {
        "title": "Table Accessibility",
        "description": (
            "Tables need proper headers so screen readers can announce column/row information. "
            "The AI detects tables and suggests header row/column designations."
        ),
        "how_to_use": (
            "1. Open the 'Tables' section in AI Suggestions\n"
            "2. Review each table detected in the document\n"
            "3. Confirm or adjust which rows/columns are headers\n"
            "4. Apply the changes to make tables accessible"
        ),
        "icon": "\u2637",  # trigram for earth (grid-like)
    },
    {
        "title": "Link Text",
        "description": (
            "Links should have descriptive text, not just 'click here' or bare URLs. "
            "The AI will flag links that need better descriptions."
        ),
        "how_to_use": (
            "1. Open the 'Links' section in AI Suggestions\n"
            "2. Review links with vague or missing text\n"
            "3. Edit the suggested link text to be more descriptive\n"
            "4. Apply the change"
        ),
        "icon": "\u2197",  # north east arrow
    },
    {
        "title": "Batch Actions",
        "description": (
            "You can apply multiple fixes at once using the batch action buttons at the bottom of the AI Suggestions panel."
        ),
        "how_to_use": (
            "\u2022 'Select All' / 'Deselect All' - Check/uncheck all items\n"
            "\u2022 'Apply Selected' - Apply only the checked items\n"
            "\u2022 'Apply All Remaining' - Apply all unapplied suggestions\n"
            "\u2022 'Undo Last' - Reverse the most recent change\n"
            "\u2022 'Preview Changes' - See what will be modified before saving"
        ),
        "icon": "\u2611",  # ballot box with check
    },
    {
        "title": "Saving Your Work",
        "description": (
            "Your changes are automatically saved every 60 seconds while you work. "
            "You can also manually save at any time."
        ),
        "how_to_use": (
            "\u2022 Click 'Save & Export PDF' in the AI Suggestions panel\n"
            "\u2022 Or use Ctrl+S (Cmd+S on Mac) to save\n"
            "\u2022 Choose 'Save As' to create a new accessible version\n"
            "\u2022 Auto-save keeps your work safe (every 60 seconds)\n\n"
            "A '_tagged' suffix is added to the filename by default."
        ),
        "icon": "\u2193",  # downwards arrow (save)
    },
    {
        "title": "You're Ready!",
        "description": (
            "You now know the basics of making PDFs accessible with this toolkit!\n\n"
            "Remember:\n"
            "\u2022 All images need alt text\n"
            "\u2022 Headings should be properly structured\n"
            "\u2022 Tables need headers\n"
            "\u2022 Links need descriptive text"
        ),
        "how_to_use": (
            "Start by reviewing the AI Suggestions on the right panel. "
            "Work through each category to ensure your document is fully accessible.\n\n"
            "Good luck making the web more accessible!"
        ),
        "icon": "\u2605",  # black star
    },
]


class TutorialDialog(QDialog):
    """Step-by-step tutorial dialog for the application."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_step = 0
        self._steps = TUTORIAL_STEPS

        self._setup_ui()
        self._update_content()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Tutorial - Accessible PDF Toolkit")
        self.setFixedSize(600, 500)
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
        self._progress.setMaximum(len(self._steps))
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

        # Content frame
        content_frame = QFrame()
        content_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.SURFACE};
                border: 1px solid {COLORS.BORDER};
                border-radius: 8px;
            }}
        """)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)

        # Icon and title row
        title_row = QHBoxLayout()

        self._icon_label = QLabel()
        self._icon_label.setStyleSheet("font-size: 32pt;")
        self._icon_label.setFixedWidth(60)
        title_row.addWidget(self._icon_label)

        self._title_label = QLabel()
        self._title_label.setWordWrap(True)
        self._title_label.setStyleSheet(f"""
            font-size: 18pt;
            font-weight: bold;
            color: {COLORS.PRIMARY};
        """)
        title_row.addWidget(self._title_label, 1)

        content_layout.addLayout(title_row)

        # Description
        self._description_label = QLabel()
        self._description_label.setWordWrap(True)
        self._description_label.setStyleSheet(f"""
            color: {COLORS.TEXT_PRIMARY};
            font-size: 12pt;
            line-height: 1.5;
        """)
        content_layout.addWidget(self._description_label)

        # How to use section
        how_to_header = QLabel("How to use:")
        how_to_header.setStyleSheet(f"""
            color: {COLORS.PRIMARY_LIGHT};
            font-size: 13pt;
            font-weight: bold;
            padding-top: 8px;
        """)
        content_layout.addWidget(how_to_header)

        self._how_to_label = QLabel()
        self._how_to_label.setWordWrap(True)
        self._how_to_label.setStyleSheet(f"""
            color: {COLORS.TEXT_PRIMARY};
            font-size: 11pt;
            line-height: 1.4;
            padding-left: 8px;
        """)
        content_layout.addWidget(self._how_to_label)

        content_layout.addStretch()
        layout.addWidget(content_frame, 1)

        # Navigation buttons
        button_layout = QHBoxLayout()

        self._skip_btn = QPushButton("Skip Tutorial")
        self._skip_btn.clicked.connect(self.reject)
        self._skip_btn.setStyleSheet(f"""
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
        button_layout.addWidget(self._skip_btn)

        button_layout.addStretch()

        self._prev_btn = QPushButton("\u2190 Previous")
        self._prev_btn.clicked.connect(self._prev_step)
        self._prev_btn.setStyleSheet(self._get_button_style(primary=False))
        self._prev_btn.setFixedWidth(120)
        button_layout.addWidget(self._prev_btn)

        self._next_btn = QPushButton("Next →")
        self._next_btn.clicked.connect(self._next_step)
        self._next_btn.setStyleSheet(self._get_button_style(primary=True))
        self._next_btn.setFixedWidth(120)
        button_layout.addWidget(self._next_btn)

        layout.addLayout(button_layout)

    def _get_button_style(self, primary: bool = False) -> str:
        """Get button stylesheet."""
        if primary:
            return f"""
                QPushButton {{
                    background-color: {COLORS.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 12px 24px;
                    font-size: 13pt;
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
                padding: 12px 24px;
                font-size: 13pt;
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
        """Update the dialog content for the current step."""
        step = self._steps[self._current_step]

        self._icon_label.setText(step.get("icon", "\u2630"))
        self._title_label.setText(step["title"])
        self._description_label.setText(step["description"])
        self._how_to_label.setText(step["how_to_use"])

        # Update progress
        self._progress.setValue(self._current_step + 1)
        self._step_label.setText(f"Step {self._current_step + 1} of {len(self._steps)}")

        # Update button states
        self._prev_btn.setEnabled(self._current_step > 0)

        if self._current_step >= len(self._steps) - 1:
            self._next_btn.setText("Finish \u2713")
        else:
            self._next_btn.setText("Next \u2192")

    def _next_step(self) -> None:
        """Go to the next step."""
        if self._current_step >= len(self._steps) - 1:
            self.accept()
        else:
            self._current_step += 1
            self._update_content()

    def _prev_step(self) -> None:
        """Go to the previous step."""
        if self._current_step > 0:
            self._current_step -= 1
            self._update_content()
