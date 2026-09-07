"""Shared path policy for AI monitor file access."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_FILE_ROOTS = {
    "data/dxdata": (PROJECT_ROOT / "data" / "dxdata").resolve(),
    "assets": (PROJECT_ROOT / "assets").resolve(),
    "languages": (PROJECT_ROOT / "languages").resolve(),
}
TEXT_FILE_SUFFIXES = {
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
IMAGE_FILE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_allowed_path(raw_path: str) -> tuple[Path | None, str | None]:
    if "\x00" in raw_path:
        return None, "path contains an invalid character"
    normalized = raw_path.strip().replace("\\", "/").strip("/")
    if not normalized:
        return None, "path is required"
    relative = Path(normalized)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        return None, "path must be a normalized relative path"
    if any(part.startswith(".") for part in relative.parts):
        return None, "hidden paths are not allowed"

    try:
        candidate = (PROJECT_ROOT / relative).resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return None, "path could not be resolved"
    if not any(_is_within(candidate, root) for root in ALLOWED_FILE_ROOTS.values()):
        return None, "path is outside the allowed directories"

    current = PROJECT_ROOT
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return None, "symbolic links are not allowed"
    return candidate, None


def is_asset_image(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() in IMAGE_FILE_SUFFIXES
        and _is_within(path, ALLOWED_FILE_ROOTS["assets"])
    )
