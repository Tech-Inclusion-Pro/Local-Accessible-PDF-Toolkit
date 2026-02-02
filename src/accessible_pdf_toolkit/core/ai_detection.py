"""
AI detection service for analyzing PDF documents and generating accessibility suggestions.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import uuid

from ..utils.constants import DetectionType, OVERLAY_COLORS
from ..utils.logger import get_logger
from .pdf_handler import PDFDocument, PDFElement, PDFPage
from .ai_processor import AIProcessor, get_ai_processor, AIBackend

logger = get_logger(__name__)


class DetectionStatus(Enum):
    """Status of a detection/suggestion."""
    NEEDS_ATTENTION = "needs_attention"
    CORRECT = "correct"
    MISSING = "missing"
    APPLIED = "applied"
    SKIPPED = "skipped"


@dataclass
class Detection:
    """Represents an AI-detected element with suggestion."""

    id: str
    detection_type: DetectionType
    page_number: int
    bbox: Tuple[float, float, float, float]
    status: DetectionStatus
    current_value: Optional[str] = None
    suggested_value: Optional[str] = None
    confidence: float = 0.0
    element_ref: Optional[PDFElement] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def overlay_color(self) -> Tuple[int, int, int, int]:
        """Get the overlay color for this detection type."""
        return OVERLAY_COLORS.get(
            self.detection_type.value,
            (100, 100, 100, 102)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "detection_type": self.detection_type.value,
            "page_number": self.page_number,
            "bbox": self.bbox,
            "status": self.status.value,
            "current_value": self.current_value,
            "suggested_value": self.suggested_value,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class DocumentAnalysis:
    """Results of document analysis."""

    document_title: Optional[str] = None
    document_language: Optional[str] = None
    document_author: Optional[str] = None
    document_subject: Optional[str] = None
    headings: List[Detection] = field(default_factory=list)
    images: List[Detection] = field(default_factory=list)
    tables: List[Detection] = field(default_factory=list)
    links: List[Detection] = field(default_factory=list)
    reading_order_issues: List[Detection] = field(default_factory=list)

    @property
    def all_detections(self) -> List[Detection]:
        """Get all detections combined."""
        return (
            self.headings +
            self.images +
            self.tables +
            self.links +
            self.reading_order_issues
        )

    @property
    def issues_count(self) -> int:
        """Count items needing attention."""
        return sum(
            1 for d in self.all_detections
            if d.status in [DetectionStatus.NEEDS_ATTENTION, DetectionStatus.MISSING]
        )


class AIDetectionService:
    """Service for AI-powered document analysis and accessibility detection."""

    def __init__(
        self,
        processor: Optional[AIProcessor] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the AI detection service.

        Args:
            processor: AI processor to use (creates default if not provided)
            config: Configuration dictionary
        """
        self._processor = processor
        self._config = config or {}
        self._analysis_cache: Dict[str, DocumentAnalysis] = {}

    def _get_processor(self) -> AIProcessor:
        """Get or create the AI processor."""
        if self._processor is None:
            backend = self._config.get("backend", AIBackend.OLLAMA)
            if isinstance(backend, str):
                backend = AIBackend(backend)
            self._processor = get_ai_processor(backend, self._config)
        return self._processor

    def analyze_document(self, document: PDFDocument) -> DocumentAnalysis:
        """
        Analyze a PDF document for accessibility issues.

        Args:
            document: PDFDocument to analyze

        Returns:
            DocumentAnalysis with all detections
        """
        logger.info(f"Analyzing document: {document.path.name}")

        analysis = DocumentAnalysis(
            document_title=document.title,
            document_language=document.language,
            document_author=document.author,
            document_subject=document.metadata.get("subject"),
        )

        # Check document properties
        if not document.title:
            analysis.headings.append(Detection(
                id=str(uuid.uuid4()),
                detection_type=DetectionType.ISSUE,
                page_number=0,
                bbox=(0, 0, 0, 0),
                status=DetectionStatus.MISSING,
                current_value=None,
                suggested_value=self._suggest_title(document),
                metadata={"issue_type": "missing_title"},
            ))

        if not document.language:
            analysis.headings.append(Detection(
                id=str(uuid.uuid4()),
                detection_type=DetectionType.ISSUE,
                page_number=0,
                bbox=(0, 0, 0, 0),
                status=DetectionStatus.MISSING,
                current_value=None,
                suggested_value="en",
                metadata={"issue_type": "missing_language"},
            ))

        # Analyze each page
        for page in document.pages:
            analysis.headings.extend(self.detect_headings(page))
            analysis.images.extend(self.detect_images_needing_alt(page, document))
            analysis.tables.extend(self.detect_tables(page))
            analysis.links.extend(self.detect_links(page))

        logger.info(
            f"Analysis complete: {len(analysis.headings)} headings, "
            f"{len(analysis.images)} images, {len(analysis.tables)} tables, "
            f"{len(analysis.links)} links"
        )

        return analysis

    def detect_headings(self, page: PDFPage) -> List[Detection]:
        """
        Detect headings on a page based on font characteristics.

        Args:
            page: PDFPage to analyze

        Returns:
            List of heading detections
        """
        detections = []

        # Calculate average font size for the page
        sizes = [
            elem.attributes.get("size", 0)
            for elem in page.elements
            if elem.attributes.get("size", 0) > 0
        ]

        if not sizes:
            return detections

        avg_size = sum(sizes) / len(sizes)

        for elem in page.elements:
            size = elem.attributes.get("size", 0)
            font = elem.attributes.get("font", "").lower()
            text = elem.text.strip()

            if not text or len(text) > 200:
                continue

            # Detect potential headings based on size and style
            is_heading = False
            suggested_level = None

            if size > avg_size * 1.8:
                is_heading = True
                suggested_level = 1
            elif size > avg_size * 1.5:
                is_heading = True
                suggested_level = 2
            elif size > avg_size * 1.2:
                is_heading = True
                suggested_level = 3
            elif "bold" in font or size > avg_size * 1.1:
                is_heading = True
                suggested_level = 4

            if is_heading:
                detections.append(Detection(
                    id=str(uuid.uuid4()),
                    detection_type=DetectionType.HEADING,
                    page_number=page.page_number,
                    bbox=elem.bbox,
                    status=DetectionStatus.NEEDS_ATTENTION,
                    current_value=text,
                    suggested_value=f"H{suggested_level}: {text}",
                    confidence=0.7 if suggested_level <= 2 else 0.5,
                    element_ref=elem,
                    metadata={
                        "font_size": size,
                        "avg_size": avg_size,
                        "suggested_level": suggested_level,
                    },
                ))

        return detections

    def detect_images_needing_alt(
        self,
        page: PDFPage,
        document: PDFDocument,
    ) -> List[Detection]:
        """
        Detect images that need alt text.

        Args:
            page: PDFPage to analyze
            document: Parent document for context

        Returns:
            List of image detections
        """
        detections = []

        for img in page.images:
            # Check if image already has alt text
            has_alt = False  # Would need structure tree check

            detection = Detection(
                id=str(uuid.uuid4()),
                detection_type=DetectionType.IMAGE,
                page_number=page.page_number,
                bbox=(0, 0, img["width"], img["height"]),
                status=DetectionStatus.MISSING if not has_alt else DetectionStatus.CORRECT,
                current_value=None if not has_alt else "Has alt text",
                suggested_value=None,  # Will be generated on demand
                confidence=0.9,
                metadata={
                    "image_index": img["index"],
                    "xref": img["xref"],
                    "width": img["width"],
                    "height": img["height"],
                    "colorspace": img.get("colorspace"),
                },
            )
            detections.append(detection)

        return detections

    def detect_tables(self, page: PDFPage) -> List[Detection]:
        """
        Detect tables on a page.

        Args:
            page: PDFPage to analyze

        Returns:
            List of table detections
        """
        detections = []

        # Simple heuristic: look for aligned text patterns
        # Group elements by their y-position (rows)
        y_groups: Dict[int, List[PDFElement]] = {}

        for elem in page.elements:
            y_key = int(elem.bbox[1] / 10) * 10  # Round to nearest 10
            if y_key not in y_groups:
                y_groups[y_key] = []
            y_groups[y_key].append(elem)

        # Look for rows with multiple aligned columns
        potential_table_rows = []
        for y_key, elements in y_groups.items():
            if len(elements) >= 3:  # At least 3 columns
                # Check if elements are evenly spaced
                x_positions = sorted([e.bbox[0] for e in elements])
                if len(x_positions) >= 3:
                    potential_table_rows.append((y_key, elements))

        # Group consecutive rows into tables
        if len(potential_table_rows) >= 2:
            sorted_rows = sorted(potential_table_rows, key=lambda x: x[0])

            # Find consecutive row groups
            current_table_rows = [sorted_rows[0]]
            for i in range(1, len(sorted_rows)):
                if sorted_rows[i][0] - sorted_rows[i-1][0] <= 30:
                    current_table_rows.append(sorted_rows[i])
                else:
                    if len(current_table_rows) >= 2:
                        # Create detection for this table
                        all_elements = [e for _, elems in current_table_rows for e in elems]
                        bbox = (
                            min(e.bbox[0] for e in all_elements),
                            min(e.bbox[1] for e in all_elements),
                            max(e.bbox[2] for e in all_elements),
                            max(e.bbox[3] for e in all_elements),
                        )
                        detections.append(Detection(
                            id=str(uuid.uuid4()),
                            detection_type=DetectionType.TABLE,
                            page_number=page.page_number,
                            bbox=bbox,
                            status=DetectionStatus.NEEDS_ATTENTION,
                            current_value=f"Table with {len(current_table_rows)} rows",
                            suggested_value="Add table headers and structure",
                            confidence=0.6,
                            metadata={
                                "row_count": len(current_table_rows),
                                "col_count": len(current_table_rows[0][1]) if current_table_rows else 0,
                            },
                        ))
                    current_table_rows = [sorted_rows[i]]

            # Don't forget the last group
            if len(current_table_rows) >= 2:
                all_elements = [e for _, elems in current_table_rows for e in elems]
                bbox = (
                    min(e.bbox[0] for e in all_elements),
                    min(e.bbox[1] for e in all_elements),
                    max(e.bbox[2] for e in all_elements),
                    max(e.bbox[3] for e in all_elements),
                )
                detections.append(Detection(
                    id=str(uuid.uuid4()),
                    detection_type=DetectionType.TABLE,
                    page_number=page.page_number,
                    bbox=bbox,
                    status=DetectionStatus.NEEDS_ATTENTION,
                    current_value=f"Table with {len(current_table_rows)} rows",
                    suggested_value="Add table headers and structure",
                    confidence=0.6,
                    metadata={
                        "row_count": len(current_table_rows),
                        "col_count": len(current_table_rows[0][1]) if current_table_rows else 0,
                    },
                ))

        return detections

    def detect_links(self, page: PDFPage) -> List[Detection]:
        """
        Detect links with poor text on a page.

        Args:
            page: PDFPage to analyze

        Returns:
            List of link detections
        """
        detections = []

        # Bad link text patterns
        bad_patterns = [
            "click here",
            "here",
            "read more",
            "more",
            "link",
            "this link",
            "learn more",
        ]

        for elem in page.elements:
            text_lower = elem.text.strip().lower()

            # Check if text matches bad patterns
            is_bad_link = any(
                text_lower == pattern or text_lower.startswith(pattern + " ")
                for pattern in bad_patterns
            )

            # Check for URLs in text
            has_url = (
                "http://" in text_lower or
                "https://" in text_lower or
                "www." in text_lower
            )

            if is_bad_link or (has_url and len(elem.text) < 100):
                detections.append(Detection(
                    id=str(uuid.uuid4()),
                    detection_type=DetectionType.LINK,
                    page_number=page.page_number,
                    bbox=elem.bbox,
                    status=DetectionStatus.NEEDS_ATTENTION,
                    current_value=elem.text.strip(),
                    suggested_value="Use descriptive link text",
                    confidence=0.8 if is_bad_link else 0.6,
                    element_ref=elem,
                    metadata={
                        "is_bad_pattern": is_bad_link,
                        "has_url": has_url,
                    },
                ))

        return detections

    def generate_alt_text_suggestion(
        self,
        detection: Detection,
        image_bytes: bytes,
        context: str = "",
    ) -> str:
        """
        Generate an alt text suggestion for an image using AI.

        Args:
            detection: The image detection
            image_bytes: Raw image data
            context: Surrounding text context

        Returns:
            Suggested alt text string
        """
        try:
            processor = self._get_processor()
            if not processor.is_available:
                return "Image description unavailable - AI backend not connected"

            response = processor.generate_alt_text(image_bytes, context)
            if response.success:
                return response.content.strip()
            else:
                logger.warning(f"Alt text generation failed: {response.error}")
                return f"Image on page {detection.page_number}"

        except Exception as e:
            logger.error(f"Error generating alt text: {e}")
            return f"Image on page {detection.page_number}"

    def generate_heading_suggestion(
        self,
        detection: Detection,
    ) -> Dict[str, Any]:
        """
        Generate a heading level suggestion.

        Args:
            detection: The heading detection

        Returns:
            Dictionary with suggested level and text
        """
        suggested_level = detection.metadata.get("suggested_level", 2)
        text = detection.current_value or ""

        return {
            "level": suggested_level,
            "text": text,
            "tag": f"H{suggested_level}",
        }

    def _suggest_title(self, document: PDFDocument) -> str:
        """Suggest a document title based on content."""
        if document.pages:
            # Get first significant text from first page
            first_page = document.pages[0]
            for elem in first_page.elements[:5]:
                text = elem.text.strip()
                if len(text) > 10 and len(text) < 100:
                    return text

        return document.path.stem.replace("_", " ").replace("-", " ").title()
