import platform
import subprocess


def is_macos() -> bool:
    return platform.system() == "Darwin"


def is_windows() -> bool:
    return platform.system() == "Windows"


def open_macos_screen_recording_settings() -> None:
    if not is_macos():
        return
    subprocess.Popen(
        [
            "open",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
        ]
    )


def open_macos_microphone_settings() -> None:
    if not is_macos():
        return
    subprocess.Popen(
        [
            "open",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
        ]
    )
