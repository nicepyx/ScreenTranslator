from __future__ import annotations

import argparse
import ast
import py_compile
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check_python_syntax() -> None:
    failures: list[str] = []
    for path in (ROOT / "screen_translator").rglob("*.py"):
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            failures.append(f"{path.relative_to(ROOT)}: {exc}")
    if failures:
        raise RuntimeError("Python syntax check failed:\n" + "\n".join(failures))


def check_main_window_structure() -> None:
    path = ROOT / "screen_translator" / "ui" / "main_window.py"
    tree = ast.parse(path.read_text("utf-8"), filename=str(path))
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MainWindow"), None)
    if cls is None:
        raise RuntimeError("MainWindow class not found")

    methods = [n.name for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    duplicates = sorted({name for name in methods if methods.count(name) > 1})
    if duplicates:
        raise RuntimeError("Duplicate MainWindow methods: " + ", ".join(duplicates))

    required = {"_build_ui", "_wrap_page", "_select_page"}
    if required - set(methods):
        raise RuntimeError("Missing shell entry points")
    calls = [n for n in ast.walk(cls) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "_build_ui"]
    if len(calls) != 1:
        raise RuntimeError("MainWindow must build its UI exactly once")
    if any(isinstance(base, ast.Name) and "Legacy" in base.id for base in cls.bases):
        raise RuntimeError("MainWindow must not inherit a legacy window")
    for file in (path, path.parent / "pages/screen_page.py", path.parent / "components/shell.py"):
        source = file.read_text("utf-8")
        if "setGeometry(" in source or "DesignCanvas" in source:
            raise RuntimeError(f"Absolute design-board layout found in {file.name}")
    logic = (path.parent / "window_logic.py").read_text("utf-8")
    if "def _build_" in logic:
        raise RuntimeError("Pipeline adapter must not build pages")


def check_assets() -> None:
    required = [
        "screen.png", "audio.png", "history.png", "languages.png", "performance.png",
        "settings.png", "subtitles.png", "app_logo.png",
    ]
    pixel = ROOT / "screen_translator" / "resources" / "pixel"
    ui = ROOT / "screen_translator" / "resources" / "pixel_ui"
    required_ui = [
        "arrow_down.png", "checkbox_off.png", "checkbox_on.png", "slider_handle.png",
        "play.png", "pause.png", "clear.png", "pin.png", "copy.png", "speaker.png",
        "star.png", "close.png", "data.png", "hotkeys.png", "tray.png", "vocabulary.png",
    ]
    missing = [str(pixel / name) for name in required if not (pixel / name).exists()]
    missing += [str(ui / name) for name in required_ui if not (ui / name).exists()]

    plates = ROOT / "screen_translator/resources/ui_v2"
    required_plates = ["frame_window", "titlebar", "card", "button_primary", "button_secondary", "button_danger", "combo", "nav_normal", "nav_selected"]
    required_plates += ["scene_" + name for name in ("general", "game", "course", "video", "meeting", "custom")]
    missing += [str(plates / f"{name}.png") for name in required_plates if not (plates / f"{name}.png").exists()]
    decor = ROOT / "screen_translator/resources/pixel_v092/decor_cat.png"
    if not decor.exists():
        missing.append(str(decor))
    spec = (ROOT / "ScreenTranslator.spec").read_text("utf-8")
    if '"screen_translator/resources/ui_v2"' not in spec:
        raise RuntimeError("PyInstaller spec does not include UI plates")
    target = ROOT / "screen_translator/resources/ui_target"
    required_target = ["frame_window", "titlebar", "card", "status_card", "combo", "nav_selected",
                       "scene", "scene_selected", "app_logo", "hero_screen", "landscape", "sidebar_cat",
                       "checkbox_on", "checkbox_off", "slider_handle", "arrow_down", "arrow_up",
                       "flag_en", "flag_zh", "source", "scene_label", "window", "swap", "status_ready"]
    required_target += ["scene_" + name for name in ("general", "game", "course", "video", "meeting", "custom")]
    required_target += ["button_" + kind + state for kind in ("primary", "secondary") for state in ("", "_hover", "_pressed")]
    missing += [str(target / f"{name}.png") for name in required_target if not (target / f"{name}.png").exists()]
    if '"screen_translator/resources/ui_target"' not in spec:
        raise RuntimeError("PyInstaller spec does not include target UI assets")
    if missing:
        raise RuntimeError("Missing UI assets:\n" + "\n".join(missing))


def check_ui_runtime_imports() -> None:
    # This deliberately evaluates the QSS f-string. It catches runtime-only mistakes
    # such as an unescaped CSS brace becoming a Python expression.
    from screen_translator.ui.pixel_theme import pixel_light_qss
    qss = pixel_light_qss()
    for asset in re.findall(r'url\("([^\"]+)"\)', qss):
        if not Path(asset).is_file():
            raise RuntimeError(f"Missing stylesheet image: {asset}")
    if "QPushButton#PrimaryButton" not in qss or "QLabel#ShortcutChip" not in qss:
        raise RuntimeError("Pixel QSS is incomplete")

    from screen_translator.ui.main_window import MainWindow
    for name in ("_select_page", "_wrap_page", "_initialize_logic", "_restore_runtime"):
        if not hasattr(MainWindow, name):
            raise RuntimeError(f"MainWindow missing runtime method: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--static-only", action="store_true")
    args = parser.parse_args()
    try:
        check_python_syntax()
        check_main_window_structure()
        check_assets()
        if not args.static_only:
            check_ui_runtime_imports()
    except Exception as exc:
        print("[PRECHECK FAILED]")
        print(exc)
        return 1
    print("Screen Translator preflight: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
