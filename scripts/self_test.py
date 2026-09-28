from __future__ import annotations

import tempfile
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from screen_translator.core.context import TranslationContext
import screen_translator.core.cache as cache_module
from screen_translator.core.ocr_base import OCRLine
from screen_translator.core.stability import StableTextDetector
from screen_translator.core.text_merge import SmartTextMerger
from screen_translator.core.vad import AdaptiveVAD, VADConfig

import numpy as np


def check_merge() -> None:
    merger = SmartTextMerger()
    lines = [
        OCRLine("I don't", 0.99, ((10, 10), (140, 10), (140, 32), (10, 32))),
        OCRLine("think we should go.", 0.99, ((11, 36), (300, 36), (300, 60), (11, 60))),
    ]
    text = merger.merge(lines)
    assert "I don't think we should go." in text, text


def check_stability() -> None:
    detector = StableTextDetector()
    assert not detector.observe("test", "Hello", 35).stable
    time.sleep(0.05)
    assert detector.observe("test", "Hello", 35).stable
    detector.reset("test")


def check_context() -> None:
    context = TranslationContext(max_entries=8)
    context.add("game:a", "en", "zh", "John went home.", "John 回家了。", ("general",))
    previous = context.compact_previous("game:a", "en", "zh", "Tell him I am waiting.")
    assert previous and "John" in previous[-1]
    assert not context.compact_previous("game:a", "en", "zh", "Interest rates rose by 25 basis points.")



def check_fuzzy_cache() -> None:
    original = cache_module.cache_db_path
    with tempfile.TemporaryDirectory() as td:
        cache_module.cache_db_path = lambda: Path(td) / "cache.sqlite3"
        try:
            cache = cache_module.TranslationCache()
            cache.put("en", "zh", "What are you doing here?", "你在这里做什么？", "plain")
            hit = cache.get_fuzzy("en", "zh", "What are you doing here ?", namespace="plain", threshold=0.95)
            assert hit is not None and hit[0] == "你在这里做什么？"
            assert cache.get_fuzzy("en", "zh", "What are you doing here ?", namespace="partial", threshold=0.95) is None
            assert cache.get_fuzzy("en", "fr", "What are you doing here ?", namespace="plain", threshold=0.95) is None
        finally:
            cache_module.cache_db_path = original

def check_vad() -> None:
    sr = 16000
    vad = AdaptiveVAD(
        sample_rate=sr,
        block_ms=100,
        config=VADConfig(
            sensitivity="high",
            end_silence_ms=300,
            max_utterance_ms=3000,
        ),
    )
    speech = np.full(sr // 10, 0.20, dtype=np.float32)
    silence = np.zeros(sr // 10, dtype=np.float32)
    emitted = None
    for _ in range(8):
        emitted = vad.feed(speech) or emitted
    assert vad.active
    snap = vad.snapshot(min_ms=500, max_ms=2000)
    assert snap is not None and snap.size > 0
    for _ in range(5):
        out = vad.feed(silence)
        if out is not None:
            emitted = out
            break
    assert emitted is not None and emitted.size > 0


def main() -> None:
    check_merge()
    check_stability()
    check_context()
    check_fuzzy_cache()
    check_vad()
    print("Screen Translator v0.8 core self-test: PASS")


if __name__ == "__main__":
    main()
