import requests
from io import BytesIO
from PIL import Image
from modules.config_loader import IMGUR_CLIENT_ID

def _upload_to_uguu(img):
    url = "https://uguu.se/upload.php"

    img_io = BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)
    files = {'files[]': ('image.png', img_io, 'image/png')}
    resp = requests.post(url, files=files)

    try:
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and data.get("files"):
                return data["files"][0]["url"]
            else:
                print("[uguu] 上传失败：", data)
        else:
            print("[uguu] 请求失败：", resp.status_code)
    except Exception as e:
        print("[uguu] 解析响应异常：", e)

    return None

def _upload_to_0x0(img):
    url = "https://0x0.st"

    img_io = BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)
    files = {'file': ('image.png', img_io, 'image/png')}
    response = requests.post(url, files=files)

    try:
        if response.status_code == 200 and response.text.startswith("https://0x0.st/"):
            return response.text.strip()
        else:
            print("[0x0] 上传失败：", response.text)
    except Exception as e:
        print("[0x0] 异常：", e)

    return None

def _upload_to_imgur(img):
    """上传图片到 Imgur"""
    if not IMGUR_CLIENT_ID:
        print("[imgur] Client ID 未配置")
        return None

    url = "https://api.imgur.com/3/image"
    headers = {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"}

    img_io = BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)

    files = {'image': img_io}

    try:
        response = requests.post(url, headers=headers, files=files)
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("data"):
                return data["data"]["link"]
            else:
                print("[imgur] 上传失败：", data)
        else:
            print("[imgur] 请求失败：", response.status_code, response.text)
    except Exception as e:
        print("[imgur] 异常：", e)

    return None

def _compress_image(img, max_width=800, quality=85):
    """压缩图片并转换为 JPEG 格式

    Args:
        img: PIL Image 对象
        max_width: 最大宽度
        quality: JPEG 质量 (1-100)

    Returns:
        压缩后的 BytesIO 对象（JPEG 格式）
    """
    # 转换为 RGB（JPEG 不支持透明通道）
    if img.mode in ('RGBA', 'LA', 'P'):
        # 创建白色背景
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # 如果宽度大于 max_width，调整大小
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    # 保存为 JPEG 格式到 BytesIO
    img_io = BytesIO()
    img.save(img_io, format='JPEG', quality=quality, optimize=True)
    img_io.seek(0)

    return img_io

# 智能图床上传（上传原图和预览图）
def smart_upload(img):
    """上传图片到图床，返回原图和预览图链接

    Args:
        img: PIL Image 对象

    Returns:
        tuple: (original_url, preview_url) 如果上传失败返回 (None, None)
    """
    # 一次性转换为 BytesIO，避免重复序列化
    original_io = BytesIO()
    img.save(original_io, format='PNG')
    original_io.seek(0)

    # 上传原图
    print("[smart_upload] 上传原图...")
    original_url = None

    # 优先尝试 imgur
    if IMGUR_CLIENT_ID:
        print("[smart_upload] 使用 imgur 上传原图")
        url = "https://api.imgur.com/3/image"
        headers = {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"}
        files = {'image': original_io}

        try:
            response = requests.post(url, headers=headers, files=files)
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data"):
                    original_url = data["data"]["link"]
        except Exception as e:
            print(f"[imgur] 异常: {e}")

        original_io.seek(0)  # 重置指针以供后续使用

    if not original_url:
        print("[smart_upload] 使用 uguu 上传原图")
        files = {'files[]': ('image.png', original_io, 'image/png')}
        try:
            resp = requests.post("https://uguu.se/upload.php", files=files)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("files"):
                    original_url = data["files"][0]["url"]
        except Exception as e:
            print(f"[uguu] 异常: {e}")

        original_io.seek(0)

    if not original_url:
        print("[smart_upload] 使用 0x0 上传原图")
        files = {'file': ('image.png', original_io, 'image/png')}
        try:
            response = requests.post("https://0x0.st", files=files)
            if response.status_code == 200 and response.text.startswith("https://0x0.st/"):
                original_url = response.text.strip()
        except Exception as e:
            print(f"[0x0] 异常: {e}")

    if not original_url:
        print("[smart_upload] 原图上传失败")
        return None, None

    # 生成并上传压缩预览图（JPEG格式）
    print("[smart_upload] 上传预览图...")
    preview_url = None

    try:
        preview_io = _compress_image(img, max_width=800, quality=85)

        # 直接上传压缩后的 BytesIO（优先使用 0x0，因为它支持直接上传）
        files = {'file': ('preview.jpg', preview_io, 'image/jpeg')}
        response = requests.post("https://0x0.st", files=files)

        if response.status_code == 200 and response.text.startswith("https://0x0.st/"):
            preview_url = response.text.strip()
            print("[smart_upload] 预览图上传成功（0x0）")
        else:
            print("[smart_upload] 预览图上传失败，使用原图链接")
            preview_url = original_url
    except Exception as e:
        print(f"[smart_upload] 预览图上传异常: {e}，使用原图链接")
        preview_url = original_url

    print(f"[smart_upload] 上传完成 - 原图: {original_url}, 预览图: {preview_url}")
    return original_url, preview_url
