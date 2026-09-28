from __future__ import annotations

import asyncio
import platform
from typing import Sequence

import numpy as np

from .ocr_base import OCRLine


_LANG_TAGS = {
    "zh": "zh-CN",
    "en": "en-US",
    "fr": "fr-FR",
    "ja": "ja-JP",
    "de": "de-DE",
    "es": "es-ES",
    "ko": "ko-KR",
    "it": "it-IT",
    "pt": "pt-PT",
    "ru": "ru-RU",
}


class WindowsNativeOCRBackend:
    key = "windows_native"
    label = "Windows 原生 OCR"

    def available(self) -> bool:
        if platform.system() != "Windows":
            return False
        try:
            import winrt.windows.media.ocr  # noqa: F401
            import winrt.windows.graphics.imaging  # noqa: F401
            import winrt.windows.storage.streams  # noqa: F401
            return True
        except Exception:
            return False

    @staticmethod
    def _software_bitmap(image_bgr: np.ndarray):
        from winrt.windows.graphics.imaging import BitmapAlphaMode, BitmapPixelFormat, SoftwareBitmap
        from winrt.windows.storage.streams import DataWriter

        h, w = image_bgr.shape[:2]
        if image_bgr.ndim != 3 or image_bgr.shape[2] < 3:
            raise ValueError("Windows OCR expects a BGR image.")
        alpha = np.full((h, w, 1), 255, dtype=np.uint8)
        bgra = np.concatenate((image_bgr[:, :, :3], alpha), axis=2)
        bitmap = SoftwareBitmap(BitmapPixelFormat.BGRA8, int(w), int(h), BitmapAlphaMode.IGNORE)
        writer = DataWriter()
        writer.write_bytes(bgra.tobytes())
        bitmap.copy_from_buffer(writer.detach_buffer())
        return bitmap

    async def _recognize_async(self, image_bgr: np.ndarray, source_lang: str) -> list[OCRLine]:
        from winrt.windows.globalization import Language
        from winrt.windows.media.ocr import OcrEngine

        if source_lang in _LANG_TAGS:
            lang = Language(_LANG_TAGS[source_lang])
            engine = OcrEngine.try_create_from_language(lang)
        else:
            engine = OcrEngine.try_create_from_user_profile_languages()
        if engine is None:
            return []

        bitmap = self._software_bitmap(image_bgr)
        result = await engine.recognize_async(bitmap)
        lines: list[OCRLine] = []
        for line in result.lines:
            words = list(line.words)
            if not words:
                continue
            left = min(float(w.bounding_rect.x) for w in words)
            top = min(float(w.bounding_rect.y) for w in words)
            right = max(float(w.bounding_rect.x + w.bounding_rect.width) for w in words)
            bottom = max(float(w.bounding_rect.y + w.bounding_rect.height) for w in words)
            text = str(line.text or "").strip()
            if not text:
                continue
            lines.append(
                OCRLine(
                    text=text,
                    # WinRT does not expose per-line confidence. Use a neutral score so the
                    # router can still decide based on text length/script quality.
                    score=0.86,
                    box=((left, top), (right, top), (right, bottom), (left, bottom)),
                )
            )
        lines.sort(key=lambda item: (item.top, item.left))
        return lines

    def recognize(
        self,
        image_bgr: np.ndarray,
        *,
        quality: str = "balanced",
        source_lang: str = "auto",
    ) -> Sequence[OCRLine]:
        if not self.available():
            return []
        try:
            return asyncio.run(self._recognize_async(image_bgr, source_lang))
        except RuntimeError:
            # Worker threads should not normally have an active loop, but this keeps the backend
            # safe if embedded in another asyncio-based host.
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._recognize_async(image_bgr, source_lang))
            finally:
                loop.close()
        except Exception:
            return []
