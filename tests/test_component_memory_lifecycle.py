"""Idle cleanup must preserve active work and allow lazy recreation."""
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
            self.assertFalse(ocr.cleanup_table_model_memory())
            clock.return_value = 400
            with ocr._TABLE_MODEL_LOCK:
                self.assertFalse(ocr.cleanup_table_model_memory())
            self.assertTrue(ocr.cleanup_table_model_memory())
            stop.assert_called_once()
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
            self.assertIsNone(cropper._CROPPER_MODEL)
            self.assertIsNone(cropper._MAIN_SCREEN_MODEL)
            self.assertFalse(cropper.cleanup_cropper_memory())

    def test_main_ocr_idle_release_and_lazy_reload(self):
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
            self.assertTrue(recognizer.cleanup_score_recognizer_memory())
            self.assertIsNone(recognizer._ENGINE)
            self.assertEqual(recognizer._ENGINE_REQUEST_COUNT, 0)
            factory = Mock()
            with patch.object(recognizer, '_load_ocr_module', return_value=((), factory, None)):
                self.assertIs(recognizer._engine(), factory.return_value)
                factory.assert_called_once_with(lang='japan')


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
            self.assertEqual(jobs.get.call_args.kwargs, {'timeout': 300})
