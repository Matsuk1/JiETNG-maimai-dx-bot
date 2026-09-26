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
        self.assertIsInstance(errors[0][1], TimeoutError)
        self.assertIn("Stack snapshot at timeout", errors[0][3])
        self.assertIn("blocking", errors[0][3])
        self.assertEqual(self.run_task(lambda: None, semaphore, timeout=1).status, "completed")

    def test_capacity_timeout_explains_that_task_did_not_start(self):
        semaphore = threading.Semaphore(0)
        errors = []

        result = self.run_task(
            lambda: None,
            semaphore,
            timeout=0.01,
            on_error=lambda *args: errors.append(args),
        )

        self.assertEqual(result.status, "timed_out")
        self.assertEqual(len(errors), 1)
        self.assertIn("did not start", errors[0][3])

    def test_failure_releases_capacity_and_reports_once(self):
        semaphore = threading.Semaphore(1)
        errors = []

        def fail():
            raise ValueError("expected test failure")

        result = self.run_task(fail, semaphore, timeout=1, on_error=lambda *a: errors.append(a))
        self.assertEqual(result.status, "failed")
        self.assertEqual(len(errors), 1)
        self.assertTrue(semaphore.acquire(blocking=False))


def test_maimai_service_timeout_uses_query_failure_without_admin_notification():
    import ast
    from pathlib import Path

    from modules.maimai_manager import MaimaiServiceTimeout

    source = Path(__file__).resolve().parents[1] / "main.py"
    handler_node = next(
        node for node in ast.parse(source.read_text()).body
        if isinstance(node, ast.FunctionDef) and node.name == "_handle_task_error"
    )
    notifications = []
    replies = []
    namespace = {
        "MaimaiServiceTimeout": MaimaiServiceTimeout,
        "notify_admins_error": lambda **kwargs: notifications.append(kwargs),
        "generate_status_flex": lambda *args, **kwargs: (args, kwargs),
        "language_catalog": lambda key: key,
        "system_error": lambda user_id: ("system_error", user_id),
        "smart_reply": lambda *args, **kwargs: replies.append((args, kwargs)),
        "configuration": object(),
        "logger": SimpleNamespace(warning=lambda *args, **kwargs: None),
    }
    exec(compile(ast.Module(body=[handler_node], type_ignores=[]), str(source), "exec"), namespace)

    context = SimpleNamespace(user_id="U-test", reply_token="reply", source_type="user")
    namespace["_handle_task_error"](
        lambda: None,
        MaimaiServiceTimeout("Maimai login and score fetch operation exceeded 10s"),
        context,
        "traceback",
    )

    assert notifications == []
    assert len(replies) == 1
    message = replies[0][0][2]
    assert message[0][:2] == (
        "main.query_failed_title",
        "main.maimai_service_busy_body",
    )
    assert message[1]["tone"] == "danger"
    assert replies[0][1]["addition"] is False

    replies.clear()
    namespace["_handle_task_error"](
        lambda: None,
        RuntimeError("real application failure"),
        context,
        "traceback",
    )
    assert len(notifications) == 1
    assert replies[0][0][2] == ("system_error", "U-test")


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

    def test_inferred_note_counts_do_not_publish_candidate_chart_metadata(self):
        result = valid_result()
        result["validation"].update(
            difficulty="master",
            level="14+",
            internal_level=14.8,
            inferred_note_count_rows=["tap", "hold", "slide", "touch", "break"],
        )

        response = build_score_recognition_response(result)

        self.assertEqual(response["chart"], {
            "difficulty": None,
            "level": None,
            "internal_level": None,
        })
        self.assertFalse(response["metadata"]["chart_metadata_confirmed"])
        self.assertFalse(response["validation"]["chart_metadata_confirmed"])

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
