import subprocess
import sys
import unittest

class ImportBoundaryTests(unittest.TestCase):
    def test_handlers_import_without_configuration_or_model_startup(self):
        code='''
import sys
from modules.api.score_api import create_score_api
from modules.api.admin_users import create_edit_user_handler
from modules.user_db import update_user_fields
from modules.score_recognition.results import expand_score_recognition_calc_variants
assert 'modules.config_loader' not in sys.modules
assert 'paddleocr' not in sys.modules
assert 'main' not in sys.modules
'''
        subprocess.run([sys.executable,'-c',code],check=True,capture_output=True,timeout=10)
