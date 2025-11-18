import json
from PIL import Image, ImageDraw, ImageFont
from modules.record_generator import create_thumbnail
from modules.image_manager import *
from modules.image_cache import paste_icon_optimized, get_cached_image
from modules.config_loader import ICON_TYPE_DIR

def song_info_generate(song_json, played_data = []):
    cover_url = song_json["cover_url"]
    cover_img = get_cached_image(cover_url)

    if not cover_img:
        cover_img = Image.new("RGBA", (200, 200), (200, 200, 200))
    else:
        cover_img = cover_img.convert("RGBA")

    img1 = _render_basic_info_image(song_json, cover_img)

    if not played_data:
        img2 = resize_by_width(_generate_song_table_image(song_json), 1200)

    else:
        img2 = resize_by_width(_makeup_played_data(played_data), 600)

    song_img = compose_images([img1, img2])

    return song_img

def _makeup_played_data(played_data, gap=20):
    rcd_imgs = []
    for rcd in played_data:
        rcd_imgs.append(create_thumbnail(rcd))

    widths = [img.width for img in rcd_imgs]
    heights = [img.height for img in rcd_imgs]

    max_width = max(widths)
    total_height = sum(heights) + gap * (len(rcd_imgs) - 1)

    # 创建新图片
    new_img = Image.new("RGB", (max_width, total_height), color=(255, 255, 255))

    # 逐张粘贴
    current_y = 0
    for img in rcd_imgs:
        new_img.paste(img, (0, current_y))
        current_y += img.height + gap

    return new_img

def _render_basic_info_image(song_json, cover_img):
    # 参数设定
    canvas_width = 1000
    canvas_height = 265
    block_height = 260
    margin = 30
    text_gap = 35

    # 创建画布
    img = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 封面图处理
    cover_size = 200
    large_cover = cover_img.resize((cover_size, cover_size))
    cover_x = margin
    cover_y = margin
    img.paste(large_cover, (cover_x, cover_y), large_cover)

    paste_icon_optimized(
        img, song_json, key='type',
        size=(100, 30),
        position=(cover_x + cover_size - 100, cover_y + cover_size - 30),
        save_dir=ICON_TYPE_DIR,
        url_func=lambda value: "https://maimaidx.jp/maimai-mobile/img/music_standard.png" if value == "std" else "https://maimaidx.jp/maimai-mobile/img/music_dx.png"
    )

    # 文字区域
    text_x = cover_x + cover_size + text_gap
    text_y = cover_y
    title = song_json.get("title", "タイトル不明")
    artist = song_json.get("artist", "アーティスト不明")
    category = song_json.get("category", "類別不明")
    bpm = song_json.get('bpm', '-')
    version = song_json.get("version", "バージョン不明")

    info_text = [
        f"アーティスト: {artist}",
        f"類別: {category}",
        f"BPM: {bpm}",
        f"バージョン: {version}"
    ]

    # 标题
    draw.text((text_x, text_y), title, font=font_title, fill=(0, 0, 0))
    title_width = draw.textlength(title, font=font_title)

    # 横线
    line_y = text_y + 45
    draw.line([(text_x, line_y), (text_x + max(title_width+10, 600), line_y)], fill=(100, 100, 100), width=2)

    draw_aligned_colon_text(
        draw,
        lines=info_text,
        top_left=(text_x, line_y + 15),  # 左上角起始坐标
        font=font_info,
        spacing=8,
        fill=(0, 0, 0)
    )

    return img

def _generate_song_table_image(song_json, scale_width=1.5, scale_height=2.0):
    font = ImageFont.truetype(FONT_PATH, 28)

    headers = ["Difficulty", "Level", "Total", "TAP", "HOLD", "SLIDE", "TOUCH", "BREAK", "JP", "INTL", "USA", "CN"]
    base_col_widths = [160, 90, 80, 80, 80, 80, 80, 80, 60, 70, 60, 60]
    col_widths = [int(w * scale_width) for w in base_col_widths]
    row_height = int(48 * scale_height)
    col_offsets = [sum(col_widths[:i]) for i in range(len(col_widths))]  # 缓存列起始坐标

    total_width = sum(col_widths)
    total_height = (len(song_json["sheets"]) + 1) * row_height

    image = Image.new("RGB", (total_width, total_height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    block_colors = {
        "info": (220, 240, 255),
        "notes": (240, 255, 240),
        "regions": (255, 240, 240)
    }

    block_ranges = {
        "info": range(0, 2),
        "notes": range(2, 8),
        "regions": range(8, 12)
    }

    # 绘制表头
    for i, header in enumerate(headers):
        x = col_offsets[i]
        fill = (
            block_colors["info"] if i in block_ranges["info"] else
            block_colors["notes"] if i in block_ranges["notes"] else
            block_colors["regions"]
        )
        draw.rectangle([x, 0, x + col_widths[i], row_height], fill=fill)
        w = draw.textlength(header, font=font)
        draw.text((x + (col_widths[i] - w) // 2, row_height // 4), header, font=font, fill=(0, 0, 0))

    # 绘制每一行
    for row_idx, sheet in enumerate(song_json["sheets"]):
        y = (row_idx + 1) * row_height
        notes = sheet["noteCounts"]
        regions = sheet.get("regions", {})

        data = [
            sheet["difficulty"].capitalize(),
            f"{sheet['internalLevelValue']:.1f}",
            notes["total"],
            notes["tap"],
            notes["hold"],
            notes["slide"],
            notes["touch"],
            notes["break"],
            "✓" if regions.get("jp") else "✗",
            "✓" if regions.get("intl") else "✗",
            "✓" if regions.get("usa") else "✗",
            "✓" if regions.get("cn") else "✗"
        ]

        for col_idx, cell in enumerate(data):
            x = col_offsets[col_idx]
            if col_idx in block_ranges["info"]:
                fill = (240, 250, 255)
            elif col_idx in block_ranges["notes"]:
                fill = (250, 255, 250)
            else:
                fill = (255, 250, 250)
            draw.rectangle([x, y, x + col_widths[col_idx], y + row_height], fill=fill)

            text = str(cell)
            w = draw.textlength(text, font=font)
            draw.text((x + (col_widths[col_idx] - w) // 2, y + row_height // 4), text, font=font, fill=(0, 0, 0))

    return image

def _render_song_info_small_img(song_json, cover_img):
    # 参数设定
    canvas_width = 1000
    canvas_height = 265
    block_height = 260
    margin = 30
    text_gap = 35

    # 创建画布
    img = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 封面图处理
    cover_size = 200
    large_cover = cover_img.resize((cover_size, cover_size))
    cover_x = margin
    cover_y = margin
    img.paste(large_cover, (cover_x, cover_y), large_cover)

    levels = []
    for sheet in song_json['sheets']:
        levels.append(sheet['internalLevelValue'])

    paste_icon_optimized(
        img, song_json, key='type',
        size=(100, 30),
        position=(cover_x + cover_size - 100, cover_y + cover_size - 30),
        save_dir=ICON_TYPE_DIR,
        url_func=lambda value: "https://maimaidx.jp/maimai-mobile/img/music_standard.png" if value == "std" else "https://maimaidx.jp/maimai-mobile/img/music_dx.png"
    )

    # 文字区域
    text_x = cover_x + cover_size + text_gap
    text_y = cover_y
    title = song_json.get("title", "タイトル不明")
    artist = song_json.get("artist", "アーティスト不明")
    bpm = f"BPM: {song_json.get('bpm', '-')}"
    category = song_json.get("category", "類別不明")
    levels_str = " / ".join(f"{level:.1f}" for level in levels)

    # 标题
    draw.text((text_x, text_y), title, font=font_title, fill=(0, 0, 0))
    title_width = draw.textlength(title, font=font_title)

    # 横线
    line_y = text_y + 45
    draw.line([(text_x, line_y), (text_x + max(title_width+10, 600), line_y)], fill=(100, 100, 100), width=2)

    # 其他信息
    draw.text((text_x, line_y + 15), artist, font=font_info, fill=(0, 0, 0))
    draw.text((text_x, line_y + 50), bpm, font=font_info, fill=(0, 0, 0))
    draw.text((text_x, line_y + 85), category, font=font_info, fill=(0, 0, 0))
    draw.text((text_x, line_y + 120), levels_str, font=font_info, fill=(0, 0, 0))

    return img

def generate_version_list(songs_json):
    # 批量并发下载所有封面（速度优化）
    from modules.image_cache import batch_download_images
    cover_urls = [song["cover_url"] for song in songs_json]
    batch_download_images(cover_urls, max_workers=20)  # 预先下载所有封面

    song_imgs = []

    for song in songs_json:
        cover_url = song["cover_url"]
        cover_img = get_cached_image(cover_url)

        if not cover_img:
            cover_img = Image.new("RGBA", (200, 200), (200, 200, 200))
        else:
            cover_img = cover_img.convert("RGBA")

        song_imgs.append(wrap_in_rounded_background(_render_song_info_small_img(song, cover_img)))

    return _concat_images_grid(song_imgs)

def _concat_images_grid(image_list, cols=4, margin=20, inner_gap=10, bg_color=(255, 255, 255)):
    """
    将图像以网格形式拼接（默认每行4张），每块之间空出间距。
    
    参数:
        image_list: 图像对象列表（PIL.Image）
        cols: 每行图片数量
        margin: 整体外边距
        inner_gap: 图片之间的间距
        bg_color: 背景颜色
    """
    if not image_list:
        raise ValueError("图片列表不能为空")

    # 计算总行数
    rows = (len(image_list) + cols - 1) // cols

    # 获取单个格子大小（按每行最大宽高对齐）
    widths = []
    heights = []
    for r in range(rows):
        group = image_list[r*cols:(r+1)*cols]
        widths.append(sum(img.width for img in group) + inner_gap * (len(group)-1))
        heights.append(max(img.height for img in group))
    total_width = max(widths)
    total_height = sum(heights) + inner_gap * (rows-1)

    # 加上外边距
    final_image = Image.new(
        "RGB",
        (total_width + 2*margin, total_height + 2*margin),
        bg_color
    )

    # 拼接
    y_offset = margin
    for r in range(rows):
        group = image_list[r*cols:(r+1)*cols]
        x_offset = margin
        max_h = max(img.height for img in group)
        for img in group:
            final_image.paste(img, (x_offset, y_offset + (max_h - img.height)//2))
            x_offset += img.width + inner_gap
        y_offset += max_h + inner_gap

    return final_image
