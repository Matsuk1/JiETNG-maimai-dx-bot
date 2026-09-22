import ast
from pathlib import Path

from flask import Flask, request


ROOT = Path(__file__).resolve().parents[1]


def _security_headers_app():
    source = (ROOT / "main.py").read_text()
    function = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == "set_security_headers"
    )
    function.decorator_list = []
    namespace = {"request": request}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(ROOT / "main.py"), "exec"), namespace)

    app = Flask(__name__)
    app.after_request(namespace["set_security_headers"])
    app.add_url_rule("/linebot/liff", endpoint="liff", view_func=lambda: "liff")
    app.add_url_rule("/regular", endpoint="regular", view_func=lambda: "regular")
    return app


def test_liff_entry_csp_allows_line_sdk_and_connections():
    response = _security_headers_app().test_client().get("/linebot/liff")
    policy = response.headers["Content-Security-Policy"]
    assert "script-src 'self' 'unsafe-inline' https://static.line-scdn.net" in policy
    assert "connect-src 'self' https://*.line.me https://*.line-scdn.net" in policy


def test_non_liff_pages_keep_strict_csp():
    response = _security_headers_app().test_client().get("/regular")
    policy = response.headers["Content-Security-Policy"]
    assert "script-src 'self' 'unsafe-inline';" in policy
    assert "connect-src 'self';" in policy
    assert "line-scdn.net" not in policy
