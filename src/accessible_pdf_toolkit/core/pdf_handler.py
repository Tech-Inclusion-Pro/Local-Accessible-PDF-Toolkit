"""
PDF handling module for opening, parsing, and modifying PDFs.
"""

import io
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Iterator
from dataclasses import dataclass, field
from enum import Enum

import fitz  # PyMuPDF
import pikepdf

from ..utils.constants import TagType, SUPPORTED_INPUT_FORMATS
from ..utils.logger import get_logger
from ..utils.file_operations import FileOperations

logger = get_logger(__name__)


@dataclass
class PDFElement:
    """Represents an element in a PDF document."""

    element_type: str
    text: str
    page_number: int
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    tag: Optional[TagType] = None
    alt_text: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PDFPage:
    """Represents a page in a PDF document."""

    page_number: int
    width: float
    height: float
    text: str
    elements: List[PDFElement] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PDFDocument:
    """Represents an open PDF document."""

    path: Path
    title: Optional[str]
    author: Optional[str]
    language: Optional[str]
    page_count: int
    pages: List[PDFPage] = field(default_factory=list)
    is_tagged: bool = False
    has_structure: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Internal references
    _fitz_doc: Optional[fitz.Document] = field(default=None, repr=False)
    _pike_doc: Optional[pikepdf.Pdf] = field(default=None, repr=False)


class PDFHandler:
    """Handles PDF operations including opening, parsing, and modification."""

    def __init__(self):
        self._current_doc: Optional[PDFDocument] = None

    def open(self, file_path: Path) -> Optional[PDFDocument]:
        """
        Open a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            PDFDocument or None if failed
        """
        # Validate file
        is_valid, error = FileOperations.validate_pdf(file_path)
        if not is_valid:
            logger.error(f"Invalid PDF: {error}")
            return None

        try:
            # Open with PyMuPDF for rendering and text extraction
            fitz_doc = fitz.open(str(file_path))

            # Open with pikepdf for structure manipulation
            pike_doc = pikepdf.open(file_path)

            # Extract metadata
            metadata = self._extract_metadata(fitz_doc, pike_doc)

            # Create document object
            doc = PDFDocument(
                path=file_path,
                title=metadata.get("title"),
                author=metadata.get("author"),
                language=metadata.get("language"),
                page_count=len(fitz_doc),
                is_tagged=self._check_tagged(pike_doc),
                has_structure=self._check_structure(pike_doc),
                metadata=metadata,
                _fitz_doc=fitz_doc,
                _pike_doc=pike_doc,
            )

            # Parse pages
            doc.pages = self._parse_pages(fitz_doc)

            self._current_doc = doc
            logger.info(f"Opened PDF: {file_path.name} ({doc.page_count} pages)")
            return doc

        except Exception as e:
            logger.error(f"Failed to open PDF: {e}")
            return None

    def close(self) -> None:
        """Close the current document."""
        if self._current_doc:
            if self._current_doc._fitz_doc:
                self._current_doc._fitz_doc.close()
            if self._current_doc._pike_doc:
                self._current_doc._pike_doc.close()
            self._current_doc = None
            logger.debug("Document closed")

    def _extract_metadata(
        self,
        fitz_doc: fitz.Document,
        pike_doc: pikepdf.Pdf,
    ) -> Dict[str, Any]:
        """Extract metadata from PDF."""
        metadata = {}

        # From PyMuPDF
        fitz_meta = fitz_doc.metadata
        if fitz_meta:
            metadata["title"] = fitz_meta.get("title", "")
            metadata["author"] = fitz_meta.get("author", "")
            metadata["subject"] = fitz_meta.get("subject", "")
            metadata["creator"] = fitz_meta.get("creator", "")
            metadata["producer"] = fitz_meta.get("producer", "")
            metadata["creation_date"] = fitz_meta.get("creationDate", "")
            metadata["modification_date"] = fitz_meta.get("modDate", "")

        # Language from catalog
        try:
            if "/Lang" in pike_doc.Root:
                metadata["language"] = str(pike_doc.Root.Lang)
        except Exception:
            pass

        return metadata

    def _check_tagged(self, pike_doc: pikepdf.Pdf) -> bool:
        """Check if PDF is tagged."""
        try:
            if "/MarkInfo" in pike_doc.Root:
                mark_info = pike_doc.Root.MarkInfo
                if "/Marked" in mark_info:
                    return bool(mark_info.Marked)
        except Exception:
            pass
        return False

    def _check_structure(self, pike_doc: pikepdf.Pdf) -> bool:
        """Check if PDF has structure tree."""
        try:
            return "/StructTreeRoot" in pike_doc.Root
        except Exception:
            return False

    def _parse_pages(self, fitz_doc: fitz.Document) -> List[PDFPage]:
        """Parse all pages in the document."""
        pages = []

        for page_num in range(len(fitz_doc)):
            fitz_page = fitz_doc[page_num]

            page = PDFPage(
                page_number=page_num + 1,
                width=fitz_page.rect.width,
                height=fitz_page.rect.height,
                text=fitz_page.get_text("text"),
                elements=self._extract_elements(fitz_page, page_num + 1),
                images=self._extract_images(fitz_page, page_num + 1),
            )
            pages.append(page)

        return pages

    def _extract_elements(self, fitz_page: fitz.Page, page_num: int) -> List[PDFElement]:
        """Extract text elements from a page."""
        elements = []

        # Get text blocks
        blocks = fitz_page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

        for block in blocks:
            if block["type"] == 0:  # Text block
                for line in block.get("lines", []):
                    text = "".join(span["text"] for span in line.get("spans", []))
                    if text.strip():
                        bbox = line["bbox"]
                        element = PDFElement(
                            element_type="text",
                            text=text,
                            page_number=page_num,
                            bbox=tuple(bbox),
                            attributes={
                                "font": line["spans"][0].get("font", "") if line["spans"] else "",
                                "size": line["spans"][0].get("size", 0) if line["spans"] else 0,
                            },
                        )
                        elements.append(element)

        return elements

    def _extract_images(self, fitz_page: fitz.Page, page_num: int) -> List[Dict[str, Any]]:
        """Extract images from a page."""
        images = []

        image_list = fitz_page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            try:
                base_image = fitz_page.parent.extract_image(xref)
                images.append({
                    "index": img_index,
                    "xref": xref,
                    "width": base_image["width"],
                    "height": base_image["height"],
                    "colorspace": base_image["colorspace"],
                    "bpc": base_image["bpc"],
                    "ext": base_image["ext"],
                    "page": page_num,
                })
            except Exception as e:
                logger.warning(f"Failed to extract image {xref}: {e}")

        return images

    def get_image_bytes(self, page_num: int, image_index: int) -> Optional[bytes]:
        """
        Get image bytes from the document.

        Args:
            page_num: Page number (1-indexed)
            image_index: Image index on the page

        Returns:
            Image bytes or None
        """
        if not self._current_doc or not self._current_doc._fitz_doc:
            return None

        try:
            page = self._current_doc._fitz_doc[page_num - 1]
            images = page.get_images(full=True)

            if image_index < len(images):
                xref = images[image_index][0]
                base_image = self._current_doc._fitz_doc.extract_image(xref)
                return base_image["image"]
        except Exception as e:
            logger.error(f"Failed to get image bytes: {e}")

        return None

    def get_page_image(self, page_num: int, zoom: float = 1.0) -> Optional[bytes]:
        """
        Render a page as an image.

        Args:
            page_num: Page number (1-indexed)
            zoom: Zoom factor

        Returns:
            PNG image bytes or None
        """
        if not self._current_doc or not self._current_doc._fitz_doc:
            return None

        try:
            page = self._current_doc._fitz_doc[page_num - 1]
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            return pix.tobytes("png")
        except Exception as e:
            logger.error(f"Failed to render page: {e}")
            return None

    def get_full_text(self) -> str:
        """Get all text from the document."""
        if not self._current_doc:
            return ""

        return "\n\n".join(page.text for page in self._current_doc.pages)

    def set_title(self, title: str) -> bool:
        """Set the document title."""
        if not self._current_doc or not self._current_doc._pike_doc:
            return False

        try:
            with self._current_doc._pike_doc.open_metadata() as meta:
                meta["dc:title"] = title
            self._current_doc.title = title
            return True
        except Exception as e:
            logger.error(f"Failed to set title: {e}")
            return False

    def set_language(self, language: str) -> bool:
        """Set the document language."""
        if not self._current_doc or not self._current_doc._pike_doc:
            return False

        try:
            self._current_doc._pike_doc.Root.Lang = language
            self._current_doc.language = language
            return True
        except Exception as e:
            logger.error(f"Failed to set language: {e}")
            return False

    def add_tag(
        self,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        tag_type: TagType,
        alt_text: Optional[str] = None,
    ) -> bool:
        """
        Add an accessibility tag to an element.

        Args:
            page_num: Page number (1-indexed)
            bbox: Bounding box of the element
            tag_type: Type of tag to add
            alt_text: Alt text for images/figures

        Returns:
            True if successful
        """
        if not self._current_doc or not self._current_doc._pike_doc:
            return False

        try:
            pike_doc = self._current_doc._pike_doc

            # Ensure structure tree exists
            if "/StructTreeRoot" not in pike_doc.Root:
                pike_doc.Root.StructTreeRoot = pikepdf.Dictionary({
                    "/Type": pikepdf.Name("/StructTreeRoot"),
                    "/K": pikepdf.Array([]),
                })
                pike_doc.Root.MarkInfo = pikepdf.Dictionary({
                    "/Marked": True,
                })

            # Create structure element
            struct_elem = pikepdf.Dictionary({
                "/Type": pikepdf.Name("/StructElem"),
                "/S": pikepdf.Name(f"/{tag_type.value}"),
            })

            if alt_text and tag_type == TagType.FIGURE:
                struct_elem["/Alt"] = alt_text

            # Add to structure tree
            struct_tree = pike_doc.Root.StructTreeRoot
            if "/K" not in struct_tree:
                struct_tree["/K"] = pikepdf.Array([])

            struct_tree.K.append(struct_elem)

            logger.debug(f"Added {tag_type.value} tag to page {page_num}")
            return True

        except Exception as e:
            logger.error(f"Failed to add tag: {e}")
            return False

    def save(self, output_path: Optional[Path] = None) -> bool:
        """
        Save the document.

        Args:
            output_path: Output path (uses original path if not specified)

        Returns:
            True if successful
        """
        if not self._current_doc or not self._current_doc._pike_doc:
            return False

        try:
            save_path = output_path or self._current_doc.path
            self._current_doc._pike_doc.save(str(save_path))
            logger.info(f"Saved PDF: {save_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save PDF: {e}")
            return False

    def get_reading_order(self) -> List[PDFElement]:
        """
        Get elements in reading order.

        Returns:
            List of elements sorted by reading order
        """
        if not self._current_doc:
            return []

        all_elements = []
        for page in self._current_doc.pages:
            all_elements.extend(page.elements)

        # Sort by page, then top-to-bottom, then left-to-right
        return sorted(
            all_elements,
            key=lambda e: (e.page_number, e.bbox[1], e.bbox[0]),
        )

    def detect_headings(self) -> List[PDFElement]:
        """
        Detect potential headings based on font size.

        Returns:
            List of elements that may be headings
        """
        if not self._current_doc:
            return []

        # Calculate average font size
        all_sizes = []
        for page in self._current_doc.pages:
            for elem in page.elements:
                size = elem.attributes.get("size", 0)
                if size > 0:
                    all_sizes.append(size)

        if not all_sizes:
            return []

        avg_size = sum(all_sizes) / len(all_sizes)

        # Find elements significantly larger than average
        headings = []
        for page in self._current_doc.pages:
            for elem in page.elements:
                size = elem.attributes.get("size", 0)
                if size > avg_size * 1.2:  # 20% larger than average
                    headings.append(elem)

        return headings

    @property
    def current_document(self) -> Optional[PDFDocument]:
        """Get the currently open document."""
        return self._current_doc

    def get_outline(self) -> List[Dict[str, Any]]:
        """
        Get the document outline (bookmarks).

        Returns:
            List of outline items with title, page, level, and children
        """
        if not self._current_doc or not self._current_doc._fitz_doc:
            return []

        try:
            toc = self._current_doc._fitz_doc.get_toc()
            if not toc:
                return []

            outline = []
            for item in toc:
                level, title, page = item[0], item[1], item[2]
                outline.append({
                    "level": level,
                    "title": title,
                    "page": page,
                })

            return outline

        except Exception as e:
            logger.error(f"Failed to get outline: {e}")
            return []

    def search_text(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for text in the document.

        Args:
            query: Search query string

        Returns:
            List of search results with page, text, and bbox
        """
        if not self._current_doc or not self._current_doc._fitz_doc:
            return []

        if not query or len(query) < 2:
            return []

        results = []
        try:
            for page_num in range(len(self._current_doc._fitz_doc)):
                page = self._current_doc._fitz_doc[page_num]
                matches = page.search_for(query)

                for rect in matches:
                    # Get surrounding text for context
                    text_page = page.get_text("text")
                    start_idx = max(0, text_page.lower().find(query.lower()) - 30)
                    end_idx = min(len(text_page), start_idx + len(query) + 60)
                    context = text_page[start_idx:end_idx].strip()

                    results.append({
                        "page": page_num + 1,
                        "bbox": (rect.x0, rect.y0, rect.x1, rect.y1),
                        "text": query,
                        "context": f"...{context}...",
                    })

            logger.debug(f"Search for '{query}' found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_thumbnail(
        self,
        page_num: int,
        width: int = 100,
        height: int = 130,
    ) -> Optional[bytes]:
        """
        Generate a thumbnail for a page.

        Args:
            page_num: Page number (1-indexed)
            width: Thumbnail width in pixels
            height: Thumbnail height in pixels

        Returns:
            PNG thumbnail bytes or None
        """
        if not self._current_doc or not self._current_doc._fitz_doc:
            return None

        try:
            page = self._current_doc._fitz_doc[page_num - 1]

            # Calculate zoom to fit thumbnail size
            page_rect = page.rect
            zoom_x = width / page_rect.width
            zoom_y = height / page_rect.height
            zoom = min(zoom_x, zoom_y)

            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            return pix.tobytes("png")

        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            return None

    def get_page_links(self, page_num: int) -> List[Dict[str, Any]]:
        """
        Get links from a specific page.

        Args:
            page_num: Page number (1-indexed)

        Returns:
            List of link info with bbox, uri, and type
        """
        if not self._current_doc or not self._current_doc._fitz_doc:
            return []

        try:
            page = self._current_doc._fitz_doc[page_num - 1]
            links = page.get_links()

            result = []
            for link in links:
                link_info = {
                    "bbox": (link["from"].x0, link["from"].y0,
                            link["from"].x1, link["from"].y1),
                    "type": link.get("kind", 0),
                }

                if "uri" in link:
                    link_info["uri"] = link["uri"]
                if "page" in link:
                    link_info["target_page"] = link["page"]

                result.append(link_info)

            return result

        except Exception as e:
            logger.error(f"Failed to get page links: {e}")
            return []
