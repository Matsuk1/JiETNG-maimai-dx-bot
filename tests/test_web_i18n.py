"""Web translation behavior after merging the Flask helpers into i18n."""
import subprocess
import sys

from pathlib import Path

from flask import Flask, render_template
from jinja2 import DictLoader

from modules.i18n import error_page, language_codes, localized_payload, register_web_i18n


ROOT = Path(__file__).resolve().parents[1]


def test_plain_translation_import_does_not_load_flask():
    subprocess.run(
        [sys.executable, '-c',
         'import sys; import modules.i18n; assert "flask" not in sys.modules'],
        check=True, capture_output=True, timeout=10,
    )


def test_localized_payload_preserves_partial_updates():
    assert localized_payload({'title': {'en': ' Hello ', 'ja': None}}, 'title') == {
        'en': 'Hello', 'ja': '',
    }
    assert localized_payload({'title_en': ' Hello '}, 'title', partial=True) == {'en': 'Hello'}
    assert localized_payload({}, 'title', partial=True) == {}
    assert localized_payload({}, 'title') == dict.fromkeys(language_codes(), '')


def test_web_context_and_error_translation():
    app = Flask(__name__)
    app.jinja_loader = DictLoader({'error.html': '{{ language }}|{{ message }}|{{ default_language }}'})
    register_web_i18n(app)
    with app.test_request_context():
        assert error_page({'en': 'Failure', 'ja': '失敗'}, 'ja', 403) == ('ja|失敗|ja', 403)
        assert error_page('Failure', 'unknown') == ('ja|Failure|ja', 400)


def test_import_token_copy_button_uses_translation_not_dict_method():
    app = Flask(__name__, template_folder=str(ROOT / "templates"))
    register_web_i18n(app)

    with app.test_request_context():
        html = render_template(
            "success.html",
            language="zh",
            mode="import_token",
            import_token="secret-token",
        )

    assert '<button type="button" class="copy-btn" id="copy-token-btn">\n        复制 Token\n      </button>' in html
    assert "built-in method copy" not in html
