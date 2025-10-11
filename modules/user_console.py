import json
from modules.record_console import delete_record
from modules.config_loader import read_user, write_user, users

def add_user(user_id):
    read_user()
    users[user_id] = {
        "status": {
            "notice_read": False,
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

def edit_user_status(user_id, key, word, type=0):
    read_user()

    if user_id not in users:
        add_user(user_id)

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

    if user_id not in users:
        add_user(user_id)

    if key:
        return users[user_id]["status"].get(key, None)

    else:
        return users[user_id]["status"]
