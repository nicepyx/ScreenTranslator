from PySide6.QtCore import QRect, Qt, Signal, QSize
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QVBoxLayout, QWidget, QPushButton, QFrame
from ...constants import APP_NAME, APP_VERSION
from ..assets import pixel_pixmap
from ..theme import SIDEBAR_WIDTH, TITLEBAR_HEIGHT
from .pixel import PixelNineSliceFrame, plate, draw_nine_slice


class PixelTitleBar(PixelNineSliceFrame):
    def __init__(self, host):
        super().__init__("titlebar", host, inset=4, border=0)
        self.host = host
        self._drag_offset = None
        self.setObjectName("PixelTitleBar")
        self.setFixedHeight(TITLEBAR_HEIGHT)
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 0, 0)
        row.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(pixel_pixmap("app_logo", 32))
        row.addWidget(logo)
        title = QLabel(APP_NAME)
        title.setObjectName("BrandTitle")
        title.setToolTip(f"{APP_NAME} v{APP_VERSION}")
        row.addWidget(title)
        row.addStretch()
        controls = QWidget()
        controls.setObjectName("WindowControls")
        cr = QHBoxLayout(controls)
        cr.setContentsMargins(0, 0, 0, 0)
        cr.setSpacing(0)
        for text, tip, action in (("−", "最小化", host.showMinimized), ("▣", "最大化 / 还原", self.toggle_maximized), ("×", "关闭", host.close)):
            button = QPushButton(text)
            button.setObjectName("WindowControl")
            button.setToolTip(tip)
            button.setAccessibleName(tip)
            button.setFixedSize(48, TITLEBAR_HEIGHT)
            button.clicked.connect(action)
            cr.addWidget(button)
        row.addWidget(controls)
        for label in self.findChildren(QLabel):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def toggle_maximized(self):
        self.host.showNormal() if self.host.isMaximized() else self.host.showMaximized()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: self.toggle_maximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.host.windowHandle().startSystemMove():
                self._drag_offset = event.globalPosition().toPoint() - self.host.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.host.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event): self._drag_offset = None


class PixelNavItem(QPushButton):
    def __init__(self, text, icon):
        super().__init__(text)
        self.art = pixel_pixmap(icon, 32)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("NavButton")
        self.setFixedHeight(48)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        if self.isChecked():
            draw_nine_slice(p, self.rect(), plate("nav_selected"), 6, 5)
        elif self.underMouse() or self.hasFocus():
            p.fillRect(self.rect().adjusted(3,3,-3,-3), QColor("#E5F1F5"))
        p.drawPixmap(20 + (32-self.art.width())//2, (self.height()-self.art.height())//2, self.art)
        p.setPen(QColor("#123052"))
        p.drawText(self.rect().adjusted(68,0,-8,0), Qt.AlignmentFlag.AlignVCenter, self.text())


class SidebarArt(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(84)
        self.setMaximumHeight(154)
    def paintEvent(self, event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        pix=plate("sidebar_cat")
        size=pix.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        p.drawPixmap(QRect(0,self.height()-size.height(),self.width(),size.height()),pix)


class PixelSidebar(QWidget):
    pageRequested = Signal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PixelSidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        layout=QVBoxLayout(self)
        layout.setContentsMargins(0,12,0,0)
        layout.setSpacing(2)
        self.group=QButtonGroup(self)
        self.buttons=[]
        specs=[("screen","屏幕翻译"),("audio","声音翻译"),("history","历史记录"),("languages","语言包"),("vocabulary","词汇学习"),
               ("subtitles","字幕设置"),("performance","性能设置"),("data","数据管理"),("hotkeys","快捷键"),("settings","设置")]
        for index,(icon,text) in enumerate(specs):
            if index==5:
                separator=QFrame()
                separator.setObjectName("NavSeparator")
                separator.setFixedHeight(1)
                separator.setFixedWidth(174)
                layout.addSpacing(8)
                layout.addWidget(separator,alignment=Qt.AlignmentFlag.AlignHCenter)
                layout.addSpacing(8)
            button=PixelNavItem(text,icon)
            self.group.addButton(button,index)
            self.buttons.append(button)
            layout.addWidget(button)
        self.group.idClicked.connect(self.pageRequested)
        layout.addStretch(1)
        layout.addWidget(SidebarArt())

    def paintEvent(self,event):
        p=QPainter(self)
        p.fillRect(self.rect(),QColor("#FFF8EC"))
        p.setPen(QColor("#E0D6C8"))
        p.drawLine(self.width()-1,0,self.width()-1,self.height())
