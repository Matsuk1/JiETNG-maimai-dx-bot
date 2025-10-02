import os
import requests
from PIL import Image, ImageDraw, ImageFont
from config_loader import fonts_folder


def _load_font(path, size):
    """加载指定字体，若缺失则回退到 PIL 默认字体。"""
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        print(f"[img_console] Font resource missing at {path}, fallback to default font.")
        return ImageFont.load_default()


# 字体加载
font_path = os.path.join(fonts_folder, "mplus-1p-regular.ttf")

font_title = _load_font(font_path, 34)
font_info = _load_font(font_path, 24)

font_for_plate = _load_font(font_path, 40)
font_huge_huge = _load_font(font_path, 170)
font_huge  = _load_font(font_path, 28)
font_large = _load_font(font_path, 19)
font_small = _load_font(font_path, 14)
font_tiny = _load_font(font_path, 6)

def paste_icon(img, song, key, size, position, save_dir, url_func, verify=False):
    """
    下载图标并粘贴到背景图 img 上（保留透明区域）。
    """
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
