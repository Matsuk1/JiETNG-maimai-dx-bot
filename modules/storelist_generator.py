import urllib.parse
import re
from linebot.v3.messaging import FlexMessage, FlexContainer
from modules.messages.service import store_error
from modules.messages.layout import (
    COLOR_BORDER,
    COLOR_BRAND_SOFT,
    COLOR_BRAND_STRONG,
    COLOR_SURFACE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    standard_product_header,
)

def generate_google_map_url(name: str, address: str = "", lat: float = None, lng: float = None):
    """生成不会触发“是否在App中打开”的 Google 地图网页链接"""
    if lat is not None and lng is not None:
        query = f"{name} {lat},{lng}"
    elif address:
        query = f"{name} {address}"
    else:
        query = name

    encoded_query = urllib.parse.quote_plus(query)
    return f"https://www.google.com/maps/search/?api=1&query={encoded_query}&hl=ja&source=web"


def parse_distance_km(distance_str: str) -> float:
    """从 '12.3 km' 或 '870 m' 解析数值（统一为 km）"""
    if not distance_str:
        return 9999.0
    distance_str = distance_str.strip().lower()
    match = re.search(r"([\d\.]+)", distance_str)
    if not match:
        return 9999.0
    value = float(match.group(1))
    if "m" in distance_str and "km" not in distance_str:
        return value / 1000.0
    return value


def generate_store_buttons(user_id, alt_text, store_list):
    """
    生成机厅列表 Flex Message。
    - 仅显示 30km 内机厅
    - 每页 5 个
    - 右侧 📍 按钮（白底黑边，固定高度 + 增宽）
    """
    if not store_list:
        return store_error(user_id)

    # 只保留 ≤30 km 的机厅
    filtered_stores = []
    for store in store_list:
        distance_str = store.get("distance", "")
        distance_km = parse_distance_km(distance_str)
        if distance_km <= 30:
            filtered_stores.append(store)

    if not filtered_stores:
        return store_error(user_id)

    # 每页 5 个
    group_size = 5
    total_pages = (len(filtered_stores) + group_size - 1) // group_size
    bubbles = []

    for page_idx in range(0, len(filtered_stores), group_size):
        group = filtered_stores[page_idx:page_idx + group_size]
        page_num = page_idx // group_size + 1

        store_rows = []
        for idx, store in enumerate(group):
            name = store.get("name", "Unknown")
            address = store.get("address", "")
            distance = store.get("distance", "")
            lat = store.get("lat")
            lng = store.get("lng")

            map_url = generate_google_map_url(name, address, lat, lng)

            # 左侧文字信息
            left_box_contents = [
                {"type": "text", "text": name, "size": "sm", "weight": "bold",
                 "color": COLOR_TEXT_PRIMARY, "wrap": True, "maxLines": 2}
            ]
            if address:
                left_box_contents.append({
                    "type": "text", "text": address, "size": "xs",
                    "color": COLOR_TEXT_MUTED, "margin": "xs", "wrap": True, "maxLines": 2
                })
            if distance:
                left_box_contents.append({
                    "type": "text", "text": distance, "size": "xs",
                    "color": COLOR_TEXT_MUTED, "margin": "xs"
                })

            # 按钮
            map_button = {
                "type": "box",
                "layout": "vertical",
                "flex": 0,
                "width": "32px",
                "height": "32px",
                "cornerRadius": "8px",
                "borderColor": "#E0B9A9",
                "borderWidth": "1px",
                "backgroundColor": COLOR_BRAND_SOFT,
                "justifyContent": "center",
                "alignItems": "center",
                "contents": [
                    {
                        "type": "text",
                        "text": "↗",
                        "weight": "bold",
                        "color": COLOR_BRAND_STRONG,
                        "align": "center",
                        "gravity": "center",
                        "size": "md",
                        "action": {
                            "type": "uri",
                            "label": "MAP",
                            "uri": map_url
                        }
                    }
                ]
            }

            row = {
                "type": "box",
                "layout": "horizontal",
                "spacing": "md",
                "margin": "md" if idx > 0 else "none",
                "contents": [
                    {"type": "box", "layout": "vertical",
                     "flex": 3, "contents": left_box_contents},
                    map_button
                ]
            }

            store_rows.append(row)
            if idx < len(group) - 1:
                store_rows.append({"type": "separator", "margin": "sm", "color": COLOR_BORDER})

        header_box = standard_product_header(
            alt_text,
            f"Page {page_num}/{total_pages} • {len(filtered_stores)} stores (≤30 km)",
        )

        # 基础 Bubble
        bubble = {
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [header_box, *store_rows],
                "paddingAll": "20px",
                "backgroundColor": COLOR_SURFACE
            },
            "styles": {"body": {"backgroundColor": COLOR_SURFACE}}
        }
        bubbles.append(bubble)

    flex_dict = bubbles[0] if len(bubbles) == 1 else {"type": "carousel", "contents": bubbles}
    return FlexMessage(alt_text=alt_text, contents=FlexContainer.from_dict(flex_dict))
