APP_NAME = "Screen Translator"
APP_ID = "ScreenTranslator"
APP_VERSION = "0.9.2"

LANGUAGE_CATALOG = {
    "zh": {"label": "简体中文", "native": "简体中文", "nllb": "zho_Hans", "core": True, "flag": "🇨🇳"},
    "en": {"label": "English", "native": "English", "nllb": "eng_Latn", "core": True, "flag": "🇺🇸"},
    "fr": {"label": "Français", "native": "Français", "nllb": "fra_Latn", "core": True, "flag": "🇫🇷"},
    "ja": {"label": "日本語", "native": "日本語", "nllb": "jpn_Jpan", "core": True, "flag": "🇯🇵"},
    "de": {"label": "Deutsch", "native": "Deutsch", "nllb": "deu_Latn", "core": False, "flag": "🇩🇪"},
    "es": {"label": "Español", "native": "Español", "nllb": "spa_Latn", "core": False, "flag": "🇪🇸"},
    "ko": {"label": "한국어", "native": "한국어", "nllb": "kor_Hang", "core": False, "flag": "🇰🇷"},
    "it": {"label": "Italiano", "native": "Italiano", "nllb": "ita_Latn", "core": False, "flag": "🇮🇹"},
    "pt": {"label": "Português", "native": "Português", "nllb": "por_Latn", "core": False, "flag": "🇵🇹"},
    "ru": {"label": "Русский", "native": "Русский", "nllb": "rus_Cyrl", "core": False, "flag": "🇷🇺"},
}

CORE_LANGUAGE_CODES = tuple(code for code, info in LANGUAGE_CATALOG.items() if info["core"])
EXTENDED_LANGUAGE_CODES = tuple(code for code, info in LANGUAGE_CATALOG.items() if not info["core"])

# Legacy constants are kept for compatibility. v0.9 fills the UI dynamically from LanguagePackManager.
SOURCE_LANGUAGES = {"auto": "自动检测", **{code: LANGUAGE_CATALOG[code]["label"] for code in CORE_LANGUAGE_CODES}}
TARGET_LANGUAGES = {code: LANGUAGE_CATALOG[code]["label"] for code in CORE_LANGUAGE_CODES}


REFRESH_PRESETS = [
    ("0.3 秒 · 低延迟（高占用）", 300),
    ("0.5 秒 · 很流畅（高占用）", 500),
    ("0.7 秒 · 高性能", 700),
    ("1.0 秒 · 推荐", 1000),
    ("1.5 秒 · 平衡", 1500),
    ("2.0 秒 · 省资源", 2000),
    ("3.0 秒 · 低占用", 3000),
    ("5.0 秒 · 最低占用", 5000),
]

OCR_QUALITY_PRESETS = [
    ("快速 · 原始分辨率", "fast"),
    ("推荐 · 小字增强", "balanced"),
    ("高精度 · 2× 放大（较高占用）", "enhanced"),
]

VAD_SENSITIVITY_PRESETS = [
    ("低 · 嘈杂环境更稳", "low"),
    ("标准 · 推荐", "normal"),
    ("高 · 小声对白更敏感", "high"),
]

WHISPER_MODEL_PRESETS = [
    ("Tiny · 最快 / 约 75MB", "tiny"),
    ("Base · 推荐 / 约 145MB", "base"),
    ("Small · 更准确 / 约 460MB", "small"),
]

# Performance profiles control quality/CPU budgets; v0.6 separately auto-detects CUDA/MLX acceleration.
PERFORMANCE_PROFILES = {
    "eco": {
        "label": "省资源",
        "refresh_ms": 2000,
        "ocr_quality": "fast",
        "whisper_model": "tiny",
        "vad_sensitivity": "low",
        "translation_beam": 1,
        "whisper_beam": 1,
        "max_cpu_threads": 4,
        "screen_change_threshold": 2.2,
        "stable_debounce_ms": 260,
        "partial_interval_ms": 1400,
        "vad_end_silence_ms": 520,
        "max_utterance_ms": 9000,
        "prefer_gpu": True,
        "description": "适合办公本、老款 Intel Mac 或后台运行。优先降低 CPU 占用。",
    },
    "balanced": {
        "label": "均衡",
        "refresh_ms": 1000,
        "ocr_quality": "balanced",
        "whisper_model": "base",
        "vad_sensitivity": "normal",
        "translation_beam": 2,
        "whisper_beam": 2,
        "max_cpu_threads": 6,
        "screen_change_threshold": 1.35,
        "stable_debounce_ms": 180,
        "partial_interval_ms": 1000,
        "vad_end_silence_ms": 420,
        "max_utterance_ms": 8000,
        "prefer_gpu": True,
        "description": "默认推荐。兼顾小字 OCR、声音识别准确率与响应速度。",
    },
    "high": {
        "label": "高性能",
        "refresh_ms": 700,
        "ocr_quality": "balanced",
        "whisper_model": "base",
        "vad_sensitivity": "normal",
        "translation_beam": 2,
        "whisper_beam": 2,
        "max_cpu_threads": 8,
        "screen_change_threshold": 0.9,
        "stable_debounce_ms": 120,
        "partial_interval_ms": 850,
        "vad_end_silence_ms": 360,
        "max_utterance_ms": 7000,
        "prefer_gpu": True,
        "description": "适合较新的 8 核以上 CPU / Apple Silicon。降低实时字幕延迟。",
    },
    "ultra": {
        "label": "极致",
        "refresh_ms": 500,
        "ocr_quality": "enhanced",
        "whisper_model": "small",
        "vad_sensitivity": "high",
        "translation_beam": 2,
        "whisper_beam": 2,
        "max_cpu_threads": 12,
        "screen_change_threshold": 0.65,
        "stable_debounce_ms": 80,
        "partial_interval_ms": 700,
        "vad_end_silence_ms": 320,
        "max_utterance_ms": 6500,
        "prefer_gpu": True,
        "description": "高占用模式。面向 12 核以上 CPU / 高配 Apple Silicon 与 32GB 级内存。",
    },
}

PERFORMANCE_PROFILE_ORDER = ["eco", "balanced", "high", "ultra"]

USAGE_MODES = {
    "general": {
        "label": "通用",
        "refresh_ms": 1000,
        "stable_debounce_ms": 180,
        "partial_enabled": True,
        "partial_interval_ms": 1000,
        "vad_end_silence_ms": 420,
        "max_utterance_ms": 8000,
        "ocr_quality": "balanced",
        "screen_change_threshold": 1.0,
    },
    "course": {
        "label": "实时课程 · 低延迟",
        "refresh_ms": 300,
        "stable_debounce_ms": 80,
        "partial_enabled": True,
        "partial_interval_ms": 750,
        "vad_end_silence_ms": 340,
        "max_utterance_ms": 6500,
        "ocr_quality": "fast",
        "screen_change_threshold": 0.35,
    },
    "game": {
        "label": "游戏字幕",
        "refresh_ms": 500,
        "stable_debounce_ms": 150,
        "partial_enabled": True,
        "partial_interval_ms": 900,
        "vad_end_silence_ms": 400,
        "max_utterance_ms": 7500,
        "ocr_quality": "balanced",
        "screen_change_threshold": 0.60,
    },
    "quality": {
        "label": "高质量",
        "refresh_ms": 1000,
        "stable_debounce_ms": 260,
        "partial_enabled": False,
        "partial_interval_ms": 1200,
        "vad_end_silence_ms": 520,
        "max_utterance_ms": 10000,
        "ocr_quality": "enhanced",
        "screen_change_threshold": 0.80,
    },
}


OVERLAY_POSITIONS = {
    "auto": "跟随选区",
    "top": "屏幕顶部",
    "bottom": "屏幕底部",
    "manual": "手动位置",
}

OVERLAY_ALIGNMENTS = {
    "left": "左对齐",
    "center": "居中",
    "right": "右对齐",
}

OVERLAY_WIDTHS = [
    ("跟随选区", "auto"),
    ("480 px", "480"),
    ("640 px · 推荐", "640"),
    ("800 px", "800"),
    ("1000 px", "1000"),
    ("手动调整", "manual"),
]

NLLB_LANGUAGE_CODES = {code: info["nllb"] for code, info in LANGUAGE_CATALOG.items()}
DEFAULT_TARGET_LANGUAGE = "zh"


# Quantized non-commercial build of Meta NLLB-200 distilled 600M.
# Override with SCREEN_TRANSLATOR_MODEL_REPO for testing another compatible CT2 repo.
DEFAULT_TRANSLATION_MODEL_REPO = "luigi000/nllb-200-distilled-600M-ct2-int8"
MODEL_SUBDIR = "nllb-200-distilled-600m-ct2-int8"

SUBTITLE_DISPLAY_MODES = [("只显示译文", "translation"), ("原文 + 译文", "bilingual")]

SUBTITLE_RECENT_COUNTS = [("最近 2 条", 2), ("最近 3 条 · 推荐", 3)]
SUBTITLE_RETENTION_MODES = [
    ("智能停留 · 推荐", "smart"),
    ("固定 3 秒", "fixed:3"),
    ("固定 5 秒", "fixed:5"),
    ("固定 8 秒", "fixed:8"),
    ("不自动隐藏", "keep"),
]

SUBTITLE_PRESETS = {
    "course": {
        "label": "网课 · 双语滚动",
        "display_mode": "bilingual",
        "recent_count": 3,
        "retention_mode": "smart",
        "opacity": 42,
        "translation_font": 22,
        "source_font": 15,
        "translation_color": "#FFFFFF",
        "source_color": "#D0D0D0",
        "outline_width": 2,
        "outline_color": "#000000",
        "shadow": True,
        "position": "bottom",
        "width": "800",
        "alignment": "center",
        "max_lines": 2,
        "smooth_updates": True,
    },
    "movie": {
        "label": "影视 · 白字黑描边",
        "display_mode": "translation",
        "recent_count": 2,
        "retention_mode": "smart",
        "opacity": 0,
        "translation_font": 24,
        "source_font": 14,
        "translation_color": "#FFFFFF",
        "source_color": "#D0D0D0",
        "outline_width": 2,
        "outline_color": "#000000",
        "shadow": True,
        "position": "bottom",
        "width": "800",
        "alignment": "center",
        "max_lines": 2,
        "smooth_updates": True,
    },
    "game": {
        "label": "游戏 · 低遮挡",
        "display_mode": "translation",
        "recent_count": 2,
        "retention_mode": "smart",
        "opacity": 28,
        "translation_font": 22,
        "source_font": 14,
        "translation_color": "#FFF7D6",
        "source_color": "#D0D0D0",
        "outline_width": 2,
        "outline_color": "#000000",
        "shadow": True,
        "position": "bottom",
        "width": "800",
        "alignment": "center",
        "max_lines": 2,
        "smooth_updates": True,
    },
    "minimal": {
        "label": "极简 · 无背景",
        "display_mode": "translation",
        "recent_count": 2,
        "retention_mode": "smart",
        "opacity": 0,
        "translation_font": 20,
        "source_font": 13,
        "translation_color": "#FFFFFF",
        "source_color": "#D0D0D0",
        "outline_width": 1,
        "outline_color": "#000000",
        "shadow": False,
        "position": "bottom",
        "width": "640",
        "alignment": "center",
        "max_lines": 2,
        "smooth_updates": True,
    },
}
SUBTITLE_MAX_LINES = [("自动", 0), ("1 行", 1), ("2 行 · 推荐", 2), ("3 行", 3)]
WINDOW_CROP_MODES = [("整个窗口", "full"), ("底部 40% · 游戏字幕推荐", "bottom40"), ("底部 25%", "bottom25")]
