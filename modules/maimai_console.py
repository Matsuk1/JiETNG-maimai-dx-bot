import json
import requests
from lxml import etree
from record_console import get_detailed_info

def fetch_dom(session: requests.Session, url: str) -> etree._Element:
    if url.startswith("https://maimaidx-eng.com"):
        # 国际服
        headers = {
            "Referer": "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=maimaidxex&redirect_url=https://maimaidx-eng.com/maimai-mobile/&back_url=https://maimai.sega.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/127.0.0.0 Safari/537.36",
            "Host": "maimaidx-eng.com"
        }
    else:
        # 日服
        headers = {
            "Referer": "https://maimaidx.jp/maimai-mobile/login/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/127.0.0.0 Safari/537.36",
            "Host": "maimaidx.jp"
        }

    resp = session.get(url, headers=headers)
    resp.raise_for_status()
    html = resp.text

    if ("Please agree to the following terms of service before log in." in html or
        "再度ログインしてください" in html):
        return None

    return etree.HTML(html)

def login_to_maimai(sega_id: str, password: str, ver="jp"):
    if ver == "intl":
            session = requests.Session()
            session.verify = False
            resp = session.get("https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=maimaidxex&redirect_url=https://maimaidx-eng.com/maimai-mobile/&back_url=https://maimai.sega.com/")
            resp.raise_for_status()

            login_resp = session.post(
                "https://lng-tgk-aime-gw.am-all.net/common_auth/login/sid/",
                data={
                    "sid": sega_id,
                    "password": password,
                    "retention": "1",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                allow_redirects=False
            )

            redirect_url = login_resp.headers.get("Location")
            final_resp = session.get(
                redirect_url,
                headers={
                    "Referer": "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=maimaidxex&redirect_url=https://maimaidx-eng.com/maimai-mobile/&back_url=https://maimai.sega.com/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/127.0.0.0 Safari/537.36",
                    "Host": "maimaidx-eng.com"
                },
                allow_redirects=True
            )

            return session
    else:
            session = requests.Session()
            session.verify = False

            response = session.get("https://maimaidx.jp/maimai-mobile/login/")
            response.raise_for_status()

            parser = etree.HTMLParser()
            dom = etree.HTML(response.text, parser)

            token_list = dom.xpath('//input[@name="token"]/@value')
            if not token_list:
                raise Exception("Unable to fetch login token")
            token = token_list[0]

            login_response = session.post(
                "https://maimaidx.jp/maimai-mobile/submit/",
                data={
                    "segaId": sega_id,
                    "password": password,
                    "save_cookie": "on",
                    "token": token
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                allow_redirects=True
            )

            aime_choose = session.get("https://maimaidx.jp/maimai-mobile/aimeList/submit/?idx=0")
            return session
def get_maimai_records(session: requests.Session, ver="jp"):
    base = "https://maimaidx-eng.com/maimai-mobile" if ver == "intl" else "https://maimaidx.jp/maimai-mobile"
    difficulty = ['basic', 'advanced', 'expert', 'master', 'remaster']
    music_record = []

    for page_num in range(5):
        url = f"{base}/record/musicGenre/search/?genre=99&diff={page_num}"
        dom = fetch_dom(session, url)
        if dom is None:
            return []

        music_blocks = dom.xpath('//div[contains(@class, "w_450")]')

        for block in music_blocks:
            name_div = block.xpath('.//div[contains(@class, "music_name_block")]/text()')
            if not name_div:
                continue
            name = name_div[0]

            score_div = block.xpath('.//div[contains(@class, "music_score_block") and contains(@class, "w_112")]/text()')
            if not score_div:
                continue
            score = score_div[0].strip()

            img_nodes = block.xpath('.//div[contains(@class, "music_score_block") and contains(@class, "w_190")]/img')
            if img_nodes:
                dx_score = img_nodes[0].tail.strip() if img_nodes[0].tail else "N/A"
            else:
                dx_score = "N/A"

            kind_icon = block.xpath('.//img[contains(@class, "music_kind_icon")]/@src')
            if kind_icon:
                if "standard.png" in kind_icon[0]:
                    kind = "std"
                elif "dx.png" in kind_icon[0]:
                    kind = "dx"
                else:
                    kind = "N/A"
            else:
                kind = "N/A"

            icons = block.xpath('.//img[contains(@class, "h_30")]/@src')
            sync_icon = combo_icon = score_icon = ""
            for index, icon in enumerate(icons):
                icon_tag = icon.split('/')[-1].split('.')[0].replace("music_icon_", "")
                if index == 0:
                    sync_icon = icon_tag
                elif index == 1:
                    combo_icon = icon_tag
                elif index == 2:
                    score_icon = icon_tag

            music_record.append({
                "name": name,
                "difficulty": difficulty[page_num],
                "kind": kind,
                "score": score,
                "dx_score": dx_score,
                "score_icon": score_icon,
                "combo_icon": combo_icon,
                "sync_icon": sync_icon
            })

    return music_record

def get_friends_list(session: requests.Session, ver="jp"):
    base = "https://maimaidx-eng.com/maimai-mobile" if ver == "intl" else "https://maimaidx.jp/maimai-mobile"
    url = f"{base}/friend/"
    dom = fetch_dom(session, url)
    if dom is None:
        return []

    friends = []
    blocks = dom.xpath('//div[contains(@class, "see_through_block")]')

    for block in blocks:
        try:
            name = block.xpath('.//div[@class="name_block t_l f_l f_16 underline"]/text()')[0].strip()
            rating = block.xpath('.//div[@class="rating_block"]/text()')[0].strip()
            user_id = block.xpath('.//form/input[@name="idx"]/@value')[0].strip()
            is_favorite = bool(
                block.xpath(f'.//form[@action="{base}/friend/favoriteOff/"]')
            )

            friends.append({
                "name": name,
                "rating": rating,
                "user_id": user_id,
                "is_favorite": is_favorite
            })

        except Exception as e:
            print(f"[get_friends_list] Error parsing block: {e}")

    return friends

def format_favorite_friends(friends):
    return [
        {
            "label": f"{f['name']} [{f['rating']}]",
            "type": "text",
            "content": f"friend-b50 {f['user_id']}"
        }
        for f in friends if f.get("is_favorite")
    ]

def parse_level_value(input_str):
    input_str = input_str.strip()

    if '.' in input_str:
        try:
            return [float(input_str)]
        except ValueError:
            raise ValueError(f"无法解析浮点数: {input_str}")

    elif input_str.endswith('+'):
        try:
            base = int(input_str[:-1])
            return [round(base + i * 0.1, 1) for i in range(6, 10)]
        except ValueError:
            raise ValueError(f"无法解析带加号的整数: {input_str}")

    else:
        try:
            base = int(input_str)
            return [round(base + i * 0.1, 1) for i in range(6)]
        except ValueError:
            raise ValueError(f"无法解析整数: {input_str}")

def get_recent_records(session: requests.Session, ver="jp"):
    base = "https://maimaidx-eng.com/maimai-mobile" if ver == "intl" else "https://maimaidx.jp/maimai-mobile"
    recent_record = []

    url = f"{base}/record/"
    dom = fetch_dom(session, url)
    if dom is None:
        return []

    music_blocks = dom.xpath('//div[contains(@class, "p_10") and contains(@class, "t_l")]')

    if music_blocks:
        for block in music_blocks:
            name_div = block.xpath('.//div[contains(@class, "basic_block") and contains(@class, "break")]/text()')
            if not name_div:
                continue
            name = name_div[1].strip()

            score_div = block.xpath('.//div[contains(@class, "playlog_achievement_txt")]')
            if not score_div:
                continue
            score = ''.join(score_div[0].xpath('.//text()')).strip()

            score_icon = block.xpath('.//img[contains(@class, "playlog_scorerank")]/@src')
            score_icon = score_icon[0].split("/")[-1].split(".")[0] if score_icon else "?"

            dx_score = block.xpath('.//div[contains(@class, "playlog_score_block")]//div[contains(@class, "white")]/text()')
            dx_score = dx_score[0].strip() if dx_score else "?"

            kind_icon = block.xpath('.//img[contains(@class, "playlog_music_kind_icon")]/@src')
            if kind_icon:
                if "standard.png" in kind_icon[0]:
                    kind = "std"
                elif "dx.png" in kind_icon[0]:
                    kind = "dx"
                else:
                    kind = "N/A"
            else:
                kind = "N/A"

            diff_img = block.xpath('.//img[contains(@class, "playlog_diff")]/@src')
            if diff_img:
                diff_raw = diff_img[0].split("/")[-1]  # "diff_master.png"
                if diff_raw.startswith("diff_") and diff_raw.endswith(".png"):
                    difficulty = diff_raw[len("diff_"):-len(".png")]
                else:
                    difficulty = "unknown"
            else:
                difficulty = "unknown"

            icons = block.xpath('.//img[contains(@class, "h_35") and contains(@class, "m_5") and contains(@class, "f_l")]/@src')

            combo_icon = sync_icon = "none"

            if len(icons) >= 1:
                combo_icon = icons[0].split('/')[-1].split('.')[0]
                combo_icon = combo_icon.replace("fc_dummy", "back")

            if len(icons) >= 2:
                sync_icon = icons[1].split('/')[-1].split('.')[0]
                sync_icon = sync_icon.replace("sync_dummy", "back")

            recent_record.append({
                "name": name,
                "difficulty": difficulty,
                "kind": kind,
                "score": score,
                "dx_score": dx_score,
                "score_icon": score_icon.replace("plus", "p"),
                "combo_icon": combo_icon.replace("plus", "p"),
                "sync_icon": sync_icon.replace("plus", "p")
            })

    return recent_record

def get_friend_records(session: requests.Session, user_id: str, ver="jp"):
    base = "https://maimaidx-eng.com/maimai-mobile" if ver == "intl" else "https://maimaidx.jp/maimai-mobile"
    difficulty = ['basic', 'advanced', 'expert', 'master', 'remaster']
    music_record = []

    for diff in range(5):
        url = f"{base}/friend/friendGenreVs/battleStart/?scoreType=2&genre=99&diff={diff}&idx={user_id}"
        dom = fetch_dom(session, url)
        if dom is None:
            continue

        blocks = dom.xpath(f'//div[contains(@class, "music_{difficulty[diff]}_score_back")]')

        for block in blocks:
            try:
                name_node = block.xpath('.//div[contains(@class, "music_name_block")]/text()')
                if not name_node:
                    continue
                name = name_node[0].strip()

                # 对手分数（右边第2个）
                score_cells = block.xpath(f'.//td[contains(@class, "{difficulty[diff]}_score_label")]/text()')
                if len(score_cells) <= 1:
                    continue
                score = score_cells[1].strip()
                if score in ("― %", "- %"):
                    continue

                # 谱面种类
                kind_img = block.xpath('.//img[contains(@class, "music_kind_icon")]/@src')
                if kind_img:
                    if "standard.png" in kind_img[0]:
                        kind = "std"
                    elif "dx.png" in kind_img[0]:
                        kind = "dx"
                    else:
                        kind = "N/A"
                else:
                    kind = "N/A"

                # 图标（取自右边 <td class="t_r f_0">）
                icons = block.xpath('.//td[@class="t_r f_0"]/img/@src')
                sync_icon = combo_icon = score_icon = ""
                for index, icon in enumerate(icons):
                    icon_tag = icon.split('/')[-1].split('.')[0].replace("music_icon_", "")
                    if index == 0:
                        sync_icon = icon_tag
                    elif index == 1:
                        combo_icon = icon_tag
                    elif index == 2:
                        score_icon = icon_tag

                music_record.append({
                    "name": name,
                    "difficulty": difficulty[diff],
                    "kind": kind,
                    "score": score,
                    "dx_score": "0 / 1000",
                    "score_icon": score_icon,
                    "combo_icon": combo_icon,
                    "sync_icon": sync_icon
                })

            except Exception as e:
                print(f"[get_friend_records_like_self] Error parsing block: {e}")

    url = f"{base}/friend/search/searchUser/?friendCode={user_id}"
    dom = fetch_dom(session, url)
    if dom is None:
        return "Unknown", music_record
    friend_name = dom.xpath('//div[contains(@class, "name_block")]/text()')
    friend_name = friend_name[0].strip() if friend_name else "Unknown"

    return friend_name, music_record

def get_maimai_info(session: requests.Session, ver="jp"):
    base = "https://maimaidx-eng.com/maimai-mobile" if ver == "intl" else "https://maimaidx.jp/maimai-mobile"
    user_info = {}

    # 主信息
    dom = fetch_dom(session, f"{base}/playerData/")
    if dom is None:
        return {}

    user_name = dom.xpath('//div[contains(@class, "name_block")]/text()')
    rating_block_url = dom.xpath('//img[contains(@class, "h_30") and contains(@class, "f_r")]/@src')
    rating = dom.xpath('//div[@class="rating_block"]/text()')
    cource_rank_url = dom.xpath('//img[contains(@class, "h_35") and contains(@class, "f_l")]/@src')
    class_rank_url = dom.xpath('//img[contains(@class, "p_l_10") and contains(@class, "h_35") and contains(@class, "f_l")]/@src')

    # 头像
    dom = fetch_dom(session, f"{base}/collection/")
    if dom is None:
        return {}
    icon_url = dom.xpath('//img[contains(@class, "w_80") and contains(@class, "m_r_10") and contains(@class, "f_l")]/@src')

    # 姓名框
    dom = fetch_dom(session, f"{base}/collection/nameplate/")
    if dom is None:
        return {}
    nameplate_url = dom.xpath('//img[contains(@class, "w_396") and contains(@class, "m_r_10")]/@src')

    # 称号
    dom = fetch_dom(session, f"{base}/collection/trophy/")
    if dom is None:
        return {}
    trophy_type = dom.xpath('//div[contains(@class, "block_info") and contains(@class, "f_11") and contains(@class, "orange")]/text()')
    trophy_blocks = dom.xpath('//div[contains(@class, "trophy_inner_block") and contains(@class, "f_13")]')
    if trophy_blocks:
        trophy_block = trophy_blocks[0]
        trophy_texts = trophy_block.xpath('.//text()')
        trophy_content = trophy_texts[1]
    else:
        trophy_content = "N/A"

    user_info = {
        "name": user_name[0].strip() if user_name else "N/A",
        "rating_block_url": rating_block_url[0] if rating_block_url else "N/A",
        "rating": rating[0].strip() if rating else "N/A",
        "cource_rank_url": cource_rank_url[0] if cource_rank_url else "N/A",
        "class_rank_url": class_rank_url[0] if class_rank_url else "N/A",
        "icon_url": icon_url[0] if icon_url else "N/A",
        "nameplate_url": nameplate_url[0] if nameplate_url else "N/A",
        "trophy_type": trophy_type[0].strip().lower() if trophy_type else "N/A",
        "trophy_content": trophy_content.strip() if trophy_content else "N/A",
    }

    return user_info

def extract_onclick_url_from_button(li, keyword):
    btn = li.xpath(f'.//button[contains(@class, "{keyword}")]/@onclick')
    if btn:
        return btn[0].split("'")[1]

    all_buttons = li.xpath('.//button')
    for b in all_buttons:
        text = "".join(b.xpath('.//text()')).strip()
        if "GoogleMap" in text or "Details" in text:
            onclick = b.attrib.get("onclick", "")
            if "window.open" in onclick or "location.href" in onclick:
                return onclick.split("'")[1]
    return ""

def get_nearby_maimai_stores(lat, lng, ver="jp"):
    version_num = "98" if ver == "intl" else "96"
    url = f"https://location.am-all.net/alm/location?gm={version_num}&lat={lat}&lng={lng}"
    session = requests.Session()
    dom = fetch_dom(session, url)
    if dom is None:
        return []

    stores = []
    li_elements = dom.xpath('//ul[@class="store_list"]/li')

    for li in li_elements:
        name = li.xpath('.//span[@class="store_name"]/text()')
        address = li.xpath('.//span[@class="store_address"][1]/text()')
        distance = li.xpath('.//span[@class="store_address"][2]/text()')

        map_url = extract_onclick_url_from_button(li, "store_bt_google_map_en")
        map_url = map_url.split('@')[0] if '@' in map_url else map_url
        details_url = extract_onclick_url_from_button(li, "bt_details_en")

        stores.append({
            "name": name[0].strip() if name else "",
            "address": address[0].strip() if address else "",
            "distance": distance[0].strip() if distance else "",
            "map_url": "https:" + map_url if map_url.startswith("//") else map_url,
            "details_url": "https://location.am-all.net/alm/" + details_url if details_url.startswith("shop") else details_url
        })

    return stores
