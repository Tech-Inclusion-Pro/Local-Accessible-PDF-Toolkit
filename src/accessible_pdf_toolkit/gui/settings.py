"""
Settings panel for application configuration.
"""

import json
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QSpinBox,
    QGroupBox,
    QScrollArea,
    QFrame,
    QMessageBox,
    QTabWidget,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, pyqtProperty, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QPen

from ..utils.constants import (
    COLORS,
    AIBackend,
    WCAGLevel,
    ColorBlindMode,
    CustomCursorStyle,
    DEFAULT_CONFIG,
    MIN_BATCH_SIZE,
    MAX_BATCH_SIZE,
    MIN_FONT_SIZE,
    MAX_FONT_SIZE,
)
from ..utils.logger import get_logger
from ..database.models import User
from ..database.queries import DatabaseQueries
from .widgets.ai_config_panel import AIConfigPanel

logger = get_logger(__name__)


class ToggleSwitch(QWidget):
    """Custom toggle switch widget replacing square checkboxes."""

    toggled = pyqtSignal(bool)

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._checked = False
        self._thumb_x = 0.0
        self._text = text

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setAccessibleName(text)

        self._anim = QPropertyAnimation(self, b"thumb_position")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    # -- Qt animated property --
    def _get_thumb_pos(self):
        return self._thumb_x

    def _set_thumb_pos(self, v):
        self._thumb_x = v
        self.update()

    thumb_position = pyqtProperty(float, _get_thumb_pos, _set_thumb_pos)

    # -- Public API (compatible with QCheckBox) --
    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked == checked:
            return
        self._checked = checked
        self._anim.stop()
        self._thumb_x = 1.0 if checked else 0.0
        self.update()
        self.toggled.emit(checked)

    def toggle(self):
        self._checked = not self._checked
        self._anim.stop()
        self._anim.setStartValue(self._thumb_x)
        self._anim.setEndValue(1.0 if self._checked else 0.0)
        self._anim.start()
        self.toggled.emit(self._checked)

    # -- Events --
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.toggle()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        track_w, track_h = 44, 24
        track_y = (self.height() - track_h) // 2
        radius = track_h // 2

        # Interpolate track color between off and on
        off_c = QColor(COLORS.BORDER)
        on_c = QColor(COLORS.PRIMARY)
        t = self._thumb_x
        track_color = QColor(
            int(off_c.red() + (on_c.red() - off_c.red()) * t),
            int(off_c.green() + (on_c.green() - off_c.green()) * t),
            int(off_c.blue() + (on_c.blue() - off_c.blue()) * t),
        )

        painter.setBrush(track_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, track_y, track_w, track_h, radius, radius)

        # Thumb
        thumb_d = track_h - 4
        thumb_y = track_y + 2
        thumb_travel = track_w - thumb_d - 4
        thumb_x = int(2 + thumb_travel * self._thumb_x)

        # Shadow
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.drawEllipse(thumb_x + 1, thumb_y + 1, thumb_d, thumb_d)
        # Knob
        painter.setBrush(QColor("white"))
        painter.drawEllipse(thumb_x, thumb_y, thumb_d, thumb_d)

        # Focus ring
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(COLORS.PRIMARY), 2))
            painter.drawRoundedRect(
                -1, track_y - 1, track_w + 2, track_h + 2, radius + 1, radius + 1
            )

        # Label text
        if self._text:
            painter.setPen(QColor(COLORS.TEXT_PRIMARY))
            text_rect = self.rect().adjusted(track_w + 10, 0, 0, 0)
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self._text,
            )

        painter.end()

    def sizeHint(self):
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self._text) if self._text else 0
        return QSize(44 + 10 + text_w + 10, max(30, fm.height() + 10))

    def minimumSizeHint(self):
        return QSize(44, 24)


class SettingsPanel(QWidget):
    """Settings panel for application configuration."""

    # Signals
    settings_changed = pyqtSignal(dict)
    preview_requested = pyqtSignal(dict)
    ai_backend_changed = pyqtSignal(str)

    def __init__(self, user: Optional[User] = None, parent=None):
        super().__init__(parent)

        self._user = user
        self._db = DatabaseQueries() if user else None
        self._config = DEFAULT_CONFIG.copy()
        self._loading_config = False

        self._setup_ui()
        self._setup_accessibility()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.BACKGROUND_ALT};
                border-bottom: 1px solid {COLORS.BORDER};
                padding: 16px;
            }}
        """)
        header_layout = QHBoxLayout(header)

        title = QLabel("Settings")
        title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {COLORS.TEXT_PRIMARY};
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save_settings)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY_DARK};
            }}
        """)
        header_layout.addWidget(save_btn)

        layout.addWidget(header)

        # Settings tabs
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {COLORS.BACKGROUND};
            }}
            QTabBar::tab {{
                padding: 10px 20px;
                margin-right: 4px;
                background-color: {COLORS.BACKGROUND_ALT};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-bottom: none;
                border-radius: 4px 4px 0 0;
                font-size: 12pt;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}
        """)

        # AI Settings tab - use new enhanced AIConfigPanel
        self._ai_config_panel = AIConfigPanel(self._config.get("ai", {}))
        self._ai_config_panel.config_changed.connect(self._on_ai_config_changed)
        tabs.addTab(self._ai_config_panel, "AI Backend")

        # Processing tab
        processing_tab = self._create_processing_settings()
        tabs.addTab(processing_tab, "Processing")

        # Accessibility tab
        accessibility_tab = self._create_accessibility_settings()
        tabs.addTab(accessibility_tab, "Accessibility")

        # UI tab
        ui_tab = self._create_ui_settings()
        tabs.addTab(ui_tab, "Interface")

        # Security tab
        security_tab = self._create_security_settings()
        tabs.addTab(security_tab, "Security")

        layout.addWidget(tabs)

    def _create_scroll_widget(self, content: QWidget) -> QScrollArea:
        """Wrap a widget in a scroll area."""
        scroll = QScrollArea()
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        return scroll

    def _create_ai_settings(self) -> QWidget:
        """Create AI settings panel."""
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
            }}
            QGroupBox {{
                font-size: 12pt;
                font-weight: bold;
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QLabel {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}
            QLineEdit {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS.INPUT_FOCUS};
            }}
            QComboBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                selection-background-color: {COLORS.PRIMARY};
            }}
            QSpinBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}
            QPushButton {{
                background-color: {COLORS.BACKGROUND_ALT};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Backend selection
        backend_group = QGroupBox("AI Backend")
        backend_layout = QVBoxLayout(backend_group)

        backend_label = QLabel("Select your preferred AI backend:")
        backend_layout.addWidget(backend_label)

        self.backend_combo = QComboBox()
        self.backend_combo.addItem("Ollama (Local)", AIBackend.OLLAMA.value)
        self.backend_combo.addItem("LM Studio (Local)", AIBackend.LM_STUDIO.value)
        self.backend_combo.addItem("GPT4All (Local)", AIBackend.GPT4ALL.value)
        self.backend_combo.addItem("OpenAI (Cloud)", AIBackend.OPENAI.value)
        self.backend_combo.addItem("Anthropic (Cloud)", AIBackend.ANTHROPIC.value)
        self.backend_combo.currentIndexChanged.connect(self._on_backend_changed)
        self.backend_combo.setAccessibleName("Select AI backend")
        backend_layout.addWidget(self.backend_combo)

        # Privacy warning for cloud
        self.privacy_warning = QLabel(
            "\u25B3 <b>Privacy Warning:</b> Cloud APIs send data to external servers. "
            "This may not be FERPA/HIPAA compliant for sensitive documents."
        )
        self.privacy_warning.setWordWrap(True)
        self.privacy_warning.setStyleSheet(f"""
            color: {COLORS.WARNING};
            background-color: #FEF3C7;
            border: 1px solid {COLORS.WARNING};
            border-radius: 4px;
            padding: 12px;
        """)
        self.privacy_warning.hide()
        backend_layout.addWidget(self.privacy_warning)

        layout.addWidget(backend_group)

        # Ollama settings
        self.ollama_group = QGroupBox("Ollama Settings")
        ollama_layout = QVBoxLayout(self.ollama_group)

        url_layout = QHBoxLayout()
        url_label = QLabel("Server URL:")
        url_layout.addWidget(url_label)
        self.ollama_url = QLineEdit()
        self.ollama_url.setPlaceholderText("http://localhost:11434")
        self.ollama_url.setAccessibleName("Ollama server URL")
        url_layout.addWidget(self.ollama_url)
        ollama_layout.addLayout(url_layout)

        model_layout = QHBoxLayout()
        model_label = QLabel("Default Model:")
        model_layout.addWidget(model_label)
        self.ollama_model = QLineEdit()
        self.ollama_model.setPlaceholderText("llava")
        self.ollama_model.setAccessibleName("Ollama model name")
        model_layout.addWidget(self.ollama_model)
        ollama_layout.addLayout(model_layout)

        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self._test_ollama)
        ollama_layout.addWidget(test_btn)

        layout.addWidget(self.ollama_group)

        # LM Studio settings
        self.lmstudio_group = QGroupBox("LM Studio Settings")
        lmstudio_layout = QVBoxLayout(self.lmstudio_group)

        lm_url_layout = QHBoxLayout()
        lm_url_label = QLabel("Server URL:")
        lm_url_layout.addWidget(lm_url_label)
        self.lmstudio_url = QLineEdit()
        self.lmstudio_url.setPlaceholderText("http://localhost:1234")
        self.lmstudio_url.setAccessibleName("LM Studio server URL")
        lm_url_layout.addWidget(self.lmstudio_url)
        lmstudio_layout.addLayout(lm_url_layout)

        self.lmstudio_group.hide()
        layout.addWidget(self.lmstudio_group)

        # GPT4All settings
        self.gpt4all_group = QGroupBox("GPT4All Settings")
        gpt4all_layout = QVBoxLayout(self.gpt4all_group)

        gpt4all_model_layout = QHBoxLayout()
        gpt4all_model_label = QLabel("Model:")
        gpt4all_model_layout.addWidget(gpt4all_model_label)
        self.gpt4all_model = QComboBox()
        self.gpt4all_model.addItem("Orca Mini 3B", "orca-mini-3b-gguf2-q4_0.gguf")
        self.gpt4all_model.addItem("Mistral 7B", "mistral-7b-openorca.gguf2.Q4_0.gguf")
        self.gpt4all_model.addItem("LLaMA 2 7B", "llama-2-7b-chat.gguf")
        self.gpt4all_model.setAccessibleName("GPT4All model")
        gpt4all_model_layout.addWidget(self.gpt4all_model)
        gpt4all_layout.addLayout(gpt4all_model_layout)

        self.gpt4all_group.hide()
        layout.addWidget(self.gpt4all_group)

        # Timeout setting
        timeout_group = QGroupBox("Request Settings")
        timeout_layout = QHBoxLayout(timeout_group)

        timeout_label = QLabel("Request Timeout (seconds):")
        timeout_layout.addWidget(timeout_label)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(10)
        self.timeout_spin.setMaximum(300)
        self.timeout_spin.setValue(60)
        self.timeout_spin.setAccessibleName("Request timeout")
        timeout_layout.addWidget(self.timeout_spin)

        timeout_layout.addStretch()
        layout.addWidget(timeout_group)

        layout.addStretch()
        return self._create_scroll_widget(container)

    def _create_processing_settings(self) -> QWidget:
        """Create processing settings panel."""
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
            }}
            QGroupBox {{
                font-size: 12pt;
                font-weight: bold;
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QLabel {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}
            QSpinBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}
            QComboBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                selection-background-color: {COLORS.PRIMARY};
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Batch processing
        batch_group = QGroupBox("Batch Processing")
        batch_layout = QVBoxLayout(batch_group)

        batch_row = QHBoxLayout()
        batch_label = QLabel("Maximum PDFs per batch:")
        batch_row.addWidget(batch_label)

        self.batch_limit = QSpinBox()
        self.batch_limit.setMinimum(MIN_BATCH_SIZE)
        self.batch_limit.setMaximum(MAX_BATCH_SIZE)
        self.batch_limit.setValue(5)
        self.batch_limit.setAccessibleName("Batch limit")
        batch_row.addWidget(self.batch_limit)
        batch_row.addStretch()

        batch_layout.addLayout(batch_row)

        batch_info = QLabel(f"Process {MIN_BATCH_SIZE}-{MAX_BATCH_SIZE} PDFs simultaneously")
        batch_info.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY};")
        batch_layout.addWidget(batch_info)

        layout.addWidget(batch_group)

        # OCR settings
        ocr_group = QGroupBox("OCR Settings")
        ocr_layout = QVBoxLayout(ocr_group)

        self.auto_ocr_cb = ToggleSwitch("Automatically run OCR on scanned documents")
        self.auto_ocr_cb.setChecked(True)
        ocr_layout.addWidget(self.auto_ocr_cb)

        lang_row = QHBoxLayout()
        lang_label = QLabel("OCR Language:")
        lang_row.addWidget(lang_label)

        self.ocr_language = QComboBox()
        self.ocr_language.addItem("English", "eng")
        self.ocr_language.addItem("Spanish", "spa")
        self.ocr_language.addItem("French", "fra")
        self.ocr_language.addItem("German", "deu")
        self.ocr_language.addItem("Italian", "ita")
        self.ocr_language.addItem("Portuguese", "por")
        self.ocr_language.setAccessibleName("OCR language")
        lang_row.addWidget(self.ocr_language)
        lang_row.addStretch()

        ocr_layout.addLayout(lang_row)
        layout.addWidget(ocr_group)

        # File handling
        file_group = QGroupBox("File Handling")
        file_layout = QVBoxLayout(file_group)

        self.preserve_original_cb = ToggleSwitch("Preserve original files (create copies)")
        self.preserve_original_cb.setChecked(True)
        file_layout.addWidget(self.preserve_original_cb)

        layout.addWidget(file_group)

        layout.addStretch()
        return self._create_scroll_widget(container)

    def _create_accessibility_settings(self) -> QWidget:
        """Create accessibility settings panel matching MycoFolio format."""
        container = QWidget()
        base_style = f"""
            QWidget {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
            }}
            QGroupBox {{
                font-size: 12pt;
                font-weight: bold;
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QLabel {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}
            QComboBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                selection-background-color: {COLORS.PRIMARY};
            }}
        """
        container.setStyleSheet(base_style)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # ── Display & Visual Accessibility ──────────────────────
        display_group = QGroupBox("Display & Visual Accessibility")
        display_layout = QVBoxLayout(display_group)
        display_layout.setSpacing(12)

        # High Contrast Mode
        self.high_contrast_cb = ToggleSwitch("High Contrast Mode")
        self.high_contrast_cb.setAccessibleName("High contrast mode")
        self.high_contrast_cb.setToolTip("Increase contrast for better visibility")
        display_layout.addWidget(self.high_contrast_cb)
        hc_desc = QLabel("Increase contrast for better visibility")
        hc_desc.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 10pt; margin-left: 26px;")
        display_layout.addWidget(hc_desc)

        # Reduced Motion
        self.reduced_motion_cb = ToggleSwitch("Reduced Motion")
        self.reduced_motion_cb.setAccessibleName("Reduced motion")
        self.reduced_motion_cb.setToolTip("Disable animations throughout the application")
        display_layout.addWidget(self.reduced_motion_cb)
        rm_desc = QLabel("Disable animations")
        rm_desc.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 10pt; margin-left: 26px;")
        display_layout.addWidget(rm_desc)

        # Large Text Mode
        self.large_text_cb = ToggleSwitch("Large Text Mode")
        self.large_text_cb.setAccessibleName("Large text mode")
        self.large_text_cb.setToolTip("Increase font size by 25%")
        display_layout.addWidget(self.large_text_cb)
        lt_desc = QLabel("Increase font size by 25%")
        lt_desc.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 10pt; margin-left: 26px;")
        display_layout.addWidget(lt_desc)

        # Enhanced Focus Indicators
        self.enhanced_focus_cb = ToggleSwitch("Enhanced Focus Indicators")
        self.enhanced_focus_cb.setAccessibleName("Enhanced focus indicators")
        self.enhanced_focus_cb.setToolTip("Larger, more visible focus outlines")
        display_layout.addWidget(self.enhanced_focus_cb)
        ef_desc = QLabel("Larger, more visible focus outlines")
        ef_desc.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 10pt; margin-left: 26px;")
        display_layout.addWidget(ef_desc)

        # Dyslexia-Friendly Font
        self.dyslexia_font_cb = ToggleSwitch("Dyslexia-Friendly Font")
        self.dyslexia_font_cb.setAccessibleName("Dyslexia-friendly font")
        self.dyslexia_font_cb.setToolTip("Use OpenDyslexic font style")
        display_layout.addWidget(self.dyslexia_font_cb)
        df_desc = QLabel("Use OpenDyslexic font style with wider letter and word spacing")
        df_desc.setWordWrap(True)
        df_desc.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 10pt; margin-left: 26px;")
        display_layout.addWidget(df_desc)

        # Color Blindness Mode
        cb_row = QHBoxLayout()
        cb_label = QLabel("Color Blindness Mode:")
        cb_row.addWidget(cb_label)
        self.color_blind_combo = QComboBox()
        self.color_blind_combo.addItem("None (Default)", ColorBlindMode.NONE.value)
        self.color_blind_combo.addItem("Deuteranopia (Green-blind)", ColorBlindMode.DEUTERANOPIA.value)
        self.color_blind_combo.addItem("Protanopia (Red-blind)", ColorBlindMode.PROTANOPIA.value)
        self.color_blind_combo.addItem("Tritanopia (Blue-blind)", ColorBlindMode.TRITANOPIA.value)
        self.color_blind_combo.addItem("Monochrome (Grayscale)", ColorBlindMode.MONOCHROME.value)
        self.color_blind_combo.setAccessibleName("Color blindness mode")
        cb_row.addWidget(self.color_blind_combo)
        cb_row.addStretch()
        display_layout.addLayout(cb_row)

        # Custom Cursor
        cursor_row = QHBoxLayout()
        cursor_label = QLabel("Custom Cursor:")
        cursor_row.addWidget(cursor_label)
        self.custom_cursor_combo = QComboBox()
        self.custom_cursor_combo.addItem("System Default", CustomCursorStyle.DEFAULT.value)
        self.custom_cursor_combo.addItem("Large Black Cursor", CustomCursorStyle.LARGE_BLACK.value)
        self.custom_cursor_combo.addItem("Large White Cursor", CustomCursorStyle.LARGE_WHITE.value)
        self.custom_cursor_combo.addItem("Large Crosshair", CustomCursorStyle.LARGE_CROSSHAIR.value)
        self.custom_cursor_combo.addItem("High Visibility (Yellow/Black)", CustomCursorStyle.HIGH_VISIBILITY.value)
        self.custom_cursor_combo.addItem("Cursor Trail", CustomCursorStyle.CURSOR_TRAIL.value)
        self.custom_cursor_combo.setAccessibleName("Custom cursor style")
        cursor_row.addWidget(self.custom_cursor_combo)
        cursor_row.addStretch()
        display_layout.addLayout(cursor_row)

        # Connect live preview signals for instant feedback
        self.high_contrast_cb.toggled.connect(self._emit_preview)
        self.reduced_motion_cb.toggled.connect(self._emit_preview)
        self.large_text_cb.toggled.connect(self._emit_preview)
        self.enhanced_focus_cb.toggled.connect(self._emit_preview)
        self.dyslexia_font_cb.toggled.connect(self._emit_preview)
        self.color_blind_combo.currentIndexChanged.connect(self._emit_preview)
        self.custom_cursor_combo.currentIndexChanged.connect(self._emit_preview)

        layout.addWidget(display_group)

        # ── WCAG Compliance Level ───────────────────────────────
        wcag_group = QGroupBox("WCAG Compliance Level")
        wcag_layout = QVBoxLayout(wcag_group)

        self.wcag_level = QComboBox()
        self.wcag_level.addItem("Level A (Minimum)", WCAGLevel.A.value)
        self.wcag_level.addItem("Level AA (Recommended)", WCAGLevel.AA.value)
        self.wcag_level.addItem("Level AAA (Enhanced)", WCAGLevel.AAA.value)
        self.wcag_level.setCurrentIndex(1)
        self.wcag_level.setAccessibleName("WCAG compliance level")
        wcag_layout.addWidget(self.wcag_level)

        wcag_info = QLabel(
            "Level AA is recommended for most documents and is required "
            "for many legal and institutional compliance requirements."
        )
        wcag_info.setWordWrap(True)
        wcag_info.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY};")
        wcag_layout.addWidget(wcag_info)

        layout.addWidget(wcag_group)

        # ── Validation Checks ───────────────────────────────────
        checks_group = QGroupBox("Validation Checks")
        checks_layout = QVBoxLayout(checks_group)

        self.check_contrast_cb = ToggleSwitch("Check color contrast")
        self.check_contrast_cb.setChecked(True)
        checks_layout.addWidget(self.check_contrast_cb)

        self.check_headings_cb = ToggleSwitch("Check heading structure")
        self.check_headings_cb.setChecked(True)
        checks_layout.addWidget(self.check_headings_cb)

        self.check_alt_text_cb = ToggleSwitch("Check image alt text")
        self.check_alt_text_cb.setChecked(True)
        checks_layout.addWidget(self.check_alt_text_cb)

        self.check_tables_cb = ToggleSwitch("Check table accessibility")
        self.check_tables_cb.setChecked(True)
        checks_layout.addWidget(self.check_tables_cb)

        self.check_links_cb = ToggleSwitch("Check link text")
        self.check_links_cb.setChecked(True)
        checks_layout.addWidget(self.check_links_cb)

        self.check_reading_order_cb = ToggleSwitch("Check reading order")
        self.check_reading_order_cb.setChecked(True)
        checks_layout.addWidget(self.check_reading_order_cb)

        layout.addWidget(checks_group)

        # Connect remaining accessibility options to live preview
        self.wcag_level.currentIndexChanged.connect(self._emit_preview)
        self.check_contrast_cb.toggled.connect(self._emit_preview)
        self.check_headings_cb.toggled.connect(self._emit_preview)
        self.check_alt_text_cb.toggled.connect(self._emit_preview)
        self.check_tables_cb.toggled.connect(self._emit_preview)
        self.check_links_cb.toggled.connect(self._emit_preview)
        self.check_reading_order_cb.toggled.connect(self._emit_preview)

        layout.addStretch()
        return self._create_scroll_widget(container)

    def _create_ui_settings(self) -> QWidget:
        """Create UI settings panel."""
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
            }}
            QGroupBox {{
                font-size: 12pt;
                font-weight: bold;
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QLabel {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}
            QSpinBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}
            QComboBox {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                selection-background-color: {COLORS.PRIMARY};
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Theme
        theme_group = QGroupBox("Appearance")
        theme_layout = QVBoxLayout(theme_group)

        theme_row = QHBoxLayout()
        theme_label = QLabel("Theme:")
        theme_row.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("System Default", "system")
        self.theme_combo.addItem("Light", "light")
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.setAccessibleName("Application theme")
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()

        theme_layout.addLayout(theme_row)

        layout.addWidget(theme_group)

        # Font
        font_group = QGroupBox("Font Settings")
        font_layout = QVBoxLayout(font_group)

        font_row = QHBoxLayout()
        font_label = QLabel("Font Size:")
        font_row.addWidget(font_label)

        self.font_size = QSpinBox()
        self.font_size.setMinimum(MIN_FONT_SIZE)
        self.font_size.setMaximum(MAX_FONT_SIZE)
        self.font_size.setValue(12)
        self.font_size.setAccessibleName("Font size")
        font_row.addWidget(self.font_size)
        font_row.addStretch()

        font_layout.addLayout(font_row)
        layout.addWidget(font_group)

        # Editor
        editor_group = QGroupBox("Editor Settings")
        editor_layout = QVBoxLayout(editor_group)

        self.show_line_numbers_cb = ToggleSwitch("Show line numbers")
        self.show_line_numbers_cb.setChecked(True)
        editor_layout.addWidget(self.show_line_numbers_cb)

        self.auto_preview_cb = ToggleSwitch("Auto-update preview")
        self.auto_preview_cb.setChecked(True)
        editor_layout.addWidget(self.auto_preview_cb)

        layout.addWidget(editor_group)

        layout.addStretch()
        return self._create_scroll_widget(container)

    def _create_security_settings(self) -> QWidget:
        """Create security settings panel."""
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.BACKGROUND};
                color: {COLORS.TEXT_PRIMARY};
            }}
            QGroupBox {{
                font-size: 12pt;
                font-weight: bold;
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QLabel {{
                color: {COLORS.TEXT_PRIMARY};
                font-size: 12pt;
            }}
            QLineEdit {{
                background-color: {COLORS.INPUT_BG};
                color: {COLORS.INPUT_TEXT};
                border: 1px solid {COLORS.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 12pt;
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
                font-size: 12pt;
            }}
            QPushButton {{
                background-color: {COLORS.BACKGROUND_ALT};
                color: {COLORS.TEXT_PRIMARY};
                border: 1px solid {COLORS.BORDER};
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS.PRIMARY};
                color: white;
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Encryption
        encryption_group = QGroupBox("File Encryption")
        encryption_layout = QVBoxLayout(encryption_group)

        self.encrypt_files_cb = ToggleSwitch("Encrypt sensitive files at rest")
        self.encrypt_files_cb.setChecked(True)
        encryption_layout.addWidget(self.encrypt_files_cb)

        encryption_info = QLabel(
            "Files are encrypted using AES-256-GCM. "
            "This helps protect sensitive student/patient data."
        )
        encryption_info.setWordWrap(True)
        encryption_info.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY};")
        encryption_layout.addWidget(encryption_info)

        layout.addWidget(encryption_group)

        # Session
        session_group = QGroupBox("Session Settings")
        session_layout = QVBoxLayout(session_group)

        timeout_row = QHBoxLayout()
        timeout_label = QLabel("Auto-logout after (minutes):")
        timeout_row.addWidget(timeout_label)

        self.auto_logout = QSpinBox()
        self.auto_logout.setMinimum(5)
        self.auto_logout.setMaximum(120)
        self.auto_logout.setValue(30)
        self.auto_logout.setAccessibleName("Auto-logout time")
        timeout_row.addWidget(self.auto_logout)
        timeout_row.addStretch()

        session_layout.addLayout(timeout_row)

        self.require_password_cb = ToggleSwitch("Require password to access encrypted files")
        session_layout.addWidget(self.require_password_cb)

        layout.addWidget(session_group)

        # Password change
        password_group = QGroupBox("Change Password")
        password_layout = QVBoxLayout(password_group)

        self.current_password = QLineEdit()
        self.current_password.setPlaceholderText("Current password")
        self.current_password.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.current_password)

        self.new_password = QLineEdit()
        self.new_password.setPlaceholderText("New password")
        self.new_password.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.new_password)

        self.confirm_password = QLineEdit()
        self.confirm_password.setPlaceholderText("Confirm new password")
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.confirm_password)

        change_btn = QPushButton("Change Password")
        change_btn.clicked.connect(self._change_password)
        password_layout.addWidget(change_btn)

        layout.addWidget(password_group)

        layout.addStretch()
        return self._create_scroll_widget(container)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        self.setAccessibleName("Settings")
        self.setAccessibleDescription("Configure application settings")

    def _on_backend_changed(self) -> None:
        """Handle AI backend change (legacy - kept for compatibility)."""
        if hasattr(self, 'backend_combo'):
            backend = self.backend_combo.currentData()

            # Show/hide relevant settings
            self.ollama_group.setVisible(backend == AIBackend.OLLAMA.value)
            self.lmstudio_group.setVisible(backend == AIBackend.LM_STUDIO.value)
            self.gpt4all_group.setVisible(backend == AIBackend.GPT4ALL.value)

            # Show privacy warning for cloud backends
            is_cloud = backend in [AIBackend.OPENAI.value, AIBackend.ANTHROPIC.value]
            self.privacy_warning.setVisible(is_cloud)

            self.ai_backend_changed.emit(backend)

    def _on_ai_config_changed(self, ai_config: dict) -> None:
        """Handle AI configuration changes from the new panel."""
        self._config["ai"] = ai_config
        self.ai_backend_changed.emit(ai_config.get("local_provider") or ai_config.get("cloud_provider", "ollama"))

    def _test_ollama(self) -> None:
        """Test Ollama connection."""
        from ..core.ai_processor import OllamaProcessor

        url = self.ollama_url.text() or "http://localhost:11434"
        processor = OllamaProcessor({"ollama_url": url})

        if processor.is_available:
            QMessageBox.information(
                self,
                "Connection Successful",
                f"Successfully connected to Ollama at {url}",
            )
        else:
            QMessageBox.warning(
                self,
                "Connection Failed",
                f"Could not connect to Ollama at {url}\n\n"
                "Make sure Ollama is running.",
            )

    def _load_settings(self) -> None:
        """Load settings from database."""
        if not self._user or not self._db:
            return

        try:
            settings_json = self._db.get_setting(self._user.id, "config")
            if settings_json:
                self._config = json.loads(settings_json)
                self._apply_config_to_ui()
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")

    def _apply_config_to_ui(self) -> None:
        """Apply loaded config to UI controls."""
        self._loading_config = True
        ai = self._config.get("ai", {})

        # Apply AI config to the new panel
        if hasattr(self, '_ai_config_panel'):
            self._ai_config_panel.set_config(ai)

        # Processing
        proc = self._config.get("processing", {})
        self.batch_limit.setValue(proc.get("batch_limit", 5))
        self.auto_ocr_cb.setChecked(proc.get("auto_ocr", True))

        # Accessibility
        acc = self._config.get("accessibility", {})
        level = acc.get("wcag_level", WCAGLevel.AA.value)
        index = self.wcag_level.findData(level)
        if index >= 0:
            self.wcag_level.setCurrentIndex(index)

        self.check_contrast_cb.setChecked(acc.get("check_contrast", True))
        self.check_headings_cb.setChecked(acc.get("check_headings", True))
        self.check_alt_text_cb.setChecked(acc.get("check_alt_text", True))
        self.check_tables_cb.setChecked(acc.get("check_tables", True))
        self.check_links_cb.setChecked(acc.get("check_links", True))
        self.check_reading_order_cb.setChecked(acc.get("check_reading_order", True))

        # UI
        ui = self._config.get("ui", {})
        theme = ui.get("theme", "system")
        index = self.theme_combo.findData(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

        self.high_contrast_cb.setChecked(ui.get("high_contrast", False))
        self.reduced_motion_cb.setChecked(ui.get("reduced_motion", False))
        self.large_text_cb.setChecked(ui.get("large_text_mode", False))
        self.enhanced_focus_cb.setChecked(ui.get("enhanced_focus", False))
        self.dyslexia_font_cb.setChecked(ui.get("dyslexia_font", False))

        cb_mode = ui.get("color_blind_mode", ColorBlindMode.NONE.value)
        cb_idx = self.color_blind_combo.findData(cb_mode)
        if cb_idx >= 0:
            self.color_blind_combo.setCurrentIndex(cb_idx)

        cursor_style = ui.get("custom_cursor", CustomCursorStyle.DEFAULT.value)
        cursor_idx = self.custom_cursor_combo.findData(cursor_style)
        if cursor_idx >= 0:
            self.custom_cursor_combo.setCurrentIndex(cursor_idx)

        self.font_size.setValue(ui.get("font_size", 12))
        self.show_line_numbers_cb.setChecked(ui.get("show_line_numbers", True))
        self.auto_preview_cb.setChecked(ui.get("auto_preview", True))

        # Security
        sec = self._config.get("security", {})
        self.encrypt_files_cb.setChecked(sec.get("encrypt_files", True))
        self.auto_logout.setValue(sec.get("auto_logout_minutes", 30))
        self.require_password_cb.setChecked(sec.get("require_password", False))
        self._loading_config = False

    def _emit_preview(self, *_) -> None:
        """Emit current accessibility settings for instant live preview."""
        if self._loading_config:
            return
        preview_config = {
            "ui": {
                "high_contrast": self.high_contrast_cb.isChecked(),
                "reduced_motion": self.reduced_motion_cb.isChecked(),
                "large_text_mode": self.large_text_cb.isChecked(),
                "enhanced_focus": self.enhanced_focus_cb.isChecked(),
                "dyslexia_font": self.dyslexia_font_cb.isChecked(),
                "color_blind_mode": self.color_blind_combo.currentData(),
                "custom_cursor": self.custom_cursor_combo.currentData(),
            },
            "accessibility": {
                "wcag_level": self.wcag_level.currentData(),
                "check_contrast": self.check_contrast_cb.isChecked(),
                "check_headings": self.check_headings_cb.isChecked(),
                "check_alt_text": self.check_alt_text_cb.isChecked(),
                "check_tables": self.check_tables_cb.isChecked(),
                "check_links": self.check_links_cb.isChecked(),
                "check_reading_order": self.check_reading_order_cb.isChecked(),
            },
        }
        self.preview_requested.emit(preview_config)

    def _save_settings(self) -> None:
        """Save settings to database."""
        # Get AI config from the new panel
        ai_config = self._ai_config_panel.get_config() if hasattr(self, '_ai_config_panel') else self._config.get("ai", {})

        # Build config from UI
        self._config = {
            "ai": ai_config,
            "processing": {
                "batch_limit": self.batch_limit.value(),
                "auto_ocr": self.auto_ocr_cb.isChecked(),
                "ocr_language": self.ocr_language.currentData(),
                "preserve_original": self.preserve_original_cb.isChecked(),
            },
            "accessibility": {
                "wcag_level": self.wcag_level.currentData(),
                "check_contrast": self.check_contrast_cb.isChecked(),
                "check_headings": self.check_headings_cb.isChecked(),
                "check_alt_text": self.check_alt_text_cb.isChecked(),
                "check_tables": self.check_tables_cb.isChecked(),
                "check_links": self.check_links_cb.isChecked(),
                "check_reading_order": self.check_reading_order_cb.isChecked(),
            },
            "ui": {
                "theme": self.theme_combo.currentData(),
                "high_contrast": self.high_contrast_cb.isChecked(),
                "reduced_motion": self.reduced_motion_cb.isChecked(),
                "large_text_mode": self.large_text_cb.isChecked(),
                "enhanced_focus": self.enhanced_focus_cb.isChecked(),
                "dyslexia_font": self.dyslexia_font_cb.isChecked(),
                "color_blind_mode": self.color_blind_combo.currentData(),
                "custom_cursor": self.custom_cursor_combo.currentData(),
                "font_size": self.font_size.value(),
                "show_line_numbers": self.show_line_numbers_cb.isChecked(),
                "auto_preview": self.auto_preview_cb.isChecked(),
            },
            "security": {
                "encrypt_files": self.encrypt_files_cb.isChecked(),
                "auto_logout_minutes": self.auto_logout.value(),
                "require_password": self.require_password_cb.isChecked(),
            },
        }

        if self._user and self._db:
            try:
                self._db.set_setting(
                    self._user.id,
                    "config",
                    json.dumps(self._config),
                )
                QMessageBox.information(self, "Saved", "Settings saved successfully")
                self.settings_changed.emit(self._config)
            except Exception as e:
                logger.error(f"Failed to save settings: {e}")
                QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
        else:
            QMessageBox.information(
                self,
                "Settings Applied",
                "Settings applied for this session.\n"
                "Log in to save settings permanently.",
            )
            self.settings_changed.emit(self._config)

    def _change_password(self) -> None:
        """Handle password change."""
        if not self._user or not self._db:
            QMessageBox.warning(self, "Error", "Please log in first")
            return

        current = self.current_password.text()
        new = self.new_password.text()
        confirm = self.confirm_password.text()

        if not current or not new:
            QMessageBox.warning(self, "Error", "Please fill in all password fields")
            return

        if new != confirm:
            QMessageBox.warning(self, "Error", "New passwords do not match")
            return

        if len(new) < 6:
            QMessageBox.warning(self, "Error", "Password must be at least 6 characters")
            return

        # Verify current password
        user = self._db.authenticate_user(self._user.username, current)
        if not user:
            QMessageBox.warning(self, "Error", "Current password is incorrect")
            return

        # Update password
        if self._db.update_password(self._user.id, new):
            QMessageBox.information(self, "Success", "Password changed successfully")
            self.current_password.clear()
            self.new_password.clear()
            self.confirm_password.clear()
        else:
            QMessageBox.critical(self, "Error", "Failed to change password")

    def set_user(self, user: User) -> None:
        """Set the current user."""
        self._user = user
        self._db = DatabaseQueries()
        self._load_settings()

    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return self._config
