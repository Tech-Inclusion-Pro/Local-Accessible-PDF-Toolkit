# API Reference

## Core Modules

### PDFHandler

Handles opening, parsing, and modifying PDF documents.

```python
from accessible_pdf_toolkit.core import PDFHandler

handler = PDFHandler()

# Open a PDF
document = handler.open(Path("document.pdf"))

# Get document information
print(f"Title: {document.title}")
print(f"Pages: {document.page_count}")
print(f"Tagged: {document.is_tagged}")

# Get full text
text = handler.get_full_text()

# Detect headings
headings = handler.detect_headings()

# Add a tag
handler.add_tag(
    page_num=1,
    bbox=(100, 100, 400, 120),
    tag_type=TagType.HEADING_1,
)

# Save changes
handler.save(Path("output.pdf"))

# Close document
handler.close()
```

### WCAGValidator

Validates documents for WCAG compliance.

```python
from accessible_pdf_toolkit.core import WCAGValidator, WCAGLevel

validator = WCAGValidator(target_level=WCAGLevel.AA)

# Validate a document
result = validator.validate(document)

# Check results
print(f"Compliant: {result.is_compliant}")
print(f"Score: {result.score}%")
print(f"Errors: {result.summary['errors']}")

# Get issues
for issue in result.issues:
    print(f"{issue.criterion}: {issue.message}")
    if issue.suggestion:
        print(f"  Fix: {issue.suggestion}")

# Get fix suggestions
fixes = validator.get_fix_suggestions(result)
```

### AIProcessor

Interface for AI-powered analysis.

```python
from accessible_pdf_toolkit.core import get_ai_processor, AIBackend

# Create processor
processor = get_ai_processor(AIBackend.OLLAMA)

# Check availability
if processor.is_available:
    # Analyze structure
    response = processor.analyze_structure(text)

    # Generate alt text
    response = processor.generate_alt_text(image_bytes, context="...")

    # Suggest headings
    response = processor.suggest_headings(text)
```

### HTMLGenerator

Converts PDFs to accessible HTML.

```python
from accessible_pdf_toolkit.core import HTMLGenerator, HTMLOptions

options = HTMLOptions(
    theme="brand",
    include_styles=True,
    include_toc=True,
    responsive=True,
)

generator = HTMLGenerator(options)

# Generate HTML
result = generator.generate(document)
print(result.html)

# Save to file
generator.save(result, Path("output.html"))

# Extract section
section = generator.generate_section(
    document,
    start_heading="Chapter 1",
    end_heading="Chapter 2",
)
```

### OCREngine

Extracts text from images using Tesseract.

```python
from accessible_pdf_toolkit.core import OCREngine

engine = OCREngine(language="eng")

# Check availability
if engine.is_available:
    # Process image
    result = engine.process_image(image_bytes)
    print(f"Text: {result.text}")
    print(f"Confidence: {result.confidence}%")

    # Create searchable PDF
    engine.get_searchable_pdf(image_bytes, Path("searchable.pdf"))
```

## Database Models

### User

```python
from accessible_pdf_toolkit.database import User, get_session

session = get_session()

# Create user
user = User(
    username="educator",
    password_hash=hash_password("secret"),
    email="educator@example.com",
)
session.add(user)
session.commit()
```

### Course

```python
from accessible_pdf_toolkit.database import Course

course = Course(
    user_id=user.id,
    code="CS101",
    name="Introduction to Computer Science",
    semester="Fall 2024",
)
session.add(course)
session.commit()
```

### File

```python
from accessible_pdf_toolkit.database import File

file = File(
    original_name="lecture1.pdf",
    file_path="/path/to/lecture1.pdf",
    file_hash="abc123...",
    file_size=1024000,
    course_id=course.id,
    compliance_status="NOT_CHECKED",
)
session.add(file)
session.commit()
```

## Database Queries

```python
from accessible_pdf_toolkit.database import DatabaseQueries

db = DatabaseQueries()

# User operations
user = db.create_user("username", "password")
user = db.authenticate_user("username", "password")

# Course operations
course = db.create_course(user.id, "CS101", "Intro to CS")
courses = db.get_courses(user.id)

# File operations
file = db.create_file("doc.pdf", "/path/doc.pdf", "hash", 1000)
files = db.get_files(course_id=1, compliance_status=ComplianceStatus.COMPLIANT)

# Statistics
stats = db.get_compliance_stats(user.id)
recent = db.get_recent_files(user.id, limit=10)
```

## Encryption

```python
from accessible_pdf_toolkit.database import EncryptionManager

# Without password (machine-specific key)
manager = EncryptionManager()

# With password
manager = EncryptionManager(password="secret")

# Encrypt/decrypt data
encrypted = manager.encrypt(b"sensitive data")
decrypted = manager.decrypt(encrypted)

# Encrypt/decrypt files
manager.encrypt_file(Path("input.pdf"), Path("encrypted.enc"))
manager.decrypt_file(Path("encrypted.enc"), Path("output.pdf"))

# Encrypt/decrypt strings
encrypted_str = manager.encrypt_string("secret text")
decrypted_str = manager.decrypt_string(encrypted_str)
```

## Constants

```python
from accessible_pdf_toolkit.utils.constants import (
    COLORS,          # Brand colors
    WCAGLevel,       # A, AA, AAA
    ComplianceStatus,  # NOT_CHECKED, COMPLIANT, etc.
    AIBackend,       # OLLAMA, LM_STUDIO, etc.
    TagType,         # HEADING_1, PARAGRAPH, etc.
    WCAG_CRITERIA,   # Criterion definitions
    DEFAULT_CONFIG,  # Default settings
)
```

## GUI Components

### MainWindow

```python
from accessible_pdf_toolkit.gui import MainWindow

window = MainWindow(user=user)
window.show()

# Open file
window.open_file(Path("document.pdf"))

# Connect signals
window.file_opened.connect(on_file_opened)
window.file_saved.connect(on_file_saved)
```

### TagEditor

```python
from accessible_pdf_toolkit.gui.tag_editor import TagEditor

editor = TagEditor()
editor.load_document(document)

# Connect signals
editor.document_loaded.connect(on_loaded)
editor.validation_complete.connect(on_validated)
```

### Dashboard

```python
from accessible_pdf_toolkit.gui.dashboard import Dashboard

dashboard = Dashboard(user=user)
dashboard.file_opened.connect(on_file_opened)
dashboard.refresh()
```

## Command Line

```bash
# Run application
python -m accessible_pdf_toolkit.main

# With debug logging
python -m accessible_pdf_toolkit.main --debug

# Skip login
python -m accessible_pdf_toolkit.main --no-login

# Open file directly
python -m accessible_pdf_toolkit.main document.pdf

# Batch processing
python -m accessible_pdf_toolkit.main --batch /path/to/pdfs/
```
