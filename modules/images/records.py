"""Record, cover, progress and score image rendering."""
from modules.images.skins import skinnable
from pathlib import Path
import logging
import os
import re
from modules.score_rules import DIFFICULTY_STYLES, DIFFICULTY_LABELS, JUDGEMENT_ROWS, score_rank as canonical_rank, combo_status as canonical_combo

from modules.config_loader import (PLATES_DIR, COVERS_DIR, ICON_TYPE_DIR, ICON_BASE_DIR, ICON_SCORE_DIR,
    ICON_COMBO_DIR, ICON_SYNC_DIR, ICON_COMBO_RCD_DIR, ICON_SYNC_RCD_DIR, ICON_DX_STAR_DIR)
from modules.images import cache as image_cache
from modules.images.composition import compose_generated_images
from modules.i18n import image_language, language_catalog, select_text
from modules.maimai_manager import get_rating_image_path
from modules.record_manager import get_single_ra

logger = logging.getLogger(__name__)

def _image_text(path, language):
    return select_text(language_catalog(f"images.{path}"), language=language)
def _format_rating_value(value):
    return str(int(value)) if float(value).is_integer() else str(value)


def create_thumbnail_in_line(song, skin=None):
    from modules.images.renderer import render_html
    return render_html(thumbnail_html(song, inline=True, skin=skin), 600, 180)


def create_thumbnail(song, skin=None):
    from modules.images.renderer import render_html
    return render_html(thumbnail_html(song, skin=skin), 300, 150)


def _score_rank_name(achievement):
    rank = canonical_rank(achievement)
    return rank.replace("+", "plus") if rank else None


def _score_combo_name(achievement, judgement):
    status = canonical_combo(achievement, judgement)
    if status is None:
        return "dummy" if all(isinstance(judgement.get(row), dict) for row in JUDGEMENT_ROWS) else None
    return status.replace("+", "plus")


def _score_recognition_payload(result):
    """Normalize the internal OCR result used by LINE/FlexMsg rendering."""
    result = result or {}
    parsed = result.get("parsed") or {}
    validation = result.get("validation") or {}
    title = parsed.get("title")
    if title is None:
        title = validation.get("title")
    if validation.get("song_id") and title == "":
        title = '""'
    elif not title:
        title = "-"
    achievement = parsed.get("achievement")
    judgement = parsed.get("sub_judgement") or {}
    difficulty = validation.get("difficulty")
    difficulty_label = DIFFICULTY_LABELS.get(str(difficulty or "").lower(), str(difficulty or "").upper() or "-")
    chart_type = validation.get("type")
    return {
        "title": title,
        "difficulty": difficulty,
        "difficulty_label": difficulty_label,
        "type": chart_type,
        "cover_url": validation.get("cover_url"),
        "cover_name": validation.get("cover_name"),
        "internal_level": validation.get("internal_level"),
        "achievement": achievement,
        "judgement": judgement,
        "rank_icon": _score_rank_name(achievement),
        "combo_icon": _score_combo_name(achievement, judgement),
        "break_detail": validation.get("break_detail") or {},
        "loss_percentages": validation.get("loss_percentages") or {},
    }


DX_STAR_THRESHOLDS = ((1, 85.0), (2, 90.0), (3, 93.0), (4, 95.0), (5, 97.0))
DX_STAR_COLORS = {
    1: (64, 157, 14),
    2: (121, 193, 26),
    3: (220, 73, 22),
    4: (239, 111, 27),
    5: (237, 154, 24),
}


def _score_dx_progress(judgement):
    row_keys = ("tap", "hold", "slide", "touch", "break")
    if not all(isinstance(judgement.get(key), dict) for key in row_keys):
        return None

    counts = {
        "critical_perfect": 0,
        "perfect": 0,
        "great": 0,
        "good": 0,
        "miss": 0,
    }
    try:
        for key in row_keys:
            row = judgement[key]
            for field_name in counts:
                counts[field_name] += max(0, int(row.get(field_name, 0) or 0))
    except (TypeError, ValueError):
        return None

    note_count = sum(counts.values())
    if note_count <= 0:
        return None

    score = (
        counts["critical_perfect"] * 3
        + counts["perfect"] * 2
        + counts["great"]
    )
    maximum = note_count * 3
    percentage = score / maximum * 100
    star = sum(percentage >= threshold for _, threshold in DX_STAR_THRESHOLDS)
    return {
        "score": score,
        "maximum": maximum,
        "percentage": percentage,
        "star": star,
        "start_percentage": min(percentage, 80.0),
    }


def _dx_progress_color(percentage):
    color_stops = [
        (threshold, DX_STAR_COLORS[star])
        for star, threshold in DX_STAR_THRESHOLDS
    ]
    if percentage <= color_stops[0][0]:
        return color_stops[0][1]
    if percentage >= color_stops[-1][0]:
        return color_stops[-1][1]

    for (left_pct, left_color), (right_pct, right_color) in zip(color_stops, color_stops[1:]):
        if percentage <= right_pct:
            ratio = (percentage - left_pct) / (right_pct - left_pct)
            return tuple(
                round(left + (right - left) * ratio)
                for left, right in zip(left_color, right_color)
            )
    return color_stops[-1][1]


def _format_score_loss(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "-"
    if abs(value) < 0.000005:
        return "0.00000%"
    return f"-{value:.5f}%"


def _has_score_loss(value):
    try:
        return abs(float(value)) >= 0.000005
    except (TypeError, ValueError):
        return False


def _score_loss_rows_from_internal(judgement, loss_percentages):
    rows = []
    has_loss_percentages = bool(loss_percentages)
    for key, label in (("tap", "TAP"), ("hold", "HOLD"), ("slide", "SLIDE"), ("touch", "TOUCH")):
        row = judgement.get(key)
        if not isinstance(row, dict):
            continue
        cells = []
        total = 0.0
        count_total = 0
        for field_name in ("great", "good", "miss"):
            try:
                count = max(0, int(row.get(field_name, 0) or 0))
            except (TypeError, ValueError):
                count = 0
            loss = loss_percentages.get(f"{key}_{field_name}") if has_loss_percentages else None
            numeric_loss = float(loss) if isinstance(loss, (int, float)) else 0.0
            total += count * numeric_loss
            count_total += count
            cells.append((field_name.upper(), count, loss))
        if count_total > 0:
            rows.append((label, cells, total))
    return rows


def _score_break_rows_from_internal(judgement, break_detail):
    break_detail = break_detail or {}
    break_loss_percentages = break_detail.get("loss_percentages") or {}
    if break_detail:
        return [
            ("CRITICAL", [("CP", break_detail.get("critical_perfect", 0), break_loss_percentages.get("critical_perfect", 0))]),
            ("PERFECT", [
                ("HIGH", break_detail.get("perfect_high", 0), break_loss_percentages.get("perfect_high", 0)),
                ("LOW", break_detail.get("perfect_low", 0), break_loss_percentages.get("perfect_low", 0)),
            ]),
            ("GREAT", [
                ("HIGH", break_detail.get("great_high", 0), break_loss_percentages.get("great_high", 0)),
                ("MID", break_detail.get("great_middle", 0), break_loss_percentages.get("great_middle", 0)),
                ("LOW", break_detail.get("great_low", 0), break_loss_percentages.get("great_low", 0)),
            ]),
            ("OTHER", [
                ("GOOD", break_detail.get("good", 0), break_loss_percentages.get("good", 0)),
                ("MISS", break_detail.get("miss", 0), break_loss_percentages.get("miss", 0)),
            ]),
        ]

    break_row = judgement.get("break")
    if not isinstance(break_row, dict):
        return []
    return [
        ("CRITICAL", [("CP", break_row.get("critical_perfect", 0), None)]),
        ("PERFECT", [("TOTAL", break_row.get("perfect", 0), None)]),
        ("GREAT", [("TOTAL", break_row.get("great", 0), None)]),
        ("OTHER", [
            ("GOOD", break_row.get("good", 0), None),
            ("MISS", break_row.get("miss", 0), None),
        ]),
    ]


def _score_judgement_table(payload):
    """Keep counts and per-note/combined losses together; unknowns stay unknown."""
    fields = ('critical_perfect', 'perfect', 'great', 'good', 'miss')
    detail = payload['break_detail']
    rows = []
    for kind in ('tap', 'hold', 'slide', 'touch', 'break'):
        source = payload['judgement'].get(kind) or {}
        cells = []
        for field in fields:
            parts = [(None, field)]
            if kind == 'break' and detail:
                if field == 'perfect':
                    parts = [('P1', 'perfect_high'), ('P2', 'perfect_low')]
                elif field == 'great':
                    parts = [('G1', 'great_high'), ('G2', 'great_middle'), ('G3', 'great_low')]
            entries = []
            for label, key in parts:
                count = detail.get(key, source.get(key)) if kind == 'break' and detail else source.get(key)
                losses = detail.get('loss_percentages', {}) if kind == 'break' else payload['loss_percentages']
                loss = losses.get(key if kind == 'break' else f'{kind}_{key}')
                active = isinstance(count, (int, float)) and count > 0
                known_loss = isinstance(loss, (int, float))
                entries.append(dict(label=label, count=count if count is not None else '—',
                    zero=count == 0, unit=_format_score_loss(loss) if active and known_loss and loss else None,
                    total=_format_score_loss(count * loss) if active and known_loss and loss else None))
            cells.append(entries)
        rows.append(dict(label=kind.upper(), cells=cells))
    return rows


@skinnable
def generate_score_recognition_picture(result, ver="jp", img_width=1100, timezone_offset=9, bg_filter=None):
    from modules.images.renderer import file_uri, render_template
    payload = _score_recognition_payload(result)
    language = image_language(ver)
    texts = {key: _image_text(f"score.{key}", language)
             for key in ("analysis_title", "type", "subtitle", "judgement", "loss", "break", "empty", "common_total", "break_total", "distribution", "cell_legend", "verified", "check_required", "validation_note")}
    judgement = payload['judgement']
    fields = ('critical_perfect', 'perfect', 'great', 'good', 'miss')
    rows = [(key.upper(), [judgement[key].get(field, 0) for field in fields])
            for key in ('tap', 'hold', 'slide', 'touch', 'break') if isinstance(judgement.get(key), dict)]
    achievement = payload['achievement']
    achievement_text = f"{achievement:.4f}%" if isinstance(achievement, (int, float)) else "-"
    constant = payload['internal_level']
    constant_text = f"{constant:.1f} → {get_single_ra(constant, achievement, 'ap' in str(payload['combo_icon'] or ''))}" if isinstance(constant, (int, float)) else "-"
    rank = {'sssplus':'sssp', 'ssplus':'ssp', 'splus':'sp'}.get(payload['rank_icon'], payload['rank_icon'])
    combo = {'fc':'fc', 'fcplus':'fcp', 'ap':'ap', 'applus':'app', 'dummy':'back'}.get(payload['combo_icon'])
    icons = [(file_uri(os.path.join(directory, f"{name}.png")), width)
             for directory, name, width in ((ICON_SCORE_DIR, rank, 130), (ICON_COMBO_RCD_DIR, combo, 112)) if name]
    progress = _score_dx_progress(judgement)
    if progress:
        start = progress['start_percentage']
        span = max(.0001, 100 - start)
        progress['fill'] = min(100, max(0, (progress['percentage'] - start) / span * 100))
        tenths = progress['score'] * 1000 // progress['maximum']
        progress['display'] = f"{progress['score']} / {progress['maximum']}  {tenths // 10}.{tenths % 10}%"
        progress['markers'] = [dict(star=star, threshold=int(threshold), position=(threshold - start) / span * 100,
                                    achieved=progress['star'] >= star,
                                    icon=file_uri(os.path.join(ICON_DX_STAR_DIR, f"{star}.png")))
                               for star, threshold in DX_STAR_THRESHOLDS]
        progress['gradient'] = ','.join(f"rgb{_dx_progress_color(pct)} {(pct-start)/span*100:.4f}%"
                                         for pct in [start] + [pct for _,pct in DX_STAR_THRESHOLDS if pct > start] + [100])
    loss_rows = _score_loss_rows_from_internal(judgement, payload['loss_percentages'])
    break_rows = _score_break_rows_from_internal(judgement, payload['break_detail'])
    break_rows = [(label, cells, sum(max(0,int(count or 0)) * (loss if isinstance(loss,(int,float)) else 0)
                                   for _,count,loss in cells)) for label,cells in break_rows]
    total_break = payload['break_detail'].get('total_loss')
    if not isinstance(total_break, (int,float)):
        total_break = sum(total for _,_,total in break_rows)
    panels = []
    for title, accent, panel_rows, total_label, total in (
        (texts['loss'], '#c0392b', loss_rows, texts['common_total'], sum(total for _,_,total in loss_rows)),
        (texts['break'], '#b86e19', break_rows, texts['break_total'], total_break),
    ):
        if panel_rows:
            panels.append(dict(title=title, accent=accent, rows=[dict(label=label,
                cells=[dict(label=kind,count=count,loss=_format_score_loss(loss),
                            nonzero=bool(count) and _has_score_loss(loss),
                            tone='great' if label=='GREAT' else kind.lower()) for kind,count,loss in cells],
                total=_format_score_loss(subtotal) if _has_score_loss(subtotal) else None)
                for label,cells,subtotal in panel_rows], total_label=total_label,
                total=_format_score_loss(total) if _has_score_loss(total) else None))
    cover = cover_html(payload['cover_url'], payload['type'], cover_name=payload['cover_name'], show_type=False) if payload['cover_url'] or payload['cover_name'] else ''
    card = render_template('score.html', img_width, payload=payload, texts=texts, rows=rows,
                           color=difficulty_color(payload['difficulty']),
                           header_color='#72148d' if payload['difficulty']=='remaster' else 'white',
                           cover=cover, type_src=file_uri(os.path.join(ICON_TYPE_DIR, f"{payload['type']}.png")),
                           achievement=achievement_text, constant=constant_text, icons=icons,
                           progress=progress, panels=panels, table_rows=_score_judgement_table(payload),
                           validation=(result or {}).get('validation') or {},
                           rank_src=file_uri(os.path.join(ICON_SCORE_DIR, f"{rank}.png")) if rank else '',
                           combo_src=file_uri(os.path.join(ICON_COMBO_RCD_DIR, f"{combo}.png")) if combo and combo != 'back' else '')
    return compose_generated_images([card], timezone_offset=timezone_offset, bg_filter=bg_filter)


def generate_records_picture(up_songs=None, down_songs=None, title="RECORD", ver="jp", details=None, skin=None):
    from modules.images.renderer import file_uri, render_template
    up_songs, down_songs = up_songs or [], down_songs or []
    records = up_songs + down_songs
    if not records:
        return None
    language = image_language(ver)
    up_ra = sum(record['ra'] for record in up_songs)
    down_ra = sum(record['ra'] for record in down_songs)
    all_ra = round(up_ra + down_ra, 2)
    stats = [
        (_image_text('records.avg_level', language), f"{sum(r['internalLevelValue'] for r in records) / len(records):.2f}"),
        (_image_text('records.avg_achievement', language), f"{sum(float(r['score'][:-1]) for r in records) / len(records):.4f}%"),
        (_image_text('records.avg_rating', language), f"{all_ra / len(records):.2f}"),
    ]
    detail_rows = [(key, [(token, difficulty_color(token.lower()) if token.lower() in DIFFICULTY_STYLES else None)
                          for token in str(value).split()]) for key, value in (details or {}).items()]
    return render_template("records.html", 1580, skin=skin, title=title, stats=stats,
                           texts={key: _image_text(f"records.{key}", language) for key in ("heading", "tracks")},
                           rating=str(int(all_ra)).rjust(5), rating_src=file_uri(get_rating_image_path(int(all_ra))),
                           equation=f"= {_format_rating_value(up_ra)} + {_format_rating_value(down_ra)}" if up_ra and down_ra else "",
                           details=detail_rows, up=[thumbnail_html(song, skin=skin, language=language) for song in up_songs],
                           down=[thumbnail_html(song, skin=skin, language=language) for song in down_songs])


@skinnable
def generate_cover(cover_url, type, icon=None, icon_type=None, cover_name=None, complete_info=None, difficulty=None, achieved=None, song_title=None):
    from modules.images.renderer import render_html
    body = cover_html(cover_url, type, icon, icon_type, cover_name, complete_info,
                      difficulty, achieved, song_title)
    return render_html(body, 150, 180 if complete_info is not None or difficulty is not None else 150)


@skinnable
def generate_plate_image(target_data, title, img_width=1820,
                         max_per_row=10, margin=20, headers=None):
    from modules.images.renderer import image_uri, file_uri, render_template
    if max_per_row < 1:
        raise ValueError("max_per_row must be positive")
    rows = []
    for level in ("15", "14+", "14", "13+", "13", "12+", "12", "11+", "11", "10+", "10"):
        entries = sorted((entry for entry in target_data if entry['level'] == level),
                         key=lambda x: (not x.get('achieved', False), -x.get('achievement_rate', 0.0)))
        if entries:
            rows.append((level, [image_uri(entry['img']) for entry in entries]))
    cards = [(key.upper(), "✓" if value['clear'] == value['all'] and value['all'] > 0
              else f"{value['clear']} / {value['all']}", difficulty_color(key))
             for key, value in (headers or {}).items()]
    return render_template("progress.html", img_width, mode="plate", margin=margin,
                           max_per_row=max_per_row, title=title,
                           title_src=file_uri(os.path.join(PLATES_DIR, f"{title}.webp")),
                           cards=cards, rows=rows)


def _level_group_sort_key(level):
    if str(level) == "10-":
        return (9, 0)
    match = re.match(r"^(\d+)(\+?)$", str(level))
    if not match:
        return (-1, 0)
    return (int(match.group(1)), 1 if match.group(2) else 0)


def _progress_level_group_label(level):
    match = re.match(r"^(\d+)(\+?)$", str(level))
    if match and int(match.group(1)) < 10:
        return "10-"
    return str(level)


@skinnable
def generate_level_rank_progress_image(
    target_data,
    level_name,
    rank_name,
    stats,
    img_width=2700,
    max_per_row=15,
    margin=20,
    group_by="internal_level",
    show_progress_suffix=True,
    ver="jp",
):
    """
    生成难度评级进度图片，顶部显示总体统计卡片，下方显示分组封面列表

    参数:
        target_data: 歌曲数据列表，每个元素为 {"img": PIL.Image, "level": str, "internal_level": float, "achieved": bool, "difficulty": str, "achievement_rate": float}
        level_name: 难度名称（如 "13", "13+", "14", "14+"）
        rank_name: 评级名称（如 "SSS⁺", "AP", "FDX"）
        stats: 统计信息字典 {"achieved": int, "unachieved": int, "unplayed": int, "total": int}
        img_width: 图片总宽度
        max_per_row: 每行最多显示的歌曲数量
        margin: 边距
        group_by: "internal_level" 按定数分组，"level" 按等级分组
        show_progress_suffix: 是否在进度标题末尾显示 PROGRESS
        ver: 服务器版本，决定图片使用日文或英文
    """
    language = image_language(ver)
    if max_per_row < 1:
        raise ValueError("max_per_row must be positive")

    # Group once instead of scanning every entry again for every level.
    groups = {}
    for entry in target_data:
        key = (_progress_level_group_label(entry.get("level", ""))
               if group_by == "level" else entry["internal_level"])
        groups.setdefault(key, []).append(entry)
    group_values = sorted(groups, key=_level_group_sort_key, reverse=True) if group_by == "level" else sorted(groups, reverse=True)
    rows = []
    for group_value in group_values:
        row_entries = groups[group_value]
        if group_by == "level" and group_value == "10-":
            row_entries.sort(key=lambda x: (-x.get("internal_level", 0.0), not x["achieved"], -x.get("achievement_rate", 0.0)))
        else:
            row_entries.sort(key=lambda x: (not x["achieved"], -x.get("achievement_rate", 0.0)))
        label = str(group_value) if group_by == "level" else f"{group_value:.1f}"
        rows.append((label, row_entries))

    # 顶部布局：标题单独居中一行，统计卡片下一行横向铺满。
    if rank_name:
        suffix = f" {_image_text('progress.progress_suffix', language)}" if show_progress_suffix else ""
        title_text = f"{level_name} {rank_name}{suffix}"
    else:
        title_text = f"{level_name} {_image_text('progress.level_list_suffix', language)}"

    from modules.images.renderer import image_uri, render_template
    cards = []
    for key, count, color in (
        ("completed", stats["achieved"], "#4caf50"),
        ("incomplete", stats["unachieved"], "#ff9800"),
        ("unplayed", stats["unplayed"], "#9e9e9e"),
        ("total", stats["total"], "#4285f4"),
    ):
        value = f"{count} ({count / stats['total'] * 100:.1f}%)" if key != "total" and stats['total'] > 0 else str(count)
        cards.append((_image_text(f"progress.{key}", language), value, color))
    return render_template("progress.html", img_width, mode="progress", title=title_text,
                           margin=margin, max_per_row=max_per_row, cards=cards,
                           rows=[(label, [image_uri(entry['img']) for entry in entries])
                                 for label, entries in rows])


def difficulty_color(difficulty):
    style = DIFFICULTY_STYLES.get(str(difficulty).lower())
    return style["background"].lower() if style else "#c8c8c8"


def icon_uri(value, directory, url):
    from modules.images.renderer import file_uri, image_uri

    if not value:
        return ''
    path = Path(directory) / f'{value}.png'
    cached = file_uri(path)
    if cached:
        return cached
    image = image_cache.download_and_cache_icon(url, str(path))
    if image is None:
        return ''
    try:
        return image_uri(image)
    finally:
        image.close()


def cover_html(cover_url, type, icon=None, icon_type=None, cover_name=None,
               complete_info=None, difficulty=None, achieved=None, song_title=None, skin=None,
               show_type=True):
    from modules.images.renderer import file_uri, image_uri, template

    path = Path(COVERS_DIR) / Path(cover_name).name if cover_name else None
    cover_src = file_uri(path) if path else ''
    if not cover_src:
        cover = image_cache.get_cover_image(cover_url, cover_name)
        try:
            cover_src = image_uri(cover) if cover is not None else ''
        finally:
            if cover is not None:
                cover.close()
    type_src = icon_uri(type, ICON_TYPE_DIR,
                        'https://maimaidx.jp/maimai-mobile/img/music_standard.png' if type == 'std'
                        else 'https://maimaidx.jp/maimai-mobile/img/music_dx.png') if show_type else ''
    status = icon_uri(icon, str(Path(ICON_BASE_DIR) / str(icon_type)),
                      f'https://maimaidx.jp/maimai-mobile/img/music_icon_{icon}.png') if icon and icon_type and icon != 'back' else ''
    footer = complete_info is not None or difficulty is not None
    return template('cover.html', skin=skin, cover=cover_src, type_src=type_src, status=status,
                    color=difficulty_color(difficulty), difficulty=difficulty,
                    achieved=achieved, footer=footer, plate=complete_info is not None,
                    blocks=[difficulty_color(d) if (complete_info or {}).get(d) else 'white'
                            for d in ('basic','advanced','expert','master')],
                    title=song_title or '', text_color='#72148d' if difficulty == 'remaster' else 'white')


def thumbnail_html(song, inline=False, skin=None, language="ja"):
    from modules.images.renderer import template

    icons = {}
    for key, directory, name in (
        ('score_icon', ICON_SCORE_DIR, lambda v: 'playlog/' + v.replace('p','plus')),
        ('combo_icon', ICON_COMBO_RCD_DIR if inline else ICON_COMBO_DIR,
         lambda v: 'playlog/' + v.replace('back','fc_dummy').replace('fcp','fcplus').replace('app','applus') if inline else 'music_icon_' + v),
        ('sync_icon', ICON_SYNC_RCD_DIR if inline else ICON_SYNC_DIR,
         lambda v: 'playlog/' + v.replace('back','sync_dummy').replace('fdx','fsd').replace('p','plus') if inline else 'music_icon_' + v),
        ('dx_star', ICON_DX_STAR_DIR, lambda v: 'music_icon_dxstar_detail_' + v),
    ):
        value = song.get(key)
        icons[key] = icon_uri(value, directory, f'https://maimaidx.jp/maimai-mobile/img/{name(str(value))}.png') if value else ''
    cover = '' if inline else cover_html(song.get('cover_url'), song.get('type'), cover_name=song.get('cover_name'), skin=skin)
    return template('thumbnail.html', skin=skin, song=song, inline=inline, icons=icons, cover=cover,
                    play_count_label=_image_text('records.play_count', language),
                    color=difficulty_color(song.get('difficulty')),
                    text_color='#72148d' if song.get('difficulty') == 'remaster' else 'white',
                    version=str(song.get('version','')).replace(' PLUS','+').replace('でらっくす','DX'))


@skinnable
def generate_crop_preview_picture(crops, ver="jp", timezone_offset=9, bg_filter=None):
    """Present detector crops without stretching or changing their content."""
    from modules.images.renderer import image_uri, render_template
    language = image_language(ver)
    cards = [dict(name=name, src=image_uri(crop), width=crop.width, height=crop.height,
                  label=_image_text(f"crop.{name}", language)) for name, crop in crops]
    card = render_template("crop.html", 1600, cards=cards,
                           title=_image_text("crop.title", language),
                           subtitle=_image_text("crop.subtitle", language))
    return compose_generated_images([card], timezone_offset=timezone_offset, bg_filter=bg_filter)
