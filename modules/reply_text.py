from linebot.models import TextSendMessage

no_record = TextSendMessage(text="maimai レコードはまだアップデートされてないね？\n「maimai update」のお試しを！")
no_segaid = TextSendMessage(text="SEGA アカウントはまだ連携されてないでしょ？\n「sega bind」を試してね！")
