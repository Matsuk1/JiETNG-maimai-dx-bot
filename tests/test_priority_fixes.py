"""Regression checks without production services or OCR model initialization."""
import copy
from io import BytesIO
import logging
import threading
import time
import unittest
from types import SimpleNamespace

from flask import Flask, request
from PIL import Image

from modules.score_recognition.presentation import (
    ScoreRecognitionResultError,
    build_score_recognition_response,
)
from modules.api.admin_users import create_edit_user_handler
from modules.api.score_api import create_score_api, ScoreApiServices
from modules.commands.command_router import CommandContext
from modules.task_runtime import execute_task, task_context

LOGGER = logging.getLogger("priority-tests")


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
            handler = create_edit_user_handler(
                check_admin_auth=lambda: True,
                read_body=lambda: {"user_id": "test", "user_data": {"nickname": "new"}},
                user_exists=lambda _: True, update_user_fields=lambda *a: saved,
            )
            app = Flask(__name__)
            app.add_url_rule("/edit", view_func=handler, methods=["POST"])
            response = app.test_client().post("/edit")
            self.assertEqual(response.status_code, 200 if saved else 500)
            self.assertEqual(response.json["success"], saved)

    def test_api_rejects_invalid_result_and_uses_same_candidate(self):
        current = valid_result()
        rendered = []

        def auth(fn):
            def wrapped():
                request.token_info = {"token_id": "test"}
                return fn()
            return wrapped

        def render(result, **kwargs):
            rendered.append(copy.deepcopy(result))
            return Image.new("RGB", (2, 2))

        services = ScoreApiServices(
            authorize=auth, rate_limit=lambda *a: False,
            recognize=lambda *a, **kw: copy.deepcopy(current),
            validate=lambda r, **kw: r, render=render,
        )
        app = Flask(__name__)
        app.register_blueprint(create_score_api(1024, services=services))
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



class CommandTaskContextTests(unittest.TestCase):
    def test_context_keeps_sender_for_error_reporting(self):
        ctx=CommandContext(event=None,text='song record',user_id='sender',source_type='group',reply_token='reply',mentioned_user_id='target',has_other_mention=True,id_use='target',mai_ver='jp',mai_ver_use='intl')
        task=task_context((ctx,))
        self.assertEqual((task.user_id,task.reply_token,task.source_type),('sender','reply','group'))
    def test_legacy_event_still_supported(self):
        event=SimpleNamespace(source=SimpleNamespace(user_id='sender',type='user'),reply_token='reply')
        self.assertEqual(task_context((event,)).user_id,'sender')
