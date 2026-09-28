from __future__ import annotations

import io
import platform
from typing import Sequence

import numpy as np
from PIL import Image

from .ocr_base import OCRLine


_LANGS = {
    "zh": ["zh-Hans"],
    "en": ["en-US"],
    "fr": ["fr-FR", "en-US"],
    "ja": ["ja-JP", "en-US"],
    "de": ["de-DE", "en-US"],
    "es": ["es-ES", "en-US"],
    "ko": ["ko-KR", "en-US"],
    "it": ["it-IT", "en-US"],
    "pt": ["pt-PT", "en-US"],
    "ru": ["ru-RU", "en-US"],
    "auto": ["en-US", "fr-FR", "ja-JP", "zh-Hans"],
}


class MacVisionOCRBackend:
    key = "mac_vision"
    label = "macOS Vision OCR"

    def available(self) -> bool:
        if platform.system() != "Darwin":
            return False
        try:
            import Vision  # noqa: F401
            import Foundation  # noqa: F401
            return True
        except Exception:
            return False

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
            import Foundation
            import Vision

            rgb = image_bgr[:, :, ::-1]
            h, w = rgb.shape[:2]
            bio = io.BytesIO()
            Image.fromarray(rgb).save(bio, format="PNG")
            raw = bio.getvalue()
            data = Foundation.NSData.dataWithBytes_length_(raw, len(raw))

            req = Vision.VNRecognizeTextRequest.alloc().init()
            # 0 is accurate, 1 is fast in VNRequestTextRecognitionLevel.
            req.setRecognitionLevel_(1 if quality == "fast" else 0)
            preferred = _LANGS.get(source_lang, _LANGS["auto"])
            try:
                supported = set(req.supportedRecognitionLanguagesAndReturnError_(None)[0] or [])
                selected = [x for x in preferred if x in supported]
                if selected:
                    req.setRecognitionLanguages_(selected)
            except Exception:
                pass

            handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(data, None)
            ok, _err = handler.performRequests_error_([req], None)
            if not ok:
                return []
            lines: list[OCRLine] = []
            for obs in req.results() or []:
                candidates = obs.topCandidates_(1)
                if not candidates:
                    continue
                candidate = candidates[0]
                text = str(candidate.string() or "").strip()
                if not text:
                    continue
                confidence = float(candidate.confidence())
                rect = obs.boundingBox()
                left = float(rect.origin.x) * w
                width = float(rect.size.width) * w
                height = float(rect.size.height) * h
                # Vision coordinates are normalized with bottom-left origin.
                top = (1.0 - float(rect.origin.y) - float(rect.size.height)) * h
                right = left + width
                bottom = top + height
                lines.append(
                    OCRLine(
                        text=text,
                        score=confidence,
                        box=((left, top), (right, top), (right, bottom), (left, bottom)),
                    )
                )
            lines.sort(key=lambda item: (item.top, item.left))
            return lines
        except Exception:
            return []
