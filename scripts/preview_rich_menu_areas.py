#!/usr/bin/env python3
"""
Render colored click-area previews for rich menu images.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SETUP_SCRIPT = ROOT / "scripts" / "setup_rich_menu.py"
OUT_DIR = ROOT / "assets" / "richmenu" / "_preview"

COLORS = [
    (239, 68, 68, 92),
    (59, 130, 246, 92),
    (16, 185, 129, 92),
    (245, 158, 11, 92),
    (139, 92, 246, 92),
    (236, 72, 153, 92),
    (20, 184, 166, 92),
    (249, 115, 22, 92),
    (99, 102, 241, 92),
]


def load_setup_module():
    spec = importlib.util.spec_from_file_location("setup_rich_menu", SETUP_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_font(size: int):
    candidates = [
        ROOT / "assets" / "fonts" / "line_seed_jietng.ttf",
        Path("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def action_label(action: dict) -> str:
    action_type = action.get("type", "")
    if action_type == "richmenuswitch":
        return f"switch:{action.get('data', '')}"
    if "text" in action:
        return f"{action.get('label', '')}: {action.get('text', '')}"
    if "uri" in action:
        return f"{action.get('label', '')}: URL"
    return action.get("label") or action_type


def draw_preview(setup, lang: str, page: str) -> Path:
    source = setup.image_path(lang, page)
    payload = setup.menu_payload(lang, page)
    image = Image.open(source).convert("RGBA")

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = load_font(34)
    small_font = load_font(24)

    for idx, area in enumerate(payload["areas"]):
        bounds = area["bounds"]
        x0 = bounds["x"]
        y0 = bounds["y"]
        x1 = x0 + bounds["width"]
        y1 = y0 + bounds["height"]
        fill = COLORS[idx % len(COLORS)]
        outline = fill[:3] + (255,)
        draw.rectangle((x0, y0, x1, y1), fill=fill, outline=outline, width=8)

        label = action_label(area["action"])
        tag = f"{idx + 1}. {label}"
        text_box = draw.textbbox((0, 0), tag, font=font)
        tag_w = min(text_box[2] - text_box[0] + 20, bounds["width"])
        tag_h = text_box[3] - text_box[1] + 18
        draw.rectangle((x0, y0, x0 + tag_w, y0 + tag_h), fill=outline)
        draw.text((x0 + 10, y0 + 8), tag, fill=(255, 255, 255, 255), font=font if tag_w == text_box[2] - text_box[0] + 20 else small_font)

    result = Image.alpha_composite(image, overlay).convert("RGB")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{lang}_{page}.jpg"
    result.save(out, quality=92)
    return out


def build_contact_sheet(paths: list[tuple[str, str, Path]]) -> Path:
    thumb_w = 520
    label_h = 42
    thumbs = []
    for lang, page, path in paths:
        image = Image.open(path).convert("RGB")
        thumb_h = round(image.height * thumb_w / image.width)
        thumb = image.resize((thumb_w, thumb_h))
        thumbs.append((lang, page, thumb))

    cols = 4
    cell_h = max(thumb.height for _, _, thumb in thumbs) + label_h
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (thumb_w * cols, cell_h * rows), "white")
    draw = ImageDraw.Draw(sheet)
    font = load_font(22)

    for idx, (lang, page, thumb) in enumerate(thumbs):
        col = idx % cols
        row = idx // cols
        x = col * thumb_w
        y = row * cell_h
        draw.text((x + 12, y + 10), f"{lang}/{page}", fill=(0, 0, 0), font=font)
        sheet.paste(thumb, (x, y + label_h))

    out = OUT_DIR / "_contact_sheet.jpg"
    sheet.save(out, quality=92)
    return out


def main() -> int:
    setup = load_setup_module()
    rendered = []
    for lang, page in setup.MENU_KEYS:
        out = draw_preview(setup, lang, page)
        rendered.append((lang, page, out))
        print(out)
    contact = build_contact_sheet(rendered)
    print(contact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
