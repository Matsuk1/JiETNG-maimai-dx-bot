"""
成绩记录管理模块

提供数据库操作、Rating计算、成绩数据处理等功能
"""

from typing import List, Dict, Any, Optional
from modules.config_loader import (
    MAIMAI_VERSION,
    SONGS,
    read_dxdata,
    read_user,
    USERS
)
from modules.dbpool_manager import get_connection


def get_single_ra(level: float, score: float, ap_clear: bool = False) -> int:
    """
    计算单曲Rating值

    根据谱面定数和达成率计算Rating值,日服AP有额外加成

    Args:
        level: 谱面定数 (如 14.5)
        score: 达成率 (如 100.5000)
        ap_clear: 是否为AP/APP (仅日服有加成)

    Returns:
        计算得到的Rating整数值
    """
    # Rating系数映射表
    if score >= 100.5000:
        ra_kake = 0.224
    elif score >= 100.4999:
        ra_kake = 0.222
    elif score >= 100.0000:
        ra_kake = 0.216
    elif score >= 99.9999:
        ra_kake = 0.214
    elif score >= 99.5000:
        ra_kake = 0.211
    elif score >= 99.0000:
        ra_kake = 0.208
    elif score >= 98.9999:
        ra_kake = 0.206
    elif score >= 98.0000:
        ra_kake = 0.203
    elif score >= 97.0000:
        ra_kake = 0.200
    elif score >= 96.9999:
        ra_kake = 0.176
    elif score >= 94.0000:
        ra_kake = 0.168
    elif score >= 90.0000:
        ra_kake = 0.152
    elif score >= 80.0000:
        ra_kake = 0.136
    elif score >= 79.9999:
        ra_kake = 0.128
    elif score >= 75.0000:
        ra_kake = 0.120
    elif score >= 70.0000:
        ra_kake = 0.112
    elif score >= 60.0000:
        ra_kake = 0.096
    elif score >= 50.0000:
        ra_kake = 0.080
    elif score >= 40.0000:
        ra_kake = 0.064
    elif score >= 30.0000:
        ra_kake = 0.048
    elif score >= 20.0000:
        ra_kake = 0.032
    elif score >= 10.0000:
        ra_kake = 0.016
    else:
        ra_kake = 0

    # 计算基础Rating
    if score <= 100.5:
        ra = int(level * score * ra_kake)
    else:
        ra = int(level * 100.5 * ra_kake)

    # AP加成 (仅日服)
    if ap_clear:
        ra += 1

    return ra

def get_yang_single_ra(song_record, eight_adding=False):
    level = float(song_record['internalLevelValue'])
    achievement = float(song_record['score'][:-1])
    dx_score = eval(song_record['dx_score'].replace(",", ""))
    score = level * max(min((achievement - 100), dx_score), 0)
    
    if not eight_adding:
        return round(score, 2)

    if song_record['combo_icon'] == 'fcp':
        score += 1
    elif 'ap' in song_record['combo_icon']:
        score += 2

    if achievement >= 100.90:
        score += 1
    if achievement >= 100.95:
        score += 1
    if achievement >= 100.98:
        score += 1

    if dx_score >= 0.93:
        score += 1
    if dx_score >= 0.95:
        score += 1
    if dx_score >= 0.97:
        score += 1

    return round(score, 2)

def get_ideal_score(score: float) -> float:
    if 99.0000 <= score < 99.5000:
        return 99.5000
    elif 99.5000 <= score < 100.0000:
        return 100.0000
    elif 100.0000 <= score < 100.5000:
        return 100.5000
    else:
        return score

def read_record(user_id: str, recent: bool = False, yang: bool = False) -> List[Dict[str, Any]]:
    """
    从数据库读取用户成绩记录

    Args:
        user_id: 用户ID
        recent: 是否读取最近记录 (False=Best记录, True=Recent记录)
        yang: 是否计算Yang Rating (过去版本rating)

    Returns:
        成绩记录列表,每条记录为字典,包含详细信息
    """
    read_user()

    table = "recent_records" if recent else "best_records"
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Reading records from table {table} for user {user_id}")

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {table} WHERE user_id = %s", (user_id,))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

        records = []
        for row in rows:
            item = dict(zip(columns, row))
            item.pop("id", None)
            item.pop("user_id", None)
            records.append(item)

        return get_detailed_info(records, USERS[user_id]['version'], yang)

    finally:
        conn.close()

def write_record(user_id, record_json, recent=False):
    table = "recent_records" if recent else "best_records"
    print(f"[*] Writing to DB table {table} for user_id = {user_id}\n")

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))

            sql = f"""
            INSERT INTO {table} (
                user_id, name, difficulty, kind, score, dx_score,
                score_icon, combo_icon, sync_icon
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # 优化：批量插入数据，减少数据库往返次数
            batch_data = [
                (
                    user_id,
                    song.get("name"),
                    song.get("difficulty"),
                    song.get("kind"),
                    song.get("score"),
                    song.get("dx_score"),
                    song.get("score_icon"),
                    song.get("combo_icon"),
                    song.get("sync_icon"),
                )
                for song in record_json
            ]

            if batch_data:
                cursor.executemany(sql, batch_data)

        conn.commit()
    finally:
        conn.close()

def delete_record(user_id, recent=False):
    table = "recent_records" if recent else "best_records"
    print(f"[*] Deleting from DB table {table} for user_id = {user_id}\n")

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
        conn.commit()
    finally:
        conn.close()

def filter_highest_achievement(data: list) -> list:
    result = {}
    for entry in data:
        key = (entry.get("name"), entry.get("difficulty"), entry.get("type"))
        if key not in result or float(entry.get("score", "0")[:-1]) > float(result[key].get("score", "0")[:-1]):
            result[key] = entry
    return list(result.values())

def get_detailed_info(song_record, ver="jp", yang=False):
    read_dxdata(ver)

    # 构建哈希表加速查找 O(1) 而不是 O(n)
    song_map = {}
    for song in SONGS:
        key = (song['title'], song['type'])
        if key not in song_map:
            song_map[key] = song

    for record in song_record:
        found = False
        key = (record['name'], record['kind'])

        if key in song_map:
            song = song_map[key]
            for sheet in song['sheets']:
                if record['difficulty'] == sheet['difficulty']:
                    found = True
                    record['internalLevelValue'] = sheet['internalLevelValue']
                    record['new_song'] = True if song['version'] in MAIMAI_VERSION[ver] else False
                    record['version'] = song['version']
                    ap_clear = "ap" in record['combo_icon']
                    record['ra'] = get_single_ra(float(record['internalLevelValue']), float(record['score'][:-1]), (ap_clear and ver == "jp"))
                    record['id'] = sheet['internalId'] if 'internalId' in sheet else -1
                    record['cover_url'] = song['cover_url']
                    if yang:
                        record['ra'] = get_yang_single_ra(record)
                    break

        if not found:
            record['internalLevelValue'] = 0
            record['new_song'] = True
            record['version'] = "UNKNOWN"
            record['ra'] = 0
            record['id'] = -1
            record['cover_url'] = None

    return song_record
