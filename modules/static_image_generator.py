"""Cached HTML rendering for static application images."""
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from modules.image_skins import current_skin
from modules.html_renderer import file_uri, render_template


def admin_icon_png(logo_path, skin=None):
    path = Path(logo_path).resolve()
    return _admin_icon_png(str(path), path.stat().st_mtime_ns, current_skin() if skin is None else skin)


@lru_cache(maxsize=8)
def _admin_icon_png(logo_path, modified, skin):
    with render_template('admin_icon.html', 512, 512, skin=skin, logo=file_uri(logo_path)) as image:
        with BytesIO() as output, image.convert('RGB') as rgb:
            rgb.save(output, format='PNG')
            return output.getvalue()
