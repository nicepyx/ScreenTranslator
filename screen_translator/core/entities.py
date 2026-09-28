from __future__ import annotations

from dataclasses import dataclass
import re


_KNOWN_PLACES = {
    "Paris": "巴黎", "France": "法国", "Tokyo": "东京", "Japan": "日本",
    "London": "伦敦", "New York": "纽约", "United States": "美国",
    "China": "中国", "Beijing": "北京", "Shanghai": "上海", "Hong Kong": "香港",
    "Seoul": "首尔", "Korea": "韩国", "Germany": "德国", "Berlin": "柏林",
    "Switzerland": "瑞士", "Zurich": "苏黎世", "Europe": "欧洲",
}


@dataclass(frozen=True)
class ProtectedEntity:
    placeholder: str
    source: str
    restore: str


class EntityProtector:
    """Small rule-based name/place protector that keeps the app lightweight.

    Known place names are normalized to Chinese. Unknown multi-word proper names and
    honorific-bearing names are preserved instead of being freely translated.
    """

    def protect(self, text: str) -> tuple[str, list[ProtectedEntity]]:
        entities: list[tuple[str, str]] = []
        occupied: list[tuple[int, int]] = []

        # Known places first, longest first.
        for source, target in sorted(_KNOWN_PLACES.items(), key=lambda kv: len(kv[0]), reverse=True):
            for m in re.finditer(rf"\b{re.escape(source)}\b", text, flags=re.IGNORECASE):
                entities.append((m.group(0), target))
                occupied.append((m.start(), m.end()))

        def free(start: int, end: int) -> bool:
            return all(end <= s or start >= e for s, e in occupied)

        # Multi-word Latin proper names are safer to preserve than to translate literally.
        proper = re.compile(r"\b(?:[A-Z][a-zÀ-ÖØ-öø-ÿ'-]{1,}\s+){1,3}[A-Z][a-zÀ-ÖØ-öø-ÿ'-]{1,}\b")
        for m in proper.finditer(text):
            if free(m.start(), m.end()):
                entities.append((m.group(0), m.group(0)))
                occupied.append((m.start(), m.end()))

        # Single Latin names with common honorific/title context.
        titled = re.compile(r"\b(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Professor|President|Captain)\s+[A-Z][A-Za-z'-]+\b")
        for m in titled.finditer(text):
            if free(m.start(), m.end()):
                entities.append((m.group(0), m.group(0)))
                occupied.append((m.start(), m.end()))

        # Single Latin names in strong name-like contexts.
        contextual = re.compile(
            r"(?i:with|from|by|called|named|meet|ask|tell|find|follow|help)\s+([A-Z][a-zÀ-ÖØ-öø-ÿ'-]{2,})"
        )
        for m in contextual.finditer(text):
            start, end = m.start(1), m.end(1)
            if free(start, end):
                entities.append((m.group(1), m.group(1)))
                occupied.append((start, end))

        direct = re.compile(r"(?:^|[.!?]\s+)([A-Z][a-zÀ-ÖØ-öø-ÿ'-]{2,}),")
        for m in direct.finditer(text):
            start, end = m.start(1), m.end(1)
            if free(start, end):
                entities.append((m.group(1), m.group(1)))
                occupied.append((start, end))

        # Japanese names followed by an honorific.
        jp = re.compile(r"[一-龯ぁ-んァ-ヶA-Za-z]{2,12}(?:さん|ちゃん|くん|君|様|氏)")
        for m in jp.finditer(text):
            if free(m.start(), m.end()):
                entities.append((m.group(0), m.group(0)))
                occupied.append((m.start(), m.end()))

        output = text
        protected: list[ProtectedEntity] = []
        # Replace longest first to avoid overlaps. Simple text replacement is enough after span collection.
        for idx, (source, restore) in enumerate(sorted(entities, key=lambda x: len(x[0]), reverse=True)):
            placeholder = f"[ENT{idx}]"
            if source in output:
                output = output.replace(source, placeholder)
                protected.append(ProtectedEntity(placeholder, source, restore))
        return output, protected

    @staticmethod
    def restore(text: str, entities: list[ProtectedEntity]) -> str:
        output = text
        for entity in entities:
            # NLLB can add spaces inside bracket tokens; tolerate variants such as [ ENT0 ].
            match = re.fullmatch(r"\[ENT(\d+)\]", entity.placeholder)
            if match:
                pattern = rf"\[\s*ENT\s*{match.group(1)}\s*\]"
            else:
                pattern = re.escape(entity.placeholder)
            output = re.sub(pattern, entity.restore, output, flags=re.IGNORECASE)
        return output
