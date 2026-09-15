"""Upload generated JPEG images to R2 or the local image host."""

import asyncio
import logging
import os
import secrets
import threading
import time
from datetime import datetime
from io import BytesIO

from PIL import Image

from modules.config_loader import (
    DOMAIN,
    IMG_DIR,
    R2_ACCESS_KEY_ID,
    R2_ACCOUNT_ID,
    R2_BUCKET_NAME,
    R2_ENABLED,
    R2_PUBLIC_URL,
    R2_SECRET_ACCESS_KEY,
)

logger = logging.getLogger(__name__)

PERMANENT_PREFIX = "keep_"
LOCAL_EXPIRY_SECONDS = 7200
CLEANUP_INTERVAL_SECONDS = 300
R2_MAX_BYTES = 10 * 1024 * 1024
_periodic_cleanup_thread = None


def cleanup_expired_images(expiry_seconds=LOCAL_EXPIRY_SECONDS):
    if not os.path.isdir(IMG_DIR):
        return

    try:
        filenames = os.listdir(IMG_DIR)
    except OSError:
        logger.exception("[ImageCleanup] Failed to list image directory")
        return

    now = time.time()
    deleted = 0
    for filename in filenames:
        if not filename.lower().endswith((".jpg", ".jpeg", ".png")) or filename.startswith(PERMANENT_PREFIX):
            continue
        path = os.path.join(IMG_DIR, filename)
        try:
            age = now - os.path.getmtime(path)
            if age <= expiry_seconds:
                continue
            os.remove(path)
            deleted += 1
            logger.debug("[ImageCleanup] Deleted expired image: id=%s, age=%ss", filename[:-4], int(age))
        except OSError:
            logger.exception("[ImageCleanup] Failed to process file: %s", filename)
    if deleted:
        logger.debug("[ImageCleanup] Cleanup complete: deleted=%s", deleted)


def _start_periodic_cleanup():
    def cleanup_loop():
        while True:
            time.sleep(CLEANUP_INTERVAL_SECONDS)
            cleanup_expired_images()

    global _periodic_cleanup_thread
    if _periodic_cleanup_thread is not None and _periodic_cleanup_thread.is_alive():
        return
    _periodic_cleanup_thread = threading.Thread(
        target=cleanup_loop,
        daemon=True,
        name="PeriodicImageCleanup",
    )
    _periodic_cleanup_thread.start()
    logger.info("[ImageCleanup] Periodic cleanup thread started")


def _encode_jpeg(image):
    """Preserve small text and colored icons with high-quality 4:4:4 JPEG."""
    if image.mode == "RGBA":
        with Image.new("RGBA", image.size, (255, 255, 255, 255)) as background:
            background.alpha_composite(image)
            rgb = background.convert("RGB")
    else:
        rgb = image.convert("RGB")
    with rgb, BytesIO() as buffer:
        rgb.save(buffer, format="JPEG", quality=95, subsampling=0,
                 optimize=True, progressive=True)
        return buffer.getvalue()


def _save_to_local(image_bytes):
    try:
        os.makedirs(IMG_DIR, exist_ok=True)
        image_id = secrets.token_urlsafe(16)
        with open(os.path.join(IMG_DIR, f"{image_id}.jpg"), "wb") as file:
            file.write(image_bytes)
        url = f"https://{DOMAIN}/linebot/img/{image_id}"
        return url
    except OSError:
        logger.exception("[LocalImageHost] Failed to save image")
        return None


async def _upload_to_r2(image_bytes, user_id=None):
    if not R2_ENABLED:
        return None
    try:
        import aioboto3
    except ImportError:
        logger.warning("[R2] aioboto3 not installed; falling back to local image host")
        return None

    image_id = secrets.token_urlsafe(16)
    file_name = f"gen/{image_id}.jpg"
    metadata = {"upload-time": datetime.now().isoformat()}
    if user_id:
        metadata["user-id"] = str(user_id)

    try:
        session = aioboto3.Session()
        async with session.client(
            "s3",
            endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name="auto",
        ) as client:
            await client.put_object(
                Bucket=R2_BUCKET_NAME,
                Key=file_name,
                Body=image_bytes,
                ContentType="image/jpeg",
                CacheControl="public, max-age=259200",
                Metadata=metadata,
            )
        base_url = R2_PUBLIC_URL.rstrip("/") if R2_PUBLIC_URL else f"https://pub-{R2_ACCOUNT_ID}.r2.dev"
        url = f"{base_url}/{file_name}"
        return url
    except Exception:
        logger.exception("[R2] Upload failed")
        return None


async def smart_upload(image, user_id=None):
    """Upload one image and return identical original and preview URLs."""
    try:
        image_bytes = await asyncio.to_thread(_encode_jpeg, image)
    except Exception:
        logger.exception("[ImageUploader] JPEG encoding failed")
        return None, None

    if R2_ENABLED and len(image_bytes) <= R2_MAX_BYTES:
        url = await _upload_to_r2(image_bytes, user_id)
        if url:
            return url, url
    elif R2_ENABLED:
        logger.debug("[ImageUploader] Image too large for R2: %.1fMB", len(image_bytes) / 1024 / 1024)

    url = await asyncio.to_thread(_save_to_local, image_bytes)
    return (url, url) if url else (None, None)


async def upload_generated_image(image, user_id=None):
    """Upload an owned generated image and always release its pixel buffer."""
    try:
        return await smart_upload(image, user_id)
    finally:
        image.close()
