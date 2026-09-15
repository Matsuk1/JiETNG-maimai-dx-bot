"""Web translation behavior after merging the Flask helpers into i18n."""
import subprocess
import sys

from flask import Flask
from jinja2 import DictLoader

from modules.i18n import error_page, language_codes, localized_payload, register_web_i18n


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
