"""Tests for WCAG validator module."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from accessible_pdf_toolkit.core.wcag_validator import (
    WCAGValidator,
    ValidationResult,
    ValidationIssue,
    IssueSeverity,
)
from accessible_pdf_toolkit.core.pdf_handler import PDFDocument, PDFPage, PDFElement
from accessible_pdf_toolkit.utils.constants import WCAGLevel, TagType


@pytest.fixture
def mock_document():
    """Create a mock PDF document for testing."""
    doc = MagicMock(spec=PDFDocument)
    doc.path = Path("test.pdf")
    doc.title = "Test Document"
    doc.author = "Test Author"
    doc.language = "en"
    doc.page_count = 2
    doc.is_tagged = True
    doc.has_structure = True
    doc.metadata = {}
    doc.alt_text_map = {}

    # Create mock pages
    page1 = MagicMock(spec=PDFPage)
    page1.page_number = 1
    page1.text = "This is page 1 content"
    page1.elements = [
        PDFElement(
            element_type="text",
            text="Heading 1",
            page_number=1,
            bbox=(100, 100, 400, 120),
            tag=TagType.HEADING_1,
            attributes={"size": 24, "color": 0, "flags": 0},
        ),
        PDFElement(
            element_type="text",
            text="Some paragraph text",
            page_number=1,
            bbox=(100, 140, 400, 160),
            tag=TagType.PARAGRAPH,
            attributes={"size": 12, "color": 0, "flags": 0},
        ),
    ]
    page1.images = []
    page1.links = []

    page2 = MagicMock(spec=PDFPage)
    page2.page_number = 2
    page2.text = "This is page 2 content"
    page2.elements = []
    page2.images = []
    page2.links = []

    doc.pages = [page1, page2]
    return doc


@pytest.fixture
def validator():
    """Create a WCAG validator instance."""
    return WCAGValidator(target_level=WCAGLevel.AA)


class TestWCAGValidator:
    """Tests for WCAGValidator class."""

    def test_validate_compliant_document(self, validator, mock_document):
        """Test validation of a compliant document."""
        result = validator.validate(mock_document)

        assert isinstance(result, ValidationResult)
        assert result.level == WCAGLevel.AA
        assert result.score >= 0
        assert isinstance(result.issues, list)

    def test_validate_missing_title(self, validator, mock_document):
        """Test detection of missing document title."""
        mock_document.title = None

        result = validator.validate(mock_document)

        title_issues = [i for i in result.issues if i.criterion == "2.4.2"]
        assert len(title_issues) > 0
        assert title_issues[0].severity == IssueSeverity.ERROR

    def test_validate_missing_language(self, validator, mock_document):
        """Test detection of missing document language."""
        mock_document.language = None

        result = validator.validate(mock_document)

        lang_issues = [i for i in result.issues if i.criterion == "3.1.1"]
        assert len(lang_issues) > 0
        assert lang_issues[0].severity == IssueSeverity.ERROR

    def test_validate_untagged_document(self, validator, mock_document):
        """Test detection of untagged PDF."""
        mock_document.is_tagged = False
        mock_document.has_structure = False

        result = validator.validate(mock_document)

        structure_issues = [i for i in result.issues if i.criterion == "1.3.1"]
        assert len(structure_issues) > 0

    def test_validate_images_without_alt(self, validator, mock_document):
        """Test detection of images without alt text."""
        mock_document.pages[0].images = [
            {"index": 0, "xref": 1, "width": 100, "height": 100}
        ]

        result = validator.validate(mock_document)

        image_issues = [i for i in result.issues if i.criterion == "1.1.1"]
        assert len(image_issues) > 0

    def test_score_calculation(self, validator, mock_document):
        """Test compliance score calculation."""
        result = validator.validate(mock_document)

        assert 0 <= result.score <= 100

    def test_get_fix_suggestions(self, validator, mock_document):
        """Test fix suggestion generation."""
        mock_document.title = None

        result = validator.validate(mock_document)
        fixes = validator.get_fix_suggestions(result)

        assert isinstance(fixes, list)
        # Should suggest fixing the missing title
        title_fixes = [f for f in fixes if f["criterion"] == "2.4.2"]
        assert len(title_fixes) > 0

    def test_criterion_info(self, validator):
        """Test getting criterion information."""
        info = validator.get_criterion_info("1.1.1")

        assert info is not None
        assert "name" in info
        assert "level" in info
        assert info["name"] == "Non-text Content"

    def test_level_a_validator(self, mock_document):
        """Test validator with Level A target."""
        validator = WCAGValidator(target_level=WCAGLevel.A)
        result = validator.validate(mock_document)

        assert result.level == WCAGLevel.A

    def test_level_aaa_validator(self, mock_document):
        """Test validator with Level AAA target."""
        validator = WCAGValidator(target_level=WCAGLevel.AAA)
        result = validator.validate(mock_document)

        assert result.level == WCAGLevel.AAA

    def test_images_with_alt_text_pass(self, validator, mock_document):
        """Test that images WITH alt text in the structure tree pass validation."""
        mock_document.pages[0].images = [
            {"index": 0, "xref": 1, "width": 100, "height": 100}
        ]
        # Provide alt text for page 1's image via the alt_text_map
        mock_document.alt_text_map = {
            1: [{"alt_text": "A description of the image", "tag": "/Figure"}]
        }

        result = validator.validate(mock_document)

        image_issues = [i for i in result.issues if i.criterion == "1.1.1"]
        assert len(image_issues) == 0

    def test_contrast_black_on_white_passes(self, validator, mock_document):
        """Test that black text on white background passes contrast check."""
        # color=0 means black (#000000) -- should pass
        mock_document.pages[0].elements = [
            PDFElement(
                element_type="text",
                text="Black text on white",
                page_number=1,
                bbox=(100, 100, 400, 120),
                attributes={"size": 12, "color": 0, "flags": 0},
            ),
        ]

        result = validator.validate(mock_document)

        contrast_issues = [i for i in result.issues if i.criterion == "1.4.3"]
        assert len(contrast_issues) == 0

    def test_contrast_light_gray_on_white_fails(self, validator, mock_document):
        """Test that light gray text on white background fails contrast check."""
        # 0xCCCCCC = light gray -- contrast ~1.6:1, well below 4.5:1
        mock_document.pages[0].elements = [
            PDFElement(
                element_type="text",
                text="Light gray text",
                page_number=1,
                bbox=(100, 100, 400, 120),
                attributes={"size": 12, "color": 0xCCCCCC, "flags": 0},
            ),
        ]

        result = validator.validate(mock_document)

        contrast_issues = [i for i in result.issues if i.criterion == "1.4.3"]
        assert len(contrast_issues) > 0
        assert contrast_issues[0].severity == IssueSeverity.ERROR


class TestContrastHelpers:
    """Tests for the contrast calculation helper methods."""

    def test_int_to_rgb(self):
        """Test color integer to RGB conversion."""
        assert WCAGValidator._int_to_rgb(0x000000) == (0, 0, 0)
        assert WCAGValidator._int_to_rgb(0xFFFFFF) == (255, 255, 255)
        assert WCAGValidator._int_to_rgb(0xFF0000) == (255, 0, 0)
        assert WCAGValidator._int_to_rgb(0x00FF00) == (0, 255, 0)
        assert WCAGValidator._int_to_rgb(0x0000FF) == (0, 0, 255)

    def test_relative_luminance(self):
        """Test WCAG relative luminance calculation."""
        # Black should have luminance 0
        assert WCAGValidator._relative_luminance(0, 0, 0) == 0.0
        # White should have luminance 1
        assert abs(WCAGValidator._relative_luminance(255, 255, 255) - 1.0) < 0.01

    def test_contrast_ratio_black_white(self):
        """Test contrast ratio between black and white is 21:1."""
        lum_black = WCAGValidator._relative_luminance(0, 0, 0)
        lum_white = WCAGValidator._relative_luminance(255, 255, 255)
        ratio = WCAGValidator._contrast_ratio(lum_black, lum_white)
        assert abs(ratio - 21.0) < 0.1

    def test_is_large_text(self):
        """Test large text detection."""
        # 18pt normal = large
        assert WCAGValidator._is_large_text(18.0, 0) is True
        # 14pt bold = large
        assert WCAGValidator._is_large_text(14.0, 1 << 4) is True
        # 12pt normal = not large
        assert WCAGValidator._is_large_text(12.0, 0) is False
        # 13pt bold = not large
        assert WCAGValidator._is_large_text(13.0, 1 << 4) is False


class TestTableDetection:
    """Tests for heuristic table detection."""

    def test_detects_untagged_table(self, validator):
        """Test that grid-like text patterns are flagged as possible untagged tables."""
        doc = MagicMock(spec=PDFDocument)
        doc.path = Path("test.pdf")
        doc.title = "Test"
        doc.language = "en"
        doc.page_count = 1
        doc.is_tagged = True
        doc.has_structure = True
        doc.alt_text_map = {}

        page = MagicMock(spec=PDFPage)
        page.page_number = 1
        page.text = "table data"
        page.images = []
        page.links = []

        # Create a 4-row x 3-column grid of text elements (no Table tags)
        elements = []
        for row in range(4):
            for col in range(3):
                elements.append(PDFElement(
                    element_type="text",
                    text=f"Cell {row},{col}",
                    page_number=1,
                    bbox=(100 + col * 150, 100 + row * 20, 200 + col * 150, 120 + row * 20),
                    attributes={"size": 10, "color": 0, "flags": 0},
                ))
        page.elements = elements
        doc.pages = [page]

        result = validator.validate(doc)
        table_issues = [
            i for i in result.issues
            if i.criterion == "1.3.1" and "table" in i.message.lower()
        ]
        assert len(table_issues) >= 1

    def test_no_false_positive_single_column(self, validator):
        """Test that a simple single-column layout is NOT flagged as a table."""
        doc = MagicMock(spec=PDFDocument)
        doc.path = Path("test.pdf")
        doc.title = "Test"
        doc.language = "en"
        doc.page_count = 1
        doc.is_tagged = True
        doc.has_structure = True
        doc.alt_text_map = {}

        page = MagicMock(spec=PDFPage)
        page.page_number = 1
        page.text = "normal text"
        page.images = []
        page.links = []

        # Single column of text lines
        elements = []
        for row in range(6):
            elements.append(PDFElement(
                element_type="text",
                text=f"Paragraph line {row}",
                page_number=1,
                bbox=(100, 100 + row * 20, 500, 120 + row * 20),
                attributes={"size": 12, "color": 0, "flags": 0},
            ))
        page.elements = elements
        doc.pages = [page]

        result = validator.validate(doc)
        table_issues = [
            i for i in result.issues
            if i.criterion == "1.3.1" and "untagged table" in i.message.lower()
        ]
        assert len(table_issues) == 0


class TestLinkDetection:
    """Tests for untagged link detection."""

    def test_detects_untagged_hyperlinks(self, validator):
        """Test that URI links without Link tags are flagged."""
        doc = MagicMock(spec=PDFDocument)
        doc.path = Path("test.pdf")
        doc.title = "Test"
        doc.language = "en"
        doc.page_count = 1
        doc.is_tagged = True
        doc.has_structure = True
        doc.alt_text_map = {}

        page = MagicMock(spec=PDFPage)
        page.page_number = 1
        page.text = "Visit our website"
        page.images = []
        page.elements = [
            PDFElement(
                element_type="text",
                text="Visit our website",
                page_number=1,
                bbox=(100, 100, 300, 120),
                attributes={"size": 12, "color": 0, "flags": 0},
            ),
        ]
        page.links = [
            {"page": 1, "kind": 2, "uri": "https://example.com", "text": "Visit our website", "bbox": (100, 100, 300, 120)},
        ]
        doc.pages = [page]

        result = validator.validate(doc)
        link_struct_issues = [
            i for i in result.issues
            if i.criterion == "1.3.1" and "not tagged" in i.message.lower() and "link" in i.message.lower()
        ]
        assert len(link_struct_issues) >= 1

    def test_non_descriptive_link_text_detected(self, validator):
        """Test that non-descriptive link text in annotations is flagged."""
        doc = MagicMock(spec=PDFDocument)
        doc.path = Path("test.pdf")
        doc.title = "Test"
        doc.language = "en"
        doc.page_count = 1
        doc.is_tagged = True
        doc.has_structure = True
        doc.alt_text_map = {}

        page = MagicMock(spec=PDFPage)
        page.page_number = 1
        page.text = "click here"
        page.images = []
        page.elements = []
        page.links = [
            {"page": 1, "kind": 2, "uri": "https://example.com", "text": "click here", "bbox": (100, 100, 200, 120)},
        ]
        doc.pages = [page]

        result = validator.validate(doc)
        text_issues = [
            i for i in result.issues
            if i.criterion == "2.4.4" and "non-descriptive" in i.message.lower()
        ]
        assert len(text_issues) >= 1


class TestReadingOrderDetection:
    """Tests for reading order checks."""

    def test_no_structure_tree_warns(self, validator):
        """Test that missing structure tree generates a reading order warning."""
        doc = MagicMock(spec=PDFDocument)
        doc.path = Path("test.pdf")
        doc.title = "Test"
        doc.language = "en"
        doc.page_count = 3
        doc.is_tagged = False
        doc.has_structure = False
        doc.alt_text_map = {}
        doc.pages = []

        result = validator.validate(doc)
        reading_issues = [
            i for i in result.issues
            if i.criterion == "1.3.2" and "structure tree" in i.message.lower()
        ]
        assert len(reading_issues) >= 1


class TestValidationIssue:
    """Tests for ValidationIssue dataclass."""

    def test_create_issue(self):
        """Test creating a validation issue."""
        issue = ValidationIssue(
            criterion="1.1.1",
            severity=IssueSeverity.ERROR,
            message="Image lacks alt text",
            page=1,
            element="Image 1",
            suggestion="Add descriptive alt text",
            auto_fixable=True,
        )

        assert issue.criterion == "1.1.1"
        assert issue.severity == IssueSeverity.ERROR
        assert issue.auto_fixable is True

    def test_issue_severity_levels(self):
        """Test issue severity levels."""
        assert IssueSeverity.ERROR.value == "error"
        assert IssueSeverity.WARNING.value == "warning"
        assert IssueSeverity.INFO.value == "info"


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_compliant_result(self):
        """Test creating a compliant result."""
        result = ValidationResult(
            is_compliant=True,
            level=WCAGLevel.AA,
            score=95.0,
            issues=[],
            passed_criteria=["1.1.1", "2.4.2"],
            failed_criteria=[],
            summary={"errors": 0, "warnings": 0, "info": 0, "total": 0},
        )

        assert result.is_compliant is True
        assert result.score == 95.0
        assert len(result.issues) == 0

    def test_non_compliant_result(self):
        """Test creating a non-compliant result."""
        result = ValidationResult(
            is_compliant=False,
            level=WCAGLevel.AA,
            score=45.0,
            issues=[
                ValidationIssue(
                    criterion="1.1.1",
                    severity=IssueSeverity.ERROR,
                    message="Test error",
                )
            ],
            passed_criteria=["2.4.2"],
            failed_criteria=["1.1.1"],
            summary={"errors": 1, "warnings": 0, "info": 0, "total": 1},
        )

        assert result.is_compliant is False
        assert len(result.failed_criteria) == 1
