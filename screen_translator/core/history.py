from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3
import threading

from .paths import data_dir


@dataclass(frozen=True)
class HistoryEntry:
    id: int
    created_at: str
    mode: str
    source_lang: str
    target_lang: str
    source_text: str
    translated_text: str
    domains: str


class TranslationHistory:
    def __init__(self) -> None:
        self.path = data_dir() / "history.sqlite3"
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    source_lang TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    domains TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cols = {row[1] for row in conn.execute("PRAGMA table_info(history)").fetchall()}
            if "target_lang" not in cols:
                conn.execute("ALTER TABLE history ADD COLUMN target_lang TEXT NOT NULL DEFAULT 'zh'")

    def add(self, mode: str, source_lang: str, target_lang: str, source_text: str,
            translated_text: str, domains: str = "") -> HistoryEntry:
        created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO history(created_at, mode, source_lang, target_lang, source_text, translated_text, domains) "
                "VALUES(?,?,?,?,?,?,?)",
                (created, mode, source_lang, target_lang, source_text, translated_text, domains),
            )
            row_id = int(cur.lastrowid)
        return HistoryEntry(row_id, created, mode, source_lang, target_lang, source_text, translated_text, domains)

    def list(self, limit: int | None = None) -> list[HistoryEntry]:
        cols = "id,created_at,mode,source_lang,target_lang,source_text,translated_text,domains"
        sql = f"SELECT {cols} FROM history ORDER BY id ASC"
        params: tuple = ()
        if limit is not None:
            sql = f"SELECT {cols} FROM (SELECT * FROM history ORDER BY id DESC LIMIT ?) ORDER BY id ASC"
            params = (int(limit),)
        with self._lock, self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [HistoryEntry(*row) for row in rows]

    def clear(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM history")

    def export_txt(self, path: Path) -> None:
        entries = self.list()
        with Path(path).open("w", encoding="utf-8") as f:
            for e in entries:
                f.write(f"[{e.created_at}] {e.mode} {e.source_lang} → {e.target_lang}\n")
                f.write(e.source_text.strip() + "\n")
                f.write(e.translated_text.strip() + "\n\n")
