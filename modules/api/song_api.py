from flask import Blueprint, jsonify, request

from modules.api.api_auth import api_error_boundary, check_user_permission, require_dev_token
from modules.commands.command_config import API_MAX_SEARCH_RESULTS, MAX_SEARCH_RESULTS
from modules.config_loader import read_dxdata
from modules.song_matcher import find_matching_songs


song_api = Blueprint("song_api", __name__)


@song_api.get("/api/v2/songs/search")
@require_dev_token
@api_error_boundary
def search_songs():
    query = request.args.get("q", "")
    limit = request.args.get("max_results", MAX_SEARCH_RESULTS, type=int)
    if limit < 1 or limit > API_MAX_SEARCH_RESULTS:
        bound = "at least 1" if limit < 1 else f"<= {API_MAX_SEARCH_RESULTS}"
        return jsonify({"error": "Invalid parameter", "message": f"Parameter 'max_results' must be {bound}"}), 400

    user_id = request.args.get("user_id")
    requested_version = request.args.get("ver")
    if requested_version:
        version = requested_version.strip().lower()
    elif user_id:
        allowed, user = check_user_permission(user_id, request.token_info["token_id"])
        if not allowed:
            return user
        version = (user or {}).get("version", "jp")
    else:
        version = "jp"
    if version not in ("jp", "intl"):
        return jsonify({"error": "Invalid parameter", "message": "Parameter 'ver' must be 'jp' or 'intl'"}), 400

    query = "" if query == "__empty__" else query
    songs = find_matching_songs(query, read_dxdata(version)[0], max_results=limit)
    if len(songs) > limit:
        return jsonify({"error": "Too many results",
                        "message": f"Found {len(songs)} songs, please refine your search (max: {limit})",
                        "count": len(songs)}), 400
    result = [{key: song.get(key) for key in ("id", "title", "artist", "type", "version")}
              for song in songs]
    payload = {"success": True, "count": len(result), "query": query,
               "ver": version, "songs": result}
    if not result:
        payload["message"] = "No songs found"
    return jsonify(payload)


@song_api.get("/api/v1/versions")
@song_api.get("/api/v2/versions")
@require_dev_token
@api_error_boundary
def get_versions():
    return jsonify({"success": True, "versions": read_dxdata()[1]})


@song_api.get("/api/v2/dxdata")
@require_dev_token
def get_dxdata():
    version = request.args.get("ver", "jp").strip().lower()
    if version not in ("jp", "intl"):
        return jsonify({"error": "Invalid ver, use jp or intl"}), 400
    songs, versions = read_dxdata(version)
    return jsonify({"songs": songs, "versions": versions})
