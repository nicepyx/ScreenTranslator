from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Optional

StatusCallback = Optional[Callable[[str], None]]


class TranslationProvider(ABC):
    key = "base"
    label = "Base"

    @property
    @abstractmethod
    def model_ready(self) -> bool: ...

    @abstractmethod
    def configure(self, **kwargs) -> None: ...

    @abstractmethod
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        *,
        status: StatusCallback = None,
        namespace: str = "plain",
        fast: bool = False,
        fuzzy_cache: bool = True,
    ) -> str: ...

    def runtime_label(self) -> str:
        return self.label
