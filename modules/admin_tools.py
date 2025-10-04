from config_loader import users, read_user
from record_console import read_record
import json

def get_service_info():
    cnt = {
        "LINE": {
            "num": 0,
            "jp": 0,
            "intl": 0,
        },
        "proxy": {
            "num": 0,
            "jp": 0,
            "intl": 0,
        },
        "unknown": 0
    }

    read_user()

    for user_id, user_info in users.items():
        if 'version' not in user_info:
            cnt['unknown'] += 1
        elif user_id.startswith("U"):
            cnt["LINE"]["num"] += 1
            if user_info['version'] == "jp":
                cnt["LINE"]["jp"] += 1
            else:
                cnt["LINE"]["intl"] += 1
        else:
            cnt["proxy"]["num"] += 1
            if user_info['version'] == "jp":
                cnt["proxy"]["jp"] += 1
            else:
                cnt["proxy"]["intl"] += 1

    return cnt
