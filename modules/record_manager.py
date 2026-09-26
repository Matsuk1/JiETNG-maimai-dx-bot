"""
成绩记录管理模块

提供数据库操作、Rating计算、成绩数据处理等功能
"""

import logging
import re
from typing import Any, Optional

from modules.config_loader import MAIMAI_VERSION, read_dxdata
from modules.user_db import get_user_field
from modules.dbpool_manager import database_cursor

logger = logging.getLogger(__name__)

CURRENT_RA_COEFFICIENTS = (
    (100.5000, 0.224),
    (100.4999, 0.222),
    (100.0000, 0.216),
    (99.9999, 0.214),
    (99.5000, 0.211),
    (99.0000, 0.208),
    (98.9999, 0.206),
    (98.0000, 0.203),
    (97.0000, 0.200),
    (96.9999, 0.176),
    (94.0000, 0.168),
    (90.0000, 0.152),
    (80.0000, 0.136),
    (79.9999, 0.128),
    (75.0000, 0.120),
    (70.0000, 0.112),
    (60.0000, 0.096),
    (50.0000, 0.080),
    (40.0000, 0.064),
    (30.0000, 0.048),
    (20.0000, 0.032),
    (10.0000, 0.016),
)
RECENT_RA_COEFFICIENTS = (
    (100.5000, 0.140),
    (100.0000, 0.135),
    (99.5000, 0.132),
    (99.0000, 0.130),
    (98.0000, 0.127),
    (97.0000, 0.125),
    (94.0000, 0.105),
    (90.0000, 0.095),
    (80.0000, 0.085),
    (75.0000, 0.075),
    (70.0000, 0.070),
    (60.0000, 0.060),
    (50.0000, 0.050),
    (40.0000, 0.040),
    (30.0000, 0.030),
    (20.0000, 0.020),
    (10.0000, 0.010),
)
DX_STAR_THRESHOLDS = (0.85, 0.90, 0.93, 0.95, 0.97)
SUPPORTED_PROGRESS_LEVELS = ("11", "11+", "12", "12+", "13", "13+", "14", "14+", "15")
PROGRESS_RANKS = {
    "s": ("score", ("s", "sp", "ss", "ssp", "sss", "sssp")),
    "s+": ("score", ("sp", "ss", "ssp", "sss", "sssp")),
    "ss": ("score", ("ss", "ssp", "sss", "sssp")),
    "ss+": ("score", ("ssp", "sss", "sssp")),
    "sss": ("score", ("sss", "sssp")),
    "sss+": ("score", ("sssp",)),
    "fc": ("combo", ("fc", "fcp", "ap", "app")),
    "fc+": ("combo", ("fcp", "ap", "app")),
    "ap": ("combo", ("ap", "app")),
    "ap+": ("combo", ("app",)),
    "fdx": ("sync", ("fdx", "fdxp")),
    "fdx+": ("sync", ("fdxp",)),
}
PLATE_RULES = {
    "極": ("combo", ("fc", "fcp", "ap", "app")),
    "将": ("score", ("sss", "sssp")),
    "神": ("combo", ("ap", "app")),
    "舞舞": ("sync", ("fdx", "fdxp")),
}


def _rating_coefficient(
    score: float, coefficients: tuple[tuple[float, float], ...]
) -> float:
    return next(
        (coefficient for threshold, coefficient in coefficients if score >= threshold),
        0.0,
    )


def get_single_ra(
    level: float, score: float, ap_clear: bool = False, recent_type: bool = False
) -> int:
    """
    计算单曲Rating值

    根据谱面定数和达成率计算Rating值,日服AP有额外加成

    Args:
        level: 谱面定数 (如 14.5)
        score: 达成率 (如 100.5000)
        ap_clear: 是否为 AP/APP
        recent_type: 是否为 b40 计算方案

    Returns:
        计算得到的Rating整数值
    """
    if recent_type:
        return get_single_ra_recent(level, score)

    coefficient = _rating_coefficient(score, CURRENT_RA_COEFFICIENTS)
    ra = int(level * min(score, 100.5) * coefficient)
    if ap_clear:
        ra += 1
    return ra


def get_single_ra_recent(level: float, score: float) -> int:
    """
    计算旧版本单曲Rating值

    根据谱面定数和达成率计算Rating值

    Args:
        level: 谱面定数 (如 14.5)
        score: 达成率 (如 100.5000)

    Returns:
        计算得到的Rating整数值
    """
    coefficient = _rating_coefficient(score, RECENT_RA_COEFFICIENTS)
    return int(level * min(score, 100.5) * coefficient)


def get_ideal_score(score: float) -> tuple[float, Optional[str]]:
    if 99.0000 <= score < 99.5000:
        return 99.5000, "ssp"
    elif 99.5000 <= score < 100.0000:
        return 100.0000, "sss"
    elif 100.0000 <= score < 100.5000:
        return 100.5000, "sssp"
    elif 100.5000 <= score <= 101.0000:
        return 101.0000, "sssp"
    else:
        return score, None


def parse_dx_score(dx_score_str: Any) -> float:
    """解析 dx_score 字符串 (如 '613 / 666') 为浮点数"""
    try:
        match = re.match(r"^\s*(\d+)\s*/\s*(\d+)\s*$", str(dx_score_str))
        if match:
            numerator = int(match.group(1))
            denominator = int(match.group(2))
            if denominator == 0:
                return 0.0
            return numerator / denominator
        return float(dx_score_str)
    except (ValueError, TypeError):
        return 0.0


def calc_dx_star(dx_percentage: float) -> int:
    if not 0 <= dx_percentage <= 1:
        return 0
    return sum(dx_percentage >= threshold for threshold in DX_STAR_THRESHOLDS)


def read_record(
    user_id: str,
    recent: bool = False,
    recent_type: bool = False,
    ver: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    从数据库读取用户成绩记录

    Args:
        user_id: 用户ID
        recent: 是否读取最近记录 (False=Best记录, True=Recent记录)

    Returns:
        成绩记录列表,每条记录为字典,包含详细信息
    """
    table = "recent_records" if recent else "best_records"

    with database_cursor() as (_, cursor):
        cursor.execute(f"SELECT * FROM {table} WHERE user_id = %s", (user_id,))
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]

    records = []
    for row in rows:
        item = dict(zip(columns, row))
        item.pop("id", None)
        item.pop("user_id", None)
        records.append(item)

    if ver is None:
        ver = get_user_field(user_id, "version", "jp")

    return get_detailed_info(records, ver, recent_type)


def _write_record(cursor: Any, user_id: str, record_json: list, recent: bool) -> None:
    table = "recent_records" if recent else "best_records"
    cursor.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))

    sql = f"""
            INSERT INTO {table} (
                user_id, name, difficulty, type, score, dx_score,
                score_icon, combo_icon, sync_icon
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    batch_data = [
        (
            user_id,
            song.get("name"),
            song.get("difficulty"),
            song.get("type"),
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


def write_record(
    user_id: str,
    record_json: list,
    recent: bool = False,
    *,
    cursor: Any = None,
) -> None:
    if cursor is not None:
        _write_record(cursor, user_id, record_json, recent)
        return
    with database_cursor(write=True) as (_, own_cursor):
        _write_record(own_cursor, user_id, record_json, recent)


def delete_record(user_id, recent=False):
    table = "recent_records" if recent else "best_records"
    with database_cursor(write=True) as (_, cursor):
        cursor.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))


def achievement_value(value: Any) -> float:
    try:
        return float(str(value or 0).rstrip("%"))
    except (TypeError, ValueError):
        return 0.0


def index_records_by_chart(records):
    """Index records by the exact chart identity used by the score database."""
    return {
        (record['name'], record['difficulty'], record['type']): record
        for record in records
    }


def find_chart_record(index, title, difficulty, chart_type):
    return index.get((title, difficulty, chart_type))


def filter_progress_entries(entries, mode):
    if mode == "uncleared":
        return [entry for entry in entries if not entry["achieved"]]
    if mode == "unplayed":
        return [entry for entry in entries if not entry["achievement_rate"] and not entry["achieved"]]
    if mode == "cleared":
        return [entry for entry in entries if entry["achieved"]]
    return entries


def get_detailed_info(song_record, ver="jp", recent_type=False):
    songs, _ = read_dxdata(ver)

    chart_map = {}
    for song in songs:
        for sheet in song.get("sheets", []):
            key = (song.get("title"), song.get("type"), sheet.get("difficulty"))
            chart_map.setdefault(key, (song, sheet))

    for record in song_record:
        key = (record.get("name"), record.get("type"), record.get("difficulty"))
        chart = chart_map.get(key)
        if chart is None:
            record["internalLevelValue"] = 0
            record["new_song"] = True
            record["version"] = "UNKNOWN"
            record["ra"] = 0
            record["cover_url"] = None
            record["cover_name"] = "UNKNOWN"
            continue

        song, sheet = chart
        record["internalLevelValue"] = sheet["internalLevelValue"]
        record["new_song"] = song["version"] in MAIMAI_VERSION[ver]
        record["version"] = song["version"]
        record["ra"] = get_single_ra(
            float(record["internalLevelValue"]),
            achievement_value(record.get("score")),
            "ap" in str(record.get("combo_icon") or ""),
            recent_type,
        )
        record["cover_url"] = song["cover_url"]
        record["cover_name"] = song["cover_name"]
        record["dx_percentage"] = parse_dx_score(record.get("dx_score"))
        record["dx_star"] = calc_dx_star(record["dx_percentage"])

    return song_record
