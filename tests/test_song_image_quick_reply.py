from unittest.mock import patch

from modules.messages.service import generate_song_image_message


def test_song_images_keep_localized_single_use_actions():
    for mode, commands in [('info', ['calc-song abc123', 'search-record abc123']),
                           ('record', ['search-song abc123'])]:
        with patch('modules.messages.service.image_button_data', side_effect=lambda value: 'signed:' + value) as sign, \
             patch('modules.messages.service.get_multilingual_text', return_value='Localized action'):
            message = generate_song_image_message('abc123', 'https://example.com/full.png',
                                                  'https://example.com/preview.png', 'user', mode)
        payload = message.to_dict()
        assert payload['type'] == 'image'
        assert payload['originalContentUrl'] == 'https://example.com/full.png'
        assert payload['previewImageUrl'] == 'https://example.com/preview.png'
        actions = [item['action'] for item in payload['quickReply']['items']]
        assert [action['data'] for action in actions] == ['signed:' + c for c in commands]
        assert all(a['type'] == 'postback' and a['label'] == 'Localized action' for a in actions)
        assert [call.args[0] for call in sign.call_args_list] == commands


def test_quick_reply_image_stays_after_appended_notice():
    from linebot.v3.messaging import Configuration, TextMessage
    from modules import line_messenger as messenger
    with patch('modules.messages.service.image_button_data', return_value='signed'), \
         patch('modules.messages.service.get_multilingual_text', return_value='Info'):
        image = generate_song_image_message('abc123', 'https://example.com/full.png', mode='record')
    notice = TextMessage(text='Notice')
    with patch.object(messenger, 'user_exists', return_value=False), \
         patch.object(messenger, 'get_latest_published_notice', return_value={'id': 1}), \
         patch.object(messenger, 'has_user_read_notice', return_value=False), \
         patch.object(messenger, 'generate_notice_flex', return_value=notice), \
         patch.object(messenger, 'record_notice_read'), \
         patch.object(messenger, 'ApiClient'), \
         patch.object(messenger, 'MessagingApi') as api:
        messenger.smart_reply('user', 'token', image, Configuration())
    sent = api.return_value.reply_message.call_args.args[0].messages
    assert [m.type for m in sent] == ['text', 'image']
    assert sent[-1].quick_reply.items[0].action.data == 'signed'
