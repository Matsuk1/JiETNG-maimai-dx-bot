import certifi
import gc
import random
import requests
import json
import re
import traceback
import math
import difflib
import numpy
import threading
import queue
import textwrap

from PIL import Image, ImageDraw
from io import BytesIO

from pyzbar.pyzbar import decode
from urllib.parse import urlparse

from flask import (
    Flask,
    request,
    abort,
    render_template,
    redirect
)

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    ImageMessage,
    ImageSendMessage,
    LocationMessage,
    TemplateSendMessage,
    ButtonsTemplate,
    MessageAction,
    URIAction,
)

from modules.admin_tools import *
from modules.song_generate import *
from modules.record_generate import *
from modules.user_console import *
from modules.token_console import *
from modules.notice_console import *
from modules.maimai_console import *
from modules.dxdata_console import *
from modules.record_console import *
from modules.config_loader import *
from modules.friend_list import *
from modules.reply_text import *
from modules.note_score import *
from modules.img_upload import *

from modules.img_console import (
    combine_with_rounded_background,
    wrap_in_rounded_background,
    generate_qr_with_title
)

divider = "-" * 33

app = Flask(__name__)

# 主任务队列
task_queue = queue.Queue(maxsize=10)
concurrency_limit = threading.Semaphore(3)

# Web任务队列
webtask_queue = queue.Queue(maxsize=10)
webtask_concurrency_limit = threading.Semaphore(1)

def run_task_with_limit(func, args, sem, q):
    with sem:
        task_done = threading.Event()

        def target():
            try:
                func(*args)
            except Exception as e:
                print(f"[Task Error] {e}")
                traceback.print_exc()
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

@app.route("/linebot/webhook", methods=['POST'])
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

    gc.collect()
    return 'OK', 200

@app.route("/linebot/adding", methods=["GET"])
@app.route("/linebot/add", methods=["GET"])
def line_add_page():
    return redirect(LINE_ADDING_URL)

@app.route("/linebot/add_friend", methods=["GET"])
def maimai_add_friend_page():
    friend_code = request.args.get("code")
    return redirect(f"line://oaMessage/{LINE_ACCOUNT_ID}/?add-friend%20{friend_code}")

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
        user_version = request.form.get("ver", "jp")
        if not segaid or not password:
            return render_template("error.html", message="すべての項目を入力してください"), 400

        if process_sega_credentials(user_id, segaid, password, user_version):
            return render_template("success.html")
        else:
            return render_template("error.html", message="SEGA ID と パスワード をもう一度確認してください"), 500

    return render_template("bind_form.html")

def process_sega_credentials(user_id, segaid, password, ver="jp"):
    base = (
        "https://maimaidx-eng.com/maimai-mobile"
        if ver == "intl"
        else "https://maimaidx.jp/maimai-mobile"
    )

    session = login_to_maimai(segaid, password, ver=ver)
    if fetch_dom(session, f"{base}/home/") is None:
        return False

    user_bind_sega_id(user_id, segaid)
    user_bind_sega_pwd(user_id, password)
    user_set_version(user_id, ver)
    if user_id.startswith("U"):
        smart_push(user_id, None, bind_msg)
    return True

def user_bind_sega_id(user_id, sega_id):
    read_user()

    if user_id not in users :
        add_user(user_id)

    users[user_id]['sega_id'] = sega_id
    write_user()

def user_bind_sega_pwd(user_id, sega_pwd):
    read_user()

    if user_id not in users :
        add_user(user_id)

    users[user_id]['sega_pwd'] = sega_pwd
    write_user()

def user_set_version(user_id, version):
    read_user()

    if user_id not in users :
        add_user(user_id)

    users[user_id]['version'] = version
    write_user()

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

def async_maimai_update_task(user_id, reply_token, ver="jp"):
    reply_msg = maimai_update(user_id, ver)
    smart_reply(user_id, reply_token, reply_msg)

def async_generate_friend_b50_task(user_id, reply_token, friend_code, ver="jp"):
    reply_msg = generate_friend_b50(user_id, friend_code, ver)
    smart_reply(user_id, reply_token, reply_msg)

def async_add_friend_task(user_id, reply_token, friend_code, ver="jp"):
    read_user()

    sega_id = users[user_id]['sega_id']
    sega_pwd = users[user_id]['sega_pwd']

    user_session = login_to_maimai(sega_id, sega_pwd, ver)
    if user_session == None:
        return segaid_error

    reply_msg_data = add_friend(user_session, friend_code, ver)

    reply_msg = TextSendMessage(text=reply_msg_data)
    smart_reply(user_id, reply_token, reply_msg)

    return None

def maimai_update(user_id, ver="jp"):
    messages = []
    func_status = {
        "User Info": True,
        "Best Records": True,
        "Recent Records": True
    }

    read_user()

    if user_id not in users:
        return segaid_error

    elif 'sega_id' not in users[user_id] or 'sega_pwd' not in users[user_id]:
        return segaid_error

    sega_id = users[user_id]['sega_id']
    sega_pwd = users[user_id]['sega_pwd']

    user_session = login_to_maimai(sega_id, sega_pwd, ver)
    if user_session == None:
        return segaid_error

    user_info = get_maimai_info(user_session, ver)
    maimai_records = get_maimai_records(user_session, ver)
    recent_records = get_recent_records(user_session, ver)

    error = False

    if user_info:
        users[user_id]['personal_info'] = user_info
        write_user()
    else:
        func_status["User Info"] = False
        error = True

    if maimai_records:
        write_record(user_id, maimai_records)
    else:
        func_status["Best Records"] = False
        error = True

    if recent_records:
        write_record(user_id, recent_records, recent=True)
    else:
        func_status["Recent Records"] = False
        error = True

    details = "詳しい情報："
    for func, status in func_status.items():
        details += f"\n「{func}」Error" if not status else ""

    if not error:
        messages.append(update_over)
    else:
        messages.append(update_error)
        messages.append(TextSendMessage(text=details))

    return messages

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

def search_song(acronym, ver="jp"):
    read_dxdata(ver)

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
        result = song_error

    return result

def random_song(key="", ver="jp"):
    read_dxdata(ver)
    length = len(songs)
    is_exit = False
    valid_songs = []

    if key:
        level_values = parse_level_value(key)


    for song in songs:
        for sheet in song['sheets']:
            if sheet['regions']['jp']:
                if not key or sheet['internalLevelValue'] in level_values:
                    valid_songs.append(song)
                    break

    if not valid_songs:
        return song_error

    song = random.choice(valid_songs)

    image_url = smart_upload(song_info_generate(song))
    result = ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)

    return result

def get_friends_list_buttons(user_id, ver="jp"):
    read_user()
    if user_id not in users:
        return segaid_error

    elif 'sega_id' not in users[user_id] or 'sega_pwd' not in users[user_id]:
        return segaid_error

    sega_id = users[user_id]['sega_id']
    sega_pwd = users[user_id]['sega_pwd']

    user_session = login_to_maimai(sega_id, sega_pwd, ver)

    friends_list = get_friends_list(user_session, ver)

    if user_id.startswith("U"):
        return generate_friend_buttons("フレンドリスト・Friends List", format_favorite_friends(friends_list))

    result = f"フレンドリスト・Friends List\n{divider}"
    for frd in friends_list:
        if not frd['is_favorite']:
            continue
        result += f"\n{frd['name']} - {frd['rating']}\n - [{frd['user_id']}]"

    result += f"\n{divider}\nCommand: friend-b50 [friend_code]\nExample: friend-b50 100818313"

    return TextSendMessage(text=result)

def get_song_record(user_id, acronym, ver="jp") :
    read_dxdata(ver)

    song_record = read_record(user_id)

    if not len(song_record):
        return record_error

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
        result = song_error

    return result

def generate_plate_rcd(user_id, title, ver="jp"):
    if not (len(title) == 2 or len(title) == 3):
        return plate_error

    read_user()
    read_dxdata(ver)

    song_record = read_record(user_id)

    if not len(song_record):
        return record_error

    version_name = title[0]
    plate_type = title[1:]

    target_version = []
    target_icon = []
    target_type = ""

    for version in versions :
        if version_name in version['abbr'] :
            target_version.append(version['version'])

    if not len(target_version) :
        return version_error

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
        target_type = "sync"
        target_icon = ["fdx", "fdxp"]

    else:
        return plate_error

    version_rcd_data = list(filter(lambda x: x['version'] in target_version, song_record))
    if not version_rcd_data:
        return version_error

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
                    icon = rcd[f'{target_type}_icon']
                    if icon in target_icon :
                        target_num[sheet['difficulty']]['clear'] += 1

            if sheet['difficulty'] == "master" :
                target_data.append({"img": create_small_record(f"https://shama.dxrating.net/images/cover/v2/{song['imageName']}.jpg", icon, target_type), "level": sheet['level']})

    img = generate_plate_image(target_data, title, headers = target_num)

    img = combine_with_rounded_background(create_user_info_img(user_id), img)

    image_url = smart_upload(img)
    message = ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)

    return message

def create_user_info_img(user_id, scale=1.5):
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
                url = user_info[key]

                # 默认不带 headers
                headers = None

                if url.startswith("https://maimaidx-eng.com"):
                    headers = {
                        "Referer": "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=maimaidxex&redirect_url=https://maimaidx-eng.com/maimai-mobile/&back_url=https://maimai.sega.com/",
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/127.0.0.0 Safari/537.36"
                        ),
                        "Host": "maimaidx-eng.com",
                    }

                response = requests.get(url, headers=headers, verify=False)
                response.raise_for_status()

                img = Image.open(BytesIO(response.content))
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                img_resized = img.resize(size)
                info_img.paste(img_resized, position, img_resized)

            except Exception as e:
                print(f"加载图片失败 {user_info[key]}: {e}")

    paste_image("nameplate_url", (0, 0), (802, 128))

    paste_image("icon_url", (15, 13), (100, 100))

    paste_image("rating_block_url", (129, 13), (131, 34))
    draw.text((188, 17), f"{user_info['rating']}", fill=(255, 255, 255), font=font_large)

    draw.rectangle([129, 51, 129 + 266, 51 + 33], fill=(255, 255, 255))
    draw.text((135, 54), user_info['name'], fill=(0, 0, 0), font=font_large)

    paste_image("class_rank_url", (296, 10), (61, 37))

    paste_image("cource_rank_url", (322, 52), (75, 33))

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

def generate_maipass(user_id):
    read_user()
    if user_id not in users:
        return segaid_error

    user_info = users[user_id]["personal_info"]
    user_img = create_user_info_img(user_id)

    title_list = [
        "QRコードをスキャンして",
        "画像を『JiETNG』に送っても",
        "maimai フレンドになれるよ！",
        "\n",
        "Scan the QR code,",
        "or send the image to 'JiETNG',",
        "and we'll become maimai friends!"
    ]

    qr_img = generate_qr_with_title(f"https://jietng.matsuki.top/linebot/add_friend?code={user_info['friend_code']}", title_list)

    img = combine_with_rounded_background(user_img, qr_img)

    image_url = smart_upload(img)
    img_msg = ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
    message = [img_msg, share_msg]
    return message

def selgen_records(user_id, type="best50", command="", ver="jp"):
    read_user()

    if user_id not in users:
        return segaid_error

    song_record = read_record(user_id)
    if not len(song_record):
        return record_error

    if not command == "":
        cmds = re.findall(r"-(\w+)\s+([^ -][^-]*)", command)
        for cmd, cmd_num in cmds:
            if cmd == "lv":
                lv_start, lv_stop = map(float, cmd_num.split())
                song_record = list(filter(lambda x: lv_start <= x['internalLevelValue'] <= lv_stop, song_record))
            elif cmd == "ra":
                ra_start, ra_stop = map(int, cmd_num.split())
                song_record = list(filter(lambda x: ra_start <= x['ra'] <= ra_stop, song_record))
            elif cmd == "dx":
                dx_score = int(re.sub(r"\D", "", cmd_num))
                song_record = list(filter(lambda x: eval(x['dx_score'].replace(",", "")) * 100 >= dx_score, song_record))
            elif cmd == "scr":
                score = float(re.sub(r"[^0-9.]", "", cmd_num))
                song_record = list(filter(lambda x: eval(x['score'].replace("%", "")) >= score, song_record))

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

    elif type == "apb50":
        up_songs_data = [x for x in up_songs_data if x.get("combo_icon") in ("ap", "app")]
        up_songs = sorted(up_songs_data, key=lambda x: x.get("ra", 0), reverse=True)[:35]

        down_songs_data = [x for x in down_songs_data if x.get("combo_icon") in ("ap", "app")]
        down_songs = sorted(down_songs_data, key=lambda x: x.get("ra", 0), reverse=True)[:15]

    elif type == "UNKNOWN":
        up_songs = list(filter(lambda x: x['version'] == "UNKNOWN", song_record))

    elif type == "rct50":
        recent_song_record = read_record(user_id, recent=True)
        if not len(recent_song_record):
            return record_error

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

    img = generate_records_picture(up_songs, down_songs, type.upper())
    img = combine_with_rounded_background(create_user_info_img(user_id), img)

    image_url = smart_upload(img)
    message = ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
    return message

def generate_yang_rating(user_id, ver="jp"):
    song_record = read_record(user_id, yang=True)
    if not len(song_record):
        return record_error

    read_user()
    now_version = MAIMAI_VERSION[users[user_id]['version']][-1]

    version_records = []

    read_dxdata(ver)
    for version in versions:
        if version['version'] == now_version:
            break

        version_data = {}
        version_data['version_title'] = version['version']
        version_song_data = list(filter(lambda x: x['version'] == version['version'], song_record))
        count = max(math.floor(version['count'] * 0.05), 1)
        version_data['songs'] = sorted(version_song_data, key=lambda x: -x["ra"])[:count]
        version_data['count'] = count
        version_records.append(version_data)

    img = generate_yang_records_picture(version_records)
    img = combine_with_rounded_background(create_user_info_img(user_id), img)

    image_url = smart_upload(img)
    message = ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
    return message

def generate_friend_b50(user_id, friend_code, ver="jp"):
    read_user()

    if user_id not in users :
        return segaid_error

    elif 'sega_id' not in users[user_id] or 'sega_pwd' not in users[user_id] :
        return segaid_error

    sega_id = users[user_id]['sega_id']
    sega_pwd = users[user_id]['sega_pwd']

    user_session = login_to_maimai(sega_id, sega_pwd, ver)
    
    friend_name, song_record = get_friend_records(user_session, friend_code, ver)

    song_record = get_detailed_info(song_record, ver)

    up_songs_data = list(filter(lambda x: x['new_song'] == False, song_record))
    down_songs_data = list(filter(lambda x: x['new_song'] == True, song_record))

    up_songs = sorted(up_songs_data, key=lambda x: -x["ra"])[:35]
    down_songs = sorted(down_songs_data, key=lambda x: -x["ra"])[:15]

    img = generate_records_picture(up_songs, down_songs, "FRD-B50")
    img = wrap_in_rounded_background(img)

    image_url = smart_upload(img)
    message = [
        TextSendMessage(text=f"「{friend_name}」さんの Best 50"),
        ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
    ]
    return message

def generate_level_records(user_id, level, ver="jp", page=1):
    read_user()

    song_record = read_record(user_id)

    if not len(song_record):
        return record_error

    level_value = parse_level_value(level)

    up_songs_data = list(filter(lambda x: x['new_song'] == False, song_record))
    down_songs_data = list(filter(lambda x: x['new_song'] == True, song_record))

    up_level_list_data = list(filter(lambda x: x['internalLevelValue'] in level_value, up_songs_data))
    down_level_list_data = list(filter(lambda x: x['internalLevelValue'] in level_value, down_songs_data))

    up_level_list = sorted(up_level_list_data, key=lambda x: -x["ra"])
    down_level_list = sorted(down_level_list_data, key=lambda x: -x["ra"])
    
    page_size_up = 35
    page_size_down = 15

    start_up = (page - 1) * page_size_up
    end_up = start_up + page_size_up

    start_down = (page - 1) * page_size_down
    end_down = start_down + page_size_down

    up_level_list = up_level_list[start_up:end_up]
    down_level_list = down_level_list[start_down:end_down]

    if not up_level_list and not down_level_list:
        return TextSendMessage(text=f"指定されたレベル {level} の譜面記録は存在しないかも...")

    title = f"LV{level} #{page}"

    img = generate_records_picture(up_level_list, down_level_list, title)

    img = combine_with_rounded_background(create_user_info_img(user_id), img)

    image_url = smart_upload(img)
    message = ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
    return message

def generate_version_songs(version_title, ver="jp"):
    read_dxdata(ver)

    target_version = []
    target_icon = []
    target_type = ""

    for version in versions :
        if version_title.lower() == version['version'].lower() :
            target_version.append(version['version'])

    if not len(target_version) :
        return version_error

    songs_data = list(filter(lambda x: x['version'] in target_version and x['type'] not in ['utage'], songs))
    img = generate_version_list(songs_data)

    image_url = smart_upload(img)
    message = ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
    return message

def smart_reply(user_id, reply_token, messages):
    if not isinstance(messages, list):
        messages = [messages]

    if user_id not in users:
        notice_read = True
    else:
        notice_read = get_user_status(user_id, "notice_read")

    if not notice_read:
        notice_json = get_latest_notice()
        if notice_json:
            notice = f"📢 お知らせ\n{divider}\n{notice_json['content']}\n{divider}\n{notice_json['date']}"
            messages += [TextSendMessage(text=notice)]
            edit_user_status(user_id, "notice_read", True)

    if reply_token.startswith("proxy"):
        try:
            message_dicts = [msg.as_json_dict() for msg in messages]
            proxy_response = requests.post(
                PROXY_URL,
                json={
                    "token": reply_token,
                    "messages": message_dicts
                }
            )
            print(f"[Proxy Reply] {proxy_response.status_code}")
        except Exception as e:
            print(f"[Proxy Reply] {e}")
    else:
        line_bot_api.reply_message(reply_token, messages)

def smart_push(user_id, reply_token, messages):
    if (reply_token or "").startswith("proxy"):
        try:
            if not isinstance(messages, list):
                messages = [messages]

            message_dicts = [msg.as_json_dict() for msg in messages]

            proxy_response = requests.post(
                PROXY_URL,
                json={
                    "token": reply_token,
                    "messages": message_dicts
                }
            )
            print(f"[Proxy Push] {proxy_response.status_code}")
        except Exception as e:
            print(f"[Proxy Push] {e}")
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
def handle_text_message(event):
    try:
        task_queue.put_nowait((handle_text_message_task, (event,)))

    except queue.Full:
        smart_reply(
            event.source.user_id,
            event.reply_token,
            access_error
        )

def handle_text_message_task(event):
    user_message = event.message.text.strip()
    user_id = event.source.user_id
    id_use = user_id
    mai_ver = "jp"
    read_user()
    if user_id in users:
        if 'version' in users[user_id]:
            mai_ver = users[user_id]['version']

    # ====== 基础命令映射 ======
    COMMAND_MAP = {
        "check": lambda: active_reply,
        "network": lambda: active_reply,

        "unbind": lambda: (delete_user(user_id), unbind_msg)[-1],
        "連携解消": lambda: (delete_user(user_id), unbind_msg)[-1],

        "get me": lambda: TextSendMessage(text=get_user(user_id)),
        "getme": lambda: TextSendMessage(text=get_user(user_id)),

        "yang": lambda: generate_yang_rating(id_use, mai_ver),
        "yrating": lambda: generate_yang_rating(id_use, mai_ver),
        "yra": lambda: generate_yang_rating(id_use, mai_ver),

        "friend list": lambda: get_friends_list_buttons(user_id, mai_ver),
        "friend-b50": lambda: get_friends_list_buttons(user_id, mai_ver),
        
        "maid card": lambda: generate_maipass(user_id),
        "maid": lambda: generate_maipass(user_id),
        "mai pass": lambda: generate_maipass(user_id)
    }

    if user_message in COMMAND_MAP:
        reply_message = COMMAND_MAP[user_message]()
        return smart_reply(user_id, event.reply_token, reply_message)

    # ====== 模糊匹配规则 ======
    SPECIAL_RULES = [
        (lambda msg: msg.endswith(("ってどんな曲", "song-info")),
        lambda msg: search_song(
            re.sub(r"(ってどんな曲|song-info)$", "", msg).strip(),
            mai_ver
        )),

        (lambda msg: msg.startswith(("ランダム曲", "random-song")),
        lambda msg: random_song(
            re.sub(r"^(ランダム曲|random-song)", "", msg).strip(),
            mai_ver
        )),

        (lambda msg: msg.startswith(("rc ", "RC ", "Rc ")),
        lambda msg: TextSendMessage(
            text=get_rc(float(re.sub(r"^rc\b[ 　]*", "", msg, flags=re.IGNORECASE)))
        )),

        (lambda msg: msg.endswith(("の達成状況", "の達成情報", "の達成表", "achievement-list")),
        lambda msg: generate_plate_rcd(
            id_use,
            re.sub(r"(の達成状況|の達成情報|の達成表|achievement-list)$", "", msg).strip(),
            mai_ver
        )),

        (lambda msg: msg.endswith(("のレコード", "song-record")),
        lambda msg: get_song_record(
            id_use,
            re.sub(r"(のレコード|song-record)$", "", msg).strip(),
            mai_ver
        )),

        (lambda msg: re.match(r".+(のレコードリスト|record-list)[ 　]*\d*$", msg),
        lambda msg: generate_level_records(
            id_use,
            re.sub(r"(のレコードリスト|record-list)[ 　]*\d*$", "", msg).strip(),
            mai_ver,
            int(re.search(r"(\d+)$", msg).group(1)) if re.search(r"(\d+)$", msg) else 1
        )),

        (lambda msg: msg.endswith(("のバージョンリスト", "version-list")),
        lambda msg: generate_version_songs(
            re.sub(r"\s*\+\s*", " PLUS", re.sub(r"(のバージョンリスト|version-list)$", "", msg)).strip(),
            mai_ver
        ))
    ]

    for cond, func in SPECIAL_RULES:
        if cond(user_message):
            reply_message = func(user_message)
            return smart_reply(user_id, event.reply_token, reply_message)

    # ====== B 系列命令 ======
    first_word = re.split(r"[ \n]", user_message.lower(), 1)[0]
    rest_text = re.split(r"[ \n]", user_message.lower(), 1)[1] if re.search(r"[ \n]", user_message) else ""

    RANK_COMMANDS = {
        ("b50", "best 50", "ベスト50"): "best50",
        ("b100", "best 100", "ベスト100"): "best100",
        ("b35", "best 35", "ベスト35"): "best35",
        ("b15", "best 15", "ベスト15"): "best15",
        ("ab50", "all best 50", "オールベスト50"): "allb50",
        ("ab35", "all best 35", "オールベスト35"): "allb35",
        ("ap50", "apb50", "オールパーフェクト50", "all perfect 50", "apb50"): "apb50",
        ("rct50", "r50", "recent 50"): "rct50",
        ("idealb50", "idlb50", "理想的ベスト50", "ideal best 50"): "idealb50",
        ("unknown", "unknown songs", "unknown data", "未発見"): "UNKNOWN",
    }

    for aliases, mode in RANK_COMMANDS.items():
        if first_word in aliases:
            reply_message = selgen_records(id_use, mode, rest_text, mai_ver)
            return smart_reply(user_id, event.reply_token, reply_message)

    # ====== SEGA ID 绑定逻辑 ======
    if user_message.lower() in ["segaid bind", "segaid バインド", "sega bind", "sega バインド"]:
        bind_url = f"https://{DOMAIN}/linebot/sega_bind?token={generate_token(user_id)}"
        if user_id.startswith("U"):
            buttons_template = ButtonsTemplate(
                title='SEGA アカウント連携',
                text='SEGA アカウントと連携されます\n有効期限は発行から2分間です',
                actions=[URIAction(label='押しで連携', uri=bind_url)]
            )
            reply_message = TemplateSendMessage(
                alt_text='SEGA アカウント連携',
                template=buttons_template
            )
        else:
            reply_message = TextSendMessage(text=f"こちらはバインド用リンクです↓\n{bind_url}\n発行から2分間有効。")
        return smart_reply(user_id, event.reply_token, reply_message)

    # ====== maimai 更新任务 ======
    if user_message in ["マイマイアップデート", "maimai update", "レコードアップデート", "record update"]:
        try:
            webtask_queue.put_nowait((async_maimai_update_task, (user_id, event.reply_token, mai_ver)))
        except queue.Full:
            smart_reply(user_id, event.reply_token, access_error)
        return

    # ====== friend-b50 异步任务 ======
    if user_message.startswith("friend-b50 "):
        friend_code = user_message.replace("friend-b50 ", "").strip()
        try:
            webtask_queue.put_nowait((async_generate_friend_b50_task, (user_id, event.reply_token, friend_code, mai_ver)))
        except queue.Full:
            smart_reply(user_id, event.reply_token, access_error)
        return

    # ====== add-friend 异步任务 ======
    if user_message.startswith("add-friend "):
        friend_code = user_message.replace("add-friend ", "").strip()
        try:
            webtask_queue.put_nowait((async_add_friend_task, (user_id, event.reply_token, friend_code, mai_ver)))
        except queue.Full:
            smart_reply(user_id, event.reply_token, access_error)
        return

    # ====== calc 命令 ======
    if user_message.startswith("calc "):
        try:
            num = list(map(int, user_message[5:].split()))
            if len(num) == 4:
                num = [num[0], num[1], num[2], 0, num[3]]
            if len(num) != 5:
                raise ValueError
            notes = dict(zip(['tap', 'hold', 'slide', 'touch', 'break'], num))
            scores = get_note_score(notes)
            result = (
                f"TAP: \t {num[0]}\nHOLD: \t {num[1]}\nSLIDE: \t {num[2]}\n"
                f"TOUCH: \t {num[3]}\nBREAK: \t {num[4]}\n{divider}\n"
            )
            for k, v in scores.items():
                result += f"{k.ljust(20)} -{v:.5f}%\n"
            reply_message = TextSendMessage(text=result)
        except Exception:
            reply_message = input_error
        return smart_reply(user_id, event.reply_token, reply_message)

    # ====== 管理员命令 ======
    if user_id in admin_id:
        admin_cmds = {
            "dxdata update": lambda: (load_dxdata(DXDATA_URL, dxdata_list), read_dxdata(), dxdata_update)[-1],
            "service info": lambda: TextSendMessage(text=textwrap.dedent(f"""
                サービス情報

                · 総ユーザー数 | {get_service_info()['LINE']['num'] + get_service_info()['proxy']['num']}
                · LINE ユーザー数 | {get_service_info()['LINE']['num']}
                · Proxy ユーザー数 | {get_service_info()['proxy']['num']}
            """)),
        }

        if user_message.startswith("upload notice"):
            new_notice = user_message.replace("upload notice", "").strip()
            upload_notice(new_notice)
            edit_user_status_of_all("notice_read", False)
            return smart_reply(user_id, event.reply_token, notice_upload)

        if user_message in admin_cmds:
            reply_message = admin_cmds[user_message]()
            return smart_reply(user_id, event.reply_token, reply_message)

    # ====== 默认：不匹配任何命令 ======
    return

#图片信息处理
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)

    img_bytes = b''.join(chunk for chunk in message_content.iter_content())
    image = Image.open(BytesIO(img_bytes))

    qr_results = decode(image)

    reply_msg = []

    if qr_results:
        for qr in qr_results:
            data = qr.data.decode("utf-8")
            new_reply_msg = handle_image_message_task(event.source.user_id, event.reply_token, data)
            if new_reply_msg:
                reply_msg.append(new_reply_msg)
        if reply_msg:
            smart_reply(
                event.source.user_id,
                event.reply_token,
                reply_msg
            )

    else:
        smart_reply(
            event.source.user_id,
            event.reply_token,
            qrcode_error
        )

def handle_image_message_task(user_id, reply_token, data):
    if DOMAIN in data:
        return handle_internal_link(user_id, reply_token, data)

    else:
        return TextSendMessage(text=data)

def handle_internal_link(user_id, reply_token, data):
    mai_ver = "jp"
    read_user()
    if user_id in users:
        if 'version' in users[user_id]:
            mai_ver = users[user_id]['version']

    URL_MAP = [
        (
            lambda content, domain: re.match(
                rf"^(?:https?://)?{re.escape(domain)}/linebot/add_friend\?code=",
                content
            ),

            lambda content, user_id, reply_token, domain, mai_ver: async_add_friend_task(
                user_id,
                reply_token,
                re.sub(
                    rf"^(?:https?://)?{re.escape(domain)}/linebot/add_friend\?code=",
                    "",
                    content
                ).strip(),
                mai_ver
            )
        ),
    ]

    for condition, action in URL_MAP:
        if condition(data, DOMAIN):
            return action(data, user_id, reply_token, DOMAIN, mai_ver)
        else:
            return TextSendMessage(text=data)


#位置信息处理
@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    try:
        task_queue.put_nowait((handle_location_message_task, (event,)))
    except queue.Full:
        smart_reply(
            event.source.user_id,
            event.reply_token,
            access_error
        )

def handle_location_message_task(event):
    read_user()

    lat = event.message.latitude
    lng = event.message.longitude
    user_id = event.source.user_id

    stores = get_nearby_maimai_stores(lat, lng, users[user_id]['version'])
    if not stores:
        reply_message = TextSendMessage(text="🥹 周辺の設置店舗がないね")
    else:
        reply_message = [TextSendMessage(text="🗺️ 最寄りの maimai 設置店舗")]
        for i, store in enumerate(stores[:4]):
            reply_message.append(TextSendMessage(text=f"📌 {store['name']}\n{store['address']}\n（{store['distance']}）\n地図: {store['map_url']}"))

    smart_reply(
        event.source.user_id,
        event.reply_token,
        reply_message
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
