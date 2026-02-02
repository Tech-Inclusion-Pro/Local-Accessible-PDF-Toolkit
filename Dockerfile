# Accessible PDF Toolkit Dockerfile
# Privacy-first PDF accessibility tool with local AI support

FROM python:3.11-slim-bookworm

LABEL maintainer="Accessible PDF Toolkit Team"
LABEL description="Privacy-first desktop application for making PDFs WCAG 2.1/2.2 compliant"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV QT_QPA_PLATFORM=offscreen
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Qt dependencies
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxkbcommon0 \
    libdbus-1-3 \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libegl1 \
    libfontconfig1 \
    libfreetype6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcb-glx0 \
    libxcb-keysyms1 \
    libxcb-image0 \
    libxcb-shm0 \
    libxcb-icccm4 \
    libxcb-render0 \
    libxcb-render-util0 \
    libxcb-randr0 \
    libxcb-shape0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-xkb1 \
    # OCR dependencies
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    # PDF dependencies
    ghostscript \
    poppler-utils \
    # Build tools
    gcc \
    g++ \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ ./src/
COPY assets/ ./assets/

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Create directories for user data
RUN mkdir -p /app/data /app/output /app/logs

# Set Python path
ENV PYTHONPATH=/app/src

# Expose no ports by default (desktop application)
# For API mode, uncomment: EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import accessible_pdf_toolkit; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "accessible_pdf_toolkit.main"]

# Build instructions:
# docker build -t accessible-pdf-toolkit .
#
# Run with display (Linux):
# docker run -it --rm \
#     -e DISPLAY=$DISPLAY \
#     -v /tmp/.X11-unix:/tmp/.X11-unix \
#     -v $(pwd)/data:/app/data \
#     accessible-pdf-toolkit
#
# Run headless (for batch processing):
# docker run -it --rm \
#     -v $(pwd)/data:/app/data \
#     -v $(pwd)/output:/app/output \
#     accessible-pdf-toolkit python -m accessible_pdf_toolkit.main --batch /app/data
