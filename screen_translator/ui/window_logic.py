from __future__ import annotations

from pathlib import Path
import numpy as np
from PySide6.QtCore import QRect, QThreadPool, QTimer, Qt
from PySide6.QtGui import QColor, QCloseEvent, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QColorDialog, QComboBox, QFileDialog, QLabel, QMessageBox, QTableWidgetItem

from ..constants import PERFORMANCE_PROFILES, LANGUAGE_CATALOG, SUBTITLE_PRESETS
from ..core.audio import AudioTranscriber, list_audio_devices
from ..core.audio_worker import AudioTranslationWorker
from ..core.capture import capture_region
from ..core.ocr import OCRService
from ..core.performance import RuntimePerformanceMonitor, detect_hardware, profile_settings, recommend_profile
from ..core.platform_helpers import is_macos
from ..core.translator import LocalTranslator
from ..core.text_pipeline import TranslationPipeline
from ..core.history import TranslationHistory
from ..core.app_settings import AppSettings
from ..core.window_capture import crop_window_rect, get_application_window, list_application_windows
from ..core.worker import TranslationWorker
from ..core.stability import StableTextDetector
from ..core.profiles import GameProfileStore
from ..core.model_manager import ModelManager
from .scene_presets import SCENE_PRESETS as USAGE_MODES
from .overlay import TranslationOverlay
from .region_selector import RegionSelector
from .model_dialogs import request_model


class TranslatorWindowLogicMixin:
    """Existing pipeline adapters. No main window or page construction."""

    def _initialize_logic(self) -> None:
        self._thread_pool = QThreadPool.globalInstance()
        self._model_manager = ModelManager()
        self._ocr = OCRService()
        self._translator = LocalTranslator(self._model_manager)
        self._pipeline = TranslationPipeline(self._translator)
        self._history = TranslationHistory()
        self._stable_detector = StableTextDetector()
        self._profiles = GameProfileStore()
        self._runtime_monitor = RuntimePerformanceMonitor()
        self._audio_transcriber = AudioTranscriber(self._model_manager)
        self._audio_worker: AudioTranslationWorker | None = None

        self._selector: RegionSelector | None = None
        self._selected_rect: QRect | None = None
        self._selected_window_key: str | None = None
        self._busy = False
        self._live_mode = False
        self._audio_running = False
        self._screen_signature: np.ndarray | None = None
        self._last_ocr_text = ""
        self._screen_pending_stability = False
        self._screen_task_generation = 0
        self._screen_change_threshold = 1.35
        self._performance_screen_threshold = 1.35
        self._applying_profile = False
        self._applying_game_profile = False
        self._stable_debounce_ms = 180
        self._partial_enabled = True
        self._partial_interval_ms = 1000
        self._vad_end_silence_ms = 420
        self._max_utterance_ms = 8000
        self._restoring_settings = False
        self._font_color = "#FFFFFF"
        self._source_font_color = "#C8C8C8"
        self._outline_color = "#000000"
        self._font_family = ""
        self._custom_font_path = ""
        self._settings = AppSettings()

        self._hardware_info = detect_hardware()
        self._recommended_profile, self._recommendation_reason = recommend_profile(self._hardware_info)

        self._live_timer = QTimer(self)
        self._live_timer.timeout.connect(self._live_tick)
        self._perf_timer = QTimer(self)
        self._perf_timer.setInterval(1000)
        self._perf_timer.timeout.connect(self._update_runtime_metrics)

        self._overlay = TranslationOverlay()
        self._overlay.closed_by_user.connect(self._overlay_closed)
        self._overlay.lock_changed.connect(self._overlay_lock_changed)


    def _restore_runtime(self) -> None:
        self._restore_settings()
        self._refresh_audio_devices()
        self._refresh_windows()
        self._load_history()
        self._refresh_model_status()
        self._apply_overlay_settings()
        self._refresh_performance_summary()
        self._perf_timer.start()
        self._update_runtime_metrics()



    def _refresh_model_status(self) -> None:
        self.status_label.setText(
            "本地翻译模型已就绪，可离线使用。" if self._translator.model_ready
            else "翻译模型尚未安装；开始翻译时可选择下载或从本地导入。"
        )


    def _require_model(self, model_id: str, continuation) -> bool:
        if self._model_manager.is_installed(model_id):
            return True
        if request_model(self, self._model_manager, model_id):
            self._refresh_model_status()
            self._refresh_storage_summary()
            QTimer.singleShot(0, continuation)
        return False


    def _restore_settings(self) -> None:
        self._restoring_settings = True

        def restore_combo(combo: QComboBox, key: str, default):
            value = self._settings.value(key, default)
            idx = combo.findData(value)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        restore_combo(self.usage_mode_combo, "usage_mode", "general")
        restore_combo(self.screen_mode_combo, "screen_mode", "window")
        restore_combo(self.source_combo, "source_language", "auto")
        restore_combo(self.target_combo, "target_language", "zh")
        restore_combo(self.ocr_backend_combo, "ocr_backend", "auto")
        restore_combo(self.window_crop_combo, "window_crop", "bottom40")
        self._saved_window_key = str(self._settings.value("window_key", ""))
        self._saved_window_profile_key = str(self._settings.value("window_profile_key", ""))
        self._saved_audio_device_key = str(self._settings.value("audio_device_key", ""))
        restore_combo(self.audio_kind_combo, "audio_kind", "microphone" if is_macos() else "system")
        restore_combo(self.audio_source_combo, "audio_source_language", "auto")
        restore_combo(self.audio_target_combo, "audio_target_language", "zh")
        self.partial_caption_check.setChecked(str(self._settings.value("partial_captions", "true")).lower() == "true")
        restore_combo(self.align_combo, "overlay_alignment", "center")
        restore_combo(self.position_combo, "overlay_position", "auto")
        restore_combo(self.width_combo, "overlay_width", "640")
        restore_combo(self.subtitle_display_combo, "overlay_display_mode", "translation")
        restore_combo(self.subtitle_lines_combo, "overlay_max_lines", 2)
        restore_combo(self.subtitle_recent_combo, "overlay_recent_count", 3)
        restore_combo(self.subtitle_retention_combo, "overlay_retention_mode", "smart")

        saved_profile = str(self._settings.value("performance_profile", "auto"))
        idx = self.performance_combo.findData(saved_profile)
        if idx < 0:
            idx = self.performance_combo.findData("auto")
        self.performance_combo.blockSignals(True)
        self.performance_combo.setCurrentIndex(idx)
        self.performance_combo.blockSignals(False)

        self._applying_profile = True
        if saved_profile == "custom":
            restore_combo(self.interval_combo, "refresh_ms", 1000)
            restore_combo(self.ocr_quality_combo, "ocr_quality", "balanced")
            restore_combo(self.whisper_model_combo, "whisper_model", "base")
            restore_combo(self.vad_sensitivity_combo, "vad_sensitivity", "normal")
            self._screen_change_threshold = float(self._settings.value("screen_change_threshold", 1.35))
            self._performance_screen_threshold = self._screen_change_threshold
            self._configure_runtime(
                int(self._settings.value("runtime_cpu_threads", 6)),
                int(self._settings.value("translation_beam", 2)),
                int(self._settings.value("whisper_beam", 2)),
            )
        else:
            self._apply_performance_profile(saved_profile, persist=False)
        self._applying_profile = False
        if saved_profile == "custom":
            self._apply_usage_mode(str(self.usage_mode_combo.currentData() or "general"), update_controls=False, persist=False)
        else:
            saved_partial = self.partial_caption_check.isChecked()
            self._apply_usage_mode(str(self.usage_mode_combo.currentData() or "general"), update_controls=True, persist=False)
            self.partial_caption_check.setChecked(saved_partial)
            self._partial_enabled = saved_partial

        self.opacity_slider.setValue(int(self._settings.value("overlay_opacity", 70)))
        self.font_size_spin.setValue(int(self._settings.value("overlay_font", 18)))
        self.source_font_size_spin.setValue(int(self._settings.value("overlay_source_font", 14)))
        self.outline_width_spin.setValue(int(self._settings.value("overlay_outline_width", 2)))
        self._font_color = str(self._settings.value("overlay_font_color", "#FFFFFF"))
        self._source_font_color = str(self._settings.value("overlay_source_font_color", "#C8C8C8"))
        self._outline_color = str(self._settings.value("overlay_outline_color", "#000000"))
        self._custom_font_path = str(self._settings.value("overlay_custom_font_path", ""))
        if self._custom_font_path and Path(self._custom_font_path).exists():
            QFontDatabase.addApplicationFont(self._custom_font_path)
        self._font_family = str(self._settings.value("overlay_font_family", self.font_family_combo.currentFont().family()))
        if self._font_family:
            self.font_family_combo.setCurrentFont(QFont(self._font_family))
        self.subtitle_smooth_check.setChecked(str(self._settings.value("overlay_smooth_updates", "true")).lower() == "true")
        self._update_font_color_preview()
        self._update_source_font_color_preview()
        self._update_outline_color_preview()

        visible = str(self._settings.value("overlay_visible", "true")).lower() == "true"
        locked = str(self._settings.value("overlay_locked", "false")).lower() == "true"
        passthrough = str(self._settings.value("overlay_passthrough", "false")).lower() == "true"
        shadow = str(self._settings.value("overlay_shadow", "true")).lower() == "true"
        self.overlay_visible_check.setChecked(visible)
        self.overlay_lock_check.setChecked(locked)
        self.overlay_passthrough_check.setChecked(passthrough)
        self.subtitle_shadow_check.setChecked(shadow)
        self._screen_mode_changed()
        self._restoring_settings = False


    def _save_settings(self) -> None:
        if self._restoring_settings:
            return
        values = {
            "usage_mode": self.usage_mode_combo.currentData(),
            "screen_mode": self.screen_mode_combo.currentData(),
            "source_language": self.source_combo.currentData(),
            "target_language": self.target_combo.currentData(),
            "window_key": self.window_combo.currentData() or "",
            "window_profile_key": self._window_profile_id() or self._settings.value("window_profile_key", ""),
            "window_crop": self.window_crop_combo.currentData(),
            "refresh_ms": self.interval_combo.currentData(),
            "ocr_quality": self.ocr_quality_combo.currentData(),
            "ocr_backend": self.ocr_backend_combo.currentData(),
            "audio_kind": self.audio_kind_combo.currentData(),
            "audio_device_key": self.audio_device_combo.currentData() or "",
            "audio_source_language": self.audio_source_combo.currentData(),
            "audio_target_language": self.audio_target_combo.currentData(),
            "whisper_model": self.whisper_model_combo.currentData(),
            "vad_sensitivity": self.vad_sensitivity_combo.currentData(),
            "partial_captions": self.partial_caption_check.isChecked(),
            "performance_profile": self.performance_combo.currentData(),
            "screen_change_threshold": self._screen_change_threshold,
            "runtime_cpu_threads": getattr(self._translator.active_provider, "_cpu_threads", 6),
            "translation_beam": getattr(self._translator.active_provider, "_beam_size", 2),
            "whisper_beam": getattr(self._audio_transcriber, "_beam_size", 2),
            "overlay_opacity": self.opacity_slider.value(),
            "overlay_font": self.font_size_spin.value(),
            "overlay_source_font": self.source_font_size_spin.value(),
            "overlay_font_color": self._font_color,
            "overlay_source_font_color": self._source_font_color,
            "overlay_font_family": self._font_family,
            "overlay_custom_font_path": self._custom_font_path,
            "overlay_display_mode": self.subtitle_display_combo.currentData(),
            "overlay_max_lines": self.subtitle_lines_combo.currentData(),
            "overlay_recent_count": self.subtitle_recent_combo.currentData(),
            "overlay_retention_mode": self.subtitle_retention_combo.currentData(),
            "overlay_smooth_updates": self.subtitle_smooth_check.isChecked(),
            "overlay_shadow": self.subtitle_shadow_check.isChecked(),
            "overlay_outline_width": self.outline_width_spin.value(),
            "overlay_outline_color": self._outline_color,
            "overlay_alignment": self.align_combo.currentData(),
            "overlay_position": self.position_combo.currentData(),
            "overlay_width": self.width_combo.currentData(),
            "overlay_visible": self.overlay_visible_check.isChecked(),
            "overlay_locked": self.overlay_lock_check.isChecked(),
            "overlay_passthrough": self.overlay_passthrough_check.isChecked(),
        }
        for key, value in values.items():
            self._settings.setValue(key, value)
        if not self._applying_game_profile and self.screen_mode_combo.currentData() == "window":
            self._save_current_game_profile()


    def _apply_overlay_settings(self) -> None:
        self._overlay.set_preferences(
            opacity_percent=self.opacity_slider.value(),
            font_size=self.font_size_spin.value(),
            source_font_size=self.source_font_size_spin.value(),
            font_color=self._font_color,
            source_font_color=self._source_font_color,
            font_family=self._font_family,
            display_mode=self.subtitle_display_combo.currentData(),
            shadow_enabled=self.subtitle_shadow_check.isChecked(),
            outline_width=self.outline_width_spin.value(),
            outline_color=self._outline_color,
            max_lines=int(self.subtitle_lines_combo.currentData() or 0),
            recent_count=int(self.subtitle_recent_combo.currentData() or 3),
            retention_mode=str(self.subtitle_retention_combo.currentData() or "smart"),
            smooth_updates=self.subtitle_smooth_check.isChecked(),
            alignment=self.align_combo.currentData(),
            position_mode=self.position_combo.currentData(),
            width_mode=self.width_combo.currentData(),
        )
        self._overlay.set_locked(self.overlay_lock_check.isChecked())
        self._overlay.set_mouse_passthrough(self.overlay_passthrough_check.isChecked())


    def _overlay_setting_changed(self, *_args) -> None:
        self._apply_overlay_settings()
        self._save_settings()


    def _set_color_preview(self, label: QLabel, value: str) -> None:
        color = QColor(value)
        lum = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
        fg = "#000000" if lum > 160 else "#FFFFFF"
        label.setText(value)
        label.setStyleSheet(f"background:{value}; color:{fg}; padding:5px 8px; border-radius:4px;")


    def _choose_font_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._font_color), self, "选择译文颜色")
        if color.isValid():
            self._font_color = color.name().upper()
            self._update_font_color_preview()
            self._overlay_setting_changed()


    def _choose_source_font_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._source_font_color), self, "选择原文字幕颜色")
        if color.isValid():
            self._source_font_color = color.name().upper()
            self._update_source_font_color_preview()
            self._overlay_setting_changed()


    def _choose_outline_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._outline_color), self, "选择字幕描边颜色")
        if color.isValid():
            self._outline_color = color.name().upper()
            self._update_outline_color_preview()
            self._overlay_setting_changed()


    def _update_font_color_preview(self) -> None:
        self._set_color_preview(self.font_color_preview, self._font_color)


    def _update_source_font_color_preview(self) -> None:
        self._set_color_preview(self.source_font_color_preview, self._source_font_color)


    def _update_outline_color_preview(self) -> None:
        self._set_color_preview(self.outline_color_preview, self._outline_color)


    def _font_family_changed(self, font: QFont) -> None:
        self._font_family = font.family()
        self._overlay_setting_changed()


    def _import_custom_font(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "导入字幕字体", "", "Font files (*.ttf *.otf *.ttc)")
        if not path:
            return
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id < 0:
            QMessageBox.warning(self, "Screen Translator", "字体加载失败，请选择有效的 TTF / OTF / TTC 字体文件。")
            return
        families = QFontDatabase.applicationFontFamilies(font_id)
        if not families:
            QMessageBox.warning(self, "Screen Translator", "字体已加载，但没有读取到字体家族名称。")
            return
        self._custom_font_path = path
        self._font_family = families[0]
        self.font_family_combo.setCurrentFont(QFont(self._font_family))
        self._overlay_setting_changed()


    def _apply_subtitle_preset(self) -> None:
        key = str(self.subtitle_preset_combo.currentData() or "course")
        preset = SUBTITLE_PRESETS.get(key)
        if not preset:
            return
        self._restoring_settings = True
        try:
            self._set_combo_data(self.subtitle_display_combo, preset["display_mode"])
            self._set_combo_data(self.subtitle_recent_combo, preset["recent_count"])
            self._set_combo_data(self.subtitle_retention_combo, preset["retention_mode"])
            self._set_combo_data(self.subtitle_lines_combo, preset["max_lines"])
            self.opacity_slider.setValue(int(preset["opacity"]))
            self.font_size_spin.setValue(int(preset["translation_font"]))
            self.source_font_size_spin.setValue(int(preset["source_font"]))
            self._font_color = str(preset["translation_color"])
            self._source_font_color = str(preset["source_color"])
            self.outline_width_spin.setValue(int(preset["outline_width"]))
            self._outline_color = str(preset["outline_color"])
            self.subtitle_shadow_check.setChecked(bool(preset["shadow"]))
            self.subtitle_smooth_check.setChecked(bool(preset["smooth_updates"]))
            self._set_combo_data(self.align_combo, preset["alignment"])
            self._set_combo_data(self.position_combo, preset["position"])
            self._set_combo_data(self.width_combo, preset["width"])
            self._update_font_color_preview()
            self._update_source_font_color_preview()
            self._update_outline_color_preview()
        finally:
            self._restoring_settings = False
        self._apply_overlay_settings()
        self._save_settings()
        self.status_label.setText(f"已应用字幕预设：{preset['label']}")


    def _overlay_visibility_changed(self, checked: bool) -> None:
        if not checked:
            self._overlay.hide()
        elif self.translation_edit.toPlainText().strip():
            self._overlay.show_translation(
                self.translation_edit.toPlainText(),
                self._selected_rect if not self._audio_running else None,
                audio_mode=self._audio_running,
                source_text=self.source_edit.toPlainText(),
            )
        self._save_settings()


    def _overlay_lock_requested(self, checked: bool) -> None:
        if self._overlay.locked != checked:
            self._overlay.set_locked(checked)
        self._save_settings()


    def _overlay_lock_changed(self, locked: bool) -> None:
        if self.overlay_lock_check.isChecked() != locked:
            self.overlay_lock_check.blockSignals(True)
            self.overlay_lock_check.setChecked(locked)
            self.overlay_lock_check.blockSignals(False)
        self._save_settings()


    def _overlay_closed(self) -> None:
        self.overlay_visible_check.blockSignals(True)
        self.overlay_visible_check.setChecked(False)
        self.overlay_visible_check.blockSignals(False)
        self._save_settings()


    def _reset_overlay_position(self) -> None:
        idx = self.position_combo.findData("auto")
        if idx >= 0:
            self.position_combo.setCurrentIndex(idx)
        self._overlay.reset_position()


    def _swap_screen_languages(self) -> None:
        src = str(self.source_combo.currentData() or "auto")
        dst = str(self.target_combo.currentData() or "zh")
        if src == "auto":
            # Auto cannot be a target. Use the current target as source and choose Chinese as a safe target.
            src = dst
            dst = "zh" if src != "zh" else "en"
        else:
            src, dst = dst, src
        self._set_combo_data(self.source_combo, src)
        self._set_combo_data(self.target_combo, dst)
        self._save_settings()


    def _swap_audio_languages(self) -> None:
        src = str(self.audio_source_combo.currentData() or "auto")
        dst = str(self.audio_target_combo.currentData() or "zh")
        if src == "auto":
            src = dst
            dst = "zh" if src != "zh" else "en"
        else:
            src, dst = dst, src
        self._set_combo_data(self.audio_source_combo, src)
        self._set_combo_data(self.audio_target_combo, dst)
        self._save_settings()


    def _append_history_row(self, entry) -> None:
        if not hasattr(self, "history_table"):
            return
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        values = [
            entry.created_at,
            entry.mode,
            f"{entry.source_lang} → {entry.target_lang}",
            entry.source_text.replace("\n", " "),
            entry.translated_text.replace("\n", " "),
            entry.domains or "通用",
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            if col == 3:
                item.setToolTip(entry.source_text)
                item.setData(Qt.ItemDataRole.UserRole, entry.source_text)
            elif col == 4:
                item.setToolTip(entry.translated_text)
                item.setData(Qt.ItemDataRole.UserRole, entry.translated_text)
            self.history_table.setItem(row, col, item)
        self.history_table.scrollToBottom()


    def _history_selection_changed(self) -> None:
        rows = self.history_table.selectionModel().selectedRows() if self.history_table.selectionModel() else []
        if not rows:
            return
        row = rows[-1].row()
        src_item = self.history_table.item(row, 3)
        dst_item = self.history_table.item(row, 4)
        if src_item is not None:
            self.source_edit.setPlainText(str(src_item.data(Qt.ItemDataRole.UserRole) or src_item.text()))
        if dst_item is not None:
            self.translation_edit.setPlainText(str(dst_item.data(Qt.ItemDataRole.UserRole) or dst_item.text()))


    def _record_history(self, mode: str, result: dict) -> None:
        domains = ", ".join(result.get("domains", []))
        entry = self._history.add(
            mode,
            str(result.get("source_lang", "")),
            str(result.get("target_lang", "zh")),
            str(result.get("source_text", "")),
            str(result.get("translated_text", "")),
            domains,
        )
        self._append_history_row(entry)


    def _load_history(self) -> None:
        if not hasattr(self, "history_table"):
            return
        self.history_table.setRowCount(0)
        for entry in self._history.list():
            self._append_history_row(entry)


    def _export_history(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出全部翻译记录",
            "ScreenTranslator-history.txt",
            "Text files (*.txt)",
        )
        if not path:
            return
        self._history.export_txt(path)
        self.status_label.setText(f"翻译记录已导出：{path}")


    def _clear_history(self) -> None:
        answer = QMessageBox.question(
            self,
            "清空翻译记录",
            "确定清空本机保存的全部翻译记录吗？此操作不会删除模型。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._history.clear()
        self.history_table.setRowCount(0)
        self.status_label.setText("全部翻译记录已清空。")


    def _clear_context(self) -> None:
        self._pipeline.context.clear()
        self.status_label.setText("上下文缓存已清空；历史翻译记录仍保留。")


    def _usage_mode_changed(self, *_args) -> None:
        if self._restoring_settings:
            return
        self._apply_usage_mode(str(self.usage_mode_combo.currentData() or "general"))


    def _apply_usage_mode(
        self,
        key: str,
        *,
        update_controls: bool = True,
        persist: bool = True,
    ) -> None:
        info = USAGE_MODES.get(key, USAGE_MODES["general"])
        self._stable_debounce_ms = int(info["stable_debounce_ms"])
        self._partial_enabled = bool(info["partial_enabled"])
        self._partial_interval_ms = int(info["partial_interval_ms"])
        self._vad_end_silence_ms = int(info["vad_end_silence_ms"])
        self._max_utterance_ms = int(info["max_utterance_ms"])
        self._screen_change_threshold = min(
            float(getattr(self, "_performance_screen_threshold", 1.35)),
            float(info.get("screen_change_threshold", 1.35)),
        )
        if update_controls:
            self._applying_profile = True
            self._set_combo_data(self.interval_combo, int(info["refresh_ms"]))
            self._set_combo_data(self.ocr_quality_combo, str(info["ocr_quality"]))
            self.partial_caption_check.setChecked(self._partial_enabled)
            self._applying_profile = False
        else:
            # User can explicitly disable provisional subtitles even in a low-latency mode.
            self._partial_enabled = self.partial_caption_check.isChecked()
        if self._live_mode:
            self._live_timer.setInterval(int(self.interval_combo.currentData()))
        if persist:
            self._save_settings()
        if hasattr(self, "status_label"):
            self.status_label.setText(
                f"已切换：{info['label']} · 稳定检测 {self._stable_debounce_ms}ms · "
                f"{'流式临时字幕' if self.partial_caption_check.isChecked() else '仅最终字幕'}"
            )


    def _window_profile_id(self) -> str:
        key = self.window_combo.currentData() if hasattr(self, "window_combo") else None
        if not key:
            return ""
        info = get_application_window(str(key))
        return info.profile_key if info is not None else ""


    def _game_profile_snapshot(self) -> dict:
        return {
            "usage_mode": self.usage_mode_combo.currentData(),
            "source_language": self.source_combo.currentData(),
            "target_language": self.target_combo.currentData(),
            "window_crop": self.window_crop_combo.currentData(),
            "ocr_quality": self.ocr_quality_combo.currentData(),
            "ocr_backend": self.ocr_backend_combo.currentData(),
            "performance_profile": self.performance_combo.currentData(),
            "overlay_opacity": self.opacity_slider.value(),
            "overlay_font": self.font_size_spin.value(),
            "overlay_source_font": self.source_font_size_spin.value(),
            "overlay_font_color": self._font_color,
            "overlay_source_font_color": self._source_font_color,
            "overlay_font_family": self._font_family,
            "overlay_custom_font_path": self._custom_font_path,
            "overlay_display_mode": self.subtitle_display_combo.currentData(),
            "overlay_max_lines": self.subtitle_lines_combo.currentData(),
            "overlay_recent_count": self.subtitle_recent_combo.currentData(),
            "overlay_retention_mode": self.subtitle_retention_combo.currentData(),
            "overlay_smooth_updates": self.subtitle_smooth_check.isChecked(),
            "overlay_shadow": self.subtitle_shadow_check.isChecked(),
            "overlay_outline_width": self.outline_width_spin.value(),
            "overlay_outline_color": self._outline_color,
            "overlay_alignment": self.align_combo.currentData(),
            "overlay_position": self.position_combo.currentData(),
            "overlay_width": self.width_combo.currentData(),
        }


    def _save_current_game_profile(self) -> None:
        profile_id = self._window_profile_id()
        if profile_id:
            try:
                self._profiles.save(profile_id, self._game_profile_snapshot())
            except Exception:
                pass


    def _window_profile_changed(self, *_args) -> None:
        if self._restoring_settings or self._applying_game_profile:
            return
        profile_id = self._window_profile_id()
        if not profile_id:
            return
        data = self._profiles.load(profile_id)
        if not data:
            return
        self._applying_game_profile = True
        try:
            self._set_combo_data(self.usage_mode_combo, data.get("usage_mode", "game"))
            self._set_combo_data(self.source_combo, data.get("source_language", "auto"))
            self._set_combo_data(self.target_combo, data.get("target_language", "zh"))
            self._set_combo_data(self.window_crop_combo, data.get("window_crop", "bottom40"))
            self._set_combo_data(self.ocr_quality_combo, data.get("ocr_quality", "balanced"))
            self._set_combo_data(self.ocr_backend_combo, data.get("ocr_backend", "auto"))
            perf = data.get("performance_profile")
            if perf is not None:
                self._set_combo_data(self.performance_combo, perf)
            self.opacity_slider.setValue(int(data.get("overlay_opacity", self.opacity_slider.value())))
            self.font_size_spin.setValue(int(data.get("overlay_font", self.font_size_spin.value())))
            self.source_font_size_spin.setValue(int(data.get("overlay_source_font", self.source_font_size_spin.value())))
            self._font_color = str(data.get("overlay_font_color", self._font_color))
            self._source_font_color = str(data.get("overlay_source_font_color", self._source_font_color))
            self._outline_color = str(data.get("overlay_outline_color", self._outline_color))
            self._font_family = str(data.get("overlay_font_family", self._font_family))
            self._custom_font_path = str(data.get("overlay_custom_font_path", self._custom_font_path))
            if self._custom_font_path and Path(self._custom_font_path).exists():
                QFontDatabase.addApplicationFont(self._custom_font_path)
            if self._font_family:
                self.font_family_combo.setCurrentFont(QFont(self._font_family))
            self._update_font_color_preview()
            self._update_source_font_color_preview()
            self._update_outline_color_preview()
            self._set_combo_data(self.subtitle_display_combo, data.get("overlay_display_mode", "translation"))
            self._set_combo_data(self.subtitle_lines_combo, data.get("overlay_max_lines", 2))
            self._set_combo_data(self.subtitle_recent_combo, data.get("overlay_recent_count", 3))
            self._set_combo_data(self.subtitle_retention_combo, data.get("overlay_retention_mode", "smart"))
            self.subtitle_smooth_check.setChecked(bool(data.get("overlay_smooth_updates", True)))
            self.subtitle_shadow_check.setChecked(bool(data.get("overlay_shadow", True)))
            self.outline_width_spin.setValue(int(data.get("overlay_outline_width", 2)))
            self._set_combo_data(self.align_combo, data.get("overlay_alignment", "center"))
            self._set_combo_data(self.position_combo, data.get("overlay_position", "auto"))
            self._set_combo_data(self.width_combo, data.get("overlay_width", "640"))
            self._apply_usage_mode(str(self.usage_mode_combo.currentData() or "game"), update_controls=False, persist=False)
            self._apply_overlay_settings()
            self.status_label.setText("已自动载入此应用/游戏的独立 Profile。")
        finally:
            self._applying_game_profile = False


    def _redetect_hardware(self) -> None:
        self._hardware_info = detect_hardware()
        self._recommended_profile, self._recommendation_reason = recommend_profile(self._hardware_info)
        self._refresh_performance_summary()
        self._perf_timer.start()
        self._update_runtime_metrics()
        if self.performance_combo.currentData() == "auto":
            self._apply_performance_profile("auto")


    def _refresh_performance_summary(self) -> None:
        self.hardware_text.setPlainText(self._hardware_info.summary)
        recommended_label = PERFORMANCE_PROFILES[self._recommended_profile]["label"]
        self.performance_recommend_label.setText(
            f"自动推荐：{recommended_label} · 依据：{self._recommendation_reason}"
        )
        active = self.performance_combo.currentData()
        if active == "auto":
            effective = self._recommended_profile
            active_label = f"自动 → {PERFORMANCE_PROFILES[effective]['label']}"
        elif active == "custom":
            active_label = "自定义"
            effective = None
        else:
            effective = str(active)
            active_label = PERFORMANCE_PROFILES[effective]["label"]

        if effective:
            profile = PERFORMANCE_PROFILES[effective]
            self.performance_details_label.setText(
                f"当前：{active_label}。{profile['description']}\n"
                f"屏幕 {profile['refresh_ms']/1000:g}s / OCR {profile['ocr_quality']} / "
                f"Whisper {profile['whisper_model']} / VAD {profile['vad_sensitivity']} / "
                f"最多 {profile['max_cpu_threads']} 推理线程。"
            )
        else:
            self.performance_details_label.setText(
                "当前：自定义。你修改了扫描频率、OCR 质量、Whisper 模型或 VAD 灵敏度；程序会保留这些设置。"
            )


    def _performance_profile_changed(self, *_args) -> None:
        if self._applying_profile:
            return
        self._apply_performance_profile(str(self.performance_combo.currentData()))


    def _mark_performance_custom(self, *_args) -> None:
        if self._applying_profile or self._restoring_settings or not hasattr(self, "performance_combo"):
            return
        if self.performance_combo.currentData() == "custom":
            return
        idx = self.performance_combo.findData("custom")
        if idx >= 0:
            self.performance_combo.blockSignals(True)
            self.performance_combo.setCurrentIndex(idx)
            self.performance_combo.blockSignals(False)
        self._refresh_performance_summary()
        self._perf_timer.start()
        self._update_runtime_metrics()
        self._save_settings()


    @staticmethod
    def _set_combo_data(combo: QComboBox, value) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)


    def _configure_runtime(self, cpu_threads: int, translation_beam: int, whisper_beam: int, prefer_gpu: bool = True) -> None:
        available = max(1, self._hardware_info.logical_cores or cpu_threads)
        threads = max(1, min(int(cpu_threads), available))
        self._translator.configure(cpu_threads=threads, beam_size=translation_beam, prefer_gpu=prefer_gpu)
        self._audio_transcriber.configure(cpu_threads=threads, beam_size=whisper_beam, prefer_gpu=prefer_gpu)


    def _apply_performance_profile(self, profile_key: str, *, persist: bool = True) -> None:
        if profile_key == "custom":
            self._refresh_performance_summary()
            if persist:
                self._save_settings()
            return
        effective = self._recommended_profile if profile_key == "auto" else profile_key
        profile = profile_settings(effective)

        self._applying_profile = True
        self._set_combo_data(self.interval_combo, profile["refresh_ms"])
        self._set_combo_data(self.ocr_quality_combo, profile["ocr_quality"])
        self._set_combo_data(self.whisper_model_combo, profile["whisper_model"])
        self._set_combo_data(self.vad_sensitivity_combo, profile["vad_sensitivity"])
        self._applying_profile = False

        self._performance_screen_threshold = float(profile["screen_change_threshold"])
        mode_info = USAGE_MODES.get(str(self.usage_mode_combo.currentData() or "general"), USAGE_MODES["general"])
        self._screen_change_threshold = min(
            self._performance_screen_threshold,
            float(mode_info.get("screen_change_threshold", self._performance_screen_threshold)),
        )
        self._configure_runtime(
            int(profile["max_cpu_threads"]),
            int(profile["translation_beam"]),
            int(profile["whisper_beam"]),
            bool(profile.get("prefer_gpu", True)),
        )
        if self._live_mode:
            self._live_timer.setInterval(int(self.interval_combo.currentData()))
        self._refresh_performance_summary()
        if persist:
            self._save_settings()


    def _update_runtime_metrics(self) -> None:
        if not hasattr(self, "system_cpu_bar"):
            return
        metrics = self._runtime_monitor.sample()
        self.system_cpu_bar.setValue(int(round(metrics["system_cpu"])))
        self.system_cpu_bar.setFormat(f"{metrics['system_cpu']:.0f}%")
        self.system_ram_bar.setValue(int(round(metrics["system_memory_percent"])))
        self.system_ram_bar.setFormat(
            f"{metrics['system_memory_percent']:.0f}% · {metrics['system_memory_used_gb']:.1f}/{metrics['system_memory_total_gb']:.1f} GB"
        )
        self.process_cpu_label.setText(
            f"Screen Translator CPU：{metrics['process_cpu']:.1f}%（psutil 单核 = 100%）"
        )
        self.process_ram_label.setText(f"Screen Translator 内存：{metrics['process_memory_mb']:.0f} MB")
        translation_backend = self._translator.runtime_label()
        asr_backend = self._audio_transcriber.runtime_label()
        self.runtime_backend_label.setText(f"推理后端：{translation_backend} · {asr_backend}")
        self.accel_label.setText(f"加速：{translation_backend.replace('NLLB · ', '')} / {asr_backend.replace('Whisper · ', '')}")


    def _screen_mode_changed(self, *_args) -> None:
        if not hasattr(self, "screen_mode_combo"):
            return
        is_window = self.screen_mode_combo.currentData() == "window"
        for widget in (self.window_label, self.window_combo, self.window_crop_label, self.window_crop_combo):
            widget.setEnabled(is_window)
        self.once_button.setText("翻译选中窗口" if is_window else "框选并翻译")
        self.live_button.setText(
            "停止实时翻译" if self._live_mode else ("开始窗口实时翻译" if is_window else "开始固定区域实时翻译")
        )
        if not self._restoring_settings and hasattr(self, "performance_combo"):
            self._save_settings()


    def _refresh_windows(self, *_args) -> None:
        if not hasattr(self, "window_combo"):
            return
        current = self.window_combo.currentData() or getattr(self, "_saved_window_key", "")
        saved_profile = getattr(self, "_saved_window_profile_key", "")
        self.window_combo.clear()
        try:
            windows = list_application_windows()
        except Exception as exc:
            self.window_combo.addItem(f"读取窗口失败：{exc}", None)
            return
        profile_index = -1
        for info in windows:
            self.window_combo.addItem(info.display_name, info.key)
            if saved_profile and info.profile_key == saved_profile:
                profile_index = self.window_combo.count() - 1
        if not windows:
            self.window_combo.addItem("未找到可捕获窗口", None)
        elif current:
            idx = self.window_combo.findData(str(current))
            if idx >= 0:
                self.window_combo.setCurrentIndex(idx)
            elif profile_index >= 0:
                self.window_combo.setCurrentIndex(profile_index)
        elif profile_index >= 0:
            self.window_combo.setCurrentIndex(profile_index)
        self._saved_window_key = ""
        self._saved_window_profile_key = ""


    def _current_window_rect(self) -> QRect | None:
        key = self.window_combo.currentData()
        if not key:
            return None
        info = get_application_window(str(key))
        if info is None:
            return None
        return crop_window_rect(info.rect, str(self.window_crop_combo.currentData()))


    def _start_screen_once(self) -> None:
        if not self._require_model("translation-nllb", self._start_screen_once):
            return
        if self.screen_mode_combo.currentData() == "window":
            rect = self._current_window_rect()
            if rect is None:
                QMessageBox.information(self, "Screen Translator", "所选窗口已关闭或无法读取，请刷新窗口列表。")
                return
            if self._audio_running:
                self._stop_audio()
            self._live_mode = False
            self._selected_rect = rect
            self._screen_signature = None
            self._last_ocr_text = ""
            self._screen_pending_stability = False
            self._stable_detector.reset()
            self._capture_and_translate()
            return
        self._start_selection(live=False)


    def _toggle_live(self) -> None:
        if self._live_mode:
            self._stop_live()
            return
        if not self._require_model("translation-nllb", self._toggle_live):
            return
        if self._audio_running:
            self._stop_audio()
        if self.screen_mode_combo.currentData() == "window":
            rect = self._current_window_rect()
            if rect is None:
                QMessageBox.information(self, "Screen Translator", "所选窗口已关闭或无法读取，请刷新窗口列表。")
                return
            self._selected_rect = rect
            self._live_mode = True
            self._screen_signature = None
            self._last_ocr_text = ""
            self._screen_pending_stability = False
            self._stable_detector.reset()
            self.live_button.setText("停止实时翻译")
            self.status_label.setText("窗口实时翻译已启动。游戏建议使用无边框/窗口化模式。")
            self._live_timer.start(int(self.interval_combo.currentData()))
            QTimer.singleShot(80, self._capture_and_translate)
        else:
            self._start_selection(live=True)


    def _start_selection(self, live: bool) -> None:
        if self._busy:
            return
        if self._audio_running:
            self._stop_audio()
        self._live_mode = live
        self._screen_signature = None
        self._last_ocr_text = ""
        self._screen_pending_stability = False
        self._stable_detector.reset()
        self.hide()
        self._overlay.hide()
        self._selector = RegionSelector()
        self._selector.region_selected.connect(self._region_selected)
        self._selector.cancelled.connect(self._selection_cancelled)
        self._selector.show()


    def _selection_cancelled(self) -> None:
        self._live_mode = False
        self.show()
        self.raise_()
        self.activateWindow()
        self.status_label.setText("已取消框选。")


    def _region_selected(self, rect: QRect) -> None:
        self._selected_rect = rect
        self._screen_signature = None
        self._last_ocr_text = ""
        self._screen_pending_stability = False
        if self._live_mode:
            self.live_button.setText("停止实时翻译")
            self.status_label.setText("实时翻译已启动。")
            self._live_timer.start(int(self.interval_combo.currentData()))
        else:
            self.show()
            self.raise_()
            self.activateWindow()
        QTimer.singleShot(180, self._capture_and_translate)


    def _live_tick(self) -> None:
        if self._busy:
            return
        if self.screen_mode_combo.currentData() == "window":
            rect = self._current_window_rect()
            if rect is None:
                self._stop_live(keep_status=True)
                self.status_label.setText("所选应用窗口已关闭，实时翻译已停止。")
                return
            self._selected_rect = rect
        if self._selected_rect is not None:
            self._capture_and_translate()


    @staticmethod
    def _image_signature(image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        sy = max(1, h // 32)
        sx = max(1, w // 48)
        sample = image[::sy, ::sx, :].astype(np.float32)
        return sample.mean(axis=2)


    def _capture_and_translate(self) -> None:
        if self._busy or self._selected_rect is None:
            return
        try:
            image = capture_region(self._selected_rect)
        except Exception as exc:
            self._on_failed(str(exc))
            return

        if self._live_mode:
            sig = self._image_signature(image)
            if (
                not self._screen_pending_stability
                and self._screen_signature is not None
                and self._screen_signature.shape == sig.shape
            ):
                diff = float(np.mean(np.abs(sig - self._screen_signature)))
                if diff < self._screen_change_threshold:
                    self.status_label.setText("画面没有明显变化，等待下一次扫描…")
                    return
            self._screen_signature = sig

        self._busy = True
        self._set_screen_buttons_enabled(False)
        if self.screen_mode_combo.currentData() == "window":
            profile_id = self._window_profile_id() or "window"
            channel = f"game:{profile_id}"
        else:
            channel = "screen"
        worker = TranslationWorker(
            image,
            self.source_combo.currentData(),
            self.target_combo.currentData(),
            self.ocr_quality_combo.currentData(),
            self._ocr,
            self._pipeline,
            previous_text=self._last_ocr_text if self._live_mode else "",
            channel=channel,
            ocr_backend=str(self.ocr_backend_combo.currentData() or "auto"),
            stable_detector=self._stable_detector,
            debounce_ms=self._stable_debounce_ms if self._live_mode else 0,
            force=not self._live_mode,
            allowed_languages=set(self._language_packs.installed_codes()) if hasattr(self, "_language_packs") else None,
            task_id=getattr(self, "_screen_task_generation", 0),
        )
        worker.signals.status.connect(self.status_label.setText)
        worker.signals.finished.connect(self._on_screen_finished)
        worker.signals.failed.connect(self._on_failed)
        self._thread_pool.start(worker)


    def _on_screen_finished(self, result: dict) -> None:
        self._busy = False
        self._set_screen_buttons_enabled(True)
        if result.get("pending"):
            self._screen_pending_stability = True
            waited = int(result.get("waited_ms", 0))
            self.status_label.setText(
                f"文字仍在变化，Stable Text Detector 等待稳定… {waited}/{self._stable_debounce_ms}ms"
            )
            if self._live_mode:
                # Do not wait for the next normal refresh interval just to satisfy the debounce.
                # A short one-shot retry gives the course preset an actual ~80 ms stability gate
                # while normal OCR scans can remain less frequent.
                retry_ms = max(40, self._stable_debounce_ms - waited + 10)
                QTimer.singleShot(retry_ms, self._capture_and_translate)
                if self.screen_mode_combo.currentData() != "window":
                    self._show_controls_away_from_region()
            return
        if result.get("unchanged"):
            self._screen_pending_stability = False
            self.status_label.setText("识别文字没有变化，已跳过翻译。")
            if self._live_mode and self.screen_mode_combo.currentData() != "window":
                self._show_controls_away_from_region()
            return

        self._screen_pending_stability = False
        self._last_ocr_text = result["source_text"]
        self.source_edit.setPlainText(result["source_text"])
        self.translation_edit.setPlainText(result["translated_text"])
        names = {code: info.get("label", code) for code, info in LANGUAGE_CATALOG.items()}
        target_name = names.get(result.get("target_lang", "zh"), result.get("target_lang", "zh"))
        domains = ", ".join(result.get("domains", [])) or "通用"
        ctx = int(result.get("context_count", 0))
        terms = int(result.get("terminology_count", 0))
        ocr_backend = str(result.get("ocr_backend", ""))
        fallback = " · OCR回退" if result.get("ocr_fallback") else ""
        provider = str(result.get("provider", ""))
        self.status_label.setText(
            f"完成 · {names.get(result['source_lang'], result['source_lang'])} → {target_name} · "
            f"上下文 {ctx} 条 · 术语 {terms} 个 · 词库 {domains} · OCR {ocr_backend}{fallback}"
            + (f" · {provider}" if provider else "")
        )
        mode = "游戏窗口" if self.screen_mode_combo.currentData() == "window" else "屏幕"
        self._record_history(mode, result)
        if self._selected_rect is not None and self.overlay_visible_check.isChecked():
            self._apply_overlay_settings()
            self._overlay.show_translation(
                result["translated_text"],
                self._selected_rect,
                source_text=result["source_text"],
            )
        if self._live_mode:
            if self.screen_mode_combo.currentData() != "window":
                self._show_controls_away_from_region()
        else:
            self.show()
            self.raise_()
            self.activateWindow()


    def _show_controls_away_from_region(self) -> None:
        if self._selected_rect is None:
            self.show()
            return
        screen = QApplication.screenAt(self._selected_rect.center()) or QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else self._selected_rect
        margin = 12
        candidates = [
            (self._selected_rect.right() + margin, self._selected_rect.top()),
            (self._selected_rect.left() - self.width() - margin, self._selected_rect.top()),
            (available.right() - self.width(), available.top()),
            (available.left(), available.bottom() - self.height()),
        ]
        for x, y in candidates:
            window_rect = QRect(x, y, self.width(), self.height())
            if available.contains(window_rect) and not window_rect.intersects(self._selected_rect):
                self.move(x, y)
                break
        self.show()
        self.raise_()


    def _stop_live(self, keep_status: bool = False) -> None:
        self._live_timer.stop()
        self._live_mode = False
        self._screen_signature = None
        self._last_ocr_text = ""
        self._screen_pending_stability = False
        self._stable_detector.reset()
        self._screen_mode_changed()
        if not keep_status:
            self.status_label.setText("实时翻译已停止。")
        self._set_screen_buttons_enabled(True)


    def _set_screen_buttons_enabled(self, enabled: bool) -> None:
        self.once_button.setEnabled(enabled and not self._live_mode and not self._audio_running)
        self.live_button.setEnabled((enabled or self._live_mode) and not self._audio_running)


    def _refresh_audio_devices(self, *_args) -> None:
        if not hasattr(self, "audio_device_combo"):
            return
        kind = self.audio_kind_combo.currentData()
        current = self.audio_device_combo.currentData() or getattr(self, "_saved_audio_device_key", "")
        self.audio_device_combo.clear()
        try:
            devices = list_audio_devices(kind)
        except Exception as exc:
            self.audio_device_combo.addItem(f"读取设备失败：{exc}", None)
            return
        for dev in devices:
            self.audio_device_combo.addItem(dev.name, dev.key)
        if not devices:
            text = "未找到系统声音回环设备" if kind == "system" else "未找到麦克风"
            self.audio_device_combo.addItem(text, None)
        elif current:
            idx = self.audio_device_combo.findData(current)
            if idx >= 0:
                self.audio_device_combo.setCurrentIndex(idx)
        self._saved_audio_device_key = ""


    def _toggle_audio(self) -> None:
        if self._audio_running:
            self._stop_audio()
            return
        if not self._require_model("translation-nllb", self._toggle_audio):
            return
        speech_model_id = self._audio_transcriber.required_model_id(
            str(self.whisper_model_combo.currentData() or "base")
        )
        if not self._require_model(speech_model_id, self._toggle_audio):
            return
        if self._live_mode:
            self._stop_live()
        if self._busy:
            return
        device_key = self.audio_device_combo.currentData()
        if not device_key:
            QMessageBox.information(
                self,
                "Screen Translator",
                "当前没有可用的音频设备。Windows 系统声音请确认扬声器正在启用；macOS 当前测试版优先使用麦克风。",
            )
            return

        self._save_settings()
        self._audio_running = True
        self.audio_button.setText("停止声音翻译")
        self._set_screen_buttons_enabled(False)
        self.audio_kind_combo.setEnabled(False)
        self.audio_device_combo.setEnabled(False)
        self.whisper_model_combo.setEnabled(False)
        self.vad_sensitivity_combo.setEnabled(False)
        self.audio_source_combo.setEnabled(False)
        self.audio_target_combo.setEnabled(False)
        self.partial_caption_check.setEnabled(False)

        worker = AudioTranslationWorker(
            kind=self.audio_kind_combo.currentData(),
            device_key=str(device_key),
            source_mode=self.audio_source_combo.currentData(),
            target_lang=self.audio_target_combo.currentData(),
            model_size=self.whisper_model_combo.currentData(),
            transcriber=self._audio_transcriber,
            pipeline=self._pipeline,
            vad_sensitivity=str(self.vad_sensitivity_combo.currentData()),
            partial_enabled=self.partial_caption_check.isChecked(),
            partial_interval_ms=self._partial_interval_ms,
            end_silence_ms=self._vad_end_silence_ms,
            max_utterance_ms=self._max_utterance_ms,
            allowed_languages=set(self._language_packs.installed_codes()) if hasattr(self, "_language_packs") else None,
        )
        self._audio_worker = worker
        worker.signals.status.connect(self.status_label.setText)
        worker.signals.transcript.connect(self._on_audio_transcript)
        worker.signals.failed.connect(self._on_audio_failed)
        worker.signals.stopped.connect(self._on_audio_stopped)
        self._thread_pool.start(worker)
        self.status_label.setText("正在启动低延迟声音流水线：持续录音 → Partial ASR → 翻译 → Final Correction…")


    def _on_audio_transcript(self, result: dict) -> None:
        partial = bool(result.get("partial"))
        self.source_edit.setPlainText(result["source_text"])
        self.translation_edit.setPlainText(result["translated_text"])
        names = {code: info.get("label", code) for code, info in LANGUAGE_CATALOG.items()}
        target_name = names.get(result.get("target_lang", "zh"), result.get("target_lang", "zh"))
        prob = float(result.get("language_probability", 0.0))
        suffix = f" · 语言置信度 {prob:.0%}" if prob > 0 else ""
        domains = ", ".join(result.get("domains", [])) or "通用"
        ctx = int(result.get("context_count", 0))
        terms = int(result.get("terminology_count", 0))
        provider = str(result.get("provider", ""))
        asr_backend = str(result.get("asr_backend", ""))
        if partial:
            self.status_label.setText(
                f"临时字幕 · {names.get(result['source_lang'], result['source_lang'])} → {target_name} · "
                f"边说边译 · {asr_backend}"
            )
        else:
            self.status_label.setText(
                f"最终字幕 · {names.get(result['source_lang'], result['source_lang'])} → {target_name}{suffix} · "
                f"上下文 {ctx} 条 · 术语 {terms} 个 · 词库 {domains}"
                + (f" · {provider}" if provider else "")
                + (f" · {asr_backend}" if asr_backend else "")
            )
            self._record_history("声音", result)
        if self.overlay_visible_check.isChecked():
            self._apply_overlay_settings()
            self._overlay.show_translation(
                result["translated_text"],
                None,
                audio_mode=True,
                source_text=result["source_text"],
                state="partial" if partial else "final",
            )


    def _on_audio_failed(self, message: str) -> None:
        self.status_label.setText("声音翻译失败：" + message)
        QMessageBox.warning(self, "Screen Translator", message)


    def _on_audio_stopped(self) -> None:
        self._audio_worker = None
        self._audio_running = False
        self.audio_button.setText("开始监听并翻译")
        self.audio_kind_combo.setEnabled(True)
        self.audio_device_combo.setEnabled(True)
        self.whisper_model_combo.setEnabled(True)
        self.vad_sensitivity_combo.setEnabled(True)
        self.audio_source_combo.setEnabled(True)
        self.audio_target_combo.setEnabled(True)
        self.partial_caption_check.setEnabled(True)
        self._set_screen_buttons_enabled(True)


    def _stop_audio(self) -> None:
        if self._audio_worker is not None:
            self._audio_worker.stop()
            self.status_label.setText("正在停止声音翻译…")
        else:
            self._on_audio_stopped()


    def _on_failed(self, message: str) -> None:
        self._busy = False
        self._set_screen_buttons_enabled(True)
        self.status_label.setText("失败：" + message)
        if self._live_mode:
            self._stop_live(keep_status=True)
        self.show()
        self.raise_()
        self.activateWindow()
        QMessageBox.warning(self, "Screen Translator", message)


    def closeEvent(self, event: QCloseEvent) -> None:
        self._live_timer.stop()
        self._perf_timer.stop()
        if self._audio_worker is not None:
            self._audio_worker.stop()
        self._save_settings()
        self._overlay.close()
        event.accept()


