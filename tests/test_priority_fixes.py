"""Regression checks without production services or OCR model initialization."""
import ast
import copy
from io import BytesIO
import logging
from pathlib import Path
import threading
import time
import unittest

from flask import Blueprint, Flask, jsonify, request, send_file
from PIL import Image

from modules.score_recognition_api import (
    ScoreRecognitionResultError,
    build_score_recognition_response,
)
from modules.task_runtime import execute_task

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger("priority-tests")


def isolated_function(path, name, namespace):
    """Load a handler's actual body without importing service startup hooks."""
    namespace.setdefault("__name__", __name__)
    tree = ast.parse((ROOT / path).read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, "exec"), namespace)
    return namespace[name]


def valid_result():
    return {
        "parsed": {"achievement": 101.0, "sub_judgement": {
            row: {"critical_perfect": 1, "perfect": 0, "great": 0, "good": 0, "miss": 0}
            for row in ("tap", "hold", "slide", "touch", "break")
        }},
        "validation": {"song_id": "test", "achievement_calc": {
            "consistent": True, "complete": True,
        }},
    }


class TaskTests(unittest.TestCase):
    def run_task(self, func, semaphore, **kwargs):
        return execute_task(func, (), semaphore, tracking={"queued": [], "running": [], "completed": []},
                            tracking_lock=threading.Lock(), logger=LOGGER, **kwargs)

    def test_timeout_keeps_capacity_until_actual_exit(self):
        release = threading.Event()
        started = threading.Event()
        semaphore = threading.Semaphore(1)
        completed = []
        errors = []

        def blocking():
            started.set()
            release.wait(2)

        try:
            before = time.monotonic()
            result = self.run_task(blocking, semaphore, timeout=0.05,
                                   on_complete=lambda *a: completed.append(a),
                                   on_error=lambda *a: errors.append(a))
            self.assertTrue(started.is_set())
            self.assertEqual(result.status, "timed_out")
            self.assertLess(time.monotonic() - before, 1)
            self.assertFalse(semaphore.acquire(blocking=False))
            forbidden = threading.Event()
            result = self.run_task(forbidden.set, semaphore, timeout=0.02)
            self.assertEqual(result.status, "timed_out")
            self.assertFalse(forbidden.is_set())
        finally:
            release.set()
        self.assertTrue(semaphore.acquire(timeout=1))
        semaphore.release()
        self.assertEqual(len(completed), 1)
        self.assertEqual(len(errors), 1)
        self.assertEqual(self.run_task(lambda: None, semaphore, timeout=1).status, "completed")

    def test_failure_releases_capacity_and_reports_once(self):
        semaphore = threading.Semaphore(1)
        errors = []

        def fail():
            raise ValueError("expected test failure")

        result = self.run_task(fail, semaphore, timeout=1, on_error=lambda *a: errors.append(a))
        self.assertEqual(result.status, "failed")
        self.assertEqual(len(errors), 1)
        self.assertTrue(semaphore.acquire(blocking=False))


class ResponseTests(unittest.TestCase):
    def test_rejects_failed_or_incomplete_validation(self):
        for key in ("consistent", "complete"):
            for value in (False, None):
                result = valid_result()
                result["validation"]["achievement_calc"][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ScoreRecognitionResultError):
                    build_score_recognition_response(result)
        for key, value in (("uncertain_cells", [{"row": "tap"}]), ("unmatched_notes", {"tap": 1})):
            result = valid_result()
            result["validation"][key] = value
            with self.assertRaises(ScoreRecognitionResultError):
                build_score_recognition_response(result)

    def test_achievement_bounds_and_valid_response(self):
        self.assertTrue(build_score_recognition_response(valid_result())["success"])
        for value in (True, float("nan"), float("inf"), -1, 102):
            result = valid_result()
            result["parsed"]["achievement"] = value
            with self.subTest(value=value), self.assertRaises(ScoreRecognitionResultError):
                build_score_recognition_response(result)

    def test_admin_save_failure_and_success(self):
        for saved in (False, True):
            handler = isolated_function("modules/api/admin_api.py", "admin_edit_user", {
                "check_admin_auth": lambda: True,
                "_json_body": lambda: {"user_id": "test", "user_data": {"nickname": "new"}},
                "user_exists": lambda _: True, "get_user": lambda _: {"nickname": "old"},
                "save_user": lambda *a: saved, "jsonify": jsonify, "logger": LOGGER,
            })
            app = Flask(__name__)
            app.add_url_rule("/edit", view_func=handler, methods=["POST"])
            response = app.test_client().post("/edit")
            self.assertEqual(response.status_code, 200 if saved else 500)
            self.assertEqual(response.json["success"], saved)

    def test_api_rejects_invalid_result_and_uses_same_candidate(self):
        current = valid_result()
        rendered = []
        expand = isolated_function("modules/score_result_recognizer.py", "expand_score_recognition_calc_variants", {})

        def auth(fn):
            def wrapped():
                request.token_info = {"token_id": "test"}
                return fn()
            return wrapped

        def render(result, **kwargs):
            rendered.append(copy.deepcopy(result))
            return Image.new("RGB", (2, 2))

        factory = isolated_function("modules/api/score_api.py", "create_score_api", {
            "Blueprint": Blueprint, "jsonify": jsonify, "request": request, "send_file": send_file,
            "BytesIO": BytesIO, "time": time, "logger": LOGGER,
            "require_dev_token": auth, "check_rate_limit": lambda *a: False,
            "recognize_score_image_bytes": lambda *a, **kw: copy.deepcopy(current),
            "validate_recognized_judgement": lambda r, **kw: r,
            "expand_score_recognition_calc_variants": expand,
            "build_score_recognition_response": build_score_recognition_response,
            "generate_score_recognition_picture": render,
            "UnsupportedScoreImageError": type("Unsupported", (Exception,), {}),
            "InvalidScoreImageError": type("Invalid", (Exception,), {}),
            "ScoreRecognitionResultError": ScoreRecognitionResultError,
        })
        app = Flask(__name__)
        app.register_blueprint(factory(1024))
        client = app.test_client()

        def post(suffix=""):
            return client.post("/api/v2/score-recognition" + suffix,
                               data={"image": (BytesIO(b"stubbed OCR input"), "score.png")})

        current["validation"]["achievement_calc"]["consistent"] = False
        for suffix in ("", "/image"):
            self.assertEqual(post(suffix).status_code, 422)
        self.assertFalse(rendered)
        candidate = copy.deepcopy(valid_result()["parsed"]["sub_judgement"])
        candidate["tap"]["critical_perfect"] = 2
        current["validation"]["calc_completion_candidates"] = [{
            "judgement": candidate, "score_range": {"minimum": 101, "maximum": 101},
        }]
        response = post()
        self.assertEqual(response.status_code, 200)
        image_response = post("/image")
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response.mimetype, "image/png")
        self.assertEqual(response.json["score"]["judgements"], rendered[0]["parsed"]["sub_judgement"])


if __name__ == "__main__":
    unittest.main()
