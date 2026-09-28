from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import threading
import time


@dataclass(frozen=True)
class StabilityResult:
    stable: bool
    text: str
    waited_ms: int


class StableTextDetector:
    """Debounce OCR text per channel to avoid translating typewriter-style reveals."""

    def __init__(self) -> None:
        self._states: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def observe(self, channel: str, text: str, debounce_ms: int) -> StabilityResult:
        normalized = self.normalize(text)
        now = time.monotonic()
        with self._lock:
            previous = self._states.get(channel)
            if previous is None:
                self._states[channel] = (normalized, now)
                return StabilityResult(debounce_ms <= 0, normalized, 0)
            previous_text, first_seen = previous
            if previous_text != normalized:
                # Treat tiny OCR punctuation/spacing jitter as the same visual text. Large changes
                # reset the debounce timer as expected for typewriter-style reveals.
                ratio = SequenceMatcher(None, previous_text, normalized).ratio()
                if ratio < 0.985:
                    self._states[channel] = (normalized, now)
                    return StabilityResult(debounce_ms <= 0, normalized, 0)
            elapsed = int((now - first_seen) * 1000)
            return StabilityResult(elapsed >= max(0, debounce_ms), normalized, elapsed)

    def reset(self, channel: str | None = None) -> None:
        with self._lock:
            if channel is None:
                self._states.clear()
            else:
                self._states.pop(channel, None)
