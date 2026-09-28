from __future__ import annotations

import re
from statistics import median
from typing import Sequence

from .ocr_base import OCRLine

_SENTENCE_END = re.compile(r"[.!?。！？…]['\"”’）)】』」]?$")
_NO_SPACE_BEFORE = set(",.!?;:%)]}，。！？：；、）》】」』")
_NO_SPACE_AFTER = set("([{（《【「『")


class SmartTextMerger:
    """Rebuild OCR rows into readable paragraphs without flattening true columns.

    The heuristics are intentionally conservative: nearby rows with similar left edges are
    merged when the previous row looks like a wrapped sentence. Large vertical gaps or strong
    x-axis jumps become paragraph breaks. CJK rows are joined without an inserted space.
    """

    def merge(self, lines: Sequence[OCRLine]) -> str:
        if not lines:
            return ""
        ordered = sorted(lines, key=lambda x: (x.top, x.left))
        heights = [x.height for x in ordered if x.height > 0]
        typical_h = median(heights) if heights else 20.0

        groups: list[list[OCRLine]] = []
        current: list[OCRLine] = []
        for line in ordered:
            if not current:
                current = [line]
                continue
            prev = current[-1]
            gap_y = line.top - prev.bottom
            left_delta = abs(line.left - prev.left)
            overlap_x = max(0.0, min(line.right, prev.right) - max(line.left, prev.left))
            overlap_ratio = overlap_x / max(1.0, min(line.width, prev.width))

            paragraph_break = gap_y > typical_h * 1.15
            different_column = left_delta > max(90.0, typical_h * 4.5) and overlap_ratio < 0.15
            if paragraph_break or different_column:
                groups.append(current)
                current = [line]
            else:
                current.append(line)
        if current:
            groups.append(current)

        paragraphs = [self._merge_group(group, typical_h) for group in groups]
        return "\n".join(p for p in paragraphs if p).strip()

    def _merge_group(self, lines: Sequence[OCRLine], typical_h: float) -> str:
        if not lines:
            return ""
        parts: list[str] = []
        for i, line in enumerate(lines):
            text = " ".join(line.text.strip().split())
            if not text:
                continue
            if not parts:
                parts.append(text)
                continue

            prev = parts[-1]
            prev_line = lines[max(0, i - 1)]
            gap_y = line.top - prev_line.bottom
            # Keep a newline after a completed sentence if the visual gap is meaningful.
            hard_break = bool(_SENTENCE_END.search(prev)) and gap_y > typical_h * 0.35
            if hard_break:
                parts.append("\n" + text)
            else:
                parts.append(self._joiner(prev, text) + text)
        return "".join(parts).strip()

    @staticmethod
    def _has_cjk(text: str) -> bool:
        return bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", text))

    def _joiner(self, left: str, right: str) -> str:
        if not left or not right:
            return ""
        if left[-1] in _NO_SPACE_AFTER or right[0] in _NO_SPACE_BEFORE:
            return ""
        if self._has_cjk(left[-2:]) or self._has_cjk(right[:2]):
            return ""
        if left.endswith("-") and right[:1].islower():
            return ""
        return " "
