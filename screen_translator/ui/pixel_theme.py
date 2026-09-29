"""Shared light pixel skin for custom widgets and retained Qt settings controls."""
from .assets import pixel_dir
from .theme import FONT_FAMILY


def pixel_light_qss() -> str:
    root=pixel_dir().parent
    def art(name): return (root/'ui_target'/f'{name}.png').as_posix()
    def ui(name): return (root/'pixel_ui'/f'{name}.png').as_posix()
    return f'''
QWidget {{ font-family:"{FONT_FAMILY}"; font-size:15px; color:#183657; }}
QMainWindow, QDialog {{ background:#FFF8EC; }}
QLabel {{ background:transparent; }}
QLabel#PageTitle {{ font-size:26px; font-weight:800; color:#102E50; }}
QLabel#BrandTitle {{ font-size:19px; font-weight:700; color:#102E50; }}
QLabel#FieldLabel, QLabel#SectionTitle {{ font-size:16px; font-weight:700; }}
QLabel#WordTitle {{ font-size:26px; font-weight:800; }}
QLabel#Muted {{ color:#61768B; }}
QLabel#StatusText {{ font-size:17px; font-weight:700; }}
QWidget#MetricColumn {{ border-left:1px solid #D6D5CC; }}
QFrame#NavSeparator {{ background:#C9C8BC; border:0; }}
QWidget#WindowControls {{ background:#FFE6CD; }}
QPushButton {{ border-image:url("{art('button_secondary')}") 10 10 10 10 stretch stretch; border-width:7px; border-style:solid; padding:4px 10px; min-height:22px; font-weight:600; color:#153556; background:transparent; }}
QPushButton:hover {{ border-image:url("{art('button_secondary_hover')}") 10 10 10 10 stretch stretch; }}
QPushButton:pressed {{ border-image:url("{art('button_secondary_pressed')}") 10 10 10 10 stretch stretch; }}
QPushButton:disabled {{ color:#91A0AD; }}
QPushButton#PrimaryButton {{ border-image:url("{art('button_primary')}") 16 16 16 16 stretch stretch; border-width:10px; color:white; font-weight:700; }}
QPushButton#DangerButton {{ border-image:url("{art('button_danger')}") 10 10 10 10 stretch stretch; }}
QPushButton#IconButton {{ padding:1px; min-width:22px; max-width:22px; min-height:22px; max-height:22px; }}
QPushButton#NavButton {{ border:0; border-image:none; background:transparent; padding:0; text-align:left; font-size:17px; font-weight:600; min-height:48px; max-height:48px; }}
QPushButton#WindowControl {{ border:0; border-image:none; padding:0; background:transparent; font-size:24px; min-height:0; }}
QPushButton#WindowControl:hover {{ background:#FFD5AF; }}
QPushButton[pixelPainted="true"] {{ border:0; border-image:none; padding:0; background:transparent; min-height:44px; }}
QPushButton#ScreenStart {{ font-size:22px; font-weight:700; min-height:66px; }}
QPushButton[sceneButton="true"] {{ min-height:80px; max-height:80px; }}
QPushButton[pixelIcon="true"] {{ min-height:38px; max-height:38px; min-width:38px; max-width:38px; }}
QPushButton#TextAction {{ border:0; border-image:none; padding:2px; min-height:0; color:#688198; font-size:12px; background:transparent; }}
QPushButton#TextAction:hover {{ color:#136B9F; }}
QFrame#PixelCard, QFrame#PreviewCard, QFrame#StatusCard, QFrame#ResultCard, QGroupBox {{ border-image:url("{art('card')}") 10 10 10 10 stretch stretch; border-width:8px; border-style:solid; background:transparent; }}
QGroupBox {{ margin-top:14px; padding:12px 4px 4px; font-weight:700; }}
QGroupBox::title {{ subcontrol-origin:margin; subcontrol-position:top left; left:14px; padding:0 6px; background:#FFF9EF; }}
QComboBox, QSpinBox, QDoubleSpinBox, QFontComboBox, QLineEdit, QKeySequenceEdit {{ border-image:url("{art('combo')}") 7 7 7 7 stretch stretch; border-width:5px; border-style:solid; padding:5px 10px; min-height:22px; background:transparent; color:#1C3958; selection-background-color:#BDE7F7; }}
QComboBox {{ padding-right:28px; }}
QComboBox::drop-down {{ subcontrol-origin:padding; subcontrol-position:top right; width:26px; border:0; background:transparent; }}
QComboBox::down-arrow {{ image:url("{art('arrow_down')}"); width:12px; height:10px; }}
QComboBox QAbstractItemView {{ background:#FFFBF3; border:2px solid #7C99B0; selection-background-color:#A3D8F0; selection-color:#123556; outline:0; padding:4px; }}
QSpinBox {{ padding-right:26px; }}
QSpinBox::up-button, QSpinBox::down-button {{ width:24px; border:0; background:#EEF6F9; }}
QSpinBox::up-arrow {{ image:url("{art('arrow_up')}"); width:9px; height:6px; }}
QSpinBox::down-arrow {{ image:url("{art('arrow_down')}"); width:9px; height:6px; }}
QCheckBox, QRadioButton {{ spacing:8px; font-weight:400; }}
QCheckBox::indicator {{ width:20px; height:20px; image:url("{art('checkbox_off')}"); }}
QCheckBox::indicator:checked {{ image:url("{art('checkbox_on')}"); }}
QRadioButton::indicator {{ width:20px; height:20px; image:url("{ui('radio_off')}"); }}
QRadioButton::indicator:checked {{ image:url("{ui('radio_on')}"); }}
QSlider::groove:horizontal {{ border-image:url("{art('combo')}") 7 7 7 7 stretch stretch; border-width:3px; height:6px; }}
QSlider::sub-page:horizontal {{ background:#6BC2EB; margin:2px; }}
QSlider::handle:horizontal {{ image:url("{art('slider_handle')}"); width:22px; height:22px; margin:-8px 0; }}
QProgressBar {{ border-image:url("{art('combo')}") 7 7 7 7 stretch stretch; border-width:4px; border-style:solid; min-height:18px; text-align:center; background:#FFF9EF; }}
QProgressBar::chunk {{ background:#56C887; margin:2px; }}
QPlainTextEdit, QTextBrowser, QTableWidget, QListWidget, QTreeWidget {{ border-image:url("{art('card')}") 10 10 10 10 stretch stretch; border-width:6px; border-style:solid; padding:6px; background:#FFFCF5; alternate-background-color:#EFF6F8; gridline-color:#E3DDD2; }}
QHeaderView::section {{ background:#E7F2F6; color:#264967; padding:8px; border:0; border-bottom:1px solid #C3D4DC; font-weight:600; }}
QScrollArea, QStackedWidget {{ border:0; background:transparent; }}
QScrollArea > QWidget > QWidget {{ background:transparent; }}
QScrollBar:vertical {{ width:10px; background:#F5F0E6; margin:0; }}
QScrollBar::handle:vertical {{ border-image:url("{art('scene_selected')}") 8 8 8 8 stretch stretch; border-width:3px; border-style:solid; min-height:30px; }}
QScrollBar:horizontal {{ height:10px; background:#F5F0E6; margin:0; }}
QScrollBar::handle:horizontal {{ background:#8FCAE3; min-width:30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width:0; height:0; }}
QToolTip {{ background:#FFF8E8; color:#173653; border:1px solid #8399AC; padding:6px; }}
QMenu {{ border-image:url("{art('frame_window')}") 16 16 16 16 stretch stretch; border-width:8px; border-style:solid; padding:4px; background:#FFF9EF; }}
QMenu::item {{ padding:9px 24px 9px 12px; }}
QMenu::item:selected {{ background:#B2DEF0; }}
QLabel#ShortcutChip {{ background:#F4F7F8; padding:6px; }}
'''
