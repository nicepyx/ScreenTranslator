"""Single construction path: title bar + sidebar + current page.

Floating windows are owned by the application lifecycle, never by page layouts.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMainWindow, QScrollArea, QSizeGrip, QStackedWidget, QVBoxLayout, QWidget

from ..constants import APP_NAME, APP_VERSION
from ..core.hotkeys import GlobalHotkeyManager
from ..core.language_packs import LanguagePackManager
from ..core.speech import SpeechService
from ..core.storage import StorageManager
from ..core.vocabulary import VocabularyStore
from .assets import pixel_icon
from .components import PixelNineSliceFrame, PixelSidebar, PixelTitleBar
from .desktop_actions import DesktopActionsMixin
from .pages.existing_pages import ExistingPagesMixin
from .pages.preserved_pages import PreservedPagesMixin
from .pages.screen_page import ScreenPage
from .pixel_theme import pixel_light_qss
from .window_logic import TranslatorWindowLogicMixin


class MainWindow(DesktopActionsMixin, ExistingPagesMixin, PreservedPagesMixin, TranslatorWindowLogicMixin, QMainWindow):
    PAGE_SCREEN, PAGE_AUDIO, PAGE_HISTORY, PAGE_LANGUAGES, PAGE_VOCABULARY = range(5)
    PAGE_SUBTITLES, PAGE_PERFORMANCE, PAGE_DATA, PAGE_HOTKEYS, PAGE_SETTINGS = range(5, 10)

    def __init__(self):
        super().__init__()
        self._force_quit = False
        self._storage_manager = StorageManager()
        self._vocabulary = VocabularyStore()
        self._hotkeys = GlobalHotkeyManager()
        self._speech = SpeechService()
        self._language_packs = LanguagePackManager()
        self._usage_buttons = {}
        self._subtitle_preview = None
        self._language_card_grid = None
        self._initialize_logic()
        saved_page = int(self._settings.value("ui_last_page", self.PAGE_SCREEN))
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setWindowIcon(pixel_icon("app_logo"))
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)
        self.setStyleSheet(pixel_light_qss())
        self._build_ui()
        self._restore_runtime()
        self._setup_tray()
        self._setup_mini_toolbar()
        self.mini_toolbar.move(int(self._settings.value("mini_toolbar_x", 80)), int(self._settings.value("mini_toolbar_y", 80)))
        self._setup_word_popup()
        self._setup_hotkeys()
        self._select_page(saved_page)
        self._update_subtitle_preview()
        self._refresh_vocabulary()
        self._refresh_storage_summary()

    def _build_ui(self):
        root = PixelNineSliceFrame("frame_window", inset=16, border=10)
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 7, 10, 8)
        layout.setSpacing(0)
        self.title_bar = PixelTitleBar(self)
        layout.addWidget(self.title_bar)
        body = QHBoxLayout()
        body.setContentsMargins(2, 0, 6, 0)
        body.setSpacing(14)
        self.sidebar = PixelSidebar()
        self.sidebar.pageRequested.connect(self._select_page)
        self._nav_buttons = self.sidebar.buttons
        body.addWidget(self.sidebar)
        self.stack = QStackedWidget()
        self.stack.setObjectName("PageContainer")
        body.addWidget(self.stack, 1)
        layout.addLayout(body, 1)
        grip = QSizeGrip(root)
        grip.setFixedSize(6, 6)
        layout.addWidget(grip, alignment=Qt.AlignmentFlag.AlignRight)
        self.screen_page = ScreenPage(self)
        for page in (self.screen_page, self._build_audio_tab(), self._build_history_tab(),
                     self._build_language_page(), self._build_vocabulary_page(), self._build_overlay_tab(),
                     self._build_performance_tab(), self._build_data_page(), self._build_hotkeys_page(), self._build_settings_page()):
            self.stack.addWidget(self._wrap_page(page))
        self._reload_language_combos()
        for combo in (self.source_combo, self.target_combo, self.audio_source_combo, self.audio_target_combo):
            combo.currentIndexChanged.connect(self._translation_direction_changed)
        self._sync_usage_buttons()

    @staticmethod
    def _wrap_page(page: QWidget):
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        area.setWidget(page)
        return area

    def _select_page(self, index):
        index = max(0, min(index, self.stack.count() - 1))
        self.stack.setCurrentIndex(index)
        self._nav_buttons[index].setChecked(True)
        self._settings.setValue("ui_last_page", index)
        self._translation_direction_changed()
