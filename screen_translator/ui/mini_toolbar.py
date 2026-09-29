from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from .assets import pixel_icon


class MiniToolbar(QFrame):
    pauseRequested = Signal()
    clearRequested = Signal()
    showMainRequested = Signal()
    toggleOverlayLockRequested = Signal()
    closeRequested = Signal()

    def __init__(self) -> None:
        super().__init__(None)
        self.setObjectName("PixelCard")
        self.setWindowTitle("Screen Translator Mini")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self._drag_pos: QPoint | None = None
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 5, 8, 5)
        row.setSpacing(5)
        self.state_dot = QLabel("■")
        self.state_dot.setStyleSheet("color:#42C973; font-size:14px;")
        self.state_text = QLabel("Ready")
        self.direction = QLabel("AUTO → 中文")
        self.direction.setObjectName("Muted")
        row.addWidget(self.state_dot)
        row.addWidget(self.state_text)
        row.addWidget(self.direction)
        row.addStretch(1)
        self.pause_btn = self._icon_button("pause", "暂停 / 继续")
        self.pause_btn.clicked.connect(self.pauseRequested)
        self.clear_btn = self._icon_button("clear", "清空字幕")
        self.clear_btn.clicked.connect(self.clearRequested)
        self.lock_btn = self._icon_button("pin", "锁定 / 解锁字幕")
        self.lock_btn.clicked.connect(self.toggleOverlayLockRequested)
        self.main_btn = QPushButton("主窗口")
        self.main_btn.clicked.connect(self.showMainRequested)
        self.close_btn = self._icon_button("close", "隐藏控制条")
        self.close_btn.clicked.connect(self.closeRequested)
        for w in (self.pause_btn, self.clear_btn, self.lock_btn, self.main_btn, self.close_btn):
            row.addWidget(w)
        self.resize(500, 48)

    @staticmethod
    def _icon_button(name: str, tip: str) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("IconButton")
        btn.setIcon(pixel_icon(name))
        btn.setToolTip(tip)
        return btn

    def set_state(self, text: str) -> None:
        self.state_text.setText(text)
        if any(k in text for k in ("失败", "错误")):
            color = "#E94C4C"
        elif any(k in text for k in ("暂停", "停止", "取消")):
            color = "#9EB4C3"
        elif any(k in text for k in ("正在", "翻译", "识别", "监听", "等待", "加载")):
            color = "#FFB545"
        else:
            color = "#42C973"
        self.state_dot.setStyleSheet(f"color:{color}; font-size:14px;")

    def set_direction(self, source: str, target: str) -> None:
        self.direction.setText(f"{source} → {target}")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)
