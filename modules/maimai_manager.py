import requests
import random
import logging
import asyncio
import aiohttp
from lxml import etree
from modules.record_manager import get_detailed_info
from modules.rate_limiter import maimai_limiter

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

def _get_random_user_agent():
    """返回随机 User-Agent"""
    return random.choice(USER_AGENTS)


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
            target = [round(base + i * 0.1, 1) for i in range(6, 10)]
            if input_str == "14+":
                target.append(15.0)
            return target
        except ValueError:
            raise ValueError(f"无法解析带加号的整数: {input_str}")

    else:
        try:
            base = int(input_str)
            return [round(base + i * 0.1, 1) for i in range(6)]
        except ValueError:
            raise ValueError(f"无法解析整数: {input_str}")

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

def get_note_score(notes):
    """计算每个 note 类型的扣分比例

    Args:
        notes: 字典，包含各类 note 的数量
            {
                'tap': int,
                'hold': int,
                'slide': int,
                'touch': int,
                'break': int
            }

    Returns:
        字典，包含各类判定的扣分百分比
    """
    tap_num = notes['tap'] if notes['tap'] else 0
    hold_num = notes['hold'] if notes['hold'] else 0
    slide_num = notes['slide'] if notes['slide'] else 0
    touch_num = notes['touch'] if notes['touch'] else 0
    break_num = notes['break'] if notes['break'] else 0

    tap_base = [500, 400, 250]
    hold_base = [1000, 800, 500]
    slide_base = [1500, 1200, 750]
    touch_base = tap_base
    break_base = [2500, 2500, 2500, 2000, 1500, 1250, 1000]
    break_add = [100, 75, 50, 40, 40, 40, 30]

    tap_base_total = tap_num * 500
    hold_base_total = hold_num * 1000
    slide_base_total = slide_num * 1500
    touch_base_total = touch_num * 500
    break_base_total = break_num * 2500
    break_add_total = break_num * 100

    total_base = tap_base_total + hold_base_total + slide_base_total + touch_base_total + break_base_total

    note_score = {
        'tap_great': round((tap_base[0] - tap_base[1]) / total_base * 100, 5),
        'tap_good': round((tap_base[0] - tap_base[2]) / total_base * 100, 5),
        'tap_miss': round(tap_base[0] / total_base * 100, 5),

        'hold_great': round((hold_base[0] - hold_base[1]) / total_base * 100, 5),
        'hold_good': round((hold_base[0] - hold_base[2]) / total_base * 100, 5),
        'hold_miss': round(hold_base[0] / total_base * 100, 5),

        'slide_great': round((slide_base[0] - slide_base[1]) / total_base * 100, 5),
        'slide_good': round((slide_base[0] - slide_base[2]) / total_base * 100, 5),
        'slide_miss': round(slide_base[0] / total_base * 100, 5),

        'touch_great': round((touch_base[0] - touch_base[1]) / total_base * 100, 5),
        'touch_good': round((touch_base[0] - touch_base[2]) / total_base * 100, 5),
        'touch_miss': round(touch_base[0] / total_base * 100, 5),

        'break_high_perfect': round(((break_base[0] - break_base[1]) / total_base * 100) + ((break_add[0] - break_add[1]) / break_add_total), 5),
        'break_low_perfect': round(((break_base[0] - break_base[2]) / total_base * 100) + ((break_add[0] - break_add[2]) / break_add_total), 5),
        'break_high_great': round(((break_base[0] - break_base[3]) / total_base * 100) + ((break_add[0] - break_add[3]) / break_add_total), 5),
        'break_middle_great': round(((break_base[0] - break_base[4]) / total_base * 100) + ((break_add[0] - break_add[4]) / break_add_total), 5),
        'break_low_great': round(((break_base[0] - break_base[5]) / total_base * 100) + ((break_add[0] - break_add[5]) / break_add_total), 5),
        'break_good': round(((break_base[0] - break_base[6]) / total_base * 100) + ((break_add[0] - break_add[6]) / break_add_total), 5),
        'break_miss': round((break_base[0] / total_base * 100) + (break_add[0] / break_add_total), 5)
    }

    return note_score

def calc_score(notes, judgements):
    """根据 note 数量和判定结果计算最终得分

    Args:
        notes: 字典，包含各类 note 的数量
        judgements: 字典，包含各类判定的数量

    Returns:
        float: 计算出的得分（满分101）
    """
    scores = get_note_score(notes)
    total_deduction = 0
    for k, v in judgements.items():
        if k in scores:
            total_deduction += scores[k] * v
    return round(101 - total_deduction, 4)

# ==================== 异步版本函数 ====================

async def fetch_dom(session: aiohttp.ClientSession, url: str, session_id: str, ver="jp") -> etree._Element:
    """异步版本的 fetch_dom，支持并发请求"""
    # 限速保护
    maimai_limiter.wait_if_needed(session_id)

    # 随机 User-Agent
    user_agent = _get_random_user_agent()

    if url.startswith("https://maimaidx-eng.com"):
        headers = {
            "Referer": "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=maimaidxex&redirect_url=https://maimaidx-eng.com/maimai-mobile/&back_url=https://maimai.sega.com/",
            "User-Agent": user_agent,
            "Host": "maimaidx-eng.com"
        }
    else:
        headers = {
            "Referer": "https://maimaidx.jp/maimai-mobile/login/",
            "User-Agent": user_agent,
            "Host": "maimaidx.jp"
        }

    try:
        async with session.get(url, headers=headers, ssl=False) as resp:
            if resp.status == 503:
                logger.warning(f"[Maimai] ⚠ Server maintenance (503): url={url}")
                return "MAINTENANCE"
            resp.raise_for_status()
            html = await resp.text()

            if ("Please agree to the following terms of service before log in." in html or
                "再度ログインしてください" in html):
                return None

            return await asyncio.to_thread(etree.HTML, html)
    except Exception as e:
        logger.error(f"[Maimai] ✗ Fetch failed: url={url}, error={e}")
        return None


async def login_to_maimai(sega_id: str, password: str, ver="jp"):
    """异步版本的 login_to_maimai

    Args:
        sega_id: SEGA ID
        password: 密码
        ver: 版本 (jp/intl)

    Returns:
        dict: cookies 字典，可用于其他异步函数
    """
    # 限速保护
    maimai_limiter.wait_if_needed(f"login_{sega_id}")

    # 随机 User-Agent
    user_agent = _get_random_user_agent()

    # 优化：增加连接池大小
    connector = aiohttp.TCPConnector(ssl=False, limit=10, ttl_dns_cache=300)

    if ver == "intl":
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                async with session.get(
                    "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=maimaidxex&redirect_url=https://maimaidx-eng.com/maimai-mobile/&back_url=https://maimai.sega.com/"
                ) as resp:
                    if resp.status == 503:
                        logger.warning("[Maimai] ⚠ Server maintenance (503): server=INTL")
                        return "MAINTENANCE"
                    resp.raise_for_status()
            except Exception as e:
                logger.error(f"[Maimai] ✗ Failed to access INTL login page: error={e}")
                raise

            # POST 登录
            async with session.post(
                "https://lng-tgk-aime-gw.am-all.net/common_auth/login/sid/",
                data={
                    "sid": sega_id,
                    "password": password,
                    "retention": "1",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                allow_redirects=False
            ) as login_resp:
                redirect_url = login_resp.headers.get("Location")

            # 跟随重定向
            async with session.get(
                redirect_url,
                headers={
                    "Referer": "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=maimaidxex&redirect_url=https://maimaidx-eng.com/maimai-mobile/&back_url=https://maimai.sega.com/",
                    "User-Agent": user_agent,
                    "Host": "maimaidx-eng.com"
                },
                allow_redirects=True
            ) as final_resp:
                pass

            return session.cookie_jar.filter_cookies("https://maimaidx-eng.com")

    else:  # jp
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                async with session.get("https://maimaidx.jp/maimai-mobile/login/") as response:
                    if response.status == 503:
                        logger.warning("[Maimai] ⚠ Server maintenance (503): server=JP")
                        return "MAINTENANCE"
                    response.raise_for_status()
                    html = await response.text()
            except Exception as e:
                logger.error(f"[Maimai] ✗ Failed to access JP login page: error={e}")
                raise

            # 异步解析 HTML 获取 token
            dom = await asyncio.to_thread(etree.HTML, html)
            token_list = dom.xpath('//input[@name="token"]/@value')
            if not token_list:
                raise Exception("Unable to fetch login token")
            token = token_list[0]

            # POST 登录
            async with session.post(
                "https://maimaidx.jp/maimai-mobile/submit/",
                data={
                    "segaId": sega_id,
                    "password": password,
                    "save_cookie": "on",
                    "token": token
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                allow_redirects=True
            ) as login_response:
                pass

            # 选择 AIME 卡
            async with session.get("https://maimaidx.jp/maimai-mobile/aimeList/submit/?idx=0") as aime_choose:
                pass

            return session.cookie_jar.filter_cookies("https://maimaidx.jp")


async def get_maimai_info(cookies: dict, ver="jp"):
    """异步版本的 get_maimai_info，4个页面并发请求

    Args:
        cookies: 登录后的 cookies 字典
        ver: 版本 (jp/intl)

    Returns:
        dict: 用户信息
    """
    base = "https://maimaidx-eng.com/maimai-mobile" if ver == "intl" else "https://maimaidx.jp/maimai-mobile"
    session_id = id(cookies)

    # 优化：增加连接池大小
    connector = aiohttp.TCPConnector(ssl=False, limit=20, ttl_dns_cache=300)
    async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
        # 并发请求所有页面
        urls = [
            f"{base}/playerData/",
            f"{base}/collection/",
            f"{base}/collection/nameplate/",
            f"{base}/collection/trophy/"
        ]

        tasks = [fetch_dom(session, url, session_id, ver) for url in urls]
        doms = await asyncio.gather(*tasks)

        # 检查维护状态
        for dom in doms:
            if dom == "MAINTENANCE":
                return {"error": "MAINTENANCE"}
            if dom is None:
                return {}

        player_dom, collection_dom, nameplate_dom, trophy_dom = doms

        # 解析主信息
        user_name = player_dom.xpath('//div[contains(@class, "name_block")]/text()')
        rating_block_url = player_dom.xpath('//img[contains(@class, "h_30") and contains(@class, "f_r")]/@src')
        rating = player_dom.xpath('//div[@class="rating_block"]/text()')
        cource_rank_url = player_dom.xpath('//img[contains(@class, "h_35") and contains(@class, "f_l")]/@src')
        class_rank_url = player_dom.xpath('//img[contains(@class, "p_l_10") and contains(@class, "h_35") and contains(@class, "f_l")]/@src')

        # 头像
        icon_url = collection_dom.xpath('//img[contains(@class, "w_80") and contains(@class, "m_r_10") and contains(@class, "f_l")]/@src')

        # 姓名框
        nameplate_url = nameplate_dom.xpath('//img[contains(@class, "w_396") and contains(@class, "m_r_10")]/@src')

        # 称号
        trophy_type_block = trophy_dom.xpath('//div[contains(@class, "block_info") and contains(@class, "f_11") and contains(@class, "orange")]/text()')
        trophy_type = trophy_type_block[0].strip().lower() if trophy_type_block else "rainbow"
        trophy_type = "rainbow" if trophy_type == "ランダム" else trophy_type
        trophy_blocks = trophy_dom.xpath('//div[contains(@class, "trophy_inner_block") and contains(@class, "f_13")]')
        if trophy_blocks:
            trophy_block = trophy_blocks[0]
            trophy_texts = trophy_block.xpath('.//text()')
            trophy_content = trophy_texts[1] if len(trophy_texts) > 1 else "ERROR"
        else:
            trophy_content = "ERROR"

        user_info = {
            "name": user_name[0] if user_name else "NAME_ERROR",
            "rating_block_url": rating_block_url[0] if rating_block_url else "N/A",
            "rating": rating[0].strip() if rating else "ERROR",
            "cource_rank_url": cource_rank_url[0] if cource_rank_url else "N/A",
            "class_rank_url": class_rank_url[0] if class_rank_url else "N/A",
            "icon_url": icon_url[0] if icon_url else "N/A",
            "nameplate_url": nameplate_url[0] if nameplate_url else "N/A",
            "trophy_url": f"https://maimaidx.jp/maimai-mobile/img/trophy_{trophy_type}.png",
            "trophy_content": trophy_content if trophy_content else "N/A"
        }

        return user_info

async def get_maimai_records(cookies: dict, ver="jp"):
    """异步版本的 get_maimai_records，5个难度并发请求

    Args:
        cookies: 登录后的 cookies 字典
        ver: 版本 (jp/intl)

    Returns:
        list: 成绩记录列表
    """
    base = "https://maimaidx-eng.com/maimai-mobile" if ver == "intl" else "https://maimaidx.jp/maimai-mobile"
    difficulty = ['basic', 'advanced', 'expert', 'master', 'remaster']

    session_id = id(cookies)  # 使用 cookies 对象 id 作为限速键

    # 优化：增加连接池大小
    connector = aiohttp.TCPConnector(ssl=False, limit=20, ttl_dns_cache=300)
    async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
        # 并发请求所有难度
        tasks = []
        for page_num in range(5):
            url = f"{base}/record/musicGenre/search/?genre=99&diff={page_num}"
            tasks.append(fetch_dom(session, url, session_id, ver))

        doms = await asyncio.gather(*tasks)

        # 解析结果
        music_record = []
        for page_num, dom in enumerate(doms):
            if dom is None:
                return []
            if dom == "MAINTENANCE":
                return "MAINTENANCE"

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

                type_icon = block.xpath('.//img[contains(@class, "music_kind_icon")]/@src')
                if type_icon:
                    if "standard.png" in type_icon[0]:
                        type = "std"
                    elif "dx.png" in type_icon[0]:
                        type = "dx"
                    else:
                        type = "N/A"
                else:
                    type = "N/A"

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
                    "type": type,
                    "score": score,
                    "dx_score": dx_score,
                    "score_icon": score_icon,
                    "combo_icon": combo_icon,
                    "sync_icon": sync_icon
                })

        return music_record


async def get_recent_records(cookies: dict, ver="jp"):
    """异步版本的 get_recent_records

    Args:
        cookies: 登录后的 cookies 字典
        ver: 版本 (jp/intl)

    Returns:
        list: 最近游戏记录
    """
    base = "https://maimaidx-eng.com/maimai-mobile" if ver == "intl" else "https://maimaidx.jp/maimai-mobile"
    session_id = id(cookies)

    # 优化：增加连接池大小
    connector = aiohttp.TCPConnector(ssl=False, limit=10, ttl_dns_cache=300)
    async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
        url = f"{base}/record/"
        dom = await fetch_dom(session, url, session_id, ver)

        if dom is None:
            return []
        if dom == "MAINTENANCE":
            return "MAINTENANCE"

        recent_record = []
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

                type_icon = block.xpath('.//img[contains(@class, "playlog_music_kind_icon")]/@src')
                if type_icon:
                    if "standard.png" in type_icon[0]:
                        type = "std"
                    elif "dx.png" in type_icon[0]:
                        type = "dx"
                    else:
                        type = "N/A"
                else:
                    type = "utage"

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
                    "type": type,
                    "score": score,
                    "dx_score": dx_score,
                    "score_icon": score_icon.replace("plus", "p"),
                    "combo_icon": combo_icon.replace("plus", "p"),
                    "sync_icon": sync_icon.replace("fsd", "fdx").replace("plus", "p")
                })

        return recent_record


async def get_friends_list(cookies: dict, ver="jp"):
    """异步版本的 get_friends_list

    Args:
        cookies: 登录后的 cookies 字典
        ver: 版本 (jp/intl)

    Returns:
        list: 好友列表
    """
    base = "https://maimaidx-eng.com/maimai-mobile" if ver == "intl" else "https://maimaidx.jp/maimai-mobile"
    session_id = id(cookies)

    # 优化：增加连接池大小
    connector = aiohttp.TCPConnector(ssl=False, limit=10, ttl_dns_cache=300)
    async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
        tasks = []
        url = f"{base}/friend/"
        tasks.append(fetch_dom(session, url, session_id, ver))
        url = f"{base}/friend/pages/?idx=2&type=0"
        tasks.append(fetch_dom(session, url, session_id, ver))
        
        doms = await asyncio.gather(*tasks)

        friends = []
        blocks = []
        for dom in doms:
            if dom is None:
                return []
            if dom == "MAINTENANCE":
                return "MAINTENANCE"

            blocks.extend(dom.xpath('//div[contains(@class, "see_through_block")]'))

        if not blocks:
            return []

        for block in blocks:
            try:
                name = block.xpath('.//div[@class="name_block t_l f_l f_16 underline"]/text()')[0].strip()
                rating = block.xpath('.//div[@class="rating_block"]/text()')[0].strip()
                friend_id = block.xpath('.//form/input[@name="idx"]/@value')[0].strip()
                is_favorite = bool(
                    block.xpath(f'.//form[@action="{base}/friend/favoriteOff/"]')
                )

                if is_favorite:
                    friends.append({
                        "name": name,
                        "rating": rating,
                        "friend_id": friend_id,
                    })

            except Exception as e:
                logger.error(f"[Maimai] ✗ Failed to parse friend list block: error={e}")
                return []

        seen = set()
        new_list = []

        for friend in friends:
            friend_id = friend["friend_id"]
            if friend_id not in seen:
                seen.add(friend_id)
                new_list.append(friend)

        friends = new_list

        return friends


async def get_friend_info(cookies: dict, friend_id: str, ver="jp"):
    """异步版本的 get_friend_info，4个页面并发请求

    Args:
        cookies: 登录后的 cookies 字典
        friend_id: 好友码
        ver: 版本 (jp/intl)

    Returns:
        dict: 好友信息
    """
    base = "https://maimaidx-eng.com/maimai-mobile" if ver == "intl" else "https://maimaidx.jp/maimai-mobile"
    session_id = id(cookies)

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
        # 并发请求所有页面
        url = f"{base}/friend/search/searchUser/?friendCode={friend_id}"
        dom = await fetch_dom(session, url, session_id, ver)

        # 检查维护状态
        if dom == "MAINTENANCE":
            return {"error": "MAINTENANCE"}
        if dom is None:
            return {}

        # 解析主信息
        user_name = dom.xpath('//div[contains(@class, "name_block")]/text()')
        rating_block_url = dom.xpath('//img[contains(@class, "h_30") and contains(@class, "f_r")]/@src')
        rating = dom.xpath('//div[@class="rating_block"]/text()')
        cource_rank_url = dom.xpath('//img[contains(@class, "h_35") and contains(@class, "f_l")]/@src')
        class_rank_url = dom.xpath('//img[contains(@class, "p_l_10") and contains(@class, "h_35") and contains(@class, "f_l")]/@src')

        # 头像
        icon_url = dom.xpath('//img[contains(@class, "w_112") and contains(@class, "f_l")]/@src')

        # 姓名框
        nameplate_list = [
            "41ef54f2f141e1fd",
            "f2b6b6808777400c",
            "a42d03bf82bb3eea",
            "85b6d4655374b56c",
            "427ce8b2e50e01c9",
            "331811d4769c6c1a",
            "af79c8fed1d26394",
            "809c981f807b3596"
        ]
        nameplate_name = random.choice(nameplate_list)
        nameplate_url = f"https://maimaidx.jp/maimai-mobile/img/NamePlate/{nameplate_name}.png"

        # 称号
        trophy_classes = dom.xpath('//div[contains(@class, "trophy_block")]/@class')[0]
        trophy_type = [c for c in trophy_classes.split() if c.startswith('trophy_') and c != 'trophy_block'][0]
        trophy_type = trophy_type.replace('trophy_', '').lower()
        trophy_blocks = dom.xpath('//div[contains(@class, "trophy_inner_block") and contains(@class, "f_13")]')
        if trophy_blocks:
            trophy_block = trophy_blocks[0]
            trophy_texts = trophy_block.xpath('.//text()')
            trophy_content = trophy_texts[1] if len(trophy_texts) > 1 else "ERROR"
        else:
            trophy_content = "ERROR"

        friend_info = {
            "name": user_name[0].strip() if user_name else "NAME_ERROR",
            "rating_block_url": rating_block_url[0] if rating_block_url else "https://maimaidx.jp/maimai-mobile/img/rating_base_rainbow.png",
            "rating": rating[0].strip() if rating else "17000",
            "cource_rank_url": cource_rank_url[0] if cource_rank_url else "https://maimaidx.jp/maimai-mobile/img/course/course_rank_13KOI1uBwE.png",
            "class_rank_url": class_rank_url[0] if class_rank_url else "https://maimaidx.jp/maimai-mobile/img/class/class_rank_s_01VFe8gl5z.png",
            "icon_url": icon_url[0] if icon_url else "https://maimaidx.jp/maimai-mobile/img/Icon/c22d52b387e3f829.png",
            "nameplate_url": nameplate_url,
            "trophy_url": f"https://maimaidx.jp/maimai-mobile/img/trophy_{trophy_type}.png",
            "trophy_content": trophy_content.strip() if trophy_content else "TROPHY_ERROR"
        }

        return friend_info

async def get_friend_records(cookies: dict, friend_id: str, ver="jp"):
    """异步版本的 get_friend_records，5个难度并发请求

    Args:
        cookies: 登录后的 cookies 字典
        friend_id: 好友码
        ver: 版本 (jp/intl)

    Returns:
        list or str: 好友成绩列表，维护时返回 "MAINTENANCE"
    """
    base = "https://maimaidx-eng.com/maimai-mobile" if ver == "intl" else "https://maimaidx.jp/maimai-mobile"
    difficulty = ['basic', 'advanced', 'expert', 'master', 'remaster']
    session_id = id(cookies)


    kaomoji = [
        "(´･ω･)",
        "(つ≧▽≦)つ",
        "(・∀・)",
        "( ﾟДﾟ)",
        "(∩^o^)⊃"
    ]

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
        # 并发请求所有难度
        tasks = []
        for diff in range(5):
            url = f"{base}/friend/friendGenreVs/battleStart/?scoreType=2&genre=99&diff={diff}&idx={friend_id}"
            tasks.append(fetch_dom(session, url, session_id, ver))

        doms = await asyncio.gather(*tasks)

        # 解析成绩
        friend_records = []
        for diff, dom in enumerate(doms):
            if dom is None:
                continue
            if dom == "MAINTENANCE":
                return "MAINTENANCE"

            blocks = dom.xpath(f'//div[contains(@class, "music_{difficulty[diff]}_score_back")]')

            for block in blocks:
                try:
                    name_node = block.xpath('.//div[contains(@class, "music_name_block")]/text()')
                    if not name_node:
                        continue
                    name = name_node[0].strip()

                    score_cells = block.xpath(f'.//td[contains(@class, "{difficulty[diff]}_score_label")]/text()')
                    if len(score_cells) <= 1:
                        continue
                    score = score_cells[1].strip()
                    if score in ("― %", "- %"):
                        continue

                    type_img = block.xpath('.//img[contains(@class, "music_kind_icon")]/@src')
                    if type_img:
                        if "standard.png" in type_img[0]:
                            type = "std"
                        elif "dx.png" in type_img[0]:
                            type = "dx"
                        else:
                            type = "N/A"
                    else:
                        type = "N/A"

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

                    friend_records.append({
                        "name": name,
                        "difficulty": difficulty[diff],
                        "type": type,
                        "score": score,
                        "dx_score": random.choice(kaomoji),
                        "score_icon": score_icon,
                        "combo_icon": combo_icon,
                        "sync_icon": sync_icon
                    })

                except Exception as e:
                    logger.error(f"[Maimai] ✗ Failed to parse friend record block: error={e}")

        return friend_records


async def get_nearby_maimai_stores(lat, lng, ver="jp"):
    """异步版本的 get_nearby_maimai_stores

    Args:
        lat: 纬度
        lng: 经度
        ver: 版本 (jp/intl)

    Returns:
        list: 店铺列表
    """
    version_num = "98" if ver == "intl" else "96"
    url = f"https://location.am-all.net/alm/location?gm={version_num}&lat={lat}&lng={lng}"

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        session_id = id(session)
        dom = await fetch_dom(session, url, session_id, ver)

        if dom is None:
            return []
        if dom == "MAINTENANCE":
            return "MAINTENANCE"

        stores = []
        li_elements = dom.xpath('//ul[@class="store_list"]/li')

        for li in li_elements:
            name = li.xpath('.//span[@class="store_name"]/text()')
            address = li.xpath('.//span[@class="store_address"][1]/text()')
            distance = li.xpath('.//span[@class="store_address"][2]/text()')

            map_url = extract_onclick_url_from_button(li, "store_bt_google_map_en")
            map_url = map_url.split('@')[0] if '@' in map_url else map_url
            details_url = extract_onclick_url_from_button(li, "bt_details_en")

            # 确保 map_url 是有效的 URL
            if map_url:
                if map_url.startswith("//"):
                    map_url = "https:" + map_url
                elif not map_url.startswith("http"):
                    map_url = ""

            # 确保 details_url 是有效的 URL
            if details_url:
                if details_url.startswith("shop"):
                    details_url = "https://location.am-all.net/alm/" + details_url
                elif not details_url.startswith("http"):
                    details_url = ""

            stores.append({
                "name": name[0].strip() if name else "",
                "address": address[0].strip() if address else "",
                "distance": distance[0].strip() if distance else "",
                "map_url": map_url,
                "details_url": details_url
            })

        return stores
