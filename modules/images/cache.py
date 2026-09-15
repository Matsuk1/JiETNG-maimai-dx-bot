"""Download and cache image assets used by generated cards."""

import logging
import os
import tempfile
from io import BytesIO

import requests
from PIL import Image, UnidentifiedImageError
from requests.adapters import HTTPAdapter

from modules.config_loader import COVERS_DIR


logger = logging.getLogger(__name__)
DOWNLOAD_ATTEMPTS = 3


def _build_session() -> requests.Session:
    session = requests.Session()
    session.verify = False
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://maimaidx.jp",
    })
    adapter = HTTPAdapter(pool_connections=20, pool_maxsize=50)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


_SESSION = _build_session()


def _write_cache(path, content):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        os.replace(temp_path, path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def _download_rgba(url, *, timeout, label):
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            response = _SESSION.get(url, timeout=timeout)
            response.raise_for_status()
            with Image.open(BytesIO(response.content)) as image:
                return image.convert("RGBA"), response.content
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status is not None and status < 500:
                logger.warning("[ImageCache] Download rejected: asset=%s, status=%s", label, status)
                return None, None
            error = exc
        except (requests.ConnectionError, requests.Timeout) as exc:
            error = exc
        except UnidentifiedImageError:
            logger.warning("[ImageCache] Invalid image response: asset=%s", label)
            return None, None

        if attempt < DOWNLOAD_ATTEMPTS:
            logger.warning(
                "[ImageCache] Download retry: asset=%s, attempt=%s/%s, error=%s",
                label,
                attempt,
                DOWNLOAD_ATTEMPTS,
                error,
            )
        else:
            logger.error("[ImageCache] Download failed: asset=%s, error=%s", label, error)
    return None, None


def _cached_or_downloaded_image(url, path, *, timeout, label):
    if path and os.path.isfile(path):
        try:
            with Image.open(path) as image:
                return image.convert("RGBA")
        except (OSError, UnidentifiedImageError) as exc:
            logger.warning("[ImageCache] Replacing invalid cache: path=%s, error=%s", path, exc)

    if not url:
        return None
    image, content = _download_rgba(url, timeout=timeout, label=label)
    if image is None:
        return None
    if path:
        try:
            _write_cache(path, content)
        except OSError:
            logger.exception("[ImageCache] Failed to cache asset: path=%s", path)
    return image


def download_and_cache_icon(url, save_path):
    try:
        return _cached_or_downloaded_image(
            url,
            save_path,
            timeout=10,
            label=os.path.basename(save_path),
        )
    except (OSError, requests.RequestException) as exc:
        logger.error("[ImageCache] Icon unavailable: url=%s, error=%s", url, exc)
        return None


def paste_icon_optimized(image, song_data, key, size, position, save_dir, url_func):
    value = song_data.get(key)
    if not value:
        return

    try:
        path = os.path.join(save_dir, f"{value}.png")
        icon = download_and_cache_icon(url_func(value), path)
        if icon:
            icon = icon.resize(size, Image.Resampling.LANCZOS)
            image.alpha_composite(icon, position)
    except (OSError, ValueError) as exc:
        logger.error("[ImageCache] Failed to paste icon: key=%s, error=%s", key, exc)


def get_cover_image(cover_url, cover_name=None):
    path = None
    if cover_name:
        path = os.path.join(COVERS_DIR, os.path.basename(cover_name))
    try:
        image = _cached_or_downloaded_image(
            cover_url,
            path,
            timeout=30,
            label=cover_name or cover_url,
        )
        if image is None and not cover_url:
            logger.warning("[ImageCache] Missing cover URL: cover_name=%s", cover_name)
        return image
    except (OSError, requests.RequestException) as exc:
        logger.error(
            "[ImageCache] Cover unavailable: cover_name=%s, error=%s",
            cover_name,
            exc,
        )
        return None
