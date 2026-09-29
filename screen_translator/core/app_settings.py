from __future__ import annotations

import json
import threading
from pathlib import Path

from .paths import data_dir


class AppSettings:
    """Small JSON-backed replacement for QSettings.

    v0.9 stores application preferences alongside the selected Screen Translator data root so
    custom data-path migration really carries settings/Profile state with it. On first run it
    imports existing v0.8 QSettings keys when available.
    """

    def __init__(self) -> None:
        self.path = data_dir() / "settings.json"
        self._lock = threading.RLock()
        self._data: dict[str, object] = {}
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text("utf-8"))
                if isinstance(raw, dict):
                    self._data = raw
            except Exception:
                self._data = {}
        elif not self._data:
            self._import_legacy_qsettings()
            self._flush()

    def _import_legacy_qsettings(self) -> None:
        try:
            from PySide6.QtCore import QSettings
            old = QSettings("Local", "ScreenTranslator")
            for key in old.allKeys():
                value = old.value(key)
                if isinstance(value, (str, int, float, bool)) or value is None:
                    self._data[str(key)] = value
                else:
                    self._data[str(key)] = str(value)
        except Exception:
            pass

    def value(self, key: str, default=None):
        with self._lock:
            return self._data.get(str(key), default)

    def setValue(self, key: str, value) -> None:
        if hasattr(value, "value") and not isinstance(value, (str, bytes)):
            try:
                value = value.value
            except Exception:
                pass
        if not isinstance(value, (str, int, float, bool, type(None), list, dict)):
            value = str(value)
        with self._lock:
            self._data[str(key)] = value
            self._flush()

    def allKeys(self) -> list[str]:
        with self._lock:
            return sorted(self._data)

    def sync(self) -> None:
        with self._lock:
            self._flush()

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(self.path)
