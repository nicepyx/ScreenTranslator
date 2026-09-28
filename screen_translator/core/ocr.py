from __future__ import annotations

from typing import List, Sequence

import numpy as np

from .ocr_base import OCRLine, OCRResult
from .ocr_router import OCRRouter
from .text_merge import SmartTextMerger


class OCRService:
    """Cross-platform OCR facade with native-first routing and smart line merging."""

    def __init__(self, min_score: float = 0.50) -> None:
        self.router = OCRRouter(min_score=min_score)
        self.merger = SmartTextMerger()
        self.last_backend = ""
        self.last_fallback = False
        self.last_confidence = 0.0

    def available_backends(self) -> list[tuple[str, str]]:
        return self.router.available_backends()

    def recognize(
        self,
        image_bgr: np.ndarray,
        quality: str = "balanced",
        *,
        source_lang: str = "auto",
        backend: str = "auto",
    ) -> List[OCRLine]:
        result: OCRResult = self.router.recognize(
            image_bgr,
            quality=quality,
            source_lang=source_lang,
            backend=backend,
        )
        self.last_backend = result.backend
        self.last_fallback = result.used_fallback
        self.last_confidence = result.confidence
        return list(result.lines)

    def to_text(self, lines: Sequence[OCRLine]) -> str:
        return self.merger.merge(lines)
