"""
权限请求Flex消息模块

生成权限请求的Flex消息，包含"承認"（同意）和"拒否"（拒绝）按钮
"""

from linebot.v3.messaging import FlexMessage, FlexContainer
from modules.message_manager import (
    get_perm_request_notification_alt_text,
    get_multilingual_text,
    perm_request_notification_title_text,
    perm_request_notification_subtitle_text,
    perm_request_accept_button_text,
    perm_request_reject_button_text
)


def generate_perm_request_message(requests: list, user_id: str = None) -> FlexMessage:
    """
    生成权限请求Flex消息（极简黑白风格）

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
        # 用户信息box
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
                    "color": "#666666",
                    "margin": "xs"
                },
                {
                    "type": "text",
                    "text": req.get("timestamp", ""),
                    "size": "xs",
                    "color": "#999999",
                    "margin": "xs"
                }
            ]
        }

        # 按钮行
        accept_label = get_multilingual_text(perm_request_accept_button_text, user_id)
        reject_label = get_multilingual_text(perm_request_reject_button_text, user_id)

        button_row = {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "margin": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": accept_label,
                        "data": f"accept-perm-request {req['request_id']}"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": reject_label,
                        "data": f"reject-perm-request {req['request_id']}"
                    }
                }
            ]
        }

        request_rows.append(info_box)
        request_rows.append(button_row)

        # 添加分隔线（除了最后一个）
        if idx < len(requests) - 1:
            request_rows.append({
                "type": "separator",
                "margin": "md"
            })

    # 获取标题和副标题
    title = get_multilingual_text(perm_request_notification_title_text, user_id)
    count = len(requests)
    subtitle = get_multilingual_text(perm_request_notification_subtitle_text, user_id).format(count=count)

    # 创建bubble（极简黑白风格）
    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": title,
                    "weight": "bold",
                    "size": "md"
                },
                {
                    "type": "text",
                    "text": subtitle,
                    "size": "xs",
                    "color": "#999999",
                    "margin": "sm"
                }
            ],
            "paddingAll": "16px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": request_rows,
            "paddingAll": "16px"
        }
    }

    return FlexMessage(
        alt_text=get_perm_request_notification_alt_text(len(requests), user_id),
        contents=FlexContainer.from_dict(bubble)
    )
