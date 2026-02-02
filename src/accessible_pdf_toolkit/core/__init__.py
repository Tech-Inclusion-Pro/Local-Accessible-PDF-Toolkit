"""Core processing modules for Accessible PDF Toolkit."""

from .ai_processor import (
    AIProcessor,
    OllamaProcessor,
    LMStudioProcessor,
    GPT4AllProcessor,
    CloudAPIProcessor,
    MistralLocalProcessor,
    LocalAIProcessor,
    LlamaCppProcessor,
    JanProcessor,
    GeminiProcessor,
    MistralAIProcessor,
    CohereProcessor,
    get_ai_processor,
    get_processor_for_provider,
)
from .pdf_handler import PDFHandler
from .ocr_engine import OCREngine
from .wcag_validator import WCAGValidator
from .html_generator import HTMLGenerator
from .ai_detection import (
    AIDetectionService,
    Detection,
    DetectionStatus,
    DocumentAnalysis,
)

__all__ = [
    "AIProcessor",
    "OllamaProcessor",
    "LMStudioProcessor",
    "GPT4AllProcessor",
    "CloudAPIProcessor",
    "MistralLocalProcessor",
    "LocalAIProcessor",
    "LlamaCppProcessor",
    "JanProcessor",
    "GeminiProcessor",
    "MistralAIProcessor",
    "CohereProcessor",
    "get_ai_processor",
    "get_processor_for_provider",
    "PDFHandler",
    "OCREngine",
    "WCAGValidator",
    "HTMLGenerator",
    "AIDetectionService",
    "Detection",
    "DetectionStatus",
    "DocumentAnalysis",
]
