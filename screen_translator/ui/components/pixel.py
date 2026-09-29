"""Text is rendered by Qt; only empty plates and icons come from PNG art."""
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QComboBox, QPushButton, QSizePolicy, QWidget

from ..assets import pixel_pixmap
from ..theme import BUTTON_HEIGHT, INPUT_HEIGHT, COLOR_OUTLINE

ASSET_ROOT = Path(__file__).resolve().parents[2] / "resources" / "ui_target"


@lru_cache(maxsize=48)
def plate(name: str) -> QPixmap:
    result = QPixmap(str(ASSET_ROOT / f"{name}.png"))
    if result.isNull():
        raise FileNotFoundError(f"Missing pixel asset: {name}")
    return result


def draw_nine_slice(painter: QPainter, rect: QRect, image: QPixmap, source_inset: int = 10, border: int = 6) -> None:
    """Keep corners at a logical size; stretch only edges and the empty centre."""
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
    sx = (0, source_inset, image.width() - source_inset, image.width())
    sy = (0, source_inset, image.height() - source_inset, image.height())
    dx = (rect.left(), rect.left() + border, rect.right() + 1 - border, rect.right() + 1)
    dy = (rect.top(), rect.top() + border, rect.bottom() + 1 - border, rect.bottom() + 1)
    for row in range(3):
        for col in range(3):
            painter.drawPixmap(QRect(dx[col], dy[row], dx[col + 1] - dx[col], dy[row + 1] - dy[row]), image,
                               QRect(sx[col], sy[row], sx[col + 1] - sx[col], sy[row + 1] - sy[row]))


class PixelNineSliceFrame(QWidget):
    def __init__(self, asset="card", parent=None, *, inset=10, border=8):
        super().__init__(parent)
        self.asset, self.inset, self.border = asset, inset, border

    def paintEvent(self, event):
        painter = QPainter(self)
        draw_nine_slice(painter, self.rect(), plate(self.asset), self.inset, self.border)


class PixelCard(PixelNineSliceFrame):
    pass


class PixelDecoration(QWidget):
    def __init__(self, path: Path, parent=None):
        super().__init__(parent)
        self.pixmap = QPixmap(str(path))
        self.setMinimumHeight(70)
        self.setMaximumHeight(108)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        size = self.pixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        target = QRect((self.width() - size.width()) // 2, (self.height() - size.height()) // 2, size.width(), size.height())
        painter.drawPixmap(target, self.pixmap)


class PixelButton(QPushButton):
    def __init__(self, text="", icon=None, parent=None, *, primary=False):
        super().__init__(text, parent)
        self.primary = primary
        self.flat = False
        self.art_icon = pixel_pixmap(icon, 24) if icon else QPixmap()
        self.setMinimumHeight(BUTTON_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.setProperty("pixelPainted", True)

    def sizeHint(self):
        icon_width = 32 if not self.art_icon.isNull() else 0
        return QSize(self.fontMetrics().horizontalAdvance(self.text()) + icon_width + 28, BUTTON_HEIGHT)

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, event):
        painter = QPainter(self)
        selected = self.primary or self.isChecked()
        if not self.flat:
            asset = "button_primary" if selected else "button_secondary"
            if self.isDown(): asset += "_pressed"
            elif self.underMouse(): asset += "_hover"
            draw_nine_slice(painter, self.rect(), plate(asset), 16 if selected else 10, 12 if selected else 7)
        if self.underMouse() or self.hasFocus():
            painter.fillRect(self.rect().adjusted(5, 5, -5, -5), QColor(255, 255, 255, 35))
        if self.isDown():
            painter.translate(0, 1)
        painter.setOpacity(1 if self.isEnabled() else 0.45)
        painter.setPen(QColor("#FFFFFF" if selected else COLOR_OUTLINE))
        painter.setFont(self.font())
        text_width = self.fontMetrics().horizontalAdvance(self.text())
        icon_width = (38 if self.text() else 24) if not self.art_icon.isNull() else 0
        x = (self.width() - text_width - icon_width) // 2
        if icon_width:
            painter.drawPixmap(QRect(x, (self.height() - self.art_icon.height()) // 2, self.art_icon.width(), self.art_icon.height()), self.art_icon)
        painter.drawText(QRect(x + icon_width, 0, text_width + 1, self.height()), Qt.AlignmentFlag.AlignCenter, self.text())


class PixelIconButton(PixelButton):
    def __init__(self, icon, tip, parent=None):
        super().__init__("", icon, parent)
        self.setProperty("pixelIcon", True)
        self.setToolTip(tip)
        self.setAccessibleName(tip)
        self.setMinimumSize(38, 38)
        self.setMaximumSize(38, 38)

    def sizeHint(self):
        return QSize(38, 38)


class PixelSceneButton(PixelButton):
    def __init__(self, text, scene, parent=None):
        super().__init__(text, parent=parent)
        self.scene = scene
        self.setProperty("sceneButton", True)
        self.setCheckable(True)
        self.setMinimumHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def sizeHint(self):
        return QSize(max(74, self.fontMetrics().horizontalAdvance(self.text()) + 22), 80)

    def paintEvent(self, event):
        painter = QPainter(self)
        draw_nine_slice(painter, self.rect(), plate("scene_selected" if self.isChecked() else "scene"), 8, 7)
        icon = plate("scene_" + self.scene)
        size = icon.size().scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio)
        painter.drawPixmap(QRect((self.width() - size.width()) // 2, 10, size.width(), size.height()), icon)
        painter.setPen(QColor(COLOR_OUTLINE))
        painter.drawText(self.rect().adjusted(4, 42, -4, -6), Qt.AlignmentFlag.AlignCenter, self.text())


class PixelComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.flat = False
        self.setMinimumHeight(INPUT_HEIGHT)
        self.setMinimumContentsLength(8)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.flat:
            draw_nine_slice(painter, self.rect(), plate("combo"), 7, 6)
        painter.setOpacity(1 if self.isEnabled() else 0.45)
        painter.setPen(QColor(COLOR_OUTLINE))
        left = 14
        code = self.currentData()
        if code in ("en", "zh"):
            flag = pixel_pixmap("flag_" + code, 28)
            painter.drawPixmap(14, (self.height() - flag.height()) // 2, flag)
            left = 52
        text_rect = self.rect().adjusted(left, 4, -34, -4)
        text = self.fontMetrics().elidedText(self.currentText(), Qt.TextElideMode.ElideRight, text_rect.width())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        painter.drawPixmap(QRect(self.width() - 25, (self.height() - 12) // 2, 12, 12), pixel_pixmap("arrow_down", 12))
        if self.hasFocus():
            painter.setPen(QColor("#42AEEB"))
            painter.drawRect(self.rect().adjusted(4, 4, -5, -5))
