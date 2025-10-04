import requests
import json
import re
import sys
import time
import traceback
import os
import urllib.parse
import math
import difflib
import base64

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

from config_loader import LOGO_PATH
from img_console import *

def get_difficulty_color(difficulty):
    colors = {
        "basic": (149, 207, 71),     # 绿色
        "advanced": (243, 162, 7),   # 黄色
        "expert": (255, 129, 141),   # 红色
        "master": (159, 81, 219),    # 紫色
        "remaster": (239, 224, 255), # 白色
        "utage": (245, 46, 221)      # 粉色
    }
    return colors.get(difficulty.lower(), (200, 200, 200))

def create_thumbnail(song, thumb_size=(300, 150), padding=15):
    bg_color = get_difficulty_color(song['difficulty'])
    img = Image.new("RGB", thumb_size, bg_color)
    draw = ImageDraw.Draw(img)

    text_color = (201, 123, 221) if song['difficulty'] == "remaster" else (255, 255, 255)

    # --- 封面 ---
    if 'url' in song and song['url']:
        try:
            response = requests.get(song['url'])
            cover_img = Image.open(BytesIO(response.content)).resize((80, 80))
            img.paste(cover_img, (padding, padding))
        except Exception as e:
            print(f"Error loading cover image: {e}")

    # --- kind 图标 ---
    paste_icon(
        img, song, key='kind',
        size=(40, 12),
        position=(padding + 80 - 40, padding + 80 - 12),
        save_dir='./assets/icon/kind',
        url_func=lambda value: "https://maimaidx.jp/maimai-mobile/img/music_standard.png" if value == "std" else "https://maimaidx.jp/maimai-mobile/img/music_dx.png",
        verify=False
    )

    line_spacing = 28
    text_x_offset = padding + 90
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
    paste_icon(
        img, song, key='score_icon',
        size=(65, 30),
        position=(score_x_offset - 60, padding + line_spacing),
        save_dir='./assets/icon/score',
        url_func=lambda value: f"https://maimaidx.jp/maimai-mobile/img/music_icon_{value}.png",
        verify=False
    )

    # --- 版本标题 + dx_score ---
    draw.text((text_x_offset, padding + line_spacing * 2),
              song['version'].replace(" PLUS", "+").replace("でらっくす", "DX"),
              fill=text_color, font=font_small)

    draw.text((score_x_offset, padding + line_spacing * 2),
              song['dx_score'], fill=text_color, font=font_small, anchor="ra")

    # --- 最下面的横线 ---
    draw.line([(0, thumb_size[1]),
               (thumb_size[0], thumb_size[1])],
              fill=(255, 255, 255), width=90)

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

            paste_icon(
                img, {'star': str(star_num)}, key='star',
                size=(80, 16),
                position=(padding + 80, thumb_size[1] - 32),
                save_dir='./assets/icon/dx_star',
                url_func=lambda value: f"https://maimaidx.jp/maimai-mobile/img/music_icon_dxstar_detail_{value}.png",
                verify=False
            )

        except Exception as e:
            print(f"Error calculating dx_star: {e}")

    # --- combo_icon 图标 ---
    paste_icon(
        img, song, key='combo_icon',
        size=(40, 45),
        position=(padding - 5, thumb_size[1] - 48),
        save_dir='./assets/icon/combo',
        url_func=lambda value: f"https://maimaidx.jp/maimai-mobile/img/music_icon_{value}.png",
        verify=False
    )

    # --- sync_icon 图标 ---
    paste_icon(
        img, song, key='sync_icon',
        size=(40, 45),
        position=(padding + 40, thumb_size[1] - 48),
        save_dir='./assets/icon/sync',
        url_func=lambda value: f"https://maimaidx.jp/maimai-mobile/img/music_icon_{value}.png",
        verify=False
    )


    # --- 名次和数值 ---
    draw.text((score_x_offset + 3, thumb_size[1] - 38),
              f"{song['internalLevelValue']:.1f} → {song['ra']}",
              fill=(0, 0, 0), font=font_large, anchor="ra")

    # --- 边框 ---
    border_color = (128, 128, 128)
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
    footer_height = 155
    side_width = 20
    spacing = 10
    header_height = 190

    version_padding = 0 if not (up_songs and down_songs) else 20

    img_width = grid_size[0] * (thumb_size[0] + spacing) - spacing + side_width * 2
    img_height = header_height + grid_size[1] * (thumb_size[1] + spacing) + footer_height + version_padding + 30
    combined = Image.new("RGB", (img_width, img_height), (255, 255, 255))
    draw = ImageDraw.Draw(combined)

    header_text = [
        f"でらっくすレーティング:  {all_ra} = {up_ra} + {down_ra}" if up_ra and down_ra else f"でらっくすレーティング:  {all_ra}",
        f"平均レーティング:  {round(float(all_ra)/num, 2):.2f}",
        f"平均レベル:  {round(float(all_level)/num, 2):.2f}",
        f"平均達成率:  {round(all_score/num, 4):.4f}%"
    ]

    draw_aligned_colon_text(
        draw,
        lines=header_text,
        top_left=(side_width + 20, side_width),  # 左上角起始坐标
        font=font_huge,
        spacing=7,
        fill=(0, 0, 0)
    )

    bbox = draw.textbbox((0, 0), title, font=font_huge_huge)
    title_width = bbox[2] - bbox[0]
    draw.text((img_width - side_width - title_width, -20), title, fill=(206, 206, 206), font=font_huge_huge)

    up_thumbnails = [create_thumbnail(song, thumb_size) for song in up_songs[:grid_size[0] * grid_size[1]]]
    down_thumbnails = [create_thumbnail(song, thumb_size) for song in down_songs[:grid_size[0] * grid_size[1]]]
    thumbnails = up_thumbnails + down_thumbnails

    for i, thumb in enumerate(up_thumbnails):
        x_offset = (i % grid_size[0]) * (thumb_size[0] + spacing) + side_width
        y_offset = header_height + (i // grid_size[0]) * (thumb_size[1] + spacing)
        combined.paste(thumb, (x_offset, y_offset))

    total_up_y_offset = header_height + ((up_num - 1) // grid_size[0]) * (thumb_size[1] + spacing)

    for i, thumb in enumerate(down_thumbnails):
        x_offset = (i % grid_size[0]) * (thumb_size[0] + spacing) + side_width
        y_offset = header_height + (i // grid_size[0]) * (thumb_size[1] + spacing) + version_padding + total_up_y_offset - spacing
        combined.paste(thumb, (x_offset, y_offset))

    footer_text = ["Generated by JiETNG.", "© 2025 Matsuki.", "All rights reserved."]
    for i, text in enumerate(footer_text):
        draw.text((side_width + 20, img_height - 150 + i * 35), text, fill=(0, 0, 0), font=font_huge)

    logo_img = Image.open(LOGO_PATH).resize((130, 130))
    combined.paste(logo_img, (img_width - 180, img_height - 150))

    return combined

def generate_yang_records_picture(version_songs, title="YANG"):
    if not version_songs:
        return

    thumb_size = (300, 150)   # 每个缩略图大小
    cols = 10                 # 固定列
    spacing = 10              # 缩略图间距
    side_width = 30           # 左右边距
    header_height = 150       # 顶部标题区域
    footer_height = 150       # 底部区域
    block_padding = 20        # 每个版本区块之间的留白
    line_height = 50          # 分隔条厚度

    # 计算整体平均 ra
    all_songs = [song for block in version_songs for song in block["songs"]]
    song_count = sum(block["count"] for block in version_songs)
    if not all_songs:
        return
    avg_ra = round(sum(song["ra"] for song in all_songs) / song_count, 2)

    # 先计算整体高度
    total_height = header_height + footer_height
    max_width = cols * (thumb_size[0] + spacing) - spacing + side_width * 2

    for block in version_songs:
        songs = block["songs"]
        rows = math.ceil(len(songs) / cols)
        block_height = rows * (thumb_size[1] + spacing)
        total_height += block_height + block_padding + line_height + 50

    combined = Image.new("RGB", (max_width, total_height), (255, 255, 255))
    draw = ImageDraw.Draw(combined)

    # 顶部 header_text
    header_text = [
        f"YANG レーティング: {avg_ra:.2f}"
    ]
    draw_aligned_colon_text(
        draw,
        lines=header_text,
        top_left=(side_width + 20, side_width),
        font=font_huge,
        spacing=7,
        fill=(0, 0, 0)
    )

    # 大标题
    bbox = draw.textbbox((0, 0), title, font=font_huge_huge)
    draw.text(((max_width - bbox[2]), -40), title, fill=(200, 200, 200), font=font_huge_huge)

    # 绘制每个版本区块
    current_y = header_height
    for idx, block in enumerate(version_songs):
        songs = block["songs"]
        version_title = block["version_title"]
        count = block["count"]

        # 分隔条
        draw.rectangle(
            [(0, current_y), (max_width, current_y + line_height)],
            fill=(200, 200, 200)
        )
        current_y += line_height + 10

        # 版本平均 ra
        if songs:
            avg_ra_version = round(sum(s["ra"] for s in songs) / count, 2)
        else:
            avg_ra_version = 0.00

        # 写版本标题 + ra
        bbox = draw.textbbox((0, 0), version_title, font=font_huge)
        title_x = 10
        title_y = current_y - line_height - 7
        draw.text((title_x, title_y), version_title, fill=(0, 0, 0), font=font_huge)

        ra_text = f"{avg_ra_version:.2f}"
        draw.text((title_x + 350, title_y), ra_text, fill=(0, 0, 0), font=font_huge)

        # 画缩略图
        for i, song in enumerate(songs):
            thumb = create_thumbnail(song, thumb_size)
            x_offset = (i % cols) * (thumb_size[0] + spacing) + side_width
            y_offset = current_y + (i // cols) * (thumb_size[1] + spacing)
            combined.paste(thumb, (x_offset, y_offset))

        # 更新 current_y
        current_y = current_y + math.ceil(len(songs) / cols) * (thumb_size[1] + spacing) + 40 + block_padding

    # 底部版权信息
    footer_text = ["Generated by JiETNG.", "© 2025 Matsuki.", "All rights reserved."]
    for i, text in enumerate(footer_text):
        draw.text((side_width, total_height - footer_height + i * 30), text, fill=(0, 0, 0), font=font_huge)

    logo_img = Image.open(LOGO_PATH).resize((100, 100))
    combined.paste(logo_img, (max_width - 150, total_height - footer_height))

    return combined

def create_small_record(cover, icon, icon_type):
    img_width = 150
    img_height = 150
    record_img = Image.new("RGBA", (img_width, img_height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(record_img)

    # 加载封面图片
    response = requests.get(cover, verify=False)
    cover_img = Image.open(BytesIO(response.content)).resize((150, 150))
    record_img.paste(cover_img, (0, 0))

    if icon != "back":
        try:
            file_path = f"./assets/icon/{icon_type}/{icon}.png"
            if not os.path.exists(file_path):
                print(f"\n\n{file_path}\n\n")
                response = requests.get(f"https://maimaidx.jp/maimai-mobile/img/music_icon_{icon}.png", verify=False)
                with open(file_path, "wb") as f:
                    f.write(response.content)

            icon_img = Image.open(file_path)

            # 计算缩放
            aspect_ratio = icon_img.height / icon_img.width
            new_height = int(130 * aspect_ratio)
            resized_img = icon_img.resize((130, new_height), Image.LANCZOS)

            # 阴影处理
            shadow = Image.new("RGBA", record_img.size, (0, 0, 0, 150))  # 半透明黑色遮罩
            record_img = Image.alpha_composite(record_img.convert("RGBA"), shadow)

            # 粘贴图标
            x_offset = (record_img.width - 130) // 2
            y_offset = (record_img.height - new_height) // 2
            record_img.paste(resized_img, (x_offset, y_offset), resized_img.convert("RGBA"))

        except Exception as e:
            print(f"Error loading image from https://maimaidx.jp/maimai-mobile/img/music_icon_{icon}.png: {e}")

    return record_img

def recent_generate_plate_image(target_data, title, img_width=1700, img_height=600, max_per_row=9, margin=20, headers={}):
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
    for key, value in headers.items() :
        draw.text((margin + 100, margin + add_), f"{key.upper()}:", fill="black", font=font_huge)
        draw.text((margin + 400, margin + add_), f"{value['clear']} / {value['all']}", fill="black", font=font_huge)
        add_ += 40

    y_offset = margin + 30 + 180
    for level, img_list in rows:
        draw.text((margin, y_offset + img_size // 3), level, fill="black", font=font_for_plate)

        x_offset = level_width + margin  # 让图片靠右对齐
        for i, img in enumerate(img_list):
            if i > 0 and i % max_per_row == 0:
                y_offset += row_height  # 换行
                x_offset = level_width + margin  # 重新起点

            final_img.paste(img, (x_offset, y_offset))
            x_offset += img_size + margin

        y_offset += row_height  # 每个等级后换行

    footer_text = ["Generated by JiETNG.", "© 2025 Matsuki.", "All rights reserved."]
    for i, text in enumerate(footer_text):
        draw.text((margin + 20, total_height - 150 + i * 35), text, fill=(0, 0, 0), font=font_huge)

    logo_img = Image.open(LOGO_PATH).resize((130, 130))
    final_img.paste(logo_img, (img_width - 180, total_height - 150))

    return final_img

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

    # 页脚
    footer_text = ["Generated by JiETNG.", "© 2025 Matsuki.", "All rights reserved."]
    for i, text in enumerate(footer_text):
        draw.text((margin + 20, total_height - 150 + i * 35), text, fill=(0, 0, 0), font=font_huge)

    logo_img = Image.open(LOGO_PATH).resize((130, 130))
    final_img.paste(logo_img, (img_width - 180, total_height - 150))

    return final_img
