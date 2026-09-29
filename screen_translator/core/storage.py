from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_dir

from ..constants import APP_ID


@dataclass(frozen=True)
class StorageBreakdown:
    models: int
    language_packs: int
    history: int
    cache: int
    profiles: int
    vocabulary: int
    other: int

    @property
    def total(self) -> int:
        return sum((self.models, self.language_packs, self.history, self.cache, self.profiles, self.vocabulary, self.other))


class StorageManager:
    """Bootstrap-aware data location manager.

    The location setting itself always lives in the platform default directory so moving the
    application's main data directory never makes the application forget where it was moved.
    """

    def __init__(self) -> None:
        self.bootstrap_root = Path(user_data_dir(APP_ID, "Local"))
        self.bootstrap_root.mkdir(parents=True, exist_ok=True)
        self.config_path = self.bootstrap_root / "storage.json"

    def _config(self) -> dict:
        if not self.config_path.exists():
            return {"mode": "standard", "custom_path": ""}
        try:
            data = json.loads(self.config_path.read_text("utf-8"))
            return data if isinstance(data, dict) else {"mode": "standard", "custom_path": ""}
        except Exception:
            return {"mode": "standard", "custom_path": ""}

    def mode(self) -> str:
        return str(self._config().get("mode", "standard"))

    def root(self) -> Path:
        cfg = self._config()
        if cfg.get("mode") == "custom" and cfg.get("custom_path"):
            path = Path(str(cfg["custom_path"])).expanduser()
        else:
            path = self.bootstrap_root
        path.mkdir(parents=True, exist_ok=True)
        return path

    def custom_path(self) -> str:
        return str(self._config().get("custom_path", ""))

    def set_standard(self) -> None:
        self.config_path.write_text(json.dumps({"mode":"standard", "custom_path":""}, indent=2), "utf-8")

    def set_custom(self, path: Path) -> None:
        path = Path(path).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"mode":"custom", "custom_path":str(path)}, ensure_ascii=False, indent=2),
            "utf-8",
        )

    @staticmethod
    def _size(path: Path) -> int:
        if not path.exists():
            return 0
        if path.is_file():
            try:
                return path.stat().st_size
            except OSError:
                return 0
        total = 0
        for p in path.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
        return total

    def breakdown(self, root: Path | None = None) -> StorageBreakdown:
        root = Path(root or self.root())
        known = {
            "models": self._size(root / "models"),
            "language_packs": self._size(root / "language_packs"),
            "history": self._size(root / "history.sqlite3"),
            "cache": self._size(root / "translations.sqlite3") + self._size(root / "cache"),
            "profiles": self._size(root / "profiles") + self._size(root / "settings.json"),
            "vocabulary": self._size(root / "vocabulary.sqlite3"),
        }
        total = self._size(root)
        other = max(0, total - sum(known.values()))
        return StorageBreakdown(other=other, **known)

    def migrate_to(self, destination: Path) -> tuple[Path, Path]:
        source = self.root().resolve()
        destination = Path(destination).expanduser().resolve()
        destination.mkdir(parents=True, exist_ok=True)
        if source == destination:
            self.set_custom(destination)
            return source, destination
        try:
            destination.relative_to(source)
            raise ValueError("新的数据目录不能位于当前数据目录内部，请选择其他文件夹。")
        except ValueError as exc:
            if str(exc).startswith("新的数据目录"):
                raise
        required = max(32 * 1024 * 1024, int(self._size(source) * 1.10))
        free = shutil.disk_usage(destination).free
        if free < required:
            raise OSError(f"目标磁盘空间不足：至少需要约 {format_bytes(required)} 可用空间。")
        # Copy first. Existing destination content is preserved unless a source file has the same name.
        for item in source.iterdir():
            # Never recursively copy the bootstrap storage pointer into a custom data location.
            if source == self.bootstrap_root and item.name == self.config_path.name:
                continue
            target = destination / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)
        self.set_custom(destination)
        return source, destination

    def clean_cache(self) -> int:
        root = self.root()
        removed = 0
        cache_db = root / "translations.sqlite3"
        if cache_db.exists():
            try:
                removed += cache_db.stat().st_size
                cache_db.unlink()
            except OSError:
                pass
        cache_dir = root / "cache"
        if cache_dir.exists():
            removed += self._size(cache_dir)
            shutil.rmtree(cache_dir, ignore_errors=True)
        return removed

    def open_root(self) -> None:
        path = self.root()
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys_platform() == "darwin":
            import subprocess
            subprocess.Popen(["open", str(path)])
        else:
            import subprocess
            subprocess.Popen(["xdg-open", str(path)])


def sys_platform() -> str:
    import sys
    return sys.platform


def format_bytes(value: int) -> str:
    n = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
