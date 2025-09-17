import requests

def fetch_all_playlogs(token):
    url_template = "https://u.otogame.net/api/game/maimai/playlog?page={}"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        "Authorization": f"Bearer {token}",
        "Priority": "u=3, i",
        "Referer": "https://u.otogame.net/maimai/music?tab=playlog",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15"
    }

    page = 1
    all_data = []

    while True:
        url = url_template.format(page)
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"Request failed at page {page}, status code: {response.status_code}")
            break

        data = response.json()

        if not data:
            print(f"No more data at page {page}, stopping.")
            break

        all_data.extend(data["data"]["data"])
        print(f"Fetched page {page} with {len(data['data']['data'])} items.")

        page += 1

    return all_data

def format_playlog_item(item):
    # 原始字段直接取
    difficulties = {
        0: "basic",
        1: "advanced",
        2: "expert",
        3: "master",
        4: "remaster",
        10: "unknown"
    }

    name = item['music']['name']
    difficulty = difficulties[item['difficulty']]
    score = f"{(item['achievement'] / 10000):.4f}%"
    dx_score = f"{item['deluxe_score']} / {item['total_combo'] * 3}"

    # kind: 根据 is_deluxe 判断
    kind = 'dx' if item['music'].get('is_deluxe', False) else 'std'

    # score-icon: 根据 score_rank 生成
    score_rank_map = {
        13: 'sssp',
        12: 'sss',
        11: 'ssp',
        10: 'ss',
        9: 'sp',
        8: 's',
        7: 'aaa',
        6: 'aa',
        5: 'a',
        4: 'bbb',
        3: 'bb',
        2: 'b',
        1: 'c',
        0: 'd'
    }
    score_icon = score_rank_map.get(item.get('score_rank', 0), 'unknown')

    # combo-icon: 根据 combo_status 生成
    combo_status_map = {
        4: 'app',
        3: 'ap',
        2: 'fcp',
        1: 'fc',
        0: 'back'
    }
    combo_icon = combo_status_map.get(item.get('combo_status', 0), '')

    # dx-icon: 根据 sync_status 生成
    sync_status_map = {
        5: 'sync',
        4: 'fdxp',
        3: 'fdx',
        2: 'fsp',
        1: 'fs',
        0: 'back'
    }
    dx_icon = sync_status_map.get(item.get('sync_status', 0), '')

    return {
        "name": name,
        "difficulty": difficulty,
        "kind": kind,
        "score": score,
        "dx-score": dx_score,
        "score-icon": score_icon,
        "combo-icon": combo_icon,
        "dx-icon": dx_icon
    }

def get_fakemai_records(token):
    playlogs = fetch_all_playlogs(token)
    formated_logs = []
    for item in playlogs:
        formated_logs.append(format_playlog_item(item))

    return formated_logs

print(get_fakemai_records("v2.local.H76zhsLgh62aMStgDVg3_6fOaVTY93YEodg2CbeQNfrw3tF1uh7IA59CzHunv_ErC9uPhJ0Wa4bHR3qBm1D9QSKE0fooUn1novveOSqsYyAPj-9502xkRb9Txg5k92i3_4oWJ8fY5bEbNblsDaN86V7w4afESOqruMyuw71f17A31W47R9XM9jLlS904YMtapLcjf4rtub8RgLHTskMFj1Hr7mqVELCq062EfXK7D9-yuPA-vnUoDq_KnhImixHem-u88iHwozpFVsUL3qS71tKUDkhmp8bUi4uoGJcQ8ztNhU1Z9hBygSCl_8hgU27HBVlDIPvN-TGfe-zyWNhr.bnVsbA"))
