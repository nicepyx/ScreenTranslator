from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from ..constants import DEFAULT_TARGET_LANGUAGE
from .context import TranslationContext
from .entities import EntityProtector
from .glossary import GlossaryEngine
from .ocr_correction import OCRCorrector
from .translator import LocalTranslator

StatusCallback = Optional[Callable[[str], None]]


@dataclass(frozen=True)
class PipelineResult:
    source_text: str
    translated_text: str
    domains: tuple[str, ...]
    terminology_count: int
    context_count: int
    target_lang: str = DEFAULT_TARGET_LANGUAGE
    provider: str = ""
    partial: bool = False


class TranslationPipeline:
    CURRENT_MARKER = "【当前句】"

    def __init__(self, translator: LocalTranslator) -> None:
        self.translator = translator
        self.glossary = GlossaryEngine()
        self.corrector = OCRCorrector(self.glossary)
        self.entities = EntityProtector()
        self.context = TranslationContext(max_entries=10)

    def _prepare(self, source: str, domains: list[str], target_lang: str):
        # Existing curated terminology maps to Chinese. Do not inject Chinese terms when the user
        # chooses a different target language; entity protection remains useful in all directions.
        if target_lang == "zh":
            injected, used_terms = self.glossary.inject_terms(source, domains)
        else:
            injected, used_terms = source, []
        protected, entities = self.entities.protect(injected)
        return protected, entities, used_terms

    def translate_partial(self, text: str, source_lang: str, *, target_lang: str = DEFAULT_TARGET_LANGUAGE,
                          channel: str, status: StatusCallback = None) -> PipelineResult:
        source = " ".join(text.strip().split())
        if source_lang == target_lang:
            return PipelineResult(source, source, (), 0, 0, target_lang, self.translator.runtime_label(), True)
        snapshot = self.context.snapshot(channel, source_lang, target_lang)
        domains = self.glossary.detect_domains([*snapshot.get("recent_sources", []), source])
        protected, entities, used_terms = self._prepare(source, domains, target_lang)
        translated = self.translator.translate(
            protected, source_lang, target_lang, status=status, cache_namespace="partial", fast=True, fuzzy_cache=True
        )
        translated = self.entities.restore(translated, entities).strip()
        return PipelineResult(source, translated, tuple(domains), len(used_terms), 0, target_lang,
                              self.translator.runtime_label(), True)

    def translate(self, text: str, source_lang: str, *, target_lang: str = DEFAULT_TARGET_LANGUAGE,
                  channel: str, is_ocr: bool = False, use_context: bool = True,
                  status: StatusCallback = None) -> PipelineResult:
        source = self.corrector.correct(text) if is_ocr else " ".join(text.strip().split())
        if source_lang == target_lang:
            return PipelineResult(source, source, (), 0, 0, target_lang, self.translator.runtime_label(), False)

        snapshot = self.context.snapshot(channel, source_lang, target_lang)
        previous = self.context.compact_previous(channel, source_lang, target_lang, source) if use_context else []
        domains = self.glossary.detect_domains([*snapshot.get("recent_sources", []), source])
        block = source
        context_count = len(previous)
        if previous:
            block = "\n".join(previous) + f"\n{self.CURRENT_MARKER}\n" + source

        protected, entities, used_terms = self._prepare(block, domains, target_lang)
        if status:
            extras = []
            if context_count:
                extras.append(f"上下文 {context_count} 条")
            if used_terms:
                extras.append(f"术语 {len(used_terms)} 个")
            status("正在翻译…" + ("（" + "，".join(extras) + "）" if extras else ""))

        translated_block = self.translator.translate(
            protected, source_lang, target_lang, status=status,
            cache_namespace="ctx" if previous else "plain", fast=False, fuzzy_cache=not previous,
        )
        translated_block = self.entities.restore(translated_block, entities)
        translated = translated_block.strip()
        if previous:
            if self.CURRENT_MARKER in translated_block:
                translated = translated_block.split(self.CURRENT_MARKER, 1)[1].strip()
            else:
                current_protected, current_entities, current_terms = self._prepare(source, domains, target_lang)
                translated = self.translator.translate(
                    current_protected, source_lang, target_lang, status=status,
                    cache_namespace="plain", fast=False, fuzzy_cache=True,
                )
                translated = self.entities.restore(translated, current_entities).strip()
                used_terms = current_terms

        self.context.add(channel, source_lang, target_lang, source, translated, tuple(domains))
        return PipelineResult(source, translated, tuple(domains), len(used_terms), context_count,
                              target_lang, self.translator.runtime_label(), False)
