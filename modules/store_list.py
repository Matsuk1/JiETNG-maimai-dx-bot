from linebot.v3.messaging import FlexMessage, TextMessage, FlexContainer
from modules.reply_text import store_error

def generate_store_buttons(alt_text, store_list, group_size=6):
    """
    生成机厅列表 Flex Message（极简黑白风格）

    Args:
        alt_text: 替代文本
        store_list: 机厅列表 [{"name": "店名", "address": "地址", "distance": "距离", "map_url": "地图链接"}]
        group_size: 每页显示的机厅数（默认6个）

    Returns:
        FlexMessage
    """
    if not store_list:
        return store_error

    bubbles = []
    total_pages = (len(store_list) + group_size - 1) // group_size

    for page_idx in range(0, len(store_list), group_size):
        group = store_list[page_idx:page_idx + group_size]
        page_num = page_idx // group_size + 1

        # 创建机厅行
        store_rows = []
        for idx, store in enumerate(group):
            name = store.get("name", "Unknown")
            address = store.get("address", "")
            distance = store.get("distance", "")
            map_url = store.get("map_url", "")

            # 创建单行（第一个不需要上边距）
            row = {
                "type": "box",
                "layout": "horizontal",
                "spacing": "md",
                "margin": "md" if idx > 0 else "none",
                "contents": [
                    # 左侧：店名、地址和距离
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
                                "text": address,
                                "size": "xs",
                                "color": "#666666",
                                "margin": "xs",
                                "wrap": True,
                                "maxLines": 2
                            },
                            {
                                "type": "text",
                                "text": distance,
                                "size": "xs",
                                "color": "#999999",
                                "margin": "xs"
                            }
                        ]
                    },
                    # 右侧：地图按钮
                    {
                        "type": "button",
                        "flex": 0,
                        "style": "primary",
                        "height": "sm",
                        "action": {
                            "type": "uri",
                            "label": "MAP",
                            "uri": map_url if map_url else "https://www.google.com/maps"
                        }
                    }
                ]
            }

            # 添加分隔线（除了最后一个）
            if idx < len(group) - 1:
                store_rows.append(row)
                store_rows.append({
                    "type": "separator",
                    "margin": "sm"
                })
            else:
                store_rows.append(row)

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
                        "text": f"Page {page_num}/{total_pages} • {len(group)} stores",
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
                "contents": store_rows,
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
