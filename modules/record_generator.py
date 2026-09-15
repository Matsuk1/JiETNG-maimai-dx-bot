import math
import logging
import os
import re
from modules.score_rules import DIFFICULTY_LABELS, JUDGEMENT_ROWS, score_rank as canonical_rank, combo_status as canonical_combo

from PIL import Image, ImageDraw, ImageFont

from modules.config_loader import (
    FONT_FILE,
    PLATES_DIR,
    ICON_TYPE_DIR,
    ICON_SCORE_DIR,
    ICON_DX_STAR_DIR,
    ICON_COMBO_DIR,
    ICON_SYNC_DIR,
    ICON_COMBO_RCD_DIR,
    ICON_SYNC_RCD_DIR,
    ICON_BASE_DIR
)
from modules.image_cache import download_and_cache_icon, get_cover_image, paste_icon_optimized
from modules.image_manager import (
    compose_generated_images,
    draw_aligned_colon_text,
    font_large,
    font_level_badge,
    font_record_detail_title,
    font_record_info,
    font_record_name,
    font_record_title,
    font_small,
    font_stadium,
    round_corner,
    truncate_text,
)
from modules.i18n import image_language, language_catalog, select_text
from modules.maimai_manager import get_rating_image_path
from modules.record_manager import get_single_ra

logger = logging.getLogger(__name__)

RECORD_RATING_BLOCK_SIZE = (259, 51)


def _image_text(path, language):
    return select_text(language_catalog(f"images.{path}"), language=language)
RATING_SOURCE_WIDTH = 296
RATING_DIGIT_WIDTH = 23
RATING_DIGIT_START_X = 140
RATING_DIGIT_Y_OFFSET = 1
RATING_EQUATION_GAP = 18
RATING_EQUATION_Y_OFFSET = -5
RATING_STATS_GAP = 2
HEADER_STAT_SPACING = 4


def _format_rating_value(value):
    return str(int(value)) if float(value).is_integer() else str(value)


def _split_colon_lines(lines):
    left_texts = []
    right_texts = []
    for line in lines:
        if ":" in line:
            left, right = line.split(":", 1)
            left_texts.append(left + ":")
            right_texts.append(right.strip())
        else:
            left_texts.append(line)
            right_texts.append("")
    return left_texts, right_texts


def _measure_aligned_colon_width(draw, lines, font):
    left_texts, right_texts = _split_colon_lines(lines)
    left_width = max(draw.textbbox((0, 0), text, font=font)[2] for text in left_texts) + 10
    right_width = max(draw.textbbox((0, 0), text, font=font)[2] for text in right_texts) if right_texts else 0
    return left_width + right_width


def _draw_record_rating_block(base_img, draw, rating, position, size=RECORD_RATING_BLOCK_SIZE, font=font_large):
    rating_int = int(float(rating))
    rating_text = str(rating_int).rjust(5)
    x, y = position
    scale_x = size[0] / RATING_SOURCE_WIDTH

    with Image.open(get_rating_image_path(rating_int)) as rb:
        rb_img = rb.convert("RGBA").resize(size, Image.LANCZOS)
    base_img.paste(rb_img, position, rb_img)

    char_width = RATING_DIGIT_WIDTH * scale_x
    start_x = x + RATING_DIGIT_START_X * scale_x
    for i, char in enumerate(rating_text):
        char_bbox = draw.textbbox((0, 0), char, font=font)
        digit_width = char_bbox[2] - char_bbox[0]
        offset = (char_width - digit_width) / 2
        text_height = char_bbox[3] - char_bbox[1]
        centered_y = y + (size[1] - text_height) / 2 - char_bbox[1] + RATING_DIGIT_Y_OFFSET
        draw.text((start_x + i * char_width + offset, centered_y), char, fill=(255, 255, 255), font=font)

def _get_difficulty_color(difficulty):
    colors = {
        "basic": (117, 181, 32),     # 绿色
        "advanced": (239, 165, 8),   # 黄色
        "expert": (204, 77, 89),     # 红色
        "master": (159, 81, 220),    # 紫色
        "remaster": (233, 212, 243), # 白色
        "utage": (245, 46, 221)      # 粉色
    }
    return colors.get(difficulty.lower(), (200, 200, 200))


_DIFF_KEYS = {"basic", "advanced", "expert", "master", "remaster", "utage"}


def _draw_detail_line(draw, x, y, key, value, font, max_w, lh):
    """绘制一行 detail，value 中的难度词替换为彩色圆角矩形小方块。"""
    tokens = value.split()
    has_diff = any(t.lower() in _DIFF_KEYS for t in tokens)

    if not has_diff:
        line = truncate_text(draw, f"{key}:  {value}", font, max_w)
        draw.text((x, y), line, fill=(40, 40, 40), font=font)
        return

    prefix = f"{key}:  "
    prefix_w = int(draw.textlength(prefix, font=font))
    if prefix_w >= max_w:
        return
    draw.text((x, y), prefix, fill=(40, 40, 40), font=font)

    cur_x = x + prefix_w
    pill_h = lh - 2

    sq = pill_h
    for token in tokens:
        diff_key = token.lower()
        if diff_key in _DIFF_KEYS:
            if cur_x + sq > x + max_w:
                break
            color = _get_difficulty_color(diff_key)
            draw.rounded_rectangle(
                (cur_x, y + 1, cur_x + sq, y + 1 + sq),
                radius=3, fill=color
            )
            cur_x += sq + 4
        else:
            token_w = int(draw.textlength(token + " ", font=font))
            if cur_x + token_w > x + max_w:
                break
            draw.text((cur_x, y), token, fill=(80, 80, 80), font=font)
            cur_x += token_w


def _draw_level_label(draw, text, x, row_top, content_h, font,
                      diameter=92, dx=-10, dy=0,
                      border_color=(150, 150, 150, 255), border_width=4):
    """绘制固定大小的等级圆形标签。"""
    label_text = str(text)
    max_text_width = diameter - border_width * 2 - 8
    label_font = font
    if draw.textlength(label_text, font=label_font) > max_text_width:
        label_font = _fit_font_to_width(draw, label_text, max_text_width, 40, 28)

    left = x + dx
    top = row_top + (content_h - diameter) // 2 + dy
    draw.ellipse(
        (left, top, left + diameter, top + diameter),
        fill=(255, 255, 255, 255),
        outline=border_color,
        width=border_width,
    )

    bbox = draw.textbbox((0, 0), label_text, font=label_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    tx = left + (diameter - text_w) / 2 - bbox[0]
    ty = top + (diameter - text_h) / 2 - bbox[1]
    draw.text((tx, ty), label_text, fill="black", font=label_font)


def create_thumbnail_in_line(song):
    from modules.html_cards import thumbnail_html
    from modules.html_renderer import render_html
    return render_html(thumbnail_html(song, inline=True), 600, 225)


def create_thumbnail(song):
    from modules.html_cards import thumbnail_html
    from modules.html_renderer import render_html
    return render_html(thumbnail_html(song), 300, 150)


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


def _paste_dx_progress_gradient(img, box, current_x, start_percentage):
    x1, y1, x2, y2 = (int(round(value)) for value in box)
    track_w = max(1, x2 - x1)
    track_h = max(1, y2 - y1)
    fill_w = min(track_w, max(0, int(round(current_x - x1))))
    if fill_w <= 0:
        return

    axis_span = max(0.0001, 100.0 - start_percentage)
    gradient = Image.new("RGBA", (fill_w, track_h), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(gradient)
    for offset in range(fill_w):
        percentage = start_percentage + offset / max(1, track_w - 1) * axis_span
        gradient_draw.line(
            (offset, 0, offset, track_h),
            fill=(*_dx_progress_color(percentage), 255),
        )

    mask = Image.new("L", (fill_w, track_h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        (0, 0, fill_w, track_h),
        radius=track_h // 2,
        fill=255,
    )
    gradient.putalpha(mask)
    img.alpha_composite(gradient, (x1, y1))


def _draw_score_card(draw, box, radius=18, fill=(248, 250, 252), outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _paste_local_icon(img, directory, name, size, position):
    if not name:
        return False
    path = os.path.join(directory, f"{name}.png")
    if not os.path.exists(path):
        return False
    try:
        with Image.open(path) as icon:
            icon_img = icon.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        img.alpha_composite(icon_img, position)
        return True
    except Exception as e:
        logger.error(f"[RecordGenerator] ✗ Failed to paste local icon: path={path}, error={e}")
        return False


def _paste_dx_star_status(img, star, size, position, achieved):
    path = os.path.join(ICON_DX_STAR_DIR, f"{star}.png")
    if not os.path.exists(path):
        return False
    try:
        with Image.open(path) as icon:
            icon_img = icon.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        if not achieved:
            alpha = icon_img.getchannel("A").point(lambda value: value * 72 // 255)
            icon_img.putalpha(alpha)
        img.alpha_composite(icon_img, position)
        return True
    except Exception as e:
        logger.error(f"[RecordGenerator] ✗ Failed to paste DX star icon: path={path}, error={e}")
        return False


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


def _draw_score_section_title(draw, x, y, title, accent, font):
    draw.rounded_rectangle((x, y + 5, x + 10, y + 42), radius=5, fill=accent)
    draw.text((x + 20, y), title, font=font, fill=(20, 24, 32))


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


def generate_score_recognition_picture(
    result,
    ver="jp",
    img_width=1100,
    timezone_offset=9,
    bg_filter=None,
):
    """
    Generate a static score-recognition result image using the same data hierarchy
    as the OCR FlexMsg.
    """
    payload = _score_recognition_payload(result)
    difficulty = str(payload.get("difficulty") or "").lower()
    diff_color = _get_difficulty_color(difficulty)
    metric_color = (114, 20, 141) if difficulty == "remaster" else diff_color
    header_text_color = (114, 20, 141) if difficulty == "remaster" else (255, 255, 255)

    language = image_language(ver)
    texts = {
        key: _image_text(f"score.{key}", language)
        for key in ("subtitle", "judgement", "loss", "break", "empty")
    }

    font_header = ImageFont.truetype(FONT_FILE, 48)
    font_subtitle = ImageFont.truetype(FONT_FILE, 26)
    font_label = ImageFont.truetype(FONT_FILE, 24)
    font_value = ImageFont.truetype(FONT_FILE, 42)
    font_table = ImageFont.truetype(FONT_FILE, 26)
    font_table_bold = ImageFont.truetype(FONT_FILE, 28)
    font_small_detail = ImageFont.truetype(FONT_FILE, 22)
    font_section = ImageFont.truetype(FONT_FILE, 34)
    font_progress = ImageFont.truetype(FONT_FILE, 20)

    margin = 42
    content_w = img_width - margin * 2
    draw_probe = ImageDraw.Draw(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
    display_title = payload.get("title") or "-"
    header_cover_size = 112
    header_cover_gap = 26
    has_header_cover = bool(payload.get("cover_url") or payload.get("cover_name"))
    title_max_w = content_w - 96
    if has_header_cover:
        title_max_w -= header_cover_size + header_cover_gap
    else:
        title_max_w -= 96
    title_text = truncate_text(draw_probe, display_title, font_header, max(240, title_max_w))
    subtitle = f"{texts['subtitle']}  {payload.get('difficulty_label') or '-'}"

    judgement = payload.get("judgement") or {}
    row_order = (("tap", "TAP"), ("hold", "HOLD"), ("slide", "SLIDE"), ("touch", "TOUCH"), ("break", "BREAK"))
    visible_rows = [(key, label, judgement.get(key)) for key, label in row_order if isinstance(judgement.get(key), dict)]
    dx_progress = _score_dx_progress(judgement)

    loss_rows = _score_loss_rows_from_internal(judgement, payload.get("loss_percentages") or {})
    break_detail = payload.get("break_detail") or {}
    break_rows = _score_break_rows_from_internal(judgement, break_detail)
    total_loss = sum(
        float(total)
        for _, _, total in loss_rows
        if isinstance(total, (int, float))
    )

    header_h = 150
    metric_h = 100
    progress_h = 170 if dx_progress else 0
    progress_gap = 28 if dx_progress else 0
    table_h = 64 + max(1, len(visible_rows)) * 58
    loss_h = 0
    if loss_rows:
        loss_h = 98 + len(loss_rows) * 148
        if _has_score_loss(total_loss):
            loss_h += 74
    break_h = 0
    if break_rows:
        break_h = 98 + len(break_rows) * 148
        break_total = break_detail.get("total_loss")
        if _has_score_loss(break_total) or break_total is None:
            break_h += 74
    img_height = (
        margin + 24 + header_h + 28 + metric_h + 30
        + progress_h + progress_gap + 58 + table_h
        + loss_h + break_h + margin + 80
    )

    img = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    y = margin + 24
    _draw_score_card(draw, (margin + 22, y, img_width - margin - 22, y + header_h), radius=18, fill=diff_color)
    draw.text((margin + 48, y + 20), title_text, font=font_header, fill=header_text_color)
    draw.text((margin + 50, y + 90), subtitle, font=font_subtitle, fill=header_text_color)
    chart_type = str(payload.get("type") or "").lower()
    cover_x = img_width - margin - 48 - header_cover_size
    cover_y = y + (header_h - header_cover_size) // 2
    if has_header_cover:
        try:
            cover_img = generate_cover(
                payload.get("cover_url"),
                chart_type,
                cover_name=payload.get("cover_name"),
            ).resize((header_cover_size, header_cover_size), Image.Resampling.LANCZOS)
            cover_img = round_corner(cover_img.convert("RGBA"), radius=12)
            img.alpha_composite(cover_img, (cover_x, cover_y))
        except Exception as e:
            logger.error(f"[RecordGenerator] ✗ Failed to draw score recognition cover: error={e}")
            has_header_cover = False
    if not has_header_cover and chart_type in ("dx", "std", "utage"):
        type_icon_size = (78, 22) if chart_type != "utage" else (76, 30)
        _paste_local_icon(
            img,
            ICON_TYPE_DIR,
            chart_type,
            type_icon_size,
            (img_width - margin - 48 - type_icon_size[0], y + 99),
        )
    y += header_h + 28

    gap = 16
    metric_total_w = content_w - 44
    unit = (metric_total_w - gap * 2) / 8
    metric_boxes = [
        ("achievement", margin + 22, y, margin + 22 + unit * 2.7, y + metric_h),
        ("status", margin + 22 + unit * 2.7 + gap, y, margin + 22 + unit * 5.4 + gap, y + metric_h),
        ("constant", margin + 22 + unit * 5.4 + gap * 2, y, margin + 22 + unit * 8.0 + gap * 2, y + metric_h),
    ]
    for _, x1, y1, x2, y2 in metric_boxes:
        _draw_score_card(draw, (x1, y1, x2, y2), radius=14, fill=(248, 250, 252))

    achievement = payload.get("achievement")
    achievement_text = f"{achievement:.4f}%" if isinstance(achievement, (int, float)) else "-"
    draw.text((metric_boxes[0][1] + 34, y + 18), achievement_text, font=font_value, fill=(184, 110, 25))

    rank_icon = payload.get("rank_icon")
    combo_icon = payload.get("combo_icon")
    icon_items = []
    status_icon_h = 58
    rank_icon_size = (130, status_icon_h)
    combo_icon_size = (112, status_icon_h)
    if rank_icon:
        icon_items.append(("rank_icon", rank_icon, rank_icon_size, "rank"))
    combo_file = {
        "fc": "fc",
        "fcplus": "fcp",
        "ap": "ap",
        "applus": "app",
        "dummy": "back",
    }.get(str(combo_icon or ""))
    if combo_file:
        icon_items.append(("combo_icon", combo_file, combo_icon_size, "combo"))

    status_x1, status_y1, status_x2, _ = metric_boxes[1][1:]
    icon_gap = 16
    total_icon_w = sum(item[2][0] for item in icon_items) + icon_gap * max(0, len(icon_items) - 1)
    icon_x = int(status_x1 + max(18, (status_x2 - status_x1 - total_icon_w) / 2))
    icon_y = status_y1 + 22
    if rank_icon:
        rank_file = {
            "sssplus": "sssp",
            "ssplus": "ssp",
            "splus": "sp",
        }.get(rank_icon, rank_icon)
        _paste_local_icon(
            img,
            ICON_SCORE_DIR,
            rank_file,
            size=rank_icon_size,
            position=(icon_x, icon_y),
        )
        icon_x += rank_icon_size[0] + icon_gap
    if combo_file:
        _paste_local_icon(
            img,
            ICON_COMBO_RCD_DIR,
            combo_file,
            size=combo_icon_size,
            position=(icon_x, icon_y),
        )

    constant = payload.get("internal_level")
    combo_icon_name = str(combo_icon or "")
    if isinstance(constant, (int, float)):
        rcd_rating = get_single_ra(constant, achievement, "ap" in combo_icon_name)
        constant_text = f"{constant:.1f} → {rcd_rating}"
    else:
        constant_text = "-"
    draw.text((metric_boxes[2][1] + 28, y + 18), constant_text, font=font_value, fill=metric_color)
    y += metric_h + 30

    if dx_progress:
        progress_x = margin + 22
        progress_w = content_w - 44
        _draw_score_card(
            draw,
            (progress_x, y, progress_x + progress_w, y + progress_h),
            radius=14,
            fill=(248, 250, 252),
        )
        draw.text(
            (progress_x + 24, y + 36),
            "DX SCORE",
            font=font_table_bold,
            fill=(20, 24, 32),
            anchor="lm",
        )
        percentage_tenths = dx_progress["score"] * 1000 // dx_progress["maximum"]
        progress_value = (
            f"{dx_progress['score']} / {dx_progress['maximum']}"
            f"  {percentage_tenths // 10}.{percentage_tenths % 10}%"
        )
        draw.text(
            (progress_x + progress_w - 24, y + 36),
            progress_value,
            font=font_table_bold,
            fill=(184, 110, 25),
            anchor="rm",
        )

        track_x1 = progress_x + 30
        track_x2 = progress_x + progress_w - 30
        track_y1 = y + 96
        track_y2 = track_y1 + 18
        start_percentage = dx_progress["start_percentage"]
        axis_span = max(0.0001, 100.0 - start_percentage)

        def progress_position(percentage):
            bounded = min(100.0, max(start_percentage, percentage))
            return track_x1 + (bounded - start_percentage) / axis_span * (track_x2 - track_x1)

        _draw_score_card(
            draw,
            (track_x1, track_y1, track_x2, track_y2),
            radius=9,
            fill=(226, 230, 236),
        )
        current_x = progress_position(dx_progress["percentage"])
        _paste_dx_progress_gradient(
            img,
            (track_x1, track_y1, track_x2, track_y2),
            current_x,
            start_percentage,
        )

        for star, threshold in DX_STAR_THRESHOLDS:
            marker_x = progress_position(threshold)
            achieved = dx_progress["star"] >= star
            marker_color = DX_STAR_COLORS[star] if achieved else (160, 165, 174)
            draw.line((marker_x, track_y1 - 7, marker_x, track_y2 + 7), fill=marker_color, width=3)
            _paste_dx_star_status(
                img,
                star,
                size=(84, 16),
                position=(int(marker_x - 42), y + 70),
                achieved=achieved,
            )
            draw.text(
                (marker_x, y + 136),
                f"{threshold:.0f}%",
                font=font_progress,
                fill=marker_color,
                anchor="mm",
            )

        draw.ellipse(
            (current_x - 7, track_y1 + 2, current_x + 7, track_y2 - 2),
            fill=(255, 255, 255),
            outline=_dx_progress_color(dx_progress["percentage"]),
            width=3,
        )
        draw.text(
            (track_x1, y + 136),
            f"{start_percentage:.1f}%",
            font=font_progress,
            fill=(105, 110, 120),
            anchor="lm",
        )
        draw.text(
            (track_x2, y + 136),
            "100%",
            font=font_progress,
            fill=(105, 110, 120),
            anchor="rm",
        )
        y += progress_h + progress_gap

    _draw_score_section_title(draw, margin + 22, y, texts["judgement"], (38, 125, 139), font_section)
    y += 58
    table_x = margin + 22
    table_w = content_w - 44
    row_h = 58
    col_flex = [2, 1, 1, 1, 1, 1]
    flex_total = sum(col_flex)
    col_w = [table_w * flex / flex_total for flex in col_flex]
    headers = ("TYPE", "CP", "PF", "GR", "GD", "MS")
    header_colors = [(90, 96, 106), (184, 110, 25), (184, 110, 25), (163, 59, 117), (47, 125, 81), (85, 85, 85)]
    column_fills = [
        None,
        (255, 246, 220),
        (255, 246, 220),
        (251, 229, 241),
        (231, 245, 237),
        (233, 237, 242),
    ]
    zero_count_fill = (145, 150, 160)

    def count_text_fill(value, default_fill=(20, 24, 32)):
        try:
            return zero_count_fill if int(value) == 0 else default_fill
        except (TypeError, ValueError):
            return default_fill

    table_top = y
    table_bottom = y + row_h * (1 + max(1, len(visible_rows)))
    _draw_score_card(draw, (table_x, table_top, table_x + table_w, table_bottom), radius=14, fill=(255, 255, 255))
    _draw_score_card(draw, (table_x, y, table_x + table_w, y + row_h), radius=12, fill=(238, 241, 245))
    draw.rectangle((table_x, y + row_h // 2, table_x + table_w, y + row_h), fill=(238, 241, 245))
    cx = table_x
    for i, text in enumerate(headers):
        align_x = cx + 22 if i == 0 else cx + col_w[i] / 2
        anchor = "lm" if i == 0 else "mm"
        draw.text((align_x, y + row_h / 2), text, font=font_table_bold, fill=header_colors[i], anchor=anchor)
        cx += col_w[i]
    y += row_h

    if visible_rows:
        last_index = len(visible_rows) - 1
        for index, (_, label, row) in enumerate(visible_rows):
            fill = (248, 250, 252) if index % 2 == 0 else (255, 255, 255)
            if index == last_index:
                _draw_score_card(draw, (table_x, y, table_x + table_w, y + row_h), radius=12, fill=fill)
                draw.rectangle((table_x, y, table_x + table_w, y + row_h // 2), fill=fill)
            else:
                draw.rectangle((table_x, y, table_x + table_w, y + row_h), fill=fill)
            values = [
                label,
                row.get("critical_perfect", 0),
                row.get("perfect", 0),
                row.get("great", 0),
                row.get("good", 0),
                row.get("miss", 0),
            ]
            cx = table_x
            for i, value in enumerate(values):
                if i > 0 and column_fills[i]:
                    inset = 4
                    draw.rounded_rectangle(
                        (
                            cx + inset,
                            y + 7,
                            cx + col_w[i] - inset,
                            y + row_h - 7,
                        ),
                        radius=8,
                        fill=column_fills[i],
                    )
                align_x = cx + 22 if i == 0 else cx + col_w[i] / 2
                anchor = "lm" if i == 0 else "mm"
                fill_color = (20, 24, 32) if i == 0 else count_text_fill(value)
                draw.text((align_x, y + row_h / 2), str(value), font=font_table_bold if i == 0 else font_table, fill=fill_color, anchor=anchor)
                cx += col_w[i]
            y += row_h
    else:
        _draw_score_card(draw, (table_x, y, table_x + table_w, y + row_h), radius=10, fill=(248, 250, 252))
        draw.rectangle((table_x, y, table_x + table_w, y + row_h // 2), fill=(248, 250, 252))
        draw.text((table_x + 24, y + row_h / 2), texts["empty"], font=font_label, fill=(120, 126, 138), anchor="lm")
        y += row_h

    def draw_loss_panel(section_title, accent, rows):
        nonlocal y
        detail_x = table_x + 180
        detail_right = table_x + table_w
        y += 36
        _draw_score_section_title(draw, margin + 22, y, section_title, accent, font_section)
        y += 62
        for row_label, cells, total in rows:
            _draw_score_card(draw, (table_x, y, table_x + table_w, y + 82), radius=12, fill=(248, 250, 252))
            draw.text((table_x + 24, y + 41), row_label, font=font_table_bold, fill=(20, 24, 32), anchor="lm")
            cell_x = detail_x
            cell_w = (detail_right - detail_x) / max(1, len(cells))
            color_map = {
                "GREAT": ((146, 52, 104), (251, 229, 241)),
                "GOOD": ((39, 112, 71), (231, 245, 237)),
                "MISS": ((85, 85, 85), (233, 237, 242)),
            }
            for label, count, loss in cells:
                if row_label == "GREAT":
                    fg, bg = (146, 52, 104), (251, 229, 241)
                else:
                    fg, bg = color_map.get(label, ((154, 91, 18), (255, 240, 199)))
                cell_right = min(cell_x + cell_w - 8, detail_right - 8)
                _draw_score_card(draw, (cell_x, y + 10, cell_right, y + 72), radius=10, fill=bg)
                loss_fill = (192, 57, 43) if count and _has_score_loss(loss) else (105, 110, 120)
                draw.text(((cell_x + cell_right) / 2, y + 27), _format_score_loss(loss), font=font_small_detail, fill=loss_fill, anchor="mm")
                draw.text(((cell_x + cell_right) / 2, y + 54), str(count), font=font_table_bold, fill=count_text_fill(count, fg), anchor="mm")
                cell_x += cell_w
            y += 90
            if _has_score_loss(total):
                _draw_score_card(draw, (detail_x, y, detail_right, y + 46), radius=10, fill=(253, 237, 236))
                draw.text((detail_x + 16, y + 8), "TOTAL", font=font_small_detail, fill=(105, 110, 120))
                draw.text((detail_right - 24, y + 23), _format_score_loss(total), font=font_table_bold, fill=(192, 57, 43), anchor="rm")
                y += 58

    def draw_summary_total_bar(label, total, accent):
        nonlocal y
        if not _has_score_loss(total):
            return
        bar_h = 62
        fill = (
            max(0, accent[0] - 18),
            max(0, accent[1] - 18),
            max(0, accent[2] - 18),
        )
        _draw_score_card(draw, (table_x, y + 4, table_x + table_w, y + bar_h), radius=14, fill=fill)
        draw.text(
            (table_x + 24, y + bar_h / 2 + 2),
            label,
            font=font_small_detail,
            fill=(255, 255, 255),
            anchor="lm",
        )
        draw.text(
            (table_x + table_w - 24, y + bar_h / 2 + 2),
            _format_score_loss(float(total or 0)),
            font=font_table_bold,
            fill=(255, 246, 220),
            anchor="rm",
        )
        y += bar_h + 12

    if loss_rows:
        loss_accent = (192, 57, 43)
        draw_loss_panel(texts["loss"], loss_accent, loss_rows)
        draw_summary_total_bar(_image_text("score.common_total", language), total_loss, loss_accent)

    if break_rows:
        def break_row_total(cells):
            return sum(
                max(0, int(count or 0)) * (
                    float(loss) if isinstance(loss, (int, float)) else 0.0
                )
                for _, count, loss in cells
            )

        break_rows = [
            (label, cells, break_row_total(cells))
            for label, cells in break_rows
        ]
        total_break_loss = break_detail.get("total_loss")
        if not isinstance(total_break_loss, (int, float)):
            total_break_loss = sum(
                max(0, int(count or 0)) * (
                    float(loss) if isinstance(loss, (int, float)) else 0.0
                )
                for _, cells, _ in break_rows
                for _, count, loss in cells
            )
        break_accent = (184, 110, 25)
        draw_loss_panel(texts["break"], break_accent, break_rows)
        draw_summary_total_bar(_image_text("score.break_total", language), total_break_loss, break_accent)

    final_h = min(img_height, y + margin + 8)
    cropped = img.crop((0, 0, img_width, final_h))
    card_img = Image.new("RGBA", (img_width, final_h), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_img)
    _draw_score_card(
        card_draw,
        (margin // 2, margin // 2, img_width - margin // 2, final_h - margin // 2),
        radius=28,
        fill=(255, 255, 255, 245),
    )
    card_img.alpha_composite(cropped, (0, 0))
    return compose_generated_images(
        [card_img],
        timezone_offset=timezone_offset,
        bg_filter=bg_filter,
    )


def generate_records_picture(
    up_songs=None,
    down_songs=None,
    title="RECORD",
    ver="jp",
    details=None,
):
    up_songs = up_songs or []
    down_songs = down_songs or []
    details = details or {}
    language = image_language(ver)
    up_num = len(up_songs)
    down_num = len(down_songs)
    num = up_num + down_num

    if not num:
        return

    up_ra = down_ra = 0
    up_level = down_level = 0
    up_score = down_score = 0

    for rcd in up_songs:
        up_ra += rcd['ra']
        up_level += rcd['internalLevelValue']
        up_score += float(rcd['score'][:-1])

    for rcd in down_songs:
        down_ra += rcd['ra']
        down_level += rcd['internalLevelValue']
        down_score += float(rcd['score'][:-1])

    all_ra = round(up_ra + down_ra, 2)
    all_level = up_level + down_level
    all_score = up_score + down_score

    grid_size = (5, math.ceil(up_num / 5) + math.ceil(down_num / 5))
    thumb_size = (300, 150)
    side_width = 20
    spacing = 10
    header_height = 245

    version_padding = 0 if not (up_songs and down_songs) else 40

    img_width = grid_size[0] * (thumb_size[0] + spacing) - spacing + side_width * 2
    img_height = header_height + grid_size[1] * (thumb_size[1] + spacing) + version_padding + 13
    combined = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(combined)

    rating_equation = f"= {_format_rating_value(up_ra)} + {_format_rating_value(down_ra)}" if up_ra and down_ra else ""
    rating_block_size = RECORD_RATING_BLOCK_SIZE

    header_text = [
        f"{_image_text('records.avg_level', language)}: {all_level / num:.2f}",
        f"{_image_text('records.avg_achievement', language)}: {all_score / num:.4f}%",
        f"{_image_text('records.avg_rating', language)}: {all_ra / num:.2f}",
    ]

    # 绘制统计信息背景卡片（右侧）
    card_padding = 20
    card_y = side_width + 10

    # 实际文本总宽度
    max_text_width = _measure_aligned_colon_width(draw, header_text, font_large)
    rating_line_width = rating_block_size[0]
    if rating_equation:
        rating_line_width += RATING_EQUATION_GAP + int(draw.textlength(rating_equation, font=font_large))
    max_text_width = max(max_text_width, rating_line_width)

    line_height = draw.textbbox((0, 0), "JiETNG", font=font_large)[3]
    text_total_height = rating_block_size[1] + RATING_STATS_GAP + len(header_text) * (line_height + HEADER_STAT_SPACING)

    # 根据实际文本宽度设置卡片宽度，卡片靠左
    card_width = max_text_width + card_padding * 2
    card_height = text_total_height + card_padding * 2 - 10
    card_x = side_width + 10

    # 绘制带圆角的半透明背景框
    draw.rounded_rectangle(
        [card_x, card_y, card_x + card_width, card_y + card_height],
        radius=12,
        fill=(255, 255, 255),
        outline=(200, 210, 225),
        width=2
    )

    content_x = card_x + card_padding
    content_y = card_y + card_padding - 5
    _draw_record_rating_block(combined, draw, all_ra, (content_x, content_y), rating_block_size, font=font_large)
    if rating_equation:
        equation_x = content_x + rating_block_size[0] + RATING_EQUATION_GAP
        equation_y = content_y + (rating_block_size[1] - line_height) // 2 + RATING_EQUATION_Y_OFFSET
        draw.text((equation_x, equation_y), rating_equation, fill=(40, 40, 40), font=font_large)

    draw_aligned_colon_text(
        draw,
        lines=header_text,
        top_left=(content_x, content_y + rating_block_size[1] + RATING_STATS_GAP),
        font=font_large,
        spacing=HEADER_STAT_SPACING,
        fill=(40, 40, 40)
    )

    # 绘制标题/详情（右侧）
    if not details:
        title_y = card_y - 35
        title_w = int(draw.textlength(title, font=font_record_title))
        title_x = img_width - side_width - 10 - title_w
        draw.text((title_x, title_y), title, fill=(255, 255, 255), font=font_record_title, stroke_width=3, stroke_fill=(50, 50, 50))
    else:
        # 将 title 渲染到临时 RGBA 图，逆时针旋转 45°，缩放至 card_height
        tb = draw.textbbox((0, 0), title, font=font_record_detail_title)
        tmp = Image.new("RGBA", (tb[2] + 4, tb[3] + 4), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((2, 2), title, fill=(255, 255, 255, 255), font=font_record_detail_title, stroke_width=2, stroke_fill=(50, 50, 50, 255))
        tmp_rot = tmp.rotate(45, expand=True, resample=Image.Resampling.BICUBIC)
        rot_h = card_height
        rot_w = max(1, int(tmp_rot.width * rot_h / tmp_rot.height))
        tmp_rot = tmp_rot.resize((rot_w, rot_h), Image.Resampling.LANCZOS)

        title_paste_x = card_x + card_width + 15
        combined.paste(tmp_rot, (title_paste_x, card_y), tmp_rot)
        draw = ImageDraw.Draw(combined)

        # 计算列数：每列最多 4 条，最多 2 列
        details_items = list(details.items())
        num_items = len(details_items)
        items_per_col = 4
        num_cols = min(2, math.ceil(num_items / items_per_col)) if num_items > 0 else 1

        left_bound = title_paste_x + rot_w
        right_bound = img_width
        avail_w = max(1, right_bound - left_bound)
        col_gap = 15
        lh = draw.textbbox((0, 0), "A", font=font_large)[3] + 2

        details_card_x = left_bound + card_padding
        details_card_x2 = right_bound - 30
        if num_cols == 1:
            col_max_w = max(1, avail_w - card_padding * 2)
        else:
            col_max_w = max(1, (avail_w - card_padding * 2 - col_gap) // 2)

        draw.rounded_rectangle(
            [details_card_x, card_y, details_card_x2, card_y + card_height],
            radius=12,
            fill=(255, 255, 255),
            outline=(200, 210, 225),
            width=2
        )

        for col_num in range(num_cols):
            col_x = details_card_x + card_padding + col_num * (col_max_w + col_gap)
            col_y = card_y + card_padding - 5
            for i in range(items_per_col):
                idx = col_num * items_per_col + i
                if idx >= num_items:
                    break
                key, value = details_items[idx]
                _draw_detail_line(draw, col_x, col_y, key, str(value), font_large, col_max_w, lh)
                col_y += lh

    up_thumbnails = [create_thumbnail(song) for song in up_songs[:grid_size[0] * grid_size[1]]]
    down_thumbnails = [create_thumbnail(song) for song in down_songs[:grid_size[0] * grid_size[1]]]
    for i, thumb in enumerate(up_thumbnails):
        x_offset = (i % grid_size[0]) * (thumb_size[0] + spacing) + side_width
        y_offset = header_height + (i // grid_size[0]) * (thumb_size[1] + spacing)
        combined.paste(thumb, (x_offset, y_offset), thumb)

    # 计算up部分最后一行的底部位置
    up_rows = math.ceil(up_num / grid_size[0])
    total_up_y_offset = header_height + up_rows * (thumb_size[1] + spacing)

    # 在上下部分中间绘制分隔线 (----·----) - 仅当同时有上下部分时显示
    if up_songs and down_songs:
        divider_y = total_up_y_offset + version_padding // 3 + 2
        divider_color = (0, 0, 0)

        # 计算中心点和线条长度
        center_x = img_width // 2
        line_half_length = (img_width - side_width * 2) // 2

        # 绘制左侧横线
        left_line_start = center_x - line_half_length // 2 - 40
        left_line_end = center_x - 30
        draw.line([(left_line_start, divider_y), (left_line_end, divider_y)], fill=divider_color, width=2)

        # 绘制中心点
        dot_radius = 3
        draw.ellipse([center_x - dot_radius, divider_y - dot_radius,
                     center_x + dot_radius, divider_y + dot_radius], fill=divider_color)

        # 绘制右侧横线
        right_line_start = center_x + 30
        right_line_end = center_x + line_half_length // 2 + 40
        draw.line([(right_line_start, divider_y), (right_line_end, divider_y)], fill=divider_color, width=2)

    for i, thumb in enumerate(down_thumbnails):
        x_offset = (i % grid_size[0]) * (thumb_size[0] + spacing) + side_width
        y_offset = total_up_y_offset + version_padding + (i // grid_size[0]) * (thumb_size[1] + spacing)
        combined.paste(thumb, (x_offset, y_offset), thumb)

    return combined


def generate_cover(cover_url, type, icon=None, icon_type=None, cover_name=None, complete_info=None, difficulty=None, achieved=None, song_title=None):
    from modules.html_cards import cover_html
    from modules.html_renderer import render_html
    body = cover_html(cover_url, type, icon, icon_type, cover_name, complete_info,
                      difficulty, achieved, song_title)
    return render_html(body, 150, 180 if complete_info is not None or difficulty is not None else 150)


def generate_plate_image(
    target_data,
    title,
    img_width=1820,
    img_height=600,
    max_per_row=10,
    margin=20,
    headers=None,
):
    headers = headers or {}
    level_width = 100
    img_size = 150
    footer_height = 30  # 与 generate_cover 中的 footer_height 一致
    row_height = img_size + footer_height + margin

    rows = []
    rows_num = 0
    level_list = ["15", "14+", "14", "13+", "13", "12+", "12", "11+", "11", "10+", "10"]
    for level in level_list:
        level_entries = [entry for entry in target_data if entry["level"] == level]
        # 按达成状态和达成率排序：已达成在前，未达成的按达成率从大到小
        level_entries.sort(key=lambda x: (not x.get("achieved", False), -x.get("achievement_rate", 0.0)))
        row_imgs = [entry["img"] for entry in level_entries]
        rows_num += math.ceil(len(row_imgs) / max_per_row)
        if row_imgs:
            rows.append((level, row_imgs))

    total_height = rows_num * row_height + margin + 170 + 40

    final_img = Image.new("RGBA", (img_width, total_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(final_img)

    # 绘制左侧信息栏：卡片式容器（2列布局）
    card_start_x = margin - 20
    card_y = margin + 15
    card_width = 325
    card_height = 65
    card_gap_x = 15  # 横向间距
    card_gap_y = 12  # 纵向间距
    border_width = 8

    final_img = final_img.convert("RGBA")

    for idx, (key, value) in enumerate(headers.items()):
        # 计算卡片位置
        row = idx % 2
        col = idx // 2
        card_x = card_start_x + col * (card_width + card_gap_x)
        current_y = card_y + row * (card_height + card_gap_y)

        # 获取难度对应的颜色
        difficulty_color = _get_difficulty_color(key)

        # 创建卡片层用于阴影和圆角
        card_layer = Image.new("RGBA", final_img.size, (0, 0, 0, 0))
        card_draw = ImageDraw.Draw(card_layer)

        # 绘制阴影效果
        shadow_offset = 3
        card_draw.rounded_rectangle(
            [card_x + shadow_offset, current_y + shadow_offset,
             card_x + card_width + shadow_offset, current_y + card_height + shadow_offset],
            radius=12,
            fill=(0, 0, 0, 30)
        )

        # 绘制卡片主体背景
        r, g, b = difficulty_color[:3]
        light_r = int(r + (255 - r) * 0.85)
        light_g = int(g + (255 - g) * 0.85)
        light_b = int(b + (255 - b) * 0.85)
        bg_color = (light_r, light_g, light_b, 255)

        card_draw.rounded_rectangle(
            [card_x, current_y, card_x + card_width, current_y + card_height],
            radius=12,
            fill=bg_color
        )

        # 绘制左侧彩色边框
        card_draw.rounded_rectangle(
            [card_x, current_y, card_x + border_width, current_y + card_height],
            radius=12,
            fill=difficulty_color + (255,) if len(difficulty_color) == 3 else difficulty_color
        )

        # 将卡片层合成到图像上
        final_img = Image.alpha_composite(final_img, card_layer)
        draw = ImageDraw.Draw(final_img)

        # 绘制难度名称
        text_x = card_x + border_width + 15
        text_y = current_y + (card_height - 30) // 2 - 5
        difficulty_text = f"{key.upper()}"
        draw.text((text_x, text_y), difficulty_text, fill=(60, 60, 60), font=font_large)

        # 判断是否全部完成
        is_completed = value['clear'] == value['all'] and value['all'] > 0

        # 绘制数据
        if is_completed:
            data_text = "✓"
        else:
            data_text = f"{value['clear']} / {value['all']}"

        data_text_width = draw.textlength(data_text, font=font_large)
        data_x = card_x + card_width - data_text_width - 15
        draw.text((data_x, text_y), data_text, fill=(40, 40, 40), font=font_large)

    draw = ImageDraw.Draw(final_img)

    # 添加右侧标题（称号图片）
    try:
        plate_path = os.path.join(PLATES_DIR, f"{title}.webp")
        if os.path.exists(plate_path):
            with Image.open(plate_path) as _plate:
                plate_img = _plate.convert("RGBA")

            target_height = 160
            aspect_ratio = plate_img.width / plate_img.height
            target_width = int(target_height * aspect_ratio)
            plate_img = plate_img.resize((target_width, target_height), Image.Resampling.LANCZOS)

            # 位置：右上角，横向中轴线不变
            plate_x = img_width - margin - target_width + 20
            original_center_y = margin + 90
            plate_y = original_center_y - target_height // 2

            # 贴上称号图片（支持透明）
            final_img.paste(plate_img, (plate_x, plate_y), plate_img)
        else:
            # 如果图片不存在，回退到文字显示
            title_text_size = draw.textlength(title, font=font_record_title)
            title_x = img_width - margin - title_text_size - 30
            title_y = margin - 25
            draw.text((title_x, title_y), title, fill=(255, 255, 255), font=font_record_title, stroke_width=3, stroke_fill=(50, 50, 50))
            logger.debug(f"[RecordGenerator] Plate image not found, using text: plate={title}")
    except Exception as e:
        # 出错时回退到文字显示
        title_text_size = draw.textlength(title, font=font_record_title)
        title_x = img_width - margin - title_text_size - 30
        title_y = margin - 25
        draw.text((title_x, title_y), title, fill=(255, 255, 255), font=font_record_title, stroke_width=3, stroke_fill=(50, 50, 50))
        logger.error(f"[RecordGenerator] ✗ Failed to load plate image: plate={title}, error={e}")

    # 渲染主体图像内容
    y_offset = margin + 30 + 180
    for level, img_list in rows:
        _draw_level_label(draw, level, margin, y_offset, img_size, font_level_badge)

        x_offset = level_width + margin
        for i, img in enumerate(img_list):
            if i > 0 and i % max_per_row == 0:
                y_offset += row_height
                x_offset = level_width + margin

            if img.mode == "RGBA":
                final_img.paste(img, (x_offset, y_offset), img)
            else:
                final_img.paste(img, (x_offset, y_offset))
            x_offset += img_size + margin

        y_offset += row_height

    return final_img


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


def _fit_font_to_width(draw, text, max_width, start_size, min_size):
    for size in range(start_size, min_size - 1, -4):
        font = ImageFont.truetype(FONT_FILE, size)
        if draw.textlength(text, font=font) <= max_width:
            return font
    return ImageFont.truetype(FONT_FILE, min_size)


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
    level_width = 100
    img_size = 150
    footer_height = 30  # 与 generate_cover 中的 footer_height 一致
    row_height = img_size + footer_height + margin

    # 等级模式按定数分组；分类模式按谱面等级分组。
    rows = []
    total_rows = 0

    if group_by == "level":
        group_values = sorted(
            {_progress_level_group_label(entry.get("level", "")) for entry in target_data},
            key=_level_group_sort_key,
            reverse=True,
        )
    else:
        group_values = sorted(set(entry["internal_level"] for entry in target_data), reverse=True)

    for group_value in group_values:
        level_str = str(group_value) if group_by == "level" else f"{group_value:.1f}"
        if group_by == "level":
            row_entries = [
                entry for entry in target_data
                if _progress_level_group_label(entry.get("level", "")) == group_value
            ]
        else:
            row_entries = [entry for entry in target_data if entry.get(group_by) == group_value]

        if group_by == "level" and group_value == "10-":
            row_entries.sort(key=lambda x: (-x.get("internal_level", 0.0), not x["achieved"], -x.get("achievement_rate", 0.0)))
        else:
            row_entries.sort(key=lambda x: (not x["achieved"], -x.get("achievement_rate", 0.0)))

        if row_entries:
            rows.append((level_str, row_entries))
            total_rows += math.ceil(len(row_entries) / max_per_row)

    # 顶部布局：标题单独居中一行，统计卡片下一行横向铺满。
    if rank_name:
        suffix = f" {_image_text('progress.progress_suffix', language)}" if show_progress_suffix else ""
        title_text = f"{level_name} {rank_name}{suffix}"
    else:
        title_text = f"{level_name} {_image_text('progress.level_list_suffix', language)}"

    measure_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
    title_font = _fit_font_to_width(measure_draw, title_text, img_width - margin * 4, 170, 92)
    title_bbox = measure_draw.textbbox((0, 0), title_text, font=title_font, stroke_width=3)
    title_height = title_bbox[3] - title_bbox[1]

    title_y = margin + 5
    card_y = title_y + title_height + 42
    card_height = 170
    card_gap_x = 26
    content_gap = 54
    top_area_height = card_y + card_height + content_gap

    total_height = top_area_height + total_rows * row_height + margin

    final_img = Image.new("RGBA", (img_width, total_height), (0, 0, 0, 0))

    card_start_x = margin * 2
    card_area_width = img_width - card_start_x * 2
    card_width = (card_area_width - card_gap_x * 3) // 4
    border_width = 14
    card_radius = 22

    card_data = [
        (_image_text("progress.completed", language), stats["achieved"], (76, 175, 80)),
        (_image_text("progress.incomplete", language), stats["unachieved"], (255, 152, 0)),
        (_image_text("progress.unplayed", language), stats["unplayed"], (158, 158, 158)),
        (_image_text("progress.total", language), stats["total"], (66, 133, 244)),
    ]

    final_img_rgba = final_img

    for idx, (label, count, color) in enumerate(card_data):
        card_x = card_start_x + idx * (card_width + card_gap_x)
        current_y = card_y

        card_layer = Image.new("RGBA", final_img_rgba.size, (0, 0, 0, 0))
        card_draw = ImageDraw.Draw(card_layer)

        shadow_offset = 3
        card_draw.rounded_rectangle(
            [card_x + shadow_offset, current_y + shadow_offset,
             card_x + card_width + shadow_offset, current_y + card_height + shadow_offset],
            radius=card_radius,
            fill=(0, 0, 0, 30)
        )

        r, g, b = color
        light_r = int(r + (255 - r) * 0.85)
        light_g = int(g + (255 - g) * 0.85)
        light_b = int(b + (255 - b) * 0.85)
        bg_color = (light_r, light_g, light_b, 255)

        card_draw.rounded_rectangle(
            [card_x, current_y, card_x + card_width, current_y + card_height],
            radius=card_radius,
            fill=bg_color
        )

        card_draw.rounded_rectangle(
            [card_x, current_y, card_x + border_width, current_y + card_height],
            radius=card_radius,
            fill=color + (255,)
        )

        final_img_rgba = Image.alpha_composite(final_img_rgba, card_layer)
        card_draw = ImageDraw.Draw(final_img_rgba)

        total = stats["total"]
        if idx < len(card_data) - 1 and total > 0:
            pct = count / total * 100
            data_text = f"{count} ({pct:.1f}%)"
        else:
            data_text = str(count)

        inner_x = card_x + border_width + 28
        inner_w = card_width - border_width - 56
        label_font = _fit_font_to_width(card_draw, label, inner_w, 54, 38)
        data_font = _fit_font_to_width(card_draw, data_text, inner_w, 66, 42)

        label_bbox = card_draw.textbbox((0, 0), label, font=label_font)
        data_bbox = card_draw.textbbox((0, 0), data_text, font=data_font)
        text_block_height = (label_bbox[3] - label_bbox[1]) + 8 + (data_bbox[3] - data_bbox[1])
        text_y = current_y + (card_height - text_block_height) // 2

        card_draw.text((inner_x, text_y - label_bbox[1]), label, fill=(72, 72, 72), font=label_font)
        data_y = text_y + (label_bbox[3] - label_bbox[1]) + 8
        card_draw.text((inner_x, data_y - data_bbox[1]), data_text, fill=(32, 32, 32), font=data_font)

    final_img = final_img_rgba
    draw = ImageDraw.Draw(final_img)

    # 绘制居中标题
    title_text_size = draw.textlength(title_text, font=title_font)
    title_x = (img_width - title_text_size) / 2
    draw.text((title_x, title_y - title_bbox[1]), title_text, fill=(255, 255, 255), font=title_font, stroke_width=3, stroke_fill=(50, 50, 50))

    # 渲染主体图像内容
    y_offset = top_area_height

    for level_str, entries_list in rows:
        _draw_level_label(draw, level_str, margin, y_offset, img_size, font_level_badge)

        x_offset = level_width + margin

        for i, entry in enumerate(entries_list):
            if i > 0 and i % max_per_row == 0:
                y_offset += row_height
                x_offset = level_width + margin

            cover_img = entry["img"]
            if cover_img.mode == "RGBA":
                final_img.paste(cover_img, (x_offset, y_offset), cover_img)
            else:
                final_img.paste(cover_img, (x_offset, y_offset))
            x_offset += img_size + margin

        y_offset += row_height

    return final_img
