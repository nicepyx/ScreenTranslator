from __future__ import annotations

import queue
import threading
import time

import numpy as np
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from .audio import AudioTranscriber, mono_float32, open_audio_recorder, resample_audio
from .text_pipeline import TranslationPipeline
from .vad import AdaptiveVAD, VADConfig
from .model_manager import user_error_message
from ..constants import LANGUAGE_CATALOG


class AudioWorkerSignals(QObject):
    status = Signal(str)
    transcript = Signal(dict)
    failed = Signal(str)
    stopped = Signal()


class AudioTranslationWorker(QRunnable):
    """Three-stage low-latency audio pipeline.

    Capture/VAD, ASR and translation run independently. Partial ASR/translation can update the
    overlay while the speaker is still talking; final ASR then replaces the provisional subtitle.
    """

    SAMPLE_RATE = 16000
    SUPPORTED_LANGS = set(LANGUAGE_CATALOG)

    def __init__(
        self,
        *,
        kind: str,
        device_key: str,
        source_mode: str,
        target_lang: str,
        model_size: str,
        transcriber: AudioTranscriber,
        pipeline: TranslationPipeline,
        vad_sensitivity: str = "normal",
        partial_enabled: bool = True,
        partial_interval_ms: int = 1000,
        end_silence_ms: int = 420,
        max_utterance_ms: int = 8000,
        allowed_languages: set[str] | None = None,
    ) -> None:
        super().__init__()
        self.kind = kind
        self.device_key = device_key
        self.source_mode = source_mode
        self.target_lang = target_lang
        self.model_size = model_size
        self.transcriber = transcriber
        self.pipeline = pipeline
        self.vad_sensitivity = vad_sensitivity
        self.partial_enabled = bool(partial_enabled)
        self.partial_interval_ms = max(600, int(partial_interval_ms))
        self.end_silence_ms = max(250, int(end_silence_ms))
        self.max_utterance_ms = max(3000, int(max_utterance_ms))
        self.allowed_languages = allowed_languages
        self.signals = AudioWorkerSignals()
        self._stop_event = threading.Event()
        self._last_final_text = ""
        self._finalized: set[int] = set()
        self._state_lock = threading.Lock()

    def stop(self) -> None:
        self._stop_event.set()

    def _capture_loop(self, audio_queue, ready, metadata, capture_error) -> None:
        try:
            with open_audio_recorder(self.device_key, self.kind) as recorder:
                native_rate = int(getattr(recorder, "sample_rate", self.SAMPLE_RATE))
                metadata["sample_rate"] = native_rate
                block_frames = max(320, int(native_rate * 0.10))
                ready.set()
                while not self._stop_event.is_set():
                    block = recorder.record(block_frames)
                    if self._stop_event.is_set():
                        break
                    try:
                        audio_queue.put(block, timeout=0.03)
                    except queue.Full:
                        try:
                            audio_queue.get_nowait()
                        except queue.Empty:
                            pass
                        try:
                            audio_queue.put_nowait(block)
                        except queue.Full:
                            pass
        except BaseException as exc:
            capture_error.append(exc)
            ready.set()

    @staticmethod
    def _drop_stale_partials(q: queue.Queue, utterance_id: int) -> None:
        kept = []
        try:
            while True:
                item = q.get_nowait()
                if item is None:
                    kept.append(item)
                elif not (item.get("utterance_id") == utterance_id and item.get("partial")):
                    kept.append(item)
        except queue.Empty:
            pass
        for item in kept:
            try:
                q.put_nowait(item)
            except queue.Full:
                break

    def _enqueue_asr(self, q: queue.Queue, job: dict) -> None:
        if job["partial"]:
            self._drop_stale_partials(q, job["utterance_id"])
            try:
                q.put_nowait(job)
            except queue.Full:
                # Provisional captions are disposable. Never let them block capture/VAD.
                return
            return

        # Final utterances are not disposable. Drop pending partials, then briefly backpressure the
        # segmentation thread instead of spinning on a queue that already contains final jobs.
        self._drop_stale_partials(q, job["utterance_id"])
        deadline = time.monotonic() + (2.0 if self._stop_event.is_set() else 8.0)
        while time.monotonic() < deadline:
            try:
                q.put(job, timeout=0.12)
                return
            except queue.Full:
                continue

    def _asr_loop(self, asr_queue: queue.Queue, translation_queue: queue.Queue) -> None:
        try:
            while not self._stop_event.is_set() or not asr_queue.empty():
                try:
                    job = asr_queue.get(timeout=0.15)
                except queue.Empty:
                    continue
                if job is None:
                    break
                uid = int(job["utterance_id"])
                partial = bool(job["partial"])
                with self._state_lock:
                    if partial and uid in self._finalized:
                        continue
                text, lang, probability = self.transcriber.transcribe(
                    job["audio"],
                    self.source_mode,
                    self.model_size,
                    status=lambda message: self.signals.status.emit(message),
                    partial=partial,
                )
                text = " ".join(text.split())
                if not text or lang not in self.SUPPORTED_LANGS:
                    continue
                if self.allowed_languages is not None and lang not in self.allowed_languages:
                    from ..constants import LANGUAGE_CATALOG
                    name = LANGUAGE_CATALOG.get(lang, {}).get("label", lang)
                    self.signals.failed.emit(f"检测到 {name}，但该语言包尚未安装。请到“语言包”页面下载后重试。")
                    self._stop_event.set()
                    return
                payload = {
                    "utterance_id": uid,
                    "partial": partial,
                    "source_text": text,
                    "source_lang": lang,
                    "language_probability": probability,
                }
                if partial:
                    # Partial results may be dropped under load; the upcoming final result is the
                    # correctness boundary. This keeps slow machines responsive instead of building
                    # an ever-growing provisional backlog.
                    try:
                        translation_queue.put(payload, timeout=0.03)
                    except queue.Full:
                        pass
                else:
                    deadline = time.monotonic() + (2.0 if self._stop_event.is_set() else 8.0)
                    while time.monotonic() < deadline:
                        try:
                            translation_queue.put(payload, timeout=0.12)
                            break
                        except queue.Full:
                            continue
        except Exception as exc:
            self.signals.failed.emit(user_error_message(exc))
            self._stop_event.set()

    def _translation_loop(self, translation_queue: queue.Queue) -> None:
        last_partial: dict[int, str] = {}
        try:
            while not self._stop_event.is_set() or not translation_queue.empty():
                try:
                    item = translation_queue.get(timeout=0.15)
                except queue.Empty:
                    continue
                if item is None:
                    break
                uid = int(item["utterance_id"])
                partial = bool(item["partial"])
                text = str(item["source_text"])
                lang = str(item["source_lang"])
                with self._state_lock:
                    if partial and uid in self._finalized:
                        continue
                if partial and last_partial.get(uid) == text:
                    continue
                if partial:
                    last_partial[uid] = text
                    result = self.pipeline.translate_partial(
                        text,
                        lang,
                        target_lang=self.target_lang,
                        channel="audio",
                        status=lambda message: self.signals.status.emit(message),
                    )
                else:
                    if text == self._last_final_text:
                        continue
                    self._last_final_text = text
                    result = self.pipeline.translate(
                        text,
                        lang,
                        target_lang=self.target_lang,
                        channel="audio",
                        is_ocr=False,
                        use_context=True,
                        status=lambda message: self.signals.status.emit(message),
                    )
                    with self._state_lock:
                        self._finalized.add(uid)
                    last_partial.pop(uid, None)
                self.signals.transcript.emit(
                    {
                        "utterance_id": uid,
                        "partial": partial,
                        "source_text": result.source_text,
                        "translated_text": result.translated_text,
                        "source_lang": lang,
                        "target_lang": self.target_lang,
                        "language_probability": float(item.get("language_probability", 0.0)),
                        "domains": list(result.domains),
                        "terminology_count": result.terminology_count,
                        "context_count": result.context_count,
                        "provider": result.provider,
                        "asr_backend": self.transcriber.runtime_label(),
                    }
                )
                self.signals.status.emit(
                    "正在监听声音…（流式临时字幕 + VAD 自动断句）"
                    if self.partial_enabled else "正在监听声音…（VAD 自动断句）"
                )
        except Exception as exc:
            self.signals.failed.emit(user_error_message(exc))
            self._stop_event.set()

    @Slot()
    def run(self) -> None:
        threads: list[threading.Thread] = []
        try:
            self.signals.status.emit("正在打开音频设备…")
            audio_queue: queue.Queue = queue.Queue(maxsize=100)
            asr_queue: queue.Queue = queue.Queue(maxsize=8)
            translation_queue: queue.Queue = queue.Queue(maxsize=8)
            ready = threading.Event()
            metadata: dict = {}
            capture_error: list[BaseException] = []

            capture_thread = threading.Thread(
                target=self._capture_loop,
                args=(audio_queue, ready, metadata, capture_error),
                daemon=True,
                name="ScreenTranslatorAudioCapture",
            )
            asr_thread = threading.Thread(
                target=self._asr_loop,
                args=(asr_queue, translation_queue),
                daemon=True,
                name="ScreenTranslatorASR",
            )
            translate_thread = threading.Thread(
                target=self._translation_loop,
                args=(translation_queue,),
                daemon=True,
                name="ScreenTranslatorAudioTranslate",
            )
            threads = [capture_thread, asr_thread, translate_thread]
            for thread in threads:
                thread.start()

            ready.wait(timeout=8.0)
            if capture_error:
                raise capture_error[0]
            if "sample_rate" not in metadata:
                raise RuntimeError("音频设备打开超时。")

            native_rate = int(metadata["sample_rate"])
            vad = AdaptiveVAD(
                sample_rate=self.SAMPLE_RATE,
                block_ms=100,
                config=VADConfig(
                    sensitivity=self.vad_sensitivity,
                    end_silence_ms=self.end_silence_ms,
                    max_utterance_ms=self.max_utterance_ms,
                ),
            )
            self.signals.status.emit("正在监听声音…（流式临时字幕 + VAD 自动断句）")
            utterance_id = 1
            last_partial_ms = 0

            while not self._stop_event.is_set():
                if capture_error:
                    raise capture_error[0]
                try:
                    block = audio_queue.get(timeout=0.15)
                except queue.Empty:
                    continue
                audio = mono_float32(block)
                if native_rate != self.SAMPLE_RATE:
                    audio = resample_audio(audio, native_rate, self.SAMPLE_RATE)
                frame_len = self.SAMPLE_RATE // 10
                offset = 0
                while offset + frame_len <= audio.size:
                    segment = vad.feed(audio[offset : offset + frame_len])
                    offset += frame_len
                    if self.partial_enabled and vad.active:
                        if vad.active_ms >= 800 and vad.active_ms - last_partial_ms >= self.partial_interval_ms:
                            snapshot = vad.snapshot(min_ms=700, max_ms=5000)
                            if snapshot is not None and snapshot.size:
                                self._enqueue_asr(
                                    asr_queue,
                                    {
                                        "utterance_id": utterance_id,
                                        "partial": True,
                                        "audio": snapshot,
                                    },
                                )
                                last_partial_ms = vad.active_ms
                    if segment is not None and segment.size:
                        self._enqueue_asr(
                            asr_queue,
                            {
                                "utterance_id": utterance_id,
                                "partial": False,
                                "audio": segment,
                            },
                        )
                        utterance_id += 1
                        last_partial_ms = 0

            tail = vad.flush()
            if tail is not None and tail.size:
                self._enqueue_asr(
                    asr_queue,
                    {"utterance_id": utterance_id, "partial": False, "audio": tail},
                )
        except Exception as exc:
            self.signals.failed.emit(user_error_message(exc))
        finally:
            self._stop_event.set()
            # Shutdown in pipeline order. The ASR sentinel must come before the translation
            # sentinel; otherwise Translation could exit while ASR is still producing finals.
            asr_q = locals().get("asr_queue")
            translation_q = locals().get("translation_queue")
            capture_thread = locals().get("capture_thread")
            asr_thread = locals().get("asr_thread")
            translate_thread = locals().get("translate_thread")

            if capture_thread is not None:
                capture_thread.join(timeout=1.0)

            if asr_q is not None:
                try:
                    asr_q.put(None, timeout=0.5)
                except Exception:
                    pass
            if asr_thread is not None:
                asr_thread.join(timeout=3.0)

            if translation_q is not None:
                try:
                    translation_q.put(None, timeout=0.5)
                except Exception:
                    pass
            if translate_thread is not None:
                translate_thread.join(timeout=3.0)
            self.signals.stopped.emit()
