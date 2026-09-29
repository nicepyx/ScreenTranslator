"""Run the real Qt UI in isolated storage, without starting OCR/ASR/downloads.

Use --native to exercise Windows' Qt backend; otherwise use offscreen rendering.
QT_SCALE_FACTOR is supplied by the caller before QApplication is created.
"""
from __future__ import annotations

import argparse
import gc
import os
from pathlib import Path
import sys
import tempfile
from contextlib import ExitStack
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--scale", default="1")
    parser.add_argument("--output", default="logs/ui-refactor")
    parser.add_argument("--capture-only", action="store_true")
    args = parser.parse_args()
    os.environ["QT_SCREEN_SCALE_FACTORS"] = "1"
    # Pin the native base at 1 so the requested factor is the tested DPR,
    # independent of the developer machine's current Windows display setting.
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_SCALE_FACTOR"] = args.scale
    if not args.native:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QPoint, QSize, Qt
    from PySide6.QtGui import QFont
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from screen_translator.core.app_settings import AppSettings
    from screen_translator.core.hotkeys import GlobalHotkeyManager
    from screen_translator.ui.main_window import MainWindow
    from screen_translator.ui.theme import FONT_FAMILY
    from screen_translator.ui.components import PixelButton

    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setFont(QFont(FONT_FAMILY, 10))
    app.setQuitOnLastWindowClosed(False)
    assert abs(app.primaryScreen().devicePixelRatio() - float(args.scale)) < 0.01
    failures = []
    original_hook = sys.excepthook
    def exception_hook(kind, value, tb):
        failures.append(str(value))
        original_hook(kind, value, tb)
    sys.excepthook = exception_hook
    with tempfile.TemporaryDirectory(prefix="screen-translator-ui-") as storage, \
         patch("screen_translator.core.storage.user_data_dir", return_value=storage), \
         patch.object(AppSettings, "_import_legacy_qsettings"), \
         patch.object(GlobalHotkeyManager, "start"), \
         patch.object(GlobalHotkeyManager, "stop"), ExitStack() as cleanup:
        cleanup.callback(gc.collect)
        window = MainWindow()
        cleanup.callback(window._quit_application)
        window.show()
        QTest.qWait(150)
        if args.capture_only:
            window.source_combo.setCurrentIndex(window.source_combo.findData("en"))
            window._usage_buttons["course"].click()
            for width, height in ((1100,700),(1280,800),(1440,900),(1920,1080)):
                window.resize(width,height)
                for index,name in ((0,"screen"),(5,"subtitles")):
                    window._select_page(index)
                    QTest.qWait(180)
                    window.grab().save(str(output/f"{name}-{width}x{height}-{args.scale}.png"))
            window.resize(1280,800)
            for index,name in enumerate(("screen", "audio", "history", "languages", "vocabulary", "subtitles", "performance", "data", "hotkeys", "settings")):
                window._select_page(index)
                QTest.qWait(100)
                window.grab().save(str(output/f"{name}-1280x800-{args.scale}.png"))
            window.mini_toolbar.show()
            window.word_popup.show_result({"term":"volatile", "meaning":"波动的；不稳定的", "source_lang":"en", "target_lang":"zh", "context":"The market remains volatile."})
            QTest.qWait(100)
            window.mini_toolbar.grab().save(str(output/f"mini-{args.scale}.png"))
            window.word_popup.grab().save(str(output/f"word-{args.scale}.png"))
            assert not failures,failures
            print("Native visual captures saved:",output)
            return 0
        window._show_main_window()
        if args.native:
            assert QTest.qWaitForWindowActive(window, 3000)
        window.source_combo.showPopup()
        QTest.qWait(300)
        assert window.source_combo.view().isVisible(), "Language menu did not open"
        window.source_combo.hidePopup()
        assert not hasattr(window, "_design_canvas")
        assert window.stack.count() == 10
        assert window.minimumSize() == QSize(1100, 700)
        assert not window._overlay.isVisible()
        assert not window.mini_toolbar.isVisible()
        assert not window.word_popup.isVisible()
        shell = window.centralWidget()
        floating = (window._overlay, window.mini_toolbar, window.word_popup)
        for item in floating:
            assert item.isWindow() and not shell.isAncestorOf(item)
        for index, button in enumerate(window._nav_buttons):
            button.click()
            app.processEvents()
            assert window.stack.currentIndex() == index
            assert window.centralWidget() is shell
            assert all(window.stack.widget(i).isVisible() == (i == index) for i in range(10))
        window._select_page(0)
        scale = os.environ.get("QT_SCALE_FACTOR", "1")
        for width, height in ((1100, 700), (1280, 800), (1440, 900), (1920, 1080)):
            window.resize(width, height)
            QTest.qWait(100)
            assert window.size() == QSize(width, height), (window.size(), width, height)
            page_area = window.stack.currentWidget()
            assert page_area.horizontalScrollBar().maximum() == 0, "Screen page overflows horizontally"
            assert window.title_bar.geometry().bottom() < window.sidebar.geometry().top()
            assert window.sidebar.geometry().right() < window.stack.geometry().left()
            for button in window.screen_page.findChildren(PixelButton):
                if button.isVisible():
                    assert button.width() >= button.minimumSizeHint().width(), button.text()
            for combo in (window.source_combo, window.target_combo):
                for index in range(combo.count()):
                    assert combo.fontMetrics().horizontalAdvance(combo.itemText(index)) <= combo.width() - 86
            assert window.grab().save(str(output / f"main-{width}x{height}-{scale}.png"))
        window.resize(1280, 800)
        window.source_combo.setCurrentIndex(window.source_combo.findData("en"))
        window.target_combo.setCurrentIndex(window.target_combo.findData("zh"))
        window.screen_swap_button.click()
        assert window.source_combo.currentData() == "zh" and window.target_combo.currentData() == "en"
        window.screen_swap_button.click()
        for key, button in window._usage_buttons.items():
            button.click()
            assert window.usage_mode_combo.currentData() == key
            assert sum(item.isChecked() for item in window._usage_buttons.values()) == 1
        window._usage_buttons["general"].click()
        window.screen_mode_combo.setCurrentIndex(window.screen_mode_combo.findData("region"))
        assert not window.window_combo.isEnabled()
        # A real start click opens the selector. Cancelling exercises lifecycle
        # without running a model, changing the download policy or capturing data.
        window.live_button.click()
        assert window._selector.isVisible() and window._live_mode
        QTest.keyClick(window._selector, Qt.Key.Key_Escape)
        assert not window._live_mode and window.isVisible()
        window._toggle_mini_toolbar()
        assert window.mini_toolbar.isVisible()
        window._select_page(1)
        assert window.mini_toolbar.isVisible()
        window._toggle_mini_toolbar()
        # Feed a fixture through the actual result adapter, history store and
        # overlay; inference itself is deliberately outside this smoke test.
        window._selected_rect = None
        window._on_screen_finished({"source_text": "The market remains volatile.", "translated_text": "市场仍然波动较大。", "source_lang": "en", "target_lang": "zh", "ocr_backend": "smoke fixture"})
        assert window.source_edit.toPlainText() == "The market remains volatile."
        assert window.history_table.rowCount() == 1
        window.word_popup.show_loading("volatile", "en", "zh", window.source_edit.toPlainText())
        window.word_popup.show_result({"term": "volatile", "meaning": "波动的", "source_lang": "en", "target_lang": "zh", "context": "The market remains volatile."})
        window.word_popup.add_btn.click()
        assert window.vocab_table.rowCount() == 1
        window.word_popup.hide()
        window._show_main_window()
        if args.native:
            assert QTest.qWaitForWindowActive(window, 3000)
        window._overlay.canvas.push("测试字幕", "test")
        window._clear_overlay_and_text()
        assert not window._overlay.canvas._entries and not window.source_edit.toPlainText()
        window._select_page(0)
        window.source_settings_button.click()
        window.screen_results_dialog.show()
        QTest.qWait(50)
        assert window.ocr_backend_combo.isVisible() and window.source_edit.isVisible()
        assert window.screen_options_dialog.isWindow() and window.screen_results_dialog.isWindow()
        window.screen_options_dialog.hide()
        window.screen_results_dialog.hide()
        window._show_main_window()
        if args.native:
            assert QTest.qWaitForWindowActive(window, 3000)
        window.stack.currentWidget().ensureWidgetVisible(window.source_combo)
        QTest.qWait(100)
        QTest.mouseClick(window.source_combo, Qt.MouseButton.LeftButton, pos=QPoint(window.source_combo.width() - 18, window.source_combo.height() // 2))
        QTest.qWait(300)
        assert window.source_combo.view().isVisible(), "Language menu arrow did not open"
        window.source_combo.hidePopup()
        window._select_page(5)
        window.opacity_slider.setValue(0)
        window.font_size_spin.setValue(23)
        window.outline_width_spin.setValue(1)
        window.subtitle_display_combo.setCurrentIndex(window.subtitle_display_combo.findData("bilingual"))
        assert window._subtitle_preview.display_mode == "bilingual"
        assert window._overlay.canvas.display_mode == "bilingual"
        assert window._subtitle_preview.background_opacity == 0
        assert window._overlay.canvas.background_opacity == 0
        assert window._subtitle_preview.translation_font_size == 23
        assert window._subtitle_preview.outline_width == 1
        assert len(window._subtitle_preview._entries) == 1
        for width,height in ((1100,700),(1280,800),(1440,900),(1920,1080)):
            window.resize(width,height)
            QTest.qWait(100)
            assert window.stack.currentWidget().horizontalScrollBar().maximum() == 0, "Subtitle settings overflow horizontally"
            assert window.grab().save(str(output/f"subtitles-{width}x{height}-{scale}.png"))
        window._select_page(7)
        window._save_settings()
        saved = AppSettings()
        assert saved.value("ui_last_page") == 7
        assert saved.value("source_language") == "en"
        window.auto_mini_check.setChecked(False)
        window.bind_window_check.setChecked(False)
        window.tray_close_check.setChecked(False)
        window._save_settings()
        assert not failures, failures
        window._force_quit = True
        window.close()
        app.processEvents()
        restored = MainWindow()
        cleanup.callback(restored._quit_application)
        assert restored.stack.currentIndex() == 7
        assert restored.source_combo.currentData() == "en"
        assert not restored.auto_mini_check.isChecked()
        assert not restored.bind_window_check.isChecked()
        assert not restored.tray_close_check.isChecked()
        restored._force_quit = True
        restored.close()
        gc.collect()
    print(f"UI smoke PASS: scale={scale}, backend={app.platformName()}, DPR={app.primaryScreen().devicePixelRatio()}, 10 pages, 4 sizes, actions/results/state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
