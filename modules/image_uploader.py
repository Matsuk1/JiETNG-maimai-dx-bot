import requests
import logging
from io import BytesIO
from PIL import Image
from modules.config_loader import IMGUR_CLIENT_ID

logger = logging.getLogger(__name__)

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
                logger.error(f"[ImageUploader] ✗ Uguu upload failed: data={data}")
        else:
            logger.error(f"[ImageUploader] ✗ Uguu request failed: status={resp.status_code}")
    except Exception as e:
        logger.error(f"[ImageUploader] ✗ Uguu response parsing error: error={e}")

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
            logger.error(f"[ImageUploader] ✗ 0x0 upload failed: response={response.text}")
    except Exception as e:
        logger.error(f"[ImageUploader] ✗ 0x0 exception: error={e}")

    return None

def _upload_to_imgur(img):
    """上传图片到 Imgur"""
    if not IMGUR_CLIENT_ID:
        logger.error("[ImageUploader] ✗ Imgur client ID not configured")
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
                logger.error(f"[ImageUploader] ✗ Imgur upload failed: data={data}")
        else:
            logger.error(f"[ImageUploader] ✗ Imgur request failed: status={response.status_code}, response={response.text}")
    except Exception as e:
        logger.error(f"[ImageUploader] ✗ Imgur exception: error={e}")

    return None

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
    logger.info("[ImageUploader] → Uploading original image")
    original_url = None

    # 优先尝试 imgur
    if IMGUR_CLIENT_ID:
        logger.info("[ImageUploader] → Using imgur to upload original")
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
            logger.error(f"[ImageUploader] ✗ Imgur upload exception: error={e}")

        original_io.seek(0)  # 重置指针以供后续使用

    if not original_url:
        logger.info("[ImageUploader] → Using uguu to upload original")
        files = {'files[]': ('image.png', original_io, 'image/png')}
        try:
            resp = requests.post("https://uguu.se/upload.php", files=files)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("files"):
                    original_url = data["files"][0]["url"]
        except Exception as e:
            logger.error(f"[ImageUploader] ✗ Uguu upload exception: error={e}")

        original_io.seek(0)

    if not original_url:
        logger.info("[ImageUploader] → Using 0x0 to upload original")
        files = {'file': ('image.png', original_io, 'image/png')}
        try:
            response = requests.post("https://0x0.st", files=files)
            if response.status_code == 200 and response.text.startswith("https://0x0.st/"):
                original_url = response.text.strip()
        except Exception as e:
            logger.error(f"[ImageUploader] ✗ 0x0 upload exception: error={e}")

    if not original_url:
        logger.error("[ImageUploader] ✗ All upload methods failed")
        return None, None

    # 不再上传预览图，直接使用原图
    logger.info(f"[ImageUploader] ✓ Upload complete: url={original_url}")
    return original_url, original_url
