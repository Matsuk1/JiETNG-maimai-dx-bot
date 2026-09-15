import os
import re

from PIL import Image, ImageDraw

from modules.image_manager import (
    compose_generated_images,
    draw_aligned_colon_text,
    font_large,
    font_level_badge,
    font_song_info,
    font_song_title,
    resize_by_width,
    round_corner,
    truncate_text,
)
from modules.config_loader import PLATES_DIR, VERSIONS_DIR
from modules.i18n import image_language, language_catalog, select_text
from modules.record_generator import _draw_level_label, _get_difficulty_color, create_thumbnail_in_line, generate_cover


def _song_text(key, language):
    return select_text(language_catalog(f"images.song.{key}"), language=language)


def _draw_rounded_panel(base_img, box, radius=22, fill=(255, 255, 255, 255), outline=(180, 180, 180, 255), width=4):
    scale = 4
    x1, y1, x2, y2 = box
    panel_size = ((x2 - x1) * scale, (y2 - y1) * scale)
    panel = Image.new("RGBA", panel_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle(
        (0, 0, panel_size[0] - scale, panel_size[1] - scale),
        radius=radius * scale,
        fill=fill,
        outline=outline,
        width=width * scale,
    )
    panel = panel.resize((x2 - x1, y2 - y1), Image.Resampling.LANCZOS)
    base_img.alpha_composite(panel, (x1, y1))


def song_info_generate(
    song_json,
    played_data=(),
    timezone_offset=9,
    ver="jp",
    bg_filter=None,
):
    language = image_language(ver)
    img1 = resize_by_width(_render_basic_info_image(song_json, language), 900)
    if played_data:
        img2 = resize_by_width(_makeup_played_data(played_data), 780)
    else:
        img2 = resize_by_width(_generate_song_table_image(song_json, language=language), 1200)
    return compose_generated_images(
        [img1, img2],
        timezone_offset=timezone_offset,
        bg_filter=bg_filter,
    )

def _render_basic_info_image(song_json, language="en"):
    from modules.html_renderer import image_uri, render_template
    with generate_cover(song_json.get("cover_url"), song_json.get("type"),
                        cover_name=song_json.get("cover_name")) as cover:
        cover_src = image_uri(cover)
    info = [(_song_text(key, language), song_json.get(key, default))
            for key, default in (("artist", "UNKNOWN"), ("category", "UNKNOWN"),
                                 ("bpm", "-"), ("version", "UNKNOWN"))]
    return render_template("song.html", 1000, 265, mode="basic", cover=cover_src,
                           title=song_json.get("title", "UNKNOWN"), info=info)


def _generate_song_table_image(song_json, scale_width=1.5, scale_height=2.0, language="en"):
    from modules.html_renderer import render_template
    header_keys = ("chart_type", "level", "designer", "total", "tap", "hold",
                   "slide", "touch", "break", "jp", "intl", "usa")
    widths = [int(w * scale_width) for w in (160, 90, 300, 90, 80, 80, 90, 90, 95, 70, 70, 70)]
    rows = []
    for sheet in song_json["sheets"]:
        notes, regions = sheet.get("noteCounts", {}), sheet.get("regions", {})
        values = [sheet["difficulty"].capitalize(), f"{sheet['internalLevelValue']:.1f}",
                  sheet.get("noteDesigner") or "-"]
        values += [notes.get(key) or "-" for key in ("total", "tap", "hold", "slide", "touch", "break")]
        values += ["✓" if regions.get(key) else "✕" for key in ("jp", "intl", "usa")]
        rows.append(("rgb" + str(_get_difficulty_color(sheet.get("difficulty", ""))), values))
    # Fractional tracks include the border in the original total width.
    return render_template("song.html", sum(widths), mode="table",
                           columns=" ".join(f"{w}fr" for w in widths), row_height=int(48 * scale_height),
                           headers=[_song_text(f"headers.{key}", language) for key in header_keys], rows=rows)


def _makeup_played_data(played_data, gap=10):
    from modules.html_cards import thumbnail_html
    from modules.html_renderer import render_template
    return render_template("stack.html", 600, gap=gap,
                           items=[thumbnail_html(record, inline=True) for record in played_data])


def generate_version_list(songs_json, version_info=None, ver="jp"):
    img_width = 1820
    margin = 20
    level_width = 100
    img_size = 150
    cover_height = img_size + 30
    cover_gap = margin
    row_height = cover_height + margin
    max_per_row = 10
    version_info = version_info or {}

    entries = []
    for song in songs_json:
        master_sheet = next(
            (sheet for sheet in song.get("sheets", []) if sheet.get("difficulty") == "master"),
            None,
        )
        if master_sheet:
            entries.append({
                "img": generate_cover(
                    song.get("cover_url"),
                    song.get("type"),
                    cover_name=song.get("cover_name"),
                    difficulty="master",
                    achieved=False,
                    song_title=song.get("title", ""),
                ),
                "level": master_sheet.get("level", "-"),
                "internal_level": master_sheet.get("internalLevelValue", 0),
                "title": song.get("title", ""),
            })

    level_order = [
        "15", "14+", "14", "13+", "13", "12+", "12", "11+", "11",
        "10+", "10", "9+", "9", "8+", "8", "7+", "7", "6+", "6",
        "5+", "5", "4+", "4", "3+", "3", "2+", "2", "1+", "1",
    ]
    rows = []
    rows_num = 0
    for level in level_order:
        level_entries = [entry for entry in entries if entry["level"] == level]
        level_entries.sort(key=lambda item: (-float(item.get("internal_level") or 0), str(item.get("title", ""))))
        if level_entries:
            rows.append((level, [entry["img"] for entry in level_entries]))
            rows_num += (len(level_entries) + max_per_row - 1) // max_per_row

    title_text = version_info.get("version") or ""
    abbr = version_info.get("abbr") or ""
    kanji_match = re.search(r"（(.+?)）|\((.+?)\)", abbr)
    plate_kanji = (kanji_match.group(1) or kanji_match.group(2)) if kanji_match else None
    logo_img = None
    logo_path = os.path.join(VERSIONS_DIR, f"{title_text.lower().replace(' ', '_')}.png") if title_text else ""
    if logo_path and os.path.exists(logo_path):
        with Image.open(logo_path) as logo:
            logo_img = resize_by_width(logo.convert("RGBA"), 1340)

    plate_imgs = []
    plate_order = {"極": 0, "将": 1, "神": 2, "舞舞": 3}
    plate_files = []
    if plate_kanji and os.path.isdir(PLATES_DIR):
        for filename in os.listdir(PLATES_DIR):
            suffix = filename.removeprefix(plate_kanji).removesuffix(".webp")
            if filename.startswith(plate_kanji) and filename.endswith(".webp") and suffix in plate_order:
                plate_files.append((plate_order[suffix], filename))

    for _, filename in sorted(plate_files)[:4]:
        plate_path = os.path.join(PLATES_DIR, filename)
        with Image.open(plate_path) as plate:
            plate_imgs.append(plate.convert("RGBA"))

    draw_probe = ImageDraw.Draw(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
    title_h = logo_img.height + 28 if logo_img else (
        draw_probe.textbbox((0, 0), title_text, font=font_song_title)[3] + 24 if title_text else 0
    )
    plate_w = 811
    plate_h = 131
    plate_gap_x = 16
    plate_gap_y = 20
    shown_plate_count = min(4, len(plate_imgs))
    plate_rows = (shown_plate_count + 1) // 2
    plates_top_h = plate_rows * plate_h + max(0, plate_rows - 1) * plate_gap_y
    top_area_height = margin + title_h + plates_top_h + 56
    total_height = top_area_height + rows_num * row_height + margin
    final_img = Image.new("RGBA", (img_width, total_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(final_img)

    if logo_img:
        final_img.paste(logo_img, ((img_width - logo_img.width) // 2, margin), logo_img)
        logo_img.close()
    elif title_text:
        title_w = draw.textlength(title_text, font=font_song_title)
        draw.text(((img_width - title_w) // 2, margin), title_text, font=font_song_title, fill=(30, 30, 30))

    start_y = margin + title_h
    for idx, plate_img in enumerate(plate_imgs[:shown_plate_count]):
        row = idx // 2
        col = idx % 2
        row_count = min(2, shown_plate_count - row * 2)
        row_width = row_count * plate_w + max(0, row_count - 1) * plate_gap_x
        x = (img_width - row_width) // 2 + col * (plate_w + plate_gap_x)
        y = start_y + row * (plate_h + plate_gap_y)
        resized_plate = plate_img.resize((plate_w, plate_h), Image.Resampling.LANCZOS)
        final_img.paste(resized_plate, (x, y), resized_plate)
        plate_img.close()

    y_offset = top_area_height
    for level, img_list in rows:
        _draw_level_label(draw, level, margin, y_offset, cover_height, font_level_badge)
        x_offset = level_width + margin
        for i, img in enumerate(img_list):
            if i > 0 and i % max_per_row == 0:
                y_offset += row_height
                x_offset = level_width + margin
            final_img.paste(img, (x_offset, y_offset), img if img.mode == "RGBA" else None)
            x_offset += img_size + cover_gap
        y_offset += row_height

    for entry in entries:
        entry["img"].close()

    return final_img
