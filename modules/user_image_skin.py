"""Apply the requesting user's image skin to a complete rendering operation."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from inspect import iscoroutinefunction, signature

from modules.image_skins import normalize_skin, use_skin

_active = ContextVar('user_image_skin_active', default=False)


def user_skin(user_id):
    from modules.user_manager import get_user
    return normalize_skin((get_user(user_id) or {}).get('image_skin', 'default')) if user_id else 'default'


@contextmanager
def user_image_context(user_id):
    # Mention/friend images retain the requester's choice, not the target's.
    if not user_id or _active.get():
        yield
        return
    token = _active.set(True)
    try:
        with use_skin(user_skin(user_id)):
            yield
    finally:
        _active.reset(token)


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
