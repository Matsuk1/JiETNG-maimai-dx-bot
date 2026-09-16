from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from modules.score_recognition import cropper

class CropAdapterTests(unittest.TestCase):
    def test_debug_crops_equal_production_pixels(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source.png'
            Image.new('RGB',(640,640),(60,70,80)).save(path)
            with patch.object(cropper,'_load_main_screen_model',return_value=None), patch.object(cropper,'_load_cropper_model',return_value=None), patch.object(cropper,'detect_result_screen',return_value=cropper.Box(0,0,640,640)):
                with Image.open(path) as source:
                    expected=cropper.crop_result_fields_in_memory(source)
                actual=cropper.crop_result_fields(path,Path(directory)/'debug')
            self.assertEqual(actual['fields'].keys(),expected['fields'].keys())
            for name,field in actual['fields'].items():
                with Image.open(field['path']) as image:
                    self.assertEqual(image.tobytes(),expected['fields'][name]['image'].tobytes())
                self.assertEqual(field['detector'],expected['fields'][name]['detector'])
            self.assertTrue((Path(directory)/'debug/source/debug_overlay.png').exists())

class OcrAdapterTests(unittest.TestCase):
    def test_partial_table_fallback_matches_in_debug_and_memory(self):
        from modules.score_recognition import ocr
        from unittest.mock import Mock
        image=Image.new('RGB',(300,100),'blue')
        row=dict(critical_perfect=1,perfect=0,great=0,good=0,miss=0)
        metadata={'screen':dict(left=0,top=0,right=300,bottom=100),'fields':{
            'main_title':dict(image=image,left=0,top=0,right=300,bottom=20),
            'sub_judgement_table':dict(image=image,left=0,top=20,right=300,bottom=100,layout_hint='dxnet')}}
        def partial(image,partial_out):
            partial_out['tap']=dict(row)
            return None
        engine=Mock()
        engine.read.return_value=[{'text':'Test song','score':0.99}]
        with tempfile.TemporaryDirectory() as directory, patch.object(ocr,'crop_result_fields_in_memory',return_value=metadata), patch.object(ocr,'recognize_judgement_with_table_model',side_effect=partial), patch.object(ocr,'recognize_judgement_by_columns',return_value={name:dict(row) for name in ('hold','slide','touch','break')}) as fallback:
            path=Path(directory)/'source.png'; image.save(path)
            memory=ocr.process_image_data(image,ocr.OCR_FIELDS,engine)
            debug=ocr.process_image(path,Path(directory)/'debug',ocr.OCR_FIELDS,engine)
            self.assertEqual(memory['parsed'],debug['parsed'])
            self.assertEqual(fallback.call_count,2)
            for call in fallback.call_args_list:
                self.assertEqual(call.kwargs['target_rows'],('hold','slide','touch','break'))
            self.assertTrue(Path(debug['ocr_fields']['main_title']['prepared']).exists())
            self.assertTrue(Path(debug['ocr_fields']['sub_judgement_table']['crop']).exists())

class EngineFailureTests(unittest.TestCase):
    def test_detector_limit_preserves_recognition_input_and_coordinates(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import Mock
        from modules.score_recognition.ocr import PaddleOcrEngine
        factory = Mock()
        box = [100, 200, 600, 800]
        factory.return_value.predict.return_value = [{
            'rec_texts': ['304'], 'rec_scores': [0.99], 'rec_boxes': [box],
        }]
        with patch.dict(sys.modules, paddleocr=SimpleNamespace(PaddleOCR=factory)), patch.dict('os.environ', JIETNG_OCR_DET_MAX_SIDE='1280'):
            engine = PaddleOcrEngine()
        self.assertEqual(factory.call_args.kwargs['text_det_limit_side_len'], 1280)
        self.assertEqual(factory.call_args.kwargs['text_det_limit_type'], 'max')
        items = engine.read(Image.new('RGB', (1600, 2400)))
        self.assertEqual(engine.ocr.predict.call_args.args[0].shape, (2400, 1600, 3))
        self.assertEqual(items[0]['box'], box)

    def test_inference_failure_is_not_retried_via_legacy_api(self):
        from modules.score_recognition.ocr import PaddleOcrEngine
        from unittest.mock import Mock
        engine=PaddleOcrEngine.__new__(PaddleOcrEngine)
        engine.ocr=Mock()
        engine.ocr.predict.side_effect=RuntimeError('model failed')
        with self.assertRaisesRegex(RuntimeError,'model failed'):
            engine.read(Image.new('RGB',(100,30)))
        engine.ocr.predict.assert_called_once()
        engine.ocr.ocr.assert_not_called()


def test_failed_crop_does_not_initialize_ocr_engine():
    import pytest
    from unittest.mock import Mock
    from modules.score_recognition import ocr

    engine_factory = Mock()
    with Image.new('RGB', (100, 100)) as source, patch.object(
        ocr, 'crop_result_fields_in_memory', side_effect=ValueError('four corners missing')
    ):
        with pytest.raises(ValueError, match='four corners missing'):
            ocr.process_image_data(source, ocr.OCR_FIELDS, None, engine_factory=engine_factory)
    engine_factory.assert_not_called()

class CpuRuntimeTests(unittest.TestCase):
    def test_engine_passes_cpu_configuration(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import Mock
        from modules.score_recognition import ocr
        factory = Mock()
        with patch.dict(sys.modules, paddleocr=SimpleNamespace(PaddleOCR=factory)), \
             patch.object(ocr, 'OCR_CPU_THREADS', 8), \
             patch.object(ocr, 'OCR_ENABLE_MKLDNN', True):
            ocr.PaddleOcrEngine()
        self.assertEqual(factory.call_args.kwargs['cpu_threads'], 8)
        self.assertTrue(factory.call_args.kwargs['enable_mkldnn'])

    def test_import_configures_backend_environment_before_paddle(self):
        import os
        import subprocess
        import sys
        env = dict(os.environ, JIETNG_OCR_CPU_THREADS='8', JIETNG_OCR_ENABLE_MKLDNN='1',
                   FLAGS_use_onednn='0', FLAGS_use_mkldnn='0')
        result = subprocess.run([sys.executable, '-c', '''
import os
from modules.score_recognition import ocr
assert ocr.OCR_CPU_THREADS == 8
assert ocr.OCR_ENABLE_MKLDNN
assert os.environ['FLAGS_use_onednn'] == '1'
assert os.environ['FLAGS_use_mkldnn'] == '1'
assert os.environ['PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT'] == '1'
'''], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_benchmark_never_supplies_images_to_codex_validation(self):
        import argparse
        import json
        from scripts.benchmark_score_ocr import run_worker
        from modules.score_recognition import recognizer, ocr
        with tempfile.TemporaryDirectory() as directory:
            photo = Path(directory) / 'photo.jpg'
            photo.write_bytes(b'test-original')
            output = Path(directory) / 'result.json'
            result = {'parsed': {'title': 'test'}, 'timing': {'crop': 0.1}}
            with patch.object(recognizer, 'recognize_score_image_bytes', return_value=result) as recognize, \
                 patch.object(recognizer, 'validate_recognized_judgement', return_value=result) as validate:
                run_worker(argparse.Namespace(images=[photo], runs=2, version='jp', output=output))
            self.assertEqual(recognize.call_count, 2)
            self.assertEqual(recognize.call_args.kwargs, {'fields': ocr.OCR_FIELDS})
            self.assertEqual(validate.call_args.kwargs, {'ver': 'jp'})
            self.assertEqual(len(json.loads(output.read_text())), 2)

class TableWorkerLifetimeTests(unittest.TestCase):
    def test_reuse_and_memory_protection_preserve_results(self):
        import json
        from contextlib import ExitStack
        from types import SimpleNamespace
        from unittest.mock import Mock
        from modules.score_recognition import ocr

        for rss, available, count, should_stop in (
            (2172, 1024, 0, False),  # Normal measured production footprint.
            (2600, 1024, 0, True),  # Worker exceeds its own limit.
            (2172, 400, 0, True),   # Host needs memory even below worker limit.
            (2172, 1024, 49, True), # Periodic recycling remains in place.
        ):
            with self.subTest(rss=rss, available=available, count=count), ExitStack() as stack:
                worker = Mock(pid=123)
                worker.poll.return_value = None
                result = {name: {'critical_perfect': 1} for name in ocr.JUDGEMENT_ROW_NAMES}
                stack.enter_context(patch.object(ocr, '_TABLE_MODEL_PROCESS', worker))
                stack.enter_context(patch.object(ocr, '_TABLE_MODEL_REQUEST_COUNT', count))
                stack.enter_context(patch.object(ocr, 'TABLE_MODEL_MAX_RSS_MB', 2560))
                stack.enter_context(patch.object(ocr, 'TABLE_MODEL_MIN_AVAILABLE_MB', 512))
                stack.enter_context(patch.object(ocr, 'TABLE_MODEL_MAX_REQUESTS', 50))
                stack.enter_context(patch.object(ocr, '_start_table_model_process', return_value=worker))
                stop = stack.enter_context(patch.object(ocr, '_stop_table_model_process'))
                stack.enter_context(patch.object(ocr.psutil, 'Process', return_value=Mock(
                    memory_info=Mock(return_value=SimpleNamespace(rss=rss * 1024**2)))))
                stack.enter_context(patch.object(ocr.psutil, 'virtual_memory', return_value=SimpleNamespace(
                    available=available * 1024**2)))
                def response(*args):
                    request = json.loads(worker.stdin.write.call_args.args[0])
                    return ocr.TABLE_MODEL_RESULT_MARKER + json.dumps({'id': request['id'], 'result': result})
                stack.enter_context(patch.object(ocr, '_read_table_model_line', side_effect=response))
                image = Image.new('RGB', (10, 10))
                self.assertEqual(ocr.recognize_judgement_with_table_model(image), result)
                self.assertEqual(stop.called, should_stop)
                if not should_stop:
                    self.assertEqual(ocr.recognize_judgement_with_table_model(image), result)
                    self.assertEqual(ocr._TABLE_MODEL_REQUEST_COUNT, 2)
                    stop.assert_not_called()
