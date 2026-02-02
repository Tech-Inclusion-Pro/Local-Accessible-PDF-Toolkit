# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Accessible PDF Toolkit macOS application.
"""

import sys
from pathlib import Path

block_cipher = None

# Get the project root
project_root = Path(SPECPATH)
src_path = project_root / 'src'

# Collect all package data
datas = [
    (str(project_root / 'assets'), 'assets'),
    (str(src_path / 'accessible_pdf_toolkit'), 'accessible_pdf_toolkit'),
]

a = Analysis(
    [str(project_root / 'launcher.py')],
    pathex=[str(src_path)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'accessible_pdf_toolkit',
        'accessible_pdf_toolkit.main',
        'accessible_pdf_toolkit.utils',
        'accessible_pdf_toolkit.utils.constants',
        'accessible_pdf_toolkit.utils.logger',
        'accessible_pdf_toolkit.utils.file_operations',
        'accessible_pdf_toolkit.utils.version_control',
        'accessible_pdf_toolkit.database',
        'accessible_pdf_toolkit.database.models',
        'accessible_pdf_toolkit.database.encryption',
        'accessible_pdf_toolkit.database.queries',
        'accessible_pdf_toolkit.core',
        'accessible_pdf_toolkit.core.ai_processor',
        'accessible_pdf_toolkit.core.pdf_handler',
        'accessible_pdf_toolkit.core.ocr_engine',
        'accessible_pdf_toolkit.core.wcag_validator',
        'accessible_pdf_toolkit.core.html_generator',
        'accessible_pdf_toolkit.gui',
        'accessible_pdf_toolkit.gui.main_window',
        'accessible_pdf_toolkit.gui.tag_editor',
        'accessible_pdf_toolkit.gui.html_converter',
        'accessible_pdf_toolkit.gui.dashboard',
        'accessible_pdf_toolkit.gui.dashboard_panel',
        'accessible_pdf_toolkit.gui.pdf_viewer',
        'accessible_pdf_toolkit.gui.settings',
        'accessible_pdf_toolkit.gui.login_dialog',
        'accessible_pdf_toolkit.gui.widgets',
        'accessible_pdf_toolkit.gui.widgets.compliance_meter',
        'accessible_pdf_toolkit.gui.widgets.pdf_preview',
        'accessible_pdf_toolkit.gui.widgets.tag_tree',
        'accessible_pdf_toolkit.gui.widgets.accordion_section',
        'accessible_pdf_toolkit.gui.widgets.navigation_panel',
        'accessible_pdf_toolkit.gui.widgets.enhanced_pdf_viewer',
        'accessible_pdf_toolkit.gui.widgets.ai_suggestions_panel',
        'accessible_pdf_toolkit.gui.widgets.ai_config_panel',
        'accessible_pdf_toolkit.gui.widgets.tutorial_dialog',
        'accessible_pdf_toolkit.gui.dialogs',
        'accessible_pdf_toolkit.gui.dialogs.privacy_warning_dialog',
        'accessible_pdf_toolkit.core.ai_detection',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        'sqlalchemy',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.orm',
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.kdf',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.backends',
        'bcrypt',
        'PIL',
        'PIL.Image',
        'fitz',
        'pikepdf',
        'pytesseract',
        'httpx',
        'bs4',
        'lxml',
        'lxml.etree',
        'yaml',
        'pyqtgraph',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['gpt4all'],  # Exclude gpt4all to avoid issues
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Accessible PDF Toolkit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Accessible PDF Toolkit',
)

app = BUNDLE(
    coll,
    name='Accessible PDF Toolkit.app',
    icon=str(project_root / 'assets' / 'app_icon.icns'),
    bundle_identifier='com.accessible-pdf-toolkit.app',
    info_plist={
        'CFBundleName': 'Accessible PDF Toolkit',
        'CFBundleDisplayName': 'Accessible PDF Toolkit',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleIdentifier': 'com.accessible-pdf-toolkit.app',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': 'APDF',
        'LSMinimumSystemVersion': '10.15.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'PDF Document',
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Alternate',
                'LSItemContentTypes': ['com.adobe.pdf'],
            }
        ],
    },
)
