"""Account, service, search and social LINE messages."""
from modules.messages.layout import (
    COLOR_AD_BG,
    COLOR_BRAND,
    COLOR_DANGER,
    COLOR_SUCCESS,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TIP,
    COLOR_TIP_BG,
    COLOR_WARNING,
    flex_action_button,
    help_filter_row,
    flex_text,
    pill,
    section_title,
    metric_card,
    metric_grid,
    pill_action_box,
    round_icon_action,
    song_type_icon,
    standard_action_bubble,
    standard_bubble,
    standard_header_box,
    standard_help_bubble,
)
from modules.i18n import (
    select_text as get_multilingual_text,
    format_catalog,
    get_user_language,
    language_catalog,
    language_label,
    localized_catalog,
    select_text,
)
from urllib.parse import quote
from modules.config_loader import LINE_ACCOUNT_ID
from modules.user_db import get_user
from modules.user_manager import get_user_timezone
from modules.notice_manager import get_random_ad, get_random_tip
from linebot.v3.messaging import (
    TextMessage,
    ImageMessage,
    QuickReply,
    QuickReplyItem,
    PostbackAction,
    FlexMessage,
    FlexContainer,
)

_message_texts = localized_catalog("messages")

welcome_msg_text = "『JiETNG・カヰテー』で有りんす。\nお願ひ申し候。"
group_welcome_msg_text = "『JiETNG・カヰテー』で有りんす。\nお出迎え有りんす。"
system_error_text = _message_texts["system_error_text"]

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


def _tip_ad_boxes(lang):
    boxes = (generate_tip_ad_box(item, lang) for item in (get_random_tip(), get_random_ad()) if item)
    return [box for box in boxes if box]

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
    return standard_action_bubble(
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
            "title": _message_texts["sega_bind_title_text"],
            "body": _message_texts["sega_bind_description_text"],
            "button": _message_texts["sega_bind_button_text"],
            "alt": _message_texts["sega_bind_alt_text"],
            "accent": COLOR_BRAND,
        },
        "rebind": {
            "title": _message_texts["rebind_title_alt_text"],
            "body": _message_texts["rebind_description_text"],
            "button": _message_texts["rebind_button_text"],
            "alt": _message_texts["rebind_title_alt_text"],
            "accent": "#8A63D2",
        },
        "unbind": {
            "title": _message_texts["unbind_title_alt_text"],
            "body": _message_texts["unbind_description_text"],
            "button": _message_texts["unbind_button_text"],
            "alt": _message_texts["unbind_title_alt_text"],
            "accent": COLOR_DANGER,
        },
        "settings": {
            "title": _message_texts["settings_title_alt_text"],
            "body": _message_texts["settings_description_text"],
            "button": _message_texts["settings_button_text"],
            "alt": _message_texts["settings_title_alt_text"],
            "accent": "#315B7D",
        },
    }
    config = configs[action_type]
    title = get_multilingual_text(config["title"], user_id)
    body = get_multilingual_text(config["body"], user_id)
    button = get_multilingual_text(config["button"], user_id)
    alt = get_multilingual_text(config["alt"], user_id)
    return standard_action_bubble(
        title=title,
        subtitle="JiETNG",
        body_text=body,
        alt_text=alt,
        actions=[
            flex_action_button({"type": "uri", "label": button, "uri": url}, color=config["accent"])
        ],
        accent=config["accent"],
        user_id=user_id,
    )


def generate_welcome_flex(user_id=None, bind_url=None, group=False):
    title = "JiETNG"
    body = group_welcome_msg_text if group else welcome_msg_text
    actions = None
    if bind_url:
        label = get_multilingual_text(_message_texts["sega_bind_button_text"], user_id)
        actions = [
            flex_action_button({"type": "uri", "label": label, "uri": bind_url}, color=COLOR_BRAND)
        ]
    return standard_action_bubble(
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
    title = get_multilingual_text(_message_texts["export_flex_title_text"], user_id)
    body = get_multilingual_text(_message_texts["export_flex_summary_text"], user_id).format(
        best=meta["best_count"],
        recent=meta["recent_count"],
        fmt=fmt_label,
        size_kb=size_kb,
    )
    foot = get_multilingual_text(_message_texts["export_flex_footnote_text"], user_id).format(ttl=meta["ttl_minutes"])
    btn = get_multilingual_text(_message_texts["export_flex_button_text"], user_id)
    copy_btn = get_multilingual_text(_message_texts["export_flex_copy_button_text"], user_id)
    alt = get_multilingual_text(_message_texts["export_alt_text"], user_id)
    return standard_action_bubble(
        title=title,
        subtitle=fmt_label,
        body_text=body,
        note_text=foot,
        alt_text=alt,
        actions=[
            flex_action_button({"type": "uri", "label": btn, "uri": f"{meta['url']}?openExternalBrowser=1"}),
            flex_action_button(
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


def _update_status_label(func_name, lang):
    status_text_keys = {
        "User Info": "status_user_info",
        "Best Records": "status_best_records",
        "Recent Records": "status_recent_records",
    }
    text_key = status_text_keys.get(func_name)
    if not text_key:
        return func_name
    return get_multilingual_text(_message_texts["update_result_flex_text"][text_key], language=lang)

def _message_factory(message_text):
    def build_message(user_id=None):
        return create_text_message(message_text, user_id)

    return build_message


rebind_msg = _message_factory(_message_texts["rebind_msg_text"])
segaid_error = _message_factory(_message_texts["segaid_error_text"])
record_error = _message_factory(_message_texts["record_error_text"])
info_error = _message_factory(_message_texts["info_error_text"])
access_error = _message_factory(_message_texts["access_error_text"])
system_error = _message_factory(system_error_text)
input_error = _message_factory(_message_texts["input_error_text"])
song_error = _message_factory(_message_texts["song_error_text"])
level_not_supported = _message_factory(_message_texts["level_not_supported_text"])
plate_error = _message_factory(_message_texts["plate_error_text"])
version_error = _message_factory(_message_texts["version_error_text"])
store_error = _message_factory(_message_texts["store_error_text"])
rate_limit_msg = _message_factory(_message_texts["rate_limit_msg_text"])
maintenance_error = _message_factory(_message_texts["maintenance_error_text"])
friend_error = _message_factory(_message_texts["friend_error_text"])
friend_rcd_error = _message_factory(_message_texts["friend_rcd_error_text"])
mention_error = _message_factory(_message_texts["mention_error_text"])
mention_not_allowed = _message_factory(_message_texts["mention_not_allowed_text"])
mention_record_error = _message_factory(_message_texts["mention_record_error_text"])
cannot_do_for_others = _message_factory(_message_texts["cannot_do_for_others_text"])
no_matching_data = _message_factory(_message_texts["no_matching_data_text"])
mention_no_matching_data = _message_factory(_message_texts["mention_no_matching_data_text"])

def level_record_not_found(level, page, user_id=None):
    """生成指定等级记录未找到消息"""
    text = get_multilingual_text(_message_texts["level_record_not_found_text"], user_id).format(level=level, page=page)
    return TextMessage(text=text)

def level_record_page_hint(page, user_id=None):
    """生成等级记录页面提示消息"""
    text = get_multilingual_text(_message_texts["level_record_page_hint_text"], user_id).format(page=page)
    return TextMessage(text=text)

def get_notice_header(user_id=None):
    """获取公告标题（多语言）"""
    return get_multilingual_text(_message_texts["notice_header_text"], user_id)

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
        "header": standard_header_box(title, "JiETNG"),
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
    return get_multilingual_text(_message_texts["friend_list_alt_text"], user_id)

def get_nearby_stores_alt_text(user_id=None):
    """获取附近机厅列表 alt_text（多语言）"""
    return get_multilingual_text(_message_texts["nearby_stores_alt_text"], user_id)


def generate_song_image_message(song_id, image_url, preview_url=None, user_id=None, mode='info'):
    """Attach localized song actions to a native image message."""
    actions = (
        [('view_record_button_text', 'search-record')]
        if mode == 'info' else [('view_info_button_text', 'search-song')]
    )
    return ImageMessage(
        original_content_url=image_url,
        preview_image_url=preview_url or image_url,
        quick_reply=QuickReply(items=[
            QuickReplyItem(action=PostbackAction(
                label=get_multilingual_text(_message_texts[label_key], user_id),
                data=f"{command} {song_id}",
            ))
            for label_key, command in actions
        ]),
    )


def build_dxdata_update_message(result, user_id=None):
    """Build the localized update summary for initial and subsequent imports."""
    def text(key, **values):
        translated = get_multilingual_text(_message_texts[f"dxdata_{key}_text"], user_id)
        return translated.format(**values) if values else translated

    if not result.get("success"):
        message = result.get("message")
        fetch_failed = "message" not in result or "データ取得失敗" in message or "fetch" in message.lower()
        return text("fetch_failed" if fetch_failed else "parse_failed")

    parts = [text("update_success"), ""]
    stats = result["new_stats"]
    old_stats = result.get("old_stats")
    if old_stats:
        diff = result.get("diff", {})
        for kind in ("songs", "sheets"):
            count = diff.get(f"{kind}_added", 0)
            if count == 0:
                parts.append(text(f"no_new_{kind}"))
            else:
                key = f"new_{kind}" if count > 0 else f"{kind}_decreased"
                parts.append(text(key, count=count))
        parts.extend([
            "",
            text("last_update", timestamp=old_stats["timestamp"]),
            text("current_stats", songs=stats["total_songs"], sheets=stats["total_sheets"]),
        ])
    else:
        parts.extend([
            text("initial_stats_songs", count=stats["total_songs"]),
            text("initial_stats_sheets", count=stats["total_sheets"]),
            "",
            text("first_update"),
        ])
    return "\n".join(parts)

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
    texts = _message_texts["user_info_flex_text"]
    user_data = get_user(user_id)

    def _info_row(label, value, action=None, value_color=COLOR_TEXT_PRIMARY, sub_value=None):
        value_contents = [
            flex_text(label, size="xxs", color=COLOR_TEXT_MUTED),
            flex_text(str(value), size="sm", color=value_color, weight="bold"),
        ]
        if sub_value:
            value_contents.append(flex_text(str(sub_value), size="xxs", color=COLOR_TEXT_MUTED, margin="xs"))
        value_block = {
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "contents": value_contents,
        }
        contents = [value_block]
        if action:
            copy_pill = pill(
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

    return standard_help_bubble(
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
    update_time,
    elapsed_time,
    func_status,
    success=True,
):
    """
    生成更新结果 Flex Message

    Args:
        user_id: 用户ID
        update_time: 更新时间
        elapsed_time: 耗时（秒）
        func_status: 各功能状态字典
        success: 是否成功

    Returns:
        FlexMessage: 更新结果 Flex Message
    """
    lang = get_user_language(user_id)
    texts = _message_texts["update_result_flex_text"]

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
        standard_header_box(
            get_multilingual_text(texts['title_success'] if success else texts['title_error'], language=lang),
            "JiETNG",
            accent=accent,
        ),
        {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": metric_grid([
                metric_card(
                    f"{get_multilingual_text(texts['update_time_label'], language=lang)} {tz_str}",
                    update_time,
                ),
                metric_card(
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
            failed_rows.append(help_filter_row(func_label, status_text))
        body_contents.append(section_title(get_multilingual_text(texts['status_label'], language=lang), accent=COLOR_DANGER))
        body_contents.append({
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": failed_rows,
        })

    body_contents.extend(_tip_ad_boxes(lang))

    alt_text = texts['alt_text_success'] if success else texts['alt_text_error']
    bubble = standard_bubble(body_contents)
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
        alt_text=get_multilingual_text(_message_texts["calc_flex_text"]['alt_single'], language=lang),
        contents=FlexContainer.from_dict(bubble)
    )


def generate_calc_carousel(calc_bubbles_data, user_id=None):
    """Use a single card for one result, otherwise retain the supplied card order."""
    if len(calc_bubbles_data) == 1:
        notes, scores, difficulty, level = calc_bubbles_data[0]
        return generate_calc_result_flex(notes, scores, difficulty, level, user_id)

    lang = get_user_language(user_id)
    bubbles = [
        _build_calc_bubble(notes, scores, difficulty, level, lang)
        for notes, scores, difficulty, level in calc_bubbles_data
    ]
    return FlexMessage(
        alt_text=get_multilingual_text(_message_texts["calc_flex_text"]['alt_multi'], language=lang),
        contents=FlexContainer.from_dict({"type": "carousel", "contents": bubbles}),
    )


def _build_calc_bubble(notes, scores, difficulty=None, level=None, lang="ja"):
    """Assemble note counts, judgement losses and tolerances in display order."""
    title_text, header_color = _calc_header(difficulty, level, lang)
    body_contents = []
    if not difficulty:
        body_contents.extend(_calc_note_rows(notes))
        body_contents.append({"type": "separator", "margin": "md"})
    body_contents.extend(_calc_score_rows(notes, scores))
    body_contents.extend(_calc_tolerance_rows(scores, lang))

    # 构建bubble
    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": standard_header_box(
            title_text,
            get_multilingual_text(_message_texts["calc_flex_text"]['subtitle'], language=lang),
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


def _calc_note_rows(notes):
    # Note类型和数量
    note_contents = []

    for key in ['tap', 'hold', 'slide', 'touch', 'break']:
        # 跳过没有 touch 数据的情况
        if key == 'touch' and not notes.get(key):
            continue

        note_contents.append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": key.upper(),
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

    return note_contents


def _calc_score_rows(notes, scores):
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
        if note_type == 'touch' and not notes.get('touch'):
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

    return score_contents


def _calc_header(difficulty, level, lang):
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
        title_text = get_multilingual_text(_message_texts["calc_flex_text"]['title_distribution'], language=lang)
        header_color = "#007AFF"

    return title_text, header_color


def _calc_tolerance_rows(scores, lang):
    if not ("tap_great" in scores and scores["tap_great"] > 0):
        return []
    tap_great = scores["tap_great"]

    rows = []
    label = get_multilingual_text(_message_texts["calc_flex_text"]['max_tap_great'], language=lang)
    for index, (achievement, allowed_loss) in enumerate((("100.5000%", 0.5), ("100.0000%", 1.0))):
        row = {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": achievement,
                    "size": "xs",
                    "color": "#666666",
                    "flex": 3,
                    "weight": "bold",
                },
                {
                    "type": "text",
                    "text": label.format(count=int(allowed_loss / tap_great)),
                    "size": "xs",
                    "color": "#FF69B4",
                    "align": "end",
                    "flex": 4,
                    "weight": "bold",
                },
            ],
        }
        if index:
            row["margin"] = "sm"
        rows.append(row)
    return [
        {"type": "separator", "margin": "lg"},
        {
            "type": "box",
            "layout": "vertical",
            "contents": rows,
            "backgroundColor": "#FFF5F0",
            "cornerRadius": "md",
            "paddingAll": "12px",
            "margin": "md",
        },
    ]


def _song_row(song, subtitle, command, *, first):
    song_title = song.get('title', 'Unknown')
    song_type = song.get('type', '')
    type_icon = song_type_icon(song_type, width="42px", height="12px")
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
        "margin": "md" if not first else "none",
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
                        "text": subtitle,
                        "size": "xs",
                        "color": "#666666",
                        "margin": "xs",
                        "wrap": True,
                        "maxLines": 1
                    },
                ]
            },
            round_icon_action(
                "→",
                {
                    "type": "postback",
                    "label": "→",
                    "data": command
                }
            )
        ]
    }
    return row


def _song_list_message(title, subtitle, rows):
    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": standard_header_box(title, subtitle),
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": rows,
            "paddingAll": "16px",
            "backgroundColor": "#FFFFFF"
        },
        "styles": {"body": {"backgroundColor": "#FFFFFF"}}
    }

    return FlexMessage(alt_text=title, contents=FlexContainer.from_dict(bubble))


def generate_search_results_flex(user_id, matching_songs, search_type='song', id_use=None):
    """显示前 20 条搜索结果，每首歌使用独立的一次性图片按钮。"""
    language = get_user_language(user_id)
    command = 'search-song' if search_type == 'song' else 'search-record'
    suffix = f"&id_use={id_use}" if id_use and search_type == 'record' else ''
    title = select_text(
        format_catalog(f"message_manager.search_titles.{search_type}", count=len(matching_songs)),
        language=language,
        default_language='ja',
    )
    rows = []
    for song in matching_songs[:20]:
        if rows:
            rows.append({"type": "separator", "margin": "sm"})
        rows.append(_song_row(
            song, song.get('artist') or '-',
            f"{command} {song.get('id', '')}{suffix}", first=not rows,
        ))
    return _song_list_message(title, "JiETNG", rows)


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
    title_text = get_multilingual_text(_message_texts["ranking_title_text"], user_id)
    ver_label = "JP" if ver == "jp" else "INTL"

    header = standard_header_box(title_text, ver_label)

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

    alt_text = get_multilingual_text(_message_texts["ranking_alt_text"], user_id)
    return FlexMessage(alt_text=alt_text, contents=FlexContainer.from_dict(bubble))


def _song_subtitle(song, command_prefix, matched_sheets_map):
    difficulty_label_map = {
        'basic': 'BAS',
        'advanced': 'ADV',
        'expert': 'EXP',
        'master': 'MAS',
        'remaster': 'ReMAS'
    }

    song_id = song.get('id', '')
    if matched_sheets_map and song_id in matched_sheets_map:
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
        sub_text = song.get('artist') or '-'

    return sub_text


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
    page_size = 15
    total = len(matching_songs)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    end = start + page_size
    has_next = end < total

    page_songs = matching_songs[start:end]
    song_rows = []
    for song in page_songs:
        if song_rows:
            song_rows.append({"type": "separator", "margin": "sm"})
        song_rows.append(_song_row(
            song, _song_subtitle(song, command_prefix, matched_sheets_map),
            f"search-song {song.get('id', '')}", first=not song_rows,
        ))

    # 翻页按钮
    if has_next:
        song_rows.append({"type": "separator", "margin": "sm"})
        next_page = page + 1
        song_rows.append(pill_action_box(
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
        song_rows.append(pill_action_box(
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

    return _song_list_message(title, f"Page {page}/{total_pages} · {total} songs", song_rows)


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
                    round_icon_action(
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
            "header": standard_header_box(
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
        "header": standard_header_box(title_text, "Rating Constant", accent="#AF52DE"),
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
        standard_header_box(
            select_text(texts['title'], language=lang),
            "JiETNG",
            accent="#111827",
        ),
        {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": metric_grid([
                metric_card(select_text(texts['uptime'], language=lang), uptime_str),
                metric_card(select_text(texts['queue'], language=lang), queue_text, value_color=queue_color),
                metric_card(select_text(texts['tasks_today'], language=lang), str(tasks_today), value_color="#8A63D2"),
                metric_card(select_text(texts['songs'], language=lang), songs_text),
            ]),
        },
    ]

    body_contents.extend(_tip_ad_boxes(lang))

    bubble = standard_bubble(body_contents)
    return FlexMessage(
        alt_text=select_text(texts['title'], language=lang),
        contents=FlexContainer.from_dict(bubble),
    )
