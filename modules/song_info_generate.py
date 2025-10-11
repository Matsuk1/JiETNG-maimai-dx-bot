import json
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from modules.record_picture_generate import create_thumbnail
from modules.img_console import *

def song_info_generate(song_json, played_data = []):
    image_name = song_json["imageName"]
    cover_url = f"https://shama.dxrating.net/images/cover/v2/{image_name}.jpg"
    response = requests.get(cover_url)
    cover_img = Image.open(BytesIO(response.content)).convert("RGBA")

    img1 = render_basic_info_image(song_json, cover_img)

    if not played_data:
        img2 = resize_by_width(generate_song_table_image(song_json), 1200)

    else:
        img2 = resize_by_width(makeup_played_data(played_data).convert('RGBA'), 600)

    song_img = combine_with_rounded_background(img1, img2)

    return song_img

def makeup_played_data(played_data, gap=20):
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

def render_basic_info_image(song_json, cover_img):
    # 参数设定
    canvas_width = 1000
    canvas_height = 265
    block_height = 260
    margin = 30
    text_gap = 35

    # 创建画布
    img = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # 封面图处理
    cover_size = 200
    large_cover = cover_img.resize((cover_size, cover_size))
    cover_x = margin
    cover_y = margin
    img.paste(large_cover, (cover_x, cover_y), large_cover)

    paste_icon(
        img, song_json, key='type',
        size=(100, 30),
        position=(cover_x + cover_size - 100, cover_y + cover_size - 30),
        save_dir='./assets/icon/kind',
        url_func=lambda value: "https://maimaidx.jp/maimai-mobile/img/music_standard.png" if value == "std" else "https://maimaidx.jp/maimai-mobile/img/music_dx.png",
        verify=False
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

def generate_song_table_image(song_json, scale_width=1.5, scale_height=2.0):
    font = ImageFont.truetype(font_path, 28)

    headers = ["Difficulty", "Level", "Total", "TAP", "HOLD", "SLIDE", "TOUCH", "BREAK", "JP", "CN", "INTL"]
    base_col_widths = [160, 90, 80, 80, 80, 80, 80, 80, 60, 60, 70]
    col_widths = [int(w * scale_width) for w in base_col_widths]
    row_height = int(48 * scale_height)
    col_offsets = [sum(col_widths[:i]) for i in range(len(col_widths))]  # 缓存列起始坐标

    total_width = sum(col_widths)
    total_height = (len(song_json["sheets"]) + 1) * row_height

    image = Image.new("RGBA", (total_width, total_height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)

    block_colors = {
        "info": (220, 240, 255, 255),
        "notes": (240, 255, 240, 255),
        "regions": (255, 240, 240, 255)
    }

    block_ranges = {
        "info": range(0, 2),
        "notes": range(2, 8),
        "regions": range(8, 11)
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
            "✓" if regions.get("cn") else "✗",
            "✓" if regions.get("intl") else "✗",
        ]

        for col_idx, cell in enumerate(data):
            x = col_offsets[col_idx]
            if col_idx in block_ranges["info"]:
                fill = (240, 250, 255, 240)
            elif col_idx in block_ranges["notes"]:
                fill = (250, 255, 250, 240)
            else:
                fill = (255, 250, 250, 240)
            draw.rectangle([x, y, x + col_widths[col_idx], y + row_height], fill=fill)

            text = str(cell)
            w = draw.textlength(text, font=font)
            draw.text((x + (col_widths[col_idx] - w) // 2, y + row_height // 4), text, font=font, fill=(0, 0, 0))

    return image

def render_song_info_small_img(song_json, cover_img):
    # 参数设定
    canvas_width = 1000
    canvas_height = 265
    block_height = 260
    margin = 30
    text_gap = 35

    # 创建画布
    img = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 0))
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

    paste_icon(
        img, song_json, key='type',
        size=(100, 30),
        position=(cover_x + cover_size - 100, cover_y + cover_size - 30),
        save_dir='./assets/icon/kind',
        url_func=lambda value: "https://maimaidx.jp/maimai-mobile/img/music_standard.png" if value == "std" else "https://maimaidx.jp/maimai-mobile/img/music_dx.png",
        verify=False
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
    song_imgs = []

    for song in songs_json:
        image_name = song["imageName"]
        cover_url = f"https://shama.dxrating.net/images/cover/v2/{image_name}.jpg"
        response = requests.get(cover_url)
        cover_img = Image.open(BytesIO(response.content)).convert("RGBA")

        song_imgs.append(wrap_in_rounded_background(render_song_info_small_img(song, cover_img)))

    return wrap_in_rounded_background(concat_images_vertically_with_margin(song_imgs))

def concat_images_vertically_with_margin(image_list, margin=10, bg_color=(255, 255, 255, 0)):
    if not image_list:
        raise ValueError("图片列表不能为空")

    # 分组，每 6 张为一组
    groups = [image_list[i:i+6] for i in range(0, len(image_list), 6)]
    row_images = []

    for group in groups:
        # 每组横向拼接
        max_height = max(img.height for img in group)
        total_width = sum(img.width for img in group) + margin * (len(group) - 1)
        row_img = Image.new("RGBA", (total_width, max_height), bg_color)

        current_x = 0
        for img in group:
            row_img.paste(img, (current_x, 0), img)
            current_x += img.width + margin

        row_images.append(row_img)

    # 将横向拼接好的每一行纵向拼接
    max_width = max(img.width for img in row_images)
    total_height = sum(img.height for img in row_images) + margin * (len(row_images) - 1)
    final_image = Image.new("RGBA", (max_width, total_height), bg_color)

    current_y = 0
    for img in row_images:
        final_image.paste(img, (0, current_y), img)
        current_y += img.height + margin

    return final_image
