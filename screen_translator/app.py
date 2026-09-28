import platform
import sys

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from .constants import APP_NAME, APP_VERSION
from .ui.main_window import MainWindow


def run() -> int:
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(APP_VERSION)
    QCoreApplication.setOrganizationName("Local")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    system = platform.system()
    if system == "Windows":
        app.setFont(QFont("Segoe UI", 10))
    elif system == "Darwin":
        app.setFont(QFont("SF Pro Text", 10))
    else:
        app.setFont(QFont("Noto Sans", 10))

    window = MainWindow()
    window.show()
    return app.exec()
