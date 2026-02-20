"""
Constants and configuration values for Accessible PDF Toolkit.
"""

from pathlib import Path
from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, Any
import os
import sys

# Application Info
APP_NAME = "Accessible PDF Toolkit"
APP_VERSION = "1.3.0"
APP_AUTHOR = "Accessible PDF Toolkit Team"

# Paths
HOME_DIR = Path.home()
APP_DATA_DIR = HOME_DIR / ".accessible-pdf-toolkit"
CONFIG_FILE = APP_DATA_DIR / "config.yaml"
DATABASE_FILE = APP_DATA_DIR / "database.sqlite"
LOG_FILE = APP_DATA_DIR / "logs" / "app.log"
CACHE_DIR = APP_DATA_DIR / "cache"
TEMP_DIR = APP_DATA_DIR / "temp"

# Assets directory - handles both development and bundled PyInstaller app
if getattr(sys, 'frozen', False):
    # Running in a PyInstaller bundle
    _BASE_DIR = Path(sys._MEIPASS)
else:
    # Running in development
    _BASE_DIR = Path(__file__).parent.parent.parent.parent
ASSETS_DIR = _BASE_DIR / "assets"


# Brand Colors - Dark Theme Default for better visibility
@dataclass(frozen=True)
class BrandColors:
    """Brand color palette for the application - Dark theme."""

    # Primary colors - New Purple Palette
    PRIMARY = "#a23b84"          # Primary Purple
    PRIMARY_DARK = "#8a3270"     # Darker Primary
    PRIMARY_LIGHT = "#b85a9a"    # Lighter Primary

    # Secondary colors
    SECONDARY = "#3a2b95"        # Secondary Purple
    SECONDARY_DARK = "#2e2277"   # Darker Secondary
    SECONDARY_LIGHT = "#4d3cad"  # Lighter Secondary

    # Accent colors
    ACCENT = "#6f2fa6"           # Accent Purple
    ACCENT_DARK = "#5a2688"      # Darker Accent

    # Semantic colors
    SUCCESS = "#22C55E"          # Green 500
    WARNING = "#F59E0B"          # Amber 500
    ERROR = "#EF4444"            # Red 500
    INFO = "#3B82F6"             # Blue 500

    # Dark theme colors (now default)
    BACKGROUND = "#1a1a2e"       # Dark blue-gray
    BACKGROUND_ALT = "#16213e"   # Slightly lighter
    SURFACE = "#1f2847"          # Card/panel background
    BORDER = "#4a5568"           # Gray 600
    TEXT_PRIMARY = "#FFFFFF"     # White text
    TEXT_SECONDARY = "#CBD5E1"   # Light gray text
    TEXT_DISABLED = "#94A3B8"    # Slate 400

    # High contrast theme
    HC_BACKGROUND = "#000000"
    HC_TEXT = "#FFFFFF"
    HC_LINK = "#00FFFF"
    HC_FOCUS = "#FFFF00"

    # Input field colors
    INPUT_BG = "#2d3748"         # Dark input background
    INPUT_TEXT = "#FFFFFF"       # White input text
    INPUT_BORDER = "#4a5568"     # Gray border
    INPUT_FOCUS = "#3B82F6"      # Blue focus ring

    # Dark theme (kept for compatibility)
    DARK_BACKGROUND = "#1a1a2e"
    DARK_SURFACE = "#1f2847"
    DARK_TEXT = "#FFFFFF"
    DARK_BORDER = "#4a5568"


COLORS = BrandColors()


class WCAGLevel(Enum):
    """WCAG compliance levels."""
    A = "A"
    AA = "AA"
    AAA = "AAA"


class ComplianceStatus(Enum):
    """Document compliance status."""
    NOT_CHECKED = auto()
    COMPLIANT = auto()
    PARTIAL = auto()
    NON_COMPLIANT = auto()


class RemediationStatus(Enum):
    """Status of a remediation category."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


class ColorBlindMode(Enum):
    """Color blindness simulation / accommodation modes."""
    NONE = "none"
    DEUTERANOPIA = "deuteranopia"   # Green-blind
    PROTANOPIA = "protanopia"       # Red-blind
    TRITANOPIA = "tritanopia"       # Blue-blind
    MONOCHROME = "monochrome"       # Grayscale


class CustomCursorStyle(Enum):
    """Custom cursor style options for accessibility."""
    DEFAULT = "default"
    LARGE_BLACK = "large-black"
    LARGE_WHITE = "large-white"
    LARGE_CROSSHAIR = "large-crosshair"
    HIGH_VISIBILITY = "high-visibility"
    CURSOR_TRAIL = "cursor-trail"


class AIBackend(Enum):
    """Supported AI backends."""
    OLLAMA = "ollama"
    LM_STUDIO = "lmstudio"
    GPT4ALL = "gpt4all"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LocalAIProvider(Enum):
    """Local AI providers for privacy-first processing."""
    OLLAMA = "ollama"
    LM_STUDIO = "lmstudio"
    MISTRAL_LOCAL = "mistral_local"
    GPT4ALL = "gpt4all"
    LOCALAI = "localai"
    LLAMA_CPP = "llama_cpp"
    JAN = "jan"
    CUSTOM = "custom"


class CloudAIProvider(Enum):
    """Cloud AI providers (not recommended for sensitive data)."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE_GEMINI = "gemini"
    MISTRAL_AI = "mistral_ai"
    COHERE = "cohere"
    CUSTOM = "custom"


class DetectionType(Enum):
    """Types of AI-detected elements."""
    HEADING = "heading"
    IMAGE = "image"
    TABLE = "table"
    LINK = "link"
    ISSUE = "issue"
    LIST = "list"
    PARAGRAPH = "paragraph"


class TagType(Enum):
    """PDF tag types for accessibility."""
    DOCUMENT = "Document"
    PART = "Part"
    ARTICLE = "Art"
    SECTION = "Sect"
    DIV = "Div"
    HEADING_1 = "H1"
    HEADING_2 = "H2"
    HEADING_3 = "H3"
    HEADING_4 = "H4"
    HEADING_5 = "H5"
    HEADING_6 = "H6"
    PARAGRAPH = "P"
    LIST = "L"
    LIST_ITEM = "LI"
    LIST_BODY = "LBody"
    TABLE = "Table"
    TABLE_ROW = "TR"
    TABLE_HEADER = "TH"
    TABLE_DATA = "TD"
    FIGURE = "Figure"
    FORMULA = "Formula"
    FORM = "Form"
    LINK = "Link"
    NOTE = "Note"
    REFERENCE = "Reference"
    BIBLIOGRAPHY = "BibEntry"
    CODE = "Code"
    QUOTE = "Quote"
    SPAN = "Span"
    TOC = "TOC"
    TOCI = "TOCI"


# WCAG Compliance Criteria
WCAG_CRITERIA = {
    "1.1.1": {
        "name": "Non-text Content",
        "level": WCAGLevel.A,
        "description": "All non-text content has a text alternative",
    },
    "1.3.1": {
        "name": "Info and Relationships",
        "level": WCAGLevel.A,
        "description": "Information and relationships conveyed through presentation can be programmatically determined",
    },
    "1.3.2": {
        "name": "Meaningful Sequence",
        "level": WCAGLevel.A,
        "description": "Reading order can be programmatically determined",
    },
    "1.4.3": {
        "name": "Contrast (Minimum)",
        "level": WCAGLevel.AA,
        "description": "Text has a contrast ratio of at least 4.5:1",
    },
    "1.4.6": {
        "name": "Contrast (Enhanced)",
        "level": WCAGLevel.AAA,
        "description": "Text has a contrast ratio of at least 7:1",
    },
    "2.4.1": {
        "name": "Bypass Blocks",
        "level": WCAGLevel.A,
        "description": "A mechanism is available to bypass blocks of content",
    },
    "2.4.2": {
        "name": "Page Titled",
        "level": WCAGLevel.A,
        "description": "Document has a title that describes topic or purpose",
    },
    "2.4.4": {
        "name": "Link Purpose",
        "level": WCAGLevel.A,
        "description": "The purpose of each link can be determined from the link text",
    },
    "2.4.6": {
        "name": "Headings and Labels",
        "level": WCAGLevel.AA,
        "description": "Headings and labels describe topic or purpose",
    },
    "3.1.1": {
        "name": "Language of Page",
        "level": WCAGLevel.A,
        "description": "Default human language can be programmatically determined",
    },
    "3.1.2": {
        "name": "Language of Parts",
        "level": WCAGLevel.AA,
        "description": "Language of passages can be programmatically determined",
    },
    "4.1.2": {
        "name": "Name, Role, Value",
        "level": WCAGLevel.A,
        "description": "For all UI components, name and role can be programmatically determined",
    },
}


# Remediation categories mapping to WCAG criteria
REMEDIATION_CATEGORIES = {
    "document_title": {
        "label": "Document Title",
        "criteria": ["2.4.2"],
        "description": "Document has a meaningful title",
    },
    "document_language": {
        "label": "Document Language",
        "criteria": ["3.1.1"],
        "description": "Primary language is specified",
    },
    "language_of_parts": {
        "label": "Language of Parts",
        "criteria": ["3.1.2"],
        "description": "Foreign-language passages are marked",
    },
    "tagged_pdf": {
        "label": "Tagged PDF",
        "criteria": ["1.3.1"],
        "description": "Document has a tag structure tree",
    },
    "reading_order": {
        "label": "Reading Order",
        "criteria": ["1.3.2"],
        "description": "Content order matches visual flow",
    },
    "headings": {
        "label": "Headings",
        "criteria": ["1.3.1", "2.4.6"],
        "description": "Headings use proper hierarchy (H1-H6)",
    },
    "alt_text": {
        "label": "Alternative Text",
        "criteria": ["1.1.1"],
        "description": "Images have descriptive alt text",
    },
    "tables": {
        "label": "Tables",
        "criteria": ["1.3.1"],
        "description": "Tables use TH/TD with scope attributes",
    },
    "links": {
        "label": "Links",
        "criteria": ["2.4.4"],
        "description": "Links have descriptive, meaningful text",
    },
    "color_contrast": {
        "label": "Color Contrast",
        "criteria": ["1.4.3", "1.4.6"],
        "description": "Text meets minimum contrast ratios",
    },
    "bookmarks": {
        "label": "Bookmarks",
        "criteria": ["2.4.1"],
        "description": "Bookmarks allow navigation bypass",
    },
    "forms": {
        "label": "Forms",
        "criteria": ["4.1.2"],
        "description": "Form fields have labels and roles",
    },
    "artifacts": {
        "label": "Artifacts",
        "criteria": ["1.3.1"],
        "description": "Decorative elements are marked as artifacts",
    },
    "security": {
        "label": "Security Settings",
        "criteria": [],
        "description": "Security settings allow screen reader access",
    },
}


# WCAG Explainer — plain-language explanations for each criterion
WCAG_EXPLAINER = {
    "1.1.1": {
        "plain_language": "Every image, chart, or non-text element needs a text description so people who can't see it still get the information.",
        "who_it_affects": "Blind and low-vision users who rely on screen readers, and users on slow connections who disable images.",
        "real_world_barrier": "A blind student opens a PDF lecture slide. The chart showing quarterly sales has no alt text, so the screen reader says 'image' — the student has no idea what the chart shows.",
    },
    "1.3.1": {
        "plain_language": "The visual structure of the document (headings, tables, lists) must also be encoded in the file's tags so assistive technology can understand it.",
        "who_it_affects": "Screen reader users, braille display users, and people who use custom stylesheets.",
        "real_world_barrier": "A table looks fine visually, but without TH tags a screen reader reads all cells in a flat stream — the user can't tell which value belongs to which column.",
    },
    "1.3.2": {
        "plain_language": "The order in which a screen reader reads the content must match the visual reading flow (left-to-right, top-to-bottom, column by column).",
        "who_it_affects": "Screen reader users and keyboard-only navigators.",
        "real_world_barrier": "A two-column newsletter is read left-across-both-columns instead of column-by-column, so sentences from unrelated articles get interleaved.",
    },
    "1.4.3": {
        "plain_language": "Text must have enough contrast against its background — at least 4.5:1 for normal text — so it's readable for people with low vision.",
        "who_it_affects": "People with low vision, color vision deficiencies, and anyone reading in bright sunlight.",
        "real_world_barrier": "Light gray text on a white background is nearly invisible to a person with moderate low vision, making the document unreadable without a magnifier.",
    },
    "1.4.6": {
        "plain_language": "Enhanced contrast (7:1 for normal text) makes text even easier to read for users with moderately low vision who don't use assistive technology.",
        "who_it_affects": "Users with moderate low vision who don't use screen magnifiers or high-contrast modes.",
        "real_world_barrier": "A user with early macular degeneration can read 7:1 contrast text comfortably but struggles with 4.5:1 text, especially in longer documents.",
    },
    "2.4.1": {
        "plain_language": "Long documents need bookmarks or a table of contents so users can jump directly to sections instead of listening to the entire document.",
        "who_it_affects": "Screen reader users and keyboard-only navigators.",
        "real_world_barrier": "A 50-page policy document has no bookmarks. A screen reader user must listen from page 1 every time they want to find Section 5.",
    },
    "2.4.2": {
        "plain_language": "The document must have a descriptive title — not a filename — so users know what it is before they open it.",
        "who_it_affects": "Screen reader users, people managing many browser tabs, and search engine indexing.",
        "real_world_barrier": "A screen reader announces 'doc_v3_final_FINAL.pdf' instead of 'Spring 2025 Course Syllabus', leaving the user unsure if they have the right file.",
    },
    "2.4.4": {
        "plain_language": "Link text must describe where the link goes. 'Click here' tells the user nothing; 'Download the 2025 budget report (PDF)' is clear.",
        "who_it_affects": "Screen reader users who navigate by pulling up a list of links on the page.",
        "real_world_barrier": "A screen reader's link list shows five entries all labelled 'Click here'. The user has no way to tell them apart without reading surrounding text.",
    },
    "2.4.6": {
        "plain_language": "Headings and form labels must clearly describe the content or purpose of the section they introduce.",
        "who_it_affects": "Screen reader users and anyone scanning the document for specific information.",
        "real_world_barrier": "A heading says 'Section 3' instead of 'Grading Policy', forcing the user to read the entire section to find out what it covers.",
    },
    "3.1.1": {
        "plain_language": "The document must declare its primary language so screen readers use the correct pronunciation rules.",
        "who_it_affects": "Screen reader users in any language.",
        "real_world_barrier": "An English document has no language tag. A French screen reader tries to pronounce every word with French phonetics, making the content unintelligible.",
    },
    "3.1.2": {
        "plain_language": "When a passage switches to a different language, it must be tagged so the screen reader switches pronunciation.",
        "who_it_affects": "Screen reader users reading multilingual documents.",
        "real_world_barrier": "A legal document includes Latin phrases. Without language-of-parts tags, the English screen reader mispronounces every Latin term.",
    },
    "4.1.2": {
        "plain_language": "Every form field and interactive control must expose its name and role to assistive technology so users know what it does.",
        "who_it_affects": "Screen reader users and voice-control users who interact with form fields.",
        "real_world_barrier": "A PDF form has an unlabelled text field. The screen reader says 'edit text' but doesn't say 'First Name', so the user doesn't know what to type.",
    },
}


# Overlay Colors for AI Detections (40% opacity = alpha 102)
OVERLAY_COLORS = {
    "heading": (162, 59, 132, 102),    # Purple (#a23b84)
    "image": (251, 191, 36, 102),      # Yellow
    "table": (16, 185, 129, 102),      # Green
    "link": (249, 115, 22, 102),       # Orange
    "issue": (239, 68, 68, 102),       # Red (missing alt, etc.)
    "list": (139, 92, 246, 102),       # Violet
    "paragraph": (100, 116, 139, 102), # Slate
}


# Default Configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    "ai": {
        "mode": "local",  # "local" or "cloud"
        "backend": AIBackend.OLLAMA.value,
        "local_provider": LocalAIProvider.OLLAMA.value,
        "cloud_provider": CloudAIProvider.OPENAI.value,
        "ollama_url": "http://localhost:11434",
        "lmstudio_url": "http://localhost:1234",
        "mistral_local_url": "http://localhost:8080",
        "localai_url": "http://localhost:8080",
        "llama_cpp_url": "http://localhost:8080",
        "jan_url": "http://localhost:1337",
        "gpt4all_model": "orca-mini-3b-gguf2-q4_0.gguf",
        "default_model": "llava",
        "temperature": 0.7,
        "max_tokens": 2000,
        "context_window": 4096,
        "timeout": 60,
        "privacy_warning_accepted": False,
    },
    "processing": {
        "batch_limit": 5,
        "auto_ocr": True,
        "ocr_language": "eng",
        "default_language": "en",
        "preserve_original": True,
    },
    "accessibility": {
        "wcag_level": WCAGLevel.AA.value,
        "check_contrast": True,
        "check_headings": True,
        "check_alt_text": True,
        "check_tables": True,
        "check_links": True,
        "check_reading_order": True,
    },
    "ui": {
        "theme": "system",
        "high_contrast": False,
        "reduced_motion": False,
        "large_text_mode": False,
        "enhanced_focus": False,
        "dyslexia_font": False,
        "color_blind_mode": ColorBlindMode.NONE.value,
        "custom_cursor": CustomCursorStyle.DEFAULT.value,
        "font_size": 12,
        "show_line_numbers": True,
        "auto_preview": True,
    },
    "security": {
        "encrypt_files": True,
        "auto_logout_minutes": 30,
        "require_password": False,
    },
    "html_export": {
        "include_styles": True,
        "theme": "brand",
        "responsive": True,
        "include_toc": True,
    },
}


# Supported file formats
SUPPORTED_INPUT_FORMATS = [".pdf"]
SUPPORTED_OUTPUT_FORMATS = [".pdf", ".html", ".docx"]


# OCR Languages (Tesseract codes)
OCR_LANGUAGES = {
    "eng": "English",
    "spa": "Spanish",
    "fra": "French",
    "deu": "German",
    "ita": "Italian",
    "por": "Portuguese",
    "nld": "Dutch",
    "pol": "Polish",
    "rus": "Russian",
    "jpn": "Japanese",
    "chi_sim": "Chinese (Simplified)",
    "chi_tra": "Chinese (Traditional)",
    "kor": "Korean",
    "ara": "Arabic",
    "hin": "Hindi",
}


# Contrast ratio requirements
CONTRAST_NORMAL_TEXT_AA = 4.5
CONTRAST_LARGE_TEXT_AA = 3.0
CONTRAST_NORMAL_TEXT_AAA = 7.0
CONTRAST_LARGE_TEXT_AAA = 4.5


# File size limits
MAX_FILE_SIZE_MB = 100
MAX_BATCH_SIZE = 10
MIN_BATCH_SIZE = 1


# UI Constants
FOCUS_BORDER_WIDTH = 2
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 24
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 800


def ensure_directories():
    """Create necessary application directories."""
    for directory in [APP_DATA_DIR, CACHE_DIR, TEMP_DIR, LOG_FILE.parent]:
        directory.mkdir(parents=True, exist_ok=True)
