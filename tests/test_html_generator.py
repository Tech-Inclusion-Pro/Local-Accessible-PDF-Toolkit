"""Tests for HTML generator module."""

import pytest
from unittest.mock import MagicMock
from pathlib import Path
import tempfile

from accessible_pdf_toolkit.core.html_generator import (
    HTMLGenerator,
    HTMLOptions,
    GeneratedHTML,
)
from accessible_pdf_toolkit.core.pdf_handler import PDFDocument, PDFPage, PDFElement
from accessible_pdf_toolkit.utils.constants import TagType


@pytest.fixture
def mock_document():
    """Create a mock PDF document for testing."""
    doc = MagicMock(spec=PDFDocument)
    doc.path = Path("test.pdf")
    doc.title = "Test Document"
    doc.language = "en"
    doc.page_count = 1

    page = MagicMock(spec=PDFPage)
    page.page_number = 1
    page.elements = [
        PDFElement(
            element_type="text",
            text="Main Heading",
            page_number=1,
            bbox=(100, 100, 400, 120),
            tag=TagType.HEADING_1,
            attributes={},
        ),
        PDFElement(
            element_type="text",
            text="This is a paragraph of text.",
            page_number=1,
            bbox=(100, 140, 400, 160),
            tag=TagType.PARAGRAPH,
            attributes={},
        ),
        PDFElement(
            element_type="text",
            text="Subheading",
            page_number=1,
            bbox=(100, 180, 400, 200),
            tag=TagType.HEADING_2,
            attributes={},
        ),
    ]
    page.images = []

    doc.pages = [page]
    return doc


@pytest.fixture
def generator():
    """Create an HTML generator with default options."""
    return HTMLGenerator()


class TestHTMLGenerator:
    """Tests for HTMLGenerator class."""

    def test_generate_basic_html(self, generator, mock_document):
        """Test basic HTML generation."""
        result = generator.generate(mock_document)

        assert isinstance(result, GeneratedHTML)
        assert result.html is not None
        assert len(result.html) > 0
        assert "Test Document" in result.html

    def test_generate_with_title(self, generator, mock_document):
        """Test that document title is included."""
        result = generator.generate(mock_document)

        assert "<title>Test Document</title>" in result.html
        assert "<h1>Test Document</h1>" in result.html

    def test_generate_with_headings(self, generator, mock_document):
        """Test that headings are properly converted."""
        result = generator.generate(mock_document)

        assert "<h1" in result.html
        assert "Main Heading" in result.html
        assert "<h2" in result.html
        assert "Subheading" in result.html

    def test_generate_with_toc(self, mock_document):
        """Test table of contents generation."""
        options = HTMLOptions(include_toc=True)
        generator = HTMLGenerator(options)

        result = generator.generate(mock_document)

        assert 'class="toc"' in result.html
        assert "Contents" in result.html
        assert len(result.toc) > 0

    def test_generate_without_toc(self, mock_document):
        """Test HTML generation without TOC."""
        options = HTMLOptions(include_toc=False)
        generator = HTMLGenerator(options)

        result = generator.generate(mock_document)

        assert 'class="toc"' not in result.html

    def test_generate_with_styles(self, mock_document):
        """Test that styles are included."""
        options = HTMLOptions(include_styles=True)
        generator = HTMLGenerator(options)

        result = generator.generate(mock_document)

        assert "<style>" in result.html

    def test_generate_without_styles(self, mock_document):
        """Test HTML generation without embedded styles."""
        options = HTMLOptions(include_styles=False)
        generator = HTMLGenerator(options)

        result = generator.generate(mock_document)

        assert "<style>" not in result.html

    def test_generate_responsive(self, mock_document):
        """Test responsive meta tag is included."""
        options = HTMLOptions(responsive=True)
        generator = HTMLGenerator(options)

        result = generator.generate(mock_document)

        assert "viewport" in result.html
        assert "width=device-width" in result.html

    def test_generate_with_language(self, mock_document):
        """Test language attribute is set."""
        mock_document.language = "es"
        result = generator.generate(mock_document)

        assert 'lang="es"' in result.html

    def test_generate_skip_link(self, generator, mock_document):
        """Test skip link for accessibility."""
        result = generator.generate(mock_document)

        assert "skip-link" in result.html
        assert "Skip to main content" in result.html

    def test_generate_main_landmark(self, generator, mock_document):
        """Test main landmark is present."""
        result = generator.generate(mock_document)

        assert '<main' in result.html
        assert 'role="main"' in result.html


class TestHTMLOptions:
    """Tests for HTMLOptions dataclass."""

    def test_default_options(self):
        """Test default options values."""
        options = HTMLOptions()

        assert options.theme == "brand"
        assert options.include_styles is True
        assert options.include_toc is True
        assert options.responsive is True

    def test_custom_options(self):
        """Test custom options."""
        options = HTMLOptions(
            theme="dark",
            include_styles=False,
            include_toc=False,
            language="fr",
        )

        assert options.theme == "dark"
        assert options.include_styles is False
        assert options.language == "fr"


class TestThemes:
    """Tests for HTML themes."""

    def test_brand_theme(self, mock_document):
        """Test brand theme."""
        options = HTMLOptions(theme="brand")
        generator = HTMLGenerator(options)

        result = generator.generate(mock_document)

        assert "--primary:" in result.html

    def test_high_contrast_theme(self, mock_document):
        """Test high contrast theme."""
        options = HTMLOptions(theme="high_contrast")
        generator = HTMLGenerator(options)

        result = generator.generate(mock_document)

        assert "#000000" in result.html or "high_contrast" in result.html

    def test_dark_theme(self, mock_document):
        """Test dark theme."""
        options = HTMLOptions(theme="dark")
        generator = HTMLGenerator(options)

        result = generator.generate(mock_document)

        assert "--background:" in result.html


class TestSaveHTML:
    """Tests for saving HTML files."""

    def test_save_html(self, generator, mock_document):
        """Test saving HTML to file."""
        result = generator.generate(mock_document)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.html"
            success = generator.save(result, output_path)

            assert success is True
            assert output_path.exists()

            content = output_path.read_text()
            assert "Test Document" in content

    def test_save_creates_directory(self, generator, mock_document):
        """Test that save creates parent directory."""
        result = generator.generate(mock_document)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "output.html"
            success = generator.save(result, output_path)

            assert success is True
            assert output_path.exists()


class TestSectionExtraction:
    """Tests for section extraction."""

    def test_extract_section(self, mock_document):
        """Test extracting a specific section."""
        generator = HTMLGenerator()

        result = generator.generate_section(
            mock_document,
            start_heading="Main Heading",
        )

        assert isinstance(result, GeneratedHTML)
        assert result.title == "Main Heading"
