# Privacy & Security Guide

## Overview

The Accessible PDF Toolkit is designed with privacy as a core principle. This guide explains how we protect your data and how to configure the application for compliance with privacy regulations.

## Privacy-First Architecture

### Local Processing

All PDF processing happens locally on your machine:

- Document parsing and analysis
- Tag editing and modification
- HTML conversion
- OCR text extraction

### Local AI Options

We support three fully local AI backends:

1. **Ollama**: Runs AI models locally with no external connections
2. **LM Studio**: Local server with OpenAI-compatible API
3. **GPT4All**: Fully embedded, no server required

### No Telemetry

The application does not:

- Send usage statistics
- Track user behavior
- Phone home for updates
- Collect any data

## Data Storage

### Local Database

User data is stored in a local SQLite database:

```
~/.accessible-pdf-toolkit/database.sqlite
```

This includes:

- User accounts (passwords are hashed with bcrypt)
- Course information
- File metadata (not file contents)
- Application settings

### File Storage

PDF files remain in their original locations. The application stores:

- References to file paths
- File hashes for integrity checking
- Compliance status and scores

### Encryption

Sensitive data can be encrypted at rest using AES-256-GCM:

```python
# Enable in Settings → Security → Encrypt Files
```

The encryption key is derived from:

- A machine-specific identifier
- Or a user-provided password

## Compliance Considerations

### FERPA (Family Educational Rights and Privacy Act)

For FERPA compliance when processing student records:

1. **Use local AI only**

   - Ollama, LM Studio, or GPT4All
   - Never use cloud APIs (OpenAI, Anthropic)

2. **Enable encryption**

   - Settings → Security → Encrypt sensitive files

3. **Set auto-logout**

   - Settings → Security → Auto-logout after X minutes

4. **Protect access**
   - Use strong passwords
   - Don't share accounts

### HIPAA (Health Insurance Portability and Accountability Act)

For HIPAA compliance when processing protected health information (PHI):

1. **Use local AI only**

   - Cloud AI is NOT HIPAA compliant without a BAA

2. **Enable encryption**

   - Required for PHI at rest

3. **Maintain access logs**

   - Application logs are stored locally
   - Review `~/.accessible-pdf-toolkit/logs/`

4. **Physical security**

   - Ensure the computer is physically secure
   - Use full-disk encryption on the OS level

5. **Secure deletion**
   - Use secure file deletion when removing PHI
   - Clear temp files regularly

### Section 508 / ADA

These regulations focus on accessibility, not privacy. The toolkit helps achieve compliance by:

- Creating WCAG-compliant documents
- Adding proper PDF tags
- Generating accessible HTML

## Cloud AI Warning

When cloud APIs are selected, the application displays a warning:

> **Privacy Warning**: You are using a cloud AI service. Document content will be sent to external servers. This may not be compliant with FERPA/HIPAA requirements.

Cloud AI should only be used for:

- Non-sensitive documents
- Publicly available content
- Testing purposes

## Security Features

### Password Hashing

User passwords are hashed using bcrypt with:

- 12 rounds of hashing
- Automatic salting
- Timing-attack resistant comparison

### Session Management

- Configurable auto-logout (5-120 minutes)
- Session data stored locally only
- No session tokens sent to external servers

### File Integrity

Files are tracked using SHA-256 hashes to detect:

- Unauthorized modifications
- Corruption
- Version changes

### Encryption Details

When encryption is enabled:

- Algorithm: AES-256-GCM (Fernet)
- Key derivation: PBKDF2-SHA256
- Iterations: 480,000 (OWASP recommended)
- Unique salt per installation

## Best Practices

### For Educators

1. Use local AI for student documents
2. Enable encryption for grade-related PDFs
3. Set reasonable auto-logout times
4. Don't process student data on shared computers

### For Healthcare

1. Never use cloud AI for PHI
2. Enable all security features
3. Use strong, unique passwords
4. Regularly review access logs
5. Follow your organization's IT policies

### For General Use

1. Keep the application updated
2. Use strong passwords
3. Back up your database regularly
4. Review settings after updates

## Data Deletion

### Removing User Data

To completely remove your data:

```bash
# Remove application data directory
rm -rf ~/.accessible-pdf-toolkit

# On Windows
rmdir /s /q %USERPROFILE%\.accessible-pdf-toolkit
```

### Secure Deletion

For sensitive data, use secure deletion tools:

```bash
# Linux/macOS
shred -u ~/.accessible-pdf-toolkit/database.sqlite

# Or use your organization's approved secure deletion method
```

## Reporting Security Issues

If you discover a security vulnerability:

1. Do NOT open a public issue
2. Email security concerns to the maintainers
3. Allow time for a fix before disclosure

## Updates

Security updates are released as needed. Check the repository for:

- Security advisories
- Release notes
- Update instructions

## Audit Trail

The application logs include:

- User login/logout events
- File operations (open, save)
- Validation runs
- Settings changes

Logs are stored locally at:

```
~/.accessible-pdf-toolkit/logs/app.log
```

Log rotation keeps the last 3 files at 5MB each.
