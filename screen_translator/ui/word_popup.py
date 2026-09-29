from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .assets import pixel_icon
from .components import PixelCard


class WordPopup(QDialog):
    addRequested = Signal(dict)
    speakRequested = Signal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("词汇释义")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Tool)
        self.setModal(False)
        self.setMinimumWidth(390)
        self._payload: dict = {}
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        card = PixelCard()
        outer.addWidget(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        self.term = QLabel("—")
        self.term.setStyleSheet("font-size:24px; font-weight:800; color:#173B63;")
        layout.addWidget(self.term)
        self.meta = QLabel("")
        self.meta.setObjectName("Muted")
        layout.addWidget(self.meta)
        title = QLabel("含义")
        title.setStyleSheet("font-weight:800;")
        layout.addWidget(title)
        self.meaning = QLabel("点击文本中的词语即可查询。")
        self.meaning.setWordWrap(True)
        layout.addWidget(self.meaning)
        self.context_title = QLabel("当前句")
        self.context_title.setStyleSheet("font-weight:800;")
        layout.addWidget(self.context_title)
        self.context = QLabel("")
        self.context.setWordWrap(True)
        self.context.setObjectName("Muted")
        layout.addWidget(self.context)
        row = QHBoxLayout()
        self.speak_btn = QPushButton("朗读")
        self.speak_btn.setIcon(pixel_icon("speaker"))
        self.speak_btn.clicked.connect(self._speak)
        self.add_btn = QPushButton("加入词汇")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.setIcon(pixel_icon("star"))
        self.add_btn.clicked.connect(self._add)
        copy_btn = QPushButton("复制")
        copy_btn.setIcon(pixel_icon("copy"))
        copy_btn.clicked.connect(self._copy)
        row.addWidget(self.speak_btn)
        row.addWidget(self.add_btn)
        row.addWidget(copy_btn)
        row.addStretch(1)
        layout.addLayout(row)

    def show_loading(self, word: str, source_lang: str, target_lang: str, context: str) -> None:
        self._payload = {
            "term": word,
            "meaning": "",
            "source_lang": source_lang,
            "target_lang": target_lang,
            "context": context,
        }
        self.term.setText(word)
        self.meta.setText(f"{source_lang} → {target_lang}")
        self.meaning.setText("正在查询本地翻译模型…")
        self.context.setText(context or "—")
        self.add_btn.setEnabled(False)
        self.show()
        self.raise_()
        self.activateWindow()

    def show_result(self, payload: dict) -> None:
        self._payload = dict(payload)
        self.term.setText(str(payload.get("term", "")))
        self.meta.setText(f"{payload.get('source_lang', '')} → {payload.get('target_lang', '')}")
        self.meaning.setText(str(payload.get("meaning", "")) or "—")
        self.context.setText(str(payload.get("context", "")) or "—")
        self.add_btn.setEnabled(True)
        self.show()
        self.raise_()

    def show_error(self, message: str) -> None:
        self.meaning.setText("查询失败：" + message)
        self.add_btn.setEnabled(False)

    def _add(self) -> None:
        if self._payload.get("term") and self._payload.get("meaning"):
            self.addRequested.emit(dict(self._payload))

    def _speak(self) -> None:
        if self._payload.get("term"):
            self.speakRequested.emit(str(self._payload.get("term")), str(self._payload.get("source_lang", "")))

    def _copy(self) -> None:
        from PySide6.QtWidgets import QApplication
        term = str(self._payload.get("term", ""))
        meaning = str(self._payload.get("meaning", ""))
        QApplication.clipboard().setText((term + "\n" + meaning).strip())
