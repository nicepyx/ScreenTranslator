from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap


def pixel_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / "pixel"


def pixel_ui_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / "pixel_ui"


def _asset_path(name: str) -> Path:
    reference = pixel_dir().parent / "ui_target" / f"{name}.png"
    if reference.exists():
        return reference
    first = pixel_dir() / f"{name}.png"
    if first.exists():
        return first
    return pixel_ui_dir() / f"{name}.png"


def pixel_icon(name: str) -> QIcon:
    return QIcon(str(_asset_path(name)))


def pixel_pixmap(name: str, size: int = 72) -> QPixmap:
    pm = QPixmap(str(_asset_path(name)))
    if not pm.isNull():
        return pm.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
    return pm
