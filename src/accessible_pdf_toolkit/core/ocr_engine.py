"""
OCR engine module using Tesseract for text extraction from images.
"""

import io
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from PIL import Image

from ..utils.constants import OCR_LANGUAGES
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OCRResult:
    """Result from OCR processing."""

    text: str
    confidence: float
    language: str
    words: List[Dict[str, Any]]
    blocks: List[Dict[str, Any]]


@dataclass
class OCRWord:
    """A word detected by OCR."""

    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # left, top, right, bottom
    line_num: int
    block_num: int


class OCREngine:
    """OCR engine using Tesseract for text extraction."""

    def __init__(self, language: str = "eng"):
        """
        Initialize the OCR engine.

        Args:
            language: Tesseract language code (default: eng)
        """
        self.language = language
        self._tesseract_available = self._check_tesseract()

    def _check_tesseract(self) -> bool:
        """Check if Tesseract is available."""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception as e:
            logger.warning(f"Tesseract not available: {e}")
            return False

    @property
    def is_available(self) -> bool:
        """Check if OCR is available."""
        return self._tesseract_available

    @property
    def supported_languages(self) -> Dict[str, str]:
        """Get supported OCR languages."""
        return OCR_LANGUAGES

    def set_language(self, language: str) -> bool:
        """
        Set the OCR language.

        Args:
            language: Tesseract language code

        Returns:
            True if language is valid
        """
        if language in OCR_LANGUAGES:
            self.language = language
            return True
        return False

    def process_image(
        self,
        image_data: bytes,
        output_type: str = "text",
    ) -> Optional[OCRResult]:
        """
        Process an image and extract text.

        Args:
            image_data: Image bytes
            output_type: Type of output (text, data, hocr)

        Returns:
            OCRResult or None if failed
        """
        if not self._tesseract_available:
            logger.error("Tesseract is not available")
            return None

        try:
            import pytesseract

            # Open image
            image = Image.open(io.BytesIO(image_data))

            # Preprocess image for better OCR
            image = self._preprocess_image(image)

            # Get text
            text = pytesseract.image_to_string(image, lang=self.language)

            # Get detailed data
            data = pytesseract.image_to_data(
                image,
                lang=self.language,
                output_type=pytesseract.Output.DICT,
            )

            # Calculate average confidence
            confidences = [c for c in data["conf"] if c > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            # Extract words with positions
            words = []
            for i in range(len(data["text"])):
                if data["text"][i].strip():
                    words.append({
                        "text": data["text"][i],
                        "confidence": data["conf"][i],
                        "bbox": (
                            data["left"][i],
                            data["top"][i],
                            data["left"][i] + data["width"][i],
                            data["top"][i] + data["height"][i],
                        ),
                        "line_num": data["line_num"][i],
                        "block_num": data["block_num"][i],
                    })

            # Group into blocks
            blocks = self._group_into_blocks(words)

            return OCRResult(
                text=text.strip(),
                confidence=avg_confidence,
                language=self.language,
                words=words,
                blocks=blocks,
            )

        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            return None

    def process_pdf_page(
        self,
        page_image: bytes,
        dpi: int = 300,
    ) -> Optional[OCRResult]:
        """
        Process a PDF page image.

        Args:
            page_image: Page rendered as image bytes
            dpi: DPI of the rendered image

        Returns:
            OCRResult or None
        """
        return self.process_image(page_image)

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR results.

        Args:
            image: PIL Image

        Returns:
            Preprocessed image
        """
        # Convert to grayscale if needed
        if image.mode != "L":
            image = image.convert("L")

        # Increase contrast
        try:
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
        except Exception:
            pass

        # Scale up small images
        min_dim = min(image.size)
        if min_dim < 300:
            scale = 300 / min_dim
            new_size = (int(image.width * scale), int(image.height * scale))
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        return image

    def _group_into_blocks(self, words: List[Dict]) -> List[Dict[str, Any]]:
        """
        Group words into text blocks.

        Args:
            words: List of word dictionaries

        Returns:
            List of block dictionaries
        """
        if not words:
            return []

        blocks = {}
        for word in words:
            block_num = word["block_num"]
            if block_num not in blocks:
                blocks[block_num] = {
                    "block_num": block_num,
                    "text": "",
                    "words": [],
                    "bbox": None,
                    "confidence": 0,
                }

            blocks[block_num]["words"].append(word)
            blocks[block_num]["text"] += word["text"] + " "

            # Update bounding box
            word_bbox = word["bbox"]
            if blocks[block_num]["bbox"] is None:
                blocks[block_num]["bbox"] = list(word_bbox)
            else:
                bbox = blocks[block_num]["bbox"]
                bbox[0] = min(bbox[0], word_bbox[0])
                bbox[1] = min(bbox[1], word_bbox[1])
                bbox[2] = max(bbox[2], word_bbox[2])
                bbox[3] = max(bbox[3], word_bbox[3])

        # Calculate block confidence
        for block in blocks.values():
            block["text"] = block["text"].strip()
            confidences = [w["confidence"] for w in block["words"] if w["confidence"] > 0]
            block["confidence"] = sum(confidences) / len(confidences) if confidences else 0
            block["bbox"] = tuple(block["bbox"]) if block["bbox"] else (0, 0, 0, 0)

        return list(blocks.values())

    def detect_tables(self, image_data: bytes) -> List[Dict[str, Any]]:
        """
        Detect tables in an image.

        Args:
            image_data: Image bytes

        Returns:
            List of detected tables with structure
        """
        # Basic table detection using line detection
        try:
            import cv2
            import numpy as np

            # Convert bytes to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

            # Edge detection
            edges = cv2.Canny(img, 50, 150, apertureSize=3)

            # Line detection
            lines = cv2.HoughLinesP(
                edges,
                rho=1,
                theta=np.pi / 180,
                threshold=100,
                minLineLength=100,
                maxLineGap=10,
            )

            if lines is None:
                return []

            # Find horizontal and vertical lines
            h_lines = []
            v_lines = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if abs(y2 - y1) < 10:  # Horizontal
                    h_lines.append(line[0])
                elif abs(x2 - x1) < 10:  # Vertical
                    v_lines.append(line[0])

            # If we have grid-like pattern, likely a table
            if len(h_lines) >= 2 and len(v_lines) >= 2:
                return [{
                    "type": "table",
                    "rows": len(h_lines) - 1,
                    "cols": len(v_lines) - 1,
                    "h_lines": h_lines,
                    "v_lines": v_lines,
                }]

        except ImportError:
            logger.debug("OpenCV not available for table detection")
        except Exception as e:
            logger.warning(f"Table detection failed: {e}")

        return []

    def extract_text_with_layout(
        self,
        image_data: bytes,
    ) -> Optional[str]:
        """
        Extract text preserving layout structure.

        Args:
            image_data: Image bytes

        Returns:
            Text with preserved layout or None
        """
        if not self._tesseract_available:
            return None

        try:
            import pytesseract

            image = Image.open(io.BytesIO(image_data))
            image = self._preprocess_image(image)

            # Use HOCR output for layout preservation
            hocr = pytesseract.image_to_pdf_or_hocr(
                image,
                lang=self.language,
                extension="hocr",
            )

            # Parse HOCR and extract text with positions
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(hocr, "lxml")

            lines = []
            for line in soup.find_all(class_="ocr_line"):
                text = line.get_text().strip()
                if text:
                    lines.append(text)

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Layout extraction failed: {e}")
            return None

    def get_searchable_pdf(
        self,
        image_data: bytes,
        output_path: Path,
    ) -> bool:
        """
        Create a searchable PDF from an image.

        Args:
            image_data: Image bytes
            output_path: Output PDF path

        Returns:
            True if successful
        """
        if not self._tesseract_available:
            return False

        try:
            import pytesseract

            image = Image.open(io.BytesIO(image_data))
            pdf_bytes = pytesseract.image_to_pdf_or_hocr(
                image,
                lang=self.language,
                extension="pdf",
            )

            with open(output_path, "wb") as f:
                f.write(pdf_bytes)

            logger.info(f"Created searchable PDF: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create searchable PDF: {e}")
            return False
