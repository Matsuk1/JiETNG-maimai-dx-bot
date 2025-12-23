import qrcode
import logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from modules.config_loader import FONT_PATH, LOGO_PATH

# 全局字体对象（一次性加载）
font_large  = ImageFont.truetype(FONT_PATH, 28)
font_stadium = ImageFont.truetype(FONT_PATH, 19)
font_small = ImageFont.truetype(FONT_PATH, 14)

font_song_title = ImageFont.truetype(FONT_PATH, 34)
font_song_info = ImageFont.truetype(FONT_PATH, 24)
font_level_badge = ImageFont.truetype(FONT_PATH, 40)
font_record_title = ImageFont.truetype(FONT_PATH, 170)

# 获取logger
logger = logging.getLogger(__name__)

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

def wrap_in_rounded_background(content_img, padding=20, radius=30,
                               bg_color=(255, 255, 255, 255), border_color=(220, 220, 220, 255), border_width=5):
    """
    将图像放入圆角白底框中（支持灰色边框，去除透明通道）

    参数：
        content_img: 原始图像 (PIL.Image)
        padding: 内容与圆角框的间距
        radius: 圆角半径
        bg_color: 内部背景颜色（默认白色）
        border_color: 边框颜色（默认浅灰）
        border_width: 边框线宽
    """
    # 计算背景尺寸
    bg_size = (content_img.width + 2 * padding, content_img.height + 2 * padding)

    # 创建白底画布
    bg = Image.new("RGBA", bg_size, bg_color)
    draw = ImageDraw.Draw(bg)

    # 绘制圆角矩形边框
    x0, y0 = 0, 0
    x1, y1 = bg_size
    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=radius,
        outline=border_color,
        width=border_width,
        fill=bg_color
    )

    # 贴上内容图
    content_img = content_img.convert("RGBA")
    bg.paste(content_img, (padding, padding), content_img)

    return bg

def compose_images(images, spacing=40, outer_margin=30,
                   footer_height=150, bg_color=(255, 255, 255, 255), inner_bg=(255, 255, 255, 255), border_width=5):
    """
    将多张图片垂直拼接，并添加页脚（RGB / RGBA 自适应）。

    参数：
        images: PIL.Image 对象列表
        spacing: 图片之间的间距
        outer_margin: 最外层边距
        footer_height: 页脚高度（基准值，会根据图片宽度动态调整）
        bg_color: 外层背景颜色（RGB 或 RGBA）
        inner_bg: 内部背景颜色（RGB 或 RGBA）

    返回：
        组合后的 PIL.Image 对象（RGB 或 RGBA）
    """
    if not images:
        raise ValueError("图片列表不能为空")

    def ensure_rgba(img: Image.Image) -> Image.Image:
        return img if img.mode == "RGBA" else img.convert("RGBA")

    def color_to_rgba(color):
        if len(color) == 4:
            return color
        return (*color, 255)

    # 判断最终是否需要 RGBA 输出
    output_rgba = (len(bg_color) == 4 and bg_color[3] < 255) or \
                  (len(inner_bg) == 4 and inner_bg[3] < 255)

    bg_color_rgba = color_to_rgba(bg_color)
    inner_bg_rgba = color_to_rgba(inner_bg)

    # 1. 给每个图加圆角背景，并统一为 RGBA
    images_with_bg = [
        ensure_rgba(wrap_in_rounded_background(img, border_width=border_width))
        for img in images
    ]

    # 2. 计算尺寸
    max_img_width = max(img.width for img in images_with_bg)
    total_images_height = sum(img.height for img in images_with_bg)
    total_images_height += spacing * (len(images_with_bg) - 1)

    # 3. 动态缩放参数
    base_width = 1700
    scale_factor = max_img_width / base_width

    dynamic_footer_height = max(150, min(250, int(footer_height * scale_factor)))

    base_font_size = 28
    dynamic_font_size = max(24, min(40, int(base_font_size * scale_factor)))
    dynamic_font = ImageFont.truetype(FONT_PATH, dynamic_font_size)

    base_logo_size = 130
    dynamic_logo_size = max(100, min(180, int(base_logo_size * scale_factor)))

    dynamic_left_margin = max(40, min(80, int(50 * scale_factor)))
    dynamic_right_margin = max(150, min(250, int(180 * scale_factor)))
    dynamic_line_spacing = max(30, min(50, int(35 * scale_factor)))

    # 4. 内部画布
    inner_width = max_img_width
    inner_height = total_images_height + spacing + dynamic_footer_height

    combined = Image.new("RGBA", (inner_width, inner_height), inner_bg_rgba)

    # 5. 粘贴图片（统一使用 alpha）
    y_offset = 0
    for img in images_with_bg:
        x_offset = (inner_width - img.width) // 2
        combined.paste(img, (x_offset, y_offset), img)
        y_offset += img.height + spacing

    # 6. 页脚
    draw = ImageDraw.Draw(combined)
    footer_y_start = total_images_height + spacing - 10

    footer_text = [
        "Generated by JiETNG.",
        "© 2025 Matsuki.",
        "All rights reserved."
    ]

    for i, text in enumerate(footer_text):
        text_y = footer_y_start + int(20 * scale_factor) + i * dynamic_line_spacing
        draw.text(
            (dynamic_left_margin, text_y),
            text,
            fill=(0, 0, 0, 255),
            font=dynamic_font
        )

    # Logo
    try:
        logo_img = Image.open(LOGO_PATH)
        logo_img = ensure_rgba(
            logo_img.resize(
                (dynamic_logo_size, dynamic_logo_size),
                Image.Resampling.LANCZOS
            )
        )
        logo_x = inner_width - dynamic_right_margin
        logo_y = footer_y_start + int(10 * scale_factor)
        combined.paste(logo_img, (logo_x, logo_y), logo_img)
    except Exception as e:
        logger.error(f"[ImageManager] ✗ Failed to load logo: error={e}")

    # 7. 外层背景
    final_width = combined.width + 2 * outer_margin
    final_height = combined.height + 2 * outer_margin

    final_img = Image.new("RGBA", (final_width, final_height), bg_color_rgba)
    final_img.paste(combined, (outer_margin, outer_margin), combined)

    # 8. 自动降级为 RGB（如果不需要透明）
    if not output_rgba:
        final_img = final_img.convert("RGB")

    return final_img

def _generate_qrcode(data: str, box_size: int = 10, border: int = 4) -> Image.Image:
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

def round_corner(img, radius=20):
    # 打开原图，并确保有 alpha 通道（RGBA）
    img = img.convert("RGBA")
    w, h = img.size

    # 创建同尺寸蒙版，初始全透明（0）
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)

    # 在蒙版上画白色圆角矩形（255 不透明）
    draw.rounded_rectangle(
        [(0, 0), (w, h)],
        radius=radius,
        fill=255
    )

    # 应用蒙版到原图
    img.putalpha(mask)

    return img
