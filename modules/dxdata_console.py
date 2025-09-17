import requests
import json

def load_dxdata(url, save_to: str = None, split=True):
    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()

        if split:
            data['songs'] = split_song_sheets_by_type(data['songs'])

        if save_to:
            with open(save_to, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
            print(f"文件已成功保存为 {save_to}")

        return data

    except requests.RequestException as e:
        return None
    except json.JSONDecodeError as e:
        return None

def split_song_sheets_by_type(song_list):
    result = []

    for song in song_list:
        base_info = {
            "songId": song["songId"],
            "category": song["category"],
            "title": song["title"],
            "artist": song["artist"],
            "bpm": song["bpm"],
            "imageName": song["imageName"],
            "isNew": song["isNew"],
            "isLocked": song["isLocked"],
            "searchAcronyms": song["searchAcronyms"]
        }

        sheets_by_type = {"dx": [], "std": [], "utage": []}
        version_by_type = {}

        for sheet in song.get("sheets", []):
            sheet_type = sheet.get("type")
            if "multiverInternalLevelValue" in sheet:
                sheet["internalLevelValue"] = sheet["multiverInternalLevelValue"].get("PRiSM PLUS", sheet["internalLevelValue"])

            if sheet_type in sheets_by_type:
                new_sheet = sheet.copy()
                version_by_type[sheet_type] = new_sheet.pop("version", "")
                new_sheet.pop("type", None)
                sheets_by_type[sheet_type].append(new_sheet)

        for sheet_type, sheets in sheets_by_type.items():
            if sheets:
                entry = base_info.copy()
                entry["type"] = sheet_type
                entry["version"] = version_by_type.get(sheet_type, "")
                entry["sheets"] = sheets
                result.append(entry)

    return result
