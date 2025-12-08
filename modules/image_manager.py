import qrcode
import logging
from PIL import Image, ImageDraw, ImageFont
from modules.config_loader import FONT_PATH, LOGO_PATH

# 全局字体对象（一次性加载）
font_title = ImageFont.truetype(FONT_PATH, 34)
font_info = ImageFont.truetype(FONT_PATH, 24)
font_for_plate = ImageFont.truetype(FONT_PATH, 40)
font_huge_huge = ImageFont.truetype(FONT_PATH, 170)
font_huge  = ImageFont.truetype(FONT_PATH, 28)
font_large = ImageFont.truetype(FONT_PATH, 19)
font_small = ImageFont.truetype(FONT_PATH, 14)
font_tiny = ImageFont.truetype(FONT_PATH, 6)

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
                               bg_color=(255, 255, 255), border_color=(220, 220, 220), border_width=5):
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
    bg = Image.new("RGB", bg_size, bg_color)
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
    content_img = content_img.convert("RGB")
    bg.paste(content_img, (padding, padding))

    return bg

def compose_images(images, spacing=40, outer_margin=30,
                   footer_height=150, bg_color=(255, 255, 255), inner_bg=(255, 255, 255)):
    """
    将多张图片垂直拼接，并添加页脚。

    参数：
        images: PIL.Image 对象列表
        spacing: 图片之间的间距
        outer_margin: 最外层边距
        footer_height: 页脚高度（基准值，会根据图片宽度动态调整）
        bg_color: 外层背景颜色（RGB）
        inner_bg: 内部背景颜色

    返回：
        组合后的 PIL.Image 对象
    """
    if not images:
        raise ValueError("图片列表不能为空")

    # 1. 给每个图加上圆角背景（不缩放，保持原始尺寸）
    images_with_bg = [wrap_in_rounded_background(img) for img in images]

    # 2. 计算总尺寸（使用最大宽度，与 combine_with_rounded_background 逻辑一致）
    max_img_width = max(img.width for img in images_with_bg)
    total_images_height = sum(img.height for img in images_with_bg)
    total_images_height += spacing * (len(images_with_bg) - 1)  # 图片间距

    # 3. 动态计算页脚高度和元素尺寸，基于图片宽度
    # 基准宽度: 1700px (原始设计宽度)
    base_width = 1700
    scale_factor = max_img_width / base_width

    # 动态调整页脚高度（最小150px，最大250px）
    dynamic_footer_height = max(150, min(250, int(footer_height * scale_factor)))

    # 动态调整字体大小
    base_font_size = 28
    dynamic_font_size = max(24, min(40, int(base_font_size * scale_factor)))
    dynamic_font = ImageFont.truetype(FONT_PATH, dynamic_font_size)

    # 动态调整 Logo 尺寸
    base_logo_size = 130
    dynamic_logo_size = max(100, min(180, int(base_logo_size * scale_factor)))

    # 动态调整边距
    dynamic_left_margin = max(40, min(80, int(50 * scale_factor)))
    dynamic_right_margin = max(150, min(250, int(180 * scale_factor)))

    # 动态调整行间距
    dynamic_line_spacing = max(30, min(50, int(35 * scale_factor)))

    # 4. 内部画布尺寸（包含图片和页脚）
    inner_width = max_img_width
    inner_height = total_images_height + spacing + dynamic_footer_height

    # 5. 创建内部白色背景
    combined = Image.new("RGB", (inner_width, inner_height), inner_bg)

    # 6. 垂直粘贴所有图片（居中对齐，与 combine_with_rounded_background 逻辑一致）
    y_offset = 0
    for img in images_with_bg:
        x_offset = (inner_width - img.width) // 2  # 居中
        if img.mode == "RGB":
            combined.paste(img, (x_offset, y_offset))
        else:
            combined.paste(img, (x_offset, y_offset), img)
        y_offset += img.height + spacing

    # 7. 添加页脚
    draw = ImageDraw.Draw(combined)
    footer_y_start = total_images_height + spacing - 10

    # 页脚文本（左侧，使用动态边距和字体）
    footer_text = ["Generated by JiETNG.", "© 2025 Matsuki.", "All rights reserved."]
    for i, text in enumerate(footer_text):
        text_y = footer_y_start + int(20 * scale_factor) + i * dynamic_line_spacing
        draw.text((dynamic_left_margin, text_y), text, fill=(0, 0, 0), font=dynamic_font)

    # 页脚 Logo（右侧，使用动态尺寸和边距）
    try:
        logo_img = Image.open(LOGO_PATH).resize((dynamic_logo_size, dynamic_logo_size), Image.Resampling.LANCZOS)
        logo_x = inner_width - dynamic_right_margin
        logo_y = footer_y_start + int(10 * scale_factor)
        combined.paste(logo_img, (logo_x, logo_y))
    except Exception as e:
        logger.error(f"无法加载 Logo: {e}")

    # 8. 添加外层灰色背景
    final_width = combined.width + 2 * outer_margin
    final_height = combined.height + 2 * outer_margin

    final_img = Image.new("RGB", (final_width, final_height), bg_color)
    final_img.paste(combined, (outer_margin, outer_margin))

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

def generate_qr_with_title(data: str, title_list: list[str]) -> Image.Image:
    qr_img = _generate_qrcode(data)
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
    qr_img = qr_img.resize((int(qr_w * scale), int(qr_h * scale)), Image.Resampling.LANCZOS)
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
