from __future__ import annotations

import os
import threading
from typing import Callable, Optional

import ctranslate2
import sentencepiece as spm

from ..constants import NLLB_LANGUAGE_CODES
from ..core.cache import TranslationCache
from ..core.models import TranslationModelManager
from ..core.model_manager import ModelManager
from .base import TranslationProvider

StatusCallback = Optional[Callable[[str], None]]


class NLLBProvider(TranslationProvider):
    key = "nllb"
    label = "NLLB-200 Local"

    def __init__(self, model_manager: ModelManager | None = None) -> None:
        self._manager = TranslationModelManager(model_manager)
        self._translator: ctranslate2.Translator | None = None
        self._sp: spm.SentencePieceProcessor | None = None
        self._lock = threading.Lock()
        self._cache = TranslationCache()
        self._cpu_threads = max(1, min(6, (os.cpu_count() or 4) - 1))
        self._beam_size = 2
        self._prefer_gpu = True
        self._device = "cpu"
        self._compute_type = "int8"
        self._gpu_failure: str = ""

    @property
    def model_ready(self) -> bool:
        return self._manager.is_ready()

    def configure(self, *, cpu_threads: int | None = None, beam_size: int | None = None,
                  prefer_gpu: bool | None = None, **_kwargs) -> None:
        new_threads = self._cpu_threads if cpu_threads is None else max(1, int(cpu_threads))
        new_beam = self._beam_size if beam_size is None else max(1, int(beam_size))
        new_gpu = self._prefer_gpu if prefer_gpu is None else bool(prefer_gpu)
        reload_required = new_threads != self._cpu_threads or new_gpu != self._prefer_gpu
        self._cpu_threads, self._beam_size, self._prefer_gpu = new_threads, new_beam, new_gpu
        if reload_required:
            self._translator = None

    def _make_translator(self, model_dir, status: StatusCallback = None) -> ctranslate2.Translator:
        if self._prefer_gpu:
            try:
                if ctranslate2.get_cuda_device_count() > 0:
                    if status:
                        status("检测到 CUDA，正在使用 GPU 加速翻译…")
                    tr = ctranslate2.Translator(str(model_dir), device="cuda", compute_type="auto",
                                                inter_threads=1, intra_threads=1)
                    self._device, self._compute_type, self._gpu_failure = "cuda", str(tr.compute_type), ""
                    return tr
            except Exception as exc:
                self._gpu_failure = str(exc)
                if status:
                    status("CUDA 翻译不可用，已自动回退 CPU。")
        tr = ctranslate2.Translator(str(model_dir), device="cpu", compute_type="int8",
                                    inter_threads=1, intra_threads=self._cpu_threads)
        self._device, self._compute_type = "cpu", str(tr.compute_type)
        return tr

    def _ensure_loaded(self, status: StatusCallback = None) -> None:
        if self._translator is not None and self._sp is not None:
            return
        model_dir = self._manager.local_path()
        if status:
            status("正在加载本地多语言翻译模型…")
        self._translator = self._make_translator(model_dir, status)
        if self._sp is None:
            self._sp = spm.SentencePieceProcessor(model_file=str(model_dir / "sentencepiece.bpe.model"))

    def translate(self, text: str, source_lang: str, target_lang: str, *, status: StatusCallback = None,
                  namespace: str = "plain", fast: bool = False, fuzzy_cache: bool = True) -> str:
        text = text.strip()
        if not text:
            return ""
        if source_lang == target_lang:
            return text
        if source_lang not in NLLB_LANGUAGE_CODES:
            raise ValueError(f"Unsupported source language: {source_lang}")
        if target_lang not in NLLB_LANGUAGE_CODES:
            raise ValueError(f"Unsupported target language: {target_lang}")

        cached = self._cache.get(source_lang, target_lang, text, namespace)
        if cached:
            return cached
        if fuzzy_cache:
            fuzzy = self._cache.get_fuzzy(source_lang, target_lang, text, namespace=namespace,
                                          threshold=0.985 if fast else 0.965)
            if fuzzy:
                return fuzzy[0]

        with self._lock:
            self._ensure_loaded(status)
            assert self._translator is not None and self._sp is not None
            src_code = NLLB_LANGUAGE_CODES[source_lang]
            tgt_code = NLLB_LANGUAGE_CODES[target_lang]
            pieces = self._sp.encode(text, out_type=str)
            source_tokens = [src_code, *pieces, "</s>"]
            beam = 1 if fast else self._beam_size
            max_len = min(512, max(48, int(len(pieces) * 2.7 + 24)))
            results = self._translator.translate_batch(
                [source_tokens], target_prefix=[[tgt_code]], beam_size=beam, max_decoding_length=max_len
            )
            output_tokens = [t for t in results[0].hypotheses[0] if t not in {tgt_code, "</s>"}]
            translated = self._sp.decode(output_tokens).strip()
            self._cache.put(source_lang, target_lang, text, translated, namespace)
            return translated

    def runtime_label(self) -> str:
        if self._device == "cuda":
            return f"NLLB · CUDA · {self._compute_type}"
        return f"NLLB · CPU · {self._compute_type}"
