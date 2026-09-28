from pathlib import Path

from platformdirs import user_data_dir

from ..constants import APP_ID


def data_dir() -> Path:
    path = Path(user_data_dir(APP_ID, "Local"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def models_dir() -> Path:
    path = data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_db_path() -> Path:
    return data_dir() / "translations.sqlite3"
