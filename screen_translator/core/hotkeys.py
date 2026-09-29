from __future__ import annotations

import threading
from PySide6.QtCore import QObject, Signal


DEFAULT_HOTKEYS = {
    "screen_once": "Ctrl+Alt+Q",
    "toggle_audio": "Ctrl+Alt+A",
    "toggle_overlay": "Ctrl+Alt+D",
    "clear_overlay": "Ctrl+Alt+C",
    "toggle_mini": "Ctrl+Alt+M",
    "show_window": "Ctrl+Alt+W",
}

ACTION_LABELS = {
    "screen_once": "框选并翻译一次",
    "toggle_audio": "开始 / 暂停声音翻译",
    "toggle_overlay": "显示 / 隐藏字幕",
    "clear_overlay": "清空当前字幕",
    "toggle_mini": "显示 / 隐藏迷你控制条",
    "show_window": "显示主窗口",
}


def qt_to_pynput(text: str) -> str:
    parts = [x.strip().lower() for x in text.split("+") if x.strip()]
    result = []
    mapping = {
        "ctrl": "<ctrl>", "control": "<ctrl>", "alt": "<alt>",
        "shift": "<shift>", "meta": "<cmd>", "cmd": "<cmd>", "command": "<cmd>",
    }
    for part in parts:
        result.append(mapping.get(part, part))
    return "+".join(result)


class GlobalHotkeyManager(QObject):
    triggered = Signal(str)
    stateChanged = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._listener = None
        self._thread: threading.Thread | None = None

    def stop(self) -> None:
        listener = self._listener
        self._listener = None
        if listener is not None:
            try:
                listener.stop()
            except Exception:
                pass

    def start(self, mapping: dict[str, str]) -> bool:
        self.stop()
        try:
            from pynput import keyboard
        except Exception as exc:
            self.stateChanged.emit(f"全局快捷键不可用：{exc}")
            return False

        hotkeys: dict[str, callable] = {}
        for action, sequence in mapping.items():
            normalized = qt_to_pynput(sequence)
            if not normalized:
                continue
            hotkeys[normalized] = (lambda a=action: self.triggered.emit(a))
        if not hotkeys:
            self.stateChanged.emit("未启用任何全局快捷键")
            return False
        try:
            self._listener = keyboard.GlobalHotKeys(hotkeys)
            self._listener.start()
            self.stateChanged.emit(f"全局快捷键已启用 · {len(hotkeys)} 项")
            return True
        except Exception as exc:
            self._listener = None
            self.stateChanged.emit(f"全局快捷键启动失败：{exc}")
            return False
