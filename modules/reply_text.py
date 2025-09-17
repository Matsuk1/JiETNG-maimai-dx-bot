from linebot.models import TextSendMessage

no_record = TextSendMessage(text="❌ maimai のレコードが保存されていません！\nSEGA ACCOUNT を連携し、「maimai update」を行った上でご利用ください。")
no_segaid = TextSendMessage(text="❌ SEGA ACCOUNT が連携されていません！\nSEGA ACCOUNT を連携し、「maimai update」を行った上でご利用ください。")
