# Changelog

All notable changes to the Accessible PDF Toolkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-02-01

### Changed
- Streamlined interface from 5 tabs to 3 tabs (Dashboard, PDF Viewer, Settings)
- Integrated accessibility fixes directly into PDF Viewer with "Apply" functionality
- Updated keyboard shortcuts: Ctrl+1 (Dashboard), Ctrl+2 (PDF Viewer), Ctrl+3 (Settings)
- Improved AI suggestions panel with direct apply capabilities

### Removed
- Removed standalone Tag Editor tab (functionality merged into PDF Viewer)
- Removed standalone HTML Export tab (accessible via File > Export to HTML)

### Fixed
- Updated documentation to reflect current interface

## [1.0.0] - 2026-02-01

### Added
- Initial release of Accessible PDF Toolkit
- Dashboard with recent files and drag-and-drop support
- PDF Viewer with AI-powered accessibility detection
- Visual overlays showing accessibility issues (headings, images, tables, links)
- AI backend support for Ollama, LM Studio, GPT4All, and more
- Local AI processing for FERPA/HIPAA compliance
- WCAG 2.1/2.2 Level AA validation
- User authentication with encrypted local database
- Dark theme with high-contrast mode option
- HTML export functionality
- OCR support via Tesseract
- Batch processing support (1-10 files)
- Keyboard navigation and accessibility features
- PyInstaller build support for macOS app bundle

### Security
- All processing runs locally - no data sent to external servers
- Encrypted local database for user credentials
- Privacy-first design suitable for sensitive documents

---

## Links

- [Repository](https://github.com/Tech-Inclusion-Pro/Local-Accessible-PDF-Toolkit)
- [Issues](https://github.com/Tech-Inclusion-Pro/Local-Accessible-PDF-Toolkit/issues)
