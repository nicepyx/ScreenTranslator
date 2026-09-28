from __future__ import annotations

from difflib import SequenceMatcher
import re

from .glossary import GlossaryEngine


_COMMON = {
    "FederaI": "Federal",
    "federaI": "federal",
    "Resenve": "Reserve",
    "rnarket": "market",
    "rnonetary": "monetary",
    "inflalion": "inflation",
    "interesl": "interest",
    "rnanagement": "management",
    "garne": "game",
    "darnage": "damage",
    "rnission": "mission",
    "pIayer": "player",
    "cIient": "client",
    "rnemory": "memory",
}


class OCRCorrector:
    def __init__(self, glossary: GlossaryEngine) -> None:
        self._vocab = sorted(glossary.vocabulary)

    @staticmethod
    def _normalize_spacing(text: str) -> str:
        text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\s+([,.;:!?])", r"\1", text)
        text = re.sub(r"([([{])\s+", r"\1", text)
        text = re.sub(r"\s+([)\]}])", r"\1", text)
        return text.strip()

    def _correct_token(self, token: str) -> str:
        if token in _COMMON:
            return _COMMON[token]
        clean = token.strip(".,!?;:'\"()[]{}")
        if len(clean) < 5 or not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ'-]+", clean):
            return token
        if not any(ch in clean for ch in "0O1Ilrnm"):
            return token
        best = clean
        best_ratio = 0.0
        lower = clean.lower()
        for candidate in self._vocab:
            if abs(len(candidate) - len(clean)) > 2:
                continue
            ratio = SequenceMatcher(None, lower, candidate.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best = candidate
        if best_ratio < 0.86 or best.lower() == lower:
            return token
        prefix = token[: len(token) - len(token.lstrip(".,!?;:'\"()[]{}"))]
        suffix = token[len(token.rstrip(".,!?;:'\"()[]{}")) :]
        return prefix + best + suffix

    def correct(self, text: str) -> str:
        text = self._normalize_spacing(text)
        for wrong, right in _COMMON.items():
            text = text.replace(wrong, right)
        lines = []
        for line in text.splitlines():
            tokens = [self._correct_token(tok) for tok in line.split(" ")]
            lines.append(" ".join(tokens))
        return "\n".join(lines).strip()
