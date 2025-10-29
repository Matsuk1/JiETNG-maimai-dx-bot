from linebot.v3.messaging import (
    FlexMessage,
    TextMessage,
    FlexBubble,
    FlexBox,
    FlexText,
    FlexButton,
    FlexSeparator,
    FlexCarousel,
    URIAction
)
from modules.reply_text import store_error

def generate_store_buttons(alt_text, store_list, group_size=6):
    """
    生成机厅列表 Flex Message（极简黑白风格）
    使用 LINE SDK v3 对象而非字典，确保类型正确

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
        store_contents = []
        for idx, store in enumerate(group):
            name = store.get("name", "Unknown")
            address = store.get("address", "")
            distance = store.get("distance", "")
            map_url = store.get("map_url", "")

            # 验证和修复 URL：确保是有效的 https URL
            if not map_url or not isinstance(map_url, str) or not map_url.startswith("http") or len(map_url) < 10:
                map_url = "https://www.google.com/maps"

            # 创建单行（使用 SDK 对象）
            store_row = FlexBox(
                layout="horizontal",
                spacing="md",
                margin="md" if idx > 0 else "none",
                contents=[
                    # 左侧：店名、地址和距离
                    FlexBox(
                        layout="vertical",
                        flex=3,
                        contents=[
                            FlexText(
                                text=name,
                                size="sm",
                                weight="bold",
                                wrap=True,
                                max_lines=2
                            ),
                            FlexText(
                                text=address,
                                size="xs",
                                color="#666666",
                                margin="xs",
                                wrap=True,
                                max_lines=2
                            ),
                            FlexText(
                                text=distance,
                                size="xs",
                                color="#999999",
                                margin="xs"
                            )
                        ]
                    ),
                    # 右侧：地图按钮
                    FlexButton(
                        flex=0,
                        style="primary",
                        height="sm",
                        action=URIAction(
                            label="MAP",
                            uri=map_url
                        )
                    )
                ]
            )

            store_contents.append(store_row)

            # 添加分隔线（除了最后一个）
            if idx < len(group) - 1:
                store_contents.append(FlexSeparator(margin="sm"))

        # 创建 bubble（使用 SDK 对象）
        bubble = FlexBubble(
            size="mega",
            header=FlexBox(
                layout="vertical",
                padding_all="16px",
                contents=[
                    FlexText(
                        text=alt_text,
                        weight="bold",
                        size="lg"
                    ),
                    FlexText(
                        text=f"Page {page_num}/{total_pages} • {len(group)} stores",
                        size="xs",
                        color="#999999",
                        margin="sm"
                    )
                ]
            ),
            body=FlexBox(
                layout="vertical",
                padding_all="16px",
                contents=store_contents
            )
        )

        bubbles.append(bubble)

    # 创建最终消息
    if len(bubbles) == 1:
        # 只有一页，直接返回 bubble
        contents = bubbles[0]
    else:
        # 多页，使用 carousel
        contents = FlexCarousel(contents=bubbles)

    return FlexMessage(
        alt_text=alt_text,
        contents=contents
    )
