from __future__ import annotations

from difflib import SequenceMatcher
import re
import sqlite3
import threading
from typing import Optional

from .paths import cache_db_path


class TranslationCache:
    """Persistent exact + fuzzy cache keyed by source AND target language."""

    def __init__(self) -> None:
        self._path = cache_db_path()
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    @staticmethod
    def normalize(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s+([,.!?;:，。！？；：])", r"\1", text)
        return text

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS translations_v3 (
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    normalized_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(source_lang, target_lang, namespace, source_text)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_translations_v3_norm "
                "ON translations_v3(source_lang, target_lang, namespace, normalized_text)"
            )

    def get(self, source_lang: str, target_lang: str, source_text: str, namespace: str = "plain") -> Optional[str]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT translated_text FROM translations_v3 "
                "WHERE source_lang=? AND target_lang=? AND namespace=? AND source_text=?",
                (source_lang, target_lang, namespace, source_text),
            ).fetchone()
        return row[0] if row else None

    def get_fuzzy(
        self,
        source_lang: str,
        target_lang: str,
        source_text: str,
        *,
        namespace: str = "plain",
        threshold: float = 0.965,
        limit: int = 120,
    ) -> Optional[tuple[str, float]]:
        normalized = self.normalize(source_text)
        if len(normalized) < 8:
            return None
        low = max(1, int(len(normalized) * 0.78))
        high = int(len(normalized) * 1.22) + 2
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT normalized_text, translated_text
                FROM translations_v3
                WHERE source_lang=? AND target_lang=? AND namespace=?
                  AND length(normalized_text) BETWEEN ? AND ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (source_lang, target_lang, namespace, low, high, int(limit)),
            ).fetchall()
        best: tuple[str, float] | None = None
        for candidate, translated in rows:
            score = SequenceMatcher(None, normalized, candidate).ratio()
            if score >= threshold and (best is None or score > best[1]):
                best = (translated, score)
        return best

    def put(
        self,
        source_lang: str,
        target_lang: str,
        source_text: str,
        translated_text: str,
        namespace: str = "plain",
    ) -> None:
        normalized = self.normalize(source_text)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO translations_v3(
                    source_lang, target_lang, namespace, source_text, normalized_text, translated_text, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(source_lang, target_lang, namespace, source_text)
                DO UPDATE SET translated_text=excluded.translated_text,
                              normalized_text=excluded.normalized_text,
                              updated_at=CURRENT_TIMESTAMP
                """,
                (source_lang, target_lang, namespace, source_text, normalized, translated_text),
            )
