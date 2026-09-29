"""Extract reusable, text-free art from the user-approved main window reference.

The reference itself is never displayed by the application. Frames use small
nine-slice plates; labels are always live Qt text. Re-run to reproduce assets.
"""
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "screen_translator/resources/ui_target"
REF = ROOT / "design/reference/main-target.png"
CREAM = (255, 249, 239, 255)


def plate(image, box, name, edge=8, sample=None, fill=None):
    """Keep reference corners/edges, replace the complete text-bearing centre."""
    src = image.crop(box)
    w, h = src.size
    n = edge
    out = Image.new("RGBA", (n * 2 + 8, n * 2 + 8), fill or src.getpixel((n + 2, h // 2)))
    sample = sample or (w // 2, h // 2)
    for x, tx in ((0, 0), (w - n, n + 8)):
        for y, ty in ((0, 0), (h - n, n + 8)):
            out.paste(src.crop((x, y, x+n, y+n)), (tx, ty))
    for y, ty in ((0, 0), (h-n, n+8)):
        out.paste(src.crop((sample[0], y, sample[0]+1, y+n)).resize((8,n), Image.Resampling.NEAREST), (n,ty))
    for x, tx in ((0, 0), (w-n, n+8)):
        out.paste(src.crop((x,sample[1],x+n,sample[1]+1)).resize((n,8), Image.Resampling.NEAREST), (tx,n))
    if name == "button_primary":
        gradient = src.crop((48,n,49,h-n)).resize((8,8),Image.Resampling.NEAREST)
        out.paste(gradient,(n,n))
    out.save(OUT / f"{name}.png")


def cutout(image, box, name, cream=True):
    im = image.crop(box).convert("RGBA")
    if cream:
        pixels = im.load()
        queue = deque([(x,y) for x in range(im.width) for y in (0,im.height-1)] + [(x,y) for y in range(im.height) for x in (0,im.width-1)])
        seen = set()
        while queue:
            x,y=queue.popleft()
            if (x,y) in seen or not (0<=x<im.width and 0<=y<im.height): continue
            seen.add((x,y))
            r,g,b,a=pixels[x,y]
            if r>200 and g>190 and b>165:
                pixels[x,y]=(r,g,b,0)
                queue.extend(((x-1,y),(x+1,y),(x,y-1),(x,y+1)))
        bounds=im.getbbox()
        if bounds: im=im.crop(bounds)
    im.save(OUT/f"{name}.png")


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    im=Image.open(REF).convert("RGBA")
    plate(im,(0,0,936,621),'frame_window',16, (610,360))
    plate(im,(224,146,897,216),'card',10,(30,35))
    plate(im,(224,499,897,581),'status_card',10,(45,35))
    plate(im,(495,421,613,476),'button_secondary',10,(20,25))
    plate(im,(224,416,485,479),'button_primary',16,(48,28), (67,161,221,255))
    plate(im,(336,160,531,201),'combo',7,(70,10))
    plate(im,(19,58,191,103),'nav_selected',6,(100,30),(103,192,232,255))
    plate(im,(368,318,448,389),'scene',8,(25,10))
    plate(im,(542,318,621,389),'scene_selected',8,(25,10),(104,197,235,255))
    strip=im.crop((620,7,621,46)).resize((80,39),Image.Resampling.NEAREST)
    strip.save(OUT/'titlebar.png')
    for name,box in {
        'app_logo':(23,12,57,42), 'screen':(34,68,67,98), 'audio':(37,110,66,143),
        'history':(36,154,67,189), 'languages':(34,199,68,234), 'vocabulary':(32,245,68,278),
        'subtitles':(34,309,69,338), 'performance':(33,350,68,381), 'data':(34,395,68,423),
        'hotkeys':(33,439,69,469), 'settings':(35,482,69,515),
        'hero_screen':(225,75,275,128), 'source':(238,247,275,285), 'scene_label':(239,336,275,372),
        'scene_general':(394,328,421,354), 'scene_game':(479,328,511,354),
        'scene_course':(566,328,599,354), 'scene_video':(653,328,688,354),
        'scene_meeting':(742,328,775,354), 'scene_custom':(830,327,863,355),
        'play':(284,430,315,463), 'pause':(517,433,539,460), 'clear':(667,431,691,459),
        'pin':(800,432,824,457), 'status_ready':(238,511,264,538),
        'flag_en':(348,168,382,193), 'flag_zh':(678,168,712,193),
        'swap':(547,169,574,194), 'arrow_down':(506,174,522,189),
        'window':(378,243,449,292),
    }.items(): cutout(im,box,name)
    cutout(im,(629,63,913,137),'landscape',False)
    cutout(im,(19,518,191,608),'sidebar_cat',False)
    # Stateful plates keep the same geometry, changing only their palette.
    for name in ('button_secondary','button_primary','combo','scene'):
        base=Image.open(OUT/f'{name}.png')
        ImageEnhance.Brightness(base).enhance(1.06).save(OUT/f'{name}_hover.png')
        ImageEnhance.Brightness(base).enhance(.93).save(OUT/f'{name}_pressed.png')
    base=Image.open(OUT/'button_secondary.png').convert('RGBA')
    for y in range(10,base.height-10):
        for x in range(10,base.width-10): base.putpixel((x,y),(242,95,84,255))
    base.save(OUT/'button_danger.png')
    board=Image.open(ROOT/'design/reference/modules-target.png').convert('RGBA')
    for name,box in {'checkbox_on':(1281,977,1304,1001), 'checkbox_off':(1393,977,1417,1001), 'slider_handle':(1357,912,1377,935)}.items():
        piece=board.crop(box)
        for corner in ((0,0),(piece.width-1,0),(0,piece.height-1),(piece.width-1,piece.height-1)):
            ImageDraw.floodfill(piece,corner,(0,0,0,0),thresh=45)
        piece.save(OUT/f'{name}.png')
    Image.open(OUT/'arrow_down.png').transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(OUT/'arrow_up.png')
    print(f'Extracted {len(list(OUT.glob("*.png")))} reference assets')


if __name__=='__main__': main()
