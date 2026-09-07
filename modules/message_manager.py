from urllib.parse import quote
from modules.config_loader import SUPPORT_PAGE, LINE_ACCOUNT_ID
from modules.i18n import (
    format_catalog,
    get_user_language,
    language_catalog,
    language_label,
    localized_catalog,
    select_text,
)
from modules.user_db import get_user
from modules.user_manager import get_user_timezone
from modules.tip_ad_manager import get_random_tip, get_random_ad
from modules.score_recognition_presenter import (
    COMBO_ICON_FILES,
    JUDGEMENT_ROWS,
    build_fix_command,
    calc_status,
    combo_status,
    difficulty_presentation,
    format_loss_percentage,
    nonnegative_count,
    score_rank,
)
from modules.message_texts import (
    access_error_text,
    calc_button_text,
    calc_flex_text,
    cannot_do_for_others_text,
    dxdata_current_stats_text,
    dxdata_fetch_failed_text,
    dxdata_first_update_text,
    dxdata_initial_stats_sheets_text,
    dxdata_initial_stats_songs_text,
    dxdata_last_update_text,
    dxdata_new_sheets_text,
    dxdata_new_songs_text,
    dxdata_no_new_sheets_text,
    dxdata_no_new_songs_text,
    dxdata_parse_failed_text,
    dxdata_sheets_decreased_text,
    dxdata_songs_decreased_text,
    dxdata_update_success_text,
    export_alt_text,
    export_flex_button_text,
    export_flex_copy_button_text,
    export_flex_footnote_text,
    export_flex_summary_text,
    export_flex_title_text,
    friend_error_text,
    friend_list_alt_text,
    friend_rcd_error_text,
    group_welcome_msg_text,
    info_error_text,
    input_error_text,
    level_not_supported_text,
    level_record_not_found_text,
    level_record_page_hint_text,
    maintenance_error_text,
    mention_error_text,
    mention_not_allowed_text,
    mention_no_matching_data_text,
    mention_record_error_text,
    nearby_stores_alt_text,
    no_matching_data_text,
    notice_header_text,
    plate_error_text,
    ranking_alt_text,
    ranking_title_text,
    rate_limit_msg_text,
    rebind_button_text,
    rebind_description_text,
    rebind_msg_text,
    rebind_title_alt_text,
    record_error_text,
    sega_bind_alt_text,
    sega_bind_button_text,
    sega_bind_description_text,
    sega_bind_title_text,
    segaid_error_text,
    settings_button_text,
    settings_description_text,
    settings_title_alt_text,
    song_error_text,
    song_info_alt_text,
    song_record_alt_text,
    store_error_text,
    system_error_text,
    unbind_button_text,
    unbind_description_text,
    unbind_title_alt_text,
    update_result_flex_text,
    user_info_flex_text,
    version_error_text,
    view_info_button_text,
    view_record_button_text,
    welcome_msg_text,
)
from linebot.v3.messaging import (
    TextMessage,
    FlexMessage,
    FlexContainer,
)

def format_timezone_string(user_id):
    """
    格式化用户时区字符串

    Args:
        user_id: 用户ID

    Returns:
        str: 格式化的时区字符串，如 "(UTC+9)"
    """
    tz_offset = get_user_timezone(user_id)
    tz_sign = '+' if tz_offset >= 0 else ''
    return f"(UTC{tz_sign}{tz_offset})"

get_multilingual_text = select_text

COLOR_TEXT_PRIMARY = "#111111"
COLOR_TEXT_SECONDARY = "#666666"
COLOR_TEXT_MUTED = "#999999"
COLOR_TEXT_INVERSE = "#FFFFFF"
COLOR_SUCCESS = "#17B169"
COLOR_DANGER = "#FF3B30"
COLOR_WARNING = "#FF9500"
COLOR_BRAND = "#FF6B35"
COLOR_TIP = "#5856D6"
COLOR_TIP_BG = "#F0EFFF"
COLOR_AD_BG = "#FFF4E6"

HELP_UI_TEXT = localized_catalog("message_manager.help_ui")

HELP_NOTE_DETAIL_LABELS = {
    "限制", "Restriction", "制限",
    "要求", "Requirement", "条件",
    "输出", "Output", "出力",
    "可设置", "Available settings", "設定項目",
}


def _help_ui(key, user_id=None):
    return get_multilingual_text(HELP_UI_TEXT[key], user_id)


def _help_i18n(user_id, key):
    return get_multilingual_text(
        language_catalog(f"message_manager.help_details.{key}"),
        user_id,
    )


def _help_flex_text(text, size="sm", color="#222222", weight=None, wrap=True, margin=None, align=None):
    node = {
        "type": "text",
        "text": text,
        "size": size,
        "color": color,
        "wrap": wrap,
    }
    if weight:
        node["weight"] = weight
    if margin:
        node["margin"] = margin
    if align:
        node["align"] = align
    return node


def _help_pill(text, color="#315B7D", bg_color="#EAF4FF"):
    return {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": bg_color,
        "cornerRadius": "12px",
        "paddingTop": "3px",
        "paddingBottom": "3px",
        "paddingStart": "8px",
        "paddingEnd": "8px",
        "contents": [
            _help_flex_text(text, size="xxs", color=color, weight="bold", align="center", wrap=False)
        ],
    }


def _help_section_title(title, accent="#FF7A45"):
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "alignItems": "center",
        "margin": "lg",
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "width": "4px",
                "height": "18px",
                "cornerRadius": "2px",
                "backgroundColor": accent,
                "contents": [{"type": "filler"}],
            },
            _help_flex_text(title, size="sm", color="#111111", weight="bold"),
        ],
    }


def _help_mode_card(title, body, accent):
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "paddingAll": "10px",
        "cornerRadius": "8px",
        "borderWidth": "1px",
        "borderColor": "#E6E8EC",
        "contents": [
            _help_flex_text(title, size="xs", color=accent, weight="bold"),
            _help_flex_text(body, size="xxs", color="#555555"),
        ],
    }


def _help_postback_button(label, data, color="#315B7D", display_text=None):
    action = {
        "type": "postback",
        "label": label,
        "data": data,
    }
    if display_text:
        action["displayText"] = display_text
    return {
        "type": "box",
        "layout": "vertical",
        "height": "32px",
        "cornerRadius": "16px",
        "backgroundColor": color,
        "justifyContent": "center",
        "alignItems": "center",
        "paddingStart": "12px",
        "paddingEnd": "12px",
        "action": action,
        "contents": [
            _help_flex_text(label, size="xxs", color="#FFFFFF", weight="bold", align="center", wrap=False),
        ],
    }


def _help_directory_card(title, desc, commands, action_data, accent):
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "paddingAll": "10px",
        "cornerRadius": "8px",
        "borderWidth": "1px",
        "borderColor": "#E6E8EC",
        "alignItems": "center",
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "flex": 1,
                "contents": [
                    node
                    for node in (
                        _help_flex_text(title, size="xs", color=accent, weight="bold"),
                        _help_flex_text(desc, size="xxs", color="#555555"),
                        _help_flex_text(commands, size="xxs", color="#6B7280") if commands else None,
                    )
                    if node is not None
                ],
            },
            {
                "type": "box",
                "layout": "vertical",
                "width": "86px",
                "contents": [
                    _help_postback_button("HELP", action_data, accent),
                ],
            },
        ],
    }


def _help_filter_row(label, desc, example=None):
    contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                _help_pill(label, color="#C93D47", bg_color="#FFF0F1"),
            ],
        },
        _help_flex_text(desc, size="xxs", color="#555555", margin="xs"),
    ]
    if example:
        contents.append({
            "type": "box",
            "layout": "vertical",
            "margin": "xs",
            "paddingAll": "7px",
            "cornerRadius": "6px",
            "backgroundColor": "#F7F8FA",
            "contents": [
                _help_flex_text(example, size="xxs", color="#222222"),
            ],
        })
    return {
        "type": "box",
        "layout": "vertical",
        "paddingBottom": "8px",
        "contents": contents,
    }


def _help_note_row(label, desc):
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "paddingAll": "9px",
        "cornerRadius": "8px",
        "backgroundColor": "#F8FAFC",
        "contents": [
            _help_flex_text(label, size="xs", color="#315B7D", weight="bold"),
            _help_flex_text(desc, size="xxs", color="#555555"),
        ],
    }


def _help_body_row(desc):
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "paddingAll": "9px",
        "cornerRadius": "8px",
        "backgroundColor": "#F8FAFC",
        "contents": [
            _help_flex_text(desc, size="xxs", color="#555555"),
        ],
    }


def _help_docs_footer(user_id=None):
    label = _help_ui("docs_button", user_id)
    support_page_uri = f"{SUPPORT_PAGE}{'&' if '?' in SUPPORT_PAGE else '?'}openExternalBrowser=1"
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "paddingAll": "12px",
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "height": "38px",
                "cornerRadius": "19px",
                "backgroundColor": "#FF7A45",
                "justifyContent": "center",
                "alignItems": "center",
                "paddingStart": "16px",
                "paddingEnd": "16px",
                "action": {
                    "type": "uri",
                    "label": label,
                    "uri": support_page_uri,
                },
                "contents": [
                    _help_flex_text(label, size="sm", color="#FFFFFF", weight="bold", align="center", wrap=False),
                ],
            }
        ],
    }


def _standard_help_bubble(title, subtitle, sections, alt_text, user_id=None, docs_button=True):
    body_contents = [
        _standard_header_box(title, subtitle),
    ]
    for title, rows in sections:
        body_contents.append(_help_section_title(title))
        body_contents.append({
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": rows,
        })
    bubble = {
        "type": "bubble",
        "size": "giga",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": "16px",
            "contents": body_contents,
        },
    }
    if docs_button:
        bubble["footer"] = _help_docs_footer(user_id)
    return FlexMessage(
        alt_text=alt_text,
        contents=FlexContainer.from_dict(bubble),
    )


def _standard_header_box(title, subtitle=None, accent="#111827", title_color="#FFFFFF"):
    contents = [
        _help_flex_text(title, size="lg", color=title_color, weight="bold"),
    ]
    if subtitle:
        contents.append(_help_flex_text(subtitle, size="xs", color="#D1D5DB", margin="xs"))
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "paddingAll": "14px",
        "cornerRadius": "8px",
        "backgroundColor": accent,
        "contents": contents,
    }


def _song_type_icon(chart_type, width="42px", height="12px", margin=None):
    normalized = str(chart_type or "").lower()
    if normalized == "std":
        url = "https://maimaidx.jp/maimai-mobile/img/music_standard.png"
    elif normalized == "dx":
        url = "https://maimaidx.jp/maimai-mobile/img/music_dx.png"
    elif normalized == "utage":
        url = "https://maimaidx.jp/maimai-mobile/img/diff_utage.png"
    else:
        return None
    icon = {
        "type": "box",
        "layout": "vertical",
        "width": width,
        "height": height,
        "flex": 0,
        "justifyContent": "center",
        "alignItems": "center",
        "contents": [{
            "type": "image",
            "url": url,
            "size": "full",
            "aspectMode": "fit",
            "aspectRatio": "113:32",
        }],
    }
    if margin:
        icon["margin"] = margin
    return icon


def _metric_card(label, value, value_color=COLOR_TEXT_PRIMARY, bg_color="#F8FAFC", flex=None):
    card = {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "paddingAll": "11px",
        "cornerRadius": "8px",
        "backgroundColor": bg_color,
        "contents": [
            _help_flex_text(label, size="xxs", color=COLOR_TEXT_MUTED),
            _help_flex_text(str(value), size="sm", color=value_color, weight="bold"),
        ],
    }
    if flex is not None:
        card["flex"] = flex
    return card


def _metric_grid(cards):
    rows = []
    for i in range(0, len(cards), 2):
        row_cards = cards[i:i + 2]
        if len(row_cards) == 1:
            row_cards.append({"type": "filler"})
        rows.append({
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": row_cards,
        })
    return rows


def _flex_action_button(label, action, style="primary", color=COLOR_BRAND):
    button = {
        "type": "button",
        "height": "sm",
        "style": style,
        "action": action,
    }
    if style == "primary":
        button["color"] = color
    return button


def _pill_action_box(label, action, bg_color="#315B7D", text_color=COLOR_TEXT_INVERSE,
                     flex=1, margin=None):
    box = {
        "type": "box",
        "layout": "vertical",
        "flex": flex,
        "cornerRadius": "999px",
        "backgroundColor": bg_color,
        "paddingAll": "0px",
        "justifyContent": "center",
        "alignItems": "center",
        "contents": [
            {
                "type": "button",
                "style": "link",
                "height": "sm",
                "color": text_color,
                "action": {
                    **action,
                    "label": label,
                },
            }
        ],
    }
    if margin:
        box["margin"] = margin
    return box


def _round_icon_action(label, action, bg_color="#315B7D", text_color=COLOR_TEXT_INVERSE):
    return {
        "type": "box",
        "layout": "vertical",
        "flex": 0,
        "width": "34px",
        "height": "34px",
        "cornerRadius": "17px",
        "backgroundColor": bg_color,
        "justifyContent": "center",
        "alignItems": "center",
        "action": {
            **action,
            "label": label,
        },
        "contents": [
            _help_flex_text(label, size="md", color=text_color, weight="bold", align="center", wrap=False),
        ],
    }


def _standard_action_bubble(title, subtitle, body_text, alt_text, actions=None, note_text=None,
                            accent=COLOR_BRAND, user_id=None):
    sections = [
        (_help_ui("function", user_id), [
            _help_body_row(body_text)
        ])
    ]
    if note_text:
        sections.append((_help_ui("notes", user_id), [
            _help_body_row(note_text)
        ]))

    body_contents = [
        _standard_header_box(title, subtitle),
    ]
    for section_title, rows in sections:
        body_contents.append(_help_section_title(section_title, accent=accent))
        body_contents.append({
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": rows,
        })

    bubble = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": "16px",
            "contents": body_contents,
        },
    }
    if actions:
        bubble["footer"] = {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "12px",
            "contents": actions,
        }
    return FlexMessage(alt_text=alt_text, contents=FlexContainer.from_dict(bubble))


def generate_status_flex(title_text, body_text, user_id=None, alt_text=None, tone="info"):
    accent_by_tone = {
        "info": "#315B7D",
        "warning": COLOR_WARNING,
        "danger": COLOR_DANGER,
        "success": COLOR_SUCCESS,
    }
    title = get_multilingual_text(title_text, user_id)
    body = get_multilingual_text(body_text, user_id)
    alt = get_multilingual_text(alt_text, user_id) if alt_text is not None else title
    return _standard_action_bubble(
        title=title,
        subtitle="JiETNG",
        body_text=body,
        alt_text=alt,
        accent=accent_by_tone.get(tone, "#315B7D"),
        user_id=user_id,
    )


def generate_account_action_flex(action_type, url, user_id=None):
    configs = {
        "bind": {
            "title": sega_bind_title_text,
            "body": sega_bind_description_text,
            "button": sega_bind_button_text,
            "alt": sega_bind_alt_text,
            "accent": COLOR_BRAND,
        },
        "rebind": {
            "title": rebind_title_alt_text,
            "body": rebind_description_text,
            "button": rebind_button_text,
            "alt": rebind_title_alt_text,
            "accent": "#8A63D2",
        },
        "unbind": {
            "title": unbind_title_alt_text,
            "body": unbind_description_text,
            "button": unbind_button_text,
            "alt": unbind_title_alt_text,
            "accent": COLOR_DANGER,
        },
        "settings": {
            "title": settings_title_alt_text,
            "body": settings_description_text,
            "button": settings_button_text,
            "alt": settings_title_alt_text,
            "accent": "#315B7D",
        },
    }
    config = configs[action_type]
    title = get_multilingual_text(config["title"], user_id)
    body = get_multilingual_text(config["body"], user_id)
    button = get_multilingual_text(config["button"], user_id)
    alt = get_multilingual_text(config["alt"], user_id)
    return _standard_action_bubble(
        title=title,
        subtitle="JiETNG",
        body_text=body,
        alt_text=alt,
        actions=[
            _flex_action_button(button, {"type": "uri", "label": button, "uri": url}, color=config["accent"])
        ],
        accent=config["accent"],
        user_id=user_id,
    )


def generate_welcome_flex(user_id=None, bind_url=None, group=False):
    title = "JiETNG"
    body = group_welcome_msg_text if group else welcome_msg_text
    actions = None
    if bind_url:
        label = get_multilingual_text(sega_bind_button_text, user_id)
        actions = [
            _flex_action_button(label, {"type": "uri", "label": label, "uri": bind_url}, color=COLOR_BRAND)
        ]
    return _standard_action_bubble(
        title=title,
        subtitle="Maimai DX LINE Bot",
        body_text=body,
        alt_text=title,
        actions=actions,
        accent=COLOR_BRAND,
        user_id=user_id,
    )


def generate_export_flex(user_id, meta):
    size_kb = max(1, round(meta["size"] / 1024))
    fmt_label = meta["fmt"].upper()
    title = get_multilingual_text(export_flex_title_text, user_id)
    body = get_multilingual_text(export_flex_summary_text, user_id).format(
        best=meta["best_count"],
        recent=meta["recent_count"],
        fmt=fmt_label,
        size_kb=size_kb,
    )
    foot = get_multilingual_text(export_flex_footnote_text, user_id).format(ttl=meta["ttl_minutes"])
    btn = get_multilingual_text(export_flex_button_text, user_id)
    copy_btn = get_multilingual_text(export_flex_copy_button_text, user_id)
    alt = get_multilingual_text(export_alt_text, user_id)
    return _standard_action_bubble(
        title=title,
        subtitle=fmt_label,
        body_text=body,
        note_text=foot,
        alt_text=alt,
        actions=[
            _flex_action_button(btn, {"type": "uri", "label": btn, "uri": f"{meta['url']}?openExternalBrowser=1"}),
            _flex_action_button(
                copy_btn,
                {"type": "clipboard", "label": copy_btn, "clipboardText": meta["url"]},
                style="secondary",
            ),
        ],
        accent=COLOR_SUCCESS,
        user_id=user_id,
    )


def create_text_message(msg_text_dict, user_id=None):
    """
    生成多语言 TextMessage

    Args:
        msg_text_dict: 多语言消息字典
        user_id: 用户ID（可选）

    Returns:
        TextMessage: 多语言文本消息
    """
    text = get_multilingual_text(msg_text_dict, user_id)
    return TextMessage(text=text)


def _parse_plain_help(text):
    fields = {"命令": "", "说明": "", "参数": "", "示例": "", "注意": ""}
    current_key = None
    for raw_line in str(text or "").replace("`", "").strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matched = False
        for key in fields:
            prefix = f"{key}:"
            if line.startswith(prefix):
                fields[key] = line[len(prefix):].strip() or fields[key]
                current_key = key
                matched = True
                break
        if not matched and current_key:
            fields[current_key] = f"{fields[current_key]}\n{line}".strip()
    return fields


def _split_help_lines(text):
    if isinstance(text, (list, tuple)):
        return [str(line).strip() for line in text if str(line).strip()]
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _partition_help_detail_lines(text, note_labels):
    detail_lines = []
    note_lines = []
    for line in _split_help_lines(text):
        head, tail = line.split(":", 1) if ":" in line else ("", "")
        label = head.strip() if head.strip() and tail.strip() else None
        if label in note_labels:
            note_lines.append(line)
        else:
            detail_lines.append(line)
    return detail_lines, note_lines


def _help_detail_rows(text, fallback_label, none_text):
    lines = _split_help_lines(text)
    if not lines:
        return [_help_filter_row(fallback_label, none_text)] if fallback_label else [_help_body_row(none_text)]

    rows = []
    for line in lines:
        label = fallback_label
        desc = line
        if ":" in line:
            head, tail = line.split(":", 1)
            if head.strip() and tail.strip():
                label = head.strip()
                desc = tail.strip()
        rows.append(_help_filter_row(label, desc) if label else _help_body_row(desc))
    return rows


def generate_standard_help_flex(help_data, user_id=None):
    fields = get_multilingual_text(help_data, user_id) if isinstance(help_data, dict) else help_data
    if not isinstance(fields, dict):
        fields = _parse_plain_help(fields)
    command = fields.get("command") or fields.get("命令") or _help_ui("help_title", user_id)
    purpose = fields.get("purpose") or fields.get("说明")
    params = fields.get("params") or fields.get("参数")
    examples = fields.get("examples") or fields.get("示例")
    notes = fields.get("notes") or fields.get("注意")
    params, param_note_lines = _partition_help_detail_lines(params, HELP_NOTE_DETAIL_LABELS)
    note_lines = [*_split_help_lines(notes), *param_note_lines]
    none_text = _help_ui("none", user_id)
    sections = [
        (_help_ui("function", user_id), [
            _help_body_row(purpose or _help_ui("default_purpose", user_id))
        ]),
        (_help_ui("params", user_id), _help_detail_rows(params, _help_ui("params", user_id), none_text)),
        (_help_ui("examples", user_id), _help_detail_rows(examples, None, none_text)),
    ]
    if note_lines:
        sections.append((_help_ui("notes", user_id), _help_detail_rows(note_lines, None, none_text)))
    return _standard_help_bubble(
        title="\n".join(part.strip() for part in str(command or "").split("/") if part.strip()),
        subtitle=_help_ui("help_title", user_id),
        sections=sections,
        alt_text=f"{command} {_help_ui('help_title', user_id)}",
        user_id=user_id,
    )


def generate_b_records_help_flex(user_id=None):
    modes = [
        ("Best", _help_i18n(user_id, 'b50_best50_b40_best40_b35_best35_b15_best15'), "#E85D75"),
        ("All Best", _help_i18n(user_id, 'ab50_allb50_ab35_allb35'), "#8A63D2"),
        ("Special", _help_i18n(user_id, 'ap50_fdx50_r50_rct50_idlb50_s50_sun50'), "#267D8B"),
    ]
    filters = [
        ("-lv / -level", _help_i18n(user_id, 'level_or_constant_one_value_is_exact_two_values_are_a_range'), "-lv 13.6   /   -lv 14 14.9"),
        ("-diff / -difficulty", _help_i18n(user_id, 'difficulty_supports_bas_adv_exp_mas_rem_or_full_names_multiple_v'), "-diff mas rem"),
        ("-ra / -rating", _help_i18n(user_id, 'chart_rating_one_value_is_exact_two_values_are_a_range'), "-ra 320 360"),
        ("-scr / -score", _help_i18n(user_id, 'achievement_one_value_is_a_lower_bound_two_values_are_a_range'), "-scr 100.5   /   -scr 100 100.5"),
        ("-dx / -dxscore", _help_i18n(user_id, 'without_values_sort_by_dx_score_with_values_filter_dx_score_perc'), "-dx   /   -dx 95 100"),
        ("-star / -dxstar", _help_i18n(user_id, 'dx_stars_one_value_is_exact_two_values_are_a_range'), "-star 5"),
        ("-ver / -version", _help_i18n(user_id, 'version_names_multiple_values_are_allowed_is_treated_as_plus_and'), "-ver buddies prism+"),
        ("-type / -tp", _help_i18n(user_id, 'chart_type_supports_dx_and_std_multiple_values_are_allowed'), "-type dx"),
        ("-next / -nxt", _help_i18n(user_id, 'next_version_preview_using_the_next_rating_structure'), "-nxt"),
        ("-page / -pg", _help_i18n(user_id, 'page_number_starting_from_1'), "-page 2"),
        ("-times / -tm", _help_i18n(user_id, 'display_multiplier_capped_at_2_5'), "-times 2"),
    ]
    sections = [
        (_help_ui("usage", user_id), [
            _help_filter_row(_help_ui("command", user_id), "b50 / b40 / b35 / b15 / ab50 / ap50 / fdx50 / r50 / idlb50 / s50"),
        ]),
        (_help_ui("function", user_id), [
            _help_body_row(_help_i18n(user_id, 'generate_best_all_best_special_score_images_with_optional_filter')),
        ]),
        (_help_ui("modes", user_id), [
            _help_mode_card(title, body, color)
            for title, body, color in modes
        ]),
        (_help_ui("params", user_id), [
            _help_filter_row(label, desc, example)
            for label, desc, example in filters
        ]),
        (_help_ui("examples", user_id), [
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "paddingAll": "10px",
                "cornerRadius": "8px",
                "backgroundColor": "#F7F8FA",
                "contents": [
                    _help_flex_text("b50 -lv 14 14.9 -diff mas rem -scr 100.5", size="xxs", color="#111111"),
                    _help_flex_text("ab50 -ver buddies -type dx", size="xxs", color="#111111"),
                    _help_flex_text("r50 -page 2", size="xxs", color="#111111"),
                ],
            },
        ]),
        (_help_ui("notes", user_id), [
            _help_note_row(_help_i18n(user_id, 'data_required'), _help_i18n(user_id, 'requires_a_linked_account_with_maimai_update_completed_or_data_i')),
            _help_note_row(_help_i18n(user_id, 'querying_others'), _help_i18n(user_id, 'line_mentions_can_query_registered_users_self_only_commands_do_n')),
        ]),
    ]
    return _standard_help_bubble(
        title=_help_ui("b_title", user_id),
        subtitle=_help_ui("b_subtitle", user_id),
        sections=sections,
        alt_text=f"{_help_ui('b_title', user_id)} {_help_ui('help_title', user_id)}",
        user_id=user_id,
    )


HELP_DIRECTORY_CATEGORIES = [
    {
        "key": "account",
        "title_key": "account_and_system",
        "commands": "help / bind / rebind / settings / profile / unbind / update / export / status",
        "desc_key": "binding_settings_profile_sync_export_and_status",
        "color": "#E85D75",
        "items": [
            ("help", "help_index"),
            ("bind", "bind"),
            ("rebind", "rebind"),
            ("settings", "settings"),
            ("profile", "profile"),
            ("unbind", "unbind_prompt"),
            ("update", "maimai_update"),
            ("export", "export"),
            ("status", "status"),
        ],
    },
    {
        "key": "scores",
        "title_key": "score_images",
        "commands": "b50 / b40 / ab50 / ap50 / fdx50 / r50 / idlb50 / s50",
        "desc_key": "best_all_best_recent_and_special_score_images",
        "color": "#8A63D2",
        "items": [
            ("b50", "b_records"),
            ("b40", "b_records"),
            ("ab50", "b_records"),
            ("ap50", "b_records"),
            ("fdx50", "b_records"),
            ("r50", "b_records"),
            ("idlb50", "b_records"),
            ("s50", "b_records"),
        ],
    },
    {
        "key": "songs",
        "title_key": "songs_and_records",
        "commands": "info / rec / record",
        "desc_key": "song_details_score_image_recognition_single_song_records_and_son",
        "color": "#267D8B",
        "items": [
            ("info", "song_info"),
            ("rec", "score_recognition"),
            ("record", "song_record"),
        ],
    },
    {
        "key": "search",
        "title_key": "search",
        "commands": "artist / designer / bpm / random",
        "desc_key": "search_by_artist_designer_bpm_or_random_conditions",
        "color": "#2F7D51",
        "items": [
            ("artist", "search_by_artist"),
            ("designer", "search_by_designer"),
            ("bpm", "search_by_bpm"),
            ("random", "random_song"),
        ],
    },
    {
        "key": "lists",
        "title_key": "lists_and_progress",
        "commands": "records / levels / ver / plate / prog",
        "desc_key": "level_lists_constant_lists_plate_completion_and_target_progress",
        "color": "#B86E19",
        "items": [
            ("records", "level_records"),
            ("levels", "level_rank_list"),
            ("ver", "version_songs"),
            ("plate", "plate"),
            ("prog", "level_rank_progress"),
        ],
    },
    {
        "key": "social",
        "title_key": "social",
        "commands": "friends",
        "desc_key": "friend_list_and_friend_record_lookup",
        "color": "#315B7D",
        "items": [
            ("friends", "friend_list"),
        ],
    },
    {
        "key": "tools",
        "title_key": "tools",
        "commands": "rank / rc / calc / refreshmenu",
        "desc_key": "ranking_rating_breakdown_note_scoring_and_utility_commands",
        "color": "#6B7280",
        "items": [
            ("rank", "ranking"),
            ("rc", "rc"),
            ("calc", "calc_notes"),
            ("refreshmenu", "refreshmenu"),
        ],
    },
]

HELP_DIRECTORY_BY_KEY = {
    category["key"]: category
    for category in HELP_DIRECTORY_CATEGORIES
}


def _help_category_title(category, user_id):
    return _help_i18n(user_id, category["title_key"])


def _help_category_desc(category, user_id):
    return _help_i18n(user_id, category["desc_key"])


def _help_command_summary(help_key, category, user_id):
    if help_key == "b_records":
        return _help_i18n(user_id, "generate_best_all_best_special_score_images_with_optional_filter")
    help_data = localized_catalog("command_help").get(help_key)
    if not help_data:
        return _help_category_desc(category, user_id)
    fields = _parse_plain_help(get_multilingual_text(help_data, user_id))
    return fields.get("说明") or fields.get("function") or _help_category_desc(category, user_id)


def generate_help_index_flex(user_id=None):
    sections = [
        (_help_ui("categories", user_id), [
            _help_directory_card(
                _help_category_title(category, user_id),
                _help_category_desc(category, user_id),
                category["commands"],
                f"help {category['items'][0][1] if category['key'] == 'scores' or len(category['items']) == 1 else category['key']}",
                category["color"],
            )
            for category in HELP_DIRECTORY_CATEGORIES
        ]),
        (_help_ui("detail_hint", user_id), [
            _help_filter_row(_help_i18n(user_id, 'single_command'), _help_i18n(user_id, 'send_b50_help_artist_help_bpm_help_and_similar_forms_for_full_us')),
            _help_filter_row(_help_i18n(user_id, 'missing_arguments'), _help_i18n(user_id, 'commands_that_need_arguments_also_show_help_when_sent_without_ar')),
        ]),
    ]
    return _standard_help_bubble(
        title=_help_ui("catalog_title", user_id),
        subtitle=_help_ui("catalog_subtitle", user_id),
        sections=sections,
        alt_text=f"{_help_ui('catalog_title', user_id)}",
        user_id=user_id,
    )


def generate_help_category_flex(category_key, user_id=None):
    category = HELP_DIRECTORY_BY_KEY.get(category_key)
    if category is None:
        return None

    rows = [
        _help_directory_card(
            label,
            _help_command_summary(help_key, category, user_id),
            "",
            f"help {help_key}",
            category["color"],
        )
        for label, help_key in category["items"]
    ]
    sections = [
        (_help_ui("function", user_id), [
            _help_body_row(_help_category_desc(category, user_id)),
        ]),
        (_help_ui("command", user_id), rows),
    ]
    return _standard_help_bubble(
        title=_help_category_title(category, user_id),
        subtitle=_help_ui("catalog_title", user_id),
        sections=sections,
        alt_text=f"{_help_category_title(category, user_id)} {_help_ui('catalog_title', user_id)}",
        user_id=user_id,
    )


def _update_status_label(func_name, lang):
    status_text_keys = {
        "User Info": "status_user_info",
        "Best Records": "status_best_records",
        "Recent Records": "status_recent_records",
    }
    text_key = status_text_keys.get(func_name)
    if not text_key:
        return func_name
    return get_multilingual_text(update_result_flex_text[text_key], language=lang)

def _message_factory(message_text):
    def build_message(user_id=None):
        return create_text_message(message_text, user_id)

    return build_message


rebind_msg = _message_factory(rebind_msg_text)
segaid_error = _message_factory(segaid_error_text)
record_error = _message_factory(record_error_text)
info_error = _message_factory(info_error_text)
access_error = _message_factory(access_error_text)
system_error = _message_factory(system_error_text)
input_error = _message_factory(input_error_text)
song_error = _message_factory(song_error_text)
level_not_supported = _message_factory(level_not_supported_text)
plate_error = _message_factory(plate_error_text)
version_error = _message_factory(version_error_text)
store_error = _message_factory(store_error_text)
rate_limit_msg = _message_factory(rate_limit_msg_text)
maintenance_error = _message_factory(maintenance_error_text)
friend_error = _message_factory(friend_error_text)
friend_rcd_error = _message_factory(friend_rcd_error_text)
mention_error = _message_factory(mention_error_text)
mention_not_allowed = _message_factory(mention_not_allowed_text)
mention_record_error = _message_factory(mention_record_error_text)
cannot_do_for_others = _message_factory(cannot_do_for_others_text)
no_matching_data = _message_factory(no_matching_data_text)
mention_no_matching_data = _message_factory(mention_no_matching_data_text)

def level_record_not_found(level, page, user_id=None):
    """生成指定等级记录未找到消息"""
    text = get_multilingual_text(level_record_not_found_text, user_id).format(level=level, page=page)
    return TextMessage(text=text)

def level_record_page_hint(page, user_id=None):
    """生成等级记录页面提示消息"""
    text = get_multilingual_text(level_record_page_hint_text, user_id).format(page=page)
    return TextMessage(text=text)

def get_notice_header(user_id=None):
    """获取公告标题（多语言）"""
    return get_multilingual_text(notice_header_text, user_id)

def generate_notice_flex(notice_json, user_id=None):
    """
    生成公告 FlexMessage (支持多语言和投票)

    Args:
        notice_json: 公告数据 {"id": "...", "content": {...}, "date": "...", "voting_enabled": bool}
        user_id: 用户ID（用于多语言和投票状态）

    Returns:
        FlexMessage
    """
    # 获取用户语言
    lang = get_user_language(user_id)

    # 标题（多语言）
    title = get_notice_header(user_id)

    # 内容（根据用户语言）
    content_dict = notice_json.get('content', {})
    if isinstance(content_dict, str):
        # 向后兼容旧格式
        content = content_dict
    else:
        content = select_text(content_dict, language=lang, default_language='ja')

    date = notice_json.get('date', '')
    notice_id = notice_json.get('id', '')
    voting_enabled = notice_json.get('voting_enabled', False)

    # 基础body内容
    body_contents = [
        {
            "type": "text",
            "text": content,
            "wrap": True,
            "size": "sm",
            "color": "#333333",
            "margin": "none"
        }
    ]

    # 如果有自定义按钮，添加按钮卡片到body
    if 'button' in notice_json:
        button_info = notice_json['button']
        button_type = button_info.get('type', 'uri')
        button_label_dict = button_info.get('label', {})
        button_label = select_text(button_label_dict, language=lang, default_language='ja')
        button_value = button_info.get('value', '')

        # 如果label为空，使用默认值
        if not button_label:
            default_labels = localized_catalog("message_manager.button_labels")
            button_label = select_text(default_labels.get(button_type, {}), language=lang, default_language='ja') or 'Go'

        # 添加箭头到按钮标签
        button_label_with_arrow = f"{button_label} →"

        # 根据按钮类型创建action
        if button_type == 'uri':
            action = {
                "type": "uri",
                "label": button_label_with_arrow,
                "uri": button_value
            }
        else:  # message
            action = {
                "type": "message",
                "label": button_label_with_arrow,
                "text": button_value
            }

        # 添加按钮卡片
        button_box = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": action,
                    "style": "link",
                    "height": "sm",
                    "color": "#FF6B35"
                }
            ],
            "backgroundColor": "#FFF5F0",
            "cornerRadius": "md",
            "paddingAll": "12px",
            "margin": "md"
        }
        body_contents.append(button_box)

    # 基础bubble结构
    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": _standard_header_box(title, "JiETNG"),
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": body_contents,
            "paddingAll": "20px",
            "backgroundColor": "#FFFFFF"
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [],
            "paddingAll": "12px",
            "backgroundColor": "#F5F5F5"
        }
    }

    # 如果启用投票，添加投票按钮
    if voting_enabled and user_id:
        # 投票按钮文本
        vote_labels = localized_catalog("message_manager.vote_labels")

        support_label = select_text(vote_labels['support'], language=lang, default_language='ja')
        oppose_label = select_text(vote_labels['oppose'], language=lang, default_language='ja')

        # 如果已投票，标记选中状态
        support_style = "primary"
        oppose_style = "primary"
        support_color = "#17B169"
        oppose_color = "#FF3B30"

        # 添加投票按钮
        vote_buttons = {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "margin": "md",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": support_label,
                        "data": f"action=vote_notice&notice_id={notice_id}&vote=support"
                    },
                    "style": support_style,
                    "color": support_color,
                    "height": "sm"
                },
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": oppose_label,
                        "data": f"action=vote_notice&notice_id={notice_id}&vote=oppose"
                    },
                    "style": oppose_style,
                    "color": oppose_color,
                    "height": "sm"
                }
            ]
        }

        bubble['footer']['contents'].append(vote_buttons)
        bubble['footer']['contents'].append({
            "type": "separator",
            "margin": "md"
        })

    # 添加日期
    bubble['footer']['contents'].append({
        "type": "text",
        "text": date,
        "size": "xs",
        "color": "#999999",
        "align": "end"
    })

    return FlexMessage(
        alt_text=title,
        contents=FlexContainer.from_dict(bubble)
    )

def get_friend_list_alt_text(user_id=None):
    """获取好友列表 alt_text（多语言）"""
    return get_multilingual_text(friend_list_alt_text, user_id)

def get_nearby_stores_alt_text(user_id=None):
    """获取附近机厅列表 alt_text（多语言）"""
    return get_multilingual_text(nearby_stores_alt_text, user_id)


def generate_song_info_flex(song_id, image_url, image_width, image_height, user_id=None, mode='info'):
    """
    生成歌曲信息 Flex Message（图片 + 按钮合为一个 bubble）

    Args:
        song_id: 歌曲ID
        image_url: 歌曲信息图片 URL
        image_width: 图片宽度（px）
        image_height: 图片高度（px）
        user_id: 用户ID（用于多语言）
        mode: 'info'（歌曲信息模式，显示 calc + record 按钮）
              'record'（成绩模式，显示 info 按钮）

    Returns:
        FlexMessage
    """
    from math import gcd
    g = gcd(image_width, image_height)
    aspect_ratio = f"{image_width // g}:{image_height // g}"

    buttons = []

    if mode == 'info':
        calc_label = get_multilingual_text(calc_button_text, user_id)
        buttons.append(_pill_action_box(
            calc_label,
            {
                "type": "postback",
                "label": calc_label,
                "data": f"calc-song {song_id}"
            },
            bg_color=COLOR_BRAND,
        ))
        record_label = get_multilingual_text(view_record_button_text, user_id)
        buttons.append(_pill_action_box(
            record_label,
            {
                "type": "postback",
                "label": record_label,
                "data": f"search-record {song_id}"
            },
            bg_color="#315B7D",
        ))
    else:
        info_label = get_multilingual_text(view_info_button_text, user_id)
        buttons.append(_pill_action_box(
            info_label,
            {
                "type": "postback",
                "label": info_label,
                "data": f"search-song {song_id}"
            },
            bg_color="#315B7D",
        ))

    alt_text = get_multilingual_text(song_info_alt_text, user_id) if mode == 'info' else get_multilingual_text(song_record_alt_text, user_id)

    bubble = {
        "type": "bubble",
        "size": "mega",
        "hero": {
            "type": "image",
            "url": image_url,
            "action": {
                "type": "uri",
                "uri": image_url
            },
            "size": "full",
            "aspectRatio": aspect_ratio,
            "aspectMode": "fit"
        },
        "footer": {
            "type": "box",
            "layout": "horizontal" if len(buttons) > 1 else "vertical",
            "spacing": "sm",
            "contents": buttons,
            "paddingAll": "12px"
        }
    }

    return FlexMessage(
        alt_text=alt_text,
        contents=FlexContainer.from_dict(bubble)
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
    """Generate the judgement details shown after score-image recognition."""
    lang = get_user_language(user_id)
    texts = localized_catalog("message_manager.score_recognition")

    def tr(key):
        return select_text(texts[key], language=lang)

    def table_cell(text, flex=1, color=COLOR_TEXT_PRIMARY, weight=None, align="center"):
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

    def zero_count_color(value, default_color=COLOR_TEXT_PRIMARY):
        try:
            return COLOR_TEXT_MUTED if int(value) == 0 else default_color
        except (TypeError, ValueError):
            return default_color

    parsed = result.get("parsed") or {}
    validation = result.get("validation") or {}
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

    combo_icon = combo_status(judgement, achievement)
    score_rank_name = score_rank(achievement)

    def playlog_icon_box(url, width, height, aspect_ratio, margin=None):
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

    def playlog_inline_icon_box(url, width, height, aspect_ratio, margin=None):
        icon_box = {
            "type": "box",
            "layout": "vertical",
            "height": "32px",
            "flex": 0,
            "justifyContent": "flex-end",
            "alignItems": "center",
            "contents": [
                playlog_icon_box(url, width, height, aspect_ratio),
            ],
        }
        if margin:
            icon_box["margin"] = margin
        return icon_box

    def achievement_metric_card():
        value_contents = [
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "flex": 1,
                "contents": [
                    _help_flex_text(tr("status"), size="xxs", color=COLOR_TEXT_MUTED),
                    _help_flex_text(achievement_text, size="sm", color="#B86E19", weight="bold"),
                ],
            }
        ]
        if score_rank_name:
            rank_file = f"{score_rank_name.replace('p', 'plus')}.png"
            value_contents.append(playlog_inline_icon_box(
                f"https://maimaidx.jp/maimai-mobile/img/playlog/{rank_file}",
                "58px",
                "28px",
                "203:90",
            ))
        if combo_icon:
            value_contents.append(playlog_inline_icon_box(
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

    difficulty = validation.get("difficulty")
    internal_level = validation.get("internal_level")
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
    type_icon = _song_type_icon(chart_type, width="50px", height="14px")
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
        {
            "type": "text",
            "text": difficulty_label,
            "size": "xs",
            "color": difficulty_style["text"],
            "weight": "bold",
            "wrap": False,
            "align": "center",
            "flex": 1,
        },
        {
            "type": "box",
            "layout": "horizontal",
            "justifyContent": "flex-end",
            "alignItems": "center",
            "flex": 1,
            "contents": [type_icon] if type_icon else [],
        },
    ]
    score_header = {
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
    uncertain_cells = validation.get("uncertain_cells") or []
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
        return table_cell(
            f"{value}?" if uncertain else value,
            color="#C0392B" if uncertain else zero_count_color(value),
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
            table_cell("TYPE", flex=2, color=COLOR_TEXT_SECONDARY, weight="bold", align="start"),
            table_cell("CP", color="#B86E19", weight="bold"),
            table_cell("PF", color="#B86E19", weight="bold"),
            table_cell("GR", color="#A33B75", weight="bold"),
            table_cell("GD", color="#2F7D51", weight="bold"),
            table_cell("MS", color="#555555", weight="bold"),
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
                table_cell(label, flex=2, weight="bold", align="start"),
                judgement_cell(key, "critical_perfect", row_value("critical_perfect")),
                judgement_cell(key, "perfect", row_value("perfect")),
                judgement_cell(key, "great", row_value("great")),
                judgement_cell(key, "good", row_value("good")),
                judgement_cell(key, "miss", row_value("miss")),
            ],
        })

    if len(table_rows) > 1:
        table_rows[-1]["cornerRadius"] = "6px"

    loss_percentages = validation.get("loss_percentages") or {}

    def detail_value_box(label, value, text_color, background_color):
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
                    "color": zero_count_color(value, text_color),
                    "weight": "bold",
                    "align": "center",
                    "wrap": False,
                },
            ],
        }

    def detail_row(label, values, values_flex=5):
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

    def loss_detail_row(label, values, total_loss_text):
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
                        {
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
                        },
                    ],
                },
            ],
        }

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
        loss_rows.append(loss_detail_row(label, [
            detail_value_box(
                format_loss_percentage(loss_percentages.get(f"{key}_great"), 1),
                counts["great"],
                "#923468",
                "#FBE5F1",
            ),
            detail_value_box(
                format_loss_percentage(loss_percentages.get(f"{key}_good"), 1),
                counts["good"],
                "#277047",
                "#E7F5ED",
            ),
            detail_value_box(
                format_loss_percentage(loss_percentages.get(f"{key}_miss"), 1),
                counts["miss"],
                "#555555",
                "#E9EDF2",
            ),
        ], format_loss_percentage(total_loss, 1)))

    body_contents = [
        score_header,
        {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                achievement_metric_card(),
                _metric_card(
                    tr("constant"),
                    constant_text,
                    value_color=difficulty_style["metric"],
                    flex=1,
                ),
            ],
        },
        _help_section_title(tr("breakdown"), accent="#267D8B"),
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
        body_contents.append(_help_body_row(tr("empty")))

    if loss_rows:
        body_contents.extend([
            _help_section_title(tr("loss_detail"), accent="#C0392B"),
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

    break_detail = validation.get("break_detail") or {}
    if break_detail:
        break_loss_percentages = break_detail.get("loss_percentages") or {}

        def break_loss_label(key):
            return format_loss_percentage(break_loss_percentages.get(key), 1)

        def break_detail_row(label, values):
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
                        "flex": 5,
                        "contents": values,
                    },
                ],
            }

        def break_loss_value(key):
            value = break_loss_percentages.get(key)
            return float(value) if isinstance(value, (int, float)) else 0.0

        break_total_loss = sum((
            break_loss_value("perfect_high") * nonnegative_count(break_detail.get("perfect_high")),
            break_loss_value("perfect_low") * nonnegative_count(break_detail.get("perfect_low")),
            break_loss_value("great_high") * nonnegative_count(break_detail.get("great_high")),
            break_loss_value("great_middle") * nonnegative_count(break_detail.get("great_middle")),
            break_loss_value("great_low") * nonnegative_count(break_detail.get("great_low")),
            break_loss_value("good") * nonnegative_count(break_detail.get("good")),
            break_loss_value("miss") * nonnegative_count(break_detail.get("miss")),
        ))

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

        body_contents.extend([
            _help_section_title(tr("break_detail"), accent="#B86E19"),
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "paddingAll": "8px",
                "backgroundColor": "#F8FAFC",
                "cornerRadius": "6px",
                "contents": [
                    break_detail_row("CRITICAL", [
                        detail_value_box(
                            break_loss_label("critical_perfect"),
                            break_detail.get("critical_perfect", 0),
                            "#9A5B12",
                            "#FFF0C7",
                        ),
                    ]),
                    break_detail_row("PERFECT", [
                        detail_value_box(break_loss_label("perfect_high"), break_detail.get("perfect_high", 0), "#A96517", "#FFF3D9"),
                        detail_value_box(break_loss_label("perfect_low"), break_detail.get("perfect_low", 0), "#B97824", "#FFF8E8"),
                    ]),
                    break_detail_row("GREAT", [
                        detail_value_box(break_loss_label("great_high"), break_detail.get("great_high", 0), "#923468", "#FBE5F1"),
                        detail_value_box(break_loss_label("great_middle"), break_detail.get("great_middle", 0), "#A64D7D", "#F9EDF4"),
                        detail_value_box(break_loss_label("great_low"), break_detail.get("great_low", 0), "#B66A91", "#F8F2F6"),
                    ]),
                    break_detail_row("OTHER", [
                        detail_value_box(break_loss_label("good"), break_detail.get("good", 0), "#277047", "#E7F5ED"),
                        detail_value_box(break_loss_label("miss"), break_detail.get("miss", 0), "#555555", "#E9EDF2"),
                    ]),
                    {
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
                                "text": format_loss_percentage(break_total_loss, 1),
                                "size": "sm",
                                "color": "#C0392B",
                                "weight": "bold",
                                "align": "end",
                                "flex": 1,
                                "wrap": False,
                            },
                        ],
                    },
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
        ])

    if validation.get("miss_corrections"):
        body_contents.append({
            "type": "text",
            "text": tr("validated"),
            "size": "xxs",
            "color": COLOR_TEXT_MUTED,
            "wrap": True,
            "align": "end",
        })

    manual_fix_command = None
    compact_fix_command = None
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
    if break_row_inferred and fully_validated:
        compact_fix_command = fix_command
    elif not fully_validated and has_judgement_data:
        manual_fix_command = fix_command
        body_contents.extend([
            _help_section_title(tr("manual_fix"), accent="#315B7D"),
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
                    "text": manual_fix_command,
                    "size": "xxs",
                    "color": COLOR_TEXT_PRIMARY,
                    "wrap": True,
                }],
            },
        ])

    bubble = {
        "type": "bubble",
        "size": "giga",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": "16px",
            "contents": body_contents,
        },
    }
    footer_fix_command = manual_fix_command or compact_fix_command or fix_command
    if footer_fix_command:
        fix_label = tr("compact_fix") if compact_fix_command and not manual_fix_command else tr("copy_fix")
        fix_pill = _help_pill(
            fix_label,
            color="#B66A00",
            bg_color="#FFF4E6",
        )
        fix_pill["action"] = {
            "type": "clipboard",
            "label": "fix-rcd",
            "clipboardText": footer_fix_command,
        }
        bubble["footer"] = {
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
    return FlexMessage(
        alt_text=f"{tr('title')}: {display_title}",
        contents=FlexContainer.from_dict(bubble),
    )


def build_dxdata_update_message(result, user_id=None):
    """
    构建 Dxdata 更新消息（多语言）

    Args:
        result: update_dxdata_with_comparison 返回的结果字典
        user_id: 用户ID（用于确定语言）

    Returns:
        str: 多语言更新消息
    """
    if not result.get('success'):
        # 更新失败
        if 'message' in result:
            # 如果已经有消息，判断是什么类型的错误
            if 'データ取得失敗' in result['message'] or 'fetch' in result['message'].lower():
                return get_multilingual_text(dxdata_fetch_failed_text, user_id)
            else:
                return get_multilingual_text(dxdata_parse_failed_text, user_id)
        return get_multilingual_text(dxdata_fetch_failed_text, user_id)

    message_parts = []

    # 标题
    message_parts.append(get_multilingual_text(dxdata_update_success_text, user_id))
    message_parts.append('')

    if result.get('old_stats'):
        # 有历史数据，显示对比
        diff = result.get('diff', {})
        songs_diff = diff.get('songs_added', 0)
        sheets_diff = diff.get('sheets_added', 0)

        # 新曲变化
        if songs_diff > 0:
            message_parts.append(get_multilingual_text(dxdata_new_songs_text, user_id).format(count=songs_diff))
        elif songs_diff < 0:
            message_parts.append(get_multilingual_text(dxdata_songs_decreased_text, user_id).format(count=songs_diff))
        else:
            message_parts.append(get_multilingual_text(dxdata_no_new_songs_text, user_id))

        # 新谱面变化
        if sheets_diff > 0:
            message_parts.append(get_multilingual_text(dxdata_new_sheets_text, user_id).format(count=sheets_diff))
        elif sheets_diff < 0:
            message_parts.append(get_multilingual_text(dxdata_sheets_decreased_text, user_id).format(count=sheets_diff))
        else:
            message_parts.append(get_multilingual_text(dxdata_no_new_sheets_text, user_id))

        # 上次更新时间
        message_parts.append('')
        message_parts.append(get_multilingual_text(dxdata_last_update_text, user_id).format(
            timestamp=result['old_stats']['timestamp']
        ))

        # 当前统计
        new_stats = result['new_stats']
        message_parts.append(get_multilingual_text(dxdata_current_stats_text, user_id).format(
            songs=new_stats['total_songs'],
            sheets=new_stats['total_sheets']
        ))
    else:
        # 首次更新
        new_stats = result['new_stats']
        message_parts.append(get_multilingual_text(dxdata_initial_stats_songs_text, user_id).format(
            count=new_stats['total_songs']
        ))
        message_parts.append(get_multilingual_text(dxdata_initial_stats_sheets_text, user_id).format(
            count=new_stats['total_sheets']
        ))
        message_parts.append('')
        message_parts.append(get_multilingual_text(dxdata_first_update_text, user_id))

    return '\n'.join(message_parts)

# ============================================================
# 用户信息 Flex Message / User Info Flex Message
# ============================================================


def generate_user_info_flex(user_id):
    """
    生成用户信息 Flex Message

    Args:
        user_id: 用户ID

    Returns:
        FlexMessage: 用户信息 Flex Message
    """
    lang = get_user_language(user_id)
    texts = user_info_flex_text
    user_data = get_user(user_id)

    def _info_row(label, value, action=None, value_color=COLOR_TEXT_PRIMARY, sub_value=None):
        value_contents = [
            _help_flex_text(label, size="xxs", color=COLOR_TEXT_MUTED),
            _help_flex_text(str(value), size="sm", color=value_color, weight="bold"),
        ]
        if sub_value:
            value_contents.append(_help_flex_text(str(sub_value), size="xxs", color=COLOR_TEXT_MUTED, margin="xs"))
        value_block = {
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "contents": value_contents,
        }
        contents = [value_block]
        if action:
            copy_pill = _help_pill(
                action.get("label", ""),
                color="#B66A00",
                bg_color="#FFF4E6",
            )
            copy_pill["margin"] = "sm"
            copy_pill["action"] = action
            contents.append(copy_pill)
        return {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "10px",
            "cornerRadius": "8px",
            "backgroundColor": "#F8FAFC",
            "contents": contents,
        }

    account_rows = [
        _info_row(
            get_multilingual_text(texts['user_id_label'], language=lang),
            user_id,
            {
                "type": "clipboard",
                "label": get_multilingual_text(texts['copy_id'], language=lang),
                "clipboardText": user_id,
            },
        )
    ]

    profile_rows = []
    settings_rows = []

    if user_data:
        sega_id_value = user_data.get('sega_id', get_multilingual_text(texts['not_bound'], language=lang))
        account_rows.append(_info_row(
            get_multilingual_text(texts['sega_id_label'], language=lang),
            sega_id_value,
        ))

        personal_info = user_data.get('personal_info') or {}
        if personal_info.get('name'):
            profile_rows.append(_info_row(
                get_multilingual_text(texts['name_label'], language=lang),
                personal_info['name'],
            ))
        if 'rating' in personal_info:
            rating_value = str(personal_info['rating'])
            rating_sub_value = None
            if 'last_update' in user_data:
                tz_str = format_timezone_string(user_id)
                rating_sub_value = (
                    f"{get_multilingual_text(texts['last_update_label'], language=lang)} "
                    f"{tz_str}: {user_data['last_update']}"
                )
            profile_rows.append(_info_row(
                get_multilingual_text(texts['rating_label'], language=lang),
                rating_value,
                sub_value=rating_sub_value,
            ))

        if "version" in user_data:
            server_text = texts['jp_server'] if user_data['version'] == 'jp' else texts['intl_server']
            settings_rows.append(_info_row(
                get_multilingual_text(texts['server_label'], language=lang),
                get_multilingual_text(server_text, language=lang),
            ))

        settings_rows.append(_info_row(
            get_multilingual_text(texts['language_label'], language=lang),
            language_label(lang),
        ))
    else:
        account_rows.append(_info_row(
            get_multilingual_text(texts['sega_id_label'], language=lang),
            get_multilingual_text(texts['not_bound'], language=lang),
            value_color=COLOR_DANGER,
        ))

    sections = [
        (
            get_multilingual_text(texts['account_section'], language=lang),
            account_rows,
        )
    ]
    if profile_rows:
        sections.append((
            get_multilingual_text(texts['profile_section'], language=lang),
            profile_rows,
        ))
    if settings_rows:
        sections.append((
            get_multilingual_text(texts['settings_section'], language=lang),
            settings_rows,
        ))

    return _standard_help_bubble(
        title=get_multilingual_text(texts['title'], language=lang),
        subtitle="JiETNG",
        sections=sections,
        alt_text=get_multilingual_text(texts['alt_text'], language=lang),
        docs_button=False,
    )

# ============================================================
# 更新结果 Flex Message / Update Result Flex Message
# ============================================================


def generate_update_result_flex(
    user_id,
    username,
    rating,
    update_time,
    elapsed_time,
    func_status,
    success=True,
):
    """
    生成更新结果 Flex Message

    Args:
        user_id: 用户ID
        username: 用户名
        rating: Rating 值
        update_time: 更新时间
        elapsed_time: 耗时（秒）
        func_status: 各功能状态字典
        success: 是否成功

    Returns:
        FlexMessage: 更新结果 Flex Message
    """
    lang = get_user_language(user_id)
    texts = update_result_flex_text

    # 格式化耗时
    if elapsed_time < 60:
        elapsed_str = f"{elapsed_time:.2f}s"
    else:
        minutes = int(elapsed_time // 60)
        seconds = elapsed_time % 60
        elapsed_str = f"{minutes}m {seconds:.1f}s"

    failed_statuses = {
        func_name: status
        for func_name, status in func_status.items()
        if not status
    }
    tz_str = format_timezone_string(user_id)
    accent = COLOR_SUCCESS if success else COLOR_DANGER
    body_contents = [
        _standard_header_box(
            get_multilingual_text(texts['title_success'] if success else texts['title_error'], language=lang),
            "JiETNG",
            accent=accent,
        ),
        {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": _metric_grid([
                _metric_card(
                    f"{get_multilingual_text(texts['update_time_label'], language=lang)} {tz_str}",
                    update_time,
                ),
                _metric_card(
                    get_multilingual_text(texts['elapsed_time_label'], language=lang),
                    elapsed_str,
                    value_color=accent,
                ),
            ]),
        },
    ]
    if failed_statuses:
        failed_rows = []
        for func_name, _status in failed_statuses.items():
            status_text = get_multilingual_text(texts['failed'], language=lang)
            func_label = _update_status_label(func_name, lang)
            failed_rows.append(_help_filter_row(func_label, status_text))
        body_contents.append(_help_section_title(get_multilingual_text(texts['status_label'], language=lang), accent=COLOR_DANGER))
        body_contents.append({
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": failed_rows,
        })

    random_tip = get_random_tip()
    random_ad = get_random_ad()
    extra_rows = []
    if random_tip:
        tip_box = generate_tip_ad_box(random_tip, lang)
        if tip_box:
            extra_rows.append(tip_box)
    if random_ad:
        ad_box = generate_tip_ad_box(random_ad, lang)
        if ad_box:
            extra_rows.append(ad_box)
    if extra_rows:
        body_contents.extend(extra_rows)

    alt_text = texts['alt_text_success'] if success else texts['alt_text_error']
    bubble = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": "16px",
            "contents": body_contents,
        },
    }
    return FlexMessage(
        alt_text=get_multilingual_text(alt_text, language=lang),
        contents=FlexContainer.from_dict(bubble),
    )

def generate_tip_ad_box(tip_ad, lang):
    """
    生成 Tip/Ad 小容器

    Args:
        tip_ad: tip/ad 数据字典
        lang: 语言代码

    Returns:
        dict: Flex Box 字典
    """
    # 获取对应语言的文本
    text_dict = tip_ad.get('text', {})
    text = str(select_text(text_dict, language=lang, default_language='ja') or '').strip()
    if not text:
        return None

    # 确定颜色和图标
    is_ad = tip_ad.get('type') == 'ad'
    bg_color = COLOR_AD_BG if is_ad else COLOR_TIP_BG
    text_color = COLOR_WARNING if is_ad else COLOR_TIP
    icon = "📢" if is_ad else "💡"

    # 构建内容
    box_contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": icon,
                    "size": "md",
                    "flex": 0
                },
                {
                    "type": "text",
                    "text": text,
                    "size": "xs",
                    "wrap": True,
                    "color": "#666666",
                    "flex": 1,
                    "margin": "sm"
                }
            ]
        }
    ]

    # 如果有按钮，添加按钮
    if 'button' in tip_ad:
        button_info = tip_ad['button']
        button_type = button_info.get('type', 'uri')
        button_label_dict = button_info.get('label', {})
        button_label = select_text(button_label_dict, language=lang, default_language='ja')
        button_value = button_info.get('value', '')

        # 如果label为空，使用默认值
        if not button_label:
            default_labels = localized_catalog("message_manager.button_labels")
            button_label = select_text(default_labels.get(button_type, {}), language=lang, default_language='ja') or 'Go'

        # 添加箭头到按钮标签
        button_label_with_arrow = f"{button_label} →"

        # 根据按钮类型创建action
        if button_type == 'uri':
            action = {
                "type": "uri",
                "label": button_label_with_arrow,
                "uri": button_value
            }
        else:  # message
            action = {
                "type": "message",
                "label": button_label_with_arrow,
                "text": button_value
            }

        # 添加按钮
        box_contents.append({
            "type": "button",
            "action": action,
            "style": "link",
            "height": "sm",
            "color": text_color,
            "margin": "sm"
        })

    # 构建最终的box
    tip_ad_box = {
        "type": "box",
        "layout": "vertical",
        "contents": box_contents,
        "backgroundColor": bg_color,
        "cornerRadius": "md",
        "paddingAll": "12px",
        "margin": "md"
    }

    return tip_ad_box

# ============================================================
# 系统错误警报 Flex Message / System Error Alert Flex Message
# ============================================================


def generate_calc_result_flex(notes, scores, difficulty=None, level=None, user_id=None):
    """
    生成计算结果 Flex Message

    Args:
        notes: dict with keys ['tap', 'hold', 'slide', 'touch', 'break']
        scores: dict with score calculations
        difficulty: 可选，难度名称 (如 'master', 'remaster')
        level: 可选，难度等级 (如 14.5)

    Returns:
        FlexMessage: 计算结果 Flex Message
    """
    lang = get_user_language(user_id)
    bubble = _build_calc_bubble(notes, scores, difficulty, level, lang)
    return FlexMessage(
        alt_text=get_multilingual_text(calc_flex_text['alt_single'], language=lang),
        contents=FlexContainer.from_dict(bubble)
    )


def generate_calc_carousel(calc_bubbles_data, user_id=None):
    """
    生成calc结果的carousel Flex Message

    Args:
        calc_bubbles_data: list of tuples (notes, scores, difficulty, level)

    Returns:
        FlexMessage: Carousel格式的calc结果
    """
    lang = get_user_language(user_id)
    if len(calc_bubbles_data) == 1:
        # 只有一个bubble，直接返回单个flex message
        notes, scores, difficulty, level = calc_bubbles_data[0]
        return generate_calc_result_flex(notes, scores, difficulty, level, user_id)

    # 多个bubble，构建carousel
    bubbles = []
    for notes, scores, difficulty, level in calc_bubbles_data:
        # 直接构建bubble字典，复制generate_calc_result_flex的逻辑
        bubble = _build_calc_bubble(notes, scores, difficulty, level, lang)
        bubbles.append(bubble)

    carousel = {
        "type": "carousel",
        "contents": bubbles
    }
    return FlexMessage(
        alt_text=get_multilingual_text(calc_flex_text['alt_multi'], language=lang),
        contents=FlexContainer.from_dict(carousel)
    )


def _build_calc_bubble(notes, scores, difficulty=None, level=None, lang="ja"):
    """
    构建calc结果的bubble字典（内部辅助函数）

    Args:
        notes: dict with keys ['tap', 'hold', 'slide', 'touch', 'break']
        scores: dict with score calculations
        difficulty: 可选，难度名称
        level: 可选，难度等级

    Returns:
        dict: bubble字典
    """
    # Note类型和数量
    note_contents = []
    note_labels = {
        'tap': 'TAP',
        'hold': 'HOLD',
        'slide': 'SLIDE',
        'touch': 'TOUCH',
        'break': 'BREAK'
    }

    for key in ['tap', 'hold', 'slide', 'touch', 'break']:
        # 跳过没有 touch 数据的情况
        if key == 'touch' and (not notes.get(key) or notes.get(key) == 0):
            continue

        note_contents.append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": note_labels[key],
                    "size": "sm",
                    "color": "#666666",
                    "flex": 0,
                    "weight": "bold"
                },
                {
                    "type": "text",
                    "text": str(notes[key]),
                    "size": "sm",
                    "color": "#111111",
                    "align": "end"
                }
            ],
            "margin": "sm"
        })

    # 分隔线
    separator = {
        "type": "separator",
        "margin": "md"
    }

    # 判定分数
    score_contents = []
    note_groups = [
        ('tap', ['tap_great', 'tap_good', 'tap_miss']),
        ('hold', ['hold_great', 'hold_good', 'hold_miss']),
        ('slide', ['slide_great', 'slide_good', 'slide_miss']),
        ('touch', ['touch_great', 'touch_good', 'touch_miss']),
        ('break', ['break_high_perfect', 'break_low_perfect', 'break_high_great',
                   'break_middle_great', 'break_low_great', 'break_good', 'break_miss'])
    ]

    def get_judgement_color(score_name):
        if 'perfect' in score_name:
            return "#FF9500"
        elif 'great' in score_name:
            return "#FF69B4"
        elif 'good' in score_name:
            return "#34C759"
        elif 'miss' in score_name:
            return "#999999"
        return "#666666"

    first_group = True
    for note_type, judgements in note_groups:
        # 跳过没有 touch 数据的情况
        if note_type == 'touch' and (not notes.get('touch') or notes.get('touch') == 0):
            continue

        if not first_group:
            score_contents.append({
                "type": "separator",
                "margin": "md"
            })
        first_group = False

        for score_name in judgements:
            if score_name in scores:
                score_value = scores[score_name]
                score_contents.append({
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": score_name.replace('_', ' ').title(),
                            "size": "xs",
                            "color": "#666666",
                            "flex": 3
                        },
                        {
                            "type": "text",
                            "text": f"-{score_value:.7f}%",
                            "size": "xs",
                            "color": get_judgement_color(score_name),
                            "align": "end",
                            "flex": 2
                        }
                    ],
                    "margin": "sm"
                })

    # 难度映射和颜色
    difficulty_map = {
        'basic': {'name': 'BASIC', 'color': '#34C759'},
        'advanced': {'name': 'ADVANCED', 'color': '#FF9500'},
        'expert': {'name': 'EXPERT', 'color': '#FF3B30'},
        'master': {'name': 'MASTER', 'color': '#AF52DE'},
        'remaster': {'name': 'Re:MASTER', 'color': '#D4A5F5'},
        'utage': {'name': 'UTAGE', 'color': '#000000'}
    }

    # 生成标题文本
    if difficulty:
        diff_info = difficulty_map.get(difficulty, {'name': difficulty.upper(), 'color': '#007AFF'})
        title_text = diff_info['name']
        if level:
            title_text += f" (Lv. {level:.1f})"
        header_color = diff_info['color']
    else:
        title_text = get_multilingual_text(calc_flex_text['title_distribution'], language=lang)
        header_color = "#007AFF"

    # 计算 tap_great 容错数
    tap_great_tolerance = []
    if 'tap_great' in scores and scores['tap_great'] > 0:
        # 从 101% 到 100.5000%
        max_tap_great_to_half = int(0.5 / scores['tap_great'])
        # 从 101% 到 100.0000%
        max_tap_great_to_full = int(1.0 / scores['tap_great'])

        tap_great_tolerance.append({
            "type": "separator",
            "margin": "lg"
        })

        tap_great_tolerance.append({
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": "100.5000%",
                            "size": "xs",
                            "color": "#666666",
                            "flex": 3,
                            "weight": "bold"
                        },
                        {
                            "type": "text",
                            "text": get_multilingual_text(
                                calc_flex_text['max_tap_great'],
                                language=lang,
                            ).format(count=max_tap_great_to_half),
                            "size": "xs",
                            "color": "#FF69B4",
                            "align": "end",
                            "flex": 4,
                            "weight": "bold"
                        }
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": "100.0000%",
                            "size": "xs",
                            "color": "#666666",
                            "flex": 3,
                            "weight": "bold"
                        },
                        {
                            "type": "text",
                            "text": get_multilingual_text(
                                calc_flex_text['max_tap_great'],
                                language=lang,
                            ).format(count=max_tap_great_to_full),
                            "size": "xs",
                            "color": "#FF69B4",
                            "align": "end",
                            "flex": 4,
                            "weight": "bold"
                        }
                    ],
                    "margin": "sm"
                }
            ],
            "backgroundColor": "#FFF5F0",
            "cornerRadius": "md",
            "paddingAll": "12px",
            "margin": "md"
        })

    # 构建body内容
    body_contents = score_contents if difficulty else (note_contents + [separator] + score_contents)
    body_contents.extend(tap_great_tolerance)

    # 构建bubble
    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": _standard_header_box(
            title_text,
            get_multilingual_text(calc_flex_text['subtitle'], language=lang),
            accent=header_color,
        ),
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": body_contents,
            "paddingAll": "16px"
        }
    }

    return bubble


def generate_search_results_flex(user_id, matching_songs, search_type='song', id_use=None):
    """
    生成搜索结果列表 Flex Message

    Args:
        user_id: 用户ID
        matching_songs: 匹配的歌曲列表
        search_type: 搜索类型 ('song' 或 'record')
        id_use: 使用的ID

    Returns:
        FlexMessage: 搜索结果列表
    """
    language = get_user_language(user_id)

    id_use_text = ""
    if id_use:
        id_use_text = f"&id_use={id_use}"

    config = {
        'command': 'search-song' if search_type == 'song' else 'search-record',
        'title': format_catalog(
            f"message_manager.search_titles.{search_type}",
            count=len(matching_songs),
        ),
    }
    display_songs = matching_songs[:20]

    song_rows = []
    for idx, song in enumerate(display_songs):
        song_id = song.get('id', '')
        song_title = song.get('title', 'Unknown')
        song_type = song.get('type', '')
        artist = song.get('artist') or '-'
        type_icon = _song_type_icon(song_type, width="42px", height="12px")
        title_contents = [
            {
                "type": "text",
                "text": song_title,
                "size": "sm",
                "weight": "bold",
                "color": "#000000",
                "wrap": True,
                "maxLines": 2,
                "flex": 1,
            }
        ]
        if type_icon:
            title_contents.append(type_icon)

        row = {
            "type": "box",
            "layout": "horizontal",
            "spacing": "md",
            "margin": "md" if idx > 0 else "none",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "flex": 3,
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "spacing": "xs",
                            "alignItems": "flex-end",
                            "contents": title_contents,
                        },
                        {
                            "type": "text",
                            "text": artist,
                            "size": "xs",
                            "color": "#666666",
                            "margin": "xs",
                            "wrap": True,
                            "maxLines": 1
                        },
                    ]
                },
                _round_icon_action(
                    "→",
                    {
                        "type": "postback",
                        "label": "→",
                        "data": f"{config['command']} {song_id}{id_use_text}"
                    }
                )
            ]
        }

        song_rows.append(row)
        if idx < len(display_songs) - 1:
            song_rows.append({"type": "separator", "margin": "sm"})

    title_text = select_text(config['title'], language=language, default_language='ja')

    header_box = _standard_header_box(title_text, "JiETNG")

    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": header_box,
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": song_rows,
            "paddingAll": "16px",
            "backgroundColor": "#FFFFFF"
        },
        "styles": {"body": {"backgroundColor": "#FFFFFF"}}
    }

    return FlexMessage(
        alt_text=title_text,
        contents=FlexContainer.from_dict(bubble)
    )


def generate_ranking_flex(user_id, top5, nearby_entries=None, ver="jp"):
    """
    生成 Rating 排行榜 Flex Message（5+7 布局）

    Args:
        user_id: 当前用户ID
        top5: 前5名列表 [{"rank": 1, "name": "xxx", "rating": "15000"}, ...]
        nearby_entries: 以用户为中心的附近名单（用户不在前5时提供），None 表示用户在前5或版本不一致
        ver: 版本 "jp" 或 "intl"

    Returns:
        FlexMessage
    """
    title_text = get_multilingual_text(ranking_title_text, user_id)
    ver_label = "JP" if ver == "jp" else "INTL"

    header = _standard_header_box(title_text, ver_label)

    body_contents = [
        {"type": "separator", "color": "#000000"}
    ]

    def make_row(entry, highlight=False):
        rank = entry["rank"]
        name = entry["name"]
        rating = entry["rating"]

        row_contents = [
            {
                "type": "text",
                "text": f"#{rank}",
                "size": "sm",
                "weight": "bold",
                "color": "#000000",
                "flex": 0,
                "contents": []
            },
            {
                "type": "text",
                "text": name,
                "size": "sm",
                "color": "#000000",
                "flex": 3,
                "wrap": True,
                "maxLines": 1
            },
            {
                "type": "text",
                "text": str(rating),
                "size": "sm",
                "color": "#666666",
                "flex": 0,
                "align": "end"
            }
        ]

        row = {
            "type": "box",
            "layout": "horizontal",
            "spacing": "md",
            "contents": row_contents,
            "paddingAll": "8px"
        }

        if highlight:
            row["borderWidth"] = "2px"
            row["borderColor"] = "#000000"
            row["cornerRadius"] = "4px"

        return row

    # 渲染前5名
    for i, entry in enumerate(top5):
        body_contents.append(make_row(entry, highlight=entry.get("is_user", False)))
        if i < len(top5) - 1:
            body_contents.append({"type": "separator", "color": "#DDDDDD"})

    # 用户不在前5，显示虚线分割 + 以用户为中心的附近名单
    if nearby_entries:
        body_contents.append({
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "· · · · · · · · · · · · · · · · · · · · · · · · · · · · · ·",
                    "size": "xxs",
                    "color": "#999999",
                    "align": "center"
                }
            ],
            "margin": "sm"
        })
        for i, entry in enumerate(nearby_entries):
            body_contents.append(make_row(entry, highlight=entry.get("is_user", False)))
            if i < len(nearby_entries) - 1:
                body_contents.append({"type": "separator", "color": "#DDDDDD"})

    body = {
        "type": "box",
        "layout": "vertical",
        "contents": body_contents,
        "paddingStart": "12px",
        "paddingEnd": "12px",
        "paddingBottom": "12px",
        "paddingTop": "4px"
    }

    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": header,
        "body": body
    }

    alt_text = get_multilingual_text(ranking_alt_text, user_id)
    return FlexMessage(alt_text=alt_text, contents=FlexContainer.from_dict(bubble))


def generate_song_list_flex(user_id, title, matching_songs, page, command_prefix, query, matched_sheets_map=None):
    """
    生成歌曲列表 Flex Message（黑白简约风，歌曲搜索列表共用）

    Args:
        user_id: 用户ID
        title: 列表标题
        matching_songs: 匹配的歌曲列表
        page: 当前页码（从1开始）
        command_prefix: 翻页命令前缀（如 "artist"、"designer" 或 "bpm"）
        query: 搜索关键词
        matched_sheets_map: designer 模式下的匹配谱面映射 {song_id: [sheet, ...]}

    Returns:
        FlexMessage: 歌曲列表
    """
    difficulty_label_map = {
        'basic': 'BAS',
        'advanced': 'ADV',
        'expert': 'EXP',
        'master': 'MAS',
        'remaster': 'ReMAS'
    }

    page_size = 15
    total = len(matching_songs)
    total_pages = (total + page_size - 1) // page_size
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    end = start + page_size
    has_next = end < total

    # 超过每页限制时，取前19条 + 翻页按钮
    if has_next:
        page_songs = matching_songs[start:start + page_size - 1]
    else:
        page_songs = matching_songs[start:end]

    song_rows = []
    for idx, song in enumerate(page_songs):
        song_id = song.get('id', '')
        song_title = song.get('title', 'Unknown')
        type_icon = _song_type_icon(song.get('type', ''), width="42px", height="12px")

        # 副信息
        if matched_sheets_map and song_id in matched_sheets_map:
            # designer 模式：谱师名 + 匹配的难度标签
            sheets = matched_sheets_map[song_id]
            designers = []
            for s in sheets:
                diff_label = difficulty_label_map.get(s.get('difficulty', ''), s.get('difficulty', ''))
                designer_name = s.get('noteDesigner', '')
                designers.append(f"{designer_name} [{diff_label}]")
            sub_text = ' / '.join(designers)
        elif command_prefix == "bpm":
            sub_text = f"BPM: {song.get('bpm', '-')}"
        else:
            # artist 模式：艺术家名
            sub_text = song.get('artist') or '-'

        title_contents = [
            {
                "type": "text",
                "text": song_title,
                "size": "sm",
                "weight": "bold",
                "color": "#000000",
                "wrap": True,
                "maxLines": 2,
                "flex": 1,
            }
        ]
        if type_icon:
            title_contents.append(type_icon)

        left_contents = [
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "xs",
                "alignItems": "flex-end",
                "contents": title_contents,
            },
            {
                "type": "text",
                "text": sub_text,
                "size": "xs",
                "color": "#666666",
                "margin": "xs",
                "wrap": True,
                "maxLines": 1
            }
        ]

        row = {
            "type": "box",
            "layout": "horizontal",
            "spacing": "md",
            "margin": "md" if idx > 0 else "none",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "flex": 3,
                    "contents": left_contents
                },
                _round_icon_action(
                    "→",
                    {
                        "type": "postback",
                        "label": "→",
                        "data": f"search-song {song_id}"
                    }
                )
            ]
        }

        song_rows.append(row)
        if idx < len(page_songs) - 1 or has_next:
            song_rows.append({"type": "separator", "margin": "sm"})

    # 翻页按钮
    if has_next:
        next_page = page + 1
        song_rows.append(_pill_action_box(
            f"Next Page ({next_page}/{total_pages})",
            {
                "type": "postback",
                "label": f"Next Page ({next_page}/{total_pages})",
                "data": f"{command_prefix} {query} {next_page}",
                "displayText": f"{command_prefix} {query} {next_page}"
            },
            bg_color="#315B7D",
            margin="md",
        ))

    # 跳转按钮（多页时显示）
    if total_pages > 1:
        jump_text = f"{command_prefix} {query} "
        song_rows.append(_pill_action_box(
            f"Go to ... (1~{total_pages})",
            {
                "type": "uri",
                "label": f"Go to ... (1~{total_pages})",
                "uri": f"https://line.me/R/oaMessage/{LINE_ACCOUNT_ID}/?{quote(jump_text)}"
            },
            bg_color="#E8EEF5",
            text_color="#315B7D",
            margin="sm",
        ))

    header_box = _standard_header_box(title, f"Page {page}/{total_pages} · {total} songs")

    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": header_box,
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": song_rows,
            "paddingAll": "16px",
            "backgroundColor": "#FFFFFF"
        },
        "styles": {"body": {"backgroundColor": "#FFFFFF"}}
    }

    return FlexMessage(
        alt_text=title,
        contents=FlexContainer.from_dict(bubble)
    )


def generate_friend_buttons(user_id, alt_text, friend_list, group_size):
    """
    生成好友列表 Flex Message（极简黑白风格）

    Args:
        alt_text: 替代文本
        friend_list: 好友列表 [{"name": "text", "rating": "text", "friend_id": "text"}]
        group_size: 每页显示的好友数（默认6个）

    Returns:
        FlexMessage
    """
    if not friend_list:
        return friend_error(user_id)

    bubbles = []
    total_pages = (len(friend_list) + group_size - 1) // group_size

    for page_idx in range(0, len(friend_list), group_size):
        group = friend_list[page_idx:page_idx + group_size]
        page_num = page_idx // group_size + 1

        # 创建好友行
        friend_rows = []
        for idx, friend in enumerate(group):
            # 解析信息
            name = friend["name"]
            rating = friend["rating"]
            friend_id = friend["friend_id"]

            # 创建单行（第一个不需要上边距）
            row = {
                "type": "box",
                "layout": "horizontal",
                "spacing": "md",
                "margin": "md" if idx > 0 else "none",
                "contents": [
                    # 左侧：名字和Rating
                    {
                        "type": "box",
                        "layout": "vertical",
                        "flex": 3,
                        "contents": [
                            {
                                "type": "text",
                                "text": name,
                                "size": "sm",
                                "weight": "bold",
                                "wrap": True,
                                "maxLines": 2
                            },
                            {
                                "type": "text",
                                "text": f"Rating: {rating}",
                                "size": "xs",
                                "color": "#999999",
                                "margin": "xs"
                            }
                        ]
                    },
                    # 右侧：按钮（只显示符号）
                    _round_icon_action(
                        "→",
                        {
                            "type": "uri",
                            "label": "→",
                            "uri": f"https://line.me/R/oaMessage/{LINE_ACCOUNT_ID}/?friend-rcd%20{friend_id}%20"
                        }
                    )
                ]
            }

            # 添加分隔线（除了最后一个）
            if idx < len(group) - 1:
                friend_rows.append(row)
                friend_rows.append({
                    "type": "separator",
                    "margin": "sm"
                })
            else:
                friend_rows.append(row)

        # 创建 bubble
        bubble = {
            "type": "bubble",
            "size": "mega",
            "header": _standard_header_box(
                alt_text,
                f"Page {page_num}/{total_pages} · {len(group)} friends",
            ),
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": friend_rows,
                "paddingAll": "16px"
            }
        }

        bubbles.append(bubble)

    # 创建 carousel
    if len(bubbles) == 1:
        # 只有一页，直接返回 bubble
        flex_dict = bubbles[0]
    else:
        # 多页，使用 carousel
        flex_dict = {
            "type": "carousel",
            "contents": bubbles
        }

    return FlexMessage(
        alt_text=alt_text,
        contents=FlexContainer.from_dict(flex_dict)
    )


def generate_rc_flex(level: float, rc_data: list, user_id=None):
    """
    生成 Rating Constant 对照表 Flex Message

    Args:
        level: 谱面定数 (如 14.5)
        rc_data: Rating 对照数据列表 [(score, rating), ...]
        user_id: 用户ID（用于多语言）

    Returns:
        FlexMessage: Rating 对照表
    """
    language = get_user_language(user_id)

    # 标题文本
    title_texts = format_catalog("message_manager.rating_chart_title", level=level)
    title_text = select_text(title_texts, language=language, default_language='ja')

    # 按达成率整数部分分组（100.xxxx、99.xxxx、98.xxxx...）
    score_groups = {}
    for score, rating in rc_data:
        score_int = int(score)
        if score_int not in score_groups:
            score_groups[score_int] = []
        score_groups[score_int].append((score, rating))

    # 获取所有达成率整数值并倒序排列（从高到低）
    sorted_score_ints = sorted(score_groups.keys(), reverse=True)

    # 构建单列内容
    content_rows = []

    for i, score_int in enumerate(sorted_score_ints):
        entries = score_groups[score_int]

        # 当整数部分变化时，添加分隔线（第一组除外）
        if i > 0:
            content_rows.append({
                "type": "separator",
                "margin": "md",
                "color": "#DDDDDD"
            })

        # 按达成率倒序排列
        entries.sort(key=lambda x: x[0], reverse=True)

        # 达成率列表
        for score, rating in entries:
            score_text = f"{score:.4f}%"
            is_special = (score_text in ["100.5000%", "100.0000%", "99.5000%", "99.0000%", "98.0000%", "97.0000%"])

            content_rows.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": score_text,
                        "size": "sm",
                        "color": "#000000" if is_special else "#666666",
                        "align": "start"
                    },
                    {
                        "type": "text",
                        "text": "→",
                        "size": "sm",
                        "color": "#222222" if is_special else "#999999",
                        "align": "center"
                    },
                    {
                        "type": "text",
                        "text": f"{rating}",
                        "size": "sm",
                        "color": "#000000" if is_special else "#666666",
                        "align": "end"
                    }
                ],
                "margin": "xs",
                "spacing": "md"
            })

    # 构建 bubble
    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": _standard_header_box(title_text, "Rating Constant", accent="#AF52DE"),
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": content_rows,
            "paddingAll": "16px"
        }
    }

    return FlexMessage(
        alt_text=title_text,
        contents=FlexContainer.from_dict(bubble)
    )

def generate_bot_status_flex(uptime_str, image_queue_size, web_queue_size,
                              tasks_today, song_count, dxdata_date, user_id=None):
    """
    生成 Bot 状态信息 Flex Message

    Args:
        uptime_str: 运行时长字符串（如 "1d 4h 22m"）
        image_queue_size: 图片队列当前排队任务数
        web_queue_size: web 队列当前排队任务数
        tasks_today: 今日已处理 image_gen 任务数
        song_count: dxdata 中的歌曲总数
        dxdata_date: dxdata 文件 mtime 的日期字符串（YYYY-MM-DD）
        user_id: 用户ID（用于多语言）

    Returns:
        FlexMessage: Bot 状态信息
    """
    lang = get_user_language(user_id)

    texts = localized_catalog("message_manager.service_status")
    # "曲" / songs / 首
    song_unit = select_text(language_catalog("message_manager.song_unit"), language=lang)

    queue_text = f"Image {image_queue_size}\nWeb {web_queue_size}"
    songs_text = f"{song_count} {song_unit}\n{dxdata_date}"

    queue_busy = (image_queue_size + web_queue_size) > 0
    queue_color = COLOR_WARNING if queue_busy else COLOR_SUCCESS
    body_contents = [
        _standard_header_box(
            select_text(texts['title'], language=lang),
            "JiETNG",
            accent="#111827",
        ),
        {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": _metric_grid([
                _metric_card(select_text(texts['uptime'], language=lang), uptime_str),
                _metric_card(select_text(texts['queue'], language=lang), queue_text, value_color=queue_color),
                _metric_card(select_text(texts['tasks_today'], language=lang), str(tasks_today), value_color="#8A63D2"),
                _metric_card(select_text(texts['songs'], language=lang), songs_text),
            ]),
        },
    ]

    random_tip = get_random_tip()
    random_ad = get_random_ad()
    extra_rows = []
    if random_tip:
        tip_box = generate_tip_ad_box(random_tip, lang)
        if tip_box:
            extra_rows.append(tip_box)
    if random_ad:
        ad_box = generate_tip_ad_box(random_ad, lang)
        if ad_box:
            extra_rows.append(ad_box)
    if extra_rows:
        body_contents.extend(extra_rows)

    bubble = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": "16px",
            "contents": body_contents,
        },
    }
    return FlexMessage(
        alt_text=select_text(texts['title'], language=lang),
        contents=FlexContainer.from_dict(bubble),
    )
