"""Logical-pixel tokens shared by the light pixel UI."""
import sys

SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
PAGE_PADDING = 20
SIDEBAR_WIDTH = 224
TITLEBAR_HEIGHT = 48
BUTTON_HEIGHT = 48
INPUT_HEIGHT = 46
ICON_SM = 20
ICON_MD = 28
ICON_LG = 48
COLOR_BACKGROUND = "#D9EFF8"
COLOR_PANEL = "#FFFCF5"
COLOR_PRIMARY = "#42AEEB"
COLOR_OUTLINE = "#123D68"
COLOR_MUTED = "#6A8195"
FONT_FAMILY = "Microsoft YaHei UI" if sys.platform == "win32" else ("PingFang SC" if sys.platform == "darwin" else "Noto Sans CJK SC")
