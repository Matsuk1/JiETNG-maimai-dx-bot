import logging
import time
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from dataclasses import dataclass
from typing import Callable
from modules.score_recognition.presentation import ScoreRecognitionResultError, build_score_recognition_response
from modules.score_recognition.results import (
    InvalidScoreImageError, UnsupportedScoreImageError, expand_score_recognition_calc_variants,
)


@dataclass(frozen=True)
class ScoreApiServices:
    authorize: Callable
    rate_limit: Callable
    recognize: Callable
    validate: Callable
    render: Callable


def _default_services():
    from modules.api.api_auth import require_dev_token
    from modules.task_runtime import check_rate_limit
    from modules.images.records import generate_score_recognition_picture
    from modules.score_recognition.recognizer import recognize_score_image_bytes, validate_recognized_judgement

    return ScoreApiServices(require_dev_token, check_rate_limit, recognize_score_image_bytes,
                            validate_recognized_judgement, generate_score_recognition_picture)


logger = logging.getLogger(__name__)


def create_score_api(max_image_bytes, *, services=None):
    services = services or _default_services()
    api = Blueprint("score_api", __name__)

    def error(kind, message, status):
        return jsonify({"error": kind, "message": message}), status

    @api.post("/api/v2/score-recognition")
    @api.post("/api/v2/score-recognition/image")
    @services.authorize
    def recognize_score():
        token_id = request.token_info["token_id"]
        image_output = request.path.rstrip("/").endswith("/image")
        if services.rate_limit(token_id, "api_score_recognition"):
            return error("Rate limited", "Too many score recognition requests. Please retry later.", 429)

        if request.content_length is not None and request.content_length > max_image_bytes + 1024 * 1024:
            return error("Payload too large", f"Image exceeds the configured upload limit of {max_image_bytes} bytes", 413)

        version = str(request.form.get("ver") or request.args.get("ver") or "jp").strip().lower()
        if version not in {"jp", "intl"}:
            return error("Invalid parameter", "Parameter 'ver' must be 'jp' or 'intl'", 400)
        uploaded = request.files.get("image")
        if uploaded is None:
            return error("Missing parameter", "Multipart image field 'image' is required", 400)
        image_bytes = uploaded.stream.read(max_image_bytes + 1)
        if not image_bytes:
            return error("Invalid image", "Uploaded image is empty", 400)
        if len(image_bytes) > max_image_bytes:
            return error("Payload too large", f"Image exceeds the configured upload limit of {max_image_bytes} bytes", 413)

        started_at = time.perf_counter()
        try:
            result = services.validate(
                services.recognize(
                    image_bytes,
                    line_like_preprocess=True,
                    ver=version,
                ),
                ver=version,
                image_bytes=image_bytes,
            )
            selected = expand_score_recognition_calc_variants(result)[0]
            public = build_score_recognition_response(selected)
            if image_output:
                image = services.render(
                    selected,
                    ver=version,
                )
                try:
                    buffer = BytesIO()
                    image.save(buffer, "PNG")
                    buffer.seek(0)
                finally:
                    image.close()

                validation = selected.get("validation") or {}
                count = max(1, int(validation.get("calc_completion_candidate_count", 0) or 0))
                song_id = str(public["song"]["id"])
                response = send_file(buffer, mimetype="image/png", download_name=f"jietng-ocr-{song_id}.png")
                response.headers["X-JiETNG-OCR-Candidate-Index"] = "1"
                response.headers["X-JiETNG-OCR-Candidate-Count"] = str(count)
                logger.debug(
                    "[API] Score image completed: token_id=%s ver=%s song_id=%s candidates=%s elapsed=%.3fs",
                    token_id, version, song_id, count, time.perf_counter() - started_at,
                )
                return response

            response = public
            logger.debug(
                "[API] Score recognition completed: token_id=%s ver=%s song_id=%s elapsed=%.3fs",
                token_id, version, response["song"]["id"], time.perf_counter() - started_at,
            )
            return jsonify(response)
        except UnsupportedScoreImageError as exc:
            return error("Unsupported media type", str(exc), 415)
        except InvalidScoreImageError as exc:
            return error("Invalid image", str(exc), 400)
        except (ScoreRecognitionResultError, ValueError) as exc:
            logger.debug(
                "[API] Score recognition rejected: token_id=%s ver=%s reason=%s elapsed=%.3fs",
                token_id, version, exc, time.perf_counter() - started_at,
            )
            return error("Recognition failed", "The image could not be recognized as a complete score result.", 422)
        except Exception:
            logger.exception(
                "[API] Score recognition failed: token_id=%s ver=%s elapsed=%.3fs",
                token_id, version, time.perf_counter() - started_at,
            )
            return error("Internal server error", "Score recognition failed due to an internal error.", 500)

    return api
