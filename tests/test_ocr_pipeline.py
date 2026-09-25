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
    def test_incomplete_full_table_ocr_retries_only_missing_rows(self):
        from modules.score_recognition import ocr
        from unittest.mock import Mock
        image=Image.new('RGB',(300,100),'blue')
        row=dict(critical_perfect=1,perfect=0,great=0,good=0,miss=0)
        metadata={'screen':dict(left=0,top=0,right=300,bottom=100),'fields':{
            'main_title':dict(image=image,left=0,top=0,right=300,bottom=20),
            'sub_judgement_table':dict(image=image,left=0,top=20,right=300,bottom=100,layout_hint='dxnet')}}
        engine=Mock()
        engine.read.return_value=[{'text':'Test song','score':0.99}]
        def recognize_full_table(*args, **kwargs):
            kwargs['confidence_out']['tap'] = dict.fromkeys(ocr.JUDGEMENT_VALUE_NAMES, 0.99)
            return {'tap': dict(row)}
        with tempfile.TemporaryDirectory() as directory, patch.object(ocr,'crop_result_fields_in_memory',return_value=metadata), patch.object(ocr,'recognize_judgement_from_table',side_effect=recognize_full_table), patch.object(ocr,'recognize_judgement_by_columns',return_value={name:dict(row) for name in ('hold','slide','touch','break')}) as fallback:
            path=Path(directory)/'source.png'; image.save(path)
            memory=ocr.process_image_data(image,ocr.OCR_FIELDS,engine)
            debug=ocr.process_image(path,Path(directory)/'debug',ocr.OCR_FIELDS,engine)
            self.assertEqual(memory['parsed'],debug['parsed'])
            self.assertEqual(fallback.call_count,2)
            for call in fallback.call_args_list:
                self.assertEqual(call.kwargs['target_rows'],('hold','slide','touch','break'))
            self.assertTrue(Path(debug['ocr_fields']['main_title']['prepared']).exists())
            self.assertTrue(Path(debug['ocr_fields']['sub_judgement_table']['crop']).exists())

    def test_full_table_ocr_maps_boxes_to_known_grid(self):
        from unittest.mock import Mock
        from modules.score_recognition import ocr

        engine = Mock()
        engine.read.return_value = [
            {'text': '123', 'score': 0.98, 'box': [600, 750, 900, 870]},
            {'text': '4', 'score': 0.97, 'box': [1140, 750, 1350, 870]},
            {'text': '9', 'score': 0.40, 'box': [1140, 750, 1350, 870]},
            {'text': '2', 'score': 0.96, 'box': [2460, 2700, 2700, 2820]},
            {'text': 'TAP', 'score': 0.99, 'box': [0, 750, 300, 870]},
        ]
        confidences = {}
        result = ocr.recognize_judgement_from_table(
            Image.new('RGB', (1000, 1000), 'white'),
            engine,
            layout_hint='dxnet',
            confidence_out=confidences,
        )
        self.assertEqual(result, {
            'tap': {'critical_perfect': 123, 'perfect': 4},
            'break': {'miss': 2},
        })
        self.assertEqual(confidences['tap']['perfect'], 0.97)

    def test_complete_full_table_ocr_skips_column_and_cell_retry(self):
        from unittest.mock import Mock
        from modules.score_recognition import ocr

        image = Image.new('RGB', (300, 100), 'blue')
        row = dict(critical_perfect=1, perfect=0, great=0, good=0, miss=0)
        metadata = {'screen': dict(left=0, top=0, right=300, bottom=100), 'fields': {
            'sub_judgement_table': dict(image=image, layout_hint='dxnet'),
        }}
        engine = Mock()
        full_table = {name: dict(row) for name in ocr.JUDGEMENT_ROW_NAMES}
        def recognize_full_table(*args, **kwargs):
            kwargs['confidence_out'].update({
                name: dict.fromkeys(ocr.JUDGEMENT_VALUE_NAMES, 0.99)
                for name in ocr.JUDGEMENT_ROW_NAMES
            })
            return full_table
        with patch.object(ocr, 'crop_result_fields_in_memory', return_value=metadata), \
             patch.object(ocr, 'recognize_judgement_from_table', side_effect=recognize_full_table), \
             patch.object(ocr, 'recognize_judgement_by_columns') as retry:
            result = ocr.process_image_data(
                image,
                ('sub_judgement_table',),
                engine,
            )
        retry.assert_not_called()
        self.assertEqual(
            result['parsed']['sub_judgement'],
            full_table,
        )

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
