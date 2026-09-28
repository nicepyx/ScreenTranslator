from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Iterable


@dataclass(frozen=True)
class GlossaryMatch:
    source: str
    target: str
    domain: str


class GlossaryEngine:
    """Built-in automatic terminology packs.

    There is intentionally no required manual glossary setup. The engine scans recent
    context, detects likely domains, and applies exact built-in terminology matches.
    Longer terms win over shorter terms.
    """

    def __init__(self) -> None:
        path = Path(__file__).resolve().parent.parent / "resources" / "builtin_glossaries.json"
        with path.open("r", encoding="utf-8") as f:
            self._data: dict = json.load(f)
        self._all_terms: list[tuple[str, str, str]] = []
        for domain, config in self._data.items():
            for source, target in config.get("terms", {}).items():
                self._all_terms.append((source, target, domain))
        self._all_terms.sort(key=lambda item: len(item[0]), reverse=True)

    @property
    def vocabulary(self) -> set[str]:
        words: set[str] = set()
        for source, _target, _domain in self._all_terms:
            for token in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'-]{3,}", source):
                words.add(token)
        return words

    def detect_domains(self, texts: Iterable[str], limit: int = 2) -> list[str]:
        corpus = " ".join(t for t in texts if t).lower()
        if not corpus.strip():
            return []
        scores: list[tuple[int, str]] = []
        for domain, config in self._data.items():
            score = 0
            for keyword in config.get("keywords", []):
                k = str(keyword).lower()
                if k and k in corpus:
                    score += 2 if " " in k else 1
            for source in config.get("terms", {}).keys():
                s = str(source).lower()
                if len(s) >= 4 and s in corpus:
                    score += 2
            if score:
                scores.append((score, domain))
        scores.sort(reverse=True)
        return [domain for _score, domain in scores[:limit]]

    @staticmethod
    def _pattern(source: str):
        flags = re.IGNORECASE if re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]", source) else 0
        escaped = re.escape(source)
        if re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9 .'-]+", source):
            escaped = rf"(?<!\w){escaped}(?!\w)"
        return re.compile(escaped, flags)

    def find_matches(self, text: str, domains: Iterable[str] | None = None) -> list[GlossaryMatch]:
        allowed = set(domains or ())
        matches: list[GlossaryMatch] = []
        for source, target, domain in self._all_terms:
            if allowed and domain not in allowed:
                continue
            if self._pattern(source).search(text):
                matches.append(GlossaryMatch(source, target, domain))
        return matches

    def inject_terms(self, text: str, domains: Iterable[str] | None = None) -> tuple[str, list[GlossaryMatch]]:
        """Replace known source terminology with its Chinese canonical form before NLLB.

        NLLB generally copies already-Chinese spans into Chinese output, which gives us a
        lightweight glossary constraint without requiring a second large model.
        """
        matches = self.find_matches(text, domains)
        output = text
        used: list[GlossaryMatch] = []
        for match in matches:
            pattern = self._pattern(match.source)
            if pattern.search(output):
                output = pattern.sub(match.target, output)
                used.append(match)
        return output, used
