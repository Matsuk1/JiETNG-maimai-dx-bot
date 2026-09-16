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
from modules.commands.command_parsers import parse_fix_record_command
from modules.score_recognition.results import expand_score_recognition_calc_variants
assert 'modules.config_loader' not in sys.modules
assert 'paddleocr' not in sys.modules
assert 'main' not in sys.modules
'''
        subprocess.run([sys.executable,'-c',code],check=True,capture_output=True,timeout=10)


def test_score_message_renders_without_service_dependencies():
    code = '''
import sys
from modules.messages.scores import generate_score_recognition_flex
message = generate_score_recognition_flex({})
assert message.contents.to_dict()['type'] == 'bubble'
from modules.commands.command_help import detect_command_help_key
assert detect_command_help_key('bpm') == 'search_by_bpm'
for module in ('modules.messages.service', 'modules.config_loader', 'modules.user_db',
               'modules.tip_ad_manager', 'modules.images.renderer', 'paddleocr', 'main'):
    assert module not in sys.modules, module
'''
    subprocess.run([sys.executable, '-c', code], check=True, capture_output=True, timeout=10)


def test_account_and_status_cards_use_shared_layout():
    from modules.messages.service import generate_account_action_flex, generate_status_flex
    for kind in ('bind', 'rebind', 'unbind', 'settings'):
        message = generate_account_action_flex(kind, 'https://example.test/action')
        bubble = message.contents.to_dict()
        assert bubble['type'] == 'bubble'
        assert bubble['footer']['contents'][0]['action']['uri'] == 'https://example.test/action'
    for tone in ('info', 'success', 'error'):
        message = generate_status_flex('Status', 'Body', tone=tone)
        assert message.contents.to_dict()['body']['contents'][0]['contents'][0]['text'] == 'Status'
