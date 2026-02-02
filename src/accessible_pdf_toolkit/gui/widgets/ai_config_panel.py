"""
Enhanced AI configuration panel with expanded provider support and privacy controls.
"""

from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QSlider,
    QSpinBox,
    QFrame,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
    QMessageBox,
    QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...utils.constants import (
    COLORS,
    LocalAIProvider,
    CloudAIProvider,
    DEFAULT_CONFIG,
)
from ...utils.logger import get_logger
from ..dialogs.privacy_warning_dialog import PrivacyWarningDialog

logger = get_logger(__name__)


class AIConfigPanel(QWidget):
    """Enhanced AI configuration panel."""

    # Signals
    config_changed = pyqtSignal(dict)
    provider_changed = pyqtSignal(str, str)  # mode, provider
    connection_tested = pyqtSignal(bool, str)  # success, message

    # Local provider configurations
    LOCAL_PROVIDERS = {
        LocalAIProvider.OLLAMA.value: {
            "name": "Ollama",
            "description": "Open-source local LLM runner",
            "url_key": "ollama_url",
            "default_url": "http://localhost:11434",
            "models_endpoint": "/api/tags",
        },
        LocalAIProvider.LM_STUDIO.value: {
            "name": "LM Studio",
            "description": "Desktop app for local LLMs",
            "url_key": "lmstudio_url",
            "default_url": "http://localhost:1234",
            "models_endpoint": "/v1/models",
        },
        LocalAIProvider.MISTRAL_LOCAL.value: {
            "name": "Mistral (Local)",
            "description": "Mistral AI local server",
            "url_key": "mistral_local_url",
            "default_url": "http://localhost:8080",
        },
        LocalAIProvider.GPT4ALL.value: {
            "name": "GPT4All",
            "description": "Local AI chatbot (no server)",
            "url_key": None,
            "requires_download": True,
        },
        LocalAIProvider.LOCALAI.value: {
            "name": "LocalAI",
            "description": "OpenAI-compatible local API",
            "url_key": "localai_url",
            "default_url": "http://localhost:8080",
        },
        LocalAIProvider.LLAMA_CPP.value: {
            "name": "Llama.cpp Server",
            "description": "C++ LLM inference server",
            "url_key": "llama_cpp_url",
            "default_url": "http://localhost:8080",
        },
        LocalAIProvider.JAN.value: {
            "name": "Jan",
            "description": "Open-source ChatGPT alternative",
            "url_key": "jan_url",
            "default_url": "http://localhost:1337",
        },
        LocalAIProvider.CUSTOM.value: {
            "name": "Custom Endpoint",
            "description": "Custom local API endpoint",
            "url_key": "custom_local_url",
            "default_url": "http://localhost:8080",
        },
    }

    # Cloud provider configurations
    CLOUD_PROVIDERS = {
        CloudAIProvider.OPENAI.value: {
            "name": "OpenAI",
            "description": "GPT-4, GPT-4o, GPT-3.5 Turbo",
            "models": ["gpt-4-turbo", "gpt-4o", "gpt-3.5-turbo"],
            "requires_key": True,
        },
        CloudAIProvider.ANTHROPIC.value: {
            "name": "Anthropic",
            "description": "Claude 3.5 Sonnet, Claude 3 Opus, Haiku",
            "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
            "requires_key": True,
        },
        CloudAIProvider.GOOGLE_GEMINI.value: {
            "name": "Google Gemini",
            "description": "Gemini 1.5 Pro, Gemini 1.5 Flash",
            "models": ["gemini-1.5-pro", "gemini-1.5-flash"],
            "requires_key": True,
        },
        CloudAIProvider.MISTRAL_AI.value: {
            "name": "Mistral AI",
            "description": "Mistral Large, Mistral Medium",
            "models": ["mistral-large-latest", "mistral-medium-latest"],
            "requires_key": True,
        },
        CloudAIProvider.COHERE.value: {
            "name": "Cohere",
            "description": "Command R+, Command R",
            "models": ["command-r-plus", "command-r"],
            "requires_key": True,
        },
        CloudAIProvider.CUSTOM.value: {
            "name": "Custom API",
            "description": "Custom cloud API endpoint",
            "models": [],
            "requires_key": True,
        },
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)

        self._config = config or DEFAULT_CONFIG.get("ai", {}).copy()
        self._privacy_warning_accepted = self._config.get("privacy_warning_accepted", False)

        self._setup_ui()
        self._setup_accessibility()
        self._apply_styles()
        self._load_config()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)

        # Processing Method Selection
        method_group = QGroupBox("Processing Method")
        method_layout = QVBoxLayout(method_group)

        self._mode_group = QButtonGroup(self)

        # Local option
        local_frame = QFrame()
        local_frame.setObjectName("localFrame")
        local_layout = QVBoxLayout(local_frame)
        local_layout.setContentsMargins(12, 12, 12, 12)

        self._local_radio = QRadioButton("LOCAL MODELS (Private - FERPA/HIPAA Safe)")
        self._local_radio.setChecked(True)
        self._local_radio.toggled.connect(self._on_mode_changed)
        self._mode_group.addButton(self._local_radio)
        local_layout.addWidget(self._local_radio)

        local_desc = QLabel(
            "\u2705 Data stays on your computer\n"
            "\u2705 No internet required\n"
            "\u2705 Full compliance with privacy regulations"
        )
        local_desc.setStyleSheet(f"color: {COLORS.SUCCESS}; font-size: 10pt; margin-left: 24px;")
        local_layout.addWidget(local_desc)

        method_layout.addWidget(local_frame)

        # Cloud option
        cloud_frame = QFrame()
        cloud_frame.setObjectName("cloudFrame")
        cloud_layout = QVBoxLayout(cloud_frame)
        cloud_layout.setContentsMargins(12, 12, 12, 12)

        self._cloud_radio = QRadioButton("CLOUD APIs (\u26A0\uFE0F NOT FERPA/HIPAA Compliant)")
        self._cloud_radio.toggled.connect(self._on_mode_changed)
        self._mode_group.addButton(self._cloud_radio)
        cloud_layout.addWidget(self._cloud_radio)

        cloud_desc = QLabel(
            "\u274C Data sent to external servers\n"
            "\u274C Not suitable for sensitive documents\n"
            "\u274C Requires API keys and internet"
        )
        cloud_desc.setStyleSheet(f"color: {COLORS.ERROR}; font-size: 10pt; margin-left: 24px;")
        cloud_layout.addWidget(cloud_desc)

        method_layout.addWidget(cloud_frame)

        content_layout.addWidget(method_group)

        # Provider Selection (stacked for local/cloud)
        self._provider_group = QGroupBox("Provider Configuration")
        provider_layout = QVBoxLayout(self._provider_group)

        # Provider dropdown
        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel("Provider:"))

        self._provider_combo = QComboBox()
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        provider_row.addWidget(self._provider_combo, 1)

        provider_layout.addLayout(provider_row)

        # Provider description
        self._provider_desc = QLabel("")
        self._provider_desc.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 10pt;")
        provider_layout.addWidget(self._provider_desc)

        # Model selection
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model:"))

        self._model_combo = QComboBox()
        self._model_combo.setEditable(True)
        model_row.addWidget(self._model_combo, 1)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self._refresh_models)
        model_row.addWidget(self._refresh_btn)

        provider_layout.addLayout(model_row)

        # Server URL (for local providers)
        self._url_row = QWidget()
        url_layout = QHBoxLayout(self._url_row)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_layout.addWidget(QLabel("Server URL:"))

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("http://localhost:11434")
        url_layout.addWidget(self._url_edit, 1)

        provider_layout.addWidget(self._url_row)

        # API Key (for cloud providers)
        self._key_row = QWidget()
        key_layout = QHBoxLayout(self._key_row)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.addWidget(QLabel("API Key:"))

        self._key_edit = QLineEdit()
        self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_edit.setPlaceholderText("Enter your API key...")
        key_layout.addWidget(self._key_edit, 1)

        provider_layout.addWidget(self._key_row)

        # Test connection button and status
        test_row = QHBoxLayout()

        self._test_btn = QPushButton("Test Connection")
        self._test_btn.clicked.connect(self._test_connection)
        test_row.addWidget(self._test_btn)

        self._status_label = QLabel("")
        test_row.addWidget(self._status_label, 1)

        provider_layout.addLayout(test_row)

        content_layout.addWidget(self._provider_group)

        # Advanced Settings
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QVBoxLayout(advanced_group)

        # Temperature
        temp_row = QHBoxLayout()
        temp_row.addWidget(QLabel("Temperature:"))

        self._temp_slider = QSlider(Qt.Orientation.Horizontal)
        self._temp_slider.setMinimum(0)
        self._temp_slider.setMaximum(100)
        self._temp_slider.setValue(30)
        self._temp_slider.valueChanged.connect(self._on_temp_changed)
        temp_row.addWidget(self._temp_slider, 1)

        self._temp_label = QLabel("0.3")
        self._temp_label.setFixedWidth(40)
        temp_row.addWidget(self._temp_label)

        temp_row.addWidget(QLabel("Low \u2190 \u2192 Creative"))

        advanced_layout.addLayout(temp_row)

        # Max Tokens
        tokens_row = QHBoxLayout()
        tokens_row.addWidget(QLabel("Max Tokens:"))

        self._tokens_slider = QSlider(Qt.Orientation.Horizontal)
        self._tokens_slider.setMinimum(256)
        self._tokens_slider.setMaximum(8192)
        self._tokens_slider.setValue(2048)
        self._tokens_slider.valueChanged.connect(self._on_tokens_changed)
        tokens_row.addWidget(self._tokens_slider, 1)

        self._tokens_label = QLabel("2048")
        self._tokens_label.setFixedWidth(50)
        tokens_row.addWidget(self._tokens_label)

        tokens_row.addWidget(QLabel("Short \u2190 \u2192 Long"))

        advanced_layout.addLayout(tokens_row)

        # Context Window
        context_row = QHBoxLayout()
        context_row.addWidget(QLabel("Context:"))

        self._context_spin = QSpinBox()
        self._context_spin.setMinimum(1024)
        self._context_spin.setMaximum(128000)
        self._context_spin.setValue(4096)
        self._context_spin.setSingleStep(1024)
        self._context_spin.setSuffix(" tokens")
        context_row.addWidget(self._context_spin)

        context_row.addStretch()

        advanced_layout.addLayout(context_row)

        content_layout.addWidget(advanced_group)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self.setAccessibleName("AI Configuration Panel")
        self.setAccessibleDescription("Configure AI processing method and provider settings")

        self._local_radio.setAccessibleName("Use local AI models")
        self._cloud_radio.setAccessibleName("Use cloud AI providers")
        self._provider_combo.setAccessibleName("Select AI provider")
        self._model_combo.setAccessibleName("Select AI model")
        self._url_edit.setAccessibleName("Server URL")
        self._key_edit.setAccessibleName("API key")
        self._temp_slider.setAccessibleName("Temperature setting")
        self._tokens_slider.setAccessibleName("Maximum tokens setting")
        self._context_spin.setAccessibleName("Context window size")

    def _apply_styles(self) -> None:
        """Apply widget styles."""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
            }}

            QGroupBox {{
                font-size: 12pt;
                font-weight: bold;
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }}

            #localFrame {{
                background-color: rgba(16, 185, 129, 0.1);
                border: 2px solid {COLORS.SUCCESS};
                border-radius: 8px;
            }}

            #cloudFrame {{
                background-color: rgba(239, 68, 68, 0.1);
                border: 2px solid {COLORS.ERROR};
                border-radius: 8px;
            }}

            QRadioButton {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
                font-weight: bold;
                spacing: 8px;
            }}

            QRadioButton::indicator {{
                width: 20px;
                height: 20px;
            }}

            QLabel {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 11pt;
            }}

            QComboBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 11pt;
            }}

            QComboBox QAbstractItemView {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                selection-background-color: {COLORS.PRIMARY};
            }}

            QLineEdit {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 11pt;
            }}

            QLineEdit:focus {{
                border: 2px solid {COLORS.INPUT_FOCUS};
            }}

            QSpinBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 11pt;
            }}

            QPushButton {{
                background-color: {COLORS.SURFACE};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11pt;
            }}

            QPushButton:hover {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}

            QSlider::groove:horizontal {{
                border: 1px solid {COLORS.BORDER};
                height: 8px;
                background: {COLORS.INPUT_BG};
                border-radius: 4px;
            }}

            QSlider::handle:horizontal {{
                background: {COLORS.PRIMARY};
                border: none;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }}

            QScrollArea {{
                border: none;
            }}
        """)

    def _load_config(self) -> None:
        """Load configuration into UI."""
        mode = self._config.get("mode", "local")
        if mode == "cloud":
            self._cloud_radio.setChecked(True)
        else:
            self._local_radio.setChecked(True)

        self._populate_providers()

        # Temperature
        temp = self._config.get("temperature", 0.7)
        self._temp_slider.setValue(int(temp * 100))

        # Tokens
        tokens = self._config.get("max_tokens", 2000)
        self._tokens_slider.setValue(tokens)

        # Context
        context = self._config.get("context_window", 4096)
        self._context_spin.setValue(context)

    def _populate_providers(self) -> None:
        """Populate provider dropdown based on mode."""
        self._provider_combo.clear()

        if self._local_radio.isChecked():
            for key, info in self.LOCAL_PROVIDERS.items():
                self._provider_combo.addItem(info["name"], key)

            # Select saved provider
            local_provider = self._config.get("local_provider", "ollama")
            index = self._provider_combo.findData(local_provider)
            if index >= 0:
                self._provider_combo.setCurrentIndex(index)

            self._url_row.show()
            self._key_row.hide()
        else:
            for key, info in self.CLOUD_PROVIDERS.items():
                self._provider_combo.addItem(info["name"], key)

            # Select saved provider
            cloud_provider = self._config.get("cloud_provider", "openai")
            index = self._provider_combo.findData(cloud_provider)
            if index >= 0:
                self._provider_combo.setCurrentIndex(index)

            self._url_row.hide()
            self._key_row.show()

    def _on_mode_changed(self, checked: bool) -> None:
        """Handle mode change."""
        if not checked:
            return

        if self._cloud_radio.isChecked():
            # Show privacy warning
            if not self._privacy_warning_accepted:
                accepted, dont_show = PrivacyWarningDialog.show_warning(
                    self, self._privacy_warning_accepted
                )
                if not accepted:
                    self._local_radio.setChecked(True)
                    return
                self._privacy_warning_accepted = dont_show

        self._populate_providers()
        self._emit_config()

    def _on_provider_changed(self, index: int) -> None:
        """Handle provider change."""
        provider_key = self._provider_combo.currentData()
        if not provider_key:
            return

        if self._local_radio.isChecked():
            info = self.LOCAL_PROVIDERS.get(provider_key, {})
            self._provider_desc.setText(info.get("description", ""))

            # Update URL
            url_key = info.get("url_key")
            if url_key:
                default_url = info.get("default_url", "")
                saved_url = self._config.get(url_key, default_url)
                self._url_edit.setText(saved_url)
                self._url_row.show()
            else:
                self._url_row.hide()

            # Clear models and refresh
            self._model_combo.clear()
            self._model_combo.addItem("(Click Refresh to load models)")

        else:
            info = self.CLOUD_PROVIDERS.get(provider_key, {})
            self._provider_desc.setText(info.get("description", ""))

            # Populate models
            self._model_combo.clear()
            for model in info.get("models", []):
                self._model_combo.addItem(model)

        self._status_label.setText("")
        self._emit_config()

    def _on_temp_changed(self, value: int) -> None:
        """Handle temperature change."""
        temp = value / 100.0
        self._temp_label.setText(f"{temp:.1f}")
        self._emit_config()

    def _on_tokens_changed(self, value: int) -> None:
        """Handle max tokens change."""
        self._tokens_label.setText(str(value))
        self._emit_config()

    def _refresh_models(self) -> None:
        """Refresh available models from provider."""
        provider_key = self._provider_combo.currentData()
        if not provider_key:
            return

        if self._local_radio.isChecked():
            info = self.LOCAL_PROVIDERS.get(provider_key, {})
            url_key = info.get("url_key")
            if not url_key:
                QMessageBox.information(
                    self,
                    "Not Supported",
                    "This provider doesn't support model listing.",
                )
                return

            base_url = self._url_edit.text() or info.get("default_url", "")
            models_endpoint = info.get("models_endpoint")

            if not models_endpoint:
                QMessageBox.information(
                    self,
                    "Not Supported",
                    "Model listing not available for this provider.",
                )
                return

            # Try to fetch models
            try:
                import httpx
                response = httpx.get(
                    f"{base_url}{models_endpoint}",
                    timeout=10,
                )
                response.raise_for_status()

                data = response.json()
                self._model_combo.clear()

                # Parse based on endpoint type
                if "/api/tags" in models_endpoint:
                    # Ollama format
                    models = data.get("models", [])
                    for model in models:
                        name = model.get("name", "")
                        if name:
                            self._model_combo.addItem(name)
                elif "/v1/models" in models_endpoint:
                    # OpenAI-compatible format
                    models = data.get("data", [])
                    for model in models:
                        model_id = model.get("id", "")
                        if model_id:
                            self._model_combo.addItem(model_id)

                if self._model_combo.count() == 0:
                    self._model_combo.addItem("(No models found)")

            except Exception as e:
                logger.error(f"Failed to fetch models: {e}")
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to fetch models: {e}",
                )

    def _test_connection(self) -> None:
        """Test connection to the selected provider."""
        provider_key = self._provider_combo.currentData()
        if not provider_key:
            return

        self._status_label.setText("Testing...")

        try:
            import httpx

            if self._local_radio.isChecked():
                info = self.LOCAL_PROVIDERS.get(provider_key, {})
                url_key = info.get("url_key")

                if not url_key:
                    # GPT4All doesn't have a server
                    try:
                        import gpt4all
                        self._status_label.setText("\u2705 GPT4All available")
                        self._status_label.setStyleSheet(f"color: {COLORS.SUCCESS};")
                        self.connection_tested.emit(True, "GPT4All available")
                        return
                    except ImportError:
                        self._status_label.setText("\u274C GPT4All not installed")
                        self._status_label.setStyleSheet(f"color: {COLORS.ERROR};")
                        self.connection_tested.emit(False, "GPT4All not installed")
                        return

                base_url = self._url_edit.text() or info.get("default_url", "")
                response = httpx.get(base_url, timeout=10)

                if response.status_code == 200:
                    self._status_label.setText(f"\u2705 Connected to {base_url}")
                    self._status_label.setStyleSheet(f"color: {COLORS.SUCCESS};")
                    self.connection_tested.emit(True, f"Connected to {base_url}")
                else:
                    self._status_label.setText(f"\u26A0\uFE0F Status: {response.status_code}")
                    self._status_label.setStyleSheet(f"color: {COLORS.WARNING};")
                    self.connection_tested.emit(False, f"Status: {response.status_code}")

            else:
                # Cloud providers - just check if API key is set
                api_key = self._key_edit.text().strip()
                if not api_key:
                    self._status_label.setText("\u274C No API key provided")
                    self._status_label.setStyleSheet(f"color: {COLORS.ERROR};")
                    self.connection_tested.emit(False, "No API key")
                    return

                # Could do a minimal API call to verify, but for now just check format
                if len(api_key) > 10:
                    self._status_label.setText("\u2705 API key configured")
                    self._status_label.setStyleSheet(f"color: {COLORS.SUCCESS};")
                    self.connection_tested.emit(True, "API key configured")
                else:
                    self._status_label.setText("\u26A0\uFE0F API key looks invalid")
                    self._status_label.setStyleSheet(f"color: {COLORS.WARNING};")
                    self.connection_tested.emit(False, "Invalid API key format")

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            self._status_label.setText(f"\u274C Error: {str(e)[:50]}")
            self._status_label.setStyleSheet(f"color: {COLORS.ERROR};")
            self.connection_tested.emit(False, str(e))

    def _emit_config(self) -> None:
        """Emit the current configuration."""
        config = self.get_config()
        self.config_changed.emit(config)

        mode = "cloud" if self._cloud_radio.isChecked() else "local"
        provider = self._provider_combo.currentData() or ""
        self.provider_changed.emit(mode, provider)

    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        mode = "cloud" if self._cloud_radio.isChecked() else "local"
        provider_key = self._provider_combo.currentData() or ""

        config = {
            "mode": mode,
            "local_provider": provider_key if mode == "local" else self._config.get("local_provider", "ollama"),
            "cloud_provider": provider_key if mode == "cloud" else self._config.get("cloud_provider", "openai"),
            "default_model": self._model_combo.currentText(),
            "temperature": self._temp_slider.value() / 100.0,
            "max_tokens": self._tokens_slider.value(),
            "context_window": self._context_spin.value(),
            "privacy_warning_accepted": self._privacy_warning_accepted,
        }

        # Add provider-specific settings
        if mode == "local":
            info = self.LOCAL_PROVIDERS.get(provider_key, {})
            url_key = info.get("url_key")
            if url_key:
                config[url_key] = self._url_edit.text() or info.get("default_url", "")

        return config

    def set_config(self, config: Dict[str, Any]) -> None:
        """Set the configuration."""
        self._config = config
        self._privacy_warning_accepted = config.get("privacy_warning_accepted", False)
        self._load_config()
