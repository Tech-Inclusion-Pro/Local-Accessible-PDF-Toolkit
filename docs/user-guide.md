# User Guide

## Getting Started

### First Launch

1. Launch the application
2. Create an account or continue without login
3. The Dashboard will open as the main screen

### Interface Overview

The application has four main tabs:

- **Dashboard**: Manage files and courses, view statistics
- **Tag Editor**: Edit PDF accessibility tags
- **HTML Export**: Convert PDFs to accessible HTML
- **Settings**: Configure application preferences

## Dashboard

### Managing Courses

Courses help organize your PDF files by class or project.

1. Click the **+** button next to "Courses"
2. Enter course code (e.g., "CS101")
3. Enter course name
4. Optionally add semester
5. Click OK

### Importing Files

1. Click **Import PDF** button
2. Select one or more PDF files
3. Files are added to the current course (or "All Courses" if none selected)

### Filtering Files

- **Search**: Type in the search box to filter by filename
- **Status Filter**: Filter by compliance status
- **Course Filter**: Show files from a specific course

### File Statistics

The dashboard shows:

- Total number of files
- Number of compliant files
- Files needing work
- Average compliance score

## Tag Editor

### Opening a File

1. Click **Open PDF** or double-click a file in Dashboard
2. The PDF preview appears on the left
3. The tag tree appears in the center

### Understanding the Tag Tree

Each element shows:

- **Tag**: Current accessibility tag (or "Untagged")
- **Content**: Text preview
- **Page**: Page number

Colors indicate status:

- Green: Properly tagged
- Yellow: Tagged but may need alt text
- Red: Untagged

### Editing Tags

1. Select an element in the tree
2. Choose a tag type from the dropdown
3. Click **Apply**

For images:

1. Select the image element
2. Enter alt text in the "Alt Text" field
3. Choose "Figure" as the tag type
4. Click Apply

### Auto-Tagging

Click **Auto-Tag Headings** to automatically detect and tag headings based on font size.

### Validation

1. Click **Validate** in the right panel
2. View the compliance score and issues
3. Click **Auto-Fix Issues** to fix common problems

### AI Suggestions

1. Click **AI Suggestions**
2. Review AI-generated recommendations
3. Apply suggestions as needed

## HTML Export

### Basic Conversion

1. Open a PDF in the HTML Converter tab
2. Select theme and options
3. Click **Convert to HTML**
4. Preview the result
5. Click **Save HTML** to export

### Theme Options

- **Brand**: Default blue/green theme
- **High Contrast**: Black/white for accessibility
- **Dark Mode**: Dark background

### Content Options

- **Include CSS Styles**: Embed styles in HTML
- **Include Table of Contents**: Add navigation TOC
- **Include Images**: Export images with alt text
- **Embed Images**: Include as base64 (larger file, self-contained)
- **Responsive Layout**: Mobile-friendly design
- **Page Dividers**: Add visual page breaks
- **Add ARIA Attributes**: Enhanced screen reader support

### Section Extraction

To export only part of a document:

1. Enter the start heading text
2. Optionally enter the end heading text
3. Convert as normal

## Settings

### AI Backend

Choose from:

- **Ollama**: Local, privacy-preserving (recommended)
- **LM Studio**: Local, OpenAI-compatible
- **GPT4All**: Fully local, no server needed
- **Cloud APIs**: OpenAI/Anthropic (privacy warning)

### Processing

- **Batch Limit**: 1-10 PDFs at once
- **Auto OCR**: Enable for scanned documents
- **Preserve Originals**: Keep backup copies

### Accessibility

- **WCAG Level**: A, AA (recommended), or AAA
- **Validation Checks**: Enable/disable specific checks

### Interface

- **Theme**: Light, dark, or system
- **High Contrast**: Accessibility mode
- **Font Size**: 8-24 points

### Security

- **Encrypt Files**: Protect sensitive documents
- **Auto Logout**: Session timeout
- **Change Password**: Update credentials

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Open File | Ctrl+O |
| Save | Ctrl+S |
| Export HTML | Ctrl+E |
| Validate | Ctrl+Shift+V |
| AI Suggest | Ctrl+Space |
| Dashboard | Ctrl+1 |
| Tag Editor | Ctrl+2 |
| HTML Export | Ctrl+3 |
| Settings | Ctrl+4 |

## Tips

1. **Start with validation** to understand current accessibility status
2. **Use auto-tagging** for a quick start, then refine manually
3. **Test with screen readers** to verify accessibility
4. **Keep originals** until you've verified the results
5. **Use local AI** for FERPA/HIPAA compliance
