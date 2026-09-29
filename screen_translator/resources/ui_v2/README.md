# Text-free pixel assets

These 15 PNGs are derived from the repository's existing `pixel_v092` artwork by
`scripts/prepare_ui_assets.py`. No new generated art or design-board screenshot is
used as a live widget background.

| Output | Existing source | Processing |
| --- | --- | --- |
| frame_window, button_secondary | secondary_md | nearest-neighbour reduction; repeat an empty interior column to remove placeholder marks |
| button_primary / button_danger | primary_md / danger_md | same text-free plate extraction |
| card | general_normal | retain the outer frame, remove the icon and baked text |
| combo | input_normal | empty input frame; Qt draws its text and separate arrow |
| titlebar | topbar_panel | empty plate, with no brand or window controls baked in |
| nav_normal / nav_selected | nav_normal_a / nav_selected | remove decorative placeholder icon/text |
| scene_* | corresponding *_normal tile | crop only the icon above the original label; remove connected cream background |

`components/pixel.py` renders plates as nine slices with smooth pixmap transforms
disabled. Corners use logical pixels, independently of content width. Qt renders
all button labels, scene captions, language names and the application title.
The original PNGs remain available for provenance. The cat decoration is drawn
directly from `pixel_v092/decor_cat.png` with its aspect ratio preserved.
