import re

from lingua import Language, LanguageDetectorBuilder

_JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff]")
_CHINESE_RE = re.compile(r"[\u3400-\u9fff]")
_KOREAN_RE = re.compile(r"[\uac00-\ud7af]")
_CYRILLIC_RE = re.compile(r"[\u0400-\u04ff]")
_FRENCH_ACCENT_RE = re.compile(r"[àâæçéèêëîïôœùûüÿÀÂÆÇÉÈÊËÎÏÔŒÙÛÜŸ]")
_FRENCH_HINTS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "est", "sont",
    "avec", "pour", "dans", "sur", "pas", "vous", "nous", "je", "tu", "il", "elle",
    "bonjour", "merci", "oui", "non", "où", "comment", "pourquoi", "france", "français",
}

_LANG_MAP = {
    Language.ENGLISH: "en",
    Language.FRENCH: "fr",
    Language.GERMAN: "de",
    Language.SPANISH: "es",
    Language.ITALIAN: "it",
    Language.PORTUGUESE: "pt",
}

_DETECTOR = LanguageDetectorBuilder.from_languages(*_LANG_MAP.keys()).build()


def detect_source_language(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "en"

    if _JAPANESE_RE.search(cleaned):
        return "ja"
    if _KOREAN_RE.search(cleaned):
        return "ko"
    if _CYRILLIC_RE.search(cleaned):
        return "ru"
    # Han characters without kana are treated as Simplified/Chinese for our current pack set.
    if _CHINESE_RE.search(cleaned):
        return "zh"
    if _FRENCH_ACCENT_RE.search(cleaned):
        return "fr"

    words = {w.lower().strip(".,!?;:'\"()[]{}") for w in cleaned.split()}
    if len(words & _FRENCH_HINTS) >= 2:
        return "fr"

    detected = _DETECTOR.detect_language_of(cleaned)
    return _LANG_MAP.get(detected, "en")
