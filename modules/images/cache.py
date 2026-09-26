"""Download and cache image assets used by generated cards."""

import logging
import os
import tempfile
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, UnidentifiedImageError
from requests.adapters import HTTPAdapter

from modules.config_loader import COVERS_DIR


logger = logging.getLogger(__name__)
DOWNLOAD_ATTEMPTS = 3
COVER_WEBP_QUALITY = 90


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


def cover_cache_path(cover_name):
    """Map source cover names to the canonical WebP cache path."""
    if not cover_name:
        return None
    name = Path(os.path.basename(cover_name)).with_suffix(".webp").name
    return os.path.join(COVERS_DIR, name)


def _encode_cover_webp(image):
    with BytesIO() as buffer:
        image.save(buffer, format="WEBP", quality=COVER_WEBP_QUALITY, method=4)
        return buffer.getvalue()


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


def _cached_or_downloaded_image(url, path, *, timeout, label, encoder=None):
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
            _write_cache(path, encoder(image) if encoder else content)
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



def get_cover_image(cover_url, cover_name=None):
    path = cover_cache_path(cover_name)
    try:
        image = _cached_or_downloaded_image(
            cover_url,
            path,
            timeout=30,
            label=cover_name or cover_url,
            encoder=_encode_cover_webp,
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
