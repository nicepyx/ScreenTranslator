from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from PySide6.QtCore import QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QMouseEvent, QPainter, QResizeEvent
from PySide6.QtWidgets import QSizeGrip, QToolButton, QVBoxLayout, QWidget


SubtitleState = Literal["partial", "final"]


@dataclass
class SubtitleEntry:
    translated: str
    source: str
    created_at: float
    expires_at: float | None


class SubtitleCanvas(QWidget):
    """Paints rolling subtitles with outline/shadow and low-jitter transitions."""

    content_empty = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.background_opacity = 70
        self.translation_font_size = 18
        self.source_font_size = 14
        self.translation_color = QColor("#FFFFFF")
        self.source_color = QColor("#C8C8C8")
        self.font_family = ""
        self.display_mode = "translation"
        self.shadow_enabled = True
        self.outline_width = 2
        self.outline_color = QColor("#000000")
        self.max_lines = 2
        self.recent_count = 3
        self.retention_mode = "smart"
        self.alignment = "center"
        self.smooth_updates = True

        self._entries: list[SubtitleEntry] = []
        self._partial: SubtitleEntry | None = None
        self._transition_started = 0.0
        self._transition_duration = 0.18
        self._last_state: SubtitleState = "final"

        self._tick = QTimer(self)
        self._tick.setInterval(40)
        self._tick.timeout.connect(self._on_tick)
        self._tick.start()

    def configure(
        self,
        *,
        background_opacity: int,
        translation_font_size: int,
        source_font_size: int,
        translation_color: str,
        source_color: str,
        font_family: str,
        display_mode: str,
        shadow_enabled: bool,
        outline_width: int,
        outline_color: str,
        max_lines: int,
        recent_count: int,
        retention_mode: str,
        alignment: str,
        smooth_updates: bool,
    ) -> None:
        self.background_opacity = max(0, min(100, int(background_opacity)))
        self.translation_font_size = max(10, min(64, int(translation_font_size)))
        self.source_font_size = max(9, min(52, int(source_font_size)))
        if QColor(translation_color).isValid():
            self.translation_color = QColor(translation_color)
        if QColor(source_color).isValid():
            self.source_color = QColor(source_color)
        if QColor(outline_color).isValid():
            self.outline_color = QColor(outline_color)
        self.font_family = font_family or ""
        self.display_mode = display_mode
        self.shadow_enabled = bool(shadow_enabled)
        self.outline_width = max(0, min(5, int(outline_width)))
        self.max_lines = max(0, min(6, int(max_lines)))
        self.recent_count = max(1, min(3, int(recent_count)))
        self.retention_mode = retention_mode
        self.alignment = alignment
        self.smooth_updates = bool(smooth_updates)
        self._entries = self._entries[-self.recent_count :]
        self.updateGeometry()
        self.update()

    def clear(self) -> None:
        self._entries.clear()
        self._partial = None
        self.update()

    def _duration_for(self, translated: str, source: str) -> float | None:
        if self.retention_mode == "keep":
            return None
        if self.retention_mode.startswith("fixed:"):
            try:
                return float(self.retention_mode.split(":", 1)[1])
            except ValueError:
                pass
        # Smart reading time: short captions stay long enough to acquire visually,
        # long captions scale up but never linger excessively.
        weighted_chars = len(translated.strip()) + len(source.strip()) * 0.28
        return max(2.8, min(9.0, 2.25 + weighted_chars * 0.055))

    def push(self, translated: str, source: str = "", *, state: SubtitleState = "final") -> None:
        translated = translated.strip()
        source = source.strip()
        if not translated:
            return
        now = time.monotonic()
        self._last_state = state
        self._transition_started = now

        if state == "partial":
            self._partial = SubtitleEntry(translated, source, now, None)
        else:
            duration = self._duration_for(translated, source)
            expires = None if duration is None else now + duration
            entry = SubtitleEntry(translated, source, now, expires)
            self._partial = None
            if self._entries and self._entries[-1].translated == translated and self._entries[-1].source == source:
                self._entries[-1] = entry
            else:
                self._entries.append(entry)
                self._entries = self._entries[-self.recent_count :]
        self.updateGeometry()
        self.update()

    def _on_tick(self) -> None:
        now = time.monotonic()
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.expires_at is None or e.expires_at > now]
        if len(self._entries) != before:
            self.updateGeometry()
            self.update()
        if self.smooth_updates and now - self._transition_started < self._transition_duration:
            self.update()
        if not self._entries and self._partial is None:
            self.content_empty.emit()

    def has_content(self) -> bool:
        return bool(self._entries or self._partial)

    def _display_entries(self) -> list[tuple[SubtitleEntry, bool]]:
        if self._partial is not None:
            keep = max(0, self.recent_count - 1)
            finals = self._entries[-keep:] if keep else []
            return [(e, False) for e in finals] + [(self._partial, True)]
        return [(e, False) for e in self._entries[-self.recent_count :]]

    def _font(self, size: int, *, bold: bool = False) -> QFont:
        font = QFont(self.font_family) if self.font_family else QFont()
        font.setPixelSize(size)
        font.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
        return font

    def _text_flags(self) -> int:
        if self.alignment == "left":
            horizontal = Qt.AlignmentFlag.AlignLeft
        elif self.alignment == "right":
            horizontal = Qt.AlignmentFlag.AlignRight
        else:
            horizontal = Qt.AlignmentFlag.AlignHCenter
        return int(horizontal | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap)

    def _measure_text(self, text: str, font: QFont, width: int, max_lines: int) -> int:
        if not text:
            return 0
        metrics = QFontMetrics(font)
        flags = self._text_flags()
        rect = metrics.boundingRect(QRect(0, 0, max(20, width), 10000), flags, text)
        height = max(metrics.lineSpacing(), rect.height())
        if max_lines > 0:
            height = min(height, metrics.lineSpacing() * max_lines)
        return height

    def _entry_height(self, entry: SubtitleEntry, width: int) -> int:
        inner = max(80, width - 36)
        translated_font = self._font(self.translation_font_size, bold=True)
        trans_h = self._measure_text(entry.translated, translated_font, inner, self.max_lines)
        if self.display_mode == "bilingual" and entry.source:
            source_font = self._font(self.source_font_size)
            source_h = self._measure_text(entry.source, source_font, inner, max(1, min(2, self.max_lines or 2)))
            return source_h + trans_h + 9 + 20
        return trans_h + 20

    def preferred_height(self, width: int | None = None) -> int:
        width = width or max(320, self.width())
        entries = self._display_entries()
        if not entries:
            return 54
        return max(54, sum(self._entry_height(entry, width) for entry, _ in entries) + 8 * (len(entries) - 1))

    def sizeHint(self):  # type: ignore[override]
        from PySide6.QtCore import QSize

        return QSize(max(320, self.width()), self.preferred_height(max(320, self.width())))

    def _draw_wrapped_text(
        self,
        painter: QPainter,
        rect: QRect,
        text: str,
        font: QFont,
        color: QColor,
        opacity: float,
        max_lines: int,
    ) -> None:
        if not text:
            return
        painter.save()
        painter.setFont(font)
        painter.setOpacity(max(0.0, min(1.0, opacity)))
        line_height = QFontMetrics(font).lineSpacing()
        if max_lines > 0:
            clip = QRect(rect)
            clip.setHeight(min(rect.height(), line_height * max_lines + 2))
            painter.setClipRect(clip)
        flags = self._text_flags()

        if self.shadow_enabled:
            shadow = QColor(0, 0, 0, 190)
            painter.setPen(shadow)
            for dx, dy in ((2, 2), (3, 3)):
                painter.drawText(rect.translated(dx, dy), flags, text)

        if self.outline_width > 0:
            painter.setPen(self.outline_color)
            w = self.outline_width
            offsets = [
                (-w, 0), (w, 0), (0, -w), (0, w),
                (-w, -w), (-w, w), (w, -w), (w, w),
            ]
            for dx, dy in offsets:
                painter.drawText(rect.translated(dx, dy), flags, text)

        painter.setPen(color)
        painter.drawText(rect, flags, text)
        painter.restore()

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        entries = self._display_entries()
        if not entries:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        now = time.monotonic()
        transition = 1.0
        if self.smooth_updates and self._transition_started:
            transition = min(1.0, max(0.0, (now - self._transition_started) / self._transition_duration))

        heights = [self._entry_height(entry, self.width()) for entry, _ in entries]
        total_h = sum(heights) + 8 * (len(entries) - 1)
        y = max(2, self.height() - total_h - 2)  # bottom-anchored: no vertical jump while text changes.

        count = len(entries)
        for index, ((entry, is_partial), h) in enumerate(zip(entries, heights)):
            is_newest = index == count - 1
            age_rank = count - 1 - index
            base_opacity = max(0.34, 1.0 - age_rank * 0.24)
            if is_partial:
                base_opacity *= 0.68
            if is_newest:
                base_opacity *= 0.72 + 0.28 * transition
                y_offset = int((1.0 - transition) * 8) if self.smooth_updates else 0
            else:
                y_offset = 0

            rect = QRect(3, y + y_offset, max(10, self.width() - 6), h)
            bg_alpha = int(round(255 * self.background_opacity / 100 * base_opacity))
            if bg_alpha > 0:
                painter.save()
                painter.setOpacity(1.0)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(15, 15, 15, bg_alpha))
                painter.drawRoundedRect(rect, 10, 10)
                painter.restore()

            content = rect.adjusted(18, 9, -18, -9)
            if self.display_mode == "bilingual" and entry.source:
                source_font = self._font(self.source_font_size)
                source_h = self._measure_text(entry.source, source_font, content.width(), max(1, min(2, self.max_lines or 2)))
                source_rect = QRect(content.x(), content.y(), content.width(), source_h)
                self._draw_wrapped_text(
                    painter,
                    source_rect,
                    entry.source,
                    source_font,
                    self.source_color,
                    base_opacity * (0.82 if is_partial else 1.0),
                    max(1, min(2, self.max_lines or 2)),
                )
                trans_rect = QRect(
                    content.x(),
                    source_rect.bottom() + 6,
                    content.width(),
                    max(12, content.bottom() - source_rect.bottom() - 5),
                )
            else:
                trans_rect = content

            trans_font = self._font(self.translation_font_size, bold=True)
            self._draw_wrapped_text(
                painter,
                trans_rect,
                entry.translated,
                trans_font,
                self.translation_color,
                base_opacity,
                self.max_lines,
            )
            y += h + 8

        painter.end()


class TranslationOverlay(QWidget):
    closed_by_user = Signal()
    lock_changed = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._opacity_percent = 70
        self._translation_font_size = 18
        self._source_font_size = 14
        self._font_color = "#FFFFFF"
        self._source_font_color = "#C8C8C8"
        self._font_family = ""
        self._display_mode = "translation"
        self._shadow_enabled = True
        self._outline_width = 2
        self._outline_color = "#000000"
        self._max_lines = 2
        self._recent_count = 3
        self._retention_mode = "smart"
        self._smooth_updates = True
        self._alignment = "center"
        self._position_mode = "auto"
        self._width_mode = "640"
        self._locked = False
        self._mouse_passthrough = False
        self._last_source_rect: QRect | None = None
        self._audio_mode = False
        self._last_text = ""
        self._last_source_text = ""
        self._last_state: SubtitleState = "final"

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(280, 54)

        self.canvas = SubtitleCanvas(self)
        self.canvas.content_empty.connect(self._on_content_empty)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self.lock_button = QToolButton(self)
        self.lock_button.setText("🔓")
        self.lock_button.setToolTip("锁定字幕框位置")
        self.lock_button.setFixedSize(28, 28)
        self.lock_button.clicked.connect(self._toggle_lock)

        self.close_button = QToolButton(self)
        self.close_button.setText("×")
        self.close_button.setToolTip("关闭字幕框")
        self.close_button.setFixedSize(28, 28)
        self.close_button.clicked.connect(self._close_from_button)

        button_style = (
            "QToolButton { background: rgba(0,0,0,0); border: none; border-radius: 6px; "
            "color: rgba(255,255,255,210); font-size: 17px; }"
            "QToolButton:hover { background: rgba(0,0,0,85); color: white; }"
            "QToolButton:pressed { background: rgba(0,0,0,130); }"
        )
        self.lock_button.setStyleSheet(button_style)
        self.close_button.setStyleSheet(button_style)

        self.size_grip = QSizeGrip(self)
        self.size_grip.setFixedSize(14, 14)
        self.size_grip.setToolTip("拖动调整字幕框大小")

        self.set_locked(False)
        self.hide()

    def _on_content_empty(self) -> None:
        # Smart/fixed subtitle retention expires naturally. The overlay can disappear
        # without changing the user's "显示字幕框" preference.
        if self.isVisible() and not self.canvas.has_content():
            self.hide()

    def _close_from_button(self) -> None:
        self.hide()
        self.closed_by_user.emit()

    def _toggle_lock(self) -> None:
        self.set_locked(not self._locked)

    def set_preferences(
        self,
        *,
        opacity_percent: int | None = None,
        font_size: int | None = None,
        source_font_size: int | None = None,
        font_color: str | None = None,
        source_font_color: str | None = None,
        font_family: str | None = None,
        display_mode: str | None = None,
        shadow_enabled: bool | None = None,
        outline_width: int | None = None,
        outline_color: str | None = None,
        max_lines: int | None = None,
        recent_count: int | None = None,
        retention_mode: str | None = None,
        smooth_updates: bool | None = None,
        alignment: str | None = None,
        position_mode: str | None = None,
        width_mode: str | None = None,
    ) -> None:
        if opacity_percent is not None:
            self._opacity_percent = max(0, min(100, int(opacity_percent)))
        if font_size is not None:
            self._translation_font_size = max(10, min(64, int(font_size)))
        if source_font_size is not None:
            self._source_font_size = max(9, min(52, int(source_font_size)))
        if font_color is not None and QColor(font_color).isValid():
            self._font_color = QColor(font_color).name().upper()
        if source_font_color is not None and QColor(source_font_color).isValid():
            self._source_font_color = QColor(source_font_color).name().upper()
        if font_family is not None:
            self._font_family = font_family
        if display_mode is not None:
            self._display_mode = display_mode
        if shadow_enabled is not None:
            self._shadow_enabled = bool(shadow_enabled)
        if outline_width is not None:
            self._outline_width = max(0, min(5, int(outline_width)))
        if outline_color is not None and QColor(outline_color).isValid():
            self._outline_color = QColor(outline_color).name().upper()
        if max_lines is not None:
            self._max_lines = max(0, int(max_lines))
        if recent_count is not None:
            self._recent_count = max(1, min(3, int(recent_count)))
        if retention_mode is not None:
            self._retention_mode = retention_mode
        if smooth_updates is not None:
            self._smooth_updates = bool(smooth_updates)
        if alignment is not None:
            self._alignment = alignment
        if position_mode is not None:
            self._position_mode = position_mode
        if width_mode is not None:
            self._width_mode = width_mode

        self.canvas.configure(
            background_opacity=self._opacity_percent,
            translation_font_size=self._translation_font_size,
            source_font_size=self._source_font_size,
            translation_color=self._font_color,
            source_color=self._source_font_color,
            font_family=self._font_family,
            display_mode=self._display_mode,
            shadow_enabled=self._shadow_enabled,
            outline_width=self._outline_width,
            outline_color=self._outline_color,
            max_lines=self._max_lines,
            recent_count=self._recent_count,
            retention_mode=self._retention_mode,
            alignment=self._alignment,
            smooth_updates=self._smooth_updates,
        )
        if self.isVisible():
            self._apply_geometry(self._last_source_rect)

    def set_locked(self, locked: bool) -> None:
        self._locked = bool(locked)
        self.lock_button.setText("🔒" if self._locked else "🔓")
        self.lock_button.setToolTip("解锁字幕框位置" if self._locked else "锁定字幕框位置")
        self.size_grip.setVisible(not self._locked and not self._mouse_passthrough)
        self.lock_changed.emit(self._locked)

    def set_mouse_passthrough(self, enabled: bool) -> None:
        self._mouse_passthrough = bool(enabled)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self._mouse_passthrough)
        self.size_grip.setVisible(not self._locked and not self._mouse_passthrough)

    @property
    def locked(self) -> bool:
        return self._locked

    @property
    def mouse_passthrough(self) -> bool:
        return self._mouse_passthrough

    def reset_position(self) -> None:
        self._position_mode = "auto"
        self._apply_geometry(self._last_source_rect)

    def clear_history(self) -> None:
        self.canvas.clear()

    def show_translation(
        self,
        text: str,
        source_rect: QRect | None = None,
        *,
        audio_mode: bool = False,
        source_text: str = "",
        state: SubtitleState = "final",
    ) -> None:
        if not text.strip():
            return
        self._audio_mode = audio_mode
        self._last_source_rect = QRect(source_rect) if source_rect is not None else None
        self._last_text = text
        self._last_source_text = source_text
        self._last_state = state
        self.canvas.push(text, source_text, state=state)
        self._apply_geometry(self._last_source_rect)
        self.show()
        self.raise_()

    def _target_width(self, source_rect: QRect | None, available: QRect) -> int:
        if self._width_mode == "manual":
            return max(280, self.width())
        if self._width_mode == "auto":
            if source_rect is not None:
                return max(320, min(1000, source_rect.width()))
            return min(800, max(420, int(available.width() * 0.62)))
        try:
            return int(self._width_mode)
        except ValueError:
            return 640

    def _apply_geometry(self, source_rect: QRect | None) -> None:
        if source_rect is not None:
            screen = QGuiApplication.screenAt(source_rect.center()) or QGuiApplication.primaryScreen()
        else:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        width = min(self._target_width(source_rect, available), max(280, available.width() - 24))
        desired_h = max(self.minimumHeight(), self.canvas.preferred_height(width))
        desired_h = min(desired_h, max(80, int(available.height() * 0.62)))

        old_bottom = self.geometry().bottom()
        self.resize(width, desired_h)

        if self._position_mode == "manual" and self.isVisible():
            # Manual placement keeps the user's top-left anchor. Automatic/top/bottom modes
            # anchor explicitly below, which prevents subtitle growth from visually jumping.
            return

        x = available.center().x() - self.width() // 2
        if self._position_mode == "top":
            y = available.top() + 24
        elif self._position_mode == "bottom" or (self._audio_mode and self._position_mode == "auto"):
            y = available.bottom() - self.height() - 48
        elif source_rect is not None:
            x = source_rect.center().x() - self.width() // 2
            below_y = source_rect.bottom() + 10
            if below_y + self.height() <= available.bottom():
                y = below_y
            else:
                y = max(available.top() + 8, source_rect.top() - self.height() - 10)
        else:
            y = available.bottom() - self.height() - 48

        # Keep automatic subtitle geometry stable while the internal text grows/shrinks.
        if self._position_mode == "manual" and old_bottom > 0:
            y = old_bottom - self.height()

        x = max(available.left() + 8, min(x, available.right() - self.width() - 8))
        y = max(available.top() + 8, min(y, available.bottom() - self.height() - 8))
        self.move(x, y)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        top = 4
        right = 4
        self.close_button.move(max(0, self.width() - self.close_button.width() - right), top)
        self.lock_button.move(
            max(0, self.width() - self.close_button.width() - self.lock_button.width() - right - 2), top
        )
        self.size_grip.move(
            max(0, self.width() - self.size_grip.width() - 2),
            max(0, self.height() - self.size_grip.height() - 2),
        )
        self.lock_button.raise_()
        self.close_button.raise_()
        self.size_grip.raise_()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and not self._locked
            and not self._mouse_passthrough
        ):
            handle = self.windowHandle()
            if handle is not None:
                handle.startSystemMove()
                event.accept()
                return
        super().mousePressEvent(event)
