import os
import random
import logging
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from modules.config_loader import FONT_FILE, LOGO_FILE, QR_CODE_FILE, BG_DIR

# 全局字体对象（一次性加载）
font_large  = ImageFont.truetype(FONT_FILE, 28)
font_stadium = ImageFont.truetype(FONT_FILE, 19)
font_small = ImageFont.truetype(FONT_FILE, 14)

font_record_name  = ImageFont.truetype(FONT_FILE, 60)
font_record_info = ImageFont.truetype(FONT_FILE, 29)

font_profile = ImageFont.truetype(FONT_FILE, 32)
font_trophy = ImageFont.truetype(FONT_FILE, 22)

font_song_title = ImageFont.truetype(FONT_FILE, 34)
font_song_info = ImageFont.truetype(FONT_FILE, 24)
font_level_badge = ImageFont.truetype(FONT_FILE, 40)
font_record_title = ImageFont.truetype(FONT_FILE, 170)
font_record_detail_title = ImageFont.truetype(FONT_FILE, 65)

# 获取logger
logger = logging.getLogger(__name__)

def draw_aligned_colon_text(draw, lines, top_left, font, spacing=10, fill=(0, 0, 0)):
    """
    将每行的冒号 ":" 作为对齐点，冒号前后分别对齐显示
    """
    x, y = top_left

    # 预处理
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
    # 处理 None 或空值
    if text is None:
        text = "-"

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


def compose_images(images, timezone_offset=9, bg_filter=None):
    """
    将多张图片垂直拼接，并添加页脚（RGB / RGBA 自适应）。

    参数：
        images: PIL.Image 对象列表
        timezone_offset: 时区偏移（小时数），默认 9（UTC+9）
        bg_filter: 可选的背景配置。兼容：
          - None: 不使用背景图
          - []: 从全部内置背景随机
          - [items]: 从指定背景随机
          - {"files": [...], "blur": 20}: 指定背景列表和模糊半径

    返回：
        组合后的 PIL.Image 对象（RGB 或 RGBA）
    """
    spacing = 5
    outer_margin = 40
    footer_height = 150
    if not images:
        raise ValueError("图片列表不能为空")

    def ensure_rgba(img: Image.Image) -> Image.Image:
        return img if img.mode == "RGBA" else img.convert("RGBA")

    images_with_bg = [ensure_rgba(img) for img in images]

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
    dynamic_font = ImageFont.truetype(FONT_FILE, dynamic_font_size)

    base_logo_size = 130
    dynamic_logo_size = max(100, min(180, int(base_logo_size * scale_factor)))
    dynamic_footer_height = max(
        dynamic_footer_height,
        30 + int(10 * scale_factor) + dynamic_logo_size,
    )

    dynamic_left_margin = max(40, min(80, int(50 * scale_factor))) - 10
    dynamic_right_margin = max(150, min(250, int(180 * scale_factor))) - 10
    dynamic_line_spacing = max(30, min(50, int(35 * scale_factor)))

    # 4. 内部画布
    inner_width = max_img_width
    inner_height = total_images_height + spacing + dynamic_footer_height

    combined = Image.new("RGBA", (inner_width, inner_height), (0, 0, 0, 0))

    # 5. 粘贴图片（统一使用 alpha）
    y_offset = 10
    for img in images_with_bg:
        x_offset = (inner_width - img.width) // 2
        combined.paste(img, (x_offset, y_offset), img)
        y_offset += img.height + spacing

    # 6. 页脚
    draw = ImageDraw.Draw(combined)
    footer_y_start = total_images_height + spacing + 20

    # 获取用户时区时间
    user_timezone = timezone(timedelta(hours=timezone_offset))
    current_date = datetime.now(user_timezone).strftime("%Y-%m-%d")

    # 格式化时区显示
    tz_sign = '+' if timezone_offset >= 0 else ''
    tz_str = f"UTC{tz_sign}{timezone_offset}"

    footer_text = [
        f"Generated by JiETNG at {current_date} ({tz_str}).",
        f"© 2025 - {datetime.now(user_timezone).year} Matsuki (Matsuk1).",
        "All rights reserved."
    ]

    for i, text in enumerate(footer_text):
        text_y = footer_y_start + int(20 * scale_factor) + i * dynamic_line_spacing
        draw.text(
            (dynamic_left_margin, text_y),
            text,
            fill=(0, 0, 0, 255),
            font=dynamic_font,
            stroke_width=2,
            stroke_fill=(255, 255, 255, 255)
        )

    # QR Code 和 Logo
    qr_logo_y = footer_y_start + int(10 * scale_factor)
    qr_logo_spacing = int(20 * scale_factor)  # QR 和 Logo 之间的间距

    # QR Code（左侧）
    try:
        with Image.open(QR_CODE_FILE) as _qr:
            qr_img = _qr.copy()
        qr_img = ensure_rgba(
            qr_img.resize(
                (dynamic_logo_size, dynamic_logo_size),
                Image.Resampling.LANCZOS
            )
        )
        qr_img = round_corner(qr_img, radius=10)
        # QR Code 放在 logo 左边
        qr_x = inner_width - dynamic_right_margin - dynamic_logo_size - qr_logo_spacing
        combined.paste(qr_img, (qr_x, qr_logo_y), qr_img)
    except Exception as exc:
        logger.warning("[ImageManager] Failed to load QR code: %s", exc)

    # Logo（右侧）
    try:
        with Image.open(LOGO_FILE) as _logo:
            logo_img = _logo.copy()
        logo_img = ensure_rgba(
            logo_img.resize(
                (dynamic_logo_size, dynamic_logo_size),
                Image.Resampling.LANCZOS
            )
        )
        logo_x = inner_width - dynamic_right_margin
        combined.paste(logo_img, (logo_x, qr_logo_y), logo_img)
    except Exception as exc:
        logger.warning("[ImageManager] Failed to load logo: %s", exc)

    bg_files_filter = bg_filter
    bg_blur_radius = 20
    bg_overlay_alpha = 40
    if isinstance(bg_filter, dict):
        bg_files_filter = bg_filter.get("files", [])
        try:
            bg_blur_radius = int(bg_filter.get("blur", 20))
        except (ValueError, TypeError):
            bg_blur_radius = 20
        bg_blur_radius = max(0, min(40, bg_blur_radius))
        try:
            bg_overlay_alpha = int(bg_filter.get("overlay", 40))
        except (ValueError, TypeError):
            bg_overlay_alpha = 40
        bg_overlay_alpha = max(0, min(120, bg_overlay_alpha))

    # 7. 外层背景（模糊背景图 or fallback 纯色）
    final_width = combined.width + 2 * outer_margin
    final_height = combined.height + 2 * outer_margin

    try:
        all_bg_files = [f for f in os.listdir(BG_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        if not all_bg_files:
            raise FileNotFoundError("No background images found")
        # bg_files_filter=None → 白色背景, [] → 内置背景随机, [items] → 指定列表
        if bg_files_filter:
            candidate_files = [f for f in bg_files_filter if f in all_bg_files]
        elif bg_files_filter == []:
            candidate_files = [f for f in all_bg_files if not f.startswith('jietnguser_')]
        else:
            raise FileNotFoundError("No candidate backgrounds")
        if not candidate_files:
            raise FileNotFoundError("No candidate backgrounds")
        bg_path = os.path.join(BG_DIR, random.choice(candidate_files))
        with Image.open(bg_path) as _bg:
            bg_img = _bg.convert("RGB")
        # Cover 裁剪：等比缩放使短边覆盖目标尺寸，居中裁剪
        bg_w, bg_h = bg_img.size
        scale = max(final_width / bg_w, final_height / bg_h)
        new_bg_w = int(bg_w * scale)
        new_bg_h = int(bg_h * scale)
        bg_img = bg_img.resize((new_bg_w, new_bg_h), Image.Resampling.LANCZOS)
        left = (new_bg_w - final_width) // 2
        top = (new_bg_h - final_height) // 2
        bg_img = bg_img.crop((left, top, left + final_width, top + final_height))
        # 高斯模糊（在 RGB 上操作避免 alpha 边缘伪影）
        if bg_blur_radius > 0:
            bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=bg_blur_radius))
        # 转回 RGBA 后叠加半透明白色遮罩
        bg_img = bg_img.convert("RGBA")
        if bg_overlay_alpha > 0:
            overlay = Image.new("RGBA", (final_width, final_height), (255, 255, 255, bg_overlay_alpha))
            bg_img = Image.alpha_composite(bg_img, overlay)
        final_img = bg_img
    except (FileNotFoundError, OSError, ValueError) as exc:
        if bg_files_filter is not None:
            logger.warning("[ImageManager] Background unavailable: %s", exc)
        final_img = Image.new("RGB", (final_width, final_height), (255, 255, 255))

    final_img.paste(combined, (outer_margin, outer_margin), combined)
    return final_img.convert("RGB")


def compose_generated_images(images, **options):
    """Compose owned source images and release them when composition finishes."""
    images = list(images)
    try:
        options.pop("outer_margin", None)
        options.pop("image_y_offset", None)
        return compose_images(images, **options)
    finally:
        closed = set()
        for image in images:
            if id(image) not in closed:
                image.close()
                closed.add(id(image))


def round_corner(img, radius=20):
    img = img.convert("RGBA")
    mask_scale = 4
    mask_size = (img.size[0] * mask_scale, img.size[1] * mask_scale)
    mask = Image.new("L", mask_size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, *mask_size),
        radius=radius * mask_scale,
        fill=255
    )
    mask = mask.resize(img.size, Image.Resampling.LANCZOS)

    img.putalpha(mask)
    return img
