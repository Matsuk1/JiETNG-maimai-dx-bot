"""
好友申请Flex消息模块

生成好友申请的Flex消息，包含"承認"（同意）和"拒否"（拒绝）按钮
采用与friend_list相同的极简黑白风格
"""

from linebot.v3.messaging import FlexMessage, FlexContainer
from modules.reply_text import get_friend_request_alt_text


def generate_friend_request_message(requests: list, user_id: str = None) -> FlexMessage:
    """
    生成好友申请Flex消息（极简黑白风格）

    Args:
        requests: 好友申请列表
            [
                {
                    "from_user_id": "U1234567890",
                    "from_user_name": "用户A",
                    "timestamp": "2025-01-01 12:00:00",
                    "request_id": "20250101120000_U1234567890"
                }
            ]

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
                    "text": req.get("from_user_name", "Unknown User"),
                    "size": "sm",
                    "weight": "bold",
                    "wrap": True,
                    "maxLines": 2
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
                        "type": "message",
                        "label": "承認",
                        "text": f"accept-request {req['request_id']}"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "拒否",
                        "text": f"reject-request {req['request_id']}"
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
                    "text": "フレンド申請 • Friend Requests",
                    "weight": "bold",
                    "size": "md"
                },
                {
                    "type": "text",
                    "text": f"{len(requests)} new request{'s' if len(requests) > 1 else ''}",
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
        alt_text=get_friend_request_alt_text(len(requests), user_id),
        contents=FlexContainer.from_dict(bubble)
    )
