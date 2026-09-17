import random
from contextlib import asynccontextmanager
import logging
import asyncio
import aiohttp
import unicodedata
import re
from urllib.parse import quote, urlencode
from lxml import etree
import os
from modules.config_loader import DOMAIN, RATING_DIR

logger = logging.getLogger(__name__)


def _mobile_base(version):
    host = "maimaidx-eng.com" if version == "intl" else "maimaidx.jp"
    return f"https://{host}/maimai-mobile"


def _create_session(cookies=None, limit=10, *, timeout=None):
    connector = aiohttp.TCPConnector(ssl=False, limit=limit, ttl_dns_cache=300)
    return aiohttp.ClientSession(cookies=cookies, connector=connector, timeout=timeout)


# Rating → 本地图片映射
RATING_TIERS = [
    (16750, "rainbow_extreme_4.png"),
    (16500, "rainbow_extreme_3.png"),
    (16250, "rainbow_extreme_2.png"),
    (16000, "rainbow_extreme_1.png"),
    (15750, "rainbow_4.png"),
    (15500, "rainbow_3.png"),
    (15250, "rainbow_2.png"),
    (15000, "rainbow_1.png"),
    (14750, "platinum_2.png"),
    (14500, "platinum_1.png"),
    (14250, "gold_2.png"),
    (14000, "gold_1.png"),
    (13000, "silver.png"),
    (12000, "bronze.png"),
    (10000, "purple.png"),
    (7000,  "red.png"),
    (4000,  "yellow.png"),
    (2000,  "green.png"),
    (1000,  "blue.png"),
    (0,     "white.png"),
]


def get_rating_image_path(rating: int) -> str:
    for threshold, filename in RATING_TIERS:
        if rating >= threshold:
            return os.path.join(RATING_DIR, filename)
    return os.path.join(RATING_DIR, "white.png")


def _static_asset_url(path):
    if not path:
        return ""

    normalized_path = os.path.normpath(str(path))
    assets_marker = f"{os.sep}assets{os.sep}"
    if assets_marker in normalized_path:
        return "/static/" + normalized_path.split(assets_marker, 1)[1].replace(os.sep, "/")
    if normalized_path.startswith(f"assets{os.sep}"):
        return "/static/" + normalized_path[len(f"assets{os.sep}"):].replace(os.sep, "/")
    return ""


def _rating_block_static_url(rating):
    try:
        rating_int = int(str(rating or "0").strip())
    except ValueError:
        rating_int = 0
    return _static_asset_url(get_rating_image_path(rating_int))

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

def normalize(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u3000", " ").replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def _get_random_user_agent():
    """返回随机 User-Agent"""
    return random.choice(USER_AGENTS)


def _jp_login_headers(user_agent):
    return {
        "User-Agent": user_agent,
        "Referer": "https://maimaidx.jp/maimai-mobile/login/",
        "Origin": "https://maimaidx.jp",
        "Host": "maimaidx.jp",
    }


def _describe_jp_login_page(html):
    if not html:
        return "empty"
    if "再度ログインしてください" in html:
        return "relogin"
    if "Please agree to the following terms of service before log in." in html:
        return "tos"
    if 'name="segaId"' in html and 'name="password"' in html:
        return "login_form_without_token"
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if title_match:
        return normalize(title_match.group(1))
    return "unknown"


def _extract_jp_login_token(session, html, dom=None):
    if dom is not None:
        token_list = dom.xpath('//input[@name="token"]/@value')
        if token_list and token_list[0]:
            return token_list[0], "input"

    token_match = re.search(
        r'<input\b(?=[^>]*\bname=["\']token["\'])(?=[^>]*\bvalue=["\']([^"\']+)["\'])[^>]*>',
        html or "",
        re.IGNORECASE,
    )
    if token_match:
        return token_match.group(1), "regex"

    cookies = session.cookie_jar.filter_cookies("https://maimaidx.jp")
    cookie = cookies.get("_t")
    token_cookie = getattr(cookie, "value", str(cookie)).strip() if cookie is not None else ""
    if re.fullmatch(r"[0-9a-fA-F]{16,64}", token_cookie or ""):
        return token_cookie, "cookie"

    return None, None


@asynccontextmanager
async def _jp_login_session(headers):
    """Keep the successful token's session; discard failed sessions before retrying."""
    last_status = None
    last_page = "unknown"
    for attempt in range(3):
        async with _create_session(timeout=aiohttp.ClientTimeout(total=15, connect=5)) as session:
            token = None
            try:
                async with session.get(
                    "https://maimaidx.jp/maimai-mobile/login/",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15, connect=5),
                ) as response:
                    last_status = response.status
                    if response.status == 503:
                        token = "MAINTENANCE"
                        logger.warning("[Maimai] ⚠ Server maintenance (503): server=JP")
                    else:
                        response.raise_for_status()
                        html = await response.text()
                        dom = await asyncio.to_thread(etree.HTML, html)
                        token, source = _extract_jp_login_token(session, html, dom)
                        last_page = _describe_jp_login_page(html)
                        if token and attempt:
                            logger.info(
                                "[Maimai] ✓ JP login token recovered: attempt=%s, source=%s",
                                attempt + 1, source,
                            )
                        elif not token:
                            logger.warning(
                                "[Maimai] ⚠ JP login token missing: attempt=%s/3, "
                                "status=%s, html_len=%s, page=%s; discarding session",
                                attempt + 1, last_status, len(html or ""), last_page,
                            )
            except Exception as exc:
                last_page = type(exc).__name__
                logger.warning(
                    "[Maimai] ⚠ JP login page fetch failed: attempt=%s/3, "
                    "error=%s; discarding session", attempt + 1, last_page,
                )

            # Do not catch exceptions from the caller's POST/Aime requests:
            # they must not restart authentication or yield a second time.
            if token:
                yield session, token
                return

        # The old cookies and connector are closed before another attempt.
        if attempt < 2:
            await asyncio.sleep(1.5)

    raise RuntimeError(
        "Unable to fetch JP login token after 3 fresh sessions "
        f"(last_status={last_status}, last_page={last_page})"
    )


def parse_level_value(input_str):
    input_str = input_str.strip()

    if '.' in input_str:
        try:
            return [float(input_str)]
        except ValueError:
            logger.error(f"[Maimai] ✗ Failed to parse a float number with point(.): {input_str}")
            return None

    elif input_str.endswith('+'):
        try:
            base = int(input_str[:-1])
            target = [round(base + i * 0.1, 1) for i in range(6, 10)]
            return target
        except ValueError:
            logger.error(f"[Maimai] ✗ Failed to parse a number with plus(+): {input_str}")
            return None

    else:
        try:
            base = int(input_str)
            return [round(base + i * 0.1, 1) for i in range(6)]
        except ValueError:
            logger.error(f"[Maimai] ✗ Failed to parse a number: {input_str}")
            return None

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

# ==================== Maimai 函数 ====================

async def fetch_dom(session: aiohttp.ClientSession, url: str, ver="jp") -> etree._Element:
    """异步版本的 fetch_dom，支持并发请求"""
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


async def login_to_maimai(sega_id: str, password: str, ver="jp", aime=0):
    """异步版本的 login_to_maimai

    Args:
        sega_id: SEGA ID
        password: 密码
        ver: 版本 (jp/intl)

    Returns:
        dict: cookies 字典，可用于其他异步函数
    """
    # 随机 User-Agent
    user_agent = _get_random_user_agent()

    if ver == "intl":
        async with _create_session() as session:
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
                "https://lng-tgk-aime-gw.am-all.net/common_auth/login/sid",
                data={
                    "sid": sega_id,
                    "password": password,
                    "retention": "1",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                allow_redirects=False
            ) as login_resp:
                redirect_url = login_resp.headers.get("Location")

            # 检查重定向 URL
            if not redirect_url:
                logger.error(f"[Maimai] ✗ Login failed: no redirect URL, server=INTL, sega_id={sega_id}")
                return None

            # 跟随重定向
            async with session.get(
                redirect_url,
                headers={
                    "Referer": "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=maimaidxex&redirect_url=https://maimaidx-eng.com/maimai-mobile/&back_url=https://maimai.sega.com/",
                    "User-Agent": user_agent,
                    "Host": "maimaidx-eng.com"
                },
                allow_redirects=True
            ):
                pass

            return session.cookie_jar.filter_cookies("https://maimaidx-eng.com")

    else:  # jp
        headers = _jp_login_headers(user_agent)
        async with _jp_login_session(headers) as (session, token):
            if token == "MAINTENANCE":
                return "MAINTENANCE"

            # POST 登录
            async with session.post(
                "https://maimaidx.jp/maimai-mobile/submit/",
                data={
                    "segaId": sega_id,
                    "password": password,
                    "save_cookie": "on",
                    "token": token
                },
                headers={
                    **headers,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                allow_redirects=True
            ):
                pass

            # 选择 AIME 卡
            async with session.get(
                f"https://maimaidx.jp/maimai-mobile/aimeList/submit/?idx={aime}",
                headers=headers,
            ):
                pass

            return session.cookie_jar.filter_cookies("https://maimaidx.jp")


def _parse_aime_candidates(dom):
    candidates = []
    seen = set()
    idx_inputs = dom.xpath('//form[contains(@action, "/aimeList/submit/")]//input[@name="idx"]')

    for idx_input in idx_inputs:
        idx_values = idx_input.xpath('./@value')
        if not idx_values:
            continue

        idx = idx_values[0].strip()
        if idx in seen:
            continue
        seen.add(idx)

        form = idx_input.getparent()
        while form is not None and form.tag != "form":
            form = form.getparent()

        container = form or idx_input
        for ancestor in container.iterancestors():
            if ancestor.xpath('.//div[contains(concat(" ", normalize-space(@class), " "), " name_block ")]'):
                container = ancestor
                break

        name_values = container.xpath('.//div[contains(concat(" ", normalize-space(@class), " "), " name_block ")]/text()')
        rating_values = container.xpath('.//div[contains(concat(" ", normalize-space(@class), " "), " rating_block ")]/text()')
        trophy_values = container.xpath('.//div[contains(@class, "trophy_inner_block")]//span/text()')
        icon_values = container.xpath('.//img[contains(@src, "/img/Icon/")]/@src')
        course_rank_values = container.xpath('.//img[contains(@src, "/img/course/course_rank_")]/@src')
        class_rank_values = container.xpath('.//img[contains(@src, "/img/class/class_rank_")]/@src')
        trophy_block_classes = container.xpath('.//div[contains(concat(" ", normalize-space(@class), " "), " trophy_block ")]/@class')

        name = normalize(name_values[0]) if name_values else ""
        rating = normalize(rating_values[0]) if rating_values else ""
        trophy = normalize(trophy_values[0]) if trophy_values else ""
        icon_url = icon_values[0] if icon_values else ""
        if icon_url.startswith("/"):
            icon_url = f"https://maimaidx.jp{icon_url}"
        elif icon_url.startswith("img/"):
            icon_url = f"https://maimaidx.jp/maimai-mobile/{icon_url}"

        course_rank_url = course_rank_values[0] if course_rank_values else ""
        if course_rank_url.startswith("/"):
            course_rank_url = f"https://maimaidx.jp{course_rank_url}"
        elif course_rank_url.startswith("img/"):
            course_rank_url = f"https://maimaidx.jp/maimai-mobile/{course_rank_url}"

        class_rank_url = class_rank_values[0] if class_rank_values else ""
        if class_rank_url.startswith("/"):
            class_rank_url = f"https://maimaidx.jp{class_rank_url}"
        elif class_rank_url.startswith("img/"):
            class_rank_url = f"https://maimaidx.jp/maimai-mobile/{class_rank_url}"

        trophy_type = ""
        for class_name in trophy_block_classes:
            for part in class_name.split():
                if part.startswith("trophy_") and part != "trophy_block":
                    trophy_type = part.replace("trophy_", "", 1).lower()
                    break
            if trophy_type:
                break
        trophy_url = f"https://maimaidx.jp/maimai-mobile/img/trophy_{trophy_type}.png" if trophy_type else ""

        try:
            idx_label = int(idx) + 1
        except ValueError:
            idx_label = idx

        candidates.append({
            "idx": idx,
            "name": name or f"Aime {idx_label}",
            "rating": rating,
            "trophy": trophy,
            "icon_url": icon_url,
            "rating_block_url": _rating_block_static_url(rating),
            "trophy_url": trophy_url,
            "course_rank_url": course_rank_url,
            "class_rank_url": class_rank_url,
        })

    return candidates


async def get_aime_candidates(sega_id: str, password: str, ver="jp"):
    """Return selectable Aime/account candidates after validating SEGA login."""
    if ver == "intl":
        cookies = await login_to_maimai(sega_id, password, ver="intl", aime=0)
        if cookies == "MAINTENANCE":
            return "MAINTENANCE"
        if not cookies:
            return None

        user_info = await get_maimai_info(cookies, ver="intl")
        if not isinstance(user_info, dict):
            return None
        if user_info.get("error") == "MAINTENANCE":
            return "MAINTENANCE"
        if not user_info:
            return None

        return [{
            "idx": "0",
            "name": user_info.get("name") or "International Account",
            "rating": user_info.get("rating") or "",
            "trophy": user_info.get("trophy_content") or "",
            "icon_url": user_info.get("icon_url") or "",
            "rating_block_url": _rating_block_static_url(user_info.get("rating")),
            "trophy_url": user_info.get("trophy_url") or "",
            "course_rank_url": user_info.get("cource_rank_url") or "",
            "class_rank_url": user_info.get("class_rank_url") or "",
        }]

    user_agent = _get_random_user_agent()
    headers = _jp_login_headers(user_agent)
    async with _jp_login_session(headers) as (session, token):
        if token == "MAINTENANCE":
            return "MAINTENANCE"

        async with session.post(
            "https://maimaidx.jp/maimai-mobile/submit/",
            data={
                "segaId": sega_id,
                "password": password,
                "save_cookie": "on",
                "token": token
            },
            headers={
                **headers,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            allow_redirects=True
        ) as login_response:
            if login_response.status == 503:
                logger.warning("[Maimai] ⚠ Server maintenance (503): server=JP")
                return "MAINTENANCE"
            await login_response.text()

        async with session.get(
            "https://maimaidx.jp/maimai-mobile/aimeList/",
            headers=headers
        ) as response:
            if response.status == 503:
                logger.warning("[Maimai] ⚠ Server maintenance (503): server=JP")
                return "MAINTENANCE"
            response.raise_for_status()
            html = await response.text()

        if "再度ログインしてください" in html:
            return None

        dom = await asyncio.to_thread(etree.HTML, html)
        if dom is None:
            return None
        candidates = _parse_aime_candidates(dom)
        return candidates or None


async def get_maimai_info(cookies: dict, ver="jp"):
    """异步版本的 get_maimai_info，4个页面并发请求

    Args:
        cookies: 登录后的 cookies 字典
        ver: 版本 (jp/intl)

    Returns:
        dict: 用户信息
    """
    base = _mobile_base(ver)
    async with _create_session(cookies, limit=20) as session:
        # 并发请求所有页面
        urls = [
            f"{base}/playerData/",
            f"{base}/collection/",
            f"{base}/collection/nameplate/",
            f"{base}/collection/trophy/"
        ]

        tasks = [fetch_dom(session, url, ver) for url in urls]
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
        # rating_block_url = player_dom.xpath('//img[contains(@class, "h_30") and contains(@class, "f_r")]/@src')
        rating = player_dom.xpath('//div[@class="rating_block"]/text()')
        cource_rank_url = player_dom.xpath('//img[contains(@class, "h_35") and contains(@class, "f_l")]/@src')
        class_rank_url = player_dom.xpath('//img[contains(@class, "w_160") and contains(@class, "p_15") and contains(@class, "m_r_10")]/@src')

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

        # 根据 rating 数值选择本地 rating block 图片
        rating_str = rating[0].strip() if rating else "0"
        try:
            rating_int = int(rating_str)
        except ValueError:
            rating_int = 0
        rating_block_path = get_rating_image_path(rating_int)

        user_info = {
            "name": user_name[0] if user_name else "NAME_ERROR",
            "rating_block_path": rating_block_path,
            "rating": rating_str,
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
    base = _mobile_base(ver)
    difficulty = ['basic', 'advanced', 'expert', 'master', 'remaster']

    async with _create_session(cookies, limit=20) as session:
        # 并发请求所有难度
        tasks = []
        for page_num in range(5):
            url = f"{base}/record/musicGenre/search/?genre=99&diff={page_num}"
            tasks.append(fetch_dom(session, url, ver))

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
                    "dx_score": dx_score.replace(",", ""),
                    "score_icon": score_icon,
                    "combo_icon": combo_icon,
                    "sync_icon": sync_icon
                })

        return music_record


def parse_music_level_options(dom):
    """Read displayed levels and their opaque search values from the official form."""
    if dom is None or isinstance(dom, str):
        raise RuntimeError("Music level page unavailable (login expired or maintenance)")
    if 'too many access' in ''.join(dom.itertext()).lower():
        raise RuntimeError('Official site rate limit: please try again later')
    options = {}
    for option in dom.xpath('//select[@name="level"]/option'):
        label = normalize(''.join(option.itertext()))
        label = re.sub(r'^(?:LEVEL|Lv\.?)\s*', '', label, flags=re.I)
        value = option.get('value', '')
        if re.fullmatch(r'\d{1,2}\+?', label) and value:
            if label in options:
                raise RuntimeError(f"Duplicate music level option: {label}")
            options[label] = value
    if not options:
        raise RuntimeError("Music level selector missing; login expired or page structure changed")
    return options


def parse_music_level_records(dom, level):
    """Preserve DOM order, including charts without a played score."""
    options = parse_music_level_options(dom)
    if level not in options:
        raise RuntimeError(f"Music level {level} missing from response")
    selected = dom.xpath('//select[@name="level"]/option[@selected]/@value')
    if selected and selected != [options[level]]:
        raise RuntimeError(f"Server returned a different music level than {level}")
    rows = _parse_music_chart_blocks(dom)
    for row in rows:
        row['level'] = level
    return rows


def _parse_music_chart_blocks(dom):
    """Common markup shared by official level and version result pages."""
    rows = []
    for name in dom.xpath('//div[contains(concat(" ", normalize-space(@class), " "), " music_name_block ")]'):
        block = next((parent for parent in name.iterancestors()
                      if re.search(r'music_(?:basic|advanced|expert|master|remaster)_score_back',
                                   parent.get('class', ''))), None)
        if block is None:
            raise RuntimeError("Cannot identify chart difficulty on music level page")
        difficulty = re.search(r'music_(basic|advanced|expert|master|remaster)_score_back',
                               block.get('class')).group(1)
        icons = block.xpath('.//img[contains(@class, "music_kind_icon")]/@src')
        chart_type = next((kind for suffix, kind in [('standard.png', 'std'), ('dx.png', 'dx')]
                           if any(src.split('?')[0].endswith(suffix) for src in icons)), None)
        raw_title = ''.join(name.itertext())
        # The official song named U+3000 is intentionally blank.
        title = normalize(raw_title) or ('\u3000' if raw_title == '\u3000' else '')
        if not chart_type or not title:
            raise RuntimeError("Cannot identify chart title/type on music level page")
        rows.append({'position': len(rows) + 1, 'title': title,
                     'type': chart_type, 'difficulty': difficulty})
        labels = block.xpath('.//div[contains(@class, "music_lv_block")]')
        if labels:
            rows[-1]['level'] = normalize(''.join(labels[0].itertext()))
    # An empty result must never silently pass a data audit.
    if not rows:
        raise RuntimeError("No charts parsed; check filters/page structure")
    # Distinct songs can share title/type/difficulty (e.g. the two STD Links).
    # Preserve both positions; auditing skips ambiguous matches.
    return rows


async def get_music_level_lists(cookies: dict, levels=None, ver="jp"):
    """Fetch regional level lists sequentially; fail instead of returning partial results.

    ``levels`` contains display labels, e.g. ['13', '13+']; checks start at 12.
    Search values are discovered rather than assuming labels equal URL values.
    """
    if ver not in ('jp', 'intl'):
        raise ValueError('ver must be jp or intl')
    base = f"{_mobile_base(ver)}/record/musicLevel/"
    async with _create_session(cookies, limit=1,
                               timeout=aiohttp.ClientTimeout(total=30, connect=10)) as session:
        options = parse_music_level_options(await fetch_dom(session, base, ver))
        requested = list(dict.fromkeys(str(level) for level in levels)) if levels is not None else list(options)
        if not requested or any(level not in options for level in requested):
            raise ValueError(f"Choose levels from: {', '.join(options)}")
        requested = [level for level in requested if int(level.rstrip('+')) >= 12]
        if not requested:
            raise ValueError('Music level checks require LEVEL 12 or above')
        result = []
        for level in requested:
            if result:
                await asyncio.sleep(1)
            url = base + 'search/?' + urlencode({'level': options[level]})
            dom = await fetch_dom(session, url, ver)
            result.append({'level': level, 'url': url,
                           'charts': parse_music_level_records(dom, level)})
        return result


def parse_music_version_options(dom):
    if dom is None or isinstance(dom, str):
        raise RuntimeError('Music version page unavailable (login expired or maintenance)')
    if 'too many access' in ''.join(dom.itertext()).lower():
        raise RuntimeError('Official site rate limit: please try again later')
    options = {}
    for node in dom.xpath('//select[@name="version"]/option'):
        value = node.get('value', '')
        label = normalize(''.join(node.itertext()))
        if value.isdigit() and label:
            options[value] = label
    if not options:
        raise RuntimeError('Music version selector missing; login expired or page structure changed')
    return options


def parse_music_version_records(dom, version_id):
    options = parse_music_version_options(dom)
    selected = dom.xpath('//select[@name="version"]/option[@selected]/@value')
    if version_id not in options or selected and selected != [version_id]:
        raise RuntimeError('Server returned a different music version')
    rows = _parse_music_chart_blocks(dom)
    if any(row['difficulty'] != 'master' for row in rows):
        raise RuntimeError('Music version page returned a different difficulty than MASTER')
    return rows


async def get_music_version_lists(cookies: dict, ver='jp'):
    """Read each release's MASTER list to identify song/type release versions."""
    if ver not in ('jp', 'intl'):
        raise ValueError('ver must be jp or intl')
    base = f"{_mobile_base(ver)}/record/musicVersion/search/"
    async with _create_session(cookies, limit=1,
                               timeout=aiohttp.ClientTimeout(total=30, connect=10)) as session:
        first_url = base + '?' + urlencode({'version': '0', 'diff': 3})
        first = await fetch_dom(session, first_url, ver)
        options = parse_music_version_options(first)
        results = []
        for version_id, label in options.items():
            url = base + '?' + urlencode({'version': version_id, 'diff': 3})
            if version_id == '0':
                dom = first
            else:
                await asyncio.sleep(1)
                dom = await fetch_dom(session, url, ver)
            charts = parse_music_version_records(dom, version_id)
            if any(not re.fullmatch(r'\d{1,2}\+?', row.get('level', '')) for row in charts):
                raise RuntimeError('Cannot identify official levels on music version page')
            results.append({'version_id': version_id, 'version': label, 'url': url,
                            'charts': [row for row in charts if int(row['level'].rstrip('+')) >= 12]})
        return results


async def get_recent_records(cookies: dict, ver="jp"):
    """异步版本的 get_recent_records

    Args:
        cookies: 登录后的 cookies 字典
        ver: 版本 (jp/intl)

    Returns:
        list: 最近游戏记录
    """
    base = _mobile_base(ver)
    async with _create_session(cookies) as session:
        url = f"{base}/record/"
        dom = await fetch_dom(session, url, ver)

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
                    "dx_score": dx_score.replace(",", ""),
                    "score_icon": score_icon.replace("plus", "p"),
                    "combo_icon": combo_icon.replace("plus", "p"),
                    "sync_icon": sync_icon.replace("fsd", "fdx").replace("plus", "p")
                })

        return recent_record


async def get_single_record(title: str, type: str, cookies: dict, ver="jp"):
    """获取单首歌曲的成绩记录

    Args:
        title: 歌曲名称（精确匹配）
        type: 谱面类型 ("dx" 或 "std")
        cookies: 登录后的 cookies 字典
        ver: 版本 (jp/intl)

    Returns:
        list: 该歌曲所有难度的成绩记录，每条记录包含：
            - name: 歌曲名称
            - difficulty: 难度 (basic/advanced/expert/master/remaster)
            - type: 谱面类型 (dx/std)
            - score: 达成率
            - dx_score: DX分数
            - score_icon: 评级图标
            - combo_icon: Combo图标
            - sync_icon: Sync图标
            - last_play_time: 最终游玩时间
            - play_count: 游玩次数
        如果未找到返回空列表
    """
    base = _mobile_base(ver)

    async with _create_session(cookies) as session:
        search_url = f"{base}/record/musicGenre/search/?genre=99&diff=0"
        dom = await fetch_dom(session, search_url, ver)

        if dom is None:
            return []
        if dom == "MAINTENANCE":
            return "MAINTENANCE"

        # 查找匹配的歌曲并提取 idx
        idx = None
        forms = dom.xpath('//div[contains(@class, "w_450")]')

        for form in forms:
            # 检查歌曲名称是否匹配
            name_div = form.xpath('.//div[contains(@class, "music_name_block")]/text()')
            if not name_div:
                continue

            song_name = name_div[0]
            if normalize(song_name) != normalize(title):
                continue

            # 检查谱面类型是否匹配
            type_icon = form.xpath('.//img[contains(@class, "music_kind_icon")]/@src')
            if not type_icon:
                continue

            song_type = None
            if 'standard.png' in type_icon[0]:
                song_type = 'std'
            elif 'dx.png' in type_icon[0]:
                song_type = 'dx'

            # 同时匹配 title 和 type
            if song_type == type:
                # 找到匹配的歌曲，提取 idx
                idx_input = form.xpath('.//input[@type="hidden" and @name="idx"]/@value')
                if idx_input:
                    idx = idx_input[0]
                    break

        if not idx:
            # 未找到该歌曲
            return []

        # 第二步：使用 idx 访问歌曲详情页面
        detail_url = f"{base}/record/musicDetail/?idx={quote(idx, safe='')}"
        detail_dom = await fetch_dom(session, detail_url, ver)

        if detail_dom is None:
            return []
        if detail_dom == "MAINTENANCE":
            return "MAINTENANCE"

        # 第三步：解析详情页面，提取所有难度的成绩
        single_record = []

        # 查找所有难度的成绩块
        # 格式：<div id="basic" class="music_basic_score_back w_450 m_15 p_3 f_0">
        #       <div id="expert" class="music_expert_score_back w_450 m_15 p_3 f_0">
        # 匹配所有包含 "score_back" 的 div
        score_blocks = detail_dom.xpath('//div[contains(@class, "_score_back")]')

        for block in score_blocks:
            # 获取难度
            block_id = block.get("id")
            if block_id:
                diff = block_id.lower()
            else:
                diff = 'unknown'

            # 获取谱面类型
            type_img = block.xpath('.//img[contains(@class, "music_kind_icon")]/@src')
            if type_img:
                if 'standard.png' in type_img[0]:
                    chart_type = 'std'
                elif 'dx.png' in type_img[0]:
                    chart_type = 'dx'
                else:
                    chart_type = 'N/A'
            else:
                chart_type = 'N/A'

            # 获取达成率
            # 格式：<div class="music_score_block w_120 d_ib t_r f_12">100.9277%</div>
            score_div = block.xpath('.//div[contains(@class, "music_score_block") and contains(@class, "w_120")]/text()')
            score = score_div[0].strip() if score_div else 'N/A'

            # 获取 DX Score
            # 格式：<div class="music_score_block w_310 m_r_0 d_ib t_r f_12">... 613 / 666</div>
            dx_score_div = block.xpath('.//div[contains(@class, "music_score_block") and contains(@class, "w_310")]')
            dx_score = 'N/A'
            if dx_score_div:
                # 提取所有文本节点
                text_nodes = dx_score_div[0].xpath('.//text()')
                # 找到包含 " / " 的文本（格式：613 / 666）
                for text in text_nodes:
                    text = text.strip()
                    if '/' in text:
                        dx_score = text.replace(',', '')
                        break

            # 获取成绩图标
            # 格式：<img src=".../music_icon_sssp.png?ver=1.60">
            score_icon_img = block.xpath('.//img[contains(@class, "p_t_5") and contains(@class, "v_t")]/@src')
            score_icon = ''
            if score_icon_img:
                icon_name = score_icon_img[0].split('/')[-1].split('?')[0].replace('.png', '').replace('music_icon_', '')
                score_icon = icon_name

            # 获取 Combo 图标
            # 格式：<img src=".../music_icon_fcp.png?ver=1.60" class="h_45 v_t">
            combo_icon_img = block.xpath('.//img[contains(@class, "h_45 v_t")]/@src')
            combo_icon = 'back'
            if combo_icon_img:
                icon_name = combo_icon_img[0].split('/')[-1].split('?')[0].replace('.png', '').replace('music_icon_', '')
                combo_icon = icon_name

            # 获取 Sync 图标
            # 格式：<img src=".../music_icon_sync.png?ver=1.60" class="h_45 m_r_10 v_t">
            sync_icon_img = block.xpath('.//img[contains(@class, "h_45") and contains(@class, "m_r_10") and contains(@class, "v_t")]/@src')
            sync_icon = 'back'
            if sync_icon_img:
                icon_name = sync_icon_img[0].split('/')[-1].split('?')[0].replace('.png', '').replace('music_icon_', '')
                sync_icon = icon_name

            # 获取最终游玩时间和游玩次数
            # JP格式：<tr><td>最終プレイ日時：</td><td>2024/11/29 15:22</td></tr>
            #         <tr><td>プレイ回数：</td><td>4回</td></tr>
            # EN格式：<tr><td>Last played date：</td><td>2025/01/25 21:07</td></tr>
            #         <tr><td>PLAY COUNT：</td><td>1</td></tr>
            last_play_time = 'N/A'
            play_count = 'N/A'

            table_rows = block.xpath('.//table[contains(@class, "collapse")]//tr')
            for row in table_rows:
                # 获取所有td元素
                tds = row.xpath('.//td')
                if len(tds) >= 2:
                    # 提取每个td的文本内容
                    label_text = ''.join(tds[0].xpath('.//text()')).strip()
                    value_text = ''.join(tds[1].xpath('.//text()')).strip()

                    label_lower = label_text.lower()

                    # 匹配最终游玩时间（日文：最終プレイ日時，英文：Last played date）
                    if 'プレイ日時' in label_text or 'played date' in label_lower or 'last played' in label_lower:
                        last_play_time = value_text
                    # 匹配游玩次数（日文：プレイ回数，英文：PLAY COUNT/Play Count）
                    elif 'プレイ回数' in label_text or 'play count' in label_lower or 'count' in label_lower:
                        # 去掉可能的后缀
                        play_count = value_text.replace('回', '').replace('times', '').strip()

            single_record.append({
                'name': title,
                'difficulty': diff,
                'type': chart_type,
                'score': score,
                'dx_score': dx_score,
                'score_icon': score_icon,
                'combo_icon': combo_icon,
                'sync_icon': sync_icon,
                'last_play_time': last_play_time,
                'play_count': play_count
            })

        return single_record


async def get_friends_list(cookies: dict, ver="jp"):
    """异步版本的 get_friends_list

    Args:
        cookies: 登录后的 cookies 字典
        ver: 版本 (jp/intl)

    Returns:
        list: 好友列表
    """
    base = _mobile_base(ver)
    async with _create_session(cookies) as session:
        tasks = []
        url = f"{base}/friend/"
        tasks.append(fetch_dom(session, url, ver))
        url = f"{base}/friend/pages/?idx=2&type=0"
        tasks.append(fetch_dom(session, url, ver))
        
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
    base = _mobile_base(ver)
    async with _create_session(
        cookies, timeout=aiohttp.ClientTimeout(total=15, connect=5),
    ) as session:
        # 并发请求所有页面
        url = f"{base}/friend/search/searchUser/?friendCode={friend_id}"
        dom = await fetch_dom(session, url, ver)

        # 检查维护状态
        if dom == "MAINTENANCE":
            return {"error": "MAINTENANCE"}
        if dom is None:
            return {}

        # 解析主信息
        user_name = dom.xpath('//div[contains(@class, "name_block")]/text()')
        # rating_block_url = dom.xpath('//img[contains(@class, "h_30") and contains(@class, "f_r")]/@src')
        rating = dom.xpath('//div[@class="rating_block"]/text()')
        cource_rank_url = dom.xpath('//img[contains(@class, "h_35") and contains(@class, "f_l")]/@src')
        class_rank_url = dom.xpath('//img[contains(@class, "p_l_10") and contains(@class, "h_35") and contains(@class, "f_l")]/@src')

        # 头像
        icon_url = dom.xpath('//img[contains(@class, "w_112") and contains(@class, "f_l")]/@src')

        # 姓名框
        # nameplate_list = [
        #    "41ef54f2f141e1fd",
        #    "f2b6b6808777400c",
        #    "a42d03bf82bb3eea",
        #    "85b6d4655374b56c",
        #    "427ce8b2e50e01c9",
        #    "331811d4769c6c1a",
        #    "af79c8fed1d26394",
        #    "809c981f807b3596"
        # ]
        # nameplate_name = random.choice(nameplate_list)
        # nameplate_url = f"https://maimaidx.jp/maimai-mobile/img/NamePlate/{nameplate_name}.png"

        nameplate_url = f"https://{DOMAIN}/linebot/img/keep_nameplate"

        # 称号
        trophy_classes_list = dom.xpath('//div[contains(@class, "trophy_block")]/@class')
        if trophy_classes_list:
            trophy_classes = trophy_classes_list[0]
            trophy_type_list = [c for c in trophy_classes.split() if c.startswith('trophy_') and c != 'trophy_block']
            trophy_type = trophy_type_list[0].replace('trophy_', '').lower() if trophy_type_list else 'normal'
        else:
            trophy_type = 'normal'  # default trophy type

        trophy_blocks = dom.xpath('//div[contains(@class, "trophy_inner_block") and contains(@class, "f_13")]')
        if trophy_blocks:
            trophy_block = trophy_blocks[0]
            trophy_texts = trophy_block.xpath('.//text()')
            trophy_content = trophy_texts[1] if len(trophy_texts) > 1 else "ERROR"
        else:
            trophy_content = "ERROR"

        rating_str = rating[0].strip() if rating else "17000"
        try:
            rating_int = int(rating_str)
        except ValueError:
            rating_int = 0

        friend_info = {
            "name": user_name[0].strip() if user_name else "NAME_ERROR",
            "rating_block_path": get_rating_image_path(rating_int),
            "rating": rating_str,
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
    base = _mobile_base(ver)
    difficulty = ['basic', 'advanced', 'expert', 'master', 'remaster']

    async with _create_session(
        cookies, timeout=aiohttp.ClientTimeout(total=15, connect=5),
    ) as session:
        # 并发请求所有难度
        tasks = []
        for diff in range(5):
            url = f"{base}/friend/friendGenreVs/battleStart/?scoreType=2&genre=99&diff={diff}&idx={friend_id}"
            tasks.append(fetch_dom(session, url, ver))

        doms = await asyncio.gather(*tasks)

        # A failed difficulty must not silently produce an incomplete best list.
        if any(isinstance(dom, str) and dom == "MAINTENANCE" for dom in doms):
            return "MAINTENANCE"
        if any(dom is None for dom in doms):
            return None

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
                    name = name_node[0]

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
                        "dx_score": "",
                        "score_icon": score_icon,
                        "combo_icon": combo_icon,
                        "sync_icon": sync_icon
                    })

                except Exception as e:
                    logger.error(f"[Maimai] ✗ Failed to parse friend record block: error={e}")

        return friend_records


_DIST_RE = re.compile(r"([\d.]+)\s*(km|m)\b", re.IGNORECASE)


def _parse_distance_meters(s: str) -> float:
    """'1.2 km' / '300 m' / '約 1.2 km' → 米；解析失败返回 +inf 排到末尾"""
    if not s:
        return float('inf')
    m = _DIST_RE.search(s)
    if not m:
        return float('inf')
    try:
        value = float(m.group(1))
    except ValueError:
        return float('inf')
    return value * 1000 if m.group(2).lower() == 'km' else value


async def _fetch_stores_for_ver(lat, lng, ver):
    """单一版本的店铺查询（jp=gm96 / intl=gm98）。内部 helper。"""
    version_num = "98" if ver == "intl" else "96"
    url = f"https://location.am-all.net/alm/location?gm={version_num}&lat={lat}&lng={lng}"

    async with _create_session() as session:
        dom = await fetch_dom(session, url, ver)

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


async def get_nearby_maimai_stores(lat, lng):
    """异步查询附近机厅 —— 同时拉 jp + intl 两数据源合并去重 + 按距离升序排序。

    返回规则：
      - 两端都 MAINTENANCE → "MAINTENANCE"
      - 仅一端 MAINTENANCE / 异常 → 用另一端的数据
      - 按 (name, address) 严格去重；按距离升序（无法解析的距离排到末尾）

    Args:
        lat: 纬度
        lng: 经度

    Returns:
        list[dict] 店铺列表，或 "MAINTENANCE" 字符串
    """
    results = await asyncio.gather(
        _fetch_stores_for_ver(lat, lng, "jp"),
        _fetch_stores_for_ver(lat, lng, "intl"),
        return_exceptions=True,
    )
    jp_stores, intl_stores = results

    if isinstance(jp_stores, Exception):
        logger.error(f"[Stores] jp fetch failed: {jp_stores}")
        jp_stores = []
    if isinstance(intl_stores, Exception):
        logger.error(f"[Stores] intl fetch failed: {intl_stores}")
        intl_stores = []

    jp_maint = jp_stores == "MAINTENANCE"
    intl_maint = intl_stores == "MAINTENANCE"
    if jp_maint and intl_maint:
        return "MAINTENANCE"

    merged = []
    if not jp_maint and isinstance(jp_stores, list):
        merged.extend(jp_stores)
    if not intl_maint and isinstance(intl_stores, list):
        merged.extend(intl_stores)

    # 去重：同名 + 同地址只留先到的一条（跨语言同店难可靠识别，仅去严格相同项）
    seen = set()
    unique = []
    for s in merged:
        key = (s.get('name', '').strip(), s.get('address', '').strip())
        if not key[0] or key in seen:
            continue
        seen.add(key)
        unique.append(s)

    unique.sort(key=lambda s: _parse_distance_meters(s.get('distance', '')))
    return unique
