from __future__ import annotations

import re
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QMouseEvent, QTextCursor
from PySide6.QtWidgets import QLabel, QTextBrowser, QFrame, QHBoxLayout, QPushButton

from .assets import pixel_icon


class ClickableTextBrowser(QTextBrowser):
    wordClicked = Signal(str)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        if event.button() != Qt.MouseButton.LeftButton:
            return
        cursor = self.cursorForPosition(event.position().toPoint())
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        word = cursor.selectedText().strip()
        word = re.sub(r"^[\W_]+|[\W_]+$", "", word, flags=re.UNICODE)
        if len(word) >= 2:
            self.wordClicked.emit(word)


class StatusLabel(QLabel):
    textChanged = Signal(str)

    def setText(self, text: str) -> None:
        text = str(text)
        changed = text != self.text()
        super().setText(text)
        if changed:
            self.textChanged.emit(text)


class StatusStrip(QFrame):
    """Pixel-style status feedback shown below the active page."""

    cancelRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusCard")
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 7, 10, 7)
        self.dot = QLabel("■")
        self.dot.setFixedWidth(18)
        self.text = StatusLabel("Ready")
        self.text.setObjectName("StatusText")
        self.text.setWordWrap(True)
        row.addWidget(self.dot)
        row.addWidget(self.text, 1)
        self.detail = QLabel("")
        self.detail.setObjectName("Muted")
        row.addWidget(self.detail)
        self.cancel_button = QPushButton("取消任务")
        self.cancel_button.setToolTip("停止实时任务；正在推理的单次任务会被标记为过期并丢弃结果")
        self.cancel_button.clicked.connect(self.cancelRequested)
        row.addWidget(self.cancel_button)
        self.set_status("Ready")

    def set_status(self, text: str) -> None:
        self.text.setText(text)
        low = text.lower()
        if any(k in text for k in ("失败", "错误")) or "error" in low:
            color = "#E94C4C"
            state = "ERROR"
        elif any(k in text for k in ("暂停", "停止", "取消")) or "paused" in low:
            color = "#9EB4C3"
            state = "PAUSED"
        elif any(k in text for k in ("正在", "翻译", "识别", "下载", "加载", "监听", "等待")):
            color = "#FFB545"
            state = "WORKING"
        else:
            color = "#42C973"
            state = "READY"
        self.dot.setStyleSheet(f"color:{color}; font-size:14px;")
        self.detail.setText(state)


class PixelIconLabel(QLabel):
    def __init__(self, icon_name: str, size: int = 28, parent=None) -> None:
        super().__init__(parent)
        self.setPixmap(pixel_icon(icon_name).pixmap(QSize(size, size)))
        self.setFixedSize(size + 4, size + 4)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
