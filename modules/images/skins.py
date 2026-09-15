"""Discover image skins and resolve per-template overrides.

Skin IDs are local directory names, never paths supplied by callers. Missing
skins or overrides fall back to the existing templates without changing data.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from inspect import iscoroutinefunction, signature
import json
import re
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[2] / 'templates' / 'images'
SKINS = TEMPLATES / 'skins'


def available_skins():
    skins = [dict(id='default', label='Default', uses_background=True, templates=[])]
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
                          uses_background=metadata.get('uses_background') is True,
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


def skin_config(skin=None):
    selected = current_skin() if skin is None else skin
    return next((item for item in available_skins() if item['id'] == selected), available_skins()[0])


def normalize_skin(skin):
    return skin_config(skin)['id']


_user_skin_active = ContextVar('user_image_skin_user_skin_active', default=False)


def user_skin(user_id):
    from modules.user_manager import get_user
    return normalize_skin((get_user(user_id) or {}).get('image_skin', 'default')) if user_id else 'default'


@contextmanager
def user_image_context(user_id):
    # Mention/friend images retain the requester's choice, not the target's.
    if not user_id or _user_skin_active.get():
        yield
        return
    token = _user_skin_active.set(True)
    try:
        with use_skin(user_skin(user_id)):
            yield
    finally:
        _user_skin_active.reset(token)


def user_image(function):
    sig = signature(function)

    def owner(args, kwargs):
        return sig.bind_partial(*args, **kwargs).arguments.get('user_id')

    if iscoroutinefunction(function):
        @wraps(function)
        async def wrapped(*args, **kwargs):
            with user_image_context(owner(args, kwargs)):
                return await function(*args, **kwargs)
    else:
        @wraps(function)
        def wrapped(*args, **kwargs):
            with user_image_context(owner(args, kwargs)):
                return function(*args, **kwargs)
    return wrapped
