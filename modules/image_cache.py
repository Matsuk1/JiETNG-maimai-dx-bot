"""
图片缓存和下载工具模块
统一管理图片的下载、缓存和加载

使用独立的 session 实例避免污染
"""
import os
import requests
import urllib3
from PIL import Image
from io import BytesIO
from functools import lru_cache
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        print(f"[image_cache] Error downloading {url}: {e}")
        return None


@lru_cache(maxsize=2048)
def get_cached_image(url):
    """
    从 URL 获取图片（带内存缓存）

    注意：LRU cache 基于 URL，不会跨线程共享 session 状态

    Args:
        url: 图片URL

    Returns:
        PIL.Image 或 None
    """
    try:
        # 每次调用都创建新的请求（避免 session 污染）
        # 对于图片下载，创建新请求的开销可以接受
        response = requests.get(
            url,
            timeout=10,
            verify=False,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://maimaidx.jp"
            }
        )
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"[image_cache] Error loading {url}: {e}")
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
        print(f"[paste_icon_optimized] Error for '{key}': {e}")


def batch_download_images(urls, max_workers=10):
    """
    并发批量下载图片

    Args:
        urls: URL 列表
        max_workers: 最大并发数

    Returns:
        dict: {url: PIL.Image} 字典
    """
    results = {}

    def download_single(url):
        try:
            img = get_cached_image(url)
            return url, img
        except Exception as e:
            print(f"[batch_download] Error downloading {url}: {e}")
            return url, None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_single, url): url for url in urls}
        for future in as_completed(futures):
            url, img = future.result()
            if img:
                results[url] = img

    return results
