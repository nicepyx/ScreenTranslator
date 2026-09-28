from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap


def pixel_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / "pixel"


def pixel_icon(name: str) -> QIcon:
    return QIcon(str(pixel_dir() / f"{name}.png"))


def pixel_pixmap(name: str, size: int = 72) -> QPixmap:
    pm = QPixmap(str(pixel_dir() / f"{name}.png"))
    if not pm.isNull():
        return pm.scaled(size, size)
    return pm
