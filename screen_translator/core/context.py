from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
import re
import threading


@dataclass(frozen=True)
class ContextEntry:
    source_lang: str
    target_lang: str
    source_text: str
    translated_text: str
    domains: tuple[str, ...] = ()


@dataclass
class ContextSession:
    entries: deque[ContextEntry]
    entities: Counter[str] = field(default_factory=Counter)
    domains: Counter[str] = field(default_factory=Counter)


class TranslationContext:
    _ENTITY_RE = re.compile(r"\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Professor\s+)?[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){0,2}\b")

    def __init__(self, max_entries: int = 10) -> None:
        self._max_entries = max(4, int(max_entries))
        self._sessions: dict[str, ContextSession] = {}
        self._lock = threading.Lock()

    def _session(self, channel: str) -> ContextSession:
        if channel not in self._sessions:
            self._sessions[channel] = ContextSession(deque(maxlen=self._max_entries))
        return self._sessions[channel]

    def recent_sources(self, channel: str, source_lang: str, target_lang: str, limit: int = 4) -> list[str]:
        with self._lock:
            items = list(self._session(channel).entries)
        return [e.source_text for e in items if e.source_lang == source_lang and e.target_lang == target_lang][-limit:]

    def snapshot(self, channel: str, source_lang: str, target_lang: str) -> dict:
        with self._lock:
            s = self._session(channel)
            entries = [e for e in s.entries if e.source_lang == source_lang and e.target_lang == target_lang]
            return {
                "recent_sources": [e.source_text for e in entries[-4:]],
                "recent_translations": [e.translated_text for e in entries[-4:]],
                "entities": [x for x, _ in s.entities.most_common(8)],
                "domains": [x for x, _ in s.domains.most_common(4)],
            }

    @staticmethod
    def needs_sentence_context(text: str, source_lang: str) -> bool:
        low = text.lower()
        if source_lang == "en":
            return bool(re.search(r"\b(he|she|it|they|him|her|them|this|that|these|those|former|latter)\b", low))
        if source_lang == "fr":
            return bool(re.search(r"\b(il|elle|ils|elles|lui|leur|ce|cet|cette|cela|ça|ceux|celles)\b", low))
        if source_lang in {"ja", "zh", "ko"}:
            return len(re.sub(r"\s+", "", text)) <= 36
        return False

    def compact_previous(self, channel: str, source_lang: str, target_lang: str, current: str) -> list[str]:
        if not self.needs_sentence_context(current, source_lang):
            return []
        previous = self.recent_sources(channel, source_lang, target_lang, limit=2)
        total, selected = 0, []
        for item in reversed(previous):
            if total + len(item) > 220:
                break
            selected.append(item)
            total += len(item)
        return list(reversed(selected))

    def add(self, channel: str, source_lang: str, target_lang: str, source_text: str,
            translated_text: str, domains: tuple[str, ...] = ()) -> None:
        source_text = source_text.strip()
        if not source_text:
            return
        with self._lock:
            session = self._session(channel)
            if session.entries and session.entries[-1].source_text == source_text and session.entries[-1].target_lang == target_lang:
                return
            session.entries.append(ContextEntry(source_lang, target_lang, source_text, translated_text.strip(), domains))
            for entity in self._ENTITY_RE.findall(source_text):
                session.entities[entity.strip()] += 1
            for domain in domains:
                session.domains[domain] += 1

    def clear(self, channel: str | None = None) -> None:
        with self._lock:
            if channel is None:
                self._sessions.clear()
            else:
                self._sessions.pop(channel, None)
