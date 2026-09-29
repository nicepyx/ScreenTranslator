from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from .text_pipeline import TranslationPipeline
from .model_manager import user_error_message


class WordLookupSignals(QObject):
    finished = Signal(dict)
    failed = Signal(str)


class WordLookupWorker(QRunnable):
    def __init__(self, word: str, source_lang: str, target_lang: str,
                 pipeline: TranslationPipeline, context: str = "") -> None:
        super().__init__()
        self.word = word.strip()
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.pipeline = pipeline
        self.context = context.strip()
        self.signals = WordLookupSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.pipeline.translate(
                self.word,
                self.source_lang,
                target_lang=self.target_lang,
                channel="word_lookup",
                is_ocr=False,
                use_context=False,
            )
            self.signals.finished.emit({
                "term": self.word,
                "meaning": result.translated_text,
                "source_lang": self.source_lang,
                "target_lang": self.target_lang,
                "context": self.context,
            })
        except Exception as exc:
            self.signals.failed.emit(user_error_message(exc))
