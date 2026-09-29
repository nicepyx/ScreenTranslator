from __future__ import annotations

from PySide6.QtCore import QLocale


LOCALES = {
    "en": QLocale("en_US"),
    "fr": QLocale("fr_FR"),
    "ja": QLocale("ja_JP"),
    "zh": QLocale("zh_CN"),
    "de": QLocale("de_DE"),
    "es": QLocale("es_ES"),
    "ko": QLocale("ko_KR"),
    "it": QLocale("it_IT"),
    "pt": QLocale("pt_PT"),
    "ru": QLocale("ru_RU"),
}


class SpeechService:
    def __init__(self) -> None:
        self._tts = None
        try:
            from PySide6.QtTextToSpeech import QTextToSpeech
            self._tts = QTextToSpeech()
        except Exception:
            self._tts = None

    def available(self) -> bool:
        return self._tts is not None

    def speak(self, text: str, lang: str = "en") -> None:
        text = text.strip()
        if not text or self._tts is None:
            return
        try:
            locale = LOCALES.get(lang)
            if locale is not None:
                self._tts.setLocale(locale)
            self._tts.say(text)
        except Exception:
            pass
