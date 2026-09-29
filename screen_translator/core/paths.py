from pathlib import Path

from .storage import StorageManager


def data_dir() -> Path:
    return StorageManager().root()


def models_dir() -> Path:
    path = data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_db_path() -> Path:
    return data_dir() / "translations.sqlite3"
