import json
import re
import sys
import os
import math
import logging

from PIL import Image, ImageDraw, ImageFont

from modules.config_loader import (
    LOGO_PATH,
    ICON_TYPE_DIR,
    ICON_SCORE_DIR,
    ICON_DX_STAR_DIR,
    ICON_COMBO_DIR,
    ICON_SYNC_DIR,
    ICON_BASE_DIR
)
from modules.image_cache import *
from modules.image_manager import *

# 获取logger
logger = logging.getLogger(__name__)

def _get_difficulty_color(difficulty):
    colors = {
        "basic": (149, 207, 71),     # 绿色
        "advanced": (243, 162, 7),   # 黄色
        "expert": (255, 129, 141),   # 红色
        "master": (159, 81, 219),    # 紫色
        "remaster": (239, 224, 255), # 白色
        "utage": (245, 46, 221)      # 粉色
    }
    return colors.get(difficulty.lower(), (200, 200, 200))

def create_thumbnail_in_line(song, thumb_size=(400, 100), scale=1.5):
    bg_color = (255, 255, 255)
    img = Image.new("RGB", thumb_size, bg_color)
    draw = ImageDraw.Draw(img)

    text_color = (0, 0, 0)

    # --- 基础分数 ---
    draw.text((15, 13), song['score'], fill=text_color, font=font_huge)
    draw.text((175, 21), song['dx_score'], fill=text_color, font=font_large)

    # --- score_icon 图标 ---
    # 根据缩略图尺寸动态计算图标大小
    paste_icon_optimized(
        img, song, key='score_icon',
        size=(90, 40),
        position=(305, 12),
        save_dir=ICON_SCORE_DIR,
        url_func=lambda value: f"https://maimaidx.jp/maimai-mobile/img/music_icon_{value}.png"
    )

    # --- 最下面的横线 ---
    # draw.line([(0, 100),(400, 100)], fill=, width=90)

    # --- combo_icon 图标 ---
    paste_icon_optimized(
        img, song, key='combo_icon',
        size=(40, 44),
        position=(19, 50),
        save_dir=ICON_COMBO_DIR,
        url_func=lambda value: f"https://maimaidx.jp/maimai-mobile/img/music_icon_{value}.png"
    )

    # --- sync_icon 图标 ---
    paste_icon_optimized(
        img, song, key='sync_icon',
        size=(40, 44),
        position=(65, 50),
        save_dir=ICON_SYNC_DIR,
        url_func=lambda value: f"https://maimaidx.jp/maimai-mobile/img/music_icon_{value}.png"
    )

    # --- dx_star 星星图标 ---
    if 'dx_score' in song and song['dx_score']:
        try:
            dx_score = eval(song['dx_score'].replace(",", ""))
            if 0 <= dx_score < 0.85:
                star_num = 0
            elif 0.85 <= dx_score < 0.9:
                star_num = 1
            elif 0.9 <= dx_score < 0.93:
                star_num = 2
            elif 0.93 <= dx_score < 0.95:
                star_num = 3
            elif 0.95 <= dx_score < 0.97:
                star_num = 4
            elif 0.97 <= dx_score <= 1:
                star_num = 5

            paste_icon_optimized(
                img, {'star': str(star_num)}, key='star',
                size=(109, 22),
                position=(129, 63),
                save_dir=ICON_DX_STAR_DIR,
                url_func=lambda value: f"https://maimaidx.jp/maimai-mobile/img/music_icon_dxstar_detail_{value}.png"
            )

        except Exception as e:
            logger.error(f"Error calculating dx_star: {e}")

    # --- 数值 ---
    draw.text((375, 61), f"{song['internalLevelValue']:.1f} → {song['ra']}", fill=(0, 0, 0), font=font_large, anchor="ra")

    # --- 边框 ---
    border_color = _get_difficulty_color(song['difficulty'])
    draw.rectangle([(0, 0), (thumb_size[0] - 1, thumb_size[1] - 1)], outline=border_color, width=5)

    final_img = img.convert("RGB")

    new_size = (int(final_img.width * scale), int(final_img.height * scale))
    final_img = final_img.resize(new_size, Image.Resampling.LANCZOS)

    return final_img

def create_thumbnail(song, thumb_size=(300, 150), padding=15):
    bg_color = _get_difficulty_color(song['difficulty'])
    img = Image.new("RGB", thumb_size, bg_color)
    draw = ImageDraw.Draw(img)

    text_color = (201, 123, 221) if song['difficulty'] == "remaster" else (255, 255, 255)

    # --- 封面 ---
    # 根据缩略图尺寸动态计算封面大小 (保持比例: 80/300 ≈ 0.267)
    cover_size = int(thumb_size[0] * 0.267)
    if 'cover_name' in song and song['cover_name']:
        try:
            # 使用新的 get_cover_image 函数（优先本地，不存在则下载）
            cover_img = get_cover_image(
                cover_url=song.get('cover_url'),
                cover_name=song['cover_name']
            )
            if cover_img:
                # 使用 LANCZOS 高质量重采样
                cover_img = round_corner(cover_img)
                cover_img = cover_img.resize((cover_size, cover_size), Image.Resampling.LANCZOS)
                img.paste(cover_img, (padding, padding), cover_img)
        except Exception as e:
            logger.error(f"Error loading cover image: {e}")

    # --- type 图标 ---
    # 根据封面尺寸动态计算图标大小
    type_width = int(cover_size * 0.5)  # 40/80 = 0.5
    type_height = int(cover_size * 0.15)  # 12/80 = 0.15
    paste_icon_optimized(
        img, song, key='type',
        size=(type_width, type_height),
        position=(padding + cover_size - type_width, padding + cover_size - type_height),
        save_dir=ICON_TYPE_DIR,
        url_func=lambda value: "https://maimaidx.jp/maimai-mobile/img/music_standard.png" if value == "std" else "https://maimaidx.jp/maimai-mobile/img/music_dx.png"
    )

    # 根据缩略图尺寸动态计算布局
    line_spacing = int(thumb_size[1] * 0.187)  # 28/150 ≈ 0.187
    text_x_offset = padding + cover_size + 10
    score_x_offset = thumb_size[0] - 20

    # --- 歌曲标题 ---
    max_text_width = thumb_size[0] - text_x_offset - 20
    truncated_name = truncate_text(draw, song['name'], font_large, max_text_width)
    draw.text((text_x_offset, padding - 5), truncated_name, fill=text_color, font=font_large)

    draw.line([(text_x_offset, padding + line_spacing - 2),
               (thumb_size[0] - padding, padding + line_spacing - 2)],
              fill=text_color, width=2)

    # --- 基础分数 ---
    draw.text((text_x_offset, padding + line_spacing), song['score'], fill=text_color, font=font_large)

    # --- score_icon 图标 ---
    # 根据缩略图尺寸动态计算图标大小
    score_icon_width = int(thumb_size[0] * 0.217)  # 65/300 ≈ 0.217
    score_icon_height = int(thumb_size[1] * 0.2)  # 30/150 = 0.2
    paste_icon_optimized(
        img, song, key='score_icon',
        size=(score_icon_width, score_icon_height),
        position=(score_x_offset - score_icon_width + 5, padding + line_spacing),
        save_dir=ICON_SCORE_DIR,
        url_func=lambda value: f"https://maimaidx.jp/maimai-mobile/img/music_icon_{value}.png"
    )

    # --- 版本标题 + dx_score ---
    draw.text((text_x_offset, padding + line_spacing * 2),
              song['version'].replace(" PLUS", "+").replace("でらっくす", "DX"),
              fill=text_color, font=font_small)

    draw.text((score_x_offset, padding + line_spacing * 2),
              song['dx_score'], fill=text_color, font=font_small, anchor="ra")

    # --- 最下面的横线 ---
    draw.line([(0, thumb_size[1]), (thumb_size[0], thumb_size[1])], fill=(255, 255, 255), width=90)

    # --- dx_star 星星图标 ---
    if 'dx_score' in song and song['dx_score']:
        try:
            dx_score = eval(song['dx_score'].replace(",", ""))
            if 0 <= dx_score < 0.85:
                star_num = 0
            elif 0.85 <= dx_score < 0.9:
                star_num = 1
            elif 0.9 <= dx_score < 0.93:
                star_num = 2
            elif 0.93 <= dx_score < 0.95:
                star_num = 3
            elif 0.95 <= dx_score < 0.97:
                star_num = 4
            elif 0.97 <= dx_score <= 1:
                star_num = 5

            # 根据缩略图尺寸动态计算星星图标大小
            star_width = int(thumb_size[0] * 0.267)  # 80/300 ≈ 0.267
            star_height = int(thumb_size[1] * 0.107)  # 16/150 ≈ 0.107
            paste_icon_optimized(
                img, {'star': str(star_num)}, key='star',
                size=(star_width, star_height),
                position=(padding + cover_size, thumb_size[1] - int(thumb_size[1] * 0.213)),
                save_dir=ICON_DX_STAR_DIR,
                url_func=lambda value: f"https://maimaidx.jp/maimai-mobile/img/music_icon_dxstar_detail_{value}.png"
            )

        except Exception as e:
            logger.error(f"Error calculating dx_star: {e}")

    # --- combo_icon 图标 ---
    # 根据缩略图尺寸动态计算图标大小
    combo_icon_width = int(thumb_size[0] * 0.133)  # 40/300 ≈ 0.133
    combo_icon_height = int(thumb_size[1] * 0.3)  # 45/150 = 0.3
    paste_icon_optimized(
        img, song, key='combo_icon',
        size=(combo_icon_width, combo_icon_height),
        position=(padding - 5, thumb_size[1] - int(thumb_size[1] * 0.32)),
        save_dir=ICON_COMBO_DIR,
        url_func=lambda value: f"https://maimaidx.jp/maimai-mobile/img/music_icon_{value}.png"
    )

    # --- sync_icon 图标 ---
    paste_icon_optimized(
        img, song, key='sync_icon',
        size=(combo_icon_width, combo_icon_height),
        position=(padding + combo_icon_width - 5, thumb_size[1] - int(thumb_size[1] * 0.32)),
        save_dir=ICON_SYNC_DIR,
        url_func=lambda value: f"https://maimaidx.jp/maimai-mobile/img/music_icon_{value}.png"
    )


    # --- 数值 ---
    draw.text((score_x_offset + 3, thumb_size[1] - 38),
              f"{song['internalLevelValue']:.1f} → {song['ra']}",
              fill=(0, 0, 0), font=font_large, anchor="ra")

    # --- 边框 ---
    border_color = (200, 200, 200)
    draw.rectangle([(0, 0), (thumb_size[0] - 1, thumb_size[1] - 1)], outline=border_color, width=5)

    final_img = img.convert("RGB")
    return final_img

def generate_records_picture(up_songs=[], down_songs=[], title="RECORD"):
    uploaded_data = up_songs + down_songs
    up_num = len(up_songs)
    down_num = len(down_songs)
    num = up_num + down_num

    if not num:
        return

    up_ra = down_ra = 0
    up_level = down_level = 0
    up_score = down_score = 0

    for rcd in up_songs :
        up_ra += rcd['ra']
        up_level += rcd['internalLevelValue']
        up_score += float(rcd['score'][:-1])

    for rcd in down_songs :
        down_ra += rcd['ra']
        down_level += rcd['internalLevelValue']
        down_score += float(rcd['score'][:-1])

    all_ra = round(up_ra + down_ra, 2)
    all_level = up_level + down_level
    all_score = up_score + down_score

    grid_size = (5, math.ceil(up_num / 5) + math.ceil(down_num / 5))
    thumb_size = (300, 150)
    side_width = 20
    spacing = 10
    header_height = 245  # 增加header高度，拉开标题和上半部分的距离

    version_padding = 0 if not (up_songs and down_songs) else 40

    img_width = grid_size[0] * (thumb_size[0] + spacing) - spacing + side_width * 2
    img_height = header_height + grid_size[1] * (thumb_size[1] + spacing) + version_padding + 13
    combined = Image.new("RGB", (img_width, img_height), (255, 255, 255))
    draw = ImageDraw.Draw(combined)

    header_text = [
        f"でらっくす RATING: {all_ra} = {up_ra} + {down_ra}" if up_ra and down_ra else f"でらっくす RATING: {all_ra}",
        f"平均レーティング: {round(float(all_ra)/num, 2):.2f}",
        f"平均レベル: {round(float(all_level)/num, 2):.2f}",
        f"平均達成率: {round(all_score/num, 4):.4f}%"
    ]

    # 绘制统计信息背景卡片
    card_padding = 20
    card_x = side_width + 10
    card_y = side_width + 10  # 向下移动10px (从 side_width - 5 改为 side_width + 5)

    # 计算实际文本宽度和高度（与 draw_aligned_colon_text 的对齐方式一致）
    left_texts = []
    right_texts = []
    for line in header_text:
        if ":" in line:
            left, right = line.split(":", 1)
            left_texts.append(left + ":")
            right_texts.append(right.strip())
        else:
            left_texts.append(line)
            right_texts.append("")

    # 计算左侧最大宽度（+10px 间距，与 draw_aligned_colon_text 一致）
    max_left_width = max(draw.textbbox((0, 0), text, font=font_huge)[2] for text in left_texts) + 10
    # 计算右侧最大宽度
    max_right_width = max(draw.textbbox((0, 0), text, font=font_huge)[2] for text in right_texts) if right_texts else 0

    # 实际文本总宽度
    max_text_width = max_left_width + max_right_width

    line_height = draw.textbbox((0, 0), "TEST", font=font_huge)[3]
    text_total_height = len(header_text) * (line_height + 7)

    # 根据实际文本宽度设置卡片宽度
    card_width = max_text_width + card_padding * 2
    card_height = text_total_height + card_padding * 2

    # 绘制带圆角的半透明背景框
    draw.rounded_rectangle(
        [card_x, card_y, card_x + card_width, card_y + card_height],
        radius=12,
        fill=(245, 248, 252),  # 淡蓝灰色背景
        outline=(200, 210, 225),  # 浅蓝灰色边框
        width=2
    )

    draw_aligned_colon_text(
        draw,
        lines=header_text,
        top_left=(card_x + card_padding, card_y + card_padding - 5),
        font=font_huge,
        spacing=7,
        fill=(40, 40, 40)  # 深灰色文字，更柔和
    )

    # 绘制斜体标题
    bbox = draw.textbbox((0, 0), title, font=font_huge_huge)
    title_width = bbox[2] - bbox[0]
    title_height = bbox[3] - bbox[1]

    # 创建临时图层用于绘制标题（留更多空间避免裁剪）
    layer_width = title_width + 150
    layer_height = title_height + 120
    title_layer = Image.new('RGBA', (layer_width, layer_height), (255, 255, 255, 0))
    title_draw = ImageDraw.Draw(title_layer)
    # 文字绘制在图层中央偏上位置
    title_draw.text((70, 15), title, fill=(206, 206, 206, 255), font=font_huge_huge)

    # 应用斜体变换 (正向斜体 "/" 方向)
    title_layer = title_layer.transform(
        (layer_width, layer_height),
        Image.AFFINE,
        (1, 0.2, 0, 0, 1, 0),  # 正向斜切，斜度0.2
        Image.BICUBIC
    )

    # 将斜体标题粘贴到主图层（继续往左上移动）
    title_x = img_width - side_width - title_width - 70
    title_y = card_y - 30
    combined.paste(title_layer, (title_x, title_y), title_layer)

    up_thumbnails = [create_thumbnail(song, thumb_size) for song in up_songs[:grid_size[0] * grid_size[1]]]
    down_thumbnails = [create_thumbnail(song, thumb_size) for song in down_songs[:grid_size[0] * grid_size[1]]]
    thumbnails = up_thumbnails + down_thumbnails

    for i, thumb in enumerate(up_thumbnails):
        x_offset = (i % grid_size[0]) * (thumb_size[0] + spacing) + side_width
        y_offset = header_height + (i // grid_size[0]) * (thumb_size[1] + spacing)
        combined.paste(thumb, (x_offset, y_offset))

    # 计算up部分最后一行的底部位置
    up_rows = math.ceil(up_num / grid_size[0])
    total_up_y_offset = header_height + up_rows * (thumb_size[1] + spacing)

    # 在上下部分中间绘制分隔线 (----·----) - 仅当同时有上下部分时显示
    if up_songs and down_songs:
        # 分隔线靠近上部，距离下部更远
        divider_y = total_up_y_offset + version_padding // 3 + 2
        divider_color = (140, 140, 140)  # 再加深颜色

        # 计算中心点和线条长度（适中长度）
        center_x = img_width // 2
        line_half_length = (img_width - side_width * 2) // 2  # 线条长度为画布宽度的1/2

        # 绘制左侧横线（更粗）
        left_line_start = center_x - line_half_length // 2
        left_line_end = center_x - 10
        draw.line([(left_line_start, divider_y), (left_line_end, divider_y)], fill=divider_color, width=2)

        # 绘制中心点（稍大）
        dot_radius = 3
        draw.ellipse([center_x - dot_radius, divider_y - dot_radius,
                     center_x + dot_radius, divider_y + dot_radius], fill=divider_color)

        # 绘制右侧横线（更粗）
        right_line_start = center_x + 10
        right_line_end = center_x + line_half_length // 2
        draw.line([(right_line_start, divider_y), (right_line_end, divider_y)], fill=divider_color, width=2)

    for i, thumb in enumerate(down_thumbnails):
        x_offset = (i % grid_size[0]) * (thumb_size[0] + spacing) + side_width
        y_offset = total_up_y_offset + version_padding + (i // grid_size[0]) * (thumb_size[1] + spacing)
        combined.paste(thumb, (x_offset, y_offset))

    return combined


def generate_cover(cover, type, icon=None, icon_type=None, size=150, cover_name=None):
    """
    生成歌曲封面图片，带有类型标识和可选图标

    参数:
        cover: 封面 URL（兼容旧代码）
        type: 歌曲类型 ("std" 或 "dx")
        icon: 可选的图标名称（如 "ap", "fc" 等）
        icon_type: 可选的图标类型（如 "combo", "score", "sync"）
        size: 封面尺寸（默认150）
        cover_name: 封面文件名（包含扩展名），优先使用本地文件
    """
    img_width = size
    img_height = size
    record_img = Image.new("RGB", (img_width, img_height), (255, 255, 255))

    # 加载封面图片（优先使用 cover_name 本地文件）
    if cover_name:
        cover_img = get_cover_image(cover_url=cover, cover_name=cover_name)
    else:
        # 向后兼容：没有 cover_name 时直接从 URL 下载
        cover_img = get_cached_image(cover)

    if cover_img:
        cover_img = cover_img.resize((size, size))
        record_img.paste(cover_img, (0, 0))

    # 添加 type 图标（std/dx）- 按比例缩放
    type_width = int(size * 0.333)  # 50/150 ≈ 0.333
    type_height = int(size * 0.1)    # 15/150 = 0.1
    paste_icon_optimized(
        record_img,
        {'type': type},
        key='type',
        size=(type_width, type_height),
        position=(img_width - type_width, img_height - type_height),
        save_dir=ICON_TYPE_DIR,
        url_func=lambda value: "https://maimaidx.jp/maimai-mobile/img/music_standard.png" if value == "std" else "https://maimaidx.jp/maimai-mobile/img/music_dx.png"
    )

    # 如果提供了 icon 和 icon_type，显示对应的图标
    if icon and icon_type and icon != "back":
        try:
            file_path = f"{ICON_BASE_DIR}/{icon_type}/{icon}.png"
            url = f"https://maimaidx.jp/maimai-mobile/img/music_icon_{icon}.png"

            icon_img = download_and_cache_icon(url, file_path)
            if icon_img:
                # 转换为 RGBA 以支持透明度
                record_img = record_img.convert("RGBA")

                # 计算缩放 - 按比例缩放图标
                icon_width = int(size * 0.867)  # 130/150 ≈ 0.867
                aspect_ratio = icon_img.height / icon_img.width
                new_height = int(icon_width * aspect_ratio)
                resized_img = icon_img.resize((icon_width, new_height), Image.Resampling.LANCZOS)

                # 阴影处理
                shadow = Image.new("RGBA", record_img.size, (0, 0, 0, 150))
                record_img = Image.alpha_composite(record_img, shadow)

                # 粘贴图标
                x_offset = (record_img.width - icon_width) // 2
                y_offset = (record_img.height - new_height) // 2
                record_img.paste(resized_img, (x_offset, y_offset), resized_img.convert("RGBA"))

        except Exception as e:
            logger.error(f"Error loading icon {icon}: {e}")

    return record_img.convert("RGB")

def generate_plate_image(target_data, title, img_width=1700, img_height=600, max_per_row=9, margin=20, headers={}):
    level_width = 100
    img_size = 150
    row_height = img_size + margin

    rows = []
    rows_num = 0
    level_list = ["15", "14+", "14", "13+", "13", "12+", "12", "11+", "11", "10+", "10"]
    for level in level_list:
        row_imgs = [entry["img"] for entry in target_data if entry["level"] == level]
        rows_num += math.ceil(len(row_imgs) / max_per_row)
        if row_imgs:
            rows.append((level, row_imgs))

    total_height = rows_num * row_height + margin + 170 + 190

    final_img = Image.new("RGB", (img_width, total_height), "white")
    draw = ImageDraw.Draw(final_img)

    add_ = 15
    for key, value in headers.items():
        draw.text((margin + 50, margin + add_), f"{key.upper()}:", fill="black", font=font_huge)
        draw.text((margin + 350, margin + add_), f"{value['clear']} / {value['all']}", fill="black", font=font_huge)
        add_ += 40

    # 添加右侧标题
    title_text_size = draw.textlength(f"{title}の達成表", font=font_huge_huge)
    title_x = img_width - margin - title_text_size - 30
    title_y = margin - 25
    draw.text((title_x, title_y), f"{title}の達成表", fill=(206, 206, 206), font=font_huge_huge)

    # 渲染主体图像内容
    y_offset = margin + 30 + 180
    for level, img_list in rows:
        draw.text((margin, y_offset + img_size // 3), level, fill="black", font=font_for_plate)

        x_offset = level_width + margin
        for i, img in enumerate(img_list):
            if i > 0 and i % max_per_row == 0:
                y_offset += row_height
                x_offset = level_width + margin

            final_img.paste(img, (x_offset, y_offset))
            x_offset += img_size + margin

        y_offset += row_height

    return final_img

def generate_internallevel_image(target_data, level_name, img_width=2400, max_per_row=12, margin=20):
    """
    生成定数查询图片，左侧显示定数（如 13.0, 13.1），右侧显示歌曲封面

    参数:
        target_data: 歌曲数据列表，每个元素为 {"img": PIL.Image, "internal_level": float}
        level_name: 难度名称（如 "13", "13+", "14", "14+"）
        img_width: 图片总宽度
        max_per_row: 每行最多显示的歌曲数量
        margin: 边距（外边距，用于不同定数行之间）
    """
    level_width = 100
    img_size = 180  # 提升清晰度: 135 -> 180 (增加33%)
    img_gap = 5  # 同一行内封面之间的间距
    row_gap = 5  # 同一定数内不同行之间的间距
    level_gap = margin  # 不同定数之间的间距（保持原有的 margin）
    row_height = img_size + level_gap  # 用于计算总高度

    # 按照定数分组（13.0, 13.1, 13.2, ...）
    rows = []
    total_rows = 0  # 所有行数
    num_levels = 0  # 不同定数的数量

    # 获取所有不重复的定数并排序
    internal_levels = sorted(set(entry["internal_level"] for entry in target_data), reverse=True)

    for internal_level in internal_levels:
        # 格式化定数显示（保留一位小数）
        level_str = f"{internal_level:.1f}"
        row_imgs = [entry["img"] for entry in target_data if entry["internal_level"] == internal_level]
        if row_imgs:
            rows.append((level_str, row_imgs))
            num_levels += 1
            total_rows += math.ceil(len(row_imgs) / max_per_row)

    # 计算总高度
    # = 每行图片高度 * 总行数 + 同定数内行间距 * (总行数 - 不同定数数量) + 不同定数间距 * (定数数量 - 1) + 顶部区域
    content_height = (img_size * total_rows +
                     row_gap * (total_rows - num_levels) +
                     level_gap * (num_levels - 1))
    total_height = content_height + margin + 170

    final_img = Image.new("RGB", (img_width, total_height), "white")
    draw = ImageDraw.Draw(final_img)

    # 添加右侧标题
    title_text = f"{level_name} 定数リスト"
    title_text_size = draw.textlength(title_text, font=font_huge_huge)
    title_x = img_width - margin - title_text_size - 30
    title_y = margin - 45
    draw.text((title_x, title_y), title_text, fill=(206, 206, 206), font=font_huge_huge)

    # 渲染主体图像内容
    y_offset = margin + 30 + 140
    for level_idx, (level_str, img_list) in enumerate(rows):
        draw.text((margin, y_offset + img_size // 3), level_str, fill="black", font=font_for_plate)

        x_offset = level_width + margin
        row_count = 0  # 当前定数的行数计数
        for i, img in enumerate(img_list):
            if i > 0 and i % max_per_row == 0:
                y_offset += img_size + row_gap  # 同一定数内行间距
                x_offset = level_width + margin
                row_count += 1

            final_img.paste(img, (x_offset, y_offset))
            x_offset += img_size + img_gap  # 同一行内封面间距

        # 移动到下一个定数: 当前行底部 + 定数间距
        if level_idx < len(rows) - 1:  # 如果不是最后一个定数
            y_offset += img_size + level_gap
        else:
            y_offset += img_size  # 最后一个定数只需要加上图片高度

    return final_img
