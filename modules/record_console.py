import pymysql
from config_loader import HOST, USER, PASSWORD, DATABASE, MAIMAI_VERSION, songs, read_dxdata

def get_single_ra(level, score, ap_clear=False) :
    if score >= 100.5000 :
        ra_kake = 0.224
    elif score >= 100.4999 :
        ra_kake = 0.222
    elif score >= 100.0000 :
        ra_kake = 0.216
    elif score >= 99.9999 :
        ra_kake = 0.214
    elif score >= 99.5000 :
        ra_kake = 0.211
    elif score >= 99.0000 :
        ra_kake = 0.208
    elif score >= 98.9999 :
        ra_kake = 0.206
    elif score >= 98.0000 :
        ra_kake = 0.203
    elif score >= 97.0000 :
        ra_kake = 0.200
    elif score >= 96.9999 :
        ra_kake = 0.176
    elif score >= 94.0000 :
        ra_kake = 0.168
    elif score >= 90.0000 :
        ra_kake = 0.152
    elif score >= 80.0000 :
        ra_kake = 0.136
    elif score >= 79.9999 :
        ra_kake = 0.128
    elif score >= 75.0000 :
        ra_kake = 0.120
    elif score >= 70.0000 :
        ra_kake = 0.112
    elif score >= 60.0000 :
        ra_kake = 0.096
    elif score >= 50.0000 :
        ra_kake = 0.080
    elif score >= 40.0000 :
        ra_kake = 0.064
    elif score >= 30.0000 :
        ra_kake = 0.048
    elif score >= 20.0000 :
        ra_kake = 0.032
    elif score >= 10.0000 :
        ra_kake = 0.016
    else :
        ra_kake = 0

    if score <= 100.5 :
        ra = int(level * score * ra_kake)
    else :
        ra = int(level * 100.5 * ra_kake)

    if ap_clear:
        ra += 1

    return ra

def get_ideal_score(score: float) -> float:
    if 99.0000 <= score < 99.5000:
        return 99.5000
    elif 99.5000 <= score < 100.0000:
        return 100.0000
    elif 100.0000 <= score < 100.5000:
        return 100.5000
    else:
        return score

def read_record(user_id, recent=False):
    table = "recent_records" if recent else "best_records"
    print(f"[*] Reading from DB table `{table}` for user_id = {user_id}\n")

    conn = pymysql.connect(
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        charset="utf8mb4"
    )

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

        return get_detailed_info(records)

    finally:
        conn.close()

def write_record(user_id, record_json, recent=False, replace=True):
    table = "recent_records" if recent else "best_records"
    print(f"[*] Writing to DB table `{table}` for user_id = {user_id}\n")

    conn = pymysql.connect(
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        charset="utf8mb4"
    )

    try:
        with conn.cursor() as cursor:
            if not replace:
                old_records = read_record(user_id, recent)
                record_json = filter_highest_achievement(record_json + old_records)

            cursor.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))

            sql = f"""
            INSERT INTO {table} (
                user_id, `name`, difficulty, kind, score, `dx-score`,
                `score-icon`, `combo-icon`, `dx-icon`
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            for song in record_json:
                cursor.execute(sql, (
                    user_id,
                    song.get("name"),
                    song.get("difficulty"),
                    song.get("kind"),
                    song.get("score"),
                    song.get("dx-score"),
                    song.get("score-icon"),
                    song.get("combo-icon"),
                    song.get("dx-icon"),
                ))

        conn.commit()
    finally:
        conn.close()

def delete_record(user_id, recent=False):
    table = "recent_records" if recent else "best_records"
    print(f"[*] Deleting from DB table `{table}` for user_id = {user_id}\n")

    conn = pymysql.connect(
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        charset="utf8mb4"
    )

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

def get_detailed_info(song_record):
    read_dxdata()

    for record in song_record :
        found = False
        for song in songs :
            if record['name'] == song['title'] and record['kind'] == song['type']:
                for sheet in song['sheets'] :
                    if record['difficulty'] == sheet['difficulty']:
                        found = True
                        record['internalLevelValue'] = sheet['internalLevelValue']
                        record['new_song'] = True if song['version'] in MAIMAI_VERSION else False
                        record['version'] = song['version']
                        ap_clear = "ap" in record['combo-icon']
                        record['ra'] = get_single_ra(float(sheet['internalLevelValue']), float(record['score'][:-1]), ap_clear)
                        record['id'] = sheet['internalId'] if 'internalId' in sheet else -1
                        record['url'] = f"https://shama.dxrating.net/images/cover/v2/{song['imageName']}.jpg"

        if not found :
            record['internalLevelValue'] = 0
            record['new_song'] = True
            record['version'] = "UNKNOWN"
            record['ra'] = 0
            record['id'] = -1
            record['url'] = "https://maimaidx.jp/maimai-mobile/img/Icon/c22d52b387e3f829.png"

    return song_record
