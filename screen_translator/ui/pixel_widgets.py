from __future__ import annotations

import re
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QTextCursor
from PySide6.QtWidgets import QLabel, QTextBrowser


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
