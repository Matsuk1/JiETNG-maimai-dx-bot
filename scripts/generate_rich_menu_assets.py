#!/usr/bin/env python3
"""Generate JiETNG's multilingual LINE rich-menu artwork.

The click geometry remains owned by setup_rich_menu.py. This script only draws
the corresponding visual layer, so artwork and actions cannot silently drift.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SETUP_PATH = ROOT / "scripts" / "setup_rich_menu.py"
FONT_PATH = ROOT / "assets" / "fonts" / "line_seed_jietng.ttf"

PAPER = "#F5F1EA"
SURFACE = "#FFFEFA"
INK = "#292724"
MUTED = "#7F7970"
LINE = "#D9D3CA"
BLUE = "#3C7FE8"
BLUE_SOFT = "#E9F1FF"
MINT_SOFT = "#E4F5F0"
AMBER_SOFT = "#FFF0D9"
ROSE_SOFT = "#FBE9EA"
VIOLET_SOFT = "#F0ECFA"


def load_setup():
    spec = importlib.util.spec_from_file_location("jietng_rich_menu_setup", SETUP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def rounded(draw: ImageDraw.ImageDraw, box, radius, fill, outline=LINE, width=4):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def fit_text(draw, text: str, max_width: int, initial: int, minimum: int = 34):
    size = initial
    while size > minimum:
        candidate = font(size)
        if draw.textbbox((0, 0), text, font=candidate)[2] <= max_width:
            return candidate
        size -= 2
    return font(minimum)


def line(draw, points, fill=INK, width=12, joint="curve"):
    draw.line(points, fill=fill, width=width, joint=joint)


def icon(draw: ImageDraw.ImageDraw, name: str, cx: int, cy: int, size: int, color=INK):
    """Draw compact, dependency-free line icons."""
    s = size / 2
    w = max(8, round(size * 0.075))
    left, top, right, bottom = cx - s, cy - s, cx + s, cy + s

    if name in {"sync", "status"}:
        draw.arc((left, top, right, bottom), 35, 205, fill=color, width=w)
        draw.arc((left, top, right, bottom), 215, 385, fill=color, width=w)
        line(draw, [(right - size * .1, top + size * .08), (right, top + size * .28), (right - size * .24, top + size * .3)], color, w)
        line(draw, [(left + size * .1, bottom - size * .08), (left, bottom - size * .28), (left + size * .24, bottom - size * .3)], color, w)
    elif name in {"b50", "b40", "ap50", "r50"}:
        draw.ellipse((left + size*.18, top, right - size*.18, bottom - size*.28), outline=color, width=w)
        line(draw, [(cx, top + size*.18), (cx + size*.07, top + size*.34), (cx + size*.24, top + size*.36), (cx + size*.11, top + size*.47), (cx + size*.15, top + size*.64), (cx, top + size*.54), (cx - size*.15, top + size*.64), (cx - size*.11, top + size*.47), (cx - size*.24, top + size*.36), (cx - size*.07, top + size*.34), (cx, top + size*.18)], color, max(5, w-3))
        line(draw, [(cx-size*.2, bottom-size*.3), (cx-size*.3, bottom), (cx, bottom-size*.16), (cx+size*.3, bottom), (cx+size*.2, bottom-size*.3)], color, w)
    elif name == "ranking":
        for index, height in enumerate((.36, .62, .88)):
            x0 = left + size * (.08 + index * .31)
            draw.rounded_rectangle((x0, bottom-size*height, x0+size*.22, bottom), radius=6, outline=color, width=w)
        line(draw, [(left, bottom), (right, bottom)], color, w)
        draw.regular_polygon((cx, top + size*.1, size*.11), 5, rotation=-90, outline=color)
    elif name == "friends":
        draw.ellipse((cx-size*.16, top, cx+size*.16, top+size*.32), outline=color, width=w)
        draw.ellipse((left, top+size*.13, left+size*.29, top+size*.42), outline=color, width=w)
        draw.ellipse((right-size*.29, top+size*.13, right, top+size*.42), outline=color, width=w)
        draw.arc((cx-size*.3, top+size*.27, cx+size*.3, bottom), 180, 360, fill=color, width=w)
        draw.arc((left-size*.02, top+size*.38, cx, bottom), 185, 330, fill=color, width=w)
        draw.arc((cx, top+size*.38, right+size*.02, bottom), 210, 355, fill=color, width=w)
    elif name == "random":
        rounded(draw, (left, top, right, bottom), size*.16, None, color, w)
        for dx, dy in ((-.22,-.22),(.22,-.22),(0,0),(-.22,.22),(.22,.22)):
            draw.ellipse((cx+size*dx-w, cy+size*dy-w, cx+size*dx+w, cy+size*dy+w), fill=color)
    elif name in {"docs", "export"}:
        line(draw, [(left+size*.12, top), (right-size*.22, top), (right, top+size*.22), (right, bottom), (left+size*.12, bottom), (left+size*.12, top)], color, w)
        line(draw, [(right-size*.22, top), (right-size*.22, top+size*.22), (right, top+size*.22)], color, w)
        if name == "docs":
            for offset in (.42, .6, .78):
                line(draw, [(left+size*.28, top+size*offset), (right-size*.2, top+size*offset)], color, max(5, w-3))
        else:
            line(draw, [(cx-size*.14, cy+size*.08), (right+size*.14, cy+size*.08)], color, w)
            line(draw, [(right-size*.04, cy-size*.08), (right+size*.14, cy+size*.08), (right-size*.04, cy+size*.24)], color, w)
    elif name in {"profile", "bind"}:
        draw.ellipse((cx-size*.2, top, cx+size*.2, top+size*.4), outline=color, width=w)
        draw.arc((left+size*.08, top+size*.32, right-size*.08, bottom), 180, 360, fill=color, width=w)
    elif name == "settings":
        draw.ellipse((cx-size*.18, cy-size*.18, cx+size*.18, cy+size*.18), outline=color, width=w)
        draw.ellipse((cx-size*.4, cy-size*.4, cx+size*.4, cy+size*.4), outline=color, width=w)
        for angle in range(0, 360, 45):
            a = math.radians(angle)
            line(draw, [(cx+math.cos(a)*size*.4, cy+math.sin(a)*size*.4), (cx+math.cos(a)*size*.52, cy+math.sin(a)*size*.52)], color, w)
    elif name in {"rebind", "unbind"}:
        draw.arc((left, top+size*.02, cx+size*.1, bottom-size*.02), 45, 315, fill=color, width=w)
        draw.arc((cx-size*.1, top+size*.02, right, bottom-size*.02), 225, 495, fill=color, width=w)
        if name == "unbind":
            line(draw, [(left, bottom), (right, top)], color, w)
    else:  # help
        rounded(draw, (left, top, right, bottom), size*.14, None, color, w)
        line(draw, [(cx-size*.25, cy-size*.18), (cx+size*.25, cy-size*.18)], color, w)
        line(draw, [(cx-size*.25, cy), (cx+size*.12, cy)], color, w)
        line(draw, [(cx-size*.25, cy+size*.18), (cx+size*.25, cy+size*.18)], color, w)


PAGE_ITEMS = {
    "start": (("bind", "bind"), ("help", "help")),
    "main": (("update", "sync"), ("b50", "b50"), ("ap50", "ap50"), ("b40", "b40"), ("r50", "r50")),
    "extra": (("ranking", "ranking"), ("friends", "friends"), ("random", "random"), ("docs", "docs")),
    "profile": (("profile", "profile"), ("status", "status"), ("export", "export"), ("settings", "settings"), ("rebind", "rebind"), ("unbind", "unbind")),
}


def item_label(labels: dict, key: str) -> str:
    return labels.get(key, key.upper())


def draw_tab(draw, box, label, selected, icon_name):
    x0, y0, x1, y1 = box
    fill = BLUE_SOFT if selected else SURFACE
    outline = BLUE if selected else LINE
    rounded(draw, box, 34, fill, outline, 5)
    icon(draw, icon_name, x0 + 66, (y0+y1)//2, 50, BLUE if selected else MUTED)
    label_font = fit_text(draw, label, x1-x0-155, 43)
    draw.text((x0+112, (y0+y1)//2), label, fill=BLUE if selected else MUTED, font=label_font, anchor="lm")


def draw_card(draw, box, label, icon_name, index, primary=False):
    x0, y0, x1, y1 = box
    palette = (BLUE_SOFT, MINT_SOFT, AMBER_SOFT, ROSE_SOFT, VIOLET_SOFT)
    accent = (BLUE, "#178D78", "#B97818", "#C6535A", "#7064C8")[index % 5]
    fill = palette[index % 5] if primary else SURFACE
    rounded(draw, box, 42, fill, BLUE if primary else LINE, 6 if primary else 4)
    card_w, card_h = x1-x0, y1-y0
    icon_size = min(150, int(min(card_w, card_h) * .25))
    icon_y = int(y0 + card_h * .42)
    draw.ellipse((x0+card_w/2-icon_size*.58, icon_y-icon_size*.58, x0+card_w/2+icon_size*.58, icon_y+icon_size*.58), fill=palette[index % 5])
    icon(draw, icon_name, int(x0+card_w/2), icon_y, icon_size, accent)
    label_font = fit_text(draw, label, card_w-80, 62 if card_w > 800 else 52)
    draw.text(((x0+x1)//2, int(y0+card_h*.72)), label, fill=INK, font=label_font, anchor="mm")


def generate(setup, lang: str, page: str):
    width, height = setup.PAGE_SIZE[page]
    image = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(image)
    labels = setup.LABELS[lang]
    draw.text((125, 56), "JiETNG", fill=INK, font=font(36), anchor="lm")
    draw.text((2379, 56), "MAIMAI DX", fill=MUTED, font=font(25), anchor="rm")

    if page in setup.SWITCH_PAGES:
        for box, tab, icon_name in zip(setup.SWITCH_BOXES, setup.SWITCH_PAGES, ("sync", "help", "profile")):
            draw_tab(draw, box, labels[f"tab_{tab}"], tab == page, icon_name)

    for index, ((key, icon_name), box) in enumerate(zip(PAGE_ITEMS[page], setup.CONTENT_BOXES[page])):
        draw_card(draw, box, item_label(labels, key), icon_name, index, primary=(index == 0))

    target = setup.image_path(lang, page)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, optimize=True)
    return target


def main() -> int:
    setup = load_setup()
    for lang, page in setup.MENU_KEYS:
        print(generate(setup, lang, page))
    setup.ensure_images()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
