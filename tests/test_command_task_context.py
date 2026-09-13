import unittest
from types import SimpleNamespace
from modules.task_runtime import task_context
from modules.commands.command_router import CommandContext

class CommandTaskContextTests(unittest.TestCase):
    def test_context_keeps_sender_for_error_reporting(self):
        ctx=CommandContext(event=None,text='song record',user_id='sender',source_type='group',reply_token='reply',mentioned_user_id='target',has_other_mention=True,id_use='target',mai_ver='jp',mai_ver_use='intl')
        task=task_context((ctx,))
        self.assertEqual((task.user_id,task.reply_token,task.source_type),('sender','reply','group'))
    def test_legacy_event_still_supported(self):
        event=SimpleNamespace(source=SimpleNamespace(user_id='sender',type='user'),reply_token='reply')
        self.assertEqual(task_context((event,)).user_id,'sender')
