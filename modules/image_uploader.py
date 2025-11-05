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
    """压缩图片

    Args:
        img: PIL Image 对象
        max_width: 最大宽度
        quality: JPEG 质量 (1-100)

    Returns:
        压缩后的 PIL Image 对象
    """
    # 如果宽度小于等于 max_width，不需要压缩
    if img.width <= max_width:
        return img.copy()

    # 计算新尺寸
    ratio = max_width / img.width
    new_height = int(img.height * ratio)

    # 调整大小
    compressed = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    return compressed

# 智能图床上传（上传原图和预览图）
def smart_upload(img):
    """上传图片到图床，返回原图和预览图链接

    Args:
        img: PIL Image 对象

    Returns:
        tuple: (original_url, preview_url) 如果上传失败返回 (None, None)
    """
    # 生成压缩预览图
    preview_img = _compress_image(img, max_width=800)

    # 上传原图
    print("[smart_upload] 上传原图...")
    original_url = None

    # 优先尝试 imgur
    if IMGUR_CLIENT_ID:
        print("[smart_upload] 使用 imgur 上传原图")
        original_url = _upload_to_imgur(img)

    if not original_url:
        print("[smart_upload] 使用 uguu 上传原图")
        original_url = _upload_to_uguu(img)

    if not original_url:
        print("[smart_upload] 使用 0x0 上传原图")
        original_url = _upload_to_0x0(img)

    if not original_url:
        print("[smart_upload] 原图上传失败")
        return None, None

    # 上传预览图
    print("[smart_upload] 上传预览图...")
    preview_url = None

    # 优先尝试 imgur
    if IMGUR_CLIENT_ID:
        print("[smart_upload] 使用 imgur 上传预览图")
        preview_url = _upload_to_imgur(preview_img)

    if not preview_url:
        print("[smart_upload] 使用 uguu 上传预览图")
        preview_url = _upload_to_uguu(preview_img)

    if not preview_url:
        print("[smart_upload] 使用 0x0 上传预览图")
        preview_url = _upload_to_0x0(preview_img)

    if not preview_url:
        print("[smart_upload] 预览图上传失败，使用原图链接作为预览")
        preview_url = original_url

    print(f"[smart_upload] 上传完成 - 原图: {original_url}, 预览图: {preview_url}")
    return original_url, preview_url
