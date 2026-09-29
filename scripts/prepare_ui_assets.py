"""Derive text-free nine-slice plates and isolated scene icons from existing art.

Run from any directory. All sampling/cropping is nearest-neighbour; no new artwork
or screenshots are used as widget backgrounds. See resources/ui_v2/README.md.
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / "screen_translator/resources"
SOURCE = ROOT / "pixel_v092"
OUTPUT = ROOT / "ui_v2"


def plate(source: str, target: str, size: tuple[int, int], inset: int) -> None:
    image = Image.open(SOURCE / f"{source}.png").convert("RGBA")
    image = image.resize(size, Image.Resampling.NEAREST)
    # Repeat a text-free interior column to remove placeholder glyphs while
    # preserving the original artist's vertical shading and edge pixels.
    column = image.crop((inset, inset, inset + 1, size[1] - inset))
    image.paste(column.resize((size[0] - 2 * inset, size[1] - 2 * inset), Image.Resampling.NEAREST), (inset, inset))
    image.save(OUTPUT / f"{target}.png")


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    plate("secondary_md", "frame_window", (120, 60), 10)
    plate("secondary_md", "button_secondary", (120, 60), 10)
    plate("primary_md", "button_primary", (120, 60), 10)
    plate("danger_md", "button_danger", (120, 60), 10)
    plate("input_normal", "combo", (180, 40), 6)
    plate("general_normal", "card", (90, 84), 10)
    plate("topbar_panel", "titlebar", (240, 40), 5)
    plate("nav_normal_a", "nav_normal", (160, 52), 8)
    plate("nav_selected", "nav_selected", (160, 52), 8)
    for name in ("general", "game", "course", "video", "meeting", "custom"):
        image = Image.open(SOURCE / f"{name}_normal.png").convert("RGBA")
        # The scene icon occupies the top-middle; labels remain in the source.
        icon = image.crop((55, 44, image.width - 55, 126))
        # Remove only the connected cream background, keeping white highlights.
        from PIL import ImageDraw
        ImageDraw.floodfill(icon, (0, 0), (0, 0, 0, 0), thresh=38)
        box = icon.getbbox()
        icon.crop(box).save(OUTPUT / f"scene_{name}.png")
    print(f"Prepared UI plates: {OUTPUT}")


if __name__ == "__main__":
    main()
