import sys

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from .constants import APP_NAME, APP_VERSION
from .ui.main_window import MainWindow
from .ui.theme import FONT_FAMILY


def run() -> int:
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(APP_VERSION)
    QCoreApplication.setOrganizationName("Local")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont(FONT_FAMILY, 10))

    window = MainWindow()
    window.show()
    return app.exec()
