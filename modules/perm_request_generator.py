"""
权限请求Flex消息模块

生成权限请求的Flex消息，包含"承認"（同意）和"拒否"（拒绝）按钮
"""

from linebot.v3.messaging import FlexMessage, FlexContainer
from modules.i18n import language_catalog, select_text
from modules.messages.layout import (
    COLOR_BORDER,
    COLOR_BRAND,
    COLOR_DANGER,
    COLOR_SUCCESS,
    COLOR_SURFACE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    flex_action_button,
    standard_product_header,
)


def _text(key, user_id, **values):
    text = select_text(language_catalog(f"messages.{key}"), user_id)
    return text.format(**values) if values else text


def generate_perm_request_message(requests: list, user_id: str = None) -> FlexMessage:
    """
    生成权限请求 Flex 消息。

    Args:
        requests: 权限请求列表
            [
                {
                    "token_id": "jt_abc123",
                    "requester_name": "MyApp",
                    "timestamp": "2025-01-01 12:00:00",
                    "request_id": "20250101120000_jt_abc123"
                }
            ]
        user_id: 用户ID（用于多语言）

    Returns:
        FlexMessage对象
    """
    if not requests:
        return None

    # 创建请求列表
    request_rows = []
    for idx, req in enumerate(requests):
        # Request details stay as plain rows; only the actions are emphasized.
        info_box = {
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "margin": "md" if idx > 0 else "none",
            "contents": [
                {
                    "type": "text",
                    "text": req.get("requester_name", req.get("token_id", "Unknown")),
                    "size": "sm",
                    "weight": "bold",
                    "wrap": True,
                    "maxLines": 2
                },
                {
                    "type": "text",
                    "text": f"Token: {req.get('token_id', 'N/A')}",
                    "size": "xxs",
                    "color": COLOR_TEXT_PRIMARY,
                    "margin": "xs"
                },
                {
                    "type": "text",
                    "text": req.get("timestamp", ""),
                    "size": "xs",
                    "color": COLOR_TEXT_MUTED,
                    "margin": "xs"
                }
            ]
        }

        # 按钮行
        accept_label = _text("perm_request_accept_button_text", user_id)
        reject_label = _text("perm_request_reject_button_text", user_id)

        button_row = {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "margin": "sm",
            "contents": [
                flex_action_button(
                    {
                        "type": "postback",
                        "label": accept_label,
                        "data": f"accept-perm-request {req['request_id']}",
                    },
                    color=COLOR_SUCCESS,
                ),
                flex_action_button(
                    {
                        "type": "postback",
                        "label": reject_label,
                        "data": f"reject-perm-request {req['request_id']}",
                    },
                    style="secondary",
                    color=COLOR_DANGER,
                ),
            ]
        }

        request_rows.append(info_box)
        request_rows.append(button_row)

        # 添加分隔线（除了最后一个）
        if idx < len(requests) - 1:
            request_rows.append({
                "type": "separator",
                "margin": "md",
                "color": COLOR_BORDER,
            })

    # 获取标题和副标题
    title = _text("perm_request_notification_title_text", user_id)
    count = len(requests)
    subtitle = _text("perm_request_notification_subtitle_text", user_id, count=count)

    # Sparse warm bubble shared with the rest of JiETNG.
    bubble = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [standard_product_header(title, subtitle, accent=COLOR_BRAND), *request_rows],
            "paddingAll": "20px",
            "backgroundColor": COLOR_SURFACE,
        },
        "styles": {"body": {"backgroundColor": COLOR_SURFACE}},
    }

    return FlexMessage(
        alt_text=_text("perm_request_notification_alt_text", user_id, count=len(requests)),
        contents=FlexContainer.from_dict(bubble)
    )
