from __future__ import annotations

from typing import Callable, Optional

from ..providers import NLLBProvider, TranslationProvider
from ..constants import DEFAULT_TARGET_LANGUAGE
from .model_manager import ModelManager

StatusCallback = Optional[Callable[[str], None]]


class LocalTranslator:
    def __init__(self, model_manager: ModelManager | None = None) -> None:
        self._providers: dict[str, TranslationProvider] = {"nllb": NLLBProvider(model_manager)}
        self._active_key = "nllb"

    @property
    def active_provider(self) -> TranslationProvider:
        return self._providers[self._active_key]

    @property
    def model_ready(self) -> bool:
        return self.active_provider.model_ready

    def provider_keys(self) -> list[str]:
        return list(self._providers)

    def set_provider(self, key: str) -> None:
        if key not in self._providers:
            raise KeyError(key)
        self._active_key = key

    def register_provider(self, provider: TranslationProvider) -> None:
        self._providers[provider.key] = provider

    def configure(self, **kwargs) -> None:
        self.active_provider.configure(**kwargs)

    def translate(self, text: str, source_lang: str, target_lang: str = DEFAULT_TARGET_LANGUAGE,
                  status: StatusCallback = None, cache_namespace: str = "plain", *,
                  fast: bool = False, fuzzy_cache: bool = True) -> str:
        return self.active_provider.translate(
            text, source_lang, target_lang, status=status, namespace=cache_namespace,
            fast=fast, fuzzy_cache=fuzzy_cache,
        )

    def runtime_label(self) -> str:
        return self.active_provider.runtime_label()
