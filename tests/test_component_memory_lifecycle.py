"""Idle cleanup must preserve active work and immediately rebuild loaded components."""
import threading
import unittest
from concurrent.futures import Future
from contextlib import ExitStack
from queue import Empty
from unittest.mock import Mock, patch


class TableIdleTests(unittest.TestCase):
    def test_idle_threshold_disabled_and_busy_worker(self):
        from modules.score_recognition import ocr
        with ExitStack() as stack:
            stack.enter_context(patch.object(ocr, '_TABLE_MODEL_PROCESS', Mock()))
            stack.enter_context(patch.object(ocr, '_TABLE_MODEL_LAST_USED', 100))
            stack.enter_context(patch.object(ocr, 'TABLE_MODEL_IDLE_SECONDS', 300))
            clock = stack.enter_context(patch.object(ocr.time, 'monotonic', return_value=399))
            stop = stack.enter_context(patch.object(ocr, '_stop_table_model_process'))
            start = stack.enter_context(patch.object(ocr, '_start_table_model_process'))
            self.assertFalse(ocr.cleanup_table_model_memory())
            clock.return_value = 400
            with ocr._TABLE_MODEL_LOCK:
                self.assertFalse(ocr.cleanup_table_model_memory())
            self.assertTrue(ocr.cleanup_table_model_memory())
            stop.assert_called_once()
            start.assert_called_once()
            self.assertEqual(ocr._TABLE_MODEL_LAST_USED, 400)
            self.assertFalse(ocr.cleanup_table_model_memory())
            with patch.object(ocr, 'TABLE_MODEL_IDLE_SECONDS', 0):
                self.assertFalse(ocr.cleanup_table_model_memory())

    def test_stop_reaps_worker_and_closes_pipes(self):
        import subprocess
        from modules.score_recognition import ocr
        worker = Mock()
        worker.poll.return_value = None
        worker.wait.side_effect = [subprocess.TimeoutExpired('worker', 5), 0]
        with patch.object(ocr, '_TABLE_MODEL_PROCESS', worker), \
             patch.object(ocr, '_TABLE_MODEL_REQUEST_COUNT', 10):
            ocr._stop_table_model_process()
            self.assertIsNone(ocr._TABLE_MODEL_PROCESS)
            self.assertEqual(ocr._TABLE_MODEL_REQUEST_COUNT, 0)
        worker.terminate.assert_called_once()
        worker.kill.assert_called_once()
        worker.stdin.close.assert_called_once()
        worker.stdout.close.assert_called_once()

    def test_warmup_updates_idle_deadline(self):
        from modules.score_recognition import ocr
        with patch.object(ocr, '_start_table_model_process'), \
             patch.object(ocr, '_TABLE_MODEL_LAST_USED', 0), \
             patch.object(ocr.time, 'monotonic', return_value=123):
            ocr.warm_table_model()
            self.assertEqual(ocr._TABLE_MODEL_LAST_USED, 123)


class ModelIdleTests(unittest.TestCase):
    def test_yolo_idle_release_and_busy_protection(self):
        from modules.score_recognition import cropper
        with ExitStack() as stack:
            first, second = object(), object()
            rebuilt_first, rebuilt_second = Mock(), Mock()
            def reload_first():
                cropper._CROPPER_MODEL = rebuilt_first
                return rebuilt_first
            def reload_second():
                cropper._MAIN_SCREEN_MODEL = rebuilt_second
                return rebuilt_second
            stack.enter_context(patch.object(cropper, '_load_cropper_model', side_effect=reload_first))
            stack.enter_context(patch.object(cropper, '_load_main_screen_model', side_effect=reload_second))
            stack.enter_context(patch.object(cropper, '_CROPPER_MODEL', first))
            stack.enter_context(patch.object(cropper, '_MAIN_SCREEN_MODEL', second))
            stack.enter_context(patch.object(cropper, '_MODELS_LAST_USED', 100))
            stack.enter_context(patch.object(cropper, 'CROPPER_IDLE_SECONDS', 300))
            clock = stack.enter_context(patch.object(cropper.time, 'monotonic', return_value=399))
            stack.enter_context(patch.object(cropper.gc, 'collect'))
            self.assertFalse(cropper.cleanup_cropper_memory())
            clock.return_value = 400
            with cropper._MODEL_LOCK:
                self.assertFalse(cropper.cleanup_cropper_memory())
            self.assertIs(cropper._CROPPER_MODEL, first)
            self.assertTrue(cropper.cleanup_cropper_memory())
            self.assertIs(cropper._CROPPER_MODEL, rebuilt_first)
            self.assertIs(cropper._MAIN_SCREEN_MODEL, rebuilt_second)
            self.assertFalse(cropper.cleanup_cropper_memory())

    def test_main_ocr_idle_release_and_immediate_reload(self):
        from modules.score_recognition import recognizer
        with ExitStack() as stack:
            stack.enter_context(patch.object(recognizer, '_ENGINE', object()))
            stack.enter_context(patch.object(recognizer, '_ENGINE_REQUEST_COUNT', 3))
            stack.enter_context(patch.object(recognizer, '_OCR_LAST_USED', 100))
            stack.enter_context(patch.object(recognizer, 'OCR_IDLE_SECONDS', 300))
            stack.enter_context(patch.object(recognizer, '_process_rss_mb', return_value=100))
            clock = stack.enter_context(patch.object(recognizer.time, 'monotonic', return_value=399))
            # Don't touch other components' live state in this unit test.
            stack.enter_context(patch.object(recognizer.sys, 'modules', {}))
            stack.enter_context(patch.object(recognizer.gc, 'collect', return_value=0))
            self.assertFalse(recognizer.cleanup_score_recognizer_memory())
            clock.return_value = 400
            with recognizer._OCR_LOCK:
                self.assertFalse(recognizer.cleanup_score_recognizer_memory())
            factory = Mock()
            with patch.object(recognizer, '_load_ocr_module', return_value=((), factory, None)):
                self.assertTrue(recognizer.cleanup_score_recognizer_memory())
                self.assertIs(recognizer._ENGINE, factory.return_value)
                self.assertEqual(recognizer._ENGINE_REQUEST_COUNT, 0)
                factory.assert_called_once_with(lang='japan')
                self.assertFalse(recognizer.cleanup_score_recognizer_memory())


class RendererIdleTests(unittest.TestCase):
    def test_idle_close_runs_on_worker_and_next_job_still_completes(self):
        from modules.images import renderer
        first, second = Future(), Future()
        jobs = Mock()
        jobs.get.side_effect = [(first, 'first', 10, 10), Empty(),
                                (second, 'second', 10, 10), None]
        calls = []
        with patch.object(renderer, '_queue', jobs), \
             patch.object(renderer, '_browser', object()), \
             patch.object(renderer, 'RENDERER_IDLE_SECONDS', 300), \
             patch.object(renderer, '_screenshot', side_effect=[b'one', b'two']), \
             patch.object(renderer, '_close_browser', side_effect=lambda: calls.append(threading.get_ident())), \
             patch.object(renderer, '_ensure_page') as rebuild, \
             patch.object(renderer, '_file_uri') as cache, \
             patch.object(renderer.gc, 'collect'):
            worker = threading.Thread(target=renderer._work)
            worker.start()
            worker.join(timeout=2)
            self.assertFalse(worker.is_alive())
            self.assertEqual(first.result(timeout=1), b'one')
            self.assertEqual(second.result(timeout=1), b'two')
            self.assertEqual(calls, [worker.ident, worker.ident])
            cache.cache_clear.assert_called_once()
            rebuild.assert_called_once_with(800, 800)
            self.assertEqual(jobs.get.call_args.kwargs, {'timeout': 300})


class StartupWarmupTests(unittest.TestCase):
    def test_yolo_warmup_initializes_both_predictors(self):
        from modules.score_recognition import cropper
        first, second = Mock(), Mock()
        with patch.object(cropper, '_load_cropper_model', return_value=first), \
             patch.object(cropper, '_load_main_screen_model', return_value=second), \
             patch.object(cropper, '_MODELS_LAST_USED', 0), \
             patch.object(cropper.time, 'monotonic', return_value=123):
            cropper.warm_cropper_models()
            for model in (first, second):
                model.predict.assert_called_once()
                self.assertEqual(model.predict.call_args.args[0].shape, (640, 640, 3))
            self.assertEqual(cropper._MODELS_LAST_USED, 123)

    def test_failed_yolo_warmup_still_attempts_other_model_and_allows_retry(self):
        from modules.score_recognition import cropper
        second = Mock()
        with patch.object(cropper, '_load_cropper_model', return_value=None), \
             patch.object(cropper, '_load_main_screen_model', return_value=second), \
             patch.object(cropper, '_CROPPER_MODEL_UNAVAILABLE', True), \
             patch.object(cropper, '_MAIN_SCREEN_MODEL_UNAVAILABLE', False):
            with self.assertRaises(RuntimeError):
                cropper.warm_cropper_models()
            second.predict.assert_called_once()
            self.assertFalse(cropper._CROPPER_MODEL_UNAVAILABLE)

    def test_renderer_warmup_uses_normal_worker_and_closes_result(self):
        from modules.images import renderer
        from PIL import Image
        image = Image.new('RGBA', (1, 1))
        with patch.object(renderer, 'render_html', return_value=image) as render, \
             patch.object(image, 'close') as close:
            renderer.warm_renderer()
            render.assert_called_once_with('', 1, 1)
            close.assert_called_once()

    def test_table_rebuild_failure_releases_failed_worker(self):
        from modules.score_recognition import ocr
        with patch.object(ocr, '_TABLE_MODEL_PROCESS', Mock()), \
             patch.object(ocr, '_TABLE_MODEL_LAST_USED', 0), \
             patch.object(ocr, 'TABLE_MODEL_IDLE_SECONDS', 300), \
             patch.object(ocr.time, 'monotonic', return_value=400), \
             patch.object(ocr, '_stop_table_model_process') as stop, \
             patch.object(ocr, '_start_table_model_process', side_effect=RuntimeError('startup failed')):
            self.assertTrue(ocr.cleanup_table_model_memory())
            self.assertEqual(stop.call_count, 2)
            self.assertEqual(ocr._TABLE_MODEL_LAST_USED, 400)
            self.assertTrue(ocr._TABLE_MODEL_LOCK.acquire(blocking=False))
            ocr._TABLE_MODEL_LOCK.release()
