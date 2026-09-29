from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QKeySequence, QDesktopServices
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QFileDialog, QMessageBox, QTableWidgetItem

from ..core.storage import format_bytes
from ..core.hotkeys import DEFAULT_HOTKEYS, ACTION_LABELS
from ..core.word_lookup import WordLookupWorker
from .assets import pixel_icon, pixel_pixmap
from .pixel_theme import pixel_light_qss
from .mini_toolbar import MiniToolbar
from .word_popup import WordPopup


class DesktopActionsMixin:
    """Tray, floating-window and task adapters, independent of the shell layout."""

    def _set_usage_mode_by_key(self, key: str) -> None:
        idx = self.usage_mode_combo.findData(key)
        if idx >= 0:
            self.usage_mode_combo.setCurrentIndex(idx)
        else:
            self.usage_mode_combo.setCurrentIndex(self.usage_mode_combo.findData("general"))
        self._sync_usage_buttons()


    def _sync_usage_buttons(self) -> None:
        if not hasattr(self, "usage_mode_combo"):
            return
        key = str(self.usage_mode_combo.currentData() or "general")
        for item_key, btn in self._usage_buttons.items():
            btn.setChecked(item_key == key)


    def _usage_mode_changed(self, *_args) -> None:
        super()._usage_mode_changed(*_args)
        self._sync_usage_buttons()


    def _update_window_preview(self, *_args) -> None:
        if not hasattr(self, "window_combo") or not hasattr(self, "window_summary"):
            return
        text = self.window_combo.currentText().strip() or "未选择窗口"
        self.window_summary.setText(text)


    def _overlay_setting_changed(self, *_args) -> None:
        super()._overlay_setting_changed(*_args)
        self._update_subtitle_preview()


    def _apply_subtitle_preset(self) -> None:
        super()._apply_subtitle_preset()
        self._update_subtitle_preview()


    def _apply_theme(self, _mode: str = "light") -> None:
        self.setStyleSheet(pixel_light_qss())
        self._update_subtitle_preview()


    def _swap_screen_languages(self) -> None:
        super()._swap_screen_languages()
        self._translation_direction_changed()


    def _swap_audio_languages(self) -> None:
        super()._swap_audio_languages()
        self._translation_direction_changed()


    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable(): return
        self.tray=QSystemTrayIcon(pixel_icon("app_logo"),self); self.tray.setToolTip("Screen Translator")
        menu=QMenu(); show=menu.addAction("打开主窗口"); show.triggered.connect(self._show_main_window); menu.addSeparator(); once=menu.addAction("屏幕翻译"); once.triggered.connect(self._start_screen_once); live=menu.addAction("开始 / 暂停实时翻译"); live.triggered.connect(self._toggle_live); audio=menu.addAction("开始 / 暂停声音翻译"); audio.triggered.connect(self._toggle_audio); menu.addSeparator(); mini=menu.addAction("显示迷你控制条"); mini.triggered.connect(self._toggle_mini_toolbar); quit_act=menu.addAction("退出"); quit_act.triggered.connect(self._quit_application)
        self.tray.setContextMenu(menu); self.tray.activated.connect(lambda reason: self._show_main_window() if reason==QSystemTrayIcon.ActivationReason.DoubleClick else None); self.tray.show()


    def _setup_mini_toolbar(self) -> None:
        self.mini_toolbar=MiniToolbar(); self.mini_toolbar.setStyleSheet(pixel_light_qss()); self.mini_toolbar.pauseRequested.connect(self._pause_active_translation); self.mini_toolbar.clearRequested.connect(self._clear_overlay_and_text); self.mini_toolbar.showMainRequested.connect(self._show_main_window); self.mini_toolbar.toggleOverlayLockRequested.connect(self._toggle_overlay_lock); self.mini_toolbar.closeRequested.connect(self.mini_toolbar.hide)
        self.mini_toolbar.move(80,80)


    def _setup_hotkeys(self) -> None:
        self._hotkeys.triggered.connect(self._handle_hotkey_action); self._hotkeys.stateChanged.connect(self._hotkey_state_changed); self._register_hotkeys()


    def _setup_word_popup(self) -> None:
        self.word_popup=WordPopup(self); self.word_popup.setStyleSheet(pixel_light_qss()); self.word_popup.addRequested.connect(self._add_word_to_vocabulary); self.word_popup.speakRequested.connect(self._speak_text)


    def _register_hotkeys(self) -> None:
        mapping={a:str(self._settings.value(f"hotkey/{a}",d)) for a,d in DEFAULT_HOTKEYS.items()}; self._hotkeys.start(mapping)


    def _save_hotkeys(self) -> None:
        sequences = {action: edit.keySequence().toString().strip() for action, edit in self.hotkey_edits.items()}
        used: dict[str, str] = {}
        for action, seq in sequences.items():
            if not seq:
                continue
            key = seq.casefold()
            if key in used:
                QMessageBox.warning(self, "快捷键冲突", f"{ACTION_LABELS[used[key]]} 与 {ACTION_LABELS[action]} 使用了同一个快捷键：{seq}")
                return
            used[key] = action
        for action, seq in sequences.items():
            self._settings.setValue(f"hotkey/{action}", seq)
        self._register_hotkeys()


    def _reset_hotkeys(self) -> None:
        for action,edit in self.hotkey_edits.items(): edit.setKeySequence(QKeySequence(DEFAULT_HOTKEYS[action]))
        self._save_hotkeys()


    def _hotkey_state_changed(self,text:str) -> None:
        if hasattr(self,"hotkey_state_label"): self.hotkey_state_label.setText(text)


    def _handle_hotkey_action(self,action:str) -> None:
        if action=="screen_once": self._start_screen_once()
        elif action=="toggle_live": self._toggle_live()
        elif action=="toggle_audio": self._toggle_audio()
        elif action=="toggle_overlay": self.overlay_visible_check.setChecked(not self.overlay_visible_check.isChecked())
        elif action=="clear_overlay": self._clear_overlay_and_text()
        elif action=="toggle_mini": self._toggle_mini_toolbar()
        elif action=="show_window": self._show_main_window()


    def _bind_source_window(self) -> None:
        self.screen_mode_combo.setCurrentIndex(self.screen_mode_combo.findData("window"))
        self.bind_window_check.setChecked(True)
        self._refresh_windows()
        self.window_combo.showPopup()

    def _start_selection(self, live: bool) -> None:
        self.screen_options_dialog.hide()
        self.screen_results_dialog.hide()
        super()._start_selection(live)

    def _screen_mode_changed(self, *_args) -> None:
        super()._screen_mode_changed(*_args)
        self._source_stack.setCurrentIndex(1 if self.screen_mode_combo.currentData() == "window" else 0)
        self.window_label.setEnabled(True)
        self.live_button.setText("停止实时翻译" if self._live_mode else "开始翻译")

    def _status_text_changed(self, text: str) -> None:
        if any(key in text for key in ("失败", "错误")):
            state, art = "Error", "status_error"
        elif self._busy or self._live_mode or self._audio_running:
            state, art = "Working", "status_busy"
        elif any(key in text for key in ("暂停", "停止", "取消")):
            state, art = "Paused", "status_paused"
        else:
            state, art = "Ready", "status_ready"
        self.screen_status_summary.setText(state)
        self.screen_ready_dot.setPixmap(pixel_pixmap(art, 20))
        if hasattr(self, "mini_toolbar"):
            self.mini_toolbar.set_state(state)
            self.mini_toolbar.setToolTip(text)

    def _translation_direction_changed(self, *_args) -> None:
        if self.stack.currentIndex() == self.PAGE_AUDIO:
            src, dst = self.audio_source_combo.currentText(), self.audio_target_combo.currentText()
        else:
            src, dst = self.source_combo.currentText(), self.target_combo.currentText()
        if hasattr(self, "mini_toolbar"):
            self.mini_toolbar.set_direction(src, dst)

    def _show_main_window(self) -> None:
        self.show(); self.raise_(); self.activateWindow()


    def _toggle_mini_toolbar(self) -> None:
        self.mini_toolbar.setVisible(not self.mini_toolbar.isVisible())


    def _pause_active_translation(self) -> None:
        if self._audio_running: self._stop_audio()
        elif self._live_mode: self._stop_live()
        else: self.status_label.setText("当前没有正在运行的实时任务。")


    def _toggle_overlay_lock(self) -> None:
        self.overlay_lock_check.setChecked(not self.overlay_lock_check.isChecked())


    def _clear_overlay_and_text(self) -> None:
        self._overlay.clear_history(); self._overlay.hide(); self.source_edit.clear(); self.translation_edit.clear(); self.status_label.setText("字幕和实时文本已清空。")


    def _clear_result_text(self) -> None: self._clear_overlay_and_text()


    def _copy_source(self) -> None:
        QApplication.clipboard().setText(self.source_edit.toPlainText())


    def _copy_translation(self) -> None:
        QApplication.clipboard().setText(self.translation_edit.toPlainText())


    def _speak_translation(self) -> None:
        target=self.audio_target_combo.currentData() if self.stack.currentIndex()==self.PAGE_AUDIO else self.target_combo.currentData(); self._speak_text(self.translation_edit.toPlainText(),str(target or "zh"))


    def _speak_text(self,text:str,lang:str) -> None:
        if self._speech.available(): self._speech.speak(text,lang)
        else: self.status_label.setText("当前系统没有可用的 Qt 语音朗读后端。")


    def _lookup_word(self,word:str) -> None:
        if not self._require_model("translation-nllb", lambda: self._lookup_word(word)):
            return
        src=str(self.audio_source_combo.currentData() if self.stack.currentIndex()==self.PAGE_AUDIO else self.source_combo.currentData() or "auto"); dst=str(self.audio_target_combo.currentData() if self.stack.currentIndex()==self.PAGE_AUDIO else self.target_combo.currentData() or "zh")
        if src=="auto":
            from ..core.language import detect_source_language
            src=detect_source_language(word)
        context=self.source_edit.toPlainText().strip(); self.word_popup.show_loading(word,src,dst,context)
        worker=WordLookupWorker(word,src,dst,self._pipeline,context); worker.signals.finished.connect(self.word_popup.show_result); worker.signals.failed.connect(self.word_popup.show_error); self._thread_pool.start(worker)


    def _add_word_to_vocabulary(self,payload:dict) -> None:
        self._vocabulary.add(str(payload.get("source_lang","")),str(payload.get("target_lang","")),str(payload.get("term","")),str(payload.get("meaning","")),str(payload.get("context","")),"General"); self._refresh_vocabulary(); self.status_label.setText(f"已加入词汇：{payload.get('term','')}")


    def _refresh_vocabulary(self) -> None:
        if not hasattr(self,"vocab_table"): return
        rows=self._vocabulary.list(); self.vocab_table.setRowCount(0)
        for e in rows:
            r=self.vocab_table.rowCount(); self.vocab_table.insertRow(r); vals=[e.term,e.meaning,f"{e.source_lang} → {e.target_lang}",e.category,e.created_at]
            for c,v in enumerate(vals):
                item=QTableWidgetItem(str(v)); item.setData(Qt.ItemDataRole.UserRole,e.id); self.vocab_table.setItem(r,c,item)


    def _selected_vocab_entry(self):
        rows=self.vocab_table.selectionModel().selectedRows() if self.vocab_table.selectionModel() else []
        if not rows:return None
        rid=int(self.vocab_table.item(rows[0].row(),0).data(Qt.ItemDataRole.UserRole)); return next((x for x in self._vocabulary.list() if x.id==rid),None)


    def _speak_selected_vocab(self) -> None:
        e=self._selected_vocab_entry();
        if e:self._speak_text(e.term,e.source_lang)


    def _delete_selected_vocab(self) -> None:
        e=self._selected_vocab_entry();
        if e:self._vocabulary.remove(e.id); self._refresh_vocabulary()


    def _refresh_storage_summary(self) -> None:
        if not hasattr(self,"storage_table"): return
        root=self._storage_manager.root(); self.storage_mode_label.setText("数据模式："+("自定义路径" if self._storage_manager.mode()=="custom" else "标准模式")); self.storage_path_label.setText(str(root)); b=self._storage_manager.breakdown(root); items=[("翻译 / ASR 模型",b.models),("语言包",b.language_packs),("翻译历史",b.history),("翻译缓存",b.cache),("配置与 Profile",b.profiles),("词汇记录",b.vocabulary),("其他",b.other)]
        self.storage_table.setRowCount(0)
        for name,size in items:
            r=self.storage_table.rowCount(); self.storage_table.insertRow(r); self.storage_table.setItem(r,0,QTableWidgetItem(name)); self.storage_table.setItem(r,1,QTableWidgetItem(format_bytes(size)))


    def _choose_storage_path(self) -> None:
        if self._busy or self._live_mode or self._audio_running:
            QMessageBox.information(self, "数据迁移", "请先停止正在运行的屏幕/声音翻译任务，再迁移数据目录。")
            return
        path=QFileDialog.getExistingDirectory(self,"选择 Screen Translator 数据目录",str(self._storage_manager.root()))
        if not path:return
        try:self._storage_manager.migrate_to(Path(path)); self._refresh_storage_summary(); QMessageBox.information(self,"数据迁移完成","数据已迁移到新路径。为确保所有模型和数据库切换到新目录，请重新启动 Screen Translator。")
        except Exception as exc: QMessageBox.warning(self,"迁移失败",str(exc))


    def _restore_standard_storage(self) -> None:
        if self._busy or self._live_mode or self._audio_running:
            QMessageBox.information(self, "数据迁移", "请先停止正在运行的屏幕/声音翻译任务，再迁移数据目录。")
            return
        try:
            if self._storage_manager.mode() == "custom":
                self._storage_manager.migrate_to(self._storage_manager.bootstrap_root)
            self._storage_manager.set_standard()
            self._refresh_storage_summary()
            QMessageBox.information(self,"存储模式","数据已迁移回标准路径。请重新启动 Screen Translator。")
        except Exception as exc:
            QMessageBox.warning(self,"迁移失败",str(exc))


    def _open_storage_dir(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._storage_manager.root())))


    def _clean_storage_cache(self) -> None:
        removed=self._storage_manager.clean_cache(); self._refresh_storage_summary(); self.status_label.setText(f"已清理翻译缓存 {format_bytes(removed)}")


    def _quit_application(self) -> None:
        self._force_quit=True; self._hotkeys.stop(); self._live_timer.stop(); self._perf_timer.stop();
        if self._audio_worker is not None:self._audio_worker.stop()
        self._save_settings(); self._overlay.close(); self.mini_toolbar.close(); self.word_popup.close();
        self.screen_options_dialog.close()
        self.screen_results_dialog.close()
        if hasattr(self,"tray"): self.tray.hide()
        QApplication.instance().quit()


    def closeEvent(self,event) -> None:
        if not self._force_quit and getattr(self,"tray_close_check",None) is not None and self.tray_close_check.isChecked() and hasattr(self,"tray"):
            event.ignore(); self.hide(); self.status_label.setText("主窗口已隐藏到系统托盘，翻译任务可继续运行。")
            return
        self._quit_application(); event.accept()


    def _live_tick(self) -> None:
        if self._busy:
            self._queued_screen_capture=True; return
        if self.screen_mode_combo.currentData()=="window":
            rect=self._current_window_rect()
            if rect is None:
                if hasattr(self, "bind_window_check") and self.bind_window_check.isChecked():
                    # The OS window handle can change after an app/game restarts. Rebind by the
                    # stable owner+title profile key before deciding the source is unavailable.
                    saved_profile = str(self._settings.value("window_profile_key", ""))
                    if saved_profile:
                        self._saved_window_profile_key = saved_profile
                        self._refresh_windows()
                        rect = self._current_window_rect()
                    if rect is None:
                        self._source_window_suspended=True; self._overlay.hide(); self.status_label.setText("来源窗口当前不可见/已最小化，翻译已自动暂停，恢复窗口后会继续。")
                        return
                self._stop_live(keep_status=True); self.status_label.setText("来源窗口已关闭或不可见，实时翻译已停止。")
                return
            if self._source_window_suspended:
                self._source_window_suspended=False; self.status_label.setText("来源窗口已恢复，继续实时翻译。")
            self._selected_rect=rect
        if self._selected_rect is not None:self._capture_and_translate()


    def _on_audio_transcript(self,result:dict) -> None:
        super()._on_audio_transcript(result)
        if hasattr(self,"auto_mini_check") and self.auto_mini_check.isChecked(): self.mini_toolbar.show()


    def _cancel_current_task(self) -> None:
        if self._audio_running:
            self._stop_audio(); self.status_label.setText("声音翻译取消中…"); return
        if self._live_mode:
            self._stop_live(); self.status_label.setText("实时屏幕翻译已取消。"); return
        if self._busy:
            self._screen_task_generation += 1
            self._ignore_next_failure = True
            self._queued_screen_capture = False
            self.status_label.setText("当前任务已标记取消，正在等待后台推理结束并丢弃结果…")
            return
        self.status_label.setText("当前没有可取消的任务。")


    def _start_screen_once(self) -> None:
        if self._busy:
            self._manual_screen_queued = True
            self.status_label.setText("当前 OCR / 翻译仍在运行，新的单次翻译已加入队列。")
            return
        self._manual_screen_queued = False
        super()._start_screen_once()


    def _on_screen_finished(self, result: dict) -> None:
        task_id = int(result.get("_task_id", getattr(self, "_screen_task_generation", 0)))
        if task_id != getattr(self, "_screen_task_generation", 0):
            self._ignore_next_failure = False
            self._busy = False
            self._set_screen_buttons_enabled(True)
            self.status_label.setText("已丢弃被取消的过期翻译结果。")
            if getattr(self, "_manual_screen_queued", False):
                self._manual_screen_queued = False
                QTimer.singleShot(0, self._start_screen_once)
            return
        super()._on_screen_finished(result)
        if getattr(self, "_manual_screen_queued", False) and not self._busy:
            self._manual_screen_queued = False
            QTimer.singleShot(0, self._start_screen_once)
        elif self._queued_screen_capture and self._live_mode and not self._busy:
            self._queued_screen_capture = False
            QTimer.singleShot(0, self._capture_and_translate)
        if self._live_mode and hasattr(self, "auto_mini_check") and self.auto_mini_check.isChecked():
            self.mini_toolbar.show()


    def _restore_settings(self) -> None:
        desktop_preferences = {key: self._settings.value(key, "true") for key in ("tray_close", "auto_mini_toolbar", "bind_source_window")}
        super()._restore_settings()
        if hasattr(self, "tray_close_check"):
            self.tray_close_check.setChecked(str(desktop_preferences["tray_close"]).lower() == "true")
        if hasattr(self, "auto_mini_check"):
            self.auto_mini_check.setChecked(str(desktop_preferences["auto_mini_toolbar"]).lower() == "true")
        if hasattr(self, "bind_window_check"):
            self.bind_window_check.setChecked(str(desktop_preferences["bind_source_window"]).lower() == "true")


    def _save_settings(self) -> None:
        if self._restoring_settings:
            return
        super()._save_settings()
        if hasattr(self, "tray_close_check"):
            self._settings.setValue("tray_close", self.tray_close_check.isChecked())
        if hasattr(self, "auto_mini_check"):
            self._settings.setValue("auto_mini_toolbar", self.auto_mini_check.isChecked())
        if hasattr(self, "bind_window_check"):
            self._settings.setValue("bind_source_window", self.bind_window_check.isChecked())
        if hasattr(self, "mini_toolbar"):
            self._settings.setValue("mini_toolbar_x", self.mini_toolbar.x())
            self._settings.setValue("mini_toolbar_y", self.mini_toolbar.y())


    def _on_failed(self, message: str) -> None:
        if getattr(self, "_ignore_next_failure", False):
            self._ignore_next_failure = False
            self._busy = False
            self._set_screen_buttons_enabled(True)
            self.status_label.setText("已忽略被取消任务的错误结果。")
            return
        super()._on_failed(message)


    def _lookup_translated_word(self, word: str) -> None:
        if not self._require_model("translation-nllb", lambda: self._lookup_translated_word(word)):
            return
        current_target = str(self.audio_target_combo.currentData() if self.stack.currentIndex()==self.PAGE_AUDIO else self.target_combo.currentData() or "zh")
        current_source = str(self.audio_source_combo.currentData() if self.stack.currentIndex()==self.PAGE_AUDIO else self.source_combo.currentData() or "auto")
        if current_source == "auto":
            from ..core.language import detect_source_language
            current_source = detect_source_language(self.source_edit.toPlainText() or word)
        context = self.translation_edit.toPlainText().strip()
        self.word_popup.show_loading(word, current_target, current_source, context)
        worker = WordLookupWorker(word, current_target, current_source, self._pipeline, context)
        worker.signals.finished.connect(self.word_popup.show_result)
        worker.signals.failed.connect(self.word_popup.show_error)
        self._thread_pool.start(worker)


