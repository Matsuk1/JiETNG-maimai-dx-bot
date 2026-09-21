"""Shared LINE Flex layout components, independent of business data loading."""
from linebot.v3.messaging import FlexMessage, FlexContainer
from modules.i18n import localized_catalog, select_text as get_multilingual_text


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


def help_ui(key, user_id=None):
    return get_multilingual_text(HELP_UI_TEXT[key], user_id)


def flex_text(text, size="sm", color="#222222", weight=None, wrap=True, margin=None, align=None):
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


def pill(text, color="#315B7D", bg_color="#EAF4FF"):
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
            flex_text(text, size="xxs", color=color, weight="bold", align="center", wrap=False)
        ],
    }


def section_title(title, accent="#FF7A45"):
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
            flex_text(title, size="sm", color="#111111", weight="bold"),
        ],
    }


def help_filter_row(label, desc, example=None):
    contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                pill(label, color="#C93D47", bg_color="#FFF0F1"),
            ],
        },
        flex_text(desc, size="xxs", color="#555555", margin="xs"),
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
                flex_text(example, size="xxs", color="#222222"),
            ],
        })
    return {
        "type": "box",
        "layout": "vertical",
        "paddingBottom": "8px",
        "contents": contents,
    }


def body_row(desc):
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "paddingAll": "9px",
        "cornerRadius": "8px",
        "backgroundColor": "#F8FAFC",
        "contents": [
            flex_text(desc, size="xxs", color="#555555"),
        ],
    }


def help_docs_footer(user_id=None):
    from modules.config_loader import SUPPORT_PAGE

    label = help_ui("docs_button", user_id)
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
                    flex_text(label, size="sm", color="#FFFFFF", weight="bold", align="center", wrap=False),
                ],
            }
        ],
    }


def standard_bubble(contents, size="mega"):
    return {
        "type": "bubble",
        "size": size,
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": "16px",
            "contents": contents,
        },
    }


def standard_help_bubble(title, subtitle, sections, alt_text, user_id=None, docs_button=True):
    body_contents = [
        standard_header_box(title, subtitle),
    ]
    for title, rows in sections:
        body_contents.append(section_title(title))
        body_contents.append({
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": rows,
        })
    bubble = standard_bubble(body_contents, "giga")
    if docs_button:
        bubble["footer"] = help_docs_footer(user_id)
    return FlexMessage(
        alt_text=alt_text,
        contents=FlexContainer.from_dict(bubble),
    )


def standard_header_box(title, subtitle=None, accent="#111827", title_color="#FFFFFF"):
    contents = [
        flex_text(title, size="lg", color=title_color, weight="bold"),
    ]
    if subtitle:
        contents.append(flex_text(subtitle, size="xs", color="#D1D5DB", margin="xs"))
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "paddingAll": "14px",
        "cornerRadius": "8px",
        "backgroundColor": accent,
        "contents": contents,
    }


def song_type_icon(chart_type, width="42px", height="12px", margin=None):
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


def metric_card(label, value, value_color=COLOR_TEXT_PRIMARY, bg_color="#F8FAFC", flex=None):
    card = {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "paddingAll": "11px",
        "cornerRadius": "8px",
        "backgroundColor": bg_color,
        "contents": [
            flex_text(label, size="xxs", color=COLOR_TEXT_MUTED),
            flex_text(str(value), size="sm", color=value_color, weight="bold"),
        ],
    }
    if flex is not None:
        card["flex"] = flex
    return card


def metric_grid(cards):
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


def flex_action_button(action, style="primary", color=COLOR_BRAND):
    button = {
        "type": "button",
        "height": "sm",
        "style": style,
        "action": action,
    }
    if style == "primary":
        button["color"] = color
    return button


def pill_action_box(label, action, bg_color="#315B7D", text_color=COLOR_TEXT_INVERSE,
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


def round_icon_action(label, action, bg_color="#315B7D", text_color=COLOR_TEXT_INVERSE):
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
            flex_text(label, size="md", color=text_color, weight="bold", align="center", wrap=False),
        ],
    }


def standard_action_bubble(title, subtitle, body_text, alt_text, actions=None, note_text=None,
                            accent=COLOR_BRAND, user_id=None):
    sections = [
        (help_ui("function", user_id), [
            body_row(body_text)
        ])
    ]
    if note_text:
        sections.append((help_ui("notes", user_id), [
            body_row(note_text)
        ]))

    body_contents = [
        standard_header_box(title, subtitle),
    ]
    for section_label, rows in sections:
        body_contents.append(section_title(section_label, accent=accent))
        body_contents.append({
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": rows,
        })

    bubble = standard_bubble(body_contents)
    if actions:
        bubble["footer"] = {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "12px",
            "contents": actions,
        }
    return FlexMessage(alt_text=alt_text, contents=FlexContainer.from_dict(bubble))
