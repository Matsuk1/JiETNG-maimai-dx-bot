"""Flask integration for the language plugin system."""

from flask import render_template

from modules.i18n import (
    DEFAULT_WEB_LANGUAGE,
    language_catalog,
    language_codes,
    language_options,
    localized_catalog,
    normalize_language,
    select_text,
)


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
