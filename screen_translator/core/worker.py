from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from .language import detect_source_language
from .ocr import OCRService
from .stability import StableTextDetector
from .text_pipeline import TranslationPipeline
from .model_manager import user_error_message


class WorkerSignals(QObject):
    status = Signal(str)
    finished = Signal(dict)
    failed = Signal(str)


class TranslationWorker(QRunnable):
    def __init__(
        self,
        image_bgr,
        source_mode: str,
        target_lang: str,
        ocr_quality: str,
        ocr_service: OCRService,
        pipeline: TranslationPipeline,
        previous_text: str = "",
        channel: str = "screen",
        *,
        ocr_backend: str = "auto",
        stable_detector: StableTextDetector | None = None,
        debounce_ms: int = 0,
        force: bool = False,
        allowed_languages: set[str] | None = None,
        task_id: int = 0,
    ) -> None:
        super().__init__()
        self.image_bgr = image_bgr
        self.source_mode = source_mode
        self.target_lang = target_lang
        self.ocr_quality = ocr_quality
        self.ocr_service = ocr_service
        self.pipeline = pipeline
        self.previous_text = previous_text.strip()
        self.channel = channel
        self.ocr_backend = ocr_backend
        self.stable_detector = stable_detector
        self.debounce_ms = int(debounce_ms)
        self.force = force
        self.allowed_languages = allowed_languages
        self.task_id = int(task_id)
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.status.emit("正在识别屏幕文字…")
            lines = self.ocr_service.recognize(
                self.image_bgr,
                self.ocr_quality,
                source_lang=self.source_mode,
                backend=self.ocr_backend,
            )
            raw_text = self.ocr_service.to_text(lines)
            if not raw_text:
                raise RuntimeError("没有识别到可靠文字，请缩小框选范围或切换 OCR 引擎/小字增强。")

            corrected = self.pipeline.corrector.correct(raw_text)
            if self.previous_text and corrected == self.previous_text:
                self.signals.finished.emit(
                    {
                        "_task_id": self.task_id,
                        "unchanged": True,
                        "source_text": corrected,
                        "lines": lines,
                        "ocr_backend": self.ocr_service.last_backend,
                    }
                )
                return

            if self.stable_detector is not None and not self.force and self.debounce_ms > 0:
                stable = self.stable_detector.observe(self.channel, corrected, self.debounce_ms)
                if not stable.stable:
                    self.signals.finished.emit(
                        {
                            "_task_id": self.task_id,
                            "pending": True,
                            "source_text": corrected,
                            "waited_ms": stable.waited_ms,
                            "lines": lines,
                            "ocr_backend": self.ocr_service.last_backend,
                        }
                    )
                    return

            source_lang = self.source_mode
            if source_lang == "auto":
                source_lang = detect_source_language(corrected)
                from ..constants import LANGUAGE_CATALOG
                name = LANGUAGE_CATALOG.get(source_lang, {}).get("label", source_lang)
                if self.allowed_languages is not None and source_lang not in self.allowed_languages:
                    raise RuntimeError(f"检测到 {name}，但该语言包尚未安装。请到“语言包”页面下载后重试。")
                self.signals.status.emit(f"检测为{name}，正在翻译…")
            else:
                self.signals.status.emit("正在翻译…")

            result = self.pipeline.translate(
                corrected,
                source_lang,
                target_lang=self.target_lang,
                channel=self.channel,
                is_ocr=True,
                use_context=True,
                status=lambda message: self.signals.status.emit(message),
            )
            self.signals.finished.emit(
                {
                    "_task_id": self.task_id,
                    "unchanged": False,
                    "pending": False,
                    "source_text": result.source_text,
                    "translated_text": result.translated_text,
                    "source_lang": source_lang,
                    "target_lang": self.target_lang,
                    "lines": lines,
                    "domains": list(result.domains),
                    "terminology_count": result.terminology_count,
                    "context_count": result.context_count,
                    "provider": result.provider,
                    "ocr_backend": self.ocr_service.last_backend,
                    "ocr_fallback": self.ocr_service.last_fallback,
                }
            )
        except Exception as exc:
            self.signals.failed.emit(user_error_message(exc))
