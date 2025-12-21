"""
图片缓存和下载工具模块
统一管理图片的下载、缓存和加载

使用独立的 session 实例避免污染
"""
import os
import requests
import logging
from PIL import Image
from io import BytesIO
from functools import lru_cache
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from modules.config_loader import COVERS_DIR


# 获取logger
logger = logging.getLogger(__name__)

# 线程本地存储（每个线程独立的 session）
_thread_local = threading.local()


def _get_session():
    """
    获取当前线程的专用 session
    每个线程有独立的 session，避免污染
    """
    if not hasattr(_thread_local, 'session'):
        session = requests.Session()
        session.verify = False
        session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://maimaidx.jp"
        })
        _thread_local.session = session
    return _thread_local.session


def download_and_cache_icon(url, save_path):
    """
    下载图标并缓存到本地

    Args:
        url: 图标URL
        save_path: 保存路径

    Returns:
        PIL.Image 或 None
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # 如果文件已存在，直接加载
        if os.path.exists(save_path):
            return Image.open(save_path).convert("RGBA")

        # 使用当前线程的 session 下载
        session = _get_session()
        response = session.get(url, timeout=10)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

        return Image.open(save_path).convert("RGBA")

    except Exception as e:
        logger.error(f"[ImageCache] ✗ Download failed: url={url}, error={e}")
        return None


def paste_icon_optimized(img, song_data, key, size, position, save_dir, url_func):
    """
    优化版的贴图标函数

    Args:
        img: 目标图像
        song_data: 歌曲数据字典
        key: 数据中的键名
        size: 图标尺寸 (width, height)
        position: 粘贴位置 (x, y)
        save_dir: 缓存目录
        url_func: URL生成函数
    """
    if key not in song_data or not song_data[key]:
        return

    try:
        file_path = os.path.join(save_dir, f"{song_data[key]}.png")
        url = url_func(song_data[key])

        icon_img = download_and_cache_icon(url, file_path)
        if icon_img:
            icon_img = icon_img.resize(size, Image.LANCZOS)
            img.paste(icon_img, position, mask=icon_img)

    except Exception as e:
        logger.error(f"[ImageCache] ✗ Failed to paste icon: key={key}, error={e}")


def get_cover_image(cover_url, cover_name, covers_dir=None):
    """
    获取封面图片（优先从本地加载，不存在则下载）

    Args:
        cover_url: 封面图片 URL（不带扩展名）
        cover_name: 封面文件名（hash，不带扩展名）
        covers_dir: 本地封面缓存目录（默认使用配置中的路径）

    Returns:
        PIL.Image 或 None
    """
    try:
        # 使用配置中的路径（如果未指定）
        if covers_dir is None:
            covers_dir = COVERS_DIR

        # 确保缓存目录存在
        os.makedirs(covers_dir, exist_ok=True)

        local_path = os.path.join(covers_dir, cover_name)

        # 1. 首先尝试从本地加载
        if os.path.exists(local_path):
            try:
                return Image.open(local_path).convert("RGBA")
            except Exception as e:
                logger.warning(f"[ImageCache] ⚠ Local file corrupted, re-downloading: path={local_path}, error={e}")
                # 如果本地文件损坏，删除它并重新下载
                os.remove(local_path)

        # 2. 本地不存在，从 URL 下载
        if not cover_url:
            logger.warning(f"[ImageCache] ⚠ No cover URL provided: cover_name={cover_name}")
            return None

        session = _get_session()

        download_url = cover_url

        # 重试机制：最多尝试 3 次
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = session.get(download_url, timeout=30)
                response.raise_for_status()

                # 3. 保存到本地
                with open(local_path, "wb") as f:
                    f.write(response.content)

                # 4. 返回图片对象
                return Image.open(local_path).convert("RGBA")

            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.warning(f"[ImageCache] ⚠ Download timeout, retrying: cover_name={cover_name}, attempt={attempt + 1}/{max_retries}")
                    continue  # 重试
                else:
                    logger.error(f"[ImageCache] ✗ Download timeout after retries: cover_name={cover_name}, attempts={max_retries}")
                    return None
            except requests.exceptions.HTTPError as e:
                # 403/404 等 HTTP 错误不重试
                if e.response.status_code in [403, 404]:
                    logger.warning(f"[ImageCache] ⚠ HTTP error (no retry): cover_name={cover_name}, status={e.response.status_code}")
                    return None
                logger.error(f"[ImageCache] ✗ HTTP error: cover_name={cover_name}, error={e}")
                return None

    except Exception as e:
        logger.error(f"[ImageCache] ✗ Failed to download cover: cover_name={cover_name}, error={e}")
        return None
