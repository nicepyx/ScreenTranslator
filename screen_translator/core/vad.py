from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class VADConfig:
    sensitivity: str = "normal"  # low / normal / high
    min_speech_ms: int = 280
    end_silence_ms: int = 420
    pre_roll_ms: int = 220
    max_utterance_ms: int = 8000


class AdaptiveVAD:
    """Low-cost streaming VAD used before ASR.

    v0.6 exposes an active snapshot for provisional ASR, so subtitles can appear before the
    speaker finishes a sentence. Final segmentation still happens on silence or max duration.
    """

    def __init__(self, sample_rate: int = 16000, block_ms: int = 100, config: VADConfig | None = None) -> None:
        self.sample_rate = sample_rate
        self.block_ms = block_ms
        self.config = config or VADConfig()
        self._pre = deque(maxlen=max(1, self.config.pre_roll_ms // block_ms))
        self._active = False
        self._speech_blocks: list[np.ndarray] = []
        self._active_ms = 0
        self._silence_ms = 0
        self._noise_floor = 0.0025

    @property
    def active(self) -> bool:
        return self._active

    @property
    def active_ms(self) -> int:
        return self._active_ms

    @staticmethod
    def _rms(block: np.ndarray) -> float:
        if block.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(block.astype(np.float64, copy=False)))))

    def _threshold(self) -> float:
        multiplier = {"low": 4.2, "normal": 3.0, "high": 2.2}.get(self.config.sensitivity, 3.0)
        absolute = {"low": 0.007, "normal": 0.0048, "high": 0.0032}.get(self.config.sensitivity, 0.0048)
        return max(absolute, self._noise_floor * multiplier)

    def feed(self, block: np.ndarray) -> np.ndarray | None:
        block = np.asarray(block, dtype=np.float32).reshape(-1)
        rms = self._rms(block)
        speech = rms >= self._threshold()

        if not self._active:
            if not speech:
                self._noise_floor = self._noise_floor * 0.96 + rms * 0.04
                self._pre.append(block.copy())
                return None
            self._active = True
            self._speech_blocks = [*list(self._pre), block.copy()]
            self._pre.clear()
            self._active_ms = self.block_ms
            self._silence_ms = 0
            return None

        self._speech_blocks.append(block.copy())
        self._active_ms += self.block_ms
        if speech:
            self._silence_ms = 0
        else:
            self._silence_ms += self.block_ms

        should_end = (
            self._silence_ms >= self.config.end_silence_ms
            or self._active_ms >= self.config.max_utterance_ms
        )
        if not should_end:
            return None

        usable_ms = self._active_ms - self._silence_ms
        segment = np.concatenate(self._speech_blocks) if self._speech_blocks else np.empty((0,), dtype=np.float32)
        self._reset_active()
        if usable_ms < self.config.min_speech_ms:
            return None
        return segment

    def snapshot(self, *, min_ms: int = 700, max_ms: int = 5000) -> np.ndarray | None:
        if not self._active or self._active_ms < min_ms or not self._speech_blocks:
            return None
        audio = np.concatenate(self._speech_blocks)
        max_samples = int(self.sample_rate * max_ms / 1000)
        if audio.size > max_samples:
            audio = audio[-max_samples:]
        return audio.copy()

    def _reset_active(self) -> None:
        self._active = False
        self._speech_blocks = []
        self._active_ms = 0
        self._silence_ms = 0

    def flush(self) -> np.ndarray | None:
        if not self._active or not self._speech_blocks:
            return None
        segment = np.concatenate(self._speech_blocks)
        usable_ms = self._active_ms - self._silence_ms
        self._reset_active()
        return segment if usable_ms >= self.config.min_speech_ms else None
