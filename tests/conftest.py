"""
Pytest configuration and fixtures for Accessible PDF Toolkit tests.
"""

import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def temp_app_dir():
    """Create a temporary application directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(autouse=True)
def mock_app_dirs(temp_app_dir, monkeypatch):
    """Mock application directories to use temp directory."""
    monkeypatch.setattr(
        "accessible_pdf_toolkit.utils.constants.APP_DATA_DIR",
        temp_app_dir,
    )
    monkeypatch.setattr(
        "accessible_pdf_toolkit.utils.constants.DATABASE_FILE",
        temp_app_dir / "test.db",
    )
    monkeypatch.setattr(
        "accessible_pdf_toolkit.utils.constants.LOG_FILE",
        temp_app_dir / "logs" / "test.log",
    )


@pytest.fixture
def sample_pdf_content():
    """Return minimal PDF content for testing."""
    # Minimal valid PDF
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
196
%%EOF
"""


@pytest.fixture
def sample_pdf_file(temp_app_dir, sample_pdf_content):
    """Create a sample PDF file for testing."""
    pdf_path = temp_app_dir / "sample.pdf"
    pdf_path.write_bytes(sample_pdf_content)
    return pdf_path


@pytest.fixture
def mock_fitz_document():
    """Create a mock PyMuPDF document."""
    doc = MagicMock()
    doc.__len__ = MagicMock(return_value=2)
    doc.metadata = {
        "title": "Test Document",
        "author": "Test Author",
        "subject": "Test Subject",
    }

    # Mock pages
    page1 = MagicMock()
    page1.rect.width = 612
    page1.rect.height = 792
    page1.get_text.return_value = "Page 1 content"
    page1.get_images.return_value = []

    page2 = MagicMock()
    page2.rect.width = 612
    page2.rect.height = 792
    page2.get_text.return_value = "Page 2 content"
    page2.get_images.return_value = []

    doc.__getitem__ = MagicMock(side_effect=lambda i: [page1, page2][i])

    return doc


@pytest.fixture
def mock_ai_response():
    """Create a mock AI response."""
    from accessible_pdf_toolkit.core.ai_processor import AIResponse, AIBackend

    return AIResponse(
        success=True,
        content='{"headings": [{"text": "Title", "level": 1}]}',
        model="test-model",
        backend=AIBackend.OLLAMA,
    )


# Skip GUI tests if PyQt6 is not available or display is not available
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "gui: mark test as requiring GUI (skipped if no display)",
    )


def pytest_collection_modifyitems(config, items):
    """Skip GUI tests if appropriate."""
    import os

    # Check if we have a display
    has_display = os.environ.get("DISPLAY") or sys.platform == "darwin"

    # Try importing PyQt6
    try:
        import PyQt6
        has_pyqt = True
    except ImportError:
        has_pyqt = False

    skip_gui = pytest.mark.skip(reason="GUI tests require PyQt6 and display")

    for item in items:
        if "gui" in item.keywords:
            if not has_display or not has_pyqt:
                item.add_marker(skip_gui)
