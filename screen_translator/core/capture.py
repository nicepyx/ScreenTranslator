import numpy as np
from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication, QImage


def capture_region(rect: QRect) -> np.ndarray:
    """Capture one selected region and return a BGR numpy image.

    The selected rectangle should stay within one monitor for best results.
    """
    if rect.width() < 2 or rect.height() < 2:
        raise ValueError("选择区域太小")

    screen = QGuiApplication.screenAt(rect.center())
    if screen is None:
        screen = QGuiApplication.primaryScreen()
    if screen is None:
        raise RuntimeError("无法获取屏幕")

    geom = screen.geometry()
    local_x = rect.x() - geom.x()
    local_y = rect.y() - geom.y()
    pixmap = screen.grabWindow(0, local_x, local_y, rect.width(), rect.height())
    if pixmap.isNull():
        raise RuntimeError("截图失败。macOS 请确认已授予屏幕录制权限。")

    image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    h = image.height()
    w = image.width()
    stride = image.bytesPerLine()
    buf = np.frombuffer(image.bits(), dtype=np.uint8, count=image.sizeInBytes())
    rgba = buf.reshape((h, stride // 4, 4))[:, :w, :].copy()

    # RapidOCR accepts ndarray; OpenCV-style BGR is the safest convention.
    return rgba[:, :, [2, 1, 0]]
