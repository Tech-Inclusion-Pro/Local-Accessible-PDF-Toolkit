# Installation Guide

## System Requirements

- **Operating System**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **Python**: 3.10 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Disk Space**: 500MB for application, additional space for AI models

## Quick Installation

### Using pip

```bash
# Clone the repository
git clone https://github.com/accessible-pdf-toolkit/accessible-pdf-toolkit.git
cd accessible-pdf-toolkit

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/accessible_pdf_toolkit/main.py
```

### Using Docker

```bash
# Build the image
docker build -t accessible-pdf-toolkit .

# Run the container
docker run -it --rm accessible-pdf-toolkit
```

## Installing Dependencies

### Tesseract OCR

Tesseract is required for OCR functionality.

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt install tesseract-ocr tesseract-ocr-eng
```

**Windows:**
Download the installer from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).

### Local AI Backends

#### Ollama (Recommended)

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a vision model for alt-text generation
ollama pull llava

# Verify installation
ollama list
```

#### LM Studio

1. Download from [lmstudio.ai](https://lmstudio.ai/)
2. Install and launch the application
3. Download a model (e.g., LLaVA for vision)
4. Start the local server

#### GPT4All

GPT4All is included as a Python dependency. Models are downloaded automatically on first use.

## Configuration

After installation, configure your settings:

1. Launch the application
2. Go to Settings tab
3. Select your AI backend
4. Configure connection URLs if needed
5. Save settings

## Troubleshooting

### PyQt6 Issues on Linux

```bash
# Install Qt dependencies
sudo apt install libxcb-xinerama0 libxcb-cursor0
```

### Tesseract Not Found

Ensure Tesseract is in your PATH:

```bash
# Check installation
tesseract --version

# Add to PATH if needed (Linux/macOS)
export PATH="/usr/local/bin:$PATH"
```

### AI Backend Connection Issues

1. Verify the backend is running
2. Check the URL in settings
3. Test connection using the "Test Connection" button

## Updating

```bash
# Pull latest changes
git pull

# Update dependencies
pip install -r requirements.txt --upgrade
```

## Uninstalling

```bash
# Remove virtual environment
rm -rf venv

# Remove application data
rm -rf ~/.accessible-pdf-toolkit
```
