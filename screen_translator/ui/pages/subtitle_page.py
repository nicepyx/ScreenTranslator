"""Subtitle settings use shared image-skinned controls and the real renderer."""
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QCheckBox, QPushButton, QLabel, QSlider, QSpinBox, QFontComboBox
from ...constants import (SUBTITLE_PRESETS, SUBTITLE_DISPLAY_MODES, SUBTITLE_RECENT_COUNTS, SUBTITLE_RETENTION_MODES,
                          SUBTITLE_MAX_LINES, OVERLAY_ALIGNMENTS, OVERLAY_POSITIONS, OVERLAY_WIDTHS)
from ..components import PixelCard, PixelComboBox
from ..overlay import SubtitleCanvas
from ..theme import FONT_FAMILY
from .screen_page import PageHero, label


class PreviewStage(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(230)
        layout=QVBoxLayout(self)
        layout.setContentsMargins(16,24,16,24)
        self.canvas=SubtitleCanvas()
        layout.addWidget(self.canvas)
    def paintEvent(self,event):
        p=QPainter(self)
        for y in range(0,self.height(),16):
            for x in range(0,self.width(),16):
                p.fillRect(QRect(x,y,16,16),QColor('#D6E3F2' if (x//16+y//16)%2 else '#E6EDF7'))


def row(*widgets):
    item=QWidget()
    layout=QHBoxLayout(item)
    layout.setContentsMargins(0,0,0,0)
    layout.setSpacing(8)
    for widget in widgets: layout.addWidget(widget)
    return item


def button(text,slot):
    b=QPushButton(text)
    b.clicked.connect(slot)
    return b


def form_card(title):
    card=PixelCard()
    outer=QVBoxLayout(card)
    outer.setContentsMargins(18,16,18,18)
    outer.setSpacing(12)
    outer.addWidget(label(title))
    form=QFormLayout()
    form.setHorizontalSpacing(14)
    form.setVerticalSpacing(12)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    outer.addLayout(form)
    return card,form


class SubtitlePage(QWidget):
    def __init__(self,host):
        super().__init__()
        self.setObjectName('SubtitlePage')
        layout=QVBoxLayout(self)
        layout.setContentsMargins(16,8,16,16)
        layout.setSpacing(16)
        layout.addWidget(PageHero('字幕设置','调整字幕外观，在右侧查看实际效果。','subtitles'))
        columns=QHBoxLayout()
        columns.setSpacing(16)
        left=QVBoxLayout()
        left.setSpacing(14)
        columns.addLayout(left,3)
        preview=PixelCard()
        right=QVBoxLayout(preview)
        right.setContentsMargins(16,16,16,16)
        right.addWidget(label('字幕预览'))
        stage=PreviewStage()
        host._subtitle_preview=stage.canvas
        right.addWidget(stage)
        note=label('The market remains volatile.\n市场仍然波动较大。',muted=True)
        note.setWordWrap(True)
        right.addWidget(note)
        right.addSpacing(8)
        right.addWidget(button('重置字幕位置',host._reset_overlay_position))
        hint=label('透明格表示桌面背景。更改左侧设置，会同步应用到字幕浮窗。',muted=True)
        hint.setWordWrap(True)
        right.addWidget(hint)
        right.addStretch()
        preview.setMinimumWidth(270)
        preview.setMaximumWidth(360)
        columns.addWidget(preview,2,alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(columns)
        layout.addStretch()

        display,form=form_card('显示与停留')
        left.addWidget(display)
        host.overlay_visible_check=QCheckBox('显示字幕')
        host.overlay_visible_check.setChecked(True)
        host.overlay_lock_check=QCheckBox('锁定位置')
        host.overlay_passthrough_check=QCheckBox('鼠标穿透')
        form.addRow(row(host.overlay_visible_check,host.overlay_lock_check,host.overlay_passthrough_check))
        def combo(attr,items):
            widget=PixelComboBox()
            for text,value in items: widget.addItem(text,value)
            setattr(host,attr,widget)
            return widget
        combo('subtitle_preset_combo',[(item['label'],key) for key,item in SUBTITLE_PRESETS.items()])
        form.addRow('字幕预设',row(host.subtitle_preset_combo,button('应用',host._apply_subtitle_preset)))
        for title,attr,items in [('显示内容','subtitle_display_combo',SUBTITLE_DISPLAY_MODES),
                                 ('滚动字幕','subtitle_recent_combo',SUBTITLE_RECENT_COUNTS),
                                 ('智能停留','subtitle_retention_combo',SUBTITLE_RETENTION_MODES),
                                 ('每条行数','subtitle_lines_combo',SUBTITLE_MAX_LINES)]:
            form.addRow(title,combo(attr,items))
        host.opacity_slider=QSlider(Qt.Orientation.Horizontal)
        host.opacity_slider.setRange(0,100)
        host.opacity_slider.setValue(70)
        host.opacity_value_label=QLabel('70%')
        host.opacity_value_label.setMinimumWidth(40)
        form.addRow('背景透明度',row(host.opacity_slider,host.opacity_value_label))
        host.subtitle_smooth_check=QCheckBox('Partial / Final 平滑更新')
        host.subtitle_smooth_check.setChecked(True)
        form.addRow(host.subtitle_smooth_check)

        style,sf=form_card('字体与效果')
        left.addWidget(style)
        for title,prefix,low,high,value,color,slot in [('译文','font',10,64,18,'#FFFFFF',host._choose_font_color),
                                                      ('原文','source_font',9,52,14,'#C8C8C8',host._choose_source_font_color)]:
            control=button('颜色',slot)
            setattr(host,prefix+'_color_button',control)
            swatch=QLabel(color)
            setattr(host,prefix+'_color_preview',swatch)
            size=QSpinBox()
            size.setRange(low,high)
            size.setValue(value)
            size.setSuffix(' px')
            setattr(host,prefix+'_size_spin',size)
            sf.addRow(title,row(control,swatch,size))
        host.outline_width_spin=QSpinBox()
        host.outline_width_spin.setRange(0,5)
        host.outline_width_spin.setValue(2)
        host.outline_width_spin.setSuffix(' px')
        host.outline_color_button=button('描边颜色',host._choose_outline_color)
        host.outline_color_preview=QLabel('#000000')
        sf.addRow('描边',row(host.outline_width_spin,host.outline_color_button,host.outline_color_preview))
        host.subtitle_shadow_check=QCheckBox('文字阴影')
        host.subtitle_shadow_check.setChecked(True)
        sf.addRow(host.subtitle_shadow_check)
        host.font_family_combo=QFontComboBox()
        host.font_family_combo.setCurrentFont(QFont(FONT_FAMILY))
        sf.addRow('字体',host.font_family_combo)
        sf.addRow(button('导入字体…',host._import_custom_font))

        position,pf=form_card('位置与排版')
        left.addWidget(position)
        for title,attr,items in [('对齐','align_combo',[(v,k) for k,v in OVERLAY_ALIGNMENTS.items()]),
                                 ('位置','position_combo',[(v,k) for k,v in OVERLAY_POSITIONS.items()]),
                                 ('宽度','width_combo',OVERLAY_WIDTHS)]:
            pf.addRow(title,combo(attr,items))
        left.addStretch()
        # Connect only after all controls exist. Restoring settings and applying
        # presets can now update the renderer without reading half-built UI.
        host.overlay_visible_check.toggled.connect(host._overlay_visibility_changed)
        host.overlay_lock_check.toggled.connect(host._overlay_lock_requested)
        host.overlay_passthrough_check.toggled.connect(host._overlay_setting_changed)
        for name in ('subtitle_display_combo','subtitle_recent_combo','subtitle_retention_combo','subtitle_lines_combo','align_combo','position_combo','width_combo'):
            getattr(host,name).currentIndexChanged.connect(host._overlay_setting_changed)
        for name in ('font_size_spin','source_font_size_spin','outline_width_spin','opacity_slider'):
            getattr(host,name).valueChanged.connect(host._overlay_setting_changed)
        host.opacity_slider.valueChanged.connect(lambda value:host.opacity_value_label.setText(f'{value}%'))
        host.subtitle_smooth_check.toggled.connect(host._overlay_setting_changed)
        host.subtitle_shadow_check.toggled.connect(host._overlay_setting_changed)
        host.font_family_combo.currentFontChanged.connect(host._font_family_changed)


def update_preview(host):
    if host._subtitle_preview is None: return
    canvas=host._subtitle_preview
    canvas.configure(background_opacity=host.opacity_slider.value(),translation_font_size=host.font_size_spin.value(),
                     source_font_size=host.source_font_size_spin.value(),translation_color=host._font_color,
                     source_color=host._source_font_color,font_family=host._font_family,
                     display_mode=host.subtitle_display_combo.currentData(),shadow_enabled=host.subtitle_shadow_check.isChecked(),
                     outline_width=host.outline_width_spin.value(),outline_color=host._outline_color,
                     max_lines=int(host.subtitle_lines_combo.currentData() or 0),recent_count=1,retention_mode='keep',
                     alignment=host.align_combo.currentData(),smooth_updates=False)
    canvas.clear()
    canvas.push('市场仍然波动较大。','The market remains volatile.')
