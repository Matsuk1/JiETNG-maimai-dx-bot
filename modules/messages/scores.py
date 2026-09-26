"""LINE Flex messages for recognized score results and candidate carousels."""
from dataclasses import dataclass

from linebot.v3.messaging import FlexMessage, FlexContainer
from modules.i18n import get_user_language, localized_catalog, select_text
from modules.score_recognition.presentation import (
    COMBO_ICON_FILES,
    JUDGEMENT_ROWS,
    build_fix_command,
    calc_status,
    flex_combo_status as combo_status,
    difficulty_presentation,
    format_loss_percentage,
    nonnegative_count,
    flex_score_rank as score_rank,
)
from modules.messages.layout import (
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    body_row,
    flex_text,
    pill,
    section_title,
    metric_card,
    song_type_icon,
    standard_bubble,
)


def generate_score_recognition_flex(results, user_id=None):
    variants = list(results) if isinstance(results, (list, tuple)) else [results]
    if len(variants) <= 1:
        return _generate_score_recognition_single_flex(variants[0], user_id)

    bubbles = []
    alt_titles = []
    for variant in variants:
        message = _generate_score_recognition_single_flex(variant, user_id)
        bubbles.append(message.contents.to_dict())
        variant_validation = variant.get("validation") or {}
        title = variant_validation.get("title") or (variant.get("parsed") or {}).get("title")
        index = variant_validation.get("calc_completion_candidate_index")
        count = variant_validation.get("calc_completion_candidate_count")
        if index and count:
            alt_titles.append(f"{title or '-'} #{index}/{count}")
        else:
            alt_titles.append(str(title or "-"))

    return FlexMessage(
        alt_text=" / ".join(alt_titles[:3]),
        contents=FlexContainer.from_dict({
            "type": "carousel",
            "contents": bubbles,
        }),
    )


def _generate_score_recognition_single_flex(result, user_id=None):
    """Assemble independent score sections in their display order."""
    lang = get_user_language(user_id)
    texts = localized_catalog("message_manager.score_recognition")

    def tr(key):
        return select_text(texts[key], language=lang)

    data = _prepare_score(result)
    table_rows = _judgement_table(data.judgement, data.validation.get("uncertain_cells") or [])
    loss_rows = _normal_loss_rows(data.judgement, data.validation.get("loss_percentages") or {})
    body_contents = [
        _score_header(data, tr),
        {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                _achievement_metric_card(
                    data.achievement_text, score_rank(data.achievement),
                    combo_status(data.judgement, data.achievement), tr,
                ),
                metric_card(
                    tr("constant"),
                    data.constant_text,
                    value_color=data.difficulty_style["metric"],
                    flex=1,
                ),
            ],
        },
        section_title(tr("breakdown"), accent="#267D8B"),
    ]
    if len(table_rows) > 1:
        body_contents.append({
            "type": "box",
            "layout": "vertical",
            "spacing": "none",
            "cornerRadius": "8px",
            "backgroundColor": "#FFFFFF",
            "contents": table_rows,
        })
    else:
        body_contents.append(body_row(tr("empty")))

    if loss_rows:
        body_contents.extend([
            section_title(tr("loss_detail"), accent="#C0392B"),
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "paddingAll": "8px",
                "backgroundColor": "#F8FAFC",
                "cornerRadius": "6px",
                "contents": loss_rows,
            },
        ])

    body_contents.extend(_break_sections(data.validation.get("break_detail") or {}, tr))
    validation_sections, footer = _validation_sections(data, tr)
    body_contents.extend(validation_sections)
    bubble = standard_bubble(body_contents, "giga")
    if footer:
        bubble["footer"] = footer
    return FlexMessage(
        alt_text=f"{tr('title')}: {data.display_title}",
        contents=FlexContainer.from_dict(bubble),
    )


@dataclass(frozen=True, slots=True)
class _ScoreData:
    """Display values prepared once and shared by the score sections."""

    validation: dict
    judgement: dict
    song_title: str
    display_title: str
    achievement: object
    achievement_text: str
    constant_text: str
    difficulty_style: dict
    difficulty_label: str
    chart_type: object
    chart_metadata_confirmed: bool


def _prepare_score(result: dict) -> _ScoreData:
    parsed = result.get("parsed") or {}
    validation = result.get("validation") or {}
    calculation = validation.get("achievement_calc") or {}
    fully_validated = (
        bool(validation.get("song_id"))
        and calculation.get("consistent") is True
        and calculation.get("complete") is True
        and not validation.get("uncertain_cells")
    )
    if not fully_validated and "raw_parsed" in result:
        parsed = result["raw_parsed"]
        # Inferred chart details and cell coordinates describe corrected data,
        # so none of them belong in the raw OCR correction form.
        validation = {"achievement_calc": {"consistent": False, "complete": False}}

    judgement = parsed.get("sub_judgement") or {}
    canonical_title = parsed.get("title")
    if canonical_title is None:
        canonical_title = validation.get("title")
    if (
        validation.get("song_id")
        and not str(canonical_title or "").strip()
    ):
        song_title = '""'
    else:
        song_title = str(canonical_title or "-")
    achievement = parsed.get("achievement")
    achievement_text = f"{achievement:.4f}%" if isinstance(achievement, (int, float)) else "-"

    chart_metadata_confirmed = bool(
        validation.get(
            "chart_metadata_confirmed",
            not validation.get("inferred_note_count_rows"),
        )
    )
    difficulty = validation.get("difficulty") if chart_metadata_confirmed else None
    internal_level = validation.get("internal_level") if chart_metadata_confirmed else None
    chart_type = validation.get("type")
    chart_type_label = {
        "dx": "DX",
        "std": "STD",
        "utage": "UTAGE",
    }.get(str(chart_type or "").lower())
    display_title = (
        f"{song_title} [{chart_type_label}]"
        if chart_type_label else song_title
    )
    if isinstance(internal_level, (int, float)):
        internal_level_label = f"{internal_level:.1f}"
    else:
        internal_level_label = str(internal_level or "")
    constant_text = internal_level_label or "-"
    difficulty_style, difficulty_label = difficulty_presentation(difficulty)
    return _ScoreData(
        validation=validation,
        judgement=judgement,
        song_title=song_title,
        display_title=display_title,
        achievement=achievement,
        achievement_text=achievement_text,
        constant_text=constant_text,
        difficulty_style=difficulty_style,
        difficulty_label=difficulty_label,
        chart_type=chart_type,
        chart_metadata_confirmed=chart_metadata_confirmed,
    )


def _score_header(data: _ScoreData, tr):
    song_title = data.song_title
    difficulty_style = data.difficulty_style
    difficulty_label = (
        data.difficulty_label
        if data.chart_metadata_confirmed
        else tr("difficulty_undetermined")
    )
    chart_type = data.chart_type
    type_icon = song_type_icon(chart_type, width="50px", height="14px")
    subtitle_contents = [
        {
            "type": "text",
            "text": tr("title"),
            "size": "xs",
            "color": difficulty_style["text"],
            "weight": "bold",
            "wrap": False,
            "align": "start",
            "flex": 1,
        },
        (
            {
                "type": "text",
                "text": difficulty_label,
                "size": "xs",
                "color": difficulty_style["text"],
                "weight": "bold",
                "wrap": False,
                "align": "center",
                "flex": 1,
            }
            if data.chart_metadata_confirmed
            else {
                "type": "box",
                "layout": "vertical",
                "cornerRadius": "12px",
                "borderWidth": "1px",
                "borderColor": "#FFFFFF99",
                "paddingTop": "2px",
                "paddingBottom": "2px",
                "paddingStart": "8px",
                "paddingEnd": "8px",
                "flex": 1,
                "contents": [{
                    "type": "text",
                    "text": difficulty_label,
                    "size": "xxs",
                    "color": difficulty_style["text"],
                    "weight": "bold",
                    "wrap": False,
                    "align": "center",
                }],
            }
        ),
        {
            "type": "box",
            "layout": "horizontal",
            "justifyContent": "flex-end",
            "alignItems": "center",
            "flex": 1,
            "contents": [type_icon] if type_icon else [],
        },
    ]
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "paddingAll": "14px",
        "cornerRadius": "8px",
        "backgroundColor": difficulty_style["bg"],
        "contents": [
            {
                "type": "text",
                "text": song_title,
                "size": "lg",
                "color": difficulty_style["text"],
                "weight": "bold",
                "wrap": True,
            },
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "alignItems": "center",
                "margin": "xs",
                "contents": subtitle_contents,
            },
        ],
    }


def _judgement_table(judgement, uncertain_cells):
    uncertain_keys = {
        (item.get("row"), item.get("field"))
        for item in uncertain_cells
        if isinstance(item, dict)
    }
    uncertain_miss_rows = {
        item.get("row")
        for item in uncertain_cells
        if isinstance(item, dict)
    }
    missing_rows = {
        item.get("row")
        for item in uncertain_cells
        if isinstance(item, dict) and item.get("row_missing")
    }

    def judgement_cell(row_name, field_name, value, weight=None):
        uncertain = (
            (row_name, field_name) in uncertain_keys
            or (field_name == "miss" and row_name in uncertain_miss_rows)
            or row_name in missing_rows
        )
        return _table_cell(
            f"{value}?" if uncertain else value,
            color="#C0392B" if uncertain else _zero_count_color(value),
            weight="bold" if uncertain else weight,
        )

    table_rows = [{
        "type": "box",
        "layout": "horizontal",
        "spacing": "xs",
        "paddingAll": "8px",
        "backgroundColor": "#EEF1F5",
        "cornerRadius": "6px",
        "contents": [
            _table_cell("TYPE", flex=2, color=COLOR_TEXT_SECONDARY, weight="bold", align="start"),
            _table_cell("CP", color="#B86E19", weight="bold"),
            _table_cell("PF", color="#B86E19", weight="bold"),
            _table_cell("GR", color="#A33B75", weight="bold"),
            _table_cell("GD", color="#2F7D51", weight="bold"),
            _table_cell("MS", color="#555555", weight="bold"),
        ],
    }]

    for index, (key, label) in enumerate((
        ("tap", "TAP"),
        ("hold", "HOLD"),
        ("slide", "SLIDE"),
        ("touch", "TOUCH"),
        ("break", "BREAK"),
    )):
        row = judgement.get(key)
        row_missing = not isinstance(row, dict)
        if row_missing and key not in missing_rows:
            continue
        if row_missing:
            row = {}

        def row_value(field_name):
            return "-" if row_missing else row.get(field_name, 0)

        table_rows.append({
            "type": "box",
            "layout": "horizontal",
            "spacing": "xs",
            "paddingAll": "8px",
            "backgroundColor": "#F8FAFC" if index % 2 == 0 else "#FFFFFF",
            "contents": [
                _table_cell(label, flex=2, weight="bold", align="start"),
                judgement_cell(key, "critical_perfect", row_value("critical_perfect")),
                judgement_cell(key, "perfect", row_value("perfect")),
                judgement_cell(key, "great", row_value("great")),
                judgement_cell(key, "good", row_value("good")),
                judgement_cell(key, "miss", row_value("miss")),
            ],
        })

    if len(table_rows) > 1:
        table_rows[-1]["cornerRadius"] = "6px"

    return table_rows


def _normal_loss_rows(judgement, loss_percentages):
    loss_rows = []
    for key, label in (("tap", "TAP"), ("hold", "HOLD"), ("slide", "SLIDE"), ("touch", "TOUCH")):
        row = judgement.get(key)
        if not isinstance(row, dict):
            continue
        counts = {
            "great": nonnegative_count(row.get("great", 0)),
            "good": nonnegative_count(row.get("good", 0)),
            "miss": nonnegative_count(row.get("miss", 0)),
        }
        total_loss = sum(
            float(loss_percentages.get(f"{key}_{field}", 0) or 0) * count
            for field, count in counts.items()
        )
        if total_loss <= 0:
            continue
        loss_rows.append(_loss_detail_row(label, [
            _detail_value_box(
                format_loss_percentage(loss_percentages.get(f"{key}_great"), 1),
                counts["great"],
                "#923468",
                "#FBE5F1",
            ),
            _detail_value_box(
                format_loss_percentage(loss_percentages.get(f"{key}_good"), 1),
                counts["good"],
                "#277047",
                "#E7F5ED",
            ),
            _detail_value_box(
                format_loss_percentage(loss_percentages.get(f"{key}_miss"), 1),
                counts["miss"],
                "#555555",
                "#E9EDF2",
            ),
        ], format_loss_percentage(total_loss, 1)))

    return loss_rows


def _break_sections(break_detail, tr):
    if not break_detail:
        return []
    break_loss_percentages = break_detail.get("loss_percentages") or {}

    def break_loss_label(key):
        return format_loss_percentage(break_loss_percentages.get(key), 1)

    def break_loss_value(key):
        value = break_loss_percentages.get(key)
        return float(value) if isinstance(value, (int, float)) else 0.0

    break_total_loss = sum(
        break_loss_value(key) * nonnegative_count(break_detail.get(key))
        for key in ("perfect_high", "perfect_low", "great_high", "great_middle", "great_low", "good", "miss")
    )

    candidate_count = max(1, int(break_detail.get("candidate_count", 1) or 1))
    row_candidate_count = max(
        0,
        int(break_detail.get("row_candidate_count", 0) or 0),
    )
    if row_candidate_count > 1:
        source_text = tr("break_row_source_multiple").format(
            count=row_candidate_count,
        )
    elif candidate_count == 1:
        source_text = tr("break_detail_source_single")
    else:
        source_text = tr("break_detail_source_multiple").format(
            count=candidate_count,
        )

    return [
        section_title(tr("break_detail"), accent="#B86E19"),
        {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "8px",
            "backgroundColor": "#F8FAFC",
            "cornerRadius": "6px",
            "contents": [
                _detail_row("CRITICAL", [
                    _detail_value_box(
                        break_loss_label("critical_perfect"),
                        break_detail.get("critical_perfect", 0),
                        "#9A5B12",
                        "#FFF0C7",
                    ),
                ]),
                _detail_row("PERFECT", [
                    _detail_value_box(break_loss_label("perfect_high"), break_detail.get("perfect_high", 0), "#A96517", "#FFF3D9"),
                    _detail_value_box(break_loss_label("perfect_low"), break_detail.get("perfect_low", 0), "#B97824", "#FFF8E8"),
                ]),
                _detail_row("GREAT", [
                    _detail_value_box(break_loss_label("great_high"), break_detail.get("great_high", 0), "#923468", "#FBE5F1"),
                    _detail_value_box(break_loss_label("great_middle"), break_detail.get("great_middle", 0), "#A64D7D", "#F9EDF4"),
                    _detail_value_box(break_loss_label("great_low"), break_detail.get("great_low", 0), "#B66A91", "#F8F2F6"),
                ]),
                _detail_row("OTHER", [
                    _detail_value_box(break_loss_label("good"), break_detail.get("good", 0), "#277047", "#E7F5ED"),
                    _detail_value_box(break_loss_label("miss"), break_detail.get("miss", 0), "#555555", "#E9EDF2"),
                ]),
                _loss_total_box(format_loss_percentage(break_total_loss, 1)),
            ],
        },
        {
            "type": "text",
            "text": source_text,
            "size": "xxs",
            "color": COLOR_TEXT_MUTED,
            "wrap": True,
            "align": "start",
        },
    ]


def _validation_sections(data: _ScoreData, tr):
    validation = data.validation
    judgement = data.judgement
    song_title = data.song_title
    achievement = data.achievement
    uncertain_cells = validation.get("uncertain_cells") or []
    body_contents = []
    if validation.get("miss_corrections"):
        body_contents.append({
            "type": "text",
            "text": tr("validated"),
            "size": "xxs",
            "color": COLOR_TEXT_MUTED,
            "wrap": True,
            "align": "end",
        })

    achievement_calc = validation.get("achievement_calc") or {}
    calc_result, break_row_inferred = calc_status(validation, uncertain_cells, tr)
    if calc_result:
        calc_text, calc_consistent = calc_result
        body_contents.append({
            "type": "text",
            "text": calc_text,
            "size": "xxs",
            "color": COLOR_TEXT_MUTED if calc_consistent else "#C0392B",
            "wrap": True,
            "align": "end",
        })

    fully_validated = (
        bool(validation.get("song_id"))
        and achievement_calc.get("consistent") is True
        and achievement_calc.get("complete") is True
        and not uncertain_cells
    )
    has_judgement_data = any(
        isinstance(judgement.get(row_name), dict)
        for row_name in JUDGEMENT_ROWS
    )
    fix_command = (
        build_fix_command(judgement, song_title, achievement)
        if has_judgement_data else None
    )
    if not fully_validated and has_judgement_data:
        body_contents.extend([
            section_title(tr("manual_fix"), accent="#315B7D"),
            {
                "type": "text",
                "text": tr("manual_fix_hint"),
                "size": "xxs",
                "color": COLOR_TEXT_MUTED,
                "wrap": True,
            },
            {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "10px",
                "backgroundColor": "#F8FAFC",
                "cornerRadius": "6px",
                "contents": [{
                    "type": "text",
                    "text": fix_command,
                    "size": "xxs",
                    "color": COLOR_TEXT_PRIMARY,
                    "wrap": True,
                }],
            },
        ])

    footer = None
    if fix_command:
        fix_label = tr("compact_fix" if break_row_inferred and fully_validated else "copy_fix")
        fix_pill = pill(
            fix_label,
            color="#B66A00",
            bg_color="#FFF4E6",
        )
        fix_pill["action"] = {
            "type": "clipboard",
            "label": "fix-rcd",
            "clipboardText": fix_command,
        }
        footer = {
            "type": "box",
            "layout": "horizontal",
            "paddingTop": "2px",
            "paddingBottom": "10px",
            "paddingStart": "16px",
            "paddingEnd": "16px",
            "contents": [
                {"type": "filler"},
                fix_pill,
                {"type": "filler"},
            ],
        }
    return body_contents, footer


def _table_cell(text, flex=1, color=COLOR_TEXT_PRIMARY, weight=None, align="center"):
    node = {
        "type": "text",
        "text": str(text),
        "size": "xxs",
        "color": color,
        "align": align,
        "flex": flex,
        "wrap": False,
    }
    if weight:
        node["weight"] = weight
    return node


def _zero_count_color(value, default_color=COLOR_TEXT_PRIMARY):
    try:
        return COLOR_TEXT_MUTED if int(value) == 0 else default_color
    except (TypeError, ValueError):
        return default_color


def _playlog_icon_box(url, width, height, aspect_ratio, margin=None):
    icon_box = {
        "type": "box",
        "layout": "vertical",
        "width": width,
        "height": height,
        "flex": 0,
        "justifyContent": "center",
        "alignItems": "center",
        "gravity": "center",
        "contents": [{
            "type": "image",
            "url": url,
            "size": "full",
            "aspectMode": "fit",
            "aspectRatio": aspect_ratio,
        }],
    }
    if margin:
        icon_box["margin"] = margin
    return icon_box


def _playlog_inline_icon_box(url, width, height, aspect_ratio, margin=None):
    icon_box = {
        "type": "box",
        "layout": "vertical",
        "height": "32px",
        "flex": 0,
        "justifyContent": "flex-end",
        "alignItems": "center",
        "contents": [
            _playlog_icon_box(url, width, height, aspect_ratio),
        ],
    }
    if margin:
        icon_box["margin"] = margin
    return icon_box


def _achievement_metric_card(achievement_text, score_rank_name, combo_icon, tr):
    value_contents = [
        {
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "flex": 1,
            "contents": [
                flex_text(tr("status"), size="xxs", color=COLOR_TEXT_MUTED),
                flex_text(achievement_text, size="sm", color="#B86E19", weight="bold"),
            ],
        }
    ]
    if score_rank_name:
        rank_file = f"{score_rank_name.replace('p', 'plus')}.png"
        value_contents.append(_playlog_inline_icon_box(
            f"https://maimaidx.jp/maimai-mobile/img/playlog/{rank_file}",
            "58px",
            "28px",
            "203:90",
        ))
    if combo_icon:
        value_contents.append(_playlog_inline_icon_box(
            (
                "https://maimaidx.jp/maimai-mobile/img/playlog/"
                f"{COMBO_ICON_FILES[combo_icon]}"
            ),
            "59px",
            "28px",
            "64:28",
            margin="md",
        ))
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "alignItems": "center",
        "paddingAll": "11px",
        "cornerRadius": "8px",
        "backgroundColor": "#F8FAFC",
        "flex": 4,
        "contents": value_contents,
    }


def _detail_value_box(label, value, text_color, background_color):
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "paddingAll": "6px",
        "backgroundColor": background_color,
        "cornerRadius": "4px",
        "flex": 1,
        "contents": [
            {
                "type": "text",
                "text": str(label),
                "size": "xxs",
                "color": COLOR_TEXT_SECONDARY,
                "align": "center",
                "wrap": False,
            },
            {
                "type": "text",
                "text": str(value),
                "size": "sm",
                "color": _zero_count_color(value, text_color),
                "weight": "bold",
                "align": "center",
                "wrap": False,
            },
        ],
    }


def _detail_row(label, values, values_flex=5):
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "contents": [
            {
                "type": "text",
                "text": label,
                "size": "xxs",
                "color": COLOR_TEXT_PRIMARY,
                "weight": "bold",
                "flex": 2,
                "gravity": "center",
                "wrap": False,
            },
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "flex": values_flex,
                "contents": values,
            },
        ],
    }


def _loss_total_box(total_loss_text):
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "paddingAll": "6px",
        "backgroundColor": "#FDEDEC",
        "cornerRadius": "4px",
        "contents": [
            {
                "type": "text",
                "text": "TOTAL",
                "size": "xxs",
                "color": COLOR_TEXT_SECONDARY,
                "weight": "bold",
                "flex": 1,
                "wrap": False,
            },
            {
                "type": "text",
                "text": total_loss_text,
                "size": "sm",
                "color": "#C0392B",
                "weight": "bold",
                "align": "end",
                "flex": 1,
                "wrap": False,
            },
        ],
    }


def _loss_detail_row(label, values, total_loss_text):
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "contents": [
            {
                "type": "text",
                "text": label,
                "size": "xxs",
                "color": COLOR_TEXT_PRIMARY,
                "weight": "bold",
                "flex": 2,
                "gravity": "center",
                "wrap": False,
            },
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "flex": 6,
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "sm",
                        "contents": values,
                    },
                    _loss_total_box(total_loss_text),
                ],
            },
        ],
    }
