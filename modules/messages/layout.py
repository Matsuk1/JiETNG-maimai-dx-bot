"""Shared LINE Flex layout components, independent of business data loading."""
from linebot.v3.messaging import FlexMessage, FlexContainer
from modules.i18n import localized_catalog, select_text as get_multilingual_text


COLOR_TEXT_PRIMARY = "#292724"
COLOR_TEXT_SECONDARY = "#56514B"
COLOR_TEXT_MUTED = "#7F7970"
COLOR_TEXT_INVERSE = "#FFFAF7"
COLOR_SUCCESS = "#2F7D64"
COLOR_DANGER = "#B74E4E"
COLOR_WARNING = "#A86B22"
COLOR_BRAND = "#C96442"
COLOR_BRAND_STRONG = "#A84D31"
COLOR_BRAND_SOFT = "#F6E7E0"
COLOR_TIP = "#765A46"
COLOR_TIP_BG = "#F3ECE6"
COLOR_AD_BG = "#F8EDDB"
COLOR_SURFACE = "#FDFCFB"
COLOR_SURFACE_SOFT = "#F6F2ED"
COLOR_BORDER = "#DED8D0"

HELP_UI_TEXT = localized_catalog("message_manager.help_ui")


def help_ui(key, user_id=None):
    return get_multilingual_text(HELP_UI_TEXT[key], user_id)


def flex_text(text, size="sm", color=COLOR_TEXT_PRIMARY, weight=None, wrap=True, margin=None, align=None):
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


def pill(text, color=COLOR_BRAND_STRONG, bg_color=COLOR_BRAND_SOFT):
    return {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": bg_color,
        "cornerRadius": "999px",
        "paddingTop": "3px",
        "paddingBottom": "3px",
        "paddingStart": "8px",
        "paddingEnd": "8px",
        "contents": [
            flex_text(text, size="xxs", color=color, weight="bold", align="center", wrap=False)
        ],
    }


def section_title(title, accent=COLOR_BRAND):
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
                "width": "3px",
                "height": "17px",
                "cornerRadius": "2px",
                "backgroundColor": accent,
                "justifyContent": "center",
                "alignItems": "center",
                "contents": [{"type": "filler"}],
            },
            flex_text(title, size="sm", color=COLOR_TEXT_PRIMARY, weight="bold"),
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
        flex_text(desc, size="xxs", color=COLOR_TEXT_SECONDARY, margin="xs"),
    ]
    if example:
        contents.append({
            "type": "box",
            "layout": "vertical",
            "margin": "xs",
            "paddingAll": "7px",
            "cornerRadius": "8px",
            "backgroundColor": COLOR_SURFACE_SOFT,
            "contents": [
                flex_text(example, size="xxs", color=COLOR_TEXT_PRIMARY),
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
        "paddingTop": "9px",
        "paddingBottom": "9px",
        "contents": [
            flex_text(desc, size="xxs", color=COLOR_TEXT_SECONDARY),
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
                "cornerRadius": "9px",
                "backgroundColor": COLOR_BRAND,
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
                    flex_text(label, size="sm", color=COLOR_TEXT_INVERSE, weight="bold", align="center", wrap=False),
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
            "spacing": "none",
            "paddingAll": "20px",
            "backgroundColor": COLOR_SURFACE,
            "contents": contents,
        },
        "styles": {
            "body": {"backgroundColor": COLOR_SURFACE},
            "footer": {"backgroundColor": COLOR_SURFACE},
        },
    }


def standard_help_bubble(title, subtitle, sections, alt_text, user_id=None, docs_button=True):
    body_contents = [
        standard_product_header(title, subtitle),
    ]
    for title, rows in sections:
        body_contents.append(section_title(title))
        body_contents.append(separated_row_group(rows))
    bubble = standard_bubble(body_contents, "giga")
    if docs_button:
        bubble["footer"] = help_docs_footer(user_id)
    return FlexMessage(
        alt_text=alt_text,
        contents=FlexContainer.from_dict(bubble),
    )


def standard_header_box(title, subtitle=None, accent=COLOR_BRAND, title_color=COLOR_TEXT_PRIMARY):
    contents = [
        flex_text(title, size="lg", color=title_color, weight="bold"),
    ]
    if subtitle:
        contents.append(flex_text(subtitle, size="xs", color=COLOR_TEXT_MUTED, margin="xs"))
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "paddingStart": "2px",
        "paddingEnd": "2px",
        "paddingTop": "4px",
        "paddingBottom": "14px",
        "borderWidth": "0px",
        "backgroundColor": COLOR_SURFACE,
        "contents": contents,
    }


def standard_product_header(title, subtitle=None, accent=COLOR_BRAND):
    """Sparse editorial header shared by user-facing command and help cards."""
    heading = {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "paddingStart": "2px",
        "paddingEnd": "2px",
        "paddingTop": "2px",
        "paddingBottom": "13px",
        "contents": [
            flex_text(title, size="xl", color=COLOR_TEXT_PRIMARY, weight="bold"),
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [pill("JiETNG", color=accent, bg_color=COLOR_BRAND_SOFT)],
            },
        ],
    }
    if subtitle and subtitle != "JiETNG":
        heading["contents"].append(
            flex_text(subtitle, size="xs", color=COLOR_TEXT_MUTED)
        )
    return heading


def separated_row_group(rows):
    """Use whitespace and hairline separators instead of a stack of mini cards."""
    contents = []
    for index, row in enumerate(rows):
        if index:
            contents.append({"type": "separator", "color": COLOR_BORDER})
        contents.append(row)
    return {
        "type": "box",
        "layout": "vertical",
        "paddingStart": "2px",
        "paddingEnd": "2px",
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


def metric_card(label, value, value_color=COLOR_TEXT_PRIMARY, bg_color=COLOR_SURFACE_SOFT, flex=None):
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


def pill_action_box(label, action, bg_color=COLOR_BRAND, text_color=COLOR_TEXT_INVERSE,
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


def round_icon_action(label, action, bg_color=COLOR_BRAND, text_color=COLOR_TEXT_INVERSE):
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
        standard_product_header(title, subtitle, accent=accent),
    ]
    for section_label, rows in sections:
        body_contents.append(section_title(section_label, accent=accent))
        body_contents.append(separated_row_group(rows))

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
