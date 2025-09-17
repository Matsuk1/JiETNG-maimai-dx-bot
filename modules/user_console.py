import json
from record_console import delete_record
from config_loader import read_user, write_user, users

def add_user(user_id):
    read_user()
    users[user_id] = {
        "status": {
            "points": 0,
            "checked": False,
            "check_days": 0,
            "notice_read": False,
            "free_times": 2,
            "replying_status": False
        }
    }
    write_user()

def delete_user(user_id):
    read_user()

    if user_id in users:
        del users[user_id]
        write_user()

    delete_record(user_id, recent=True)
    delete_record(user_id, recent=False)
    delete_record(f"fake_{user_id}")

def edit_user_status(user_id, key, word, type=0):
    read_user()

    if type == 0:
        users[user_id]["status"][key] = word

    elif type == 1:
        users[user_id]["status"][key] += word

    elif type == 2:
        users[user_id]["status"][key] -= word

    elif type == 4:
        del user[user_id]["status"][key]

    write_user()

def edit_user_status_of_all(key, word, type=0):
    for user_id in list(users.keys()):
        edit_user_status(user_id, key, word, type)

def get_user_status(user_id, key=""):
    read_user()
    if key:
        return users[user_id]["status"].get(key, None)

    else:
        return users[user_id]["status"]

def reset_clean_users():
    read_user()

    for user_id in list(users.keys()):
        info = users[user_id]

        if list(info.keys()) == ["status"]:
            if not info["status"]["points"]:
                delete_user(user_id)
                continue

        edit_user_status(user_id, "check_days", get_user_status(user_id, "check_days") if get_user_status(user_id, "checked") else 0)
        edit_user_status(user_id, "checked", False)
        edit_user_status(user_id, "free_times", 3)

    write_user()
