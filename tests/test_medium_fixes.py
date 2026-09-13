import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import Mock, patch

from flask import Flask, session
from PIL import Image

from modules.session_key import load_session_key
from modules.score_recognition import cropper
from test_priority_fixes import isolated_function


class SessionTests(unittest.TestCase):
    def test_parallel_processes_share_persistent_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.key"
            env = {**os.environ, "JIETNG_SESSION_KEY_FILE": str(path)}
            env.pop("JIETNG_SESSION_SECRET", None)
            code = "from modules.session_key import load_session_key; print(load_session_key())"
            processes = [subprocess.Popen([sys.executable, "-c", code], env=env,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(4)]
            outputs = [p.communicate(timeout=10) for p in processes]
            self.assertTrue(all(p.returncode == 0 for p in processes))
            self.assertEqual(len({out for out, _ in outputs}), 1)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with patch.dict(os.environ, env, clear=True):
                first = Flask("first")
                first.secret_key = load_session_key()
                with first.test_request_context():
                    session["admin_authenticated"] = True
                    cookie = first.session_interface.get_signing_serializer(first).dumps(dict(session))
                second = Flask("second")
                second.secret_key = load_session_key()
                self.assertTrue(second.session_interface.get_signing_serializer(second).loads(cookie)["admin_authenticated"])

    def test_environment_override_does_not_write_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unused"
            with patch.dict(os.environ, {"JIETNG_SESSION_SECRET": "test-explicit-secret",
                                         "JIETNG_SESSION_KEY_FILE": str(path)}):
                self.assertEqual(load_session_key(), "test-explicit-secret")
            self.assertFalse(path.exists())


class UserUpdateTests(unittest.TestCase):
    def test_editor_submits_only_changed_fields(self):
        source = (Path(__file__).resolve().parents[1] / "templates/admin_panel.html").read_text()
        editor = source.split("    let editingUserOriginalData", 1)[1].split("    // Close modal", 1)[0]
        script = '''
const assert = require('node:assert/strict');
const elements = {
  'data-user': {querySelector: () => ({textContent: '{"nickname":"old","version":"jp","settings":{"a":1}}'})},
  'edit-user-id': {}, 'edit-user-data': {},
  editUserModal: {classList: {add() {}, remove() {}}}
};
global.document = {getElementById: id => elements[id]};
global.confirm = () => true;
global.alert = () => {};
global.location = {reload() {}};
const sent = [];
global.fetch = (url, options) => {
  sent.push(JSON.parse(options.body));
  return Promise.resolve({json: () => Promise.resolve({success: true})});
};
''' + "let editingUserOriginalData" + editor + '''
editUser('user');
elements['edit-user-data'].value = '{"nickname":"new","version":"jp","settings":{"a":1}}';
saveUserData({preventDefault() {}});
assert.deepEqual(sent, [{user_id: 'user', user_data: {nickname: 'new'}}]);
editUser('user');
saveUserData({preventDefault() {}});
assert.equal(sent.length, 1);
'''
        subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True, timeout=10)

    def updater(self, cursor):
        @contextmanager
        def database_cursor(**kwargs):
            self.assertTrue(kwargs["write"])
            yield None, cursor

        return isolated_function("modules/user_db.py", "update_user_fields", {
            "database_cursor": database_cursor, "json": json,
            "_encode_json": json.dumps, "logger": logging.getLogger("test"),
        })

    def test_only_submitted_fields_are_sent_to_database(self):
        cursor = Mock(rowcount=1)
        updater = self.updater(cursor)
        self.assertTrue(updater("user", {'nickname': 'new', 'key.with"quote': None}))
        sql, args = cursor.execute.call_args.args
        self.assertIn("JSON_SET(data,", sql)
        self.assertNotIn('key.with', sql)
        self.assertEqual(args, ('$."nickname"', '"new"', '$."key.with\\"quote"', 'null', 'user'))
        self.assertEqual(cursor.execute.call_count, 1)
        # A second independent edit carries no stale nickname value.
        self.assertTrue(updater("user", {"version": "intl"}))
        self.assertEqual(cursor.execute.call_args.args[1], ('$."version"', '"intl"', 'user'))

    def test_unchanged_missing_and_failed_updates(self):
        cursor = Mock(rowcount=0)
        cursor.fetchone.return_value = (1,)
        updater = self.updater(cursor)
        self.assertTrue(updater("user", {"nickname": "same"}))
        cursor.fetchone.return_value = None
        self.assertFalse(updater("deleted", {"nickname": "new"}))
        cursor.execute.side_effect = OSError("simulated database failure")
        self.assertFalse(updater("user", {"nickname": "new"}))
        for value in ([], {}, None):
            with self.assertRaises(ValueError):
                updater("user", value)


class CropFallbackTests(unittest.TestCase):
    def run_crop(self, fallback, model=None, size=(500, 1000)):
        image = Image.new("RGB", size)
        screen = cropper.Box(0, 400, 500, 900)
        table = cropper.Box(50, 50, 450, 200)
        mocks = {
            "is_dxnet_result_screenshot": Mock(return_value=False),
            "detect_result_screen": Mock(return_value=screen),
            "detect_main_screen_with_cropper_model": Mock(return_value=(None, None)),
            "detect_main_title": Mock(return_value=cropper.Box(100, 450, 350, 480)),
            "detect_main_achievement": Mock(return_value=cropper.Box(100, 500, 350, 540)),
            "detect_sub_judgement_table_with_cropper_model": Mock(return_value=(
                table if model else None, table if model else None,
                "cropper_pt_pose_warp", Image.new("RGB", (400, 150)) if model else None)),
            "detect_sub_screen": Mock(return_value=cropper.Box(0, 0, 500, 250)),
            "detect_sub_judgement_table": Mock(return_value=fallback),
        }
        with patch.multiple(cropper, **mocks):
            result = cropper.crop_result_fields_in_memory(image)
        return result, mocks

    def test_model_failure_uses_complete_blue_grid(self):
        result, mocks = self.run_crop(cropper.Box(50, 50, 450, 200))
        field = result["fields"]["sub_judgement_table"]
        self.assertEqual(field["detector"], "blue_grid")
        self.assertIsNone(field["layout_hint"])
        self.assertEqual(field["image"].size, (400, 150))
        mocks["detect_sub_judgement_table"].assert_called_once()

    def test_missing_or_partial_fallback_is_not_used(self):
        for fallback in (None, cropper.Box(50, 50, 450, 100)):
            result, _ = self.run_crop(fallback)
            self.assertNotIn("sub_judgement_table", result["fields"])

    def test_model_success_and_main_only_skip_fallback(self):
        result, mocks = self.run_crop(None, model=True)
        self.assertEqual(result["fields"]["sub_judgement_table"]["detector"], "cropper_pt_pose_warp")
        mocks["detect_sub_judgement_table"].assert_not_called()
        result, mocks = self.run_crop(None, size=(1000, 1000))
        self.assertNotIn("sub_judgement_table", result["fields"])
        mocks["detect_sub_judgement_table"].assert_not_called()


if __name__ == "__main__":
    unittest.main()
