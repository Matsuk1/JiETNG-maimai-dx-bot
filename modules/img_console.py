import os
import io
import requests
import qrcode
from PIL import Image, ImageDraw, ImageFont
from modules.config_loader import font_path

font_title = ImageFont.truetype(font_path, 34)
font_info = ImageFont.truetype(font_path, 24)

font_for_plate = ImageFont.truetype(font_path, 40)
font_huge_huge = ImageFont.truetype(font_path, 170)
font_huge  = ImageFont.truetype(font_path, 28)
font_large = ImageFont.truetype(font_path, 19)
font_small = ImageFont.truetype(font_path, 14)
font_tiny = ImageFont.truetype(font_path, 6)

def paste_icon(img, song, key, size, position, save_dir, url_func, verify=False):
    if key in song and song[key]:
        try:
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, f"{song[key]}.png")

            if not os.path.exists(file_path):
                print(f"\n\nDownloading {file_path}\n\n")
                url = url_func(song[key])
                headers = {
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://maimaidx.jp"
                }
                response = requests.get(url, headers=headers, verify=verify)
                response.raise_for_status()
                with open(file_path, "wb") as f:
                    f.write(response.content)

            icon_img = Image.open(file_path).convert("RGBA").resize(size)
            img.paste(icon_img, position, mask=icon_img)

        except Exception as e:
            print(f"[paste_icon] Error loading icon for '{key}': {e}")

def draw_aligned_colon_text(draw, lines, top_left, font, spacing=10, fill=(0, 0, 0)):
    """
    将每行的冒号 ":" 作为对齐点，冒号前后分别对齐显示
    """
    x, y = top_left

    # 预处理：分离左边（冒号前）和右边（冒号后）
    left_texts = []
    right_texts = []
    for line in lines:
        if ":" in line:
            left, right = line.split(":", 1)
            left_texts.append(left + ":")
            right_texts.append(right.strip())
        else:
            left_texts.append(line)
            right_texts.append("")

    # 计算左侧最大宽度
    max_left_width = max(draw.textbbox((0, 0), text, font=font)[2] for text in left_texts) + 10

    # 绘制
    for left, right in zip(left_texts, right_texts):
        draw.text((x, y), left, font=font, fill=fill)
        draw.text((x + max_left_width, y), right, font=font, fill=fill)
        y += draw.textbbox((0, 0), left, font=font)[3] + spacing

def truncate_text(draw, text, font, max_width):
    """
    如果文本超出最大宽度，自动截断并加省略号
    """
    ellipsis = "..."
    text_width = draw.textlength(text, font=font)
    ellipsis_width = draw.textlength(ellipsis, font=font)

    if text_width <= max_width:
        return text

    while text and draw.textlength(text + ellipsis, font=font) > max_width:
        text = text[:-1]

    return text + ellipsis

def resize_by_width(img, target_width):
    original_width, original_height = img.size
    ratio = target_width / original_width
    target_height = int(original_height * ratio)

    resized_img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    return resized_img

def create_rounded_background(size, radius=30, fill=(230, 230, 230, 255)):
    """创建不透明度为80%的圆角白底图层"""
    w, h = size
    bg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bg)
    draw.rounded_rectangle([0, 0, w, h], radius=radius, fill=fill)
    return bg

def wrap_in_rounded_background(content_img, padding=20, radius=30):
    """将图像放入圆角白底框中"""
    bg_size = (content_img.width + 2 * padding, content_img.height + 2 * padding)
    bg = create_rounded_background(bg_size, radius)
    combined = Image.new("RGBA", bg_size, (0, 0, 0, 0))
    content_img = content_img.convert("RGBA")
    combined.paste(bg, (0, 0), bg)
    combined.paste(content_img, (padding, padding), content_img)
    return combined

def combine_with_rounded_background(img1, img2, spacing=40):
    img1_bg = wrap_in_rounded_background(img1)
    img2_bg = wrap_in_rounded_background(img2)

    width = max(img1_bg.width, img2_bg.width)
    height = img1_bg.height + spacing + img2_bg.height

    combined = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    x1 = (width - img1_bg.width) // 2
    x2 = (width - img2_bg.width) // 2

    combined.paste(img1_bg, (x1, 0), img1_bg)
    combined.paste(img2_bg, (x2, img1_bg.height + spacing), img2_bg)

    new_width = combined.width + 2 * spacing
    new_height = combined.height + 2 * spacing

    final_img = Image.new("RGBA", (new_width, new_height), (255, 255, 255, 255))

    final_img.paste(combined, (spacing, spacing), combined)

    return final_img

def generate_qrcode(data: str, box_size: int = 10, border: int = 4) -> Image.Image:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img

def generate_qr_with_title(data: str, title_list: list[str]) -> Image.Image:
    qr_img = generate_qrcode(data)
    qr_w, qr_h = qr_img.size

    padding = 40
    line_spacing = 10

    # 计算文字尺寸
    dummy_img = Image.new("RGB", (1, 1), "white")
    draw = ImageDraw.Draw(dummy_img)

    line_sizes = []
    max_line_w = 0
    total_text_height = 0
    for i, text in enumerate(title_list):
        bbox = draw.textbbox((0, 0), text, font=font_title)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        line_sizes.append((w, h))
        max_line_w = max(max_line_w, w)
        total_text_height += h
        if i < len(title_list) - 1:
            total_text_height += line_spacing

    # 保证二维码与文本区高度一致
    text_h = total_text_height
    text_w = max_line_w
    target_h = max(qr_h, text_h)
    scale = target_h / qr_h
    qr_img = qr_img.resize((int(qr_w * scale), int(qr_h * scale)), Image.LANCZOS)
    qr_w, qr_h = qr_img.size

    # 左右空余相等 → 左右各 padding，二维码-文字间距设为 padding
    total_w = padding + qr_w + padding + text_w + padding
    total_h = target_h + padding * 2

    img = Image.new("RGB", (total_w, total_h), "white")
    draw = ImageDraw.Draw(img)

    # 绘制二维码（垂直居中）
    qr_x = padding
    qr_y = (total_h - qr_h) // 2
    img.paste(qr_img, (qr_x, qr_y))

    # 绘制文字区域（整体垂直居中）
    text_start_x = qr_x + qr_w + padding
    text_start_y = (total_h - text_h) // 2
    for (text, (w, h)) in zip(title_list, line_sizes):
        draw.text((text_start_x, text_start_y), text, font=font_title, fill=(0, 0, 0))
        text_start_y += h + line_spacing

    return img
