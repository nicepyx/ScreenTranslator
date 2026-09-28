from __future__ import annotations

import re
from typing import Sequence

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from rapidocr import RapidOCR

from .ocr_base import OCRLine


class RapidOCRBackend:
    key = "rapid"
    label = "RapidOCR · 多语言兼容"

    def __init__(self, min_score: float = 0.50) -> None:
        self.min_score = min_score
        self._engine: RapidOCR | None = None

    def available(self) -> bool:
        return True

    def _ensure_engine(self) -> RapidOCR:
        if self._engine is None:
            self._engine = RapidOCR()
        return self._engine

    @staticmethod
    def _prepare_image(image_bgr: np.ndarray, quality: str) -> tuple[np.ndarray, float]:
        if quality == "fast":
            return image_bgr, 1.0
        scale = 1.5 if quality == "balanced" else 2.0
        rgb = image_bgr[:, :, ::-1]
        pil = Image.fromarray(rgb)
        pil = pil.resize(
            (max(1, int(pil.width * scale)), max(1, int(pil.height * scale))),
            Image.Resampling.LANCZOS,
        )
        pil = ImageEnhance.Contrast(pil).enhance(1.12 if quality == "balanced" else 1.20)
        if quality == "enhanced":
            pil = pil.filter(ImageFilter.SHARPEN)
        prepared_rgb = np.asarray(pil)
        return prepared_rgb[:, :, ::-1].copy(), scale

    @staticmethod
    def _looks_like_noise(text: str, score: float) -> bool:
        text = text.strip()
        if not text or score < 0.42:
            return True
        has_letter = bool(re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af\u0400-\u04ff]", text))
        if not has_letter:
            return True
        compact = re.sub(r"\s+", "", text)
        if len(compact) >= 8:
            strange = sum(
                1
                for ch in compact
                if not (
                    ch.isalnum()
                    or ch in "À-ÖØ-öø-ÿ"
                    or "\u3040" <= ch <= "\u30ff"
                    or "\u3400" <= ch <= "\u9fff"
                    or "\uac00" <= ch <= "\ud7af"
                    or "\u0400" <= ch <= "\u04ff"
                    or ch in ".,!?;:'\"-_/()[]{}%+&@#€$¥£·…—–、。！？：；（）【】「」『』"
                )
            )
            if strange / max(1, len(compact)) > 0.28:
                return True
        return False

    def recognize(
        self,
        image_bgr: np.ndarray,
        *,
        quality: str = "balanced",
        source_lang: str = "auto",
    ) -> Sequence[OCRLine]:
        prepared, scale = self._prepare_image(image_bgr, quality)
        result = self._ensure_engine()(prepared)
        if result is None or result.txts is None or result.boxes is None:
            return []
        score_floor = {
            "fast": self.min_score,
            "balanced": max(self.min_score, 0.52),
            "enhanced": max(self.min_score, 0.54),
        }.get(quality, self.min_score)
        scores = result.scores or [1.0] * len(result.txts)
        lines: list[OCRLine] = []
        for box, text, score in zip(result.boxes, result.txts, scores):
            text = re.sub(r"[ \t]+", " ", (text or "").strip())
            score = float(score)
            if not text or score < score_floor or self._looks_like_noise(text, score):
                continue
            box_tuple = tuple((float(p[0]) / scale, float(p[1]) / scale) for p in box)
            lines.append(OCRLine(text=text, score=score, box=box_tuple))
        lines.sort(key=lambda item: (item.top, item.left))
        return lines
