from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

import numpy as np


@dataclass(frozen=True)
class OCRLine:
    text: str
    score: float
    box: tuple[tuple[float, float], ...]

    @property
    def left(self) -> float:
        return min(p[0] for p in self.box)

    @property
    def right(self) -> float:
        return max(p[0] for p in self.box)

    @property
    def top(self) -> float:
        return min(p[1] for p in self.box)

    @property
    def bottom(self) -> float:
        return max(p[1] for p in self.box)

    @property
    def width(self) -> float:
        return max(1.0, self.right - self.left)

    @property
    def height(self) -> float:
        return max(1.0, self.bottom - self.top)


@dataclass(frozen=True)
class OCRResult:
    lines: tuple[OCRLine, ...]
    backend: str
    confidence: float
    used_fallback: bool = False


class OCRBackend(Protocol):
    key: str
    label: str

    def available(self) -> bool: ...

    def recognize(
        self,
        image_bgr: np.ndarray,
        *,
        quality: str = "balanced",
        source_lang: str = "auto",
    ) -> Sequence[OCRLine]: ...
