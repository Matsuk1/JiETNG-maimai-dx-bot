"""Language registration, locale normalization, and translation fallback."""

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from languages import iter_language_plugins


TextTransform = Callable[[str], str]
DEFAULT_LANGUAGE = "en"
DEFAULT_WEB_LANGUAGE = "ja"
IMAGE_LANGUAGES = {"jp": "ja", "intl": "en"}


@dataclass(frozen=True, slots=True)
class Language:
    label: str
    aliases: tuple[str, ...] = ()
    fallbacks: tuple[str, ...] = ()
    transforms: Mapping[str, TextTransform] = field(default_factory=dict)
    texts: Mapping[str, Any] = field(default_factory=dict)


LANGUAGES: dict[str, Language] = {}


def _clean_code(language: Any) -> str:
    return str(language or "").strip().lower().replace("_", "-")


def _resolve_registered_language(code: str) -> str | None:
    candidate = code
    while candidate:
        if candidate in LANGUAGES:
            return candidate
        for language, definition in LANGUAGES.items():
            if candidate in definition.aliases:
                return language
        candidate = candidate.rpartition("-")[0]
    return None


def register_language(
    code: str,
    *,
    label: str | None = None,
    aliases=(),
    fallbacks=(),
    transforms: Mapping[str, TextTransform] | None = None,
    texts: Mapping[str, Any] | None = None,
):
    """Register a language without changing normalization or selection code."""
    code = _clean_code(code)
    if not code:
        raise ValueError("Language code must not be empty")
    LANGUAGES[code] = Language(
        label=label or code,
        aliases=tuple(_clean_code(alias) for alias in aliases),
        fallbacks=tuple(_clean_code(item) for item in fallbacks),
        transforms=dict(transforms or {}),
        texts=dict(texts or {}),
    )
    return code


def _load_language_plugins():
    for plugin in iter_language_plugins():
        definition = dict(plugin.LANGUAGE)
        definition["texts"] = getattr(plugin, "TEXTS", {})
        register_language(**definition)


_load_language_plugins()

if DEFAULT_LANGUAGE not in LANGUAGES or DEFAULT_WEB_LANGUAGE not in LANGUAGES:
    raise RuntimeError("Default language plugins are missing")


def language_codes() -> tuple[str, ...]:
    return tuple(LANGUAGES)


def language_options() -> tuple[dict[str, str], ...]:
    return tuple(
        {"code": code, "label": definition.label}
        for code, definition in LANGUAGES.items()
    )


def language_label(language: Any) -> str:
    code = normalize_language(language)
    return LANGUAGES[code].label


def language_catalog(path: str) -> dict[str, Any]:
    """Return one catalog entry keyed by every plugin's language code."""
    keys = path.split(".") if path else ()
    catalog = {}
    for code, definition in LANGUAGES.items():
        value: Any = definition.texts
        for key in keys:
            if not isinstance(value, Mapping) or key not in value:
                break
            value = value[key]
        else:
            catalog[code] = value
    return catalog


def localized_catalog(path: str) -> dict[str, Any]:
    """Return a catalog section transposed to key -> language -> value."""
    def transpose(catalogs):
        values = list(catalogs.values())
        if values and all(isinstance(value, Mapping) for value in values):
            keys = dict.fromkeys(key for value in values for key in value)
            return {
                key: transpose(
                    {
                        language: value[key]
                        for language, value in catalogs.items()
                        if key in value
                    }
                )
                for key in keys
            }
        return dict(catalogs)

    return transpose(language_catalog(path))


def format_catalog(path: str, **values) -> dict[str, str]:
    """Format one text entry for every language plugin."""
    return {
        language: str(text).format(**values)
        for language, text in language_catalog(path).items()
    }


def normalize_language(language: Any, default=DEFAULT_LANGUAGE) -> str:
    normalized_default = (
        _resolve_registered_language(_clean_code(default)) or DEFAULT_LANGUAGE
    )
    return _resolve_registered_language(_clean_code(language)) or normalized_default


def image_language(version: Any) -> str:
    """Return the font-safe language used by image renderers."""
    return IMAGE_LANGUAGES.get(_clean_code(version), "ja")


def get_user_language(user_id: str | None, default=DEFAULT_LANGUAGE) -> str:
    if not user_id:
        return normalize_language(default)

    from modules.user_db import get_user_field, user_exists

    language = (
        get_user_field(user_id, "language", default)
        if user_exists(user_id)
        else default
    )
    return normalize_language(language, default)


def _fallback_chain(language: str, default_language: str):
    candidates = (
        language,
        *LANGUAGES[language].fallbacks,
        normalize_language(default_language),
        DEFAULT_LANGUAGE,
        *LANGUAGES,
    )
    resolved = (_resolve_registered_language(code) for code in candidates)
    yield from dict.fromkeys(code for code in resolved if code)


def _transform(value: str, target_language: str, source_language: str):
    transforms = LANGUAGES[target_language].transforms
    transform = transforms.get(source_language) or transforms.get("*")
    return transform(value) if transform else value


def select_text(
    text: Any,
    user_id: str | None = None,
    language: str | None = None,
    default_language=DEFAULT_LANGUAGE,
) -> str:
    if not isinstance(text, Mapping):
        return "" if text is None else str(text)

    target = (
        normalize_language(language, default_language)
        if language is not None
        else get_user_language(user_id, default_language)
    )
    for source in _fallback_chain(target, default_language):
        if text.get(source) is not None:
            return _transform(str(text[source]), target, source)

    source, value = next(
        ((str(code), value) for code, value in text.items() if value is not None),
        (target, ""),
    )
    return _transform(str(value), target, source)


def register_web_i18n(app):
    @app.context_processor
    def language_context():
        return {
            "default_language": DEFAULT_WEB_LANGUAGE,
            "i18n_catalog": language_catalog,
            "i18n_section": localized_catalog,
            "language_options": language_options(),
            "i18n_select": select_text,
        }


def localized_payload(data, key, *, partial=False):
    values = data.get(key)
    if isinstance(values, dict):
        return {str(code): str(value or "").strip() for code, value in values.items()}
    if partial:
        return {
            code: str(data.get(f"{key}_{code.replace('-', '_')}", "") or "").strip()
            for code in language_codes()
            if f"{key}_{code.replace('-', '_')}" in data
        }
    return {
        code: str(data.get(f"{key}_{code.replace('-', '_')}", "") or "").strip()
        for code in language_codes()
    }


def error_page(message, language=DEFAULT_WEB_LANGUAGE, status=400):
    from flask import render_template

    translations = None
    if isinstance(message, dict):
        translations = {
            code: select_text(
                message,
                language=code,
                default_language=DEFAULT_WEB_LANGUAGE,
            )
            for code in language_codes()
        }

    language = normalize_language(language, DEFAULT_WEB_LANGUAGE)
    selected_message = select_text(
        translations or message,
        language=language,
        default_language=DEFAULT_WEB_LANGUAGE,
    )
    return render_template(
        "error.html",
        message=selected_message,
        message_i18n=translations,
        language=language,
    ), status
