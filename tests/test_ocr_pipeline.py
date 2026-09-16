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
