"""Screen page follows the approved main-window reference; dialogs hold detail."""
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget, QFrame
from ...constants import OCR_QUALITY_PRESETS
from ..scene_presets import SCENE_PRESETS as USAGE_MODES
from ..assets import pixel_pixmap
from ..components import PixelButton, PixelCard, PixelComboBox, PixelIconButton, PixelSceneButton
from ..components.pixel import PixelNineSliceFrame, plate
from ..pixel_widgets import ClickableTextBrowser, StatusLabel


def label(text, *, muted=False):
    item=QLabel(text)
    item.setObjectName("Muted" if muted else "FieldLabel")
    return item


def card_layout(card, kind=QVBoxLayout):
    layout=kind(card)
    layout.setContentsMargins(20,18,20,18)
    layout.setSpacing(12)
    return layout


class PageHero(QWidget):
    def __init__(self, title, description, icon="hero_screen", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(104)
        row=QHBoxLayout(self)
        row.setContentsMargins(12,16,12,16)
        row.setSpacing(14)
        picture=QLabel()
        picture.setPixmap(pixel_pixmap(icon,60))
        row.addWidget(picture)
        text=QVBoxLayout()
        text.setSpacing(4)
        heading=label(title)
        heading.setObjectName("PageTitle")
        text.addWidget(heading)
        note=label(description,muted=True)
        note.setWordWrap(True)
        text.addWidget(note)
        row.addLayout(text,1)
        row.addSpacing(250)

    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,False)
        art=plate("landscape")
        height=min(94,self.height()-8)
        width=round(art.width()*height/art.height())
        p.drawPixmap(QRect(self.width()-width,8,width,height),art)


class ScreenPage(PixelNineSliceFrame):
    def __init__(self,host):
        super().__init__("card",inset=10,border=8)
        self.setObjectName("ScreenPage")
        self.setMaximumWidth(1220)
        layout=QVBoxLayout(self)
        layout.setContentsMargins(20,8,20,20)
        layout.setSpacing(20)
        layout.addWidget(PageHero("屏幕翻译","手动框选屏幕区域，完成一次 OCR 与本地翻译。"))
        languages=PixelCard()
        languages.setMinimumHeight(90)
        row=card_layout(languages,QHBoxLayout)
        row.addWidget(label("源语言"))
        row.addSpacing(12)
        host.source_combo=PixelComboBox()
        row.addWidget(host.source_combo,1)
        host.screen_swap_button=PixelButton("","swap")
        host.screen_swap_button.flat=True
        host.screen_swap_button.setMaximumWidth(60)
        host.screen_swap_button.setToolTip("交换源语言和目标语言")
        host.screen_swap_button.clicked.connect(host._swap_screen_languages)
        row.addWidget(host.screen_swap_button)
        row.addWidget(label("目标语言"))
        row.addSpacing(8)
        host.target_combo=PixelComboBox()
        row.addWidget(host.target_combo,1)
        layout.addWidget(languages)

        source=PixelCard()
        source.setMinimumHeight(230)
        grid=card_layout(source,QGridLayout)
        grid.setVerticalSpacing(18)
        source_icon=QLabel()
        source_icon.setPixmap(pixel_pixmap("source",34))
        grid.addWidget(source_icon,0,0)
        grid.addWidget(label("识别区域"),0,1)
        selection=QWidget()
        sr=QHBoxLayout(selection)
        sr.setContentsMargins(0,0,0,0)
        sr.setSpacing(12)
        thumbnail=QLabel()
        thumbnail.setPixmap(pixel_pixmap("screen",68))
        sr.addWidget(thumbnail)
        region_label=label("点击下方按钮后，拖动鼠标框选需要翻译的文字区域",muted=True)
        region_label.setWordWrap(True)
        sr.addWidget(region_label,1)
        host.source_settings_button=PixelIconButton("settings","OCR 设置 / 最近翻译")
        sr.addWidget(host.source_settings_button)
        grid.addWidget(selection,0,2)
        separator=QFrame()
        separator.setObjectName("NavSeparator")
        separator.setFixedHeight(1)
        grid.addWidget(separator,1,0,1,3)
        scene_icon=QLabel()
        scene_icon.setPixmap(pixel_pixmap("scene_label",34))
        grid.addWidget(scene_icon,2,0)
        grid.addWidget(label("使用场景"),2,1)
        scenes=QHBoxLayout()
        scenes.setSpacing(8)
        host.usage_mode_combo=QComboBox(self)
        for key,info in USAGE_MODES.items(): host.usage_mode_combo.addItem(info['label'],key)
        host.usage_mode_combo.hide()
        for key,text,art in (("general","通用","general"),("game","游戏","game"),("course","网课","course"),("quality","视频","video"),("meeting","会议","meeting")):
            button=PixelSceneButton(text,art)
            button.clicked.connect(lambda checked=False,k=key:host._set_usage_mode_by_key(k))
            host._usage_buttons[key]=button
            scenes.addWidget(button,1)
        custom=PixelSceneButton("自定义","custom")
        custom.setCheckable(False)
        custom.setToolTip("打开 OCR 设置")
        scenes.addWidget(custom,1)
        grid.addLayout(scenes,2,2)
        grid.setColumnStretch(2,1)
        layout.addWidget(source)

        actions=QHBoxLayout()
        actions.setSpacing(12)
        host.once_button=PixelButton("框选并翻译一次","screen",primary=True)
        host.once_button.setObjectName("ScreenStart")
        host.once_button.setMinimumHeight(66)
        host.once_button.setMinimumWidth(250)
        host.once_button.setMaximumWidth(360)
        host.once_button.clicked.connect(host._start_screen_once)
        actions.addWidget(host.once_button,3)
        actions.addStretch(1)
        for text,icon,action in (("清空字幕","clear",host._clear_result_text),("迷你模式","pin",host._toggle_mini_toolbar)):
            button=PixelButton(text,icon)
            button.clicked.connect(action)
            actions.addWidget(button)
        layout.addLayout(actions)

        status=PixelCard("status_card")
        status.setMinimumHeight(110)
        status_grid=card_layout(status,QGridLayout)
        host.screen_ready_dot=QLabel()
        host.screen_ready_dot.setPixmap(pixel_pixmap("status_ready",24))
        status_grid.addWidget(host.screen_ready_dot,0,0)
        host.screen_status_summary=label("Ready")
        host.screen_status_summary.setObjectName("StatusText")
        status_grid.addWidget(host.screen_status_summary,0,1)
        host.status_label=StatusLabel("准备就绪，按快捷键或点击按钮后框选区域")
        host.status_label.setWordWrap(True)
        host.status_label.setObjectName("Muted")
        host.status_label.textChanged.connect(host._status_text_changed)
        status_grid.addWidget(host.status_label,1,1)
        host.metric_ocr,host.metric_translator,host.metric_latency=QLabel("--"),QLabel("--"),QLabel("--")
        for column,(name,widget) in enumerate((("OCR",host.metric_ocr),("翻译引擎",host.metric_translator),("延迟",host.metric_latency)),2):
            metric=QWidget()
            mr=QVBoxLayout(metric)
            mr.setContentsMargins(18,0,8,0)
            mr.addWidget(label(name,muted=True))
            mr.addWidget(widget)
            metric.setMinimumWidth(82)
            metric.setObjectName("MetricColumn")
            status_grid.addWidget(metric,0,column,2,1)
        status_grid.setColumnStretch(1,1)
        layout.addWidget(status)
        layout.addStretch(1)

        host.screen_options_dialog=QDialog(host)
        host.screen_options_dialog.setWindowTitle("屏幕翻译设置")
        host.screen_options_dialog.resize(620,360)
        options_layout=QVBoxLayout(host.screen_options_dialog)
        host.source_settings_button.clicked.connect(host.screen_options_dialog.show)
        custom.clicked.connect(host.screen_options_dialog.show)
        advanced = PixelCard()
        form = card_layout(advanced, QGridLayout)
        host.ocr_quality_combo, host.ocr_backend_combo = (PixelComboBox() for _ in range(2))
        for combo, items in ((host.ocr_quality_combo, OCR_QUALITY_PRESETS),
                             (host.ocr_backend_combo, [(name, key) for key, name in host._ocr.available_backends()])):
            for name, data in items:
                combo.addItem(name, data)
        for i, (title, widget) in enumerate(((label("OCR 质量"), host.ocr_quality_combo),
                                            (label("OCR 引擎"), host.ocr_backend_combo))):
            form.addWidget(title, i, 0)
            form.addWidget(widget, i, 1)
        host.accel_label = label("翻译模型固定使用 CPU INT8；语音识别可单独使用硬件加速。", muted=True)
        host.accel_label.setWordWrap(True)
        form.addWidget(host.accel_label, 2, 0, 1, 2)
        options_layout.addWidget(advanced)

        result_button = PixelButton("查看最近翻译 · 点词 / 复制 / 朗读")
        options_layout.addWidget(result_button)
        host.screen_results_dialog = QDialog(host)
        host.screen_results_dialog.setWindowTitle("最近翻译")
        host.screen_results_dialog.resize(680, 480)
        results_outer = QVBoxLayout(host.screen_results_dialog)
        results = PixelCard()
        result_layout = card_layout(results)
        host.source_edit, host.translation_edit = ClickableTextBrowser(), ClickableTextBrowser()
        host.source_edit.setMinimumHeight(100)
        host.translation_edit.setMinimumHeight(100)
        host.source_edit.wordClicked.connect(host._lookup_word)
        host.translation_edit.wordClicked.connect(host._lookup_translated_word)
        result_layout.addWidget(label("原文"))
        result_layout.addWidget(host.source_edit)
        result_layout.addWidget(label("译文"))
        result_layout.addWidget(host.translation_edit)
        row = QHBoxLayout()
        for text, action in (("复制原文", host._copy_source), ("复制译文", host._copy_translation), ("朗读译文", host._speak_translation)):
            button = PixelButton(text)
            button.clicked.connect(action)
            row.addWidget(button)
        result_layout.addLayout(row)
        results_outer.addWidget(results)
        result_button.clicked.connect(host.screen_results_dialog.show)
        cancel = PixelButton("取消当前任务")
        cancel.clicked.connect(host._cancel_current_task)
        options_layout.addWidget(cancel)


        host.usage_mode_combo.currentIndexChanged.connect(host._usage_mode_changed)
        host.ocr_quality_combo.currentIndexChanged.connect(host._mark_performance_custom)
        host.ocr_backend_combo.currentIndexChanged.connect(lambda _:host._save_settings())
