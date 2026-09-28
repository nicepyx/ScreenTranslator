from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .paths import data_dir


class GameProfileStore:
    """Per-window/game settings stored outside the application folder."""

    def __init__(self) -> None:
        self.root = data_dir() / "profiles"
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _slug(key: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", key.strip())[:96].strip("_.")
        if not cleaned:
            cleaned = "window"
        # Include a deterministic suffix to avoid title collisions.
        import hashlib

        digest = hashlib.sha1(key.encode("utf-8", errors="ignore")).hexdigest()[:8]
        return f"{cleaned}_{digest}"

    def path_for(self, key: str) -> Path:
        return self.root / f"{self._slug(key)}.json"

    def load(self, key: str) -> dict[str, Any]:
        if not key:
            return {}
        path = self.path_for(key)
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text("utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save(self, key: str, data: dict[str, Any]) -> None:
        if not key:
            return
        path = self.path_for(key)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(path)
