"""Offline HTML/CSS image rendering on one bounded, thread-confined browser worker.

The public boundary remains a Pillow image for upload/encoding compatibility.
No application data is interpreted as HTML; Jinja templates autoescape by default.
"""
import atexit
import base64
import os
import logging
from concurrent.futures import Future
from queue import Queue
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import threading

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
_ENV = Environment(loader=FileSystemLoader(ROOT / 'templates' / 'images'),
                   autoescape=select_autoescape(['html']), trim_blocks=True, lstrip_blocks=True)
_queue = Queue()
_worker_thread = None
_worker_lock = threading.Lock()
_slots = threading.BoundedSemaphore(8)
_playwright = None
_browser = None
_page = None


def image_uri(image):
    with BytesIO() as buffer:
        image.save(buffer, format='PNG')
        return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


def file_uri(path):
    """Embed local assets, including fonts, so Chromium needs no network access."""
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        return ''
    return _file_uri(str(path), path.stat().st_mtime_ns)


@lru_cache(maxsize=128)
def _file_uri(path, modified):
    import mimetypes
    mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    if mime.startswith('image/'):
        try:
            with Image.open(path) as asset:
                asset.verify()
        except (OSError, ValueError):
            logging.getLogger(__name__).warning('Invalid optional image asset: %s', path)
            return ''
    return f'data:{mime};base64,' + base64.b64encode(Path(path).read_bytes()).decode('ascii')


def template(name, **data):
    return _ENV.get_template(name).render(**data)


def _close_browser():
    global _browser, _playwright, _page
    try:
        if _browser is not None:
            _browser.close()
    finally:
        _browser = None
        _page = None
        if _playwright is not None:
            _playwright.stop()
            _playwright = None


def _screenshot(body, width, height):
    global _playwright, _browser, _page
    from playwright.sync_api import sync_playwright
    if _browser is None or not _browser.is_connected():
        _close_browser()
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=True)
    if _page is None or _page.is_closed():
        _page = _browser.new_page(viewport={'width': width, 'height': height or 800},
                                 device_scale_factor=1, reduced_motion='reduce')
        _page.route('**/*', lambda route: route.abort())
        _page.set_default_timeout(30000)
        _page.set_content(template('document.html', body='', width=width, height=height,
                                   font=file_uri('assets/fonts/line_seed_jietng.ttf')))
    try:
        _page.set_viewport_size({'width': width, 'height': min(height or 800, 2000)})
        _page.evaluate("""({body,width,height}) => {
            const root = document.getElementById('image-root');
            root.style.width = width + 'px';
            root.style.height = height ? height + 'px' : 'auto';
            root.innerHTML = body;
        }""", dict(body=body, width=width, height=height))
        _page.evaluate("""async () => {
            await document.fonts.ready;
            await Promise.all([...document.images].map(img => img.decode()));
            for (const el of document.querySelectorAll('[data-fit]')) {
                const minimum = Number(el.dataset.fit) || 12;
                let size = parseFloat(getComputedStyle(el).fontSize);
                while (el.scrollWidth > el.clientWidth && size > minimum) {
                    el.style.fontSize = `${--size}px`;
                }
            }
        }""")
        return _page.locator('#image-root').screenshot(type='png', omit_background=True,
                                                      animations='disabled')
    except Exception:
        _page.close()
        _page = None
        raise
    finally:
        if _page is not None and not _page.is_closed():
            _page.evaluate("document.getElementById('image-root').replaceChildren()")


def render_html(body, width, height=None):
    width = int(width)
    height = int(height) if height is not None else None
    if width < 1 or (height is not None and height < 1):
        raise ValueError('Image dimensions must be positive')
    if not _slots.acquire(timeout=60):
        raise TimeoutError('Image renderer is busy; retry later')
    try:
        global _worker_thread
        with _worker_lock:
            if _worker_thread is None:
                _worker_thread = threading.Thread(target=_work, name='image-renderer', daemon=True)
                _worker_thread.start()
        future = Future()
        _queue.put((future, body, width, height))
        png = future.result()
    finally:
        _slots.release()
    with Image.open(BytesIO(png)) as image:
        return image.convert('RGBA')


def render_template(name, width, height=None, **data):
    return render_html(template(name, **data), width, height)


def _work():
    try:
        while True:
            item = _queue.get()
            if item is None:
                return
            future, body, width, height = item
            try:
                future.set_result(_screenshot(body, width, height))
            except Exception as exc:
                future.set_exception(exc)
    finally:
        _close_browser()


def shutdown_renderer():
    global _worker_thread
    with _worker_lock:
        if _worker_thread is not None:
            _queue.put(None)
            _worker_thread.join()
            _worker_thread = None


atexit.register(shutdown_renderer)


def _after_fork():
    # A prefork server must never reuse its parent's thread or Playwright pipes.
    global _queue, _worker_thread, _worker_lock, _slots, _playwright, _browser, _page
    _queue = Queue()
    _worker_thread = None
    _worker_lock = threading.Lock()
    _slots = threading.BoundedSemaphore(8)
    _playwright = _browser = _page = None


if hasattr(os, 'register_at_fork'):
    os.register_at_fork(after_in_child=_after_fork)
