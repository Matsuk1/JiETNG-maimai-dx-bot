"""Stable Flask signing key shared by local server processes."""

import fcntl
import os
from pathlib import Path
import secrets


def load_session_key():
    configured = os.environ.get("JIETNG_SESSION_SECRET")
    if configured:
        return configured

    path = Path(os.environ.get("JIETNG_SESSION_KEY_FILE", "./data/session.key"))
    path.parent.mkdir(parents=True, exist_ok=True)
    # Lock before reading/generating so simultaneous worker startup agrees on
    # one key. Failure to persist must fail startup, not silently rotate it.
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(descriptor, "r+", encoding="ascii") as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        os.fchmod(file.fileno(), 0o600)
        key = file.read().strip()
        if not key:
            key = secrets.token_hex(32)
            file.seek(0)
            file.write(key)
            file.truncate()
            file.flush()
            os.fsync(file.fileno())
        return key
