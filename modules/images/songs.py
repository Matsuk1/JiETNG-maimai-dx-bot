from modules.images.skins import skinnable
import os
import re

from modules.images.composition import compose_generated_images, resize_by_width
from modules.config_loader import PLATES_DIR, VERSIONS_DIR
from modules.i18n import image_language, language_catalog, select_text
from modules.images.records import difficulty_color, generate_cover


def _song_text(key, language):
    return select_text(language_catalog(f"images.song.{key}"), language=language)


@skinnable
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
    from modules.images.renderer import image_uri, render_template
    with generate_cover(song_json.get("cover_url"), song_json.get("type"),
                        cover_name=song_json.get("cover_name")) as cover:
        cover_src = image_uri(cover)
    info = [(_song_text(key, language), song_json.get(key, default))
            for key, default in (("artist", "UNKNOWN"), ("category", "UNKNOWN"),
                                 ("bpm", "-"), ("version", "UNKNOWN"))]
    return render_template("song.html", 1000, 265, mode="basic", cover=cover_src,
                           title=song_json.get("title", "UNKNOWN"), info=info)


def _generate_song_table_image(song_json, scale_width=1.5, scale_height=2.0, language="en"):
    from modules.images.renderer import render_template
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
        rows.append((difficulty_color(sheet.get("difficulty", "")), values))
    # Fractional tracks include the border in the original total width.
    return render_template("song.html", sum(widths), mode="table",
                           columns=" ".join(f"{w}fr" for w in widths), row_height=int(48 * scale_height),
                           headers=[_song_text(f"headers.{key}", language) for key in header_keys], rows=rows)


def _makeup_played_data(played_data, gap=10):
    from modules.images.records import thumbnail_html
    from modules.images.renderer import render_template
    return render_template("stack.html", 600, gap=gap,
                           items=[thumbnail_html(record, inline=True) for record in played_data])


@skinnable
def generate_version_list(songs_json, version_info=None, ver="jp"):
    from modules.images.records import cover_html
    from modules.images.renderer import file_uri, render_template
    from modules.images.records import _level_group_sort_key
    groups = {}
    for song in songs_json:
        master = next((sheet for sheet in song.get("sheets", []) if sheet.get("difficulty") == "master"), None)
        if master:
            groups.setdefault(master.get("level", "-"), []).append((master, song))
    rows = []
    levels = sorted(groups, key=_level_group_sort_key, reverse=True)
    for level in levels:
        selected = sorted(groups[level],
                          key=lambda pair: (-float(pair[0].get("internalLevelValue") or 0), str(pair[1].get("title", ""))))
        rows.append((level, [cover_html(song.get("cover_url"), song.get("type"),
                                       cover_name=song.get("cover_name"), difficulty="master",
                                       achieved=False, song_title=song.get("title", "")) for _, song in selected]))
    info = version_info or {}
    title = info.get("version") or ""
    match = re.search(r"（(.+?)）|\((.+?)\)", info.get("abbr") or "")
    kanji = (match.group(1) or match.group(2)) if match else None
    plate_order = {"極": 0, "将": 1, "神": 2, "舞舞": 3}
    plates = []
    if kanji and os.path.isdir(PLATES_DIR):
        files = []
        for filename in os.listdir(PLATES_DIR):
            suffix = filename.removeprefix(kanji).removesuffix(".webp")
            if filename.startswith(kanji) and filename.endswith(".webp") and suffix in plate_order:
                files.append((plate_order[suffix], filename))
        plates = [file_uri(os.path.join(PLATES_DIR, name)) for _, name in sorted(files)[:4]]
    return render_template("progress.html", 1820, mode="version", title=title,
                           title_src=file_uri(os.path.join(VERSIONS_DIR, f"{title.lower().replace(' ', '_')}.png")) if title else "",
                           plates=plates, margin=20, max_per_row=10, rows=rows, markup=True)
