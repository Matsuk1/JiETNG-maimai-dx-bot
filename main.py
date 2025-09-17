import certifi
import gc
import ast
import random
import socket
import requests
import json
import re
import sys
import subprocess
import time
import traceback
import os
import urllib.parse
import math
import difflib
import numpy
import base64
import warnings
import threading
import queue

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

from datetime import timedelta

from flask import Flask, request, abort, render_template

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage, LocationMessage, TemplateSendMessage, ButtonsTemplate, MessageAction, URIAction
from linebot import __version__ as linebot_version

sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
from song_info_generate import *
from record_picture_generate import *
from user_console import *
from token_console import *
from notice_console import *
from maimai_console import *
from dxdata_console import *
from record_console import *
from config_loader import *
from create_button_list import *
from reply_text import *
from note_score import *
from fakemai_console import get_fakemai_records
from img_upload import smart_upload
from img_console import combine_with_rounded_background, wrap_in_rounded_background

if linebot_version.startswith("3."):
    warnings.filterwarnings("ignore", category=DeprecationWarning)

divider = "-" * 33

app = Flask(__name__)

# 主任务队列（比如消息处理）
task_queue = queue.Queue(maxsize=10)
concurrency_limit = threading.Semaphore(3)

# Web任务队列（比如网页绑定、图像上传等）
webtask_queue = queue.Queue(maxsize=10)
webtask_concurrency_limit = threading.Semaphore(1)

# 通用任务处理函数
def run_task_with_limit(func, args, sem, q):
    with sem:
        task_done = threading.Event()

        def target():
            try:
                func(*args)
            except Exception as e:
                print(f"[Task Error] {e}")
            finally:
                task_done.set()
                q.task_done()

        thread = threading.Thread(target=target)
        thread.start()

        timer = threading.Timer(120, cancel_if_timeout, args=(task_done,))
        timer.start()

        thread.join()
        timer.cancel()

# 主任务 worker
def task_worker():
    while True:
        try:
            func, args = task_queue.get()
            threading.Thread(
                target=run_task_with_limit,
                args=(func, args, concurrency_limit, task_queue)
            ).start()
        except Exception as e:
            print(f"[Worker Error] {e}")

# Web任务 worker
def webtask_worker():
    while True:
        try:
            func, args = webtask_queue.get()
            threading.Thread(
                target=run_task_with_limit,
                args=(func, args, webtask_concurrency_limit, webtask_queue)
            ).start()
        except Exception as e:
            print(f"[Web Worker Error] {e}")

# 启动 worker
threading.Thread(target=task_worker, daemon=True).start()
threading.Thread(target=webtask_worker, daemon=True).start()

# 超时处理函数
def cancel_if_timeout(task_done):
    if not task_done.is_set():
        print("[Timeout] 任务超时")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/linebot/", methods=['POST'])
def linebot_reply():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    try:
        json_data = json.loads(body)
        print(f"\n\n{json.dumps(json_data, indent=4, ensure_ascii=False)}\n\n")
        destination = json_data.get("destination")
        request.destination = destination
        handler.handle(body, signature)

    except json.JSONDecodeError:
        app.logger.error("JSON 解析失败")
        abort(400)

    except InvalidSignatureError:
        app.logger.error("InvalidSignatureError: 无效的 LINE 签名")
        abort(400)

    return 'OK', 200

@app.route("/linebot/sega_bind", methods=["GET", "POST"])
def website_segaid_bind():
    token = request.args.get("token")
    if not token:
        return render_template("error.html", message="トークン未申請"), 400

    try:
        user_id = get_user_id_from_token(token)
    except Exception as e:
        return render_template("error.html", message="トークン無効"), 400

    if request.method == "POST":
        segaid = request.form.get("segaid")
        password = request.form.get("password")
        if not segaid or not password:
            return render_template("error.html", message="すべての項目を入力してください"), 400

        if process_sega_credentials(user_id, segaid, password):
            return render_template("success.html")
        else:
            return render_template("error.html", message="SEGA ID と パスワード をもう一度確認してください"), 500

    return render_template("bind_form.html")

def process_sega_credentials(user_id, segaid, password):
    if not user_id.startswith(("QQ", "U")):
        return False

    if fetch_dom(login_to_maimai(segaid, password), "https://maimaidx.jp/maimai-mobile/home/") is None:
        return False

    user_bind_sega_id(user_id, segaid)
    user_bind_sega_pwd(user_id, password)
    return True

def bind_fake_token(user_id, fake_token):
    read_user()

    if user_id not in users:
        add_user(user_id)

    users[user_id]["fake_token"] = fake_token
    write_user()

def get_fake_token(user_id):
    read_user()

    if user_id not in users:
        add_user(user_id)

    if "fake_token" not in users[user_id]:
        return ""

    return users[user_id]["fake_token"]

def user_bind_sega_id(user_id, sega_id):
    read_user()

    if user_id not in users :
        add_user(user_id)

    users[user_id]['sega_id'] = sega_id

    write_user()
    return "SEGA ID バインド完了！"

def user_bind_sega_pwd(user_id, sega_pwd):
    read_user()

    if user_id not in users :
        add_user(user_id)

    users[user_id]['sega_pwd'] = sega_pwd

    write_user()
    return "SEGA PASSWORD バインド完了！"

def get_user(user_id):
    read_user()

    result = f"USER_ID: {user_id}\n"

    if user_id in users :
        if "sega_id" in users[user_id] :
            result += f"SEGA_ID: {users[user_id]['sega_id']}\n"
        else :
            result += "SEGA_ID: 未連携\n"

        if "sega_pwd" in users[user_id] :
            result += f"PASSWORD: 連携完了"
        else :
            result += "PASSWORD: 未連携"

    else :
        result += "USER_INFO: 未連携"

    return result

def fakemai_update(fake_id, fake_token):
    record = get_fakemai_records(fake_token)

    if not record :
        return False, "❌ fakemai レコードアップデート中エラーが発生しました！"

    write_record(fake_id, record, replace=False)

    return True, "✅ fakemaiレコードアップデート完了！"

def async_maimai_update_task(user_id, reply_token):
    update_success, reply_msg = maimai_update(user_id)
    smart_reply(user_id, reply_token, reply_msg)

def maimai_update(user_id):
    messages = []
    status = True

    read_user()

    if user_id not in users :
        return no_segaid

    elif 'sega_id' not in users[user_id] or 'sega_pwd' not in users[user_id] :
        return no_segaid

    sega_id = users[user_id]['sega_id']
    sega_pwd = users[user_id]['sega_pwd']

    user_session = login_to_maimai(sega_id, sega_pwd)
    user_info = get_maimai_info(user_session)
    maimai_records = get_maimai_records(user_session)
    recent_records = get_recent_records(user_session)

    if user_info:
        users[user_id]['personal_info'] = user_info
        write_user()
    else:
        status = False

    if maimai_records:
        write_record(user_id, maimai_records)
    else:
        status = False

    if recent_records:
        write_record(user_id, recent_records, recent=True)
    else:
        status = False

    if status:
        messages.append(TextSendMessage(text="✅ maimai レコードアップデート完了！"))
    else:
        messages.append(TextSendMessage(text="❌ maimai レコードアップデート中エラーが発生しました！"))
    return status, messages

def get_rc(level):
    result = f"LEVEL: {level}\n"
    result += divider
    last_ra = 0

    for score in numpy.arange(97.0000, 100.5001, 0.0001) :
        ra = get_single_ra(level, score)
        if not ra == last_ra :
            result += f"\n{format(score, '.4f')}% \t-\t {ra}"
            last_ra = ra

    return result

def search_song(acronym):
    read_dxdata()

    result = []
    result_num = 0
    for song in songs :
        if acronym in song['searchAcronyms'] or difflib.SequenceMatcher(None, acronym.lower(), song['title'].lower()).ratio() >= 0.9 or acronym.lower() in song['title'].lower():
            result_num += 1
            image_url = smart_upload(song_info_generate(song))
            message = ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
            result.append(message)

    if result_num >= 6:
        result = result[:6]

    elif not result_num:
        result = TextSendMessage(text="❓ こういう曲がないかも...")

    return result

def random_song(key=""):
    read_dxdata()
    length = len(songs)
    is_exit = False
    result = [TextSendMessage(text="🥳 この曲必ずできるよ！")]
    valid_songs = []

    if key:
        level_values = parse_level_value(key)


    for song in songs:
        for sheet in song['sheets']:
            if sheet['regions']['jp']:
                if not key or sheet['internalLevelValue'] in level_values:
                    valid_songs.append(song)
                    break  # 一个 song 满足一次即可

    if not valid_songs:
        return [TextSendMessage(text="❓ 条件に合う楽曲がないかも...")]

    song = random.choice(valid_songs)

    image_url = smart_upload(song_info_generate(song))
    message = ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
    result.append(message)

    return result

def get_friends_list_buttons(user_id):
    if user_id not in users :
        return no_segaid

    elif 'sega_id' not in users[user_id] or 'sega_pwd' not in users[user_id] :
        return no_segaid

    sega_id = users[user_id]['sega_id']
    sega_pwd = users[user_id]['sega_pwd']

    user_session = login_to_maimai(sega_id, sega_pwd)

    return generate_flex_carousel("オトモダチリスト", format_favorite_friends(get_friends_list(user_session)))

def get_song_record(user_id, acronym) :
    read_dxdata()

    song_record = read_record(user_id)

    if not len(song_record):
        return no_record

    result = []

    for song in songs :
        if acronym in song['searchAcronyms'] or difflib.SequenceMatcher(None, acronym.lower(), song['title'].lower()).ratio() >= 0.9 or acronym.lower() in song['title'].lower():
            played_data = []
            for rcd in song_record :
                if difflib.SequenceMatcher(None, rcd['name'], song['title']).ratio() >= 1.0 and rcd['kind'] == song['type']:
                    rcd['rank'] = ""
                    played_data.append(rcd)

            if not played_data:
                continue

            image_url = smart_upload(song_info_generate(song, played_data))
            message = ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
            result.append(message)

    if len(result) == 0 or len(result) > 6:
        result = [TextSendMessage(text="❓ こういう曲がないかも...")]

    return result

def generate_plate_rcd(user_id, title, generate_user_info=True):
    if not (len(title) == 2 or len(title) == 3):
        return TextSendMessage(text="Error")

    read_user()
    read_dxdata()

    song_record = read_record(user_id)

    if not len(song_record):
        return no_record

    version_name = title[0]
    plate_type = title[1:]

    target_version = []
    target_icon = []
    target_type = ""

    for version in versions :
        if version_name in version['abbr'] :
            target_version.append(version['version'])

    if not len(target_version) :
        return TextSendMessage(text="Error")

    if plate_type in ["極", "极"] :
        target_type = "combo"
        target_icon = ["fc", "fcp", "ap", "app"]

    elif plate_type == "将" :
        target_type = "score"
        target_icon = ["sss", "sssp"]

    elif plate_type == "神" :
        target_type = "combo"
        target_icon = ["ap", "app"]

    elif plate_type == "舞舞" :
        target_type = "dx"
        target_icon = ["fdx", "fdxp"]

    version_rcd_data = list(filter(lambda x: x['version'] in target_version, song_record))
    target_data = []
    target_num = {
        'basic': {'all': 0, 'clear': 0},
        'advanced': {'all': 0, 'clear': 0},
        'expert': {'all': 0, 'clear': 0},
        'master': {'all': 0, 'clear': 0}
    }

    for song in songs :
        if song['version'] not in target_version or song['type'] == 'utage':
            continue

        for sheet in song['sheets'] :
            if not sheet['regions']['jp'] or sheet["difficulty"] not in target_num:
                continue

            icon = "back"
            target_num[sheet['difficulty']]['all'] += 1
            for rcd in version_rcd_data:
                if rcd['name'] == song['title'] and sheet['difficulty'] == rcd['difficulty'] and rcd['kind'] == song['type'] :
                    icon = rcd[f'{target_type}-icon']
                    if icon in target_icon :
                        target_num[sheet['difficulty']]['clear'] += 1

            if sheet['difficulty'] == "master" :
                target_data.append({"img": create_small_record(f"https://shama.dxrating.net/images/cover/v2/{song['imageName']}.jpg", icon, target_type), "level": sheet['level']})

    img = generate_plate_image(target_data, title, headers = target_num)

    if generate_user_info :
        img = combine_with_rounded_background(create_user_info_img(user_id), img)

    image_url = smart_upload(img)
    message = ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)

    return message

def create_user_info_img(user_id, scale=1.5):
    global users
    read_user()

    user_info = users[user_id]['personal_info']

    img_width = 802
    img_height = 128
    info_img = Image.new("RGBA", (img_width, img_height), (255, 255, 255))
    draw = ImageDraw.Draw(info_img)

    def paste_image(key, position, size):
        nonlocal user_info
        if key in user_info and user_info[key]:
            try:
                response = requests.get(user_info[key], verify=False)
                img = Image.open(BytesIO(response.content))
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                img_resized = img.resize(size)
                info_img.paste(img_resized, position, img_resized)
            except Exception as e:
                print(f"加载图片失败 {user_info[key]}: {e}")

    # 背景为名牌图
    paste_image("nameplate_url", (0, 0), (802, 128))

    # 玩家图标（左侧）
    paste_image("icon_url", (15, 13), (100, 100))

    # 等级评分块
    paste_image("rating_block_url", (129, 13), (131, 34))
    draw.text((188, 17), f"{user_info['rating']}", fill=(255, 255, 255), font=font_large)

    # 名字
    draw.rectangle([129, 51, 129 + 266, 51 + 33], fill=(255, 255, 255))
    draw.text((135, 54), user_info['name'], fill=(0, 0, 0), font=font_large)

    # 段位块
    paste_image("class_rank_url", (296, 10), (61, 37))

    # 段位课程块
    paste_image("cource_rank_url", (322, 52), (75, 33))

    # 奖杯信息
    def trophy_color(type):
        return {
            "normal": (255, 255, 255),
            "bronze": (193, 102, 78),
            "silver": (186, 255, 251),
            "gold": (255, 243, 122),
            "rainbow": (233, 83, 106),
        }.get(type, (255, 255, 255))

    draw.rectangle([129, 92, 129 + 266, 92 + 21], fill=trophy_color(user_info['trophy_type']))
    draw.text((135, 93), user_info['trophy_content'], fill=(0, 0, 0), font=font_small)

    info_img = info_img.resize((int(img_width * scale), int(img_height * scale)), Image.LANCZOS)
    return info_img

def selgen_records(user_id, type="best50", generate_user_info=True):
    read_user()

    song_record = read_record(user_id)
    if not len(song_record):
        return no_record

    up_songs = down_songs = []

    up_songs_data = list(filter(lambda x: x['new_song'] == False, song_record))
    down_songs_data = list(filter(lambda x: x['new_song'] == True, song_record))

    if type == "best50":
        up_songs = sorted(up_songs_data, key=lambda x: -x["ra"])[:35]
        down_songs = sorted(down_songs_data, key=lambda x: -x["ra"])[:15]

    elif type == "best100":
        up_songs = sorted(up_songs_data, key=lambda x: -x["ra"])[:70]
        down_songs = sorted(down_songs_data, key=lambda x: -x["ra"])[:30]

    elif type == "best35":
        up_songs = sorted(up_songs_data, key=lambda x: -x["ra"])[:35]

    elif type == "best15":
        down_songs = sorted(down_songs_data, key=lambda x: -x["ra"])[:15]

    elif type == "allb50":
        up_songs = sorted(song_record, key=lambda x: -x["ra"])[:50]

    elif type == "allb35":
        up_songs = sorted(song_record, key=lambda x: -x["ra"])[:35]

    elif type == "allp50":
        up_songs_data = list(filter(lambda x: x['combo-icon'] == 'ap' or x['combo-icon'] == 'app', up_songs_data))
        up_songs = sorted(up_songs_data, key=lambda x: -x["ra"])[:35]

        down_songs_data = list(filter(lambda x: x['combo-icon'] == 'ap' or x['combo-icon'] == 'app', down_songs_data))
        down_songs = sorted(down_songs_data, key=lambda x: -x["ra"])[:15]

    elif type == "未発見":
        up_songs = list(filter(lambda x: x['version'] == "UNKNOWN", song_record))

    elif type == "rct50":
        recent_song_record = read_record(user_id, recent=True)
        if not len(recent_song_record):
            return no_record

        up_songs = recent_song_record

    elif type == "idealb50":
        for rcd in up_songs_data:
            ideal_score = get_ideal_score(float(rcd['score'][:-1]))
            rcd['score'] = f"{ideal_score:.4f}%"
            rcd['ra'] = get_single_ra(rcd['internalLevelValue'], ideal_score)

        for rcd in down_songs_data:
            ideal_score = get_ideal_score(float(rcd['score'][:-1]))
            rcd['score'] = f"{ideal_score:.4f}%"
            rcd['ra'] = get_single_ra(rcd['internalLevelValue'], ideal_score)

        up_songs = sorted(up_songs_data, key=lambda x: -x["ra"])[:35]
        down_songs = sorted(down_songs_data, key=lambda x: -x["ra"])[:15]

    else:
        return selgen_records(user_id)

    img = generate_records_picture(up_songs, down_songs, type.upper())

    if generate_user_info:
        img = combine_with_rounded_background(create_user_info_img(user_id), img)

    else:
        img = wrap_in_rounded_background(img)

    image_url = smart_upload(img)
    message = ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
    return message

def generate_friend_b50(user_id, friend_id):
    read_user()

    if user_id not in users :
        return no_segaid

    elif 'sega_id' not in users[user_id] or 'sega_pwd' not in users[user_id] :
        return no_segaid

    sega_id = users[user_id]['sega_id']
    sega_pwd = users[user_id]['sega_pwd']

    user_session = login_to_maimai(sega_id, sega_pwd)

    song_record = get_detailed_info(get_friend_records(user_session, friend_id))

    up_songs_data = list(filter(lambda x: x['new_song'] == False, song_record))
    down_songs_data = list(filter(lambda x: x['new_song'] == True, song_record))

    up_songs = sorted(up_songs_data, key=lambda x: -x["ra"])[:35]
    down_songs = sorted(down_songs_data, key=lambda x: -x["ra"])[:15]

    img = generate_records_picture(up_songs, down_songs, "FRD-B50")
    img = wrap_in_rounded_background(img)

    image_url = smart_upload(img)
    message = ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
    return message

def generate_level_records(user_id, level, generate_user_info=True):
    read_user()

    song_record = read_record(user_id)

    if not len(song_record):
        return no_record

    level_value = parse_level_value(level)

    up_songs_data = list(filter(lambda x: x['new_song'] == False, song_record))
    down_songs_data = list(filter(lambda x: x['new_song'] == True, song_record))

    up_level_list_data = list(filter(lambda x: x['internalLevelValue'] in level_value, up_songs_data))
    down_level_list_data = list(filter(lambda x: x['internalLevelValue'] in level_value, down_songs_data))

    up_level_list = sorted(up_level_list_data, key=lambda x: -x["ra"])
    down_level_list = sorted(down_level_list_data, key=lambda x: -x["ra"])

    if not up_level_list and not down_level_list:
        return TextSendMessage(text=f"❓ 指定されたレベル {level} の譜面記録は存在しないかも...")

    title = f"LV {level}"

    img = generate_records_picture(up_level_list, down_level_list, title)

    if generate_user_info :
        img = combine_with_rounded_background(create_user_info_img(user_id), img)
    else:
        img = wrap_in_rounded_background(img)

    image_url = smart_upload(img)
    message = ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
    return message

def generate_version_songs(version_title):
    read_dxdata()

    target_version = []
    target_icon = []
    target_type = ""

    for version in versions :
        if version_title.lower() == version['version'].lower() :
            target_version.append(version['version'])

    if not len(target_version) :
        return TextSendMessage(text="Error")

    songs_data = list(filter(lambda x: x['version'] in target_version and x['type'] not in ['utage'], songs))
    img = generate_version_list(songs_data)

    image_url = smart_upload(img)
    message = ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
    return message

def smart_reply(user_id, reply_token, messages):
    if not isinstance(messages, list):
        messages = [messages]

    notice_read = get_user_status(user_id, "notice_read")
    if not notice_read:
        noticement_json = get_latest_notice()
        noticement = f"📢 お知らせ\n{divider}\n{noticement_json['content']}\n{divider}\n{noticement_json['date']}" if noticement_json else "通知ありません"
        messages += [TextSendMessage(text=noticement)]
        edit_user_status(user_id, "notice_read", True)

    if reply_token.startswith("proxy"):
        try:
            origin_ip = '127.0.0.1'

            message_dicts = [msg.as_json_dict() for msg in messages]
            debug_response = requests.post(
                f"http://{origin_ip}:4001/jietng_reply",
                json={
                    "token": reply_token,
                    "messages": message_dicts
                }
            )
            print(f"[Debug Reply] {debug_response.status_code}")
        except Exception as e:
            print(f"[Debug Reply] {e}")
    else:
        line_bot_api.reply_message(reply_token, messages)

def smart_push(user_id, reply_token, messages):
    if reply_token.startswith("proxy"):
        try:
            origin_ip = '127.0.0.1'

            if not isinstance(messages, list):
                messages = [messages]

            message_dicts = [msg.as_json_dict() for msg in messages]

            debug_response = requests.post(
                f"http://{origin_ip}:4001/jietng_reply",
                json={
                    "token": reply_token,
                    "messages": message_dicts
                }
            )
            print(f"[Debug Push] {debug_response.status_code}")
        except Exception as e:
            print(f"[Debug Push] {e}")
    else:
        line_bot_api.push_message(user_id, messages)

def should_respond(event):
    source_type = event.source.type

    if source_type == "user":
        return True

    if hasattr(event.message, "mention") and event.message.mention:
        for mention in event.message.mention.mentionees:
            if mention.user_id == request.destination:
                return True

    return False


#消息处理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        task_queue.put_nowait((handle_text_message_task, (event,)))

    except queue.Full:
        smart_reply(
            event.source.user_id,
            event.reply_token,
            TextSendMessage(text="🙇 今はアクセスが集中しています。後ほどもう一度お試しください。")
        )


def handle_text_message_task(event):
    user_message = event.message.text.strip()
    user_id = event.source.user_id
    is_fake = False
    fake_id = f"fake_{user_id}"
    fake_token = get_fake_token(user_id)

    if user_message.startswith("fakemai "):
        user_message = user_message[8:]
        is_fake = bool(fake_id)

    need_reply = True

    if user_message in ["check", "network"]:
        reply_message = TextSendMessage(text="Active")

    elif user_message == "人数チェック":
        reply_message = TextSendMessage(text=get_num_of_people())

    elif user_message.endswith("ってどんな曲") :
        reply_message = search_song(user_message[:-6].strip())

    elif user_message.startswith("ランダム曲"):
        reply_message = random_song(user_message[5:].strip())

    elif user_message.startswith("rc ") :
        reply_message = TextSendMessage(text=get_rc(float(user_message[3:])))

    elif user_message.lower() in ["segaid bind", "segaid バインド", "sega bind", "sega バインド"]:
        bind_url = f"https://{DOMAIN}/linebot/sega_bind?token={generate_token(user_id)}"

        if user_id.startswith("U"):
            buttons_template = ButtonsTemplate(
                title='SEGA アカウント連携',
                text=(
                    'このボタンを押すとSEGAアカウントと連携されます\n'
                    '有効期限は発行から2分です'
                ),
                actions=[
                    URIAction(label='押しで連携', uri=bind_url)
                ]
            )
            reply_message = TemplateSendMessage(
                alt_text='SEGA アカウント連携',
                template=buttons_template
            )

        else:
            reply_message = TextSendMessage(text=f"こちらはバインド用リンクです↓\n{bind_url}\nこのリンクは発行から10分間有効です")

    elif user_message.startswith(("segaid bind ", "pwd bind ")):
        reply_message = TextSendMessage(text="SEGA IDの連携には「sega bind」コマンドをご利用ください")

    elif user_message.startswith("bind fakemai "):
        bind_fake_token(user_id, user_message[13:].strip())
        reply_message = TextSendMessage(text="Binded Successfully!")

    elif user_message in ["unbind", "連携削除", "連携解消"]:
        user_id = fake_id if is_fake else user_id
        delete_user(user_id)
        reply_message = TextSendMessage(text="SEGA ID 連携解消成功！")

    elif user_message in ["get me", "getme", "個人情報", "个人信息"]:
        reply_message = TextSendMessage(text=get_user(user_id))

    elif user_message == "update fakemai" :
        need_reply = False
        reply_message = TextSendMessage(text="🥳 アップデートの順番に入った！")
        smart_reply(
            user_id,
            event.reply_token,
            reply_message
        )
        update_success, reply_text = fakemai_update(fake_id, fake_token)
        smart_push(user_id, event.reply_token, TextSendMessage(text=reply_text))

    elif user_message in ["マイマイアップデート", "maimai update", "レコードアップデート", "record update"]:
        need_reply = False
        try:
            webtask_queue.put_nowait((async_maimai_update_task, (user_id, event.reply_token)))
        except queue.Full:
            smart_reply(user_id, event.reply_token, TextSendMessage(text="🙇 現在アップデート処理が混雑しています。後ほどお試しください。"))

    elif user_message.endswith(("の達成状況", "の達成情報", "の達成表")) :
        id_use = fake_id if is_fake else user_id
        reply_message = generate_plate_rcd(id_use, user_message.replace("の達成状況", "").replace("の達成情報", "").replace("の達成表", "").strip(), (not is_fake))

    elif user_message.endswith("のレコード") :
        id_use = fake_id if is_fake else user_id
        reply_message = get_song_record(id_use, user_message.replace("のレコード", "").strip())

    elif user_message.lower() in ["ベスト50", "b50", "best 50"]:
        id_use = fake_id if is_fake else user_id
        reply_message = selgen_records(id_use, "best50", (not is_fake))

    elif user_message.lower() in ["ベスト35", "b35", "best 35"]:
        id_use = fake_id if is_fake else user_id
        reply_message = selgen_records(id_use, "best35", (not is_fake))

    elif user_message.lower() in ["ベスト15", "b15", "best 15"]:
        id_use = fake_id if is_fake else user_id
        reply_message = selgen_records(id_use, "best15", (not is_fake))

    elif user_message.lower() in ["オールベスト50", "ab50", "all best 50"]:
        id_use = fake_id if is_fake else user_id
        reply_message = selgen_records(id_use, "allb50", (not is_fake))

    elif user_message.lower() in ["オールベスト35", "ab35", "all best 35"]:
        id_use = fake_id if is_fake else user_id
        reply_message = selgen_records(id_use, "allb35", (not is_fake))

    elif user_message.lower() in ["オールパーフェクト50", "ap50", "all perfect 50"]:
        id_use = fake_id if is_fake else user_id
        reply_message = selgen_records(id_use, "allp50", (not is_fake))

    elif user_message.lower() in ["未発見", "unknown songs", "unknown data"]:
        id_use = fake_id if is_fake else user_id
        reply_message = selgen_records(id_use, "未発見", (not is_fake))

    elif user_message.lower() in ["rct50", "r50", "recent 50"]:
        id_use = fake_id if is_fake else user_id
        reply_message = selgen_records(id_use, "rct50", (not is_fake))

    elif user_message.lower() in ["理想的ベスト50", "idealb50", "idlb50", "ideal best 50"]:
        id_use = fake_id if is_fake else user_id
        reply_message = selgen_records(id_use, "idealb50", (not is_fake))

    elif user_message in ["friend list", "friends list", "友達リスト", "friend-b50"]:
        reply_message = get_friends_list_buttons(user_id)

    elif user_message.startswith("friend-b50 "):
        friend_id = user_message.replace("friend-b50 ", "").strip()
        reply_message = generate_friend_b50(user_id, friend_id)

    elif user_message.endswith("のレコードリスト") :
        id_use = fake_id if is_fake else user_id
        reply_message = generate_level_records(id_use, user_message[:-8].strip(), (not is_fake))

    elif user_message.endswith(("のレベルリスト", "の定数リスト")):
        reply_message = TextSendMessage(text="最新のコマンド「XXのレコードリスト」をご利用ください")

    elif user_message.endswith("のバージョンリスト"):
        reply_message = generate_version_songs(user_message[:-9].replace("+", " plus").strip())

    elif user_message.startswith("calc "):
        num= list(map(int, user_message[5:].split()))
        if len(num) == 5 or len(num) == 4:
            if len(num) == 4:
                num[4] = num[3]
                num[3] = 0

            notes = {
                'tap': num[0],
                'hold': num[1],
                'slide': num[2],
                'touch': num[3],
                'break': num[4]
            }

            scores = get_note_score(notes)
            result = f"TAP: \t {num[0]}\nHOLD: \t {num[1]}\nSLIDE: \t {num[2]}\nTOUCH: \t {num[3]}\nBREAK: \t {num[4]}\n{divider}\n"
            for k, v in scores.items():
                result += f"{k.ljust(20)} -{v:.5f}%\n"

            print(result)

            reply_message = TextSendMessage(text=result)

        else:
            reply_message = TextSendMessage(text="入力エラー")


    elif user_message in ["お知らせ", "notice", "notification", "noticement", "通知"]:
        noticement_json = get_latest_notice()
        noticement = f"📢 お知らせ\n{divider}\n{noticement_json['content']}\n{divider}\n{noticement_json['date']}" if noticement_json else "通知ありません"
        reply_message = TextSendMessage(text=noticement)

    elif user_id in admin_id:
        if user_message == "dxdata update":
            load_dxdata(DXDATA_URL, dxdata_list)
            read_dxdata()
            reply_message = TextSendMessage(text="updated")

        elif user_message.startswith("upload notice"):
            new_noticement = user_message.replace("upload notice", "").strip()
            upload_notice(new_noticement)
            edit_user_status_of_all("notice_read", False)
            reply_message = TextSendMessage(text="uploaded")

    else:
        need_reply = False

    if need_reply :
        smart_reply(
            user_id,
            event.reply_token,
            reply_message
        )

#位置信息处理
@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    try:
        task_queue.put_nowait((handle_location_message_task, (event,)))
    except queue.Full:
        smart_reply(
            event.source.user_id,
            event.reply_token,
            TextSendMessage(text="🙇 今はアクセスが集中しています。後ほどもう一度お試しください。")
        )

def handle_location_message_task(event):
    lat = event.message.latitude
    lng = event.message.longitude

    stores = get_nearby_maimai_stores(lat, lng)
    if not stores:
        reply_message = TextSendMessage(text="🥹 周辺の設置店舗が見つからなかった...")
    else:
        reply_message = [TextSendMessage(text="🗺️ 最寄りのmaimai設置店舗:")]
        for i, store in enumerate(stores[:4]):
            reply_message.append(TextSendMessage(text=f"📌 {store['name']}\n{store['address']}\n（{store['distance']}）\n地図: {store['map_url']}"))

    smart_reply(
        event.source.user_id,
        event.reply_token,
        reply_message
    )

if __name__ == "__main__":
    app.run(port=5100, threaded=True)
