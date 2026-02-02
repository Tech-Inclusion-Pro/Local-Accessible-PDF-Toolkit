# Contributing to Accessible PDF Toolkit

Thank you for your interest in contributing to the Accessible PDF Toolkit! This project aims to make PDF accessibility easier for educators while maintaining privacy compliance.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Use the bug report template
3. Include:
   - OS and Python version
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable

### Suggesting Features

1. Open a feature request issue
2. Describe the use case
3. Explain how it helps accessibility or privacy goals

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Write or update tests
5. Run the test suite: `pytest`
6. Format code: `black src/`
7. Submit a pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/accessible-pdf-toolkit.git
cd accessible-pdf-toolkit

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run the application
python src/accessible_pdf_toolkit/main.py
```

## Code Style

- Follow PEP 8
- Use Black for formatting (line length 88)
- Use type hints for function signatures
- Write docstrings for public functions
- Keep functions focused and under 50 lines

## Testing

- Write tests for new features
- Maintain or improve code coverage
- Use pytest fixtures for common setup
- Test edge cases and error conditions

## Accessibility Guidelines

Since this is an accessibility tool, our UI must be accessible:

- All widgets must have accessible names
- Keyboard navigation must work everywhere
- Color must not be the only indicator
- Focus indicators must be visible
- Screen reader testing is appreciated

## Questions?

Open a discussion or reach out to maintainers.

Thank you for helping make documents more accessible!
