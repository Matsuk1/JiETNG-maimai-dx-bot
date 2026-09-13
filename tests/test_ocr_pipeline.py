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
