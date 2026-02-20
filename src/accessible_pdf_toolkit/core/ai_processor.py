"""
AI processor module with support for multiple local and cloud AI backends.
"""

import base64
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

import httpx

from ..utils.constants import AIBackend, LocalAIProvider, CloudAIProvider, DEFAULT_CONFIG
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AIResponse:
    """Structured response from AI processing."""

    success: bool
    content: str
    model: str
    backend: AIBackend
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AIProcessor(ABC):
    """Abstract base class for AI processors."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the AI processor.

        Args:
            config: Configuration dictionary
        """
        self.config = config or DEFAULT_CONFIG.get("ai", {})
        self.timeout = self.config.get("timeout", 60)

    @property
    @abstractmethod
    def backend(self) -> AIBackend:
        """Get the backend type."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is available."""
        pass

    @abstractmethod
    def analyze_structure(self, text: str) -> AIResponse:
        """
        Analyze document structure for accessibility.

        Args:
            text: Document text content

        Returns:
            AIResponse with structure analysis
        """
        pass

    @abstractmethod
    def generate_alt_text(self, image_bytes: bytes, context: str = "") -> AIResponse:
        """
        Generate alt text for an image.

        Args:
            image_bytes: Image data
            context: Surrounding text context

        Returns:
            AIResponse with generated alt text
        """
        pass

    @abstractmethod
    def suggest_headings(self, text: str) -> AIResponse:
        """
        Suggest heading structure for text.

        Args:
            text: Document text content

        Returns:
            AIResponse with heading suggestions
        """
        pass

    def improve_reading_order(self, elements: List[Dict]) -> AIResponse:
        """
        Suggest improvements to reading order.

        Args:
            elements: List of document elements with positions

        Returns:
            AIResponse with reading order suggestions
        """
        # Default implementation - can be overridden
        return AIResponse(
            success=False,
            content="",
            model="",
            backend=self.backend,
            error="Not implemented for this backend",
        )

    def check_link_text(self, links: List[Dict]) -> AIResponse:
        """
        Check and suggest improvements for link text.

        Args:
            links: List of links with text and URLs

        Returns:
            AIResponse with link text suggestions
        """
        # Default implementation
        return AIResponse(
            success=False,
            content="",
            model="",
            backend=self.backend,
            error="Not implemented for this backend",
        )

    def correct_heading_outline(self, text: str, current_headings: List[Dict]) -> AIResponse:
        """Fix skipped heading levels and mis-leveled headings."""
        return AIResponse(
            success=False, content="", model="",
            backend=self.backend, error="Not implemented for this backend",
        )

    def rewrite_link_text(self, links: List[Dict]) -> AIResponse:
        """Rewrite generic link text to descriptive text."""
        return AIResponse(
            success=False, content="", model="",
            backend=self.backend, error="Not implemented for this backend",
        )

    def suggest_contrast_fixes(self, elements: List[Dict]) -> AIResponse:
        """Recommend replacement colors for low-contrast elements."""
        return AIResponse(
            success=False, content="", model="",
            backend=self.backend, error="Not implemented for this backend",
        )

    def suggest_document_metadata(self, text: str) -> AIResponse:
        """Suggest title, language, and subject for the document."""
        return AIResponse(
            success=False, content="", model="",
            backend=self.backend, error="Not implemented for this backend",
        )

    def generate_graph_description(self, image_bytes: bytes, context: str = "") -> AIResponse:
        """Generate long-form chart/graph description."""
        return AIResponse(
            success=False, content="", model="",
            backend=self.backend, error="Not implemented for this backend",
        )

    def generate_form_labels(self, form_fields: List[Dict]) -> AIResponse:
        """Generate labels and tooltips for form fields."""
        return AIResponse(
            success=False, content="", model="",
            backend=self.backend, error="Not implemented for this backend",
        )

    def draft_captions_footnotes(self, elements: List[Dict]) -> AIResponse:
        """Draft captions for figures and footnote text."""
        return AIResponse(
            success=False, content="", model="",
            backend=self.backend, error="Not implemented for this backend",
        )

    def suggest_non_color_cues(self, elements: List[Dict]) -> AIResponse:
        """Suggest text labels, icons, or patterns for color-only information."""
        return AIResponse(
            success=False, content="", model="",
            backend=self.backend, error="Not implemented for this backend",
        )

    def review_ocr_accuracy(self, ocr_text: str, image_bytes: bytes) -> AIResponse:
        """Flag likely OCR errors in specialized terminology."""
        return AIResponse(
            success=False, content="", model="",
            backend=self.backend, error="Not implemented for this backend",
        )

    def generate_bookmark_structure(self, text: str, headings: List[Dict]) -> AIResponse:
        """Build bookmark hierarchy from headings."""
        return AIResponse(
            success=False, content="", model="",
            backend=self.backend, error="Not implemented for this backend",
        )

    def generate_math_alt_text(self, formula_image: bytes, context: str = "") -> AIResponse:
        """Generate spoken-math description of equations."""
        return AIResponse(
            success=False, content="", model="",
            backend=self.backend, error="Not implemented for this backend",
        )


class OllamaProcessor(AIProcessor):
    """Ollama local AI processor."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = self.config.get("ollama_url", "http://localhost:11434")
        self.model = self.config.get("default_model", "llava")
        self._client = httpx.Client(timeout=self.timeout)

    @property
    def backend(self) -> AIBackend:
        return AIBackend.OLLAMA

    @property
    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = self._client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    def _generate(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        system: Optional[str] = None,
    ) -> AIResponse:
        """
        Generate a response from Ollama.

        Args:
            prompt: User prompt
            images: List of base64-encoded images
            system: System prompt

        Returns:
            AIResponse
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }

            if images:
                payload["images"] = images

            if system:
                payload["system"] = system

            response = self._client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            return AIResponse(
                success=True,
                content=data.get("response", ""),
                model=self.model,
                backend=self.backend,
                metadata={"eval_count": data.get("eval_count")},
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e}")
            return AIResponse(
                success=False,
                content="",
                model=self.model,
                backend=self.backend,
                error=f"HTTP error: {e.response.status_code}",
            )
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return AIResponse(
                success=False,
                content="",
                model=self.model,
                backend=self.backend,
                error=str(e),
            )

    def analyze_structure(self, text: str) -> AIResponse:
        """Analyze document structure."""
        system = """You are an accessibility expert analyzing PDF documents.
Identify the document structure including:
- Main sections and their hierarchy
- Headings and their levels
- Lists and tables
- Images and figures that need alt text
Respond in JSON format."""

        prompt = f"""Analyze this document text and identify its structure for accessibility:

{text[:4000]}

Provide a JSON response with:
{{
    "title": "detected title",
    "sections": [
        {{"heading": "text", "level": 1, "start_index": 0}}
    ],
    "lists": [...],
    "tables": [...],
    "images_needing_alt": [...]
}}"""

        return self._generate(prompt, system=system)

    def generate_alt_text(self, image_bytes: bytes, context: str = "") -> AIResponse:
        """Generate alt text for an image."""
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        system = """You are an accessibility expert creating alt text for images.
Create concise, descriptive alt text that:
- Describes the image content accurately
- Is useful for screen reader users
- Avoids phrases like "image of" or "picture of"
- Is under 125 characters when possible"""

        prompt = f"""Create alt text for this image.
Context from surrounding text: {context[:500] if context else 'No context available'}

Respond with ONLY the alt text, no explanation."""

        return self._generate(prompt, images=[image_b64], system=system)

    def suggest_headings(self, text: str) -> AIResponse:
        """Suggest heading structure."""
        system = """You are an accessibility expert improving document structure.
Suggest a heading hierarchy that:
- Uses proper nesting (H1 -> H2 -> H3)
- Never skips levels
- Makes the document navigable
- Helps screen reader users understand the structure"""

        prompt = f"""Analyze this text and suggest a heading structure:

{text[:4000]}

Respond in JSON format:
{{
    "suggested_headings": [
        {{"text": "heading text", "level": 1, "position": "start/after paragraph X"}}
    ],
    "issues": ["list of current heading problems"],
    "recommendations": ["list of improvements"]
}}"""

        return self._generate(prompt, system=system)

    def correct_heading_outline(self, text: str, current_headings: List[Dict]) -> AIResponse:
        """Fix skipped heading levels and mis-leveled headings."""
        system = (
            "You are an accessibility expert. Given document text and its current heading outline, "
            "produce a corrected outline where no heading level is skipped (H1→H2→H3, never H1→H3). "
            "Respond in JSON: [{\"text\": \"...\", \"current_level\": N, \"suggested_level\": M}]"
        )
        headings_str = json.dumps(current_headings[:50])
        prompt = f"Text (first 4000 chars):\n{text[:4000]}\n\nCurrent headings:\n{headings_str}"
        return self._generate(prompt, system=system)

    def rewrite_link_text(self, links: List[Dict]) -> AIResponse:
        """Rewrite generic link text to descriptive text."""
        system = (
            "You are an accessibility expert. Rewrite generic link text (like 'click here', 'read more') "
            "into descriptive text that conveys the link's purpose. "
            "Respond in JSON: [{\"original\": \"...\", \"url\": \"...\", \"rewritten\": \"...\"}]"
        )
        prompt = f"Links to rewrite:\n{json.dumps(links[:30])}"
        return self._generate(prompt, system=system)

    def suggest_contrast_fixes(self, elements: List[Dict]) -> AIResponse:
        """Recommend replacement colors for low-contrast elements."""
        system = (
            "You are an accessibility expert and color designer. For each low-contrast element, "
            "suggest a replacement foreground color that meets WCAG AA (4.5:1) against the given background. "
            "Respond in JSON: [{\"original_fg\": \"#...\", \"bg\": \"#...\", \"suggested_fg\": \"#...\", \"new_ratio\": N.N}]"
        )
        prompt = f"Low-contrast elements:\n{json.dumps(elements[:20])}"
        return self._generate(prompt, system=system)

    def suggest_document_metadata(self, text: str) -> AIResponse:
        """Suggest title, language, and subject for the document."""
        system = (
            "You are an accessibility expert. From the document text, suggest: "
            "1) A descriptive document title, 2) The primary language (BCP 47 code), "
            "3) A brief subject description. "
            "Respond in JSON: {\"title\": \"...\", \"language\": \"...\", \"subject\": \"...\"}"
        )
        prompt = f"Document text (first 4000 chars):\n{text[:4000]}"
        return self._generate(prompt, system=system)

    def generate_graph_description(self, image_bytes: bytes, context: str = "") -> AIResponse:
        """Generate long-form chart/graph description."""
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        system = (
            "You are an accessibility expert creating long descriptions for charts and graphs. "
            "Describe the chart type, axes, data trends, key values, and conclusions. "
            "Write 2-4 sentences suitable as a long description for screen reader users."
        )
        prompt = f"Describe this chart/graph in detail.\nContext: {context[:500] if context else 'No context'}"
        return self._generate(prompt, images=[image_b64], system=system)

    def generate_form_labels(self, form_fields: List[Dict]) -> AIResponse:
        """Generate labels and tooltips for form fields."""
        system = (
            "You are an accessibility expert. For each unlabelled form field, suggest "
            "a visible label and a tooltip/title attribute. "
            "Respond in JSON: [{\"field_id\": \"...\", \"label\": \"...\", \"tooltip\": \"...\"}]"
        )
        prompt = f"Form fields needing labels:\n{json.dumps(form_fields[:30])}"
        return self._generate(prompt, system=system)

    def draft_captions_footnotes(self, elements: List[Dict]) -> AIResponse:
        """Draft captions for figures and footnote text."""
        system = (
            "You are an accessibility expert. Draft concise captions for figures "
            "and footnote text for referenced items. "
            "Respond in JSON: [{\"element\": \"...\", \"caption\": \"...\"}]"
        )
        prompt = f"Elements needing captions:\n{json.dumps(elements[:20])}"
        return self._generate(prompt, system=system)

    def suggest_non_color_cues(self, elements: List[Dict]) -> AIResponse:
        """Suggest text labels, icons, or patterns for color-only information."""
        system = (
            "You are an accessibility expert. For each element that uses color alone to convey information, "
            "suggest an additional non-color cue (text label, icon, pattern, or shape). "
            "Respond in JSON: [{\"element\": \"...\", \"current_cue\": \"color only\", \"suggested_cue\": \"...\"}]"
        )
        prompt = f"Elements using color-only cues:\n{json.dumps(elements[:20])}"
        return self._generate(prompt, system=system)

    def review_ocr_accuracy(self, ocr_text: str, image_bytes: bytes) -> AIResponse:
        """Flag likely OCR errors in specialized terminology."""
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        system = (
            "You are a proofreading expert. Compare the OCR text against the image and flag "
            "likely misrecognitions, especially in technical terms, proper nouns, and numbers. "
            "Respond in JSON: [{\"original\": \"...\", \"likely_correct\": \"...\", \"confidence\": \"high/medium/low\"}]"
        )
        prompt = f"OCR text to review:\n{ocr_text[:3000]}"
        return self._generate(prompt, images=[image_b64], system=system)

    def generate_bookmark_structure(self, text: str, headings: List[Dict]) -> AIResponse:
        """Build bookmark hierarchy from headings."""
        system = (
            "You are an accessibility expert. From the heading list, produce a bookmark hierarchy. "
            "Respond in JSON: [{\"title\": \"...\", \"level\": N, \"page\": N}]"
        )
        headings_str = json.dumps(headings[:50])
        prompt = f"Headings:\n{headings_str}\n\nDocument text (first 2000 chars):\n{text[:2000]}"
        return self._generate(prompt, system=system)

    def generate_math_alt_text(self, formula_image: bytes, context: str = "") -> AIResponse:
        """Generate spoken-math description of equations."""
        image_b64 = base64.b64encode(formula_image).decode("utf-8")
        system = (
            "You are a math accessibility expert. Describe this mathematical formula "
            "in spoken-math format suitable for screen readers. Use natural language, "
            "e.g., 'x squared plus 2 x plus 1 equals open parenthesis x plus 1 close parenthesis squared'. "
            "Respond with ONLY the spoken description."
        )
        prompt = f"Describe this formula for a screen reader.\nContext: {context[:300] if context else 'No context'}"
        return self._generate(prompt, images=[image_b64], system=system)


class LMStudioProcessor(AIProcessor):
    """LM Studio local AI processor (OpenAI-compatible API)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = self.config.get("lmstudio_url", "http://localhost:1234")
        self.model = self.config.get("default_model", "local-model")
        self._client = httpx.Client(timeout=self.timeout)

    @property
    def backend(self) -> AIBackend:
        return AIBackend.LM_STUDIO

    @property
    def is_available(self) -> bool:
        """Check if LM Studio server is running."""
        try:
            response = self._client.get(f"{self.base_url}/v1/models")
            return response.status_code == 200
        except Exception:
            return False

    def _chat_completion(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 2000,
    ) -> AIResponse:
        """
        Send a chat completion request.

        Args:
            messages: Chat messages
            max_tokens: Maximum response tokens

        Returns:
            AIResponse
        """
        try:
            response = self._client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            return AIResponse(
                success=True,
                content=content,
                model=self.model,
                backend=self.backend,
                metadata={"usage": data.get("usage")},
            )

        except Exception as e:
            logger.error(f"LM Studio error: {e}")
            return AIResponse(
                success=False,
                content="",
                model=self.model,
                backend=self.backend,
                error=str(e),
            )

    def analyze_structure(self, text: str) -> AIResponse:
        """Analyze document structure."""
        messages = [
            {
                "role": "system",
                "content": "You are an accessibility expert. Analyze document structure and respond in JSON format.",
            },
            {
                "role": "user",
                "content": f"Analyze this document structure:\n\n{text[:4000]}",
            },
        ]
        return self._chat_completion(messages)

    def generate_alt_text(self, image_bytes: bytes, context: str = "") -> AIResponse:
        """Generate alt text for an image."""
        # LM Studio may not support vision - check model capabilities
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        messages = [
            {
                "role": "system",
                "content": "Create concise alt text for images. Respond with only the alt text.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Create alt text for this image. Context: {context[:500]}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                ],
            },
        ]
        return self._chat_completion(messages)

    def suggest_headings(self, text: str) -> AIResponse:
        """Suggest heading structure."""
        messages = [
            {
                "role": "system",
                "content": "You are an accessibility expert. Suggest heading structure in JSON format.",
            },
            {
                "role": "user",
                "content": f"Suggest headings for this document:\n\n{text[:4000]}",
            },
        ]
        return self._chat_completion(messages)


class GPT4AllProcessor(AIProcessor):
    """GPT4All local AI processor."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.model_name = self.config.get("gpt4all_model", "orca-mini-3b-gguf2-q4_0.gguf")
        self._model = None

    @property
    def backend(self) -> AIBackend:
        return AIBackend.GPT4ALL

    @property
    def is_available(self) -> bool:
        """Check if GPT4All is available."""
        try:
            import gpt4all
            return True
        except ImportError:
            return False

    def _get_model(self):
        """Get or initialize the GPT4All model."""
        if self._model is None:
            try:
                from gpt4all import GPT4All
                self._model = GPT4All(self.model_name)
            except Exception as e:
                logger.error(f"Failed to load GPT4All model: {e}")
                raise
        return self._model

    def _generate(self, prompt: str, max_tokens: int = 1000) -> AIResponse:
        """Generate a response from GPT4All."""
        try:
            model = self._get_model()
            response = model.generate(prompt, max_tokens=max_tokens)

            return AIResponse(
                success=True,
                content=response,
                model=self.model_name,
                backend=self.backend,
            )

        except Exception as e:
            logger.error(f"GPT4All error: {e}")
            return AIResponse(
                success=False,
                content="",
                model=self.model_name,
                backend=self.backend,
                error=str(e),
            )

    def analyze_structure(self, text: str) -> AIResponse:
        """Analyze document structure."""
        prompt = f"""Analyze this document and identify its structure (headings, sections, lists).
Respond in JSON format.

Document:
{text[:3000]}

Structure analysis:"""
        return self._generate(prompt)

    def generate_alt_text(self, image_bytes: bytes, context: str = "") -> AIResponse:
        """Generate alt text - GPT4All doesn't support vision."""
        return AIResponse(
            success=False,
            content="",
            model=self.model_name,
            backend=self.backend,
            error="GPT4All does not support image analysis. Use Ollama with LLaVA for alt text generation.",
        )

    def suggest_headings(self, text: str) -> AIResponse:
        """Suggest heading structure."""
        prompt = f"""Analyze this text and suggest a heading structure for accessibility.
Use proper hierarchy (H1, H2, H3) without skipping levels.

Text:
{text[:3000]}

Suggested headings (JSON format):"""
        return self._generate(prompt)


class CloudAPIProcessor(AIProcessor):
    """Cloud API processor (OpenAI/Anthropic) with privacy warnings."""

    PRIVACY_WARNING = """
WARNING: You are using a cloud AI service.
- Document content will be sent to external servers
- This may not be compliant with FERPA/HIPAA requirements
- Consider using local AI (Ollama, LM Studio, GPT4All) for sensitive documents
"""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        provider: str = "openai",
    ):
        super().__init__(config)
        self.api_key = api_key
        self.provider = provider
        self._warned = False

        if provider == "openai":
            self.base_url = "https://api.openai.com/v1"
            self.model = "gpt-4-vision-preview"
        elif provider == "anthropic":
            self.base_url = "https://api.anthropic.com/v1"
            self.model = "claude-3-opus-20240229"
        else:
            raise ValueError(f"Unknown provider: {provider}")

        self._client = httpx.Client(timeout=self.timeout)

    @property
    def backend(self) -> AIBackend:
        if self.provider == "openai":
            return AIBackend.OPENAI
        return AIBackend.ANTHROPIC

    @property
    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    def _warn_privacy(self) -> None:
        """Log privacy warning once."""
        if not self._warned:
            logger.warning(self.PRIVACY_WARNING)
            self._warned = True

    def _openai_request(self, messages: List[Dict], max_tokens: int = 2000) -> AIResponse:
        """Send request to OpenAI API."""
        self._warn_privacy()

        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            return AIResponse(
                success=True,
                content=content,
                model=self.model,
                backend=self.backend,
                metadata={"usage": data.get("usage")},
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return AIResponse(
                success=False,
                content="",
                model=self.model,
                backend=self.backend,
                error=str(e),
            )

    def _anthropic_request(self, messages: List[Dict], max_tokens: int = 2000) -> AIResponse:
        """Send request to Anthropic API."""
        self._warn_privacy()

        try:
            response = self._client.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": messages,
                },
            )
            response.raise_for_status()

            data = response.json()
            content = data["content"][0]["text"]

            return AIResponse(
                success=True,
                content=content,
                model=self.model,
                backend=self.backend,
                metadata={"usage": data.get("usage")},
            )

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return AIResponse(
                success=False,
                content="",
                model=self.model,
                backend=self.backend,
                error=str(e),
            )

    def analyze_structure(self, text: str) -> AIResponse:
        """Analyze document structure."""
        messages = [
            {
                "role": "user",
                "content": f"Analyze this document structure for accessibility. Respond in JSON:\n\n{text[:4000]}",
            }
        ]

        if self.provider == "openai":
            return self._openai_request(messages)
        return self._anthropic_request(messages)

    def generate_alt_text(self, image_bytes: bytes, context: str = "") -> AIResponse:
        """Generate alt text for an image."""
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        if self.provider == "openai":
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Create alt text for this image. Context: {context[:500]}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                    ],
                }
            ]
            return self._openai_request(messages)
        else:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Create alt text for this image. Context: {context[:500]}"},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
                    ],
                }
            ]
            return self._anthropic_request(messages)

    def suggest_headings(self, text: str) -> AIResponse:
        """Suggest heading structure."""
        messages = [
            {
                "role": "user",
                "content": f"Suggest accessible heading structure for this document. Respond in JSON:\n\n{text[:4000]}",
            }
        ]

        if self.provider == "openai":
            return self._openai_request(messages)
        return self._anthropic_request(messages)


class MistralLocalProcessor(AIProcessor):
    """Mistral local server processor."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = self.config.get("mistral_local_url", "http://localhost:8080")
        self.model = self.config.get("default_model", "mistral")
        self._client = httpx.Client(timeout=self.timeout)

    @property
    def backend(self) -> AIBackend:
        return AIBackend.OLLAMA  # Use Ollama enum for compatibility

    @property
    def is_available(self) -> bool:
        try:
            response = self._client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False

    def _chat(self, messages: List[Dict], max_tokens: int = 2000) -> AIResponse:
        try:
            response = self._client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return AIResponse(
                success=True,
                content=data["choices"][0]["message"]["content"],
                model=self.model,
                backend=self.backend,
            )
        except Exception as e:
            return AIResponse(
                success=False, content="", model=self.model,
                backend=self.backend, error=str(e),
            )

    def analyze_structure(self, text: str) -> AIResponse:
        messages = [{"role": "user", "content": f"Analyze document structure:\n{text[:4000]}"}]
        return self._chat(messages)

    def generate_alt_text(self, image_bytes: bytes, context: str = "") -> AIResponse:
        return AIResponse(
            success=False, content="", model=self.model, backend=self.backend,
            error="Mistral local doesn't support vision",
        )

    def suggest_headings(self, text: str) -> AIResponse:
        messages = [{"role": "user", "content": f"Suggest headings:\n{text[:4000]}"}]
        return self._chat(messages)


class LocalAIProcessor(AIProcessor):
    """LocalAI processor (OpenAI-compatible local API)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = self.config.get("localai_url", "http://localhost:8080")
        self.model = self.config.get("default_model", "gpt-3.5-turbo")
        self._client = httpx.Client(timeout=self.timeout)

    @property
    def backend(self) -> AIBackend:
        return AIBackend.LM_STUDIO  # Use compatible enum

    @property
    def is_available(self) -> bool:
        try:
            response = self._client.get(f"{self.base_url}/v1/models")
            return response.status_code == 200
        except Exception:
            return False

    def _chat(self, messages: List[Dict], max_tokens: int = 2000) -> AIResponse:
        try:
            response = self._client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return AIResponse(
                success=True,
                content=data["choices"][0]["message"]["content"],
                model=self.model,
                backend=self.backend,
            )
        except Exception as e:
            return AIResponse(
                success=False, content="", model=self.model,
                backend=self.backend, error=str(e),
            )

    def analyze_structure(self, text: str) -> AIResponse:
        messages = [
            {"role": "system", "content": "Analyze document structure for accessibility."},
            {"role": "user", "content": text[:4000]},
        ]
        return self._chat(messages)

    def generate_alt_text(self, image_bytes: bytes, context: str = "") -> AIResponse:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": f"Create alt text. Context: {context[:500]}"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
            ]},
        ]
        return self._chat(messages)

    def suggest_headings(self, text: str) -> AIResponse:
        messages = [
            {"role": "system", "content": "Suggest heading structure in JSON format."},
            {"role": "user", "content": text[:4000]},
        ]
        return self._chat(messages)


class LlamaCppProcessor(AIProcessor):
    """Llama.cpp HTTP server processor."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = self.config.get("llama_cpp_url", "http://localhost:8080")
        self.model = "llama"
        self._client = httpx.Client(timeout=self.timeout)

    @property
    def backend(self) -> AIBackend:
        return AIBackend.OLLAMA

    @property
    def is_available(self) -> bool:
        try:
            response = self._client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False

    def _generate(self, prompt: str, max_tokens: int = 1000) -> AIResponse:
        try:
            response = self._client.post(
                f"{self.base_url}/completion",
                json={"prompt": prompt, "n_predict": max_tokens},
            )
            response.raise_for_status()
            data = response.json()
            return AIResponse(
                success=True,
                content=data.get("content", ""),
                model=self.model,
                backend=self.backend,
            )
        except Exception as e:
            return AIResponse(
                success=False, content="", model=self.model,
                backend=self.backend, error=str(e),
            )

    def analyze_structure(self, text: str) -> AIResponse:
        return self._generate(f"Analyze document structure:\n{text[:3000]}")

    def generate_alt_text(self, image_bytes: bytes, context: str = "") -> AIResponse:
        return AIResponse(
            success=False, content="", model=self.model, backend=self.backend,
            error="Llama.cpp server doesn't support vision by default",
        )

    def suggest_headings(self, text: str) -> AIResponse:
        return self._generate(f"Suggest headings for:\n{text[:3000]}")


class JanProcessor(AIProcessor):
    """Jan AI processor."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = self.config.get("jan_url", "http://localhost:1337")
        self.model = self.config.get("default_model", "tinyllama-1.1b")
        self._client = httpx.Client(timeout=self.timeout)

    @property
    def backend(self) -> AIBackend:
        return AIBackend.LM_STUDIO

    @property
    def is_available(self) -> bool:
        try:
            response = self._client.get(f"{self.base_url}/v1/models")
            return response.status_code == 200
        except Exception:
            return False

    def _chat(self, messages: List[Dict], max_tokens: int = 2000) -> AIResponse:
        try:
            response = self._client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return AIResponse(
                success=True,
                content=data["choices"][0]["message"]["content"],
                model=self.model,
                backend=self.backend,
            )
        except Exception as e:
            return AIResponse(
                success=False, content="", model=self.model,
                backend=self.backend, error=str(e),
            )

    def analyze_structure(self, text: str) -> AIResponse:
        messages = [{"role": "user", "content": f"Analyze structure:\n{text[:4000]}"}]
        return self._chat(messages)

    def generate_alt_text(self, image_bytes: bytes, context: str = "") -> AIResponse:
        return AIResponse(
            success=False, content="", model=self.model, backend=self.backend,
            error="Jan doesn't support vision models",
        )

    def suggest_headings(self, text: str) -> AIResponse:
        messages = [{"role": "user", "content": f"Suggest headings:\n{text[:4000]}"}]
        return self._chat(messages)


class GeminiProcessor(AIProcessor):
    """Google Gemini API processor."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, api_key: Optional[str] = None):
        super().__init__(config)
        self.api_key = api_key or config.get("gemini_api_key")
        self.model = config.get("default_model", "gemini-1.5-pro")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self._client = httpx.Client(timeout=self.timeout)
        self._warned = False

    @property
    def backend(self) -> AIBackend:
        return AIBackend.OPENAI  # Use for cloud compatibility

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def _warn_privacy(self) -> None:
        if not self._warned:
            logger.warning("Using Google Gemini - data sent to Google servers")
            self._warned = True

    def _generate(self, contents: List[Dict], max_tokens: int = 2000) -> AIResponse:
        self._warn_privacy()
        try:
            response = self._client.post(
                f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}",
                json={
                    "contents": contents,
                    "generationConfig": {"maxOutputTokens": max_tokens},
                },
            )
            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return AIResponse(
                success=True, content=text, model=self.model, backend=self.backend,
            )
        except Exception as e:
            return AIResponse(
                success=False, content="", model=self.model,
                backend=self.backend, error=str(e),
            )

    def analyze_structure(self, text: str) -> AIResponse:
        contents = [{"parts": [{"text": f"Analyze document structure:\n{text[:4000]}"}]}]
        return self._generate(contents)

    def generate_alt_text(self, image_bytes: bytes, context: str = "") -> AIResponse:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        contents = [{
            "parts": [
                {"text": f"Create alt text. Context: {context[:500]}"},
                {"inline_data": {"mime_type": "image/png", "data": image_b64}},
            ]
        }]
        return self._generate(contents)

    def suggest_headings(self, text: str) -> AIResponse:
        contents = [{"parts": [{"text": f"Suggest headings:\n{text[:4000]}"}]}]
        return self._generate(contents)


class MistralAIProcessor(AIProcessor):
    """Mistral AI cloud processor."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, api_key: Optional[str] = None):
        super().__init__(config)
        self.api_key = api_key or config.get("mistral_api_key")
        self.model = config.get("default_model", "mistral-large-latest")
        self.base_url = "https://api.mistral.ai/v1"
        self._client = httpx.Client(timeout=self.timeout)
        self._warned = False

    @property
    def backend(self) -> AIBackend:
        return AIBackend.OPENAI

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def _warn_privacy(self) -> None:
        if not self._warned:
            logger.warning("Using Mistral AI - data sent to Mistral servers")
            self._warned = True

    def _chat(self, messages: List[Dict], max_tokens: int = 2000) -> AIResponse:
        self._warn_privacy()
        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return AIResponse(
                success=True,
                content=data["choices"][0]["message"]["content"],
                model=self.model,
                backend=self.backend,
            )
        except Exception as e:
            return AIResponse(
                success=False, content="", model=self.model,
                backend=self.backend, error=str(e),
            )

    def analyze_structure(self, text: str) -> AIResponse:
        messages = [{"role": "user", "content": f"Analyze structure:\n{text[:4000]}"}]
        return self._chat(messages)

    def generate_alt_text(self, image_bytes: bytes, context: str = "") -> AIResponse:
        return AIResponse(
            success=False, content="", model=self.model, backend=self.backend,
            error="Mistral AI doesn't support vision yet",
        )

    def suggest_headings(self, text: str) -> AIResponse:
        messages = [{"role": "user", "content": f"Suggest headings:\n{text[:4000]}"}]
        return self._chat(messages)


class CohereProcessor(AIProcessor):
    """Cohere API processor."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, api_key: Optional[str] = None):
        super().__init__(config)
        self.api_key = api_key or config.get("cohere_api_key")
        self.model = config.get("default_model", "command-r-plus")
        self.base_url = "https://api.cohere.ai/v1"
        self._client = httpx.Client(timeout=self.timeout)
        self._warned = False

    @property
    def backend(self) -> AIBackend:
        return AIBackend.OPENAI

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def _warn_privacy(self) -> None:
        if not self._warned:
            logger.warning("Using Cohere - data sent to Cohere servers")
            self._warned = True

    def _chat(self, message: str, max_tokens: int = 2000) -> AIResponse:
        self._warn_privacy()
        try:
            response = self._client.post(
                f"{self.base_url}/chat",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "message": message,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return AIResponse(
                success=True,
                content=data.get("text", ""),
                model=self.model,
                backend=self.backend,
            )
        except Exception as e:
            return AIResponse(
                success=False, content="", model=self.model,
                backend=self.backend, error=str(e),
            )

    def analyze_structure(self, text: str) -> AIResponse:
        return self._chat(f"Analyze document structure:\n{text[:4000]}")

    def generate_alt_text(self, image_bytes: bytes, context: str = "") -> AIResponse:
        return AIResponse(
            success=False, content="", model=self.model, backend=self.backend,
            error="Cohere doesn't support vision",
        )

    def suggest_headings(self, text: str) -> AIResponse:
        return self._chat(f"Suggest headings:\n{text[:4000]}")


def get_ai_processor(
    backend: AIBackend = AIBackend.OLLAMA,
    config: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> AIProcessor:
    """
    Factory function to get an AI processor.

    Args:
        backend: AI backend to use
        config: Configuration dictionary
        **kwargs: Additional arguments for specific processors

    Returns:
        AIProcessor instance
    """
    processors = {
        AIBackend.OLLAMA: OllamaProcessor,
        AIBackend.LM_STUDIO: LMStudioProcessor,
        AIBackend.GPT4ALL: GPT4AllProcessor,
        AIBackend.OPENAI: lambda c: CloudAPIProcessor(c, provider="openai", **kwargs),
        AIBackend.ANTHROPIC: lambda c: CloudAPIProcessor(c, provider="anthropic", **kwargs),
    }

    processor_class = processors.get(backend)
    if processor_class is None:
        raise ValueError(f"Unknown AI backend: {backend}")

    return processor_class(config)


def get_processor_for_provider(
    mode: str,
    provider: str,
    config: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> AIProcessor:
    """
    Get an AI processor for a specific provider.

    Args:
        mode: "local" or "cloud"
        provider: Provider identifier
        config: Configuration dictionary
        **kwargs: Additional arguments

    Returns:
        AIProcessor instance
    """
    if mode == "local":
        local_processors = {
            LocalAIProvider.OLLAMA.value: OllamaProcessor,
            LocalAIProvider.LM_STUDIO.value: LMStudioProcessor,
            LocalAIProvider.MISTRAL_LOCAL.value: MistralLocalProcessor,
            LocalAIProvider.GPT4ALL.value: GPT4AllProcessor,
            LocalAIProvider.LOCALAI.value: LocalAIProcessor,
            LocalAIProvider.LLAMA_CPP.value: LlamaCppProcessor,
            LocalAIProvider.JAN.value: JanProcessor,
            LocalAIProvider.CUSTOM.value: LocalAIProcessor,
        }
        processor_class = local_processors.get(provider, OllamaProcessor)
        return processor_class(config)

    else:
        cloud_processors = {
            CloudAIProvider.OPENAI.value: lambda c: CloudAPIProcessor(c, provider="openai", **kwargs),
            CloudAIProvider.ANTHROPIC.value: lambda c: CloudAPIProcessor(c, provider="anthropic", **kwargs),
            CloudAIProvider.GOOGLE_GEMINI.value: GeminiProcessor,
            CloudAIProvider.MISTRAL_AI.value: MistralAIProcessor,
            CloudAIProvider.COHERE.value: CohereProcessor,
            CloudAIProvider.CUSTOM.value: lambda c: CloudAPIProcessor(c, provider="openai", **kwargs),
        }
        processor_class = cloud_processors.get(provider)
        if processor_class is None:
            raise ValueError(f"Unknown cloud provider: {provider}")
        return processor_class(config, **kwargs)
