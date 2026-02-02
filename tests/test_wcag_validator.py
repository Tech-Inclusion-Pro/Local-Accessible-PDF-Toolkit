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
            attributes={"size": 24},
        ),
        PDFElement(
            element_type="text",
            text="Some paragraph text",
            page_number=1,
            bbox=(100, 140, 400, 160),
            tag=TagType.PARAGRAPH,
            attributes={"size": 12},
        ),
    ]
    page1.images = []

    page2 = MagicMock(spec=PDFPage)
    page2.page_number = 2
    page2.text = "This is page 2 content"
    page2.elements = []
    page2.images = []

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
