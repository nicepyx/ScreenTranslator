from __future__ import annotations

from functools import partial

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..constants import APP_NAME, APP_VERSION, LANGUAGE_CATALOG, CORE_LANGUAGE_CODES
from ..core.language_packs import LanguagePackManager
from ..core.paths import data_dir
from ..core.platform_helpers import (
    is_macos,
    open_macos_microphone_settings,
    open_macos_screen_recording_settings,
)
from .assets import pixel_icon, pixel_pixmap
from .legacy_main_window import MainWindow as LegacyMainWindow


_DARK_QSS = r"""
QMainWindow, QWidget#AppRoot { background:#0F1117; color:#E8ECF4; }
QFrame#Sidebar { background:#121722; border-right:1px solid #242B39; }
QFrame#TopBar, QFrame#StatusCard, QFrame#ResultCard, QFrame#PixelCard,
QGroupBox { background:#171D28; border:1px solid #283143; border-radius:12px; }
QGroupBox { margin-top:14px; padding-top:14px; font-weight:600; }
QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 6px; color:#DCE5F5; }
QLabel#PageTitle { font-size:24px; font-weight:750; color:#F6F8FC; }
QLabel#Muted { color:#8F9AAD; }
QLabel#BrandTitle { font-size:15px; font-weight:750; }
QPushButton { background:#202838; color:#EAF0F8; border:1px solid #313D52; border-radius:8px; padding:7px 12px; }
QPushButton:hover { background:#28354A; border-color:#4B648A; }
QPushButton:pressed { background:#1B2535; }
QPushButton#PrimaryButton { background:#3478F6; border-color:#4A8BFF; color:white; font-weight:700; }
QPushButton#PrimaryButton:hover { background:#4285FF; }
QPushButton#NavButton { text-align:left; border:0; background:transparent; padding:8px 10px; border-radius:9px; color:#AAB4C6; }
QPushButton#NavButton:hover { background:#1B2331; color:#F3F6FB; }
QPushButton#NavButton:checked { background:#213653; color:#FFFFFF; border-left:3px solid #46B9FF; }
QComboBox, QSpinBox, QFontComboBox, QPlainTextEdit, QLineEdit { background:#111722; border:1px solid #303B4E; border-radius:8px; padding:6px; color:#E9EEF7; selection-background-color:#2C6FDB; }
QComboBox::drop-down { border:0; width:24px; }
QTableWidget { background:#121822; alternate-background-color:#151D29; border:1px solid #2B3546; border-radius:8px; gridline-color:#263143; }
QHeaderView::section { background:#1A2230; color:#CBD5E6; border:0; padding:7px; }
QProgressBar { border:1px solid #303B4E; border-radius:6px; background:#111722; text-align:center; }
QProgressBar::chunk { background:#3D8BFF; border-radius:5px; }
QSlider::groove:horizontal { height:5px; background:#283246; border-radius:2px; }
QSlider::handle:horizontal { width:15px; margin:-5px 0; background:#4BB9FF; border-radius:7px; }
QCheckBox { spacing:7px; }
QScrollArea { border:0; background:transparent; }
QScrollArea > QWidget > QWidget, QStackedWidget { background:transparent; }
QSplitter::handle { background:#222B3A; height:5px; }
"""

_LIGHT_QSS = r"""
QMainWindow, QWidget#AppRoot { background:#F4F7FB; color:#202735; }
QFrame#Sidebar { background:#FFFFFF; border-right:1px solid #DCE3ED; }
QFrame#TopBar, QFrame#StatusCard, QFrame#ResultCard, QFrame#PixelCard,
QGroupBox { background:#FFFFFF; border:1px solid #DDE5EF; border-radius:12px; }
QGroupBox { margin-top:14px; padding-top:14px; font-weight:600; }
QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 6px; color:#2B3545; }
QLabel#PageTitle { font-size:24px; font-weight:750; color:#1D2633; }
QLabel#Muted { color:#68758A; }
QLabel#BrandTitle { font-size:15px; font-weight:750; }
QPushButton { background:#F5F8FC; color:#253044; border:1px solid #D4DDEA; border-radius:8px; padding:7px 12px; }
QPushButton:hover { background:#EDF3FB; border-color:#9BB9DD; }
QPushButton#PrimaryButton { background:#2979F2; border-color:#2979F2; color:white; font-weight:700; }
QPushButton#NavButton { text-align:left; border:0; background:transparent; padding:8px 10px; border-radius:9px; color:#647187; }
QPushButton#NavButton:hover { background:#EFF4FA; color:#233047; }
QPushButton#NavButton:checked { background:#E4F0FF; color:#165FAF; border-left:3px solid #348DFF; }
QComboBox, QSpinBox, QFontComboBox, QPlainTextEdit, QLineEdit { background:#FFFFFF; border:1px solid #D4DDEA; border-radius:8px; padding:6px; color:#273247; selection-background-color:#BBD9FF; }
QTableWidget { background:#FFFFFF; alternate-background-color:#F8FAFD; border:1px solid #DDE5EF; border-radius:8px; gridline-color:#E8EDF4; }
QHeaderView::section { background:#F0F4F9; color:#46536A; border:0; padding:7px; }
QProgressBar { border:1px solid #D4DDEA; border-radius:6px; background:#F4F7FB; text-align:center; }
QProgressBar::chunk { background:#348DFF; border-radius:5px; }
QSlider::groove:horizontal { height:5px; background:#DCE5F1; border-radius:2px; }
QSlider::handle:horizontal { width:15px; margin:-5px 0; background:#348DFF; border-radius:7px; }
QScrollArea { border:0; background:transparent; }
QScrollArea > QWidget > QWidget, QStackedWidget { background:transparent; }
QSplitter::handle { background:#DCE4EE; height:5px; }
"""


class MainWindow(LegacyMainWindow):
    PAGE_HOME = 0
    PAGE_SCREEN = 1
    PAGE_AUDIO = 2
    PAGE_HISTORY = 3
    PAGE_LANGUAGES = 4
    PAGE_SUBTITLES = 5
    PAGE_PERFORMANCE = 6
    PAGE_SETTINGS = 7

    def __init__(self) -> None:
        super().__init__()
        self.resize(1180, 820)
        self.setMinimumSize(980, 700)
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setWindowIcon(pixel_icon("app_logo"))
        self._theme_mode = str(self._settings.value("ui_theme", "dark"))
        if hasattr(self, "theme_combo"):
            idx = self.theme_combo.findData(self._theme_mode)
            if idx >= 0:
                self.theme_combo.blockSignals(True)
                self.theme_combo.setCurrentIndex(idx)
                self.theme_combo.blockSignals(False)
        self._apply_theme(self._theme_mode)
        self._update_subtitle_preview()

    # ---------- Modern shell ----------
    def _build_ui(self) -> None:
        self._language_packs = LanguagePackManager()
        self._theme_mode = "dark"
        self._nav_buttons: list[QPushButton] = []
        self._language_card_grid: QGridLayout | None = None
        self._subtitle_preview: QLabel | None = None
        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(205)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14, 16, 14, 14)
        side.setSpacing(6)

        brand = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(pixel_pixmap("app_logo", 48))
        logo.setFixedSize(52, 52)
        brand.addWidget(logo)
        brand_text = QVBoxLayout()
        title = QLabel("Screen\nTranslator")
        title.setObjectName("BrandTitle")
        subtitle = QLabel(f"v{APP_VERSION}")
        subtitle.setObjectName("Muted")
        brand_text.addWidget(title)
        brand_text.addWidget(subtitle)
        brand.addLayout(brand_text)
        brand.addStretch(1)
        side.addLayout(brand)
        side.addSpacing(10)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        nav_specs = [
            (self.PAGE_HOME, "home", "主页"),
            (self.PAGE_SCREEN, "screen", "屏幕翻译"),
            (self.PAGE_AUDIO, "audio", "声音翻译"),
            (self.PAGE_HISTORY, "history", "翻译记录"),
            (self.PAGE_LANGUAGES, "languages", "语言包"),
            (self.PAGE_SUBTITLES, "subtitles", "字幕"),
            (self.PAGE_PERFORMANCE, "performance", "性能"),
            (self.PAGE_SETTINGS, "settings", "设置"),
        ]
        for index, icon_name, label in nav_specs:
            btn = QPushButton(label)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setIcon(pixel_icon(icon_name))
            btn.setIconSize(QSize(28, 28))
            btn.setMinimumHeight(44)
            btn.clicked.connect(partial(self._select_page, index))
            self.nav_group.addButton(btn, index)
            self._nav_buttons.append(btn)
            side.addWidget(btn)
        side.addStretch(1)

        privacy = QLabel("● 本地处理\n屏幕与音频默认不上传")
        privacy.setObjectName("Muted")
        privacy.setWordWrap(True)
        privacy.setStyleSheet("font-size:11px; padding:8px;")
        side.addWidget(privacy)
        shell.addWidget(sidebar)

        content_wrap = QWidget()
        content = QVBoxLayout(content_wrap)
        content.setContentsMargins(18, 14, 18, 14)
        content.setSpacing(10)

        topbar = QFrame()
        topbar.setObjectName("TopBar")
        top = QHBoxLayout(topbar)
        top.setContentsMargins(16, 10, 16, 10)
        self.page_title = QLabel("主页")
        self.page_title.setObjectName("PageTitle")
        top.addWidget(self.page_title)
        top.addStretch(1)
        top.addWidget(QLabel("使用场景"))
        self.usage_mode_combo = QComboBox()
        from ..constants import USAGE_MODES
        for key, info in USAGE_MODES.items():
            self.usage_mode_combo.addItem(info["label"], key)
        self.usage_mode_combo.currentIndexChanged.connect(self._usage_mode_changed)
        self.usage_mode_combo.setMinimumWidth(155)
        top.addWidget(self.usage_mode_combo)
        self.accel_label = QLabel("推理加速：自动检测")
        self.accel_label.setObjectName("Muted")
        top.addWidget(self.accel_label)
        content.addWidget(topbar)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._wrap_page(self._build_home_page()))
        self.stack.addWidget(self._wrap_page(self._build_screen_tab()))
        self.stack.addWidget(self._wrap_page(self._build_audio_tab()))
        self.stack.addWidget(self._wrap_page(self._build_history_tab()))
        self.stack.addWidget(self._wrap_page(self._build_language_page()))
        self.stack.addWidget(self._wrap_page(self._build_overlay_tab()))
        self.stack.addWidget(self._wrap_page(self._build_performance_tab()))
        self.stack.addWidget(self._wrap_page(self._build_settings_page()))
        content.addWidget(self.stack, 1)

        # Status and live text are still visible on every page, but presented as modern cards.
        self.status_label = QLabel("准备就绪")
        self.status_label.setWordWrap(True)
        status_card = QFrame()
        status_card.setObjectName("StatusCard")
        sr = QHBoxLayout(status_card)
        sr.setContentsMargins(12, 8, 12, 8)
        dot = QLabel("●")
        dot.setStyleSheet("color:#48D597; font-size:15px;")
        sr.addWidget(dot)
        sr.addWidget(self.status_label, 1)
        content.addWidget(status_card)

        result_card = QFrame()
        result_card.setObjectName("ResultCard")
        result_layout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(10, 8, 10, 10)
        result_header = QHBoxLayout()
        result_title = QLabel("实时文本")
        result_title.setStyleSheet("font-weight:700;")
        result_header.addWidget(result_title)
        result_header.addStretch(1)
        self.translation_direction_label = QLabel("自动检测 → 简体中文")
        self.translation_direction_label.setObjectName("Muted")
        result_header.addWidget(self.translation_direction_label)
        result_layout.addLayout(result_header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        src = QWidget()
        sl = QVBoxLayout(src)
        sl.setContentsMargins(0, 0, 4, 0)
        src_label = QLabel("识别原文 / 语音转写")
        src_label.setObjectName("Muted")
        sl.addWidget(src_label)
        self.source_edit = QPlainTextEdit()
        self.source_edit.setReadOnly(True)
        self.source_edit.setPlaceholderText("识别出的原文会显示在这里")
        self.source_edit.setMaximumHeight(135)
        sl.addWidget(self.source_edit)
        splitter.addWidget(src)

        dst = QWidget()
        dl = QVBoxLayout(dst)
        dl.setContentsMargins(4, 0, 0, 0)
        self.translation_result_label = QLabel("翻译结果")
        self.translation_result_label.setObjectName("Muted")
        dl.addWidget(self.translation_result_label)
        self.translation_edit = QPlainTextEdit()
        self.translation_edit.setReadOnly(True)
        self.translation_edit.setPlaceholderText("翻译结果会显示在这里")
        self.translation_edit.setMaximumHeight(135)
        dl.addWidget(self.translation_edit)
        splitter.addWidget(dst)
        splitter.setSizes([1, 1])
        result_layout.addWidget(splitter)
        content.addWidget(result_card)

        shell.addWidget(content_wrap, 1)

        self._reload_language_combos()
        for combo in (self.source_combo, self.target_combo, self.audio_source_combo, self.audio_target_combo):
            combo.currentIndexChanged.connect(self._translation_direction_changed)
        self._nav_buttons[self.PAGE_HOME].setChecked(True)
        self._select_page(self.PAGE_HOME)
        self._apply_theme(str(self._settings.value("ui_theme", "dark")))

    def _wrap_page(self, page: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setWidget(page)
        return area

    def _select_page(self, index: int) -> None:
        titles = ["主页", "屏幕翻译", "声音翻译", "翻译记录", "语言包", "字幕", "性能", "设置"]
        self.stack.setCurrentIndex(index)
        self.page_title.setText(titles[index])
        if 0 <= index < len(self._nav_buttons):
            self._nav_buttons[index].setChecked(True)
        self._translation_direction_changed()

    # ---------- Home ----------
    def _build_home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(2, 8, 2, 8)
        hero = QFrame()
        hero.setObjectName("PixelCard")
        h = QHBoxLayout(hero)
        h.setContentsMargins(18, 14, 18, 14)
        art = QLabel()
        art.setPixmap(pixel_pixmap("app_logo", 92))
        art.setFixedSize(100, 100)
        h.addWidget(art)
        copy = QVBoxLayout()
        headline = QLabel("本地实时翻译，不打断你正在看的内容")
        headline.setStyleSheet("font-size:20px; font-weight:750;")
        desc = QLabel("屏幕 OCR、系统声音 / 麦克风、上下文翻译、VAD 自动断句和字幕叠加统一在一个应用中。")
        desc.setWordWrap(True)
        desc.setObjectName("Muted")
        copy.addWidget(headline)
        copy.addWidget(desc)
        h.addLayout(copy, 1)
        layout.addWidget(hero)

        cards = QGridLayout()
        cards.setHorizontalSpacing(12)
        cards.setVerticalSpacing(12)
        cards.addWidget(self._action_card("screen", "屏幕翻译", "框选、游戏窗口、Native OCR / RapidOCR", "打开屏幕翻译", self.PAGE_SCREEN), 0, 0)
        cards.addWidget(self._action_card("audio", "声音翻译", "实时课程、视频、系统声音、VAD 自动断句", "打开声音翻译", self.PAGE_AUDIO), 0, 1)
        cards.addWidget(self._action_card("languages", "语言包", "中英法日内置，其他语言按需下载 / 安装", "管理语言", self.PAGE_LANGUAGES), 1, 0)
        cards.addWidget(self._action_card("subtitles", "字幕样式", "像素风工具不意味着像素字幕：排版保持现代可读", "调整字幕", self.PAGE_SUBTITLES), 1, 1)
        layout.addLayout(cards)
        layout.addStretch(1)
        return page

    def _action_card(self, icon_name: str, title: str, description: str, action: str, page_index: int) -> QFrame:
        card = QFrame()
        card.setObjectName("PixelCard")
        row = QHBoxLayout(card)
        row.setContentsMargins(14, 12, 14, 12)
        icon = QLabel()
        icon.setPixmap(pixel_pixmap(icon_name, 66))
        icon.setFixedSize(72, 72)
        row.addWidget(icon)
        body = QVBoxLayout()
        t = QLabel(title)
        t.setStyleSheet("font-size:16px; font-weight:700;")
        d = QLabel(description)
        d.setWordWrap(True)
        d.setObjectName("Muted")
        btn = QPushButton(action)
        btn.setObjectName("PrimaryButton")
        btn.clicked.connect(partial(self._select_page, page_index))
        body.addWidget(t)
        body.addWidget(d)
        body.addWidget(btn, 0, Qt.AlignmentFlag.AlignLeft)
        row.addLayout(body, 1)
        return card

    # ---------- Language packs ----------
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
                combo.addItem(f"{info.get('flag', '')} {info['label']}", code)
            idx = combo.findData(current)
            if idx < 0:
                idx = combo.findData("auto" if allow_auto else "zh")
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)
        self._translation_direction_changed()

    # ---------- Subtitle preview ----------
    def _build_overlay_tab(self) -> QWidget:
        page = super()._build_overlay_tab()
        preview = QFrame()
        preview.setObjectName("PixelCard")
        pv = QVBoxLayout(preview)
        title = QLabel("实时预览")
        title.setStyleSheet("font-weight:700;")
        pv.addWidget(title)
        self._subtitle_preview = QLabel("The market remains volatile.\n市场仍然波动较大。")
        self._subtitle_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle_preview.setMinimumHeight(110)
        self._subtitle_preview.setWordWrap(True)
        pv.addWidget(self._subtitle_preview)
        layout = page.layout()
        if layout is not None:
            layout.insertWidget(max(0, layout.count() - 1), preview)
        return page

    def _overlay_setting_changed(self, *_args) -> None:
        super()._overlay_setting_changed(*_args)
        self._update_subtitle_preview()

    def _update_subtitle_preview(self) -> None:
        if self._subtitle_preview is None or not hasattr(self, "opacity_slider"):
            return
        bg_alpha = max(0, min(255, int(self.opacity_slider.value() * 2.55)))
        color = getattr(self, "_font_color", "#FFFFFF")
        source_color = getattr(self, "_source_font_color", "#C8C8C8")
        # QLabel cannot independently style two wrapped lines with QSS, so use lightweight rich text.
        self._subtitle_preview.setText(
            f'<div style="color:{source_color}; font-size:{self.source_font_size_spin.value()}px;">The market remains volatile.</div>'
            f'<div style="color:{color}; font-size:{self.font_size_spin.value()}px; font-weight:600;">市场仍然波动较大。</div>'
        )
        self._subtitle_preview.setStyleSheet(
            f"background:rgba(8,12,18,{bg_alpha}); border-radius:10px; padding:16px;"
        )

    def _apply_subtitle_preset(self) -> None:
        super()._apply_subtitle_preset()
        self._update_subtitle_preview()

    # ---------- Settings / theme ----------
    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(2, 8, 2, 8)

        card = QFrame()
        card.setObjectName("PixelCard")
        row = QHBoxLayout(card)
        icon = QLabel()
        icon.setPixmap(pixel_pixmap("settings", 78))
        icon.setFixedSize(84, 84)
        row.addWidget(icon)
        body = QVBoxLayout()
        t = QLabel("外观")
        t.setStyleSheet("font-size:18px; font-weight:700;")
        body.addWidget(t)
        line = QHBoxLayout()
        line.addWidget(QLabel("主题"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("深色", "dark")
        self.theme_combo.addItem("浅色", "light")
        self.theme_combo.currentIndexChanged.connect(self._theme_changed)
        line.addWidget(self.theme_combo, 1)
        body.addLayout(line)
        note = QLabel("像素风只用于品牌和导航美术，文本、设置与字幕仍采用现代高可读性排版。")
        note.setWordWrap(True)
        note.setObjectName("Muted")
        body.addWidget(note)
        row.addLayout(body, 1)
        layout.addWidget(card)

        storage = QFrame()
        storage.setObjectName("PixelCard")
        sl = QVBoxLayout(storage)
        st = QLabel("本地数据")
        st.setStyleSheet("font-size:16px; font-weight:700;")
        sl.addWidget(st)
        path = QLabel(str(data_dir()))
        path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        path.setObjectName("Muted")
        sl.addWidget(path)
        sl.addWidget(QLabel("模型、语言包、缓存与翻译历史都保存在本机用户数据目录。"))
        layout.addWidget(storage)

        if is_macos():
            perms = QFrame()
            perms.setObjectName("PixelCard")
            pl = QHBoxLayout(perms)
            pl.addWidget(QLabel("macOS 权限"))
            screen_btn = QPushButton("屏幕录制权限")
            screen_btn.clicked.connect(open_macos_screen_recording_settings)
            mic_btn = QPushButton("麦克风权限")
            mic_btn.clicked.connect(open_macos_microphone_settings)
            pl.addWidget(screen_btn)
            pl.addWidget(mic_btn)
            pl.addStretch(1)
            layout.addWidget(perms)
        layout.addStretch(1)
        return page

    def _theme_changed(self, *_args) -> None:
        mode = str(self.theme_combo.currentData() or "dark")
        self._settings.setValue("ui_theme", mode)
        self._apply_theme(mode)

    def _apply_theme(self, mode: str) -> None:
        self._theme_mode = "light" if mode == "light" else "dark"
        self.setStyleSheet(_LIGHT_QSS if self._theme_mode == "light" else _DARK_QSS)
        if self._theme_mode == "dark":
            self.translation_edit.setStyleSheet("font-size:15px; background:#111722;")
        else:
            self.translation_edit.setStyleSheet("font-size:15px; background:#FFFFFF;")
        self._update_subtitle_preview()

    def _translation_direction_changed(self, *_args) -> None:
        if not hasattr(self, "translation_direction_label"):
            return
        if self.stack.currentIndex() == self.PAGE_AUDIO and hasattr(self, "audio_source_combo"):
            src = self.audio_source_combo.currentText()
            dst = self.audio_target_combo.currentText()
        else:
            src = self.source_combo.currentText() if hasattr(self, "source_combo") else "自动检测"
            dst = self.target_combo.currentText() if hasattr(self, "target_combo") else "简体中文"
        self.translation_direction_label.setText(f"{src}  →  {dst}")
        if hasattr(self, "translation_result_label"):
            self.translation_result_label.setText(f"翻译结果 · {dst}")

    def _swap_screen_languages(self) -> None:
        super()._swap_screen_languages()
        self._translation_direction_changed()

    def _swap_audio_languages(self) -> None:
        super()._swap_audio_languages()
        self._translation_direction_changed()
