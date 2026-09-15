"""Cached HTML rendering for static application images."""
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from modules.html_renderer import file_uri, render_template


def admin_icon_png(logo_path):
    path = Path(logo_path).resolve()
    return _admin_icon_png(str(path), path.stat().st_mtime_ns)


@lru_cache(maxsize=1)
def _admin_icon_png(logo_path, modified):
    with render_template('admin_icon.html', 512, 512, logo=file_uri(logo_path)) as image:
        with BytesIO() as output, image.convert('RGB') as rgb:
            rgb.save(output, format='PNG')
            return output.getvalue()
