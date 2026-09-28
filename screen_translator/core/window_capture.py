from __future__ import annotations

from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import platform
from PySide6.QtCore import QRect


@dataclass(frozen=True)
class WindowInfo:
    key: str
    title: str
    owner: str
    rect: QRect

    @property
    def display_name(self) -> str:
        prefix = f"{self.owner} · " if self.owner and self.owner not in self.title else ""
        return f"{prefix}{self.title}"

    @property
    def profile_key(self) -> str:
        # Window handles/CGWindow IDs change every launch. Profiles therefore bind to the
        # process/owner + visible title instead of the transient capture ID.
        return f"{self.owner or 'app'}::{self.title}"


def _windows_info(hwnd: int) -> WindowInfo | None:
    user32 = ctypes.windll.user32
    if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
        return None
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return None
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value.strip()
    if not title or title.startswith("Screen Translator"):
        return None

    rect = wintypes.RECT()
    ok = False
    try:
        dwmapi = ctypes.windll.dwmapi
        ok = dwmapi.DwmGetWindowAttribute(
            hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect)
        ) == 0
    except Exception:
        ok = False
    if not ok and not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    w = int(rect.right - rect.left)
    h = int(rect.bottom - rect.top)
    if w < 160 or h < 120:
        return None
    owner = ""
    try:
        import psutil
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value:
            owner = psutil.Process(int(pid.value)).name()
    except Exception:
        owner = ""
    return WindowInfo(str(int(hwnd)), title, owner, QRect(rect.left, rect.top, w, h))


def _windows_list() -> list[WindowInfo]:
    user32 = ctypes.windll.user32
    results: list[WindowInfo] = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _lparam):
        info = _windows_info(int(hwnd))
        if info is not None:
            results.append(info)
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    results.sort(key=lambda w: w.title.lower())
    return results


def _mac_item_to_info(item) -> WindowInfo | None:
    import Quartz
    if int(item.get(Quartz.kCGWindowLayer, 0) or 0) != 0:
        return None
    owner = str(item.get(Quartz.kCGWindowOwnerName, "") or "").strip()
    title = str(item.get(Quartz.kCGWindowName, "") or "").strip()
    if owner == "Screen Translator" or (not title and not owner):
        return None
    bounds = item.get(Quartz.kCGWindowBounds, {}) or {}
    x = int(bounds.get("X", 0))
    y = int(bounds.get("Y", 0))
    w = int(bounds.get("Width", 0))
    h = int(bounds.get("Height", 0))
    if w < 160 or h < 120:
        return None
    key = str(int(item.get(Quartz.kCGWindowNumber, 0) or 0))
    return WindowInfo(key, title or owner, owner, QRect(x, y, w, h))


def _mac_list() -> list[WindowInfo]:
    try:
        import Quartz
    except Exception:
        return []
    options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
    windows = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
    results: list[WindowInfo] = []
    for item in windows or []:
        info = _mac_item_to_info(item)
        if info is not None:
            results.append(info)
    results.sort(key=lambda w: w.display_name.lower())
    return results


def list_application_windows() -> list[WindowInfo]:
    system = platform.system()
    if system == "Windows":
        return _windows_list()
    if system == "Darwin":
        return _mac_list()
    return []


def get_application_window(key: str) -> WindowInfo | None:
    system = platform.system()
    if system == "Windows":
        try:
            return _windows_info(int(key))
        except (TypeError, ValueError):
            return None
    if system == "Darwin":
        try:
            import Quartz
            window_id = int(key)
            options = Quartz.kCGWindowListOptionIncludingWindow
            items = Quartz.CGWindowListCopyWindowInfo(options, window_id)
            for item in items or []:
                info = _mac_item_to_info(item)
                if info is not None and info.key == str(window_id):
                    return info
        except Exception:
            return None
    return None


def crop_window_rect(rect: QRect, mode: str) -> QRect:
    if mode == "bottom40":
        h = max(80, int(rect.height() * 0.40))
        return QRect(rect.x(), rect.bottom() - h + 1, rect.width(), h)
    if mode == "bottom25":
        h = max(80, int(rect.height() * 0.25))
        return QRect(rect.x(), rect.bottom() - h + 1, rect.width(), h)
    return QRect(rect)
