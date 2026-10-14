# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification for AI Suite v1.0.

This spec uses dynamic hook utilities to automatically collect required C-extensions 
(DLLs) and data files without hardcoding paths to developer virtual environments.
"""

import os
from PyInstaller.utils.hooks import collect_dynamic_libs

block_cipher = None


# =============================================================================
# 1. DEPENDENCY COLLECTION (Hidden Imports)
# =============================================================================
# PyInstaller cannot statically analyze modules loaded via importlib or 
# factory patterns. We explicitly declare them here.
hiddenimports = [
    'ai_suite',
    'jarvis_ai',
    'friday_ai',
    'shared',
    'shared.config',
    'shared.config.settings_manager',
    'shared.config.secrets_manager',
    'ultralytics',          # YOLOv8 Vision pipeline
    'torch',
    'torchvision',
    'sklearn',
    'pandas',
    'numpy',
    'vosk',                 # Offline STT pipeline
    'pyaudio',              # Microphone capture pipeline
    'onnxruntime',          # SFace recognition pipeline
    'pycaw',                # Windows volume automation
    'pygame',               # Edge-TTS audio playback
    'edge_tts',             # Cloud TTS pipeline
    'pyttsx3',              # Offline TTS fallback
    'cv2',                  # OpenCV (Computer Vision)
    'ai_suite.ui.boot.boot_controller', # Boot sequence dynamic loading
    'ai_suite.ui.onboarding_wizard',    # Explicit onboarding packaging
    'shared.logger',         # Centralized logging
    'fitz',                  # PyMuPDF for PDF parsing/generation
    'docx',                  # python-docx for DOCX parsing/generation
    'pptx',                  # python-pptx for PPTX parsing/generation
    'openpyxl',              # openpyxl for XLSX reading
    'reportlab',             # reportlab for PDF generation
]

# =============================================================================
# 2. DYNAMIC LIBRARIES (Binaries)
# =============================================================================
# Automatically locate and bundle complex C++ DLLs (FFmpeg, ONNX, Vosk).
binaries = []
binaries += collect_dynamic_libs('cv2')
binaries += collect_dynamic_libs('vosk')

# ONNX Runtime ships with CUDA and TensorRT providers.
# We explicitly include them to preserve GPU acceleration for SFace.
ort_binaries = collect_dynamic_libs('onnxruntime')
binaries += ort_binaries

# =============================================================================
# 3. ASSETS (Datas)
# =============================================================================
# Bundle the UI assets folder. 
# NOTE: The models/ directory is intentionally omitted to keep the bundle small.
# The external models/ folder will be read dynamically by ResourceManager.
datas = [
    ('assets', 'assets'),
]

# =============================================================================
# 4. BLOAT REDUCTION (Excludes)
# =============================================================================
# Aggressively exclude unused massive packages often dragged in by dependencies.
excludes = [
    'nltk',
    'tkinter',
    'IPython',
    'jupyter',
    'notebook',
]

# =============================================================================
# 5. ICON DISCOVERY
# =============================================================================
# Use a custom .ico if available, otherwise fallback to default PyInstaller icon.
# Placeholder: Drop your production 'app_icon.ico' into assets/logo/
ICON_PATH = 'assets/logo/app_icon.ico'
icon_config = ICON_PATH if os.path.exists(ICON_PATH) else None


# =============================================================================
# PYINSTALLER ANALYSIS & BUNDLE GENERATION
# =============================================================================

a = Analysis(
    ['ai_suite/main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# PyInstaller hooks (e.g. hook-onnxruntime.py) automatically inject their own 
# DLLs into a.binaries. We must forcefully purge the GPU providers here.
a.binaries = [
    x for x in a.binaries 
    if 'onnxruntime_providers_tensorrt' not in x[0].lower()
]

pyz = PYZ(
    a.pure, 
    a.zipped_data, 
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AI Suite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False, # Compress executables if UPX is installed
    console=False, # Ensure NO console window is shown
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_config,
    version='version_info.txt'
)

# Compile into a directory (--onedir mode)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AI Suite',
)



