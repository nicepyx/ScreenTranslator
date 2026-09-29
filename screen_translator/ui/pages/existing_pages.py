from __future__ import annotations

from functools import partial

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QCheckBox, QKeySequenceEdit, QTableWidget, QAbstractItemView, QProgressBar, QPushButton, QVBoxLayout, QWidget

from ...constants import LANGUAGE_CATALOG, CORE_LANGUAGE_CODES
from ...core.hotkeys import DEFAULT_HOTKEYS, ACTION_LABELS
from ...core.platform_helpers import (
    is_macos,
    open_macos_microphone_settings,
    open_macos_screen_recording_settings,
)
from ..assets import pixel_icon, pixel_pixmap
class ExistingPagesMixin:
    """Functional pages preserved during the staged UI rebuild."""

    def _build_language_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(2, 8, 2, 8)

        header = QFrame()
        header.setObjectName("PixelCard")
        hr = QHBoxLayout(header)
        icon = QLabel()
        icon.setPixmap(pixel_pixmap("languages", 84))
        icon.setFixedSize(90, 90)
        hr.addWidget(icon)
        copy = QVBoxLayout()
        title = QLabel("语言包")
        title.setStyleSheet("font-size:20px; font-weight:750;")
        note = QLabel(
            "简体中文、English、Français、日本語默认可用。其他语言按需安装。"
            "NLLB / Whisper / OCR 大模型跨语言共享，因此扩展语言包本身很小，不会重复下载几百 MB 模型。"
        )
        note.setWordWrap(True)
        note.setObjectName("Muted")
        self.language_storage_label = QLabel(self._language_packs.storage_summary())
        self.language_storage_label.setObjectName("Muted")
        copy.addWidget(title)
        copy.addWidget(note)
        copy.addWidget(self.language_storage_label)
        hr.addLayout(copy, 1)
        layout.addWidget(header)

        self.language_progress = QProgressBar()
        self.language_progress.setRange(0, 100)
        self.language_progress.setValue(0)
        self.language_progress.setTextVisible(True)
        self.language_progress.hide()
        layout.addWidget(self.language_progress)

        grid_host = QWidget()
        self._language_card_grid = QGridLayout(grid_host)
        self._language_card_grid.setContentsMargins(0, 6, 0, 0)
        self._language_card_grid.setHorizontalSpacing(12)
        self._language_card_grid.setVerticalSpacing(12)
        layout.addWidget(grid_host)
        layout.addStretch(1)
        self._refresh_language_cards()
        return page


    def _refresh_language_cards(self) -> None:
        grid = self._language_card_grid
        if grid is None:
            return
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for i, info in enumerate(self._language_packs.catalog()):
            card = QFrame()
            card.setObjectName("PixelCard")
            box = QVBoxLayout(card)
            box.setContentsMargins(14, 12, 14, 12)
            title = QLabel(f"{info.get('flag', '')}  {info['label']}")
            title.setStyleSheet("font-size:16px; font-weight:700;")
            box.addWidget(title)
            tag = QLabel("核心语言 · 默认安装" if info["core"] else "扩展语言 · 按需安装")
            tag.setObjectName("Muted")
            box.addWidget(tag)
            installed = bool(info["installed"])
            state = QLabel("● 已安装" if installed else "○ 未安装")
            state.setStyleSheet("color:#45D39A;" if installed else "color:#8F9AAD;")
            box.addWidget(state)
            btn = QPushButton("已内置" if info["core"] else ("删除" if installed else "下载"))
            btn.setEnabled(not info["core"])
            if not info["core"] and not installed:
                btn.setObjectName("PrimaryButton")
            btn.clicked.connect(partial(self._toggle_language_pack, info["code"]))
            box.addWidget(btn)
            grid.addWidget(card, i // 2, i % 2)


    def _toggle_language_pack(self, code: str) -> None:
        if code in CORE_LANGUAGE_CODES:
            return
        try:
            if self._language_packs.is_installed(code):
                self._language_packs.remove(code)
                self.status_label.setText(f"已删除 {LANGUAGE_CATALOG[code]['label']} 语言包。翻译历史保留。")
            else:
                self.language_progress.show()
                self.language_progress.setValue(5)
                self._language_packs.install(
                    code,
                    lambda value, text: (self.language_progress.setValue(value), self.language_progress.setFormat(text + " %p%")),
                )
                self.status_label.setText(f"{LANGUAGE_CATALOG[code]['label']} 语言包已安装，现在可作为源语言或目标语言。")
                self.language_progress.hide()
            self.language_storage_label.setText(self._language_packs.storage_summary())
            self._reload_language_combos()
            self._refresh_language_cards()
        except Exception as exc:
            self.language_progress.hide()
            self.status_label.setText(f"语言包操作失败：{exc}")


    def _reload_language_combos(self) -> None:
        installed = self._language_packs.installed_codes()
        combos = []
        if hasattr(self, "source_combo"):
            combos.append((self.source_combo, True))
        if hasattr(self, "target_combo"):
            combos.append((self.target_combo, False))
        if hasattr(self, "audio_source_combo"):
            combos.append((self.audio_source_combo, True))
        if hasattr(self, "audio_target_combo"):
            combos.append((self.audio_target_combo, False))
        for combo, allow_auto in combos:
            current = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            if allow_auto:
                combo.addItem("自动检测", "auto")
            for code in installed:
                info = LANGUAGE_CATALOG[code]
                combo.addItem(info["label"], code)
            idx = combo.findData(current)
            if idx < 0:
                idx = combo.findData("auto" if allow_auto else "zh")
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)
        self._translation_direction_changed()


    def _build_overlay_tab(self) -> QWidget:
        from .subtitle_page import SubtitlePage
        return SubtitlePage(self)

    def _update_subtitle_preview(self) -> None:
        from .subtitle_page import update_preview
        update_preview(self)

    def _build_settings_page(self) -> QWidget:
        page=QWidget(); layout=QVBoxLayout(page); layout.setContentsMargins(2,8,2,8)
        card=QFrame(); card.setObjectName("PixelCard"); row=QHBoxLayout(card)
        icon=QLabel(); icon.setPixmap(pixel_pixmap("settings",78)); icon.setFixedSize(84,84); row.addWidget(icon)
        body=QVBoxLayout(); t=QLabel("应用设置"); t.setObjectName("SectionTitle"); body.addWidget(t)
        note=QLabel("v0.9 固定使用浅色像素 UI，不再提供深色主题。高频操作建议通过托盘、全局快捷键或迷你控制条完成。")
        note.setWordWrap(True); note.setObjectName("Muted"); body.addWidget(note)
        self.tray_close_check=QCheckBox("关闭主窗口时最小化到系统托盘")
        self.tray_close_check.setChecked(True); body.addWidget(self.tray_close_check)
        self.auto_mini_check=QCheckBox("开始声音翻译时自动显示迷你控制条")
        self.auto_mini_check.setChecked(True); body.addWidget(self.auto_mini_check)
        row.addLayout(body,1); layout.addWidget(card)
        if is_macos():
            perms=QFrame(); perms.setObjectName("PixelCard"); pl=QHBoxLayout(perms); pl.addWidget(QLabel("macOS 权限"))
            sb=QPushButton("屏幕录制权限"); sb.clicked.connect(open_macos_screen_recording_settings)
            mb=QPushButton("麦克风权限"); mb.clicked.connect(open_macos_microphone_settings)
            pl.addWidget(sb); pl.addWidget(mb); pl.addStretch(1); layout.addWidget(perms)
        layout.addStretch(1); return page


    def _build_vocabulary_page(self) -> QWidget:
        page=QWidget(); layout=QVBoxLayout(page); layout.setContentsMargins(2,8,2,8)
        hero=QFrame(); hero.setObjectName("PixelCard"); hr=QHBoxLayout(hero)
        ic=QLabel(); ic.setPixmap(pixel_icon("vocabulary").pixmap(QSize(72,72))); hr.addWidget(ic)
        copy=QVBoxLayout(); tt=QLabel("词汇学习"); tt.setObjectName("SectionTitle"); copy.addWidget(tt)
        desc=QLabel("在翻译原文或译文中点击单词即可查看本地翻译含义并朗读，收藏后会出现在这里。")
        desc.setWordWrap(True); desc.setObjectName("Muted"); copy.addWidget(desc); hr.addLayout(copy,1); layout.addWidget(hero)
        self.vocab_table=QTableWidget(0,5); self.vocab_table.setHorizontalHeaderLabels(["词汇","含义","语言","分类","时间"]); self.vocab_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.vocab_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.vocab_table.horizontalHeader().setStretchLastSection(True); layout.addWidget(self.vocab_table,1)
        row=QHBoxLayout(); speak=QPushButton("朗读选中词"); speak.clicked.connect(self._speak_selected_vocab); delete=QPushButton("删除选中词"); delete.clicked.connect(self._delete_selected_vocab); row.addWidget(speak); row.addWidget(delete); row.addStretch(1); layout.addLayout(row)
        return page


    def _build_data_page(self) -> QWidget:
        page=QWidget(); layout=QVBoxLayout(page); layout.setContentsMargins(2,8,2,8)
        hero=QFrame(); hero.setObjectName("PixelCard"); h=QHBoxLayout(hero); ic=QLabel(); ic.setPixmap(pixel_icon("data").pixmap(QSize(72,72))); h.addWidget(ic)
        b=QVBoxLayout(); t=QLabel("本地数据管理"); t.setObjectName("SectionTitle"); b.addWidget(t); n=QLabel("支持标准模式或自定义磁盘路径；更改路径时可自动迁移模型、语言包、历史、缓存和 Profile。")
        n.setWordWrap(True); n.setObjectName("Muted"); b.addWidget(n); h.addLayout(b,1); layout.addWidget(hero)
        card=QFrame(); card.setObjectName("PixelCard"); cl=QVBoxLayout(card)
        self.storage_mode_label=QLabel(); self.storage_path_label=QLabel(); self.storage_path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); self.storage_path_label.setObjectName("Muted")
        cl.addWidget(self.storage_mode_label); cl.addWidget(self.storage_path_label)
        buttons=QHBoxLayout(); change=QPushButton("更改路径并迁移"); change.clicked.connect(self._choose_storage_path); standard=QPushButton("恢复标准路径"); standard.clicked.connect(self._restore_standard_storage); op=QPushButton("打开目录"); op.clicked.connect(self._open_storage_dir); clean=QPushButton("清理缓存"); clean.clicked.connect(self._clean_storage_cache)
        for x in (change,standard,op,clean): buttons.addWidget(x)
        buttons.addStretch(1); cl.addLayout(buttons); layout.addWidget(card)
        self.storage_table=QTableWidget(0,2); self.storage_table.setHorizontalHeaderLabels(["数据类别","占用空间"]); self.storage_table.horizontalHeader().setStretchLastSection(True); self.storage_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); layout.addWidget(self.storage_table)
        return page


    def _build_hotkeys_page(self) -> QWidget:
        page=QWidget(); layout=QVBoxLayout(page); layout.setContentsMargins(2,8,2,8)
        hero=QFrame(); hero.setObjectName("PixelCard"); h=QHBoxLayout(hero); ic=QLabel(); ic.setPixmap(pixel_icon("hotkeys").pixmap(QSize(72,72))); h.addWidget(ic)
        b=QVBoxLayout(); t=QLabel("全局快捷键中心"); t.setObjectName("SectionTitle"); b.addWidget(t); n=QLabel("快捷键在应用位于后台或系统托盘时仍可触发。macOS 首次使用可能需要辅助功能权限。")
        n.setWordWrap(True); n.setObjectName("Muted"); b.addWidget(n); h.addLayout(b,1); layout.addWidget(hero)
        self.hotkey_edits={}; grid=QGridLayout()
        for r,(action,label) in enumerate(ACTION_LABELS.items()):
            grid.addWidget(QLabel(label),r,0); edit=QKeySequenceEdit(QKeySequence(str(self._settings.value(f"hotkey/{action}",DEFAULT_HOTKEYS[action])))); self.hotkey_edits[action]=edit; grid.addWidget(edit,r,1)
        layout.addLayout(grid); row=QHBoxLayout(); save=QPushButton("保存并重新注册"); save.setObjectName("PrimaryButton"); save.clicked.connect(self._save_hotkeys); reset=QPushButton("恢复默认"); reset.clicked.connect(self._reset_hotkeys); row.addWidget(save); row.addWidget(reset); row.addStretch(1); layout.addLayout(row)
        self.hotkey_state_label=QLabel("等待注册…"); self.hotkey_state_label.setObjectName("Muted"); layout.addWidget(self.hotkey_state_label); layout.addStretch(1); return page


    def _build_audio_tab(self) -> QWidget:
        from ...constants import SOURCE_LANGUAGES, TARGET_LANGUAGES, WHISPER_MODEL_PRESETS, VAD_SENSITIVITY_PRESETS
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(2,8,2,8); layout.setSpacing(10)
        hero = QFrame(); hero.setObjectName("PixelCard"); hr = QHBoxLayout(hero); hr.setContentsMargins(14,10,14,10)
        icon = QLabel(); icon.setPixmap(pixel_pixmap("audio",72)); icon.setFixedSize(78,78); hr.addWidget(icon)
        copy = QVBoxLayout(); title = QLabel("声音翻译"); title.setObjectName("SectionTitle"); copy.addWidget(title)
        desc = QLabel("VAD 自动断句 + Partial / Final 流式字幕，适合网课、视频和实时对话。")
        desc.setWordWrap(True); desc.setObjectName("Muted"); copy.addWidget(desc); hr.addLayout(copy,1); layout.addWidget(hero)

        source = QFrame(); source.setObjectName("PixelCard"); grid = QGridLayout(source); grid.setContentsMargins(14,12,14,12); grid.setHorizontalSpacing(12); grid.setVerticalSpacing(10)
        grid.addWidget(QLabel("音频来源"),0,0); self.audio_kind_combo=QComboBox(); self.audio_kind_combo.addItem("系统声音（游戏 / 视频 / 课程）","system"); self.audio_kind_combo.addItem("麦克风","microphone"); self.audio_kind_combo.currentIndexChanged.connect(self._refresh_audio_devices); grid.addWidget(self.audio_kind_combo,0,1)
        grid.addWidget(QLabel("设备"),1,0); dev=QWidget(); dr=QHBoxLayout(dev); dr.setContentsMargins(0,0,0,0); self.audio_device_combo=QComboBox(); dr.addWidget(self.audio_device_combo,1); rb=QPushButton("刷新设备"); rb.clicked.connect(self._refresh_audio_devices); dr.addWidget(rb); grid.addWidget(dev,1,1)
        grid.addWidget(QLabel("翻译语言"),2,0); lw=QWidget(); lr=QHBoxLayout(lw); lr.setContentsMargins(0,0,0,0); self.audio_source_combo=QComboBox(); [self.audio_source_combo.addItem(label,key) for key,label in SOURCE_LANGUAGES.items()]; lr.addWidget(self.audio_source_combo,1); self.audio_swap_button=QPushButton("⇄"); self.audio_swap_button.setFixedWidth(44); self.audio_swap_button.clicked.connect(self._swap_audio_languages); lr.addWidget(self.audio_swap_button); self.audio_target_combo=QComboBox(); [self.audio_target_combo.addItem(label,key) for key,label in TARGET_LANGUAGES.items()]; lr.addWidget(self.audio_target_combo,1); grid.addWidget(lw,2,1); layout.addWidget(source)

        realtime = QFrame(); realtime.setObjectName("PixelCard"); rg=QGridLayout(realtime); rg.setContentsMargins(14,12,14,12); rg.setHorizontalSpacing(12); rg.setVerticalSpacing(10)
        rg.addWidget(QLabel("语音模型"),0,0); self.whisper_model_combo=QComboBox(); [self.whisper_model_combo.addItem(label,key) for label,key in WHISPER_MODEL_PRESETS]; self.whisper_model_combo.currentIndexChanged.connect(self._mark_performance_custom); rg.addWidget(self.whisper_model_combo,0,1)
        rg.addWidget(QLabel("VAD 灵敏度"),1,0); self.vad_sensitivity_combo=QComboBox(); [self.vad_sensitivity_combo.addItem(label,key) for label,key in VAD_SENSITIVITY_PRESETS]; self.vad_sensitivity_combo.currentIndexChanged.connect(self._mark_performance_custom); rg.addWidget(self.vad_sensitivity_combo,1,1)
        rg.addWidget(QLabel("流式字幕"),2,0); self.partial_caption_check=QCheckBox("边说边识别 / 临时翻译（推荐网课）"); self.partial_caption_check.setChecked(True); self.partial_caption_check.toggled.connect(lambda _=None:self._save_settings()); rg.addWidget(self.partial_caption_check,2,1)
        self.audio_platform_hint=QLabel(); self.audio_platform_hint.setWordWrap(True); self.audio_platform_hint.setObjectName("Muted")
        from ...core.platform_helpers import is_windows
        if is_windows(): self.audio_platform_hint.setText("Windows：系统声音使用 WASAPI 回环。")
        elif is_macos(): self.audio_platform_hint.setText("macOS：麦克风可直接使用；系统内部声音仍依赖后续 ScreenCaptureKit 音频接入。")
        else: self.audio_platform_hint.setText("系统声音是否可用取决于系统提供的回环/monitor 设备。")
        rg.addWidget(self.audio_platform_hint,3,0,1,2); layout.addWidget(realtime)
        self.audio_button=QPushButton("开始监听并翻译"); self.audio_button.setObjectName("PrimaryButton"); self.audio_button.setMinimumHeight(48); self.audio_button.clicked.connect(self._toggle_audio); layout.addWidget(self.audio_button); layout.addStretch(1); return page


    def _build_history_tab(self) -> QWidget:
        from PySide6.QtWidgets import QHeaderView, QLineEdit
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(2,8,2,8); layout.setSpacing(10)
        hero = QFrame(); hero.setObjectName("PixelCard"); hr = QHBoxLayout(hero)
        icon = QLabel(); icon.setPixmap(pixel_pixmap("history", 70)); icon.setFixedSize(76,76); hr.addWidget(icon)
        copy = QVBoxLayout(); title = QLabel("翻译记录"); title.setObjectName("SectionTitle"); copy.addWidget(title)
        desc = QLabel("屏幕与声音翻译会持续保存在本机。选中记录后会同步到下方翻译文本区，便于复制、朗读或点词学习。")
        desc.setWordWrap(True); desc.setObjectName("Muted"); copy.addWidget(desc); hr.addLayout(copy,1); layout.addWidget(hero)
        tools = QHBoxLayout(); self.history_search = QLineEdit(); self.history_search.setPlaceholderText("搜索原文 / 译文 / 语言 / 来源…"); self.history_search.textChanged.connect(self._filter_history); tools.addWidget(self.history_search,1)
        copy_src = QPushButton("复制选中原文"); copy_src.clicked.connect(lambda: QApplication.clipboard().setText(self.source_edit.toPlainText())); tools.addWidget(copy_src)
        copy_dst = QPushButton("复制选中译文"); copy_dst.clicked.connect(lambda: QApplication.clipboard().setText(self.translation_edit.toPlainText())); tools.addWidget(copy_dst); layout.addLayout(tools)
        self.history_table = QTableWidget(0,6); self.history_table.setHorizontalHeaderLabels(["时间","来源","语言","原文","译文","自动词库"]); self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.history_table.itemSelectionChanged.connect(self._history_selection_changed)
        header=self.history_table.horizontalHeader(); header.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents); header.setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents); header.setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents); header.setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch); header.setSectionResizeMode(4,QHeaderView.ResizeMode.Stretch); header.setSectionResizeMode(5,QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.setWordWrap(True); self.history_table.verticalHeader().setDefaultSectionSize(64); self.history_table.verticalHeader().setVisible(False); layout.addWidget(self.history_table,1)
        row=QHBoxLayout(); exp=QPushButton("导出全部 TXT"); exp.clicked.connect(self._export_history); row.addWidget(exp); ctx=QPushButton("清空上下文"); ctx.clicked.connect(self._clear_context); row.addWidget(ctx); clear=QPushButton("清空全部记录"); clear.setObjectName("DangerButton"); clear.clicked.connect(self._clear_history); row.addWidget(clear); row.addStretch(1); layout.addLayout(row); return page


    def _filter_history(self, text: str) -> None:
        if not hasattr(self, "history_table"):
            return
        query = text.strip().casefold()
        for row in range(self.history_table.rowCount()):
            hay = " ".join((self.history_table.item(row,c).text() if self.history_table.item(row,c) else "") for c in range(self.history_table.columnCount())).casefold()
            self.history_table.setRowHidden(row, bool(query and query not in hay))


