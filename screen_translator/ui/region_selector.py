from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget


class RegionSelector(QWidget):
    region_selected = Signal(QRect)
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._start: QPoint | None = None
        self._end: QPoint | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        screens = QGuiApplication.screens()
        if not screens:
            return
        virtual = screens[0].geometry()
        for screen in screens[1:]:
            virtual = virtual.united(screen.geometry())
        self.setGeometry(virtual)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.activateWindow()
        self.setFocus()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))

        if self._start is not None and self._end is not None:
            selected = QRect(self._start, self._end).normalized()
            painter.setPen(QPen(QColor(70, 190, 255), 2))
            painter.setBrush(QColor(70, 190, 255, 35))
            painter.drawRect(selected)

            painter.setPen(QColor(255, 255, 255))
            label = f"{selected.width()} × {selected.height()}"
            painter.drawText(
                selected.adjusted(8, 8, -8, -8),
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                label,
            )
        else:
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "拖动鼠标框选需要翻译的区域 · Esc 取消",
            )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.position().toPoint()
            self._end = self._start
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._start is not None:
            self._end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._start is None:
            return
        self._end = event.position().toPoint()
        local_rect = QRect(self._start, self._end).normalized()
        if local_rect.width() < 10 or local_rect.height() < 10:
            self._start = None
            self._end = None
            self.update()
            return

        global_rect = QRect(
            local_rect.x() + self.geometry().x(),
            local_rect.y() + self.geometry().y(),
            local_rect.width(),
            local_rect.height(),
        )
        self.hide()
        self.region_selected.emit(global_rect)
        self.deleteLater()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.cancelled.emit()
            self.deleteLater()
            return
        super().keyPressEvent(event)
