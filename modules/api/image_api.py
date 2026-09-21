import base64
import logging
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Callable

from flask import Blueprint, jsonify, request, send_file

from modules.api.api_auth import check_user_permission, require_dev_token
from modules.commands.command_config import RANK_COMMANDS
from modules.config_loader import TEMP_VERSION, read_dxdata
from modules.event_tracker import track_event
from modules.images.skins import user_image
from modules.images.composition import compose_generated_images
from modules.task_runtime import check_rate_limit
from modules.images.records import (
    generate_level_rank_progress_image,
    generate_plate_image,
    generate_records_picture,
)
from modules.images.progress import build_plate_entries, build_progress_entries
from modules.record_manager import (
    PLATE_RULES,
    PROGRESS_RANKS,
    SUPPORTED_PROGRESS_LEVELS,
    read_record,
)
from modules.images.songs import song_info_generate
from modules.user_manager import get_user_timezone


logger = logging.getLogger(__name__)
image_api = Blueprint("image_api", __name__)


@dataclass(frozen=True)
class ImageApiServices:
    background_filter: Callable
    generate_profile: Callable
    select_records: Callable


_services: ImageApiServices | None = None


def configure_image_api(*, background_filter, generate_profile, select_records):
    global _services
    _services = ImageApiServices(background_filter, generate_profile, select_records)


def _send_image_response(buf):
    if request.args.get("format", "png").strip().lower() == "base64":
        img_data = base64.b64encode(buf.getvalue()).decode()
        buf.close()
        return jsonify({"success": True, "format": "base64", "image": img_data})
    return send_file(buf, mimetype="image/png")


def _png_buffer(image):
    buf = BytesIO()
    try:
        image.save(buf, "PNG")
        buf.seek(0)
        return buf
    except Exception:
        buf.close()
        raise
    finally:
        image.close()


def _close_entry_images(entries):
    for entry in entries:
        image = entry.pop("img", None)
        if image:
            image.close()


def _find_song(song_id, version):
    return next((song for song in read_dxdata(version)[0] if song.get("id") == song_id), None)


def _authorized_user(user_id, token_id, rate_key):
    if check_rate_limit(user_id, rate_key):
        return None, (jsonify({"error": "Rate limited", "message": "Too many image requests. Please retry later."}), 429)
    allowed, result = check_user_permission(user_id, token_id)
    if not allowed:
        return None, result
    if "personal_info" not in result:
        return None, (jsonify({"error": "User info not found, please sync first"}), 404)
    return result, None


@image_api.route("/api/v2/songs/<song_id>/image", methods=["GET"])
@require_dev_token
def api_v2_song_info(song_id):
    try:
        token_info = request.token_info
        if check_rate_limit(token_info['token_id'], "api_song_info_image"):
            return jsonify({"error": "Rate limited", "message": "Too many image requests. Please retry later."}), 429

        ver = request.args.get('ver', 'jp').strip().lower()
        if ver not in ('jp', 'intl'):
            return jsonify({"error": "Invalid ver, must be jp or intl"}), 400

        matching_song = _find_song(song_id, ver)
        if not matching_song:
            return jsonify({"error": "Song not found"}), 404

        buf = _png_buffer(
            song_info_generate(matching_song, ver=ver)
        )

        logger.debug(
            "[API] Song info generated: song_id=%s, ver=%s, token_id=%s",
            song_id, ver, token_info["token_id"],
        )
        track_event('image_gen', user_id=None, metadata={'command': 'song-info', 'song_id': song_id, 'ver': ver})
        return _send_image_response(buf)

    except Exception as exc:
        logger.exception("[API] Song info failed: song_id=%s", song_id)
        return jsonify({"error": "Internal server error", "message": str(exc)}), 500


@image_api.route("/api/v2/users/<user_id>/songs/<song_id>/image", methods=["GET"])
@require_dev_token
@user_image
def api_v2_song_record(user_id, song_id):
    try:
        token_info = request.token_info
        _udata, error = _authorized_user(user_id, token_info['token_id'], "api_song_record_image")
        if error:
            return error

        ver = _udata.get("version", "jp")
        matching_song = _find_song(song_id, ver)
        if not matching_song:
            return jsonify({"error": "Song not found"}), 404

        song_record = read_record(user_id, ver=ver)
        if not song_record:
            return jsonify({"error": "No records found, please sync first"}), 404

        played_data = []
        for rcd in song_record:
            if rcd['cover_name'] == matching_song['cover_name'] and rcd['type'] == matching_song['type']:
                played_data.append(rcd)

        if not played_data:
            return jsonify({"error": "No record for this song"}), 404

        user_tz = get_user_timezone(user_id)
        song_img = song_info_generate(
            matching_song,
            played_data,
            timezone_offset=user_tz,
            ver=ver,
            bg_filter=_services.background_filter(user_id),
        )
        buf = _png_buffer(song_img)

        logger.debug(
            "[API] Song record generated: user_id=%s, song_id=%s, token_id=%s",
            user_id, song_id, token_info["token_id"],
        )
        track_event('image_gen', user_id=user_id, metadata={'command': 'song-record'})
        return _send_image_response(buf)

    except Exception as exc:
        logger.exception("[API] Song record failed: user_id=%s, song_id=%s", user_id, song_id)
        return jsonify({"error": "Internal server error", "message": str(exc)}), 500


@image_api.route("/api/v2/users/<user_id>/image", methods=["GET"])
@require_dev_token
@user_image
def api_v2_generate_record_image(user_id):
    try:
        token_info = request.token_info
        _udata, error = _authorized_user(user_id, token_info['token_id'], "api_record_image")
        if error:
            return error

        command = request.args.get('command', 'b50').strip().lower()
        parts = re.split(r"[ \n]", command, 1)
        first_word = parts[0]
        rest_text = parts[1] if len(parts) > 1 else ""

        ver = _udata.get("version", "jp")

        record_type = None
        for aliases, mode in RANK_COMMANDS.items():
            if isinstance(aliases, tuple):
                if first_word in aliases:
                    record_type = mode
                    break
            else:
                if first_word == aliases:
                    record_type = mode
                    break

        if not record_type:
            return jsonify({"error": f"Unknown command: {command}",
                            "available": [a for aliases in RANK_COMMANDS for a in (aliases if isinstance(aliases, tuple) else (aliases,))]}), 400

        recent = (record_type == "rct50")
        recent_type = (record_type == "best40")
        song_record = read_record(user_id, recent, recent_type, ver=ver)
        if not song_record:
            return jsonify({"error": "No records found, please sync first"}), 404

        up_songs, down_songs, details = _services.select_records(song_record, record_type, rest_text, ver)
        if not up_songs and not down_songs:
            return jsonify({"error": "No matching records for this command"}), 404

        display_type = "未だ知らず" if record_type == "unknown" else record_type
        record_img = generate_records_picture(
            up_songs,
            down_songs,
            display_type.upper(),
            ver,
            details,
        )
        user_info = _udata.get('personal_info')
        profile_img = _services.generate_profile(user_info, user_id=user_id)
        user_tz = get_user_timezone(user_id)
        img = compose_generated_images(
            [profile_img, record_img],
            timezone_offset=user_tz,
            bg_filter=_services.background_filter(user_id),
        )

        buf = _png_buffer(img)

        logger.debug(
            "[API] Record image generated: user_id=%s, command=%s, token_id=%s",
            user_id, command, token_info["token_id"],
        )
        track_event('image_gen', user_id=user_id, metadata={'command': command, 'source': 'api'})
        return _send_image_response(buf)

    except Exception as exc:
        logger.exception("[API] Record image failed: user_id=%s", user_id)
        return jsonify({"error": "Internal server error", "message": str(exc)}), 500


@image_api.route("/api/v2/users/<user_id>/plate", methods=["GET"])
@require_dev_token
@user_image
def api_v2_generate_plate(user_id):
    try:
        token_info = request.token_info
        _udata, error = _authorized_user(user_id, token_info['token_id'], "api_plate_image")
        if error:
            return error

        title = request.args.get('title', '').strip()
        if not title:
            return jsonify({"error": "title parameter is required"}), 400
        if not (len(title) == 2 or len(title) == 3):
            return jsonify({"error": "Invalid title length, must be 2 or 3 characters"}), 400

        ver = _udata.get("version", "jp")
        song_record = read_record(user_id, ver=ver)
        if not song_record:
            return jsonify({"error": "No records found, please sync first"}), 404

        title = title.replace("晓", "暁").replace("极", "極")

        version_name = title[0]
        plate_type = title[1:]

        songs, versions = read_dxdata(ver)
        target_version = []
        if version_name in TEMP_VERSION["abbr"]:
            target_version.append(TEMP_VERSION["title"])
        for version in versions:
            if version_name in version['abbr']:
                target_version.append(version['version'])

        if not target_version:
            return jsonify({"error": "Version not found"}), 404

        if plate_type not in PLATE_RULES:
            return jsonify({"error": "Invalid plate type, must be 極/将/神/舞舞"}), 400
        target_type, target_icon = PLATE_RULES[plate_type]

        version_rcd_data = list(filter(lambda x: x['version'] in target_version, song_record))
        if not version_rcd_data:
            return jsonify({"error": "No version records found"}), 404

        target_data, target_num = build_plate_entries(
            songs, version_rcd_data, target_version, target_type, target_icon, ver)

        try:
            plate_img = generate_plate_image(target_data, title, headers=target_num)
        finally:
            _close_entry_images(target_data)

        user_info = _udata.get('personal_info')
        profile_img = _services.generate_profile(user_info, user_id=user_id)
        user_tz = get_user_timezone(user_id)
        img = compose_generated_images(
            [profile_img, plate_img],
            timezone_offset=user_tz,
            bg_filter=_services.background_filter(user_id),
        )

        buf = _png_buffer(img)

        logger.debug(
            "[API] Plate generated: user_id=%s, title=%s, token_id=%s",
            user_id, title, token_info["token_id"],
        )
        track_event('image_gen', user_id=user_id, metadata={'command': 'plate'})
        return _send_image_response(buf)

    except Exception as exc:
        logger.exception("[API] Plate generation failed: user_id=%s", user_id)
        return jsonify({"error": "Internal server error", "message": str(exc)}), 500


@image_api.route("/api/v2/users/<user_id>/achievement", methods=["GET"])
@require_dev_token
@user_image
def api_v2_generate_achievement(user_id):
    try:
        token_info = request.token_info
        _udata, error = _authorized_user(user_id, token_info['token_id'], "api_achievement_image")
        if error:
            return error

        level = request.args.get('level', '').strip()
        rank = request.args.get('rank', None)
        if rank:
            rank = rank.strip().lower()

        if level not in SUPPORTED_PROGRESS_LEVELS:
            return jsonify({"error": f"Invalid level, supported: {list(SUPPORTED_PROGRESS_LEVELS)}"}), 400
        if rank is not None and rank not in PROGRESS_RANKS:
            return jsonify({"error": f"Invalid rank, supported: {list(PROGRESS_RANKS)}"}), 400

        ver = _udata.get("version", "jp")
        song_record = read_record(user_id, ver=ver)
        if not song_record:
            return jsonify({"error": "No records found, please sync first"}), 404

        songs, _ = read_dxdata(ver)
        target_data, stats = build_progress_entries(
            songs, song_record, level, None, rank, ver, PROGRESS_RANKS.get(rank))

        if not target_data:
            return jsonify({"error": "No matching data"}), 404

        level_display = level.replace("+", "⁺")
        rank_display = rank.upper().replace("+", "⁺") if rank else ""
        try:
            record_img = generate_level_rank_progress_image(
                target_data,
                level_display,
                rank_display,
                stats,
                ver=ver,
            )
        finally:
            _close_entry_images(target_data)

        user_info = _udata.get('personal_info')
        profile_img = _services.generate_profile(user_info, scale=1.5, user_id=user_id)
        user_tz = get_user_timezone(user_id)
        img = compose_generated_images(
            [profile_img, record_img],
            timezone_offset=user_tz,
            bg_filter=_services.background_filter(user_id),
        )

        buf = _png_buffer(img)

        logger.debug(
            "[API] Achievement generated: user_id=%s, level=%s, rank=%s, token_id=%s",
            user_id, level, rank, token_info["token_id"],
        )
        track_event('image_gen', user_id=user_id, metadata={'command': 'progress' if rank else 'level-list'})
        return _send_image_response(buf)

    except Exception as exc:
        logger.exception("[API] Achievement generation failed: user_id=%s", user_id)
        return jsonify({"error": "Internal server error", "message": str(exc)}), 500
