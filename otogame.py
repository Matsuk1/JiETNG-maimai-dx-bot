import io
import sys
import os

from flask import Flask, request, send_file, jsonify
from playwright.sync_api import sync_playwright

# 确保项目根目录在 path 中，以便 import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.record_manager import get_detailed_info
from modules.images.records import generate_records_picture
from modules.images.composition import compose_images
from modules.maimai_manager import get_rating_image_path
from modules.config_loader import DOMAIN

app = Flask(__name__)

OTOGAME_API = "https://u.otogame.net"
BCN_BASE = "https://bemanicn.com"

DIFFICULTY_MAP = {0: "basic", 1: "advanced", 2: "expert", 3: "master", 4: "remaster"}
COMBO_MAP = {0: "back", 1: "fc", 2: "fcp", 3: "ap", 4: "app"}


class OtogameClient:
    """Otogame API 客户端，复用浏览器实例。"""

    def __init__(self):
        self._pw = None
        self._browser = None
        self._page = None

    def login(self, email, password):
        """登录并保持浏览器实例用于后续请求。"""
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self._page = self._browser.new_page()

        self._page.goto(f"{OTOGAME_API}/")
        self._page.wait_for_load_state("networkidle")
        self._page.click(".auth-button.login")
        self._page.click("text=使用BCN账户登录", timeout=5000)
        self._page.wait_for_url(f"{BCN_BASE}/**", timeout=15000)

        self._page.fill("#email", email)
        self._page.fill("#password", password)
        self._page.click("button[type=submit]")
        self._page.wait_for_url(f"{OTOGAME_API}/dashboard**", timeout=30000)
        self._page.wait_for_load_state("networkidle")

    def request(self, path, params=None):
        """通过页面内 fetch 发起 API 请求。"""
        qs = ""
        if params:
            qs = "?" + "&".join(f"{k}={v}" for k, v in params.items())

        return self._page.evaluate("""
            async ([path, qs]) => {
                const tokenData = JSON.parse(localStorage.getItem('TOKEN') || '{}');
                const idTokenData = JSON.parse(localStorage.getItem('ID_TOKEN') || '{}');
                const token = idTokenData.value || tokenData.value;
                const resp = await fetch(path + qs, {
                    headers: {
                        "Authorization": "Bearer " + token,
                        "Accept": "application/json"
                    }
                });
                return resp.json();
            }
        """, [path, qs])

    def get_rating(self):
        return self.request("/api/game/maimai/rating")

    def get_profile(self):
        return self.request("/api/game/maimai/profile")

    def close(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._browser = None
        self._page = None
        self._pw = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def convert_record(entry):
    """将 Otogame rating 条目转换为 JiETNG music_record 格式。"""
    music = entry.get("music", {})
    level_info = entry.get("level_info", {})

    achievement = entry.get("achievement", 0)
    score = f"{achievement / 10000:.4f}%"

    difficulty = DIFFICULTY_MAP.get(level_info.get("difficulty", 3), "master")
    song_type = "dx" if music.get("is_deluxe") else "std"
    combo_icon = COMBO_MAP.get(entry.get("combo_status", 0), "back")

    ach = achievement / 10000
    if ach >= 100.5:
        score_icon = "sssp"
    elif ach >= 100.0:
        score_icon = "sss"
    elif ach >= 99.5:
        score_icon = "ssp"
    elif ach >= 99.0:
        score_icon = "ss"
    elif ach >= 98.0:
        score_icon = "sp"
    elif ach >= 97.0:
        score_icon = "s"
    else:
        score_icon = "aaa"

    return {
        "name": music.get("name", ""),
        "difficulty": difficulty,
        "type": song_type,
        "score": score,
        "dx_score": "",
        "score_icon": score_icon,
        "combo_icon": combo_icon,
        "sync_icon": "back"
    }


def convert_rating(rating_data):
    """将 Otogame rating 响应转换为 JiETNG 格式。"""
    data = rating_data.get("data", rating_data)

    best_list = data.get("rating_list", [])
    new_list = data.get("new_rating_list", [])

    return {
        "rating": data.get("rating", 0),
        "best_rating": data.get("best_rating", 0),
        "new_rating": data.get("new_rating", 0),
        "best": [convert_record(e) for e in best_list],
        "new": [convert_record(e) for e in new_list],
    }


CDN_URL = "https://oss-hd1.bemanicn.com/SDEZ"

TROPHY_RARITY_MAP = {0: "normal", 1: "bronze", 2: "silver", 3: "gold", 4: "rainbow"}


def convert_profile(profile_data, rating_value=0):
    """将 Otogame profile 转为 JiETNG user_info 格式。"""
    data = profile_data.get("data", profile_data)

    name = data.get("user_name", "")
    rating_str = str(rating_value or data.get("rating", 0))
    rating_int = int(rating_str) if rating_str.isdigit() else 0

    # 头像
    avatar = data.get("avatar", "")
    icon_url = f"{CDN_URL}/icon/{avatar}.webp-thumbnail" if avatar else "N/A"

    # 称号
    title = data.get("title", {})
    trophy_name = title.get("name", "N/A") if isinstance(title, dict) else "N/A"
    trophy_rarity = title.get("rarity", 4) if isinstance(title, dict) else 4
    trophy_type = TROPHY_RARITY_MAP.get(trophy_rarity, "rainbow")

    return {
        "name": name,
        "rating_block_path": get_rating_image_path(rating_int),
        "rating": rating_str,
        "cource_rank_url": "N/A",
        "class_rank_url": "N/A",
        "icon_url": icon_url,
        "nameplate_url": f"https://{DOMAIN}/linebot/img/keep_nameplate",
        "trophy_url": f"https://maimaidx.jp/maimai-mobile/img/trophy_{trophy_type}.png",
        "trophy_content": trophy_name,
    }


@app.route("/best50", methods=["GET"])
def api_best50():
    """生成 Best50 图片并返回。"""
    email = request.args.get("email")
    password = request.args.get("password")
    ver = request.args.get("ver", "jp")
    if not email or not password:
        return jsonify({"error": "缺少 email 或 password 参数"}), 400

    try:
        with OtogameClient() as client:
            client.login(email, password)
            rating_raw = client.get_rating()
            profile_raw = client.get_profile()
            rating = convert_rating(rating_raw)
            user_info = convert_profile(profile_raw, rating["rating"])

        # 合并 best + new 为完整记录列表，补充详细信息
        all_records = rating["best"] + rating["new"]
        all_records = get_detailed_info(all_records, ver)

        # 分离旧曲和新曲
        up_songs = sorted(
            [r for r in all_records if not r.get("new_song", True)],
            key=lambda x: (x["ra"], float(x["score"][:-1])),
            reverse=True
        )[:35]

        down_songs = sorted(
            [r for r in all_records if r.get("new_song", True)],
            key=lambda x: (x["ra"], float(x["score"][:-1])),
            reverse=True
        )[:15]

        # 生成图片
        record_img = generate_records_picture(up_songs, down_songs, "BEST50", ver)

        # 生成用户信息图片
        # 延迟 import 避免循环依赖
        from main import generate_profile
        profile_img = generate_profile(user_info)

        final_img = compose_images([profile_img, record_img])

        # 输出为 PNG
        buf = io.BytesIO()
        final_img.save(buf, format="PNG")
        buf.seek(0)

        return send_file(buf, mimetype="image/png")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
