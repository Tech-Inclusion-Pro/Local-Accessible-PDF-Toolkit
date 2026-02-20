"""
WCAG validation module for checking PDF accessibility compliance.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..utils.constants import (
    WCAGLevel,
    WCAG_CRITERIA,
    CONTRAST_NORMAL_TEXT_AA,
    CONTRAST_LARGE_TEXT_AA,
    CONTRAST_NORMAL_TEXT_AAA,
    CONTRAST_LARGE_TEXT_AAA,
)
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

        # If the document has no structure tree, reading order can't be guaranteed
        if not doc.has_structure and doc.page_count > 1:
            issues.append(ValidationIssue(
                criterion="1.3.2",
                severity=IssueSeverity.WARNING,
                message="No structure tree -- reading order cannot be verified",
                suggestion="Add a structure tree to define explicit reading order",
            ))

        for page in doc.pages:
            if not page.elements:
                continue

            # Check for multi-column layout misreads
            # Detect if text elements span multiple visual columns
            text_elems = [e for e in page.elements if e.element_type == "text"]
            if len(text_elems) < 4:
                continue

            # Gather x-positions of left edges
            left_edges = [e.bbox[0] for e in text_elems]
            if not left_edges:
                continue

            # Detect columns: cluster left-edge x positions
            sorted_edges = sorted(set(round(x / 20) * 20 for x in left_edges))
            distinct_columns = len(sorted_edges)

            if distinct_columns >= 2:
                # Multi-column layout detected -- check if document order follows
                # visual order (top-to-bottom, column-by-column)
                sorted_by_position = sorted(
                    text_elems,
                    key=lambda e: (round(e.bbox[0] / 50), e.bbox[1])  # group by column, then top-to-bottom
                )

                # Compare against the content stream order
                position_matches = 0
                for i, elem in enumerate(text_elems):
                    if i < len(sorted_by_position) and elem == sorted_by_position[i]:
                        position_matches += 1

                if len(text_elems) > 0:
                    match_ratio = position_matches / len(text_elems)
                    if match_ratio < 0.7:
                        issues.append(ValidationIssue(
                            criterion="1.3.2",
                            severity=IssueSeverity.WARNING,
                            message=f"Multi-column layout on page {page.page_number}: "
                                    f"reading order may not match visual flow "
                                    f"({distinct_columns} columns detected)",
                            page=page.page_number,
                            suggestion="Review reading order to ensure multi-column content "
                                       "is read in the correct sequence",
                        ))
            else:
                # Single column -- check simple top-to-bottom order
                sorted_by_position = sorted(
                    text_elems,
                    key=lambda e: (e.bbox[1], e.bbox[0])
                )

                position_matches = sum(
                    1 for i, elem in enumerate(text_elems)
                    if i < len(sorted_by_position) and elem == sorted_by_position[i]
                )

                if len(text_elems) > 0:
                    match_ratio = position_matches / len(text_elems)
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

        # Build a set of pages that have alt text entries from the structure tree
        alt_text_map = getattr(doc, "alt_text_map", {})

        for page in doc.pages:
            page_alt_entries = alt_text_map.get(page.page_number, [])
            # Count how many figures on this page have non-empty alt text
            figures_with_alt = [
                entry for entry in page_alt_entries
                if entry.get("alt_text") and entry["alt_text"].strip()
            ]

            for img_idx, img in enumerate(page.images):
                # Image has alt text if there's a matching Figure entry with alt text
                image_has_alt = img_idx < len(figures_with_alt)

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

        for page in doc.pages:
            # Check already-tagged tables
            for elem in page.elements:
                if elem.tag and elem.tag.value == "Table":
                    issues.append(ValidationIssue(
                        criterion="1.3.1",
                        severity=IssueSeverity.INFO,
                        message=f"Table on page {page.page_number} - verify header cells are marked",
                        page=page.page_number,
                        suggestion="Ensure table headers use TH tags with scope attributes",
                    ))

            # Heuristic: detect untagged tabular data
            # Group text elements by approximate y-position (rows)
            if not page.elements:
                continue

            y_tolerance = 3.0  # points
            rows: Dict[float, List] = {}
            for elem in page.elements:
                if elem.element_type != "text":
                    continue
                y = round(elem.bbox[1] / y_tolerance) * y_tolerance
                rows.setdefault(y, []).append(elem)

            # A table-like pattern: multiple rows each with 3+ columns at similar x positions
            multi_col_rows = [elems for elems in rows.values() if len(elems) >= 3]
            if len(multi_col_rows) >= 3:
                # Check if columns are consistently aligned (same x positions across rows)
                col_positions = set()
                for elems in multi_col_rows:
                    for e in elems:
                        col_positions.add(round(e.bbox[0] / 10) * 10)  # round to 10pt grid

                if len(col_positions) >= 3:
                    # Likely a table -- check if it's tagged
                    has_table_tag = any(
                        e.tag and e.tag.value == "Table"
                        for e in page.elements
                    )
                    if not has_table_tag:
                        issues.append(ValidationIssue(
                            criterion="1.3.1",
                            severity=IssueSeverity.WARNING,
                            message=f"Possible untagged table on page {page.page_number} "
                                    f"({len(multi_col_rows)} rows, ~{len(col_positions)} columns detected)",
                            page=page.page_number,
                            suggestion="Tag the table with Table, TR, TH, and TD elements",
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
            # Check already-tagged links
            tagged_link_count = 0
            for elem in page.elements:
                if elem.tag and elem.tag.value == "Link":
                    tagged_link_count += 1
                    text = elem.text.lower().strip()
                    if text in bad_link_texts:
                        issues.append(ValidationIssue(
                            criterion="2.4.4",
                            severity=IssueSeverity.ERROR,
                            message=f"Non-descriptive link text: '{elem.text}'",
                            page=page.page_number,
                            element=elem.text,
                            suggestion="Use descriptive text that indicates the link's purpose",
                            auto_fixable=False,
                        ))

            # Check untagged hyperlinks from PDF annotations
            page_links = getattr(page, "links", [])
            untagged_link_count = 0
            for link_info in page_links:
                # URI links (kind=2) that may not have Link tags
                uri = link_info.get("uri", "")
                link_text = link_info.get("text", "").strip()

                if uri:
                    untagged_link_count += 1

                    # Check for non-descriptive text
                    if link_text.lower() in bad_link_texts:
                        issues.append(ValidationIssue(
                            criterion="2.4.4",
                            severity=IssueSeverity.ERROR,
                            message=f"Non-descriptive link text: '{link_text}' (URL: {uri[:60]})",
                            page=page.page_number,
                            element=link_text,
                            suggestion="Use descriptive text that indicates the link's purpose",
                        ))
                    elif not link_text:
                        issues.append(ValidationIssue(
                            criterion="2.4.4",
                            severity=IssueSeverity.WARNING,
                            message=f"Link with no visible text on page {page.page_number} (URL: {uri[:60]})",
                            page=page.page_number,
                            suggestion="Ensure the link has visible, descriptive text",
                        ))

            # Warn if there are URI links but no Link tags at all
            if untagged_link_count > 0 and tagged_link_count == 0:
                issues.append(ValidationIssue(
                    criterion="1.3.1",
                    severity=IssueSeverity.WARNING,
                    message=f"{untagged_link_count} hyperlink(s) on page {page.page_number} "
                            f"are not tagged as Link elements",
                    page=page.page_number,
                    suggestion="Tag hyperlinks with Link structure elements for accessibility",
                ))

        return issues

    @staticmethod
    def _int_to_rgb(color_int: int) -> Tuple[int, int, int]:
        """Convert a PyMuPDF color integer to (R, G, B) 0-255 tuple."""
        # PyMuPDF stores color as an integer: 0xRRGGBB
        r = (color_int >> 16) & 0xFF
        g = (color_int >> 8) & 0xFF
        b = color_int & 0xFF
        return (r, g, b)

    @staticmethod
    def _relative_luminance(r: int, g: int, b: int) -> float:
        """Calculate WCAG relative luminance from sRGB values (0-255)."""
        def linearize(c: int) -> float:
            cs = c / 255.0
            return cs / 12.92 if cs <= 0.04045 else ((cs + 0.055) / 1.055) ** 2.4

        return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)

    @staticmethod
    def _contrast_ratio(lum1: float, lum2: float) -> float:
        """Calculate contrast ratio between two luminance values."""
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        return (lighter + 0.05) / (darker + 0.05)

    @staticmethod
    def _is_large_text(size: float, flags: int = 0) -> bool:
        """Determine if text qualifies as 'large' under WCAG (>=18pt or >=14pt bold)."""
        is_bold = bool(flags & (1 << 4))  # fitz bold flag
        if is_bold:
            return size >= 14.0
        return size >= 18.0

    def _check_color_contrast(self, doc: PDFDocument) -> List[ValidationIssue]:
        """Check color contrast (WCAG 1.4.3 / 1.4.6)."""
        issues = []

        # Assume white background (default for most PDFs)
        bg_luminance = self._relative_luminance(255, 255, 255)

        check_aaa = self.target_level == WCAGLevel.AAA

        for page in doc.pages:
            for elem in page.elements:
                if elem.element_type != "text":
                    continue

                color_int = elem.attributes.get("color", 0)
                size = elem.attributes.get("size", 12)
                flags = elem.attributes.get("flags", 0)

                r, g, b = self._int_to_rgb(color_int)
                text_luminance = self._relative_luminance(r, g, b)
                ratio = self._contrast_ratio(text_luminance, bg_luminance)
                large = self._is_large_text(size, flags)

                # AA thresholds
                aa_threshold = CONTRAST_LARGE_TEXT_AA if large else CONTRAST_NORMAL_TEXT_AA
                if ratio < aa_threshold:
                    issues.append(ValidationIssue(
                        criterion="1.4.3",
                        severity=IssueSeverity.ERROR,
                        message=(
                            f"Insufficient contrast {ratio:.1f}:1 "
                            f"(needs {aa_threshold}:1) on page {page.page_number}: "
                            f"'{elem.text[:40]}...'" if len(elem.text) > 40 else
                            f"Insufficient contrast {ratio:.1f}:1 "
                            f"(needs {aa_threshold}:1) on page {page.page_number}: "
                            f"'{elem.text}'"
                        ),
                        page=page.page_number,
                        element=elem.text[:50],
                        suggestion=f"Increase text contrast to at least {aa_threshold}:1",
                    ))
                elif check_aaa:
                    # AAA thresholds
                    aaa_threshold = CONTRAST_LARGE_TEXT_AAA if large else CONTRAST_NORMAL_TEXT_AAA
                    if ratio < aaa_threshold:
                        issues.append(ValidationIssue(
                            criterion="1.4.6",
                            severity=IssueSeverity.WARNING,
                            message=(
                                f"Contrast {ratio:.1f}:1 below AAA threshold "
                                f"({aaa_threshold}:1) on page {page.page_number}: "
                                f"'{elem.text[:40]}'"
                            ),
                            page=page.page_number,
                            element=elem.text[:50],
                            suggestion=f"Increase text contrast to at least {aaa_threshold}:1 for AAA",
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

    @staticmethod
    def prioritize_issues(issues: List[ValidationIssue]) -> List[ValidationIssue]:
        """
        Sort issues by priority: WCAG level (A first), severity (ERROR first),
        then screen-reader-blocking criteria first.

        Args:
            issues: List of validation issues

        Returns:
            Sorted list (highest priority first)
        """
        SCREEN_READER_BLOCKERS = {"1.3.1", "1.3.2", "1.1.1", "2.4.2", "3.1.1"}

        LEVEL_ORDER = {WCAGLevel.A: 0, WCAGLevel.AA: 1, WCAGLevel.AAA: 2}
        SEVERITY_ORDER = {
            IssueSeverity.ERROR: 0,
            IssueSeverity.WARNING: 1,
            IssueSeverity.INFO: 2,
        }

        def sort_key(issue: ValidationIssue):
            criterion_info = WCAG_CRITERIA.get(issue.criterion, {})
            level = criterion_info.get("level", WCAGLevel.AAA)
            level_val = LEVEL_ORDER.get(level, 2)
            severity_val = SEVERITY_ORDER.get(issue.severity, 2)
            blocker_val = 0 if issue.criterion in SCREEN_READER_BLOCKERS else 1
            return (level_val, severity_val, blocker_val)

        return sorted(issues, key=sort_key)
