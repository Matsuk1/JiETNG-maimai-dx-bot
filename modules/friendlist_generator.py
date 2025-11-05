from linebot.v3.messaging import FlexMessage, FlexContainer
from modules.message_manager import friend_error

def generate_friend_buttons(user_id, alt_text, button_list, group_size=6):
    """
    生成好友列表 Flex Message（极简黑白风格）

    Args:
        alt_text: 替代文本
        button_list: 按钮列表 [{"label": "Name [Rating]", "type": "text", "content": "command"}]
        group_size: 每页显示的好友数（默认6个）

    Returns:
        FlexMessage
    """
    if not button_list:
        return friend_error(user_id)

    bubbles = []
    total_pages = (len(button_list) + group_size - 1) // group_size

    for page_idx in range(0, len(button_list), group_size):
        group = button_list[page_idx:page_idx + group_size]
        page_num = page_idx // group_size + 1

        # 创建好友行
        friend_rows = []
        for idx, friend in enumerate(group):
            # 解析信息
            label = friend["label"]
            if "[" in label and "]" in label:
                name = label.split("[")[0].strip()
                rating = label.split("[")[1].split("]")[0].strip()
            else:
                name = label
                rating = "----"

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
                    {
                        "type": "button",
                        "flex": 0,
                        "style": "secondary",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "→",
                            "text": friend["content"]
                        }
                    }
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
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": alt_text,
                        "weight": "bold",
                        "size": "lg"
                    },
                    {
                        "type": "text",
                        "text": f"Page {page_num}/{total_pages} • {len(group)} friends",
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
