"""
HTML generator module for converting PDFs to accessible HTML.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass, field
import html
import re

from ..utils.constants import COLORS, TagType
from ..utils.logger import get_logger
from .pdf_handler import PDFDocument, PDFPage, PDFElement

logger = get_logger(__name__)


@dataclass
class HTMLOptions:
    """Options for HTML generation."""

    theme: str = "brand"           # brand, high_contrast, dark
    include_styles: bool = True
    include_toc: bool = True
    responsive: bool = True
    include_images: bool = True
    embed_images: bool = False     # Embed as base64 vs external files
    section_dividers: bool = True
    add_aria: bool = True
    language: str = "en"


@dataclass
class GeneratedHTML:
    """Result of HTML generation."""

    html: str
    title: str
    toc: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class HTMLGenerator:
    """Generates accessible HTML from PDF documents."""

    # Theme CSS templates
    THEMES = {
        "brand": f"""
            :root {{
                --primary: {COLORS.PRIMARY};
                --primary-dark: {COLORS.PRIMARY_DARK};
                --background: {COLORS.BACKGROUND};
                --surface: {COLORS.SURFACE};
                --text: {COLORS.TEXT_PRIMARY};
                --text-secondary: {COLORS.TEXT_SECONDARY};
                --border: {COLORS.BORDER};
                --link: {COLORS.PRIMARY};
                --focus: {COLORS.PRIMARY};
            }}
        """,
        "high_contrast": f"""
            :root {{
                --primary: {COLORS.HC_LINK};
                --primary-dark: {COLORS.HC_LINK};
                --background: {COLORS.HC_BACKGROUND};
                --surface: {COLORS.HC_BACKGROUND};
                --text: {COLORS.HC_TEXT};
                --text-secondary: {COLORS.HC_TEXT};
                --border: {COLORS.HC_TEXT};
                --link: {COLORS.HC_LINK};
                --focus: {COLORS.HC_FOCUS};
            }}
        """,
        "dark": f"""
            :root {{
                --primary: {COLORS.PRIMARY_LIGHT};
                --primary-dark: {COLORS.PRIMARY};
                --background: {COLORS.DARK_BACKGROUND};
                --surface: {COLORS.DARK_SURFACE};
                --text: {COLORS.DARK_TEXT};
                --text-secondary: #9CA3AF;
                --border: {COLORS.DARK_BORDER};
                --link: {COLORS.PRIMARY_LIGHT};
                --focus: {COLORS.PRIMARY_LIGHT};
            }}
        """,
    }

    BASE_CSS = """
        * {
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: var(--text);
            background-color: var(--background);
            margin: 0;
            padding: 0;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
        }

        h1, h2, h3, h4, h5, h6 {
            color: var(--text);
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            line-height: 1.3;
        }

        h1 { font-size: 2rem; border-bottom: 2px solid var(--primary); padding-bottom: 0.5rem; }
        h2 { font-size: 1.5rem; }
        h3 { font-size: 1.25rem; }
        h4 { font-size: 1.1rem; }

        p {
            margin: 1em 0;
        }

        a {
            color: var(--link);
            text-decoration: underline;
        }

        a:hover {
            color: var(--primary-dark);
        }

        a:focus {
            outline: 3px solid var(--focus);
            outline-offset: 2px;
        }

        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1rem 0;
        }

        figure {
            margin: 1.5rem 0;
            padding: 1rem;
            background-color: var(--surface);
            border: 1px solid var(--border);
            border-radius: 4px;
        }

        figcaption {
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-top: 0.5rem;
            font-style: italic;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
        }

        th, td {
            border: 1px solid var(--border);
            padding: 0.75rem;
            text-align: left;
        }

        th {
            background-color: var(--primary);
            color: white;
            font-weight: bold;
        }

        tr:nth-child(even) {
            background-color: var(--surface);
        }

        ul, ol {
            margin: 1em 0;
            padding-left: 2em;
        }

        li {
            margin: 0.5em 0;
        }

        blockquote {
            border-left: 4px solid var(--primary);
            margin: 1.5rem 0;
            padding: 1rem 1.5rem;
            background-color: var(--surface);
            font-style: italic;
        }

        code {
            font-family: 'Fira Code', 'Courier New', monospace;
            background-color: var(--surface);
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-size: 0.9em;
        }

        pre {
            background-color: var(--surface);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 1rem;
            overflow-x: auto;
        }

        pre code {
            background: none;
            padding: 0;
        }

        .toc {
            background-color: var(--surface);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 1.5rem;
            margin: 2rem 0;
        }

        .toc h2 {
            margin-top: 0;
            font-size: 1.2rem;
        }

        .toc ul {
            list-style: none;
            padding-left: 0;
        }

        .toc li {
            margin: 0.5rem 0;
        }

        .toc a {
            text-decoration: none;
        }

        .toc a:hover {
            text-decoration: underline;
        }

        .toc-level-2 { padding-left: 1rem; }
        .toc-level-3 { padding-left: 2rem; }
        .toc-level-4 { padding-left: 3rem; }

        .section-divider {
            border: none;
            border-top: 1px solid var(--border);
            margin: 2rem 0;
        }

        .skip-link {
            position: absolute;
            top: -40px;
            left: 0;
            background: var(--primary);
            color: white;
            padding: 8px 16px;
            text-decoration: none;
            z-index: 1000;
        }

        .skip-link:focus {
            top: 0;
        }

        /* Print styles */
        @media print {
            body {
                background: white;
                color: black;
            }

            a {
                color: black;
                text-decoration: underline;
            }

            .toc {
                break-inside: avoid;
            }
        }
    """

    def __init__(self, options: Optional[HTMLOptions] = None):
        """
        Initialize the HTML generator.

        Args:
            options: HTML generation options
        """
        self.options = options or HTMLOptions()

    def generate(self, document: PDFDocument) -> GeneratedHTML:
        """
        Generate accessible HTML from a PDF document.

        Args:
            document: PDFDocument to convert

        Returns:
            GeneratedHTML with the generated content
        """
        result = GeneratedHTML(
            html="",
            title=document.title or document.path.stem,
        )

        # Build HTML parts
        content_parts = []
        toc_entries = []
        heading_counter = 0

        for page in document.pages:
            page_content, page_toc = self._process_page(page, heading_counter)
            content_parts.append(page_content)
            toc_entries.extend(page_toc)
            heading_counter += len(page_toc)

            if self.options.section_dividers and page != document.pages[-1]:
                content_parts.append('<hr class="section-divider" aria-hidden="true">')

        result.toc = toc_entries

        # Build complete HTML
        result.html = self._build_html(
            title=result.title,
            content="\n".join(content_parts),
            toc=toc_entries,
            language=document.language or self.options.language,
        )

        return result

    def _process_page(
        self,
        page: PDFPage,
        heading_offset: int,
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Process a single page.

        Args:
            page: PDFPage to process
            heading_offset: Offset for heading IDs

        Returns:
            Tuple of (html_content, toc_entries)
        """
        html_parts = []
        toc_entries = []

        for element in page.elements:
            elem_html, toc_entry = self._element_to_html(
                element,
                len(toc_entries) + heading_offset,
            )
            if elem_html:
                html_parts.append(elem_html)
            if toc_entry:
                toc_entries.append(toc_entry)

        # Add images
        if self.options.include_images:
            for img in page.images:
                img_html = self._image_to_html(img, page.page_number)
                if img_html:
                    html_parts.append(img_html)

        return "\n".join(html_parts), toc_entries

    def _element_to_html(
        self,
        element: PDFElement,
        index: int,
    ) -> tuple[str, Optional[Dict[str, Any]]]:
        """
        Convert a PDF element to HTML.

        Args:
            element: PDFElement to convert
            index: Element index for ID generation

        Returns:
            Tuple of (html_string, toc_entry_or_none)
        """
        text = html.escape(element.text.strip())
        if not text:
            return "", None

        toc_entry = None

        if not element.tag:
            # Untagged content becomes paragraph
            return f"<p>{text}</p>", None

        tag = element.tag

        # Headings
        if tag.value.startswith("H") and len(tag.value) == 2:
            level = tag.value[1]
            heading_id = f"heading-{index}"
            toc_entry = {
                "id": heading_id,
                "text": text,
                "level": int(level),
            }
            return f'<h{level} id="{heading_id}">{text}</h{level}>', toc_entry

        # Paragraph
        if tag == TagType.PARAGRAPH:
            return f"<p>{text}</p>", None

        # List items
        if tag == TagType.LIST_ITEM:
            return f"<li>{text}</li>", None

        # Figure with alt text
        if tag == TagType.FIGURE:
            alt = html.escape(element.alt_text or "Image")
            caption = f'<figcaption>{alt}</figcaption>' if element.alt_text else ""
            return f"""
<figure role="img" aria-label="{alt}">
    <div>[Image placeholder]</div>
    {caption}
</figure>""", None

        # Quote
        if tag == TagType.QUOTE:
            return f"<blockquote>{text}</blockquote>", None

        # Code
        if tag == TagType.CODE:
            return f"<pre><code>{text}</code></pre>", None

        # Link
        if tag == TagType.LINK:
            # Try to extract URL from attributes
            url = element.attributes.get("url", "#")
            return f'<a href="{html.escape(url)}">{text}</a>', None

        # Table elements handled separately
        if tag in [TagType.TABLE, TagType.TABLE_ROW, TagType.TABLE_HEADER, TagType.TABLE_DATA]:
            return "", None  # Tables need special handling

        # Default: wrap in span
        return f'<span class="pdf-{tag.value.lower()}">{text}</span>', None

    def _image_to_html(self, img: Dict[str, Any], page_num: int) -> str:
        """
        Convert an image to HTML.

        Args:
            img: Image info dictionary
            page_num: Page number

        Returns:
            HTML string
        """
        alt = img.get("alt_text", f"Image from page {page_num}")
        alt = html.escape(alt)

        if self.options.embed_images and "data" in img:
            # Embed as base64
            import base64
            data = base64.b64encode(img["data"]).decode()
            ext = img.get("ext", "png")
            return f'<img src="data:image/{ext};base64,{data}" alt="{alt}">'
        else:
            # External file reference
            filename = f"image_p{page_num}_{img.get('index', 0)}.{img.get('ext', 'png')}"
            return f'<img src="images/{filename}" alt="{alt}">'

    def _build_toc(self, entries: List[Dict[str, Any]]) -> str:
        """
        Build table of contents HTML.

        Args:
            entries: List of TOC entries

        Returns:
            HTML string
        """
        if not entries:
            return ""

        lines = ['<nav class="toc" aria-label="Table of Contents">']
        lines.append("<h2>Contents</h2>")
        lines.append("<ul>")

        for entry in entries:
            level = entry["level"]
            lines.append(
                f'<li class="toc-level-{level}">'
                f'<a href="#{entry["id"]}">{html.escape(entry["text"])}</a>'
                f"</li>"
            )

        lines.append("</ul>")
        lines.append("</nav>")

        return "\n".join(lines)

    def _build_html(
        self,
        title: str,
        content: str,
        toc: List[Dict[str, Any]],
        language: str,
    ) -> str:
        """
        Build the complete HTML document.

        Args:
            title: Document title
            content: Main content HTML
            toc: Table of contents entries
            language: Document language

        Returns:
            Complete HTML document
        """
        # Get theme CSS
        theme_css = self.THEMES.get(self.options.theme, self.THEMES["brand"])

        # Build TOC if requested
        toc_html = self._build_toc(toc) if self.options.include_toc else ""

        # Build styles
        styles = ""
        if self.options.include_styles:
            styles = f"""
<style>
{theme_css}
{self.BASE_CSS}
</style>
"""

        # Build responsive meta tag
        responsive_meta = ""
        if self.options.responsive:
            responsive_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'

        # Build complete HTML
        html_doc = f"""<!DOCTYPE html>
<html lang="{html.escape(language)}">
<head>
    <meta charset="UTF-8">
    {responsive_meta}
    <title>{html.escape(title)}</title>
    {styles}
</head>
<body>
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <main id="main-content" class="container" role="main">
        <header>
            <h1>{html.escape(title)}</h1>
        </header>

        {toc_html}

        <article>
            {content}
        </article>
    </main>

    <footer class="container" role="contentinfo">
        <p>Generated by Accessible PDF Toolkit</p>
    </footer>
</body>
</html>
"""

        return html_doc

    def save(
        self,
        result: GeneratedHTML,
        output_path: Path,
        save_images: bool = True,
    ) -> bool:
        """
        Save the generated HTML to a file.

        Args:
            result: GeneratedHTML to save
            output_path: Output file path
            save_images: Whether to save extracted images

        Returns:
            True if successful
        """
        try:
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save HTML
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.html)

            # Save images if requested
            if save_images and result.images:
                images_dir = output_path.parent / "images"
                images_dir.mkdir(exist_ok=True)

                for img in result.images:
                    if "data" in img and "filename" in img:
                        img_path = images_dir / img["filename"]
                        with open(img_path, "wb") as f:
                            f.write(img["data"])

            logger.info(f"Saved HTML to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save HTML: {e}")
            return False

    def generate_section(
        self,
        document: PDFDocument,
        start_heading: str,
        end_heading: Optional[str] = None,
    ) -> GeneratedHTML:
        """
        Generate HTML for a specific section of the document.

        Args:
            document: Source document
            start_heading: Text of the starting heading
            end_heading: Text of the ending heading (exclusive)

        Returns:
            GeneratedHTML for the section
        """
        result = GeneratedHTML(
            html="",
            title=start_heading,
        )

        in_section = False
        content_parts = []
        toc_entries = []

        for page in document.pages:
            for element in page.elements:
                # Check for section start
                if element.text.strip() == start_heading:
                    in_section = True

                # Check for section end
                if end_heading and element.text.strip() == end_heading:
                    in_section = False
                    break

                if in_section:
                    elem_html, toc_entry = self._element_to_html(
                        element,
                        len(toc_entries),
                    )
                    if elem_html:
                        content_parts.append(elem_html)
                    if toc_entry:
                        toc_entries.append(toc_entry)

        result.toc = toc_entries
        result.html = self._build_html(
            title=start_heading,
            content="\n".join(content_parts),
            toc=toc_entries,
            language=document.language or self.options.language,
        )

        return result
