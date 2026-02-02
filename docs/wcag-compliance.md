# WCAG Compliance Guide

## Overview

The Web Content Accessibility Guidelines (WCAG) provide international standards for making content accessible. This guide explains how the Accessible PDF Toolkit helps you meet these standards.

## WCAG Levels

### Level A (Minimum)

Basic accessibility requirements. Documents failing Level A have significant barriers.

### Level AA (Recommended)

Standard compliance level. Required by many laws and policies, including:

- Section 508 (US Federal agencies)
- ADA (Americans with Disabilities Act)
- Many educational institution policies

### Level AAA (Enhanced)

Highest accessibility standard. May not be achievable for all content types.

## Checked Criteria

### 1.1.1 Non-text Content (Level A)

**Requirement**: All images must have text alternatives.

**What we check**:

- Images have alt text
- Alt text is descriptive (not "image" or "picture")
- Decorative images are marked appropriately

**How to fix**:

1. Select the image in Tag Editor
2. Enter descriptive alt text
3. Tag as Figure

### 1.3.1 Info and Relationships (Level A)

**Requirement**: Information and structure must be programmatically determinable.

**What we check**:

- Document is tagged
- Headings are properly marked
- Tables have header cells
- Lists use proper tags

**How to fix**:

1. Run auto-tagging for headings
2. Manually tag tables with TH/TD
3. Tag lists with L/LI

### 1.3.2 Meaningful Sequence (Level A)

**Requirement**: Reading order can be programmatically determined.

**What we check**:

- Document has structure tree
- Reading order matches visual layout

**How to fix**:

1. Ensure PDF is tagged
2. Review reading order in structure
3. Adjust element order if needed

### 1.4.3 Contrast (Minimum) (Level AA)

**Requirement**: Text has sufficient contrast with background.

**What we check**:

- Normal text: 4.5:1 contrast ratio
- Large text: 3:1 contrast ratio

**How to fix**:

- This must be fixed in the source document
- Consider using high contrast theme for HTML export

### 2.4.2 Page Titled (Level A)

**Requirement**: Document has a descriptive title.

**What we check**:

- Title metadata exists
- Title is not the filename

**How to fix**:

1. Auto-fix sets title from filename
2. Edit title in document properties

### 2.4.4 Link Purpose (Level A)

**Requirement**: Link text describes the destination.

**What we check**:

- No "click here" or "read more" links
- Link text is descriptive

**How to fix**:

1. Edit link text to be descriptive
2. Or add context in surrounding text

### 2.4.6 Headings and Labels (Level AA)

**Requirement**: Headings describe content topic.

**What we check**:

- Headings are present
- Heading hierarchy is correct (H1→H2→H3)
- No skipped levels

**How to fix**:

1. Tag content as appropriate heading level
2. Ensure H1 comes before H2
3. Don't skip from H2 to H4

### 3.1.1 Language of Page (Level A)

**Requirement**: Default language is programmatically set.

**What we check**:

- Document language is specified
- Language code is valid (e.g., "en", "es")

**How to fix**:

1. Auto-fix sets language to English
2. Change in settings if different language

### 3.1.2 Language of Parts (Level AA)

**Requirement**: Language changes are marked.

**What we check**:

- Passages in different languages are tagged

**How to fix**:

1. Tag foreign language sections with lang attribute

### 4.1.2 Name, Role, Value (Level A)

**Requirement**: UI components have accessible names.

**What we check**:

- Form fields are labeled
- Interactive elements have names

**How to fix**:

1. Add labels to form fields
2. Ensure buttons have text

## PDF/UA Compliance

PDF/UA (ISO 14289) is the international standard for accessible PDFs. The toolkit helps achieve PDF/UA by:

1. Creating tagged PDF structure
2. Setting document language
3. Adding alt text for images
4. Defining reading order
5. Marking decorative content

## Compliance Scores

The compliance score is calculated as:

```
Score = (Passed Criteria / Total Applicable Criteria) × 100
```

- **90-100%**: Excellent - minimal issues
- **70-89%**: Good - some improvements needed
- **50-69%**: Fair - significant work required
- **Below 50%**: Poor - major accessibility barriers

## Legal Considerations

### FERPA (US)

The Family Educational Rights and Privacy Act requires protecting student information. Using local AI processing (Ollama, GPT4All) keeps data on your machine.

### HIPAA (US)

The Health Insurance Portability and Accountability Act requires protecting patient information. Avoid cloud AI for documents containing PHI.

### ADA (US)

The Americans with Disabilities Act requires accessible content. WCAG 2.0 Level AA is often cited as the standard.

### Section 508 (US Federal)

Requires federal agencies to make electronic content accessible. References WCAG 2.0 Level AA.

## Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [PDF/UA Technical Standard](https://www.pdfa.org/pdfua-the-iso-standard-for-universal-accessibility/)
- [WebAIM WCAG Checklist](https://webaim.org/standards/wcag/checklist)
