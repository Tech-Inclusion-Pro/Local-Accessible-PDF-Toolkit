"""
WCAG validation module for checking PDF accessibility compliance.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..utils.constants import WCAGLevel, WCAG_CRITERIA, CONTRAST_NORMAL_TEXT_AA
from ..utils.logger import get_logger
from .pdf_handler import PDFDocument, PDFElement

logger = get_logger(__name__)


class IssueSeverity(Enum):
    """Severity levels for accessibility issues."""

    ERROR = "error"          # Must fix for compliance
    WARNING = "warning"      # Should fix for better accessibility
    INFO = "info"           # Suggestion for improvement


@dataclass
class ValidationIssue:
    """Represents a single accessibility issue."""

    criterion: str           # WCAG criterion ID (e.g., "1.1.1")
    severity: IssueSeverity
    message: str
    page: Optional[int] = None
    element: Optional[str] = None
    suggestion: Optional[str] = None
    auto_fixable: bool = False


@dataclass
class ValidationResult:
    """Result of WCAG validation."""

    is_compliant: bool
    level: WCAGLevel
    score: float            # 0-100
    issues: List[ValidationIssue] = field(default_factory=list)
    passed_criteria: List[str] = field(default_factory=list)
    failed_criteria: List[str] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)


class WCAGValidator:
    """Validates PDF documents for WCAG compliance."""

    def __init__(self, target_level: WCAGLevel = WCAGLevel.AA):
        """
        Initialize the validator.

        Args:
            target_level: Target WCAG compliance level
        """
        self.target_level = target_level

    def validate(self, document: PDFDocument) -> ValidationResult:
        """
        Validate a PDF document for WCAG compliance.

        Args:
            document: PDFDocument to validate

        Returns:
            ValidationResult with all findings
        """
        issues = []

        # Run all checks
        issues.extend(self._check_document_title(document))
        issues.extend(self._check_document_language(document))
        issues.extend(self._check_tagged_pdf(document))
        issues.extend(self._check_reading_order(document))
        issues.extend(self._check_headings(document))
        issues.extend(self._check_images(document))
        issues.extend(self._check_tables(document))
        issues.extend(self._check_links(document))
        issues.extend(self._check_color_contrast(document))

        # Calculate results
        return self._calculate_result(issues)

    def _check_document_title(self, doc: PDFDocument) -> List[ValidationIssue]:
        """Check for document title (WCAG 2.4.2)."""
        issues = []

        if not doc.title or doc.title.strip() == "":
            issues.append(ValidationIssue(
                criterion="2.4.2",
                severity=IssueSeverity.ERROR,
                message="Document does not have a title",
                suggestion="Add a descriptive title that describes the document's topic or purpose",
                auto_fixable=True,
            ))
        elif doc.title == doc.path.stem:
            issues.append(ValidationIssue(
                criterion="2.4.2",
                severity=IssueSeverity.WARNING,
                message="Document title appears to be the filename",
                suggestion="Use a descriptive title instead of the filename",
                auto_fixable=True,
            ))

        return issues

    def _check_document_language(self, doc: PDFDocument) -> List[ValidationIssue]:
        """Check for document language (WCAG 3.1.1)."""
        issues = []

        if not doc.language:
            issues.append(ValidationIssue(
                criterion="3.1.1",
                severity=IssueSeverity.ERROR,
                message="Document language is not specified",
                suggestion="Set the document language (e.g., 'en' for English)",
                auto_fixable=True,
            ))
        elif len(doc.language) < 2:
            issues.append(ValidationIssue(
                criterion="3.1.1",
                severity=IssueSeverity.WARNING,
                message=f"Document language '{doc.language}' may not be a valid language code",
                suggestion="Use a valid BCP 47 language code (e.g., 'en', 'en-US', 'es')",
            ))

        return issues

    def _check_tagged_pdf(self, doc: PDFDocument) -> List[ValidationIssue]:
        """Check if PDF is tagged (WCAG 1.3.1, 1.3.2)."""
        issues = []

        if not doc.is_tagged:
            issues.append(ValidationIssue(
                criterion="1.3.1",
                severity=IssueSeverity.ERROR,
                message="PDF is not tagged",
                suggestion="Add PDF tags to define document structure",
                auto_fixable=True,
            ))

        if not doc.has_structure:
            issues.append(ValidationIssue(
                criterion="1.3.2",
                severity=IssueSeverity.ERROR,
                message="PDF does not have a structure tree",
                suggestion="Create a structure tree to define reading order",
                auto_fixable=True,
            ))

        return issues

    def _check_reading_order(self, doc: PDFDocument) -> List[ValidationIssue]:
        """Check reading order (WCAG 1.3.2)."""
        issues = []

        for page in doc.pages:
            if not page.elements:
                continue

            # Check for potential reading order issues
            # Look for elements that might be out of visual order
            sorted_by_position = sorted(
                page.elements,
                key=lambda e: (e.bbox[1], e.bbox[0])  # top-to-bottom, left-to-right
            )

            # Compare with document order
            # This is a simplified check - real implementation would be more sophisticated
            position_matches = 0
            for i, elem in enumerate(page.elements):
                if i < len(sorted_by_position) and elem == sorted_by_position[i]:
                    position_matches += 1

            if len(page.elements) > 0:
                match_ratio = position_matches / len(page.elements)
                if match_ratio < 0.8:
                    issues.append(ValidationIssue(
                        criterion="1.3.2",
                        severity=IssueSeverity.WARNING,
                        message=f"Reading order on page {page.page_number} may not match visual order",
                        page=page.page_number,
                        suggestion="Review and adjust the reading order for logical flow",
                    ))

        return issues

    def _check_headings(self, doc: PDFDocument) -> List[ValidationIssue]:
        """Check heading structure (WCAG 1.3.1, 2.4.6)."""
        issues = []

        # Detect headings based on font size
        all_elements = []
        for page in doc.pages:
            all_elements.extend(page.elements)

        if not all_elements:
            return issues

        # Get font sizes
        sizes = [e.attributes.get("size", 0) for e in all_elements]
        avg_size = sum(sizes) / len(sizes) if sizes else 0

        # Find potential headings
        potential_headings = [
            e for e in all_elements
            if e.attributes.get("size", 0) > avg_size * 1.2
        ]

        if not potential_headings and doc.page_count > 1:
            issues.append(ValidationIssue(
                criterion="2.4.6",
                severity=IssueSeverity.WARNING,
                message="No headings detected in document",
                suggestion="Add headings to provide document structure",
            ))

        # Check for tagged headings
        tagged_headings = [
            e for e in all_elements
            if e.tag and e.tag.value.startswith("H")
        ]

        if potential_headings and not tagged_headings:
            issues.append(ValidationIssue(
                criterion="1.3.1",
                severity=IssueSeverity.WARNING,
                message="Headings are not properly tagged",
                suggestion="Tag headings using H1-H6 structure elements",
                auto_fixable=True,
            ))

        # Check heading hierarchy
        if tagged_headings:
            current_level = 0
            for elem in tagged_headings:
                if elem.tag:
                    level = int(elem.tag.value[1]) if elem.tag.value[1].isdigit() else 0
                    if level > current_level + 1:
                        issues.append(ValidationIssue(
                            criterion="1.3.1",
                            severity=IssueSeverity.ERROR,
                            message=f"Heading level skipped: H{current_level} to H{level}",
                            element=elem.text[:50],
                            suggestion=f"Use H{current_level + 1} instead of H{level}",
                            auto_fixable=True,
                        ))
                    current_level = level

        return issues

    def _check_images(self, doc: PDFDocument) -> List[ValidationIssue]:
        """Check images for alt text (WCAG 1.1.1)."""
        issues = []

        for page in doc.pages:
            for img in page.images:
                # Check if image has alt text
                # In real implementation, this would check the tag structure
                image_has_alt = False  # Simplified - check actual tags

                if not image_has_alt:
                    issues.append(ValidationIssue(
                        criterion="1.1.1",
                        severity=IssueSeverity.ERROR,
                        message=f"Image on page {page.page_number} lacks alt text",
                        page=page.page_number,
                        element=f"Image {img['index'] + 1}",
                        suggestion="Add descriptive alt text for the image",
                        auto_fixable=True,
                    ))

        return issues

    def _check_tables(self, doc: PDFDocument) -> List[ValidationIssue]:
        """Check tables for proper structure (WCAG 1.3.1)."""
        issues = []

        # This would require more sophisticated table detection
        # For now, we'll check if any tagged tables exist

        for page in doc.pages:
            for elem in page.elements:
                if elem.tag and elem.tag.value == "Table":
                    # Check for header cells
                    # Simplified check
                    issues.append(ValidationIssue(
                        criterion="1.3.1",
                        severity=IssueSeverity.INFO,
                        message=f"Table on page {page.page_number} - verify header cells are marked",
                        page=page.page_number,
                        suggestion="Ensure table headers use TH tags with scope attributes",
                    ))

        return issues

    def _check_links(self, doc: PDFDocument) -> List[ValidationIssue]:
        """Check links for meaningful text (WCAG 2.4.4)."""
        issues = []

        # Non-descriptive link texts
        bad_link_texts = [
            "click here", "here", "read more", "more", "link",
            "learn more", "this link", "click", "go"
        ]

        for page in doc.pages:
            for elem in page.elements:
                if elem.tag and elem.tag.value == "Link":
                    text = elem.text.lower().strip()
                    if text in bad_link_texts:
                        issues.append(ValidationIssue(
                            criterion="2.4.4",
                            severity=IssueSeverity.ERROR,
                            message=f"Non-descriptive link text: '{elem.text}'",
                            page=page.page_number,
                            element=elem.text,
                            suggestion="Use descriptive text that indicates the link's purpose",
                            auto_fixable=True,
                        ))

        return issues

    def _check_color_contrast(self, doc: PDFDocument) -> List[ValidationIssue]:
        """Check color contrast (WCAG 1.4.3)."""
        issues = []

        # This would require actual color analysis of the PDF
        # For now, we'll add an informational note

        issues.append(ValidationIssue(
            criterion="1.4.3",
            severity=IssueSeverity.INFO,
            message="Color contrast should be verified manually",
            suggestion=f"Ensure text has at least {CONTRAST_NORMAL_TEXT_AA}:1 contrast ratio",
        ))

        return issues

    def _calculate_result(self, issues: List[ValidationIssue]) -> ValidationResult:
        """Calculate the validation result from issues."""
        # Count issues by severity
        errors = sum(1 for i in issues if i.severity == IssueSeverity.ERROR)
        warnings = sum(1 for i in issues if i.severity == IssueSeverity.WARNING)
        infos = sum(1 for i in issues if i.severity == IssueSeverity.INFO)

        # Determine passed/failed criteria
        failed_criteria = set(i.criterion for i in issues if i.severity == IssueSeverity.ERROR)
        all_criteria = set(WCAG_CRITERIA.keys())

        # Filter by target level
        target_criteria = {
            crit for crit, info in WCAG_CRITERIA.items()
            if info["level"].value <= self.target_level.value
        }

        passed_criteria = target_criteria - failed_criteria

        # Calculate score
        if target_criteria:
            score = len(passed_criteria) / len(target_criteria) * 100
        else:
            score = 100.0 if errors == 0 else 0.0

        # Determine compliance
        is_compliant = errors == 0

        return ValidationResult(
            is_compliant=is_compliant,
            level=self.target_level,
            score=round(score, 1),
            issues=issues,
            passed_criteria=list(passed_criteria),
            failed_criteria=list(failed_criteria),
            summary={
                "errors": errors,
                "warnings": warnings,
                "info": infos,
                "total": len(issues),
            },
        )

    def get_criterion_info(self, criterion_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a WCAG criterion."""
        return WCAG_CRITERIA.get(criterion_id)

    def get_fix_suggestions(self, result: ValidationResult) -> List[Dict[str, Any]]:
        """
        Get prioritized fix suggestions.

        Args:
            result: Validation result

        Returns:
            List of fixes prioritized by impact
        """
        fixes = []

        for issue in result.issues:
            if issue.auto_fixable and issue.severity == IssueSeverity.ERROR:
                fixes.append({
                    "criterion": issue.criterion,
                    "message": issue.message,
                    "suggestion": issue.suggestion,
                    "priority": "high",
                    "page": issue.page,
                })

        for issue in result.issues:
            if issue.auto_fixable and issue.severity == IssueSeverity.WARNING:
                fixes.append({
                    "criterion": issue.criterion,
                    "message": issue.message,
                    "suggestion": issue.suggestion,
                    "priority": "medium",
                    "page": issue.page,
                })

        return fixes
