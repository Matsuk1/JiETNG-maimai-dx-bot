"""Discover image skins and resolve per-template overrides.

Skin IDs are local directory names, never paths supplied by callers. Missing
skins or overrides fall back to the existing templates without changing data.
"""
import json
import re
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[1] / 'templates' / 'images'
SKINS = TEMPLATES / 'skins'


def available_skins():
    skins = [dict(id='default', label='默认', templates=[])]
    for manifest in sorted(SKINS.glob('*/skin.json')):
        skin_id = manifest.parent.name
        if not re.fullmatch(r'[a-z0-9_-]+', skin_id) or skin_id == 'default':
            continue
        try:
            metadata = json.loads(manifest.read_text())
            label = metadata['label']
            if not isinstance(label, str):
                continue
        except (OSError, ValueError, KeyError, TypeError):
            continue
        skins.append(dict(id=skin_id, label=label,
                          templates=sorted(p.name for p in manifest.parent.glob('*.html'))))
    return skins


def resolve_template(name, skin='default'):
    """Resolve only registered overrides; always retain the default fallback."""
    if skin != 'default' and any(item['id'] == skin for item in available_skins()):
        if Path(name).name == name and (SKINS / skin / name).is_file():
            return f'skins/{skin}/{name}'
    return name


# Template expansion happens on the caller thread before screenshot submission.
# ContextVar keeps nested generators in one skin without cross-request leakage.
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

_current_skin = ContextVar('image_skin', default='default')


def current_skin():
    return _current_skin.get()


@contextmanager
def use_skin(skin=None):
    token = _current_skin.set(current_skin() if skin is None else skin)
    try:
        yield
    finally:
        _current_skin.reset(token)


def skinnable(function):
    """Add an optional skin keyword to a composite image generator."""
    @wraps(function)
    def wrapped(*args, skin=None, **kwargs):
        with use_skin(skin):
            return function(*args, **kwargs)
    return wrapped
