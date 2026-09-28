# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = [("screen_translator/resources/builtin_glossaries.json", "screen_translator/resources"), ("screen_translator/resources/pixel", "screen_translator/resources/pixel")]
binaries = []
hiddenimports = []

for package in [
    "rapidocr",
    "onnxruntime",
    "ctranslate2",
    "sentencepiece",
    "lingua",
    "huggingface_hub",
    "platformdirs",
    "psutil",
    "PIL",
    "faster_whisper",
    "soundcard",
    "pyaudiowpatch",
    "av",
    "cffi",
    "Quartz",
    "Vision",
    "winrt.windows.media.ocr",
    "winrt.windows.globalization",
    "winrt.windows.graphics.imaging",
    "winrt.windows.storage.streams",
    "mlx_whisper",
]:
    try:
        d, b, h = collect_all(package)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

hiddenimports += [
    "winrt.windows.media.ocr",
    "winrt.windows.globalization",
    "winrt.windows.graphics.imaging",
    "winrt.windows.storage.streams",
    "winrt.windows.foundation",
    "Vision",
    "mlx_whisper",
]

analysis = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="ScreenTranslator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon="screen_translator/resources/pixel/app_icon.ico" if sys.platform == "win32" else None,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=False,
    name="ScreenTranslator",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="ScreenTranslator.app",
        icon="screen_translator/resources/pixel/app_icon.icns",
        bundle_identifier="local.screentranslator.app",
        info_plist={
            "NSHighResolutionCapable": True,
            "LSUIElement": False,
            "NSMicrophoneUsageDescription": "Screen Translator uses microphone audio only for local speech recognition and translation.",
            "NSScreenCaptureUsageDescription": "Screen Translator captures selected screen areas for local OCR translation.",
            "NSHumanReadableCopyright": "Screen Translator v0.8.0",
        },
    )
