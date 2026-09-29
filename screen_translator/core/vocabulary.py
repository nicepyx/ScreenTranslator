from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3
import threading

from .paths import data_dir


@dataclass(frozen=True)
class VocabularyEntry:
    id: int
    created_at: str
    source_lang: str
    target_lang: str
    term: str
    meaning: str
    context: str
    category: str


class VocabularyStore:
    def __init__(self) -> None:
        self.path = data_dir() / "vocabulary.sqlite3"
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vocabulary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    term TEXT NOT NULL,
                    meaning TEXT NOT NULL,
                    context TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT 'General',
                    UNIQUE(source_lang, target_lang, term)
                )
            """)

    def add(self, source_lang: str, target_lang: str, term: str, meaning: str,
            context: str = "", category: str = "General") -> VocabularyEntry:
        created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO vocabulary(created_at,source_lang,target_lang,term,meaning,context,category) "
                "VALUES(?,?,?,?,?,?,?) ON CONFLICT(source_lang,target_lang,term) DO UPDATE SET "
                "meaning=excluded.meaning, context=excluded.context, category=excluded.category",
                (created, source_lang, target_lang, term, meaning, context, category),
            )
            row = conn.execute(
                "SELECT id,created_at,source_lang,target_lang,term,meaning,context,category FROM vocabulary "
                "WHERE source_lang=? AND target_lang=? AND term=?",
                (source_lang, target_lang, term),
            ).fetchone()
        return VocabularyEntry(*row)

    def list(self) -> list[VocabularyEntry]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT id,created_at,source_lang,target_lang,term,meaning,context,category "
                "FROM vocabulary ORDER BY id DESC"
            ).fetchall()
        return [VocabularyEntry(*row) for row in rows]

    def remove(self, row_id: int) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM vocabulary WHERE id=?", (int(row_id),))
