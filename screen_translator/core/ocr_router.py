from __future__ import annotations

import platform
import re
from statistics import mean

import numpy as np

from .ocr_base import OCRLine, OCRResult
from .ocr_macos import MacVisionOCRBackend
from .ocr_rapid import RapidOCRBackend
from .ocr_windows import WindowsNativeOCRBackend


class OCRRouter:
    """Choose a low-latency native OCR backend first and fall back to RapidOCR."""

    def __init__(self, min_score: float = 0.50) -> None:
        self.rapid = RapidOCRBackend(min_score=min_score)
        self.windows = WindowsNativeOCRBackend()
        self.macos = MacVisionOCRBackend()

    def available_backends(self) -> list[tuple[str, str]]:
        options = [("auto", "自动 · 原生优先 / RapidOCR 回退")]
        if self.windows.available():
            options.append((self.windows.key, self.windows.label))
        if self.macos.available():
            options.append((self.macos.key, self.macos.label))
        options.append((self.rapid.key, self.rapid.label))
        return options

    @staticmethod
    def _quality(lines: list[OCRLine]) -> float:
        if not lines:
            return 0.0
        text = " ".join(line.text for line in lines)
        chars = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af\u0400-\u04ff]", text)
        useful = min(1.0, len(chars) / 20.0)
        avg = mean([max(0.0, min(1.0, line.score)) for line in lines])
        return avg * 0.7 + useful * 0.3

    def _native(self):
        system = platform.system()
        if system == "Windows" and self.windows.available():
            return self.windows
        if system == "Darwin" and self.macos.available():
            return self.macos
        return None

    def recognize(
        self,
        image_bgr: np.ndarray,
        *,
        quality: str = "balanced",
        source_lang: str = "auto",
        backend: str = "auto",
    ) -> OCRResult:
        if backend == "rapid":
            lines = list(self.rapid.recognize(image_bgr, quality=quality, source_lang=source_lang))
            return OCRResult(tuple(lines), self.rapid.key, self._quality(lines), False)

        explicit = {
            self.windows.key: self.windows,
            self.macos.key: self.macos,
        }.get(backend)
        if explicit is not None:
            lines = list(explicit.recognize(image_bgr, quality=quality, source_lang=source_lang))
            if lines:
                return OCRResult(tuple(lines), explicit.key, self._quality(lines), False)
            fallback = list(self.rapid.recognize(image_bgr, quality=quality, source_lang=source_lang))
            return OCRResult(tuple(fallback), self.rapid.key, self._quality(fallback), True)

        native = self._native()
        if native is not None:
            native_lines = list(native.recognize(image_bgr, quality=quality, source_lang=source_lang))
            native_quality = self._quality(native_lines)
            # For explicit source languages the native engine is normally strong enough at a
            # moderate score. Auto-language mode uses a slightly higher bar because WinRT is not
            # genuinely multilingual in a single pass.
            threshold = 0.62 if source_lang == "auto" else 0.50
            if native_lines and native_quality >= threshold:
                return OCRResult(tuple(native_lines), native.key, native_quality, False)

        rapid_lines = list(self.rapid.recognize(image_bgr, quality=quality, source_lang=source_lang))
        return OCRResult(tuple(rapid_lines), self.rapid.key, self._quality(rapid_lines), native is not None)
