#!/usr/bin/env python3
"""OCR pipeline and command-line debugger for maimai result photos."""
from __future__ import annotations

import argparse
import atexit
import base64
import inspect
import itertools
import json
import logging
import os
import re
import selectors
import subprocess
import sys
import threading
import time
import unicodedata
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import psutil
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

try:
    from .cropper import (
        save_crop_debug,
        crop_result_fields_in_memory,
        iter_images,
    )
except ImportError:  # Allows direct CLI execution of this file.
    from cropper import (
        save_crop_debug,
        crop_result_fields_in_memory,
        iter_images,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(PROJECT_ROOT / ".paddle-home" / "paddlex"))
os.environ.setdefault("MPLCONFIGDIR", "/tmp/jietng-matplotlib")
os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "huggingface")
os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "0")
os.environ.setdefault("FLAGS_use_onednn", "0")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")

OCR_FIELDS = (
    "main_title",
    "main_achievement",
    "sub_judgement_table",
)

OCR_MODEL_NAMES = ("PP-OCRv6_small_det", "PP-OCRv6_small_rec")
FIXED_TABLE_LAYOUT_HINTS = {"dxnet", "cropper_pt_pose_warp"}
SUB_JUDGEMENT_COLUMN_OCR_SCALE = 5
JUDGEMENT_ROW_NAMES = ("tap", "hold", "slide", "touch", "break")
JUDGEMENT_VALUE_NAMES = ("critical_perfect", "perfect", "great", "good", "miss")
TABLE_MODEL_RESULT_MARKER = "JIETNG_TABLE_RESULT="
TABLE_MODEL_READY_MARKER = "JIETNG_TABLE_READY"
TABLE_MODEL_START_TIMEOUT_SECONDS = 180
TABLE_MODEL_REQUEST_TIMEOUT_SECONDS = 60
TABLE_MODEL_MAX_RSS_MB = int(os.getenv("JIETNG_TABLE_OCR_MAX_RSS_MB", "1536"))
TABLE_MODEL_MAX_REQUESTS = int(os.getenv("JIETNG_TABLE_OCR_MAX_REQUESTS", "50"))
_TABLE_MODEL_PROCESS: subprocess.Popen[str] | None = None
_TABLE_MODEL_LOCK = threading.Lock()
_TABLE_MODEL_REQUEST_COUNT = 0
_TABLE_MODEL_HELPER_MTIME_NS: int | None = None


def _stop_table_model_process() -> None:
    global _TABLE_MODEL_PROCESS, _TABLE_MODEL_REQUEST_COUNT
    global _TABLE_MODEL_HELPER_MTIME_NS
    process = _TABLE_MODEL_PROCESS
    _TABLE_MODEL_PROCESS = None
    _TABLE_MODEL_REQUEST_COUNT = 0
    _TABLE_MODEL_HELPER_MTIME_NS = None
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _read_table_model_line(
    process: subprocess.Popen[str],
    timeout: float,
) -> str:
    if process.stdout is None:
        raise RuntimeError("table model stdout is unavailable")
    selector = selectors.DefaultSelector()
    try:
        selector.register(process.stdout, selectors.EVENT_READ)
        if not selector.select(timeout):
            raise subprocess.TimeoutExpired(process.args, timeout)
        line = process.stdout.readline()
    finally:
        selector.close()
    if not line:
        raise RuntimeError(
            f"table model stopped unexpectedly (exit={process.poll()})"
        )
    return line.rstrip("\r\n")


def _start_table_model_process() -> subprocess.Popen[str]:
    global _TABLE_MODEL_PROCESS, _TABLE_MODEL_HELPER_MTIME_NS
    helper = Path(__file__).with_name("table_model.py")
    helper_mtime_ns = helper.stat().st_mtime_ns
    process = _TABLE_MODEL_PROCESS
    if process is not None and process.poll() is None:
        if _TABLE_MODEL_HELPER_MTIME_NS == helper_mtime_ns:
            return process
        logger.info("[Recognize] Restarting table OCR worker after helper file update")
        _stop_table_model_process()

    env = os.environ.copy()
    env.setdefault("MPLCONFIGDIR", "/tmp/jietng-matplotlib")
    env.setdefault(
        "PADDLE_PDX_CACHE_HOME",
        str(PROJECT_ROOT / ".paddle-home" / "paddlex"),
    )
    cpu_threads = min(8, os.cpu_count() or 1)
    env.setdefault("JIETNG_TABLE_OCR_CPU_THREADS", str(cpu_threads))
    env.setdefault("PADDLE_PDX_CPU_NUM_THREADS", str(cpu_threads))
    env.setdefault("OMP_NUM_THREADS", str(cpu_threads))
    env.setdefault("MKL_NUM_THREADS", str(cpu_threads))
    use_onednn = env.get("JIETNG_TABLE_OCR_ENABLE_MKLDNN", "0") == "1"
    if use_onednn:
        env["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "1"
        env["FLAGS_use_onednn"] = "1"
        env["FLAGS_use_mkldnn"] = "1"
    else:
        env["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"
        env["FLAGS_use_onednn"] = "0"
        env["FLAGS_use_mkldnn"] = "0"
    started_at = time.perf_counter()
    process = subprocess.Popen(
        [sys.executable, str(helper), "--serve"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        env=env,
    )
    _TABLE_MODEL_PROCESS = process
    ready = _read_table_model_line(process, TABLE_MODEL_START_TIMEOUT_SECONDS)
    if ready != TABLE_MODEL_READY_MARKER:
        _stop_table_model_process()
        raise RuntimeError(f"unexpected table model startup response: {ready}")
    _TABLE_MODEL_HELPER_MTIME_NS = helper_mtime_ns
    try:
        rss_mb = psutil.Process(process.pid).memory_info().rss / (1024**2)
    except psutil.Error:
        rss_mb = 0.0
    logger.info(
        "[Recognize] Table OCR worker ready: startup=%.3fs pid=%s rss=%.1fMB "
        "threads=%s onednn=%s",
        time.perf_counter() - started_at,
        process.pid,
        rss_mb,
        cpu_threads,
        use_onednn,
    )
    return process


def warm_table_model() -> None:
    """Load the table model during service startup instead of the first request."""
    with _TABLE_MODEL_LOCK:
        _start_table_model_process()


def recognize_judgement_with_table_model(
    image: Image.Image,
    partial_out: dict[str, dict[str, int]] | None = None,
) -> dict[str, dict[str, int]] | None:
    global _TABLE_MODEL_REQUEST_COUNT
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    request_id = uuid.uuid4().hex
    request = json.dumps({
        "id": request_id,
        "image": base64.b64encode(buffer.getvalue()).decode("ascii"),
    }, separators=(",", ":"))

    with _TABLE_MODEL_LOCK:
        try:
            previous_pid = (
                _TABLE_MODEL_PROCESS.pid
                if _TABLE_MODEL_PROCESS is not None
                and _TABLE_MODEL_PROCESS.poll() is None
                else None
            )
            started_at = time.perf_counter()
            process = _start_table_model_process()
            reused_worker = previous_pid == process.pid
            startup_seconds = time.perf_counter() - started_at
            if process.stdin is None:
                raise RuntimeError("table model stdin is unavailable")
            process.stdin.write(request + "\n")
            process.stdin.flush()
            line = _read_table_model_line(
                process,
                TABLE_MODEL_REQUEST_TIMEOUT_SECONDS,
            )
            if not line.startswith(TABLE_MODEL_RESULT_MARKER):
                raise RuntimeError(f"unexpected table model response: {line}")
            payload = json.loads(line[len(TABLE_MODEL_RESULT_MARKER):])
            if payload.get("id") != request_id:
                raise RuntimeError("table model response id does not match request")
            result = payload.get("result")
            partial_result = payload.get("partial_result")
            if partial_out is not None:
                partial_out.clear()
                if isinstance(partial_result, dict):
                    partial_out.update({
                        str(row_name): {
                            str(column_name): max(0, int(value))
                            for column_name, value in row.items()
                            if column_name in JUDGEMENT_VALUE_NAMES
                        }
                        for row_name, row in partial_result.items()
                        if row_name in JUDGEMENT_ROW_NAMES and isinstance(row, dict)
                    })
            _TABLE_MODEL_REQUEST_COUNT += 1

            try:
                rss_mb = psutil.Process(process.pid).memory_info().rss / (1024**2)
            except psutil.Error:
                rss_mb = 0.0
            logger.debug(
                "[Recognize] Table OCR request: reused=%s startup=%.3fs inference=%.3fs "
                "pid=%s rss=%.1fMB requests=%s mode=%s",
                reused_worker,
                startup_seconds,
                time.perf_counter() - started_at - startup_seconds,
                process.pid,
                rss_mb,
                _TABLE_MODEL_REQUEST_COUNT,
                payload.get("mode") or "unknown",
            )
            if (
                rss_mb >= TABLE_MODEL_MAX_RSS_MB
                or _TABLE_MODEL_REQUEST_COUNT >= TABLE_MODEL_MAX_REQUESTS
            ):
                logger.info(
                    "[Recognize] Restarting table model worker: rss=%.1fMB requests=%s",
                    rss_mb,
                    _TABLE_MODEL_REQUEST_COUNT,
                )
                _stop_table_model_process()

            if isinstance(result, dict) and len(result) == 5:
                return result
            logger.warning(
                "[Recognize] Table model returned no complete result: partial_rows=%s error=%s",
                sorted(partial_out) if partial_out else [],
                payload.get("error") or "incomplete table",
            )
        except (
            OSError,
            RuntimeError,
            ValueError,
            json.JSONDecodeError,
            subprocess.TimeoutExpired,
        ) as exc:
            _stop_table_model_process()
            logger.warning("[Recognize] Table model failed; using column OCR: %s", exc)
    return None


atexit.register(_stop_table_model_process)


def is_table_blue_pixel(red: int, green: int, blue: int) -> bool:
    return blue >= 95 and blue >= red + 18 and blue >= green + 8


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    replacements = {
        "％": "%",
        "／": "/",
        "｜": "/",
        "|": "/",
        "﹣": "-",
        "−": "-",
        "ー": "-",
        "Ｏ": "0",
        "O": "0",
        "o": "0",
        "I": "1",
        "l": "1",
    }
    for before, after in replacements.items():
        value = value.replace(before, after)
    return re.sub(r"\s+", " ", value).strip()


def normalize_song_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = re.sub(r"\s+", " ", value).strip()
    # The title crop can still include UI labels from the same header band.
    value = re.sub(r"(NEW\s*RECORD|MY\s*BEST|ACHIEVEMENT|TRACK\s*\d+)", " ", value, flags=re.IGNORECASE)
    value = re.sub(
        r"(RE\s*[:\-]?\s*MASTER|MASTER|EXPERT|ADVANCED|BASIC|LV\s*\d+\+?)",
        " ",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"(でらっくす|てらっくす|DX)", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip()
    return value.strip(" -|")


def enhance_judgement_color_contrast(image: Image.Image) -> Image.Image:
    """Boost low-contrast colored judgement digits after table cropping."""
    arr = np.asarray(image.convert("RGB")).astype(np.int16)
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    maximum = arr.max(axis=2)
    minimum = arr.min(axis=2)
    brightness = (r + g + b) / 3
    blue_line = (b >= 90) & (g >= 45) & (b >= r + 18) & (brightness >= 42) & (brightness <= 215)
    row_label = (b >= 70) & (r <= 85) & (g <= 120) & (b >= r + 22) & (brightness <= 145)
    protected = blue_line | row_label

    pink = (r > 105) & (b > 70) & (g < r * 0.82) & (g < b * 0.95) & ~protected
    green = (g > 85) & (g > r * 1.06) & (g > b * 1.04) & ~protected
    gray = ((maximum - minimum) <= 30) & (maximum >= 58) & (maximum <= 220) & ~protected
    light = (minimum >= 205) & ~protected

    arr[:, :, 0][pink] = np.minimum(255, (r[pink] * 1.10).astype(np.int16))
    arr[:, :, 1][pink] = np.maximum(0, (g[pink] * 0.45).astype(np.int16))
    arr[:, :, 2][pink] = np.minimum(255, (b[pink] * 1.02).astype(np.int16))

    arr[:, :, 0][green] = np.maximum(0, (r[green] * 0.50).astype(np.int16))
    arr[:, :, 1][green] = np.minimum(255, (g[green] * 1.16).astype(np.int16))
    arr[:, :, 2][green] = np.maximum(0, (b[green] * 0.58).astype(np.int16))

    gray_value = np.maximum(0, (minimum[gray] * 0.55).astype(np.int16))
    arr[:, :, 0][gray] = gray_value
    arr[:, :, 1][gray] = gray_value
    arr[:, :, 2][gray] = gray_value

    arr[:, :, 0][light] = np.minimum(255, (r[light] * 1.05).astype(np.int16))
    arr[:, :, 1][light] = np.minimum(255, (g[light] * 1.05).astype(np.int16))
    arr[:, :, 2][light] = np.minimum(255, (b[light] * 1.05).astype(np.int16))

    return Image.fromarray(arr.astype(np.uint8), "RGB")


def prepare_ocr_image_data(source_image: Image.Image, field: str) -> Image.Image:
    image = ImageOps.exif_transpose(source_image).convert("RGB")
    scale = (
        SUB_JUDGEMENT_COLUMN_OCR_SCALE
        if field == "sub_judgement_column"
        else 3 if field == "sub_judgement_table" else 2
    )
    image = image.resize((image.width * scale, image.height * scale), Image.Resampling.LANCZOS)

    if field == "sub_judgement_column":
        pass
    elif field in {"main_achievement", "rating", "dx_score", "max_combo", "judgement", "level"}:
        image = ImageEnhance.Contrast(image).enhance(1.65)
        image = ImageEnhance.Sharpness(image).enhance(1.75)
    else:
        image = ImageEnhance.Contrast(image).enhance(1.35)
        image = ImageEnhance.Sharpness(image).enhance(1.45)

    image = image.filter(ImageFilter.SHARPEN)
    return image


class PaddleOcrEngine:
    def __init__(self, lang: str = "japan") -> None:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise RuntimeError(
                "PaddleOCR is not installed. Install it in the test environment with: "
                "python3 -m pip install paddlepaddle paddleocr"
            ) from exc

        detection_model, recognition_model = OCR_MODEL_NAMES
        model_kwargs = {
            "text_detection_model_name": detection_model,
            "text_recognition_model_name": recognition_model,
        }
        self.model_names = (detection_model, recognition_model)
        self._direct_recognition_error_logged = False

        init_attempts = (
            {
                **model_kwargs,
                "use_doc_orientation_classify": False,
                "use_doc_unwarping": False,
                "use_textline_orientation": False,
                "enable_mkldnn": False,
                "cpu_threads": 4,
            },
            {**model_kwargs, "use_textline_orientation": False, "enable_mkldnn": False},
            {**model_kwargs, "use_angle_cls": False, "show_log": False, "enable_mkldnn": False},
            model_kwargs,
        )
        last_error: Exception | None = None
        for kwargs in init_attempts:
            try:
                self.ocr = PaddleOCR(**kwargs)
                break
            except Exception as exc:  # pragma: no cover - depends on PaddleOCR version
                last_error = exc
        else:
            raise RuntimeError(f"failed to initialize PaddleOCR: {last_error}") from last_error

    def read(self, image_source: str | Path | Image.Image) -> list[dict[str, Any]]:
        if isinstance(image_source, Image.Image):
            import numpy as np

            source = np.asarray(image_source.convert("RGB"))
        else:
            source = str(image_source)
        attempts = [
            ("predict", lambda: self.ocr.predict(source)),
            ("ocr", lambda: self.ocr.ocr(source)),
        ]

        try:
            ocr_parameters = inspect.signature(self.ocr.ocr).parameters
        except (TypeError, ValueError):
            ocr_parameters = {}
        if "cls" in ocr_parameters:
            attempts.append(("ocr(cls=False)", lambda: self.ocr.ocr(source, cls=False)))

        errors: list[str] = []
        for name, attempt in attempts:
            try:
                return extract_ocr_items(attempt())
            except Exception as exc:  # pragma: no cover - depends on PaddleOCR version
                errors.append(f"{name}: {type(exc).__name__}: {exc}")
        source_name = str(image_source) if not isinstance(image_source, Image.Image) else "in-memory image"
        raise RuntimeError(f"OCR failed for {source_name}: {'; '.join(errors)}")

    def read_cropped_lines(
        self,
        images: list[Image.Image],
    ) -> list[dict[str, Any]] | None:
        """Run recognition directly when text bounds are already known."""
        try:
            import numpy as np

            pipeline = getattr(self.ocr, "paddlex_pipeline", None)
            recognizer = None
            visited: set[int] = set()
            while pipeline is not None and id(pipeline) not in visited:
                visited.add(id(pipeline))
                recognizer = getattr(pipeline, "text_rec_model", None)
                if recognizer is not None:
                    break
                pipeline = getattr(pipeline, "_pipeline", None)
            if recognizer is None:
                raise AttributeError("PaddleOCR text recognition model is unavailable")
            outputs = list(
                recognizer.predict(
                    [np.asarray(image.convert("RGB")) for image in images],
                    batch_size=len(images),
                )
            )
        except Exception as exc:
            if not self._direct_recognition_error_logged:
                logger.warning(
                    "[Recognize] Direct cropped-text recognition unavailable; using detector fallback: %s",
                    exc,
                )
                self._direct_recognition_error_logged = True
            return None

        results: list[dict[str, Any]] = []
        for output in outputs:
            payload = getattr(output, "json", None)
            if callable(payload):
                payload = payload()
            if isinstance(payload, dict):
                payload = payload.get("res", payload)
            if not isinstance(payload, dict):
                return None
            results.append({
                "text": str(payload.get("rec_text", "")),
                "score": float(payload.get("rec_score", 0.0)),
            })
        return results if len(results) == len(images) else None


def extract_ocr_items(result: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if node is None:
            return
        if isinstance(node, dict):
            texts = node.get("rec_texts")
            scores = node.get("rec_scores")
            if scores is None:
                scores = []
            boxes = node.get("rec_boxes")
            if boxes is None:
                boxes = node.get("dt_polys")
            if boxes is None:
                boxes = []
            if isinstance(texts, list):
                for index, text in enumerate(texts):
                    items.append({
                        "text": str(text),
                        "score": float(scores[index]) if index < len(scores) else None,
                        "box": _jsonable_box(boxes[index]) if index < len(boxes) else None,
                    })
                return
            for value in node.values():
                walk(value)
            return
        if isinstance(node, (list, tuple)):
            if len(node) >= 2 and isinstance(node[1], (list, tuple)) and len(node[1]) >= 1 and isinstance(node[1][0], str):
                items.append({
                    "text": node[1][0],
                    "score": float(node[1][1]) if len(node[1]) > 1 and isinstance(node[1][1], (int, float)) else None,
                    "box": _jsonable_box(node[0]),
                })
                return
            for value in node:
                walk(value)
            return
        json_attr = getattr(node, "json", None)
        if isinstance(json_attr, dict):
            walk(json_attr)

    walk(result)
    return items


def _jsonable_box(value: Any) -> Any:
    try:
        if hasattr(value, "tolist"):
            return value.tolist()
        if isinstance(value, tuple):
            return list(value)
        return value
    except Exception:
        return None


def joined_text(items: list[dict[str, Any]]) -> str:
    return normalize_text(" ".join(str(item.get("text", "")) for item in items if item.get("text")))


def joined_song_text(items: list[dict[str, Any]]) -> str:
    text = " ".join(str(item.get("text", "")) for item in items if item.get("text"))
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def item_bounds(item: dict[str, Any]) -> tuple[float, float, float, float] | None:
    box = item.get("box")
    if not isinstance(box, list) or not box:
        return None
    if len(box) == 4 and all(isinstance(value, (int, float)) for value in box):
        left, top, right, bottom = (float(value) for value in box)
        return left, top, right, bottom
    xs: list[float] = []
    ys: list[float] = []
    for point in box:
        if isinstance(point, list) and len(point) >= 2:
            xs.append(float(point[0]))
            ys.append(float(point[1]))
    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def extract_song_title(items: list[dict[str, Any]]) -> str:
    fragments = []
    for item in items:
        text = normalize_song_text(str(item.get("text", "")))
        bounds = item_bounds(item)
        if not text or bounds is None:
            continue
        left, top, right, bottom = bounds
        height = max(1.0, bottom - top)
        fragments.append({
            "text": text,
            "left": left,
            "center_y": (top + bottom) / 2,
            "width": max(1.0, right - left),
            "height": height,
        })
    if not fragments:
        return normalize_song_text(joined_song_text(items))

    fragments.sort(key=lambda fragment: fragment["center_y"])
    lines: list[list[dict[str, Any]]] = []
    for fragment in fragments:
        matching_line = next((
            line for line in lines
            if abs(
                fragment["center_y"]
                - sum(item["center_y"] for item in line) / len(line)
            ) <= max(fragment["height"], max(item["height"] for item in line)) * 0.65
        ), None)
        if matching_line is None:
            lines.append([fragment])
        else:
            matching_line.append(fragment)

    candidates = []
    for line in lines:
        line.sort(key=lambda fragment: fragment["left"])
        text = normalize_song_text(" ".join(fragment["text"] for fragment in line))
        if not text:
            continue
        compact = re.sub(r"[^A-Za-z0-9]", "", text)
        numeric_only = bool(re.fullmatch(r"[A-Za-z]?\d+(?:[.,]\d+)?%?", text.replace(" ", "")))
        score = (
            max(fragment["height"] for fragment in line) * 4
            + sum(fragment["width"] for fragment in line) * 0.05
            + len(text) * 2
            + max(fragment["center_y"] for fragment in line) * 2
        )
        if numeric_only or compact.upper() in {"NEWRECORD", "MYBEST", "ACHIEVEMENT"}:
            score -= 500
        candidates.append((score, text))

    if not candidates:
        return normalize_song_text(joined_song_text(items))
    return max(candidates, key=lambda candidate: candidate[0])[1]


def parse_result(fields: dict[str, dict[str, Any]]) -> dict[str, Any]:
    raw = {name: joined_text(data.get("items", [])) for name, data in fields.items()}
    if "main_title" in fields:
        raw["main_title"] = extract_song_title(fields["main_title"].get("items", []))
    sub_judgement_field = fields.get("sub_judgement_table", {})
    sub_judgement_items = sub_judgement_field.get("items", [])
    parsed: dict[str, Any] = {
        "title": normalize_song_text(raw.get("main_title", "")),
        "achievement": parse_percent_items(
            fields.get("main_achievement", {}).get("items", []),
            raw.get("main_achievement", ""),
        ),
        "sub_judgement": (
            sub_judgement_field.get("column_values")
            or parse_sub_judgement_items(sub_judgement_items)
            or parse_sub_judgement(raw.get("sub_judgement_table", ""))
        ),
    }
    if sub_judgement_field.get("column_confidences"):
        parsed["sub_judgement_confidence"] = sub_judgement_field.get("column_confidences")
    parsed["raw"] = raw
    return parsed


def normalize_achievement_percent_text(text: str) -> str | None:
    match = re.fullmatch(r"\s*(\d{0,3})[.,](\d{3,4})\s*%?\s*", text)
    if not match:
        return None
    integer, decimal = match.groups()
    # Result screenshots sometimes crop the leading achievement digit:
    # `.xxxx` / `00.xxxx` / `0.xxxx` mean `100.xxxx`, while `9.xxxx` means `99.xxxx`.
    if integer == "":
        integer = "100"
    elif len(integer) == 2 and integer == "00":
        integer = "100"
    elif len(integer) == 1:
        integer = "100" if integer == "0" else f"9{integer}"
    return f"{integer}.{decimal}"


def parse_percent(text: str) -> float | None:
    candidates = re.findall(r"(?<!\d)(\d{0,3}[.,]\d{3,4})\s*%?", text)
    # Paddle occasionally repeats the integer's last digit before the decimal:
    # `100 0.9934%` and `97 7.6199%` mean `100.9934%` and `97.6199%`.
    split_candidates = re.findall(
        r"(?<!\d)(\d{2,3})[.,]?\s+(\d)[.,](\d{3,4})\s*%?",
        text,
    )
    values = []
    for item in candidates:
        normalized = normalize_achievement_percent_text(item)
        if normalized is None:
            continue
        try:
            values.append(float(normalized))
        except ValueError:
            continue
    for integer, repeated_digit, decimal in split_candidates:
        if integer[-1] != repeated_digit:
            continue
        try:
            values.append(float(f"{integer}.{decimal}"))
        except ValueError:
            continue
    plausible = [value for value in values if 0 <= value <= 101]
    return max(plausible) if plausible else None


def parse_percent_items(items: list[dict[str, Any]], fallback_text: str) -> float | None:
    boxed_items: list[tuple[float, float, float, float, str]] = []
    for item in items:
        box = item.get("box")
        if not isinstance(box, (list, tuple)) or len(box) < 4:
            continue
        try:
            left, top, right, bottom = (float(box[index]) for index in range(4))
        except (TypeError, ValueError):
            continue
        if right <= left or bottom <= top:
            continue
        boxed_items.append((left, top, right, bottom, str(item.get("text", ""))))

    if boxed_items:
        groups: list[list[tuple[float, float, float, float, str]]] = []
        for item in sorted(boxed_items, key=lambda candidate: (candidate[1] + candidate[3]) / 2):
            height = item[3] - item[1]
            center_y = (item[1] + item[3]) / 2
            for group in groups:
                group_top = min(candidate[1] for candidate in group)
                group_bottom = max(candidate[3] for candidate in group)
                group_height = max(candidate[3] - candidate[1] for candidate in group)
                group_center_y = (group_top + group_bottom) / 2
                if abs(center_y - group_center_y) <= max(height, group_height) * 0.65:
                    group.append(item)
                    break
            else:
                groups.append([item])

        ranked_groups = sorted(
            groups,
            key=lambda group: (
                max(item[3] - item[1] for item in group),
                sum((item[2] - item[0]) * (item[3] - item[1]) for item in group),
            ),
            reverse=True,
        )
        for group in ranked_groups:
            merged = ""
            for *_, text in sorted(group, key=lambda item: item[0]):
                compact = re.sub(r"\s+", "", text)
                overlap = min(len(merged), len(compact))
                while overlap and merged[-overlap:] != compact[:overlap]:
                    overlap -= 1
                merged += compact[overlap:]
            merged_value = parse_percent(merged)
            if merged_value is not None:
                return merged_value

    candidates: list[tuple[float, float]] = []
    for item in items:
        value = parse_percent(str(item.get("text", "")))
        box = item.get("box")
        if value is None or not isinstance(box, (list, tuple)) or len(box) < 4:
            continue
        try:
            area = max(0.0, float(box[2]) - float(box[0])) * max(
                0.0,
                float(box[3]) - float(box[1]),
            )
        except (TypeError, ValueError):
            continue
        candidates.append((area, value))

    if candidates:
        return max(candidates, key=lambda candidate: candidate[0])[1]
    return parse_percent(fallback_text)


def item_center(item: dict[str, Any]) -> tuple[float, float] | None:
    box = item.get("box")
    if not isinstance(box, list) or not box:
        return None
    if len(box) == 4 and all(isinstance(value, (int, float)) for value in box):
        return ((float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2)

    xs: list[float] = []
    ys: list[float] = []
    for point in box:
        if isinstance(point, list) and len(point) >= 2:
            xs.append(float(point[0]))
            ys.append(float(point[1]))
    if not xs or not ys:
        return None
    return sum(xs) / len(xs), sum(ys) / len(ys)


def normalize_label_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "").upper()
    value = value.replace("0", "O").replace("1", "I")
    return re.sub(r"[^A-Z]", "", value)


def normalize_digit_ocr_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "").upper()
    value = re.sub(r"\s+", "", value)
    return value.translate(str.maketrans({
        "Z": "2",
    }))


def parse_item_int(text: str) -> int | None:
    normalized = normalize_digit_ocr_text(text)
    if re.fullmatch(r"[O0〇]+", unicodedata.normalize("NFKC", text or "").upper().strip()):
        return 0
    match = re.fullmatch(r"\d{1,4}", normalized)
    return int(match.group(0)) if match else None


def parse_column_int(text: str) -> int | None:
    raw = unicodedata.normalize("NFKC", text or "").upper()
    raw_compact = re.sub(r"\s+", "", raw)
    normalized = normalize_digit_ocr_text(text)
    if re.fullmatch(r"\d{1,3}日", normalized):
        normalized = normalized[:-1] + "1"
    match = re.search(r"\d{1,4}", normalized)
    if match:
        return int(match.group(0))
    if re.fullmatch(r"[O0〇]+", raw_compact):
        return 0
    return None


def cluster_indexes(indexes: list[int], max_gap: int = 3) -> list[tuple[int, int]]:
    if not indexes:
        return []
    ranges: list[tuple[int, int]] = []
    start = end = indexes[0]
    for value in indexes[1:]:
        if value <= end + max_gap:
            end = value
        else:
            ranges.append((start, end))
            start = end = value
    ranges.append((start, end))
    return ranges


def is_judgement_grid_pixel(r: int, g: int, b: int) -> bool:
    brightness = (r + g + b) / 3
    return b >= 70 and r <= 125 and g <= 150 and b >= r + 8 and brightness <= 215


def detect_regular_dark_lines(
    image: Image.Image,
    axis: str,
    count: int,
) -> list[int] | None:
    gray = ImageOps.grayscale(image)
    width, height = gray.size
    pixels = gray.load()
    if axis == "vertical":
        length = width
        values = [
            sum(pixels[x, y] for y in range(int(height * 0.15), int(height * 0.88), 3))
            / len(range(int(height * 0.15), int(height * 0.88), 3))
            for x in range(width)
        ]
        local_radius = 30
        threshold = 8.0
        min_spacing = max(20, int(width * 0.012))
        min_step = width * 0.10
        max_step = width * 0.18
    else:
        length = height
        values = [
            sum(pixels[x, y] for x in range(int(width * 0.08), int(width * 0.92), 4))
            / len(range(int(width * 0.08), int(width * 0.92), 4))
            for y in range(height)
        ]
        local_radius = 20
        threshold = 5.0
        min_spacing = max(10, int(height * 0.018))
        min_step = height * 0.08
        max_step = height * 0.18

    smooth = [
        sum(values[max(0, index - 2):min(length, index + 3)])
        / len(values[max(0, index - 2):min(length, index + 3)])
        for index in range(length)
    ]
    scores = []
    for index, value in enumerate(smooth):
        left = max(0, index - local_radius)
        right = min(length, index + local_radius + 1)
        scores.append(sum(smooth[left:right]) / (right - left) - value)

    local_peaks = [
        index for index in range(4, length - 4)
        if scores[index] >= threshold
        and scores[index] == max(scores[index - 4:index + 5])
    ]
    candidates: list[int] = []
    for index in sorted(local_peaks, key=lambda value: scores[value], reverse=True):
        if all(abs(index - selected) >= min_spacing for selected in candidates):
            candidates.append(index)
    candidates.sort()
    if len(candidates) < count:
        return None

    best: tuple[float, list[int]] | None = None
    tolerance = length * 0.025
    for first in candidates:
        for last in candidates:
            if last <= first:
                continue
            step = (last - first) / (count - 1)
            if not min_step <= step <= max_step:
                continue
            selected: list[int] = []
            error = 0.0
            for offset in range(count):
                target = first + step * offset
                nearest = min(candidates, key=lambda value: abs(value - target))
                distance = abs(nearest - target)
                if distance > tolerance or nearest in selected:
                    break
                selected.append(nearest)
                error += distance / step
            if len(selected) != count:
                continue
            strength = sum(min(scores[value], 80.0) / 80.0 for value in selected)
            objective = error - strength * 0.08
            if best is None or objective < best[0]:
                best = (objective, selected)
    return best[1] if best else None


def detect_judgement_rows_and_columns(image: Image.Image) -> tuple[list[float], list[int]] | None:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()

    label_rows: list[int] = []
    for y in range(height):
        score = 0
        for x in range(int(width * 0.02), int(width * 0.26), 2):
            r, g, b = pixels[x, y]
            brightness = (r + g + b) / 3
            if b >= 60 and r <= 95 and g <= 130 and b >= r + 16 and brightness <= 165:
                score += 1
        if score >= width * 0.035:
            label_rows.append(y)

    label_ranges = [
        row_range for row_range in cluster_indexes(label_rows, max_gap=6)
        if row_range[1] - row_range[0] >= height * 0.28
    ]
    if label_ranges:
        label_top, label_bottom = max(label_ranges, key=lambda row_range: row_range[1] - row_range[0])
        row_step = (label_bottom - label_top) / 5
        row_centers = [label_top + row_step * (index + 0.5) for index in range(5)]
    else:
        row_centers = []

    horizontal: list[int] = []
    for y in range(height):
        score = 0
        for x in range(int(width * 0.05), int(width * 0.94), 2):
            if is_judgement_grid_pixel(*pixels[x, y]):
                score += 1
        if score >= width * 0.10:
            horizontal.append(y)
    h_lines = [
        (start + end) / 2
        for start, end in cluster_indexes(horizontal, max_gap=4)
        if end - start >= 2
    ]
    h_lines = sorted(h_lines)

    # Dark grid lines survive JPEG recompression better than the blue color
    # mask. Resolve them before the color-based path can give up early.
    row_line_image = image.crop((0, 0, max(1, int(width * 0.85)), height))
    regular_row_boundaries = detect_regular_dark_lines(
        row_line_image,
        "horizontal",
        6,
    )
    if regular_row_boundaries:
        gaps = [
            right - left
            for left, right in zip(regular_row_boundaries, regular_row_boundaries[1:])
        ]
        median_gap = sorted(gaps)[len(gaps) // 2]
        if (
            min(gaps) < median_gap * 0.72
            or max(gaps) > median_gap * 1.28
        ):
            # JPEG blocks can displace one horizontal line while the bottom
            # table edge remains clear. Rebuild the six boundaries from that
            # edge instead of prepending a false line above TAP.
            last_boundary = regular_row_boundaries[-1]
            if (
                height * 0.07 <= median_gap <= height * 0.18
                and last_boundary >= height * 0.72
                and last_boundary - median_gap * 5 >= 0
            ):
                regular_row_boundaries = [
                    int(round(last_boundary - median_gap * offset))
                    for offset in range(5, -1, -1)
                ]
            else:
                regular_row_boundaries = None
    if not regular_row_boundaries:
        partial_boundaries = detect_regular_dark_lines(
            row_line_image,
            "horizontal",
            5,
        )
        if partial_boundaries:
            gaps = sorted(
                right - left
                for left, right in zip(partial_boundaries, partial_boundaries[1:])
            )
            row_step = gaps[len(gaps) // 2]
            if gaps[0] >= row_step * 0.72 and gaps[-1] <= row_step * 1.28:
                if partial_boundaries[-1] >= height * 0.75:
                    inferred = partial_boundaries[0] - row_step
                    if inferred >= 0:
                        regular_row_boundaries = [inferred, *partial_boundaries]
                else:
                    inferred = partial_boundaries[-1] + row_step
                    if inferred < height:
                        regular_row_boundaries = [*partial_boundaries, inferred]

    if regular_row_boundaries:
        row_centers = [
            (regular_row_boundaries[index] + regular_row_boundaries[index + 1]) / 2
            for index in range(5)
        ]
    elif not row_centers:
        h_lines = [
            line for line in h_lines
            if height * 0.08 <= line <= height * 0.96
        ]
        if len(h_lines) < 6:
            return None

        best_lines: list[float] | None = None
        best_error: float | None = None
        for start in range(0, len(h_lines) - 5):
            candidate = h_lines[start:start + 6]
            gaps = [b - a for a, b in zip(candidate, candidate[1:])]
            avg_gap = sum(gaps) / len(gaps)
            if avg_gap <= 0:
                continue
            error = sum(abs(gap - avg_gap) for gap in gaps) / avg_gap
            if best_error is None or error < best_error:
                best_error = error
                best_lines = candidate
        if not best_lines:
            return None
        row_centers = [(best_lines[index] + best_lines[index + 1]) / 2 for index in range(5)]

    # The full grid has one label column followed by five numeric columns.
    # Detect all seven boundaries, then discard the label column dynamically.
    full_column_bounds = detect_regular_dark_lines(image, "vertical", 7)
    numeric_column_bounds = detect_regular_dark_lines(image, "vertical", 6)

    def label_column_fill_ratio(left: int, right: int) -> float:
        sample_left = max(0, left + 6)
        sample_right = min(width, right - 6)
        sample_top = int(height * 0.20)
        sample_bottom = int(height * 0.92)
        sampled = 0
        label_pixels = 0
        for x in range(sample_left, sample_right, 4):
            for y in range(sample_top, sample_bottom, 4):
                sampled += 1
                r, g, b = pixels[x, y]
                brightness = (r + g + b) / 3
                if (
                    b >= 60
                    and r <= 95
                    and g <= 130
                    and b >= r + 16
                    and brightness <= 165
                ):
                    label_pixels += 1
        return label_pixels / sampled if sampled else 0.0

    full_grid_has_label_column = bool(
        full_column_bounds
        and label_column_fill_ratio(
            full_column_bounds[0],
            full_column_bounds[1],
        ) >= 0.35
    )
    full_grid_is_regular = False
    if full_column_bounds:
        full_gaps = [
            right - left
            for left, right in zip(full_column_bounds, full_column_bounds[1:])
        ]
        full_step = sorted(full_gaps)[len(full_gaps) // 2]
        full_grid_is_regular = (
            min(full_gaps) >= full_step * 0.82
            and max(full_gaps) <= full_step * 1.18
        )
    numeric_prefix_with_label = None
    numeric_grid_is_regular = False
    if numeric_column_bounds:
        numeric_gaps = [
            right - left
            for left, right in zip(
                numeric_column_bounds,
                numeric_column_bounds[1:],
            )
        ]
        numeric_step = sorted(numeric_gaps)[len(numeric_gaps) // 2]
        numeric_grid_is_regular = (
            min(numeric_gaps) >= numeric_step * 0.75
            and max(numeric_gaps) <= numeric_step * 1.25
        )
        trailing_gaps = [
            right - left
            for left, right in zip(
                numeric_column_bounds[1:],
                numeric_column_bounds[2:],
            )
        ]
        if trailing_gaps:
            trailing_step = sorted(trailing_gaps)[len(trailing_gaps) // 2]
            if (
                numeric_column_bounds[0] < width * 0.22
                and width * 0.16 <= numeric_column_bounds[1] <= width * 0.36
                and label_column_fill_ratio(
                    numeric_column_bounds[0],
                    numeric_column_bounds[1],
                ) >= 0.35
                and min(trailing_gaps) >= trailing_step * 0.82
                and max(trailing_gaps) <= trailing_step * 1.18
            ):
                numeric_prefix_with_label = [
                    *numeric_column_bounds[1:],
                    min(width, numeric_column_bounds[-1] + trailing_step),
                ]
    numeric_matches_full_grid = False
    if full_column_bounds and numeric_column_bounds:
        numeric_gaps = [
            right - left
            for left, right in zip(numeric_column_bounds, numeric_column_bounds[1:])
        ]
        numeric_step = sorted(numeric_gaps)[len(numeric_gaps) // 2]
        numeric_matches_full_grid = (
            min(numeric_gaps) >= numeric_step * 0.75
            and max(numeric_gaps) <= numeric_step * 1.25
            and all(
                abs(numeric - full) <= numeric_step * 0.08
                for numeric, full in zip(
                    numeric_column_bounds[:-1],
                    full_column_bounds[1:-1],
                )
            )
        )
    expanded_column_bounds = detect_regular_dark_lines(image, "vertical", 8)
    expanded_is_regular = False
    if expanded_column_bounds:
        expanded_gaps = [
            right - left
            for left, right in zip(expanded_column_bounds, expanded_column_bounds[1:])
        ]
        expanded_median = sorted(expanded_gaps)[len(expanded_gaps) // 2]
        expanded_is_regular = (
            min(expanded_gaps) >= expanded_median * 0.85
            and max(expanded_gaps) <= expanded_median * 1.15
        )

    expanded_adds_leading_boundary = False
    if expanded_is_regular and full_column_bounds:
        expanded_step = sorted(expanded_gaps)[len(expanded_gaps) // 2]
        expanded_adds_leading_boundary = all(
            abs(current - expanded) <= expanded_step * 0.08
            for current, expanded in zip(
                full_column_bounds,
                expanded_column_bounds[1:],
            )
        )

    if expanded_adds_leading_boundary:
        # The eight-line sequence includes the left table edge, the label
        # separator, five numeric columns, and one unrelated line beside the
        # table. Keep the separator through the numeric right edge.
        detected_columns = expanded_column_bounds[1:7]
    elif full_grid_is_regular and full_grid_has_label_column:
        detected_columns = full_column_bounds[1:]
    elif numeric_prefix_with_label:
        # JPEG artifacts often hide the far-right edge while preserving the
        # label edge, label separator, and first four numeric separators.
        # Drop the label edge and infer only the missing outer boundary.
        detected_columns = numeric_prefix_with_label
    elif numeric_matches_full_grid:
        # JPEG recompression may weaken the right table edge enough to confuse
        # its color score. Six regular lines aligned with the trailing lines of
        # the full seven-line grid are the five numeric columns directly.
        detected_columns = numeric_column_bounds
    elif numeric_grid_is_regular and not full_grid_has_label_column:
        detected_columns = numeric_column_bounds
    else:
        detected_columns = None
    if (
        detected_columns is None
        and not numeric_prefix_with_label
        and not full_grid_is_regular
        and not numeric_matches_full_grid
        and not expanded_adds_leading_boundary
        and full_column_bounds
        and full_grid_has_label_column
    ):
        rgb = image.convert("RGB")
        pixels = rgb.load()
        blue_scores = []
        for line_x in full_column_bounds:
            blue_scores.append(sum(
                is_table_blue_pixel(*pixels[x, y])
                for x in range(max(0, line_x - 5), min(width, line_x + 6))
                for y in range(height)
            ))
        reference_scores = sorted(blue_scores[1:-1])
        reference_score = reference_scores[len(reference_scores) // 2]
        if blue_scores[-1] < reference_score * 0.45:
            detected_columns = full_column_bounds[:-1]
        else:
            detected_columns = full_column_bounds[1:]
    elif (
        detected_columns is None
        and not numeric_prefix_with_label
        and not full_grid_is_regular
        and not numeric_matches_full_grid
        and not expanded_adds_leading_boundary
    ):
        detected_columns = numeric_column_bounds
        if detected_columns and detected_columns[-1] < width * 0.90:
            gaps = sorted(
                right - left
                for left, right in zip(detected_columns, detected_columns[1:])
            )
            column_step = gaps[len(gaps) // 2]
            available = width - detected_columns[-1]
            if available >= column_step * 0.45:
                inferred = min(width, detected_columns[-1] + column_step)
                detected_columns = [*detected_columns[1:], inferred]
    if detected_columns:
        col_bounds = detected_columns
    else:
        table_left = int(width * 0.25)
        table_right = int(width * 0.94)
        step = (table_right - table_left) / 5
        col_bounds = [int(round(table_left + step * index)) for index in range(6)]
    return row_centers, col_bounds


def cropper_judgement_has_left_header(image: Image.Image) -> bool:
    """Return whether a cropper pose image still contains the row labels."""
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    sampled = 0
    label_pixels = 0
    dark_label_pixels = 0
    for x in range(0, max(1, int(width * 0.20)), 3):
        for y in range(int(height * 0.10), int(height * 0.94), 3):
            sampled += 1
            r, g, b = pixels[x, y]
            brightness = (r + g + b) / 3
            if brightness <= 70:
                dark_label_pixels += 1
            if (
                b >= 60
                and r <= 95
                and g <= 130
                and b >= r + 16
                and brightness <= 165
            ):
                label_pixels += 1
    return bool(
        sampled
        and (
            label_pixels / sampled >= 0.45
            or dark_label_pixels / sampled >= 0.45
        )
    )


def cropper_judgement_has_top_header(
    image: Image.Image,
    output_dir: str | Path | None,
    engine: PaddleOcrEngine,
) -> bool:
    """Return whether the first of six cropper rows is the column header."""
    top_strip = image.crop((0, 0, image.width, max(1, int(image.height * 0.23))))
    prepared = prepare_ocr_image_data(top_strip, "sub_judgement_column")
    if output_dir is not None:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        top_strip.save(output / "top_header.png")
        prepared.save(output / "top_header_ocr.png")

    header_labels = {"CRITICAL", "PERFECT", "GREAT", "GOOD", "MISS"}
    return any(
        normalize_label_text(str(item.get("text", ""))) in header_labels
        for item in engine.read(prepared)
    )


def detect_cropper_numeric_row_centers(
    image: Image.Image,
    col_bounds: list[int],
) -> list[float] | None:
    """Fit numeric row centers from the blue grid in at least two columns."""
    detected = []
    for index in range(5):
        boundaries = detect_local_judgement_row_boundaries(
            image,
            col_bounds[index],
            col_bounds[index + 1],
        )
        if boundaries is not None:
            detected.append((
                (col_bounds[index] + col_bounds[index + 1]) / 2,
                boundaries,
            ))
    if len(detected) < 2:
        return None

    steps = [
        sorted(right - left for left, right in zip(bounds, bounds[1:]))[2]
        for _, bounds in detected
    ]
    median_step = sorted(steps)[len(steps) // 2]
    if median_step <= 0 or any(
        step < median_step * 0.78 or step > median_step * 1.22
        for step in steps
    ):
        return None

    target_x = image.width / 2
    fitted = []
    for row_index in range(5):
        points = [
            (x, (bounds[row_index] + bounds[row_index + 1]) / 2)
            for x, bounds in detected
        ]
        mean_x = sum(x for x, _ in points) / len(points)
        mean_y = sum(y for _, y in points) / len(points)
        denominator = sum((x - mean_x) ** 2 for x, _ in points)
        slope = (
            sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator
            if denominator
            else 0.0
        )
        fitted.append(mean_y + slope * (target_x - mean_x))
    return fitted


def recognize_judgement_row_centers(
    image: Image.Image,
    col_bounds: list[int],
    fallback_centers: list[float],
    output_dir: str | Path | None,
    engine: PaddleOcrEngine,
) -> list[float]:
    row_names = ("TAP", "HOLD", "SLIDE", "TOUCH", "BREAK")
    gaps = [right - left for left, right in zip(fallback_centers, fallback_centers[1:])]
    fallback_step = sum(gaps) / len(gaps) if gaps else image.height / 7
    column_widths = [right - left for left, right in zip(col_bounds, col_bounds[1:])]
    column_width = sum(column_widths) / len(column_widths)
    left = max(0, int(round(col_bounds[0] - column_width * 1.30)))
    right = max(left + 1, col_bounds[0] - max(5, int(image.width * 0.004)))
    top = max(0, int(round(fallback_centers[0] - fallback_step * 0.72)))
    bottom = min(image.height, int(round(fallback_centers[-1] + fallback_step * 0.72)))
    if right <= left or bottom <= top:
        return fallback_centers

    label_image = image.crop((left, top, right, bottom))
    prepared = prepare_ocr_image_data(label_image, "sub_judgement_column")
    if output_dir is not None:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        label_image.save(output / "row_labels.png")
        prepared.save(output / "row_labels_ocr.png")

    anchors: list[tuple[int, float]] = []
    for item in engine.read(prepared):
        label = normalize_label_text(str(item.get("text", "")))
        center = item_center(item)
        if center is None:
            continue
        for index, expected in enumerate(row_names):
            if label == expected:
                anchors.append((index, top + center[1] / 3))
                break
    if not anchors:
        return fallback_centers

    step_candidates = [
        (right_anchor - left_anchor) / (right_index - left_index)
        for left_pos, (left_index, left_anchor) in enumerate(anchors)
        for right_index, right_anchor in anchors[left_pos + 1:]
        if right_index > left_index and right_anchor > left_anchor
    ]
    if step_candidates:
        ordered_steps = sorted(step_candidates)
        fitted_step = ordered_steps[len(ordered_steps) // 2]
    else:
        fitted_step = fallback_step
    if not image.height * 0.05 <= fitted_step <= image.height * 0.20:
        fitted_step = fallback_step

    intercepts = sorted(center - index * fitted_step for index, center in anchors)
    intercept = intercepts[len(intercepts) // 2]
    fitted = [intercept + index * fitted_step for index in range(5)]
    if any(center < 0 or center >= image.height for center in fitted[:4]):
        return fallback_centers
    return fitted


def detect_local_judgement_row_boundaries(
    image: Image.Image,
    left: int,
    right: int,
) -> list[float] | None:
    """Find the six numeric-row boundaries inside one perspective column."""
    rgb = image.convert("RGB")
    pixels = rgb.load()
    sample_left = max(0, left + max(6, int((right - left) * 0.05)))
    sample_right = min(image.width, right - max(6, int((right - left) * 0.05)))
    sample_x = range(sample_left, sample_right, 3)
    sample_count = len(sample_x)
    if sample_count < 8:
        return None

    row_scores = [
        sum(is_judgement_grid_pixel(*pixels[x, y]) for x in sample_x)
        for y in range(image.height)
    ]
    minimum_score = max(4, int(sample_count * 0.10))
    ranges = cluster_indexes(
        [y for y, score in enumerate(row_scores) if score >= minimum_score],
        max_gap=5,
    )
    candidates: list[tuple[float, float]] = []
    for start, end in ranges:
        if end - start < 4:
            continue
        weights = row_scores[start:end + 1]
        total_weight = sum(weights)
        center = (
            sum((start + offset) * weight for offset, weight in enumerate(weights))
            / total_weight
            if total_weight
            else (start + end) / 2
        )
        candidates.append((center, max(weights) / sample_count))

    if len(candidates) < 6:
        return None

    best: tuple[float, list[float]] | None = None
    height = image.height
    for first_index, (first, _) in enumerate(candidates):
        for last, _ in candidates[first_index + 5:]:
            step = (last - first) / 5
            if not height * 0.08 <= step <= height * 0.18:
                continue
            selected: list[float] = []
            error = 0.0
            strength = 0.0
            for offset in range(6):
                target = first + step * offset
                center, score = min(candidates, key=lambda item: abs(item[0] - target))
                distance = abs(center - target)
                if distance > step * 0.24 or center in selected:
                    break
                selected.append(center)
                error += distance / step
                strength += min(score, 1.0)
            if len(selected) != 6:
                continue
            objective = error - strength * 0.025
            if best is None or objective < best[0]:
                best = (objective, selected)
    if best is None:
        return None
    selected = best[1]
    gaps = sorted(right - left for left, right in zip(selected, selected[1:]))
    fitted_step = gaps[len(gaps) // 2]
    intercepts = sorted(
        center - index * fitted_step
        for index, center in enumerate(selected)
    )
    intercept = intercepts[len(intercepts) // 2]
    fitted = [intercept + index * fitted_step for index in range(6)]
    if fitted[0] < 0 or fitted[-1] > image.height + fitted_step * 0.10:
        return None
    return fitted


def rectify_judgement_numeric_grid(
    image: Image.Image,
    col_bounds: list[int],
) -> Image.Image | None:
    """Rectify the perspective numeric grid before slicing its 25 cells."""
    detected = []
    for index in range(5):
        boundaries = detect_local_judgement_row_boundaries(
            image,
            col_bounds[index],
            col_bounds[index + 1],
        )
        if boundaries:
            detected.append((
                (col_bounds[index] + col_bounds[index + 1]) / 2,
                boundaries,
            ))
    def regression_y(
        points: list[tuple[float, list[float]]],
        boundary_index: int,
        target_x: float,
    ) -> float:
        values = [(x, bounds[boundary_index]) for x, bounds in points]
        mean_x = sum(x for x, _ in values) / len(values)
        mean_y = sum(y for _, y in values) / len(values)
        denominator = sum((x - mean_x) ** 2 for x, _ in values)
        slope = (
            sum((x - mean_x) * (y - mean_y) for x, y in values)
            / denominator
            if denominator
            else 0.0
        )
        return mean_y + slope * (target_x - mean_x)

    # A damaged JPEG can make one column detect the previous or next row while
    # preserving the row spacing. Repair only that explicit whole-row offset;
    # leave the normal perspective tolerances unchanged for every other image.
    if len(detected) >= 4:
        baseline_candidates = []
        for candidate in itertools.combinations(detected, 3):
            candidate = list(candidate)
            if not local_judgement_boundaries_are_consistent(candidate):
                continue
            residual = sum(
                abs(
                    value
                    - regression_y(candidate, boundary_index, x)
                )
                for x, boundaries in candidate
                for boundary_index, value in enumerate(boundaries)
            ) / 18
            baseline_candidates.append((residual, candidate))
        if baseline_candidates:
            _, baseline = min(baseline_candidates, key=lambda item: item[0])
            baseline_x = {x for x, _ in baseline}
            baseline_steps = [
                sorted(
                    right - left
                    for left, right in zip(bounds, bounds[1:])
                )[2]
                for _, bounds in baseline
            ]
            baseline_step = sorted(baseline_steps)[len(baseline_steps) // 2]
            normalized = []
            for x, bounds in detected:
                if x in baseline_x:
                    normalized.append((x, bounds))
                    continue
                gaps = sorted(
                    right - left
                    for left, right in zip(bounds, bounds[1:])
                )
                local_step = gaps[len(gaps) // 2]
                shifted_candidates = []
                for row_shift in range(-2, 3):
                    shifted = [
                        value + row_shift * local_step for value in bounds
                    ]
                    residual = sum(
                        abs(
                            shifted[index]
                            - regression_y(baseline, index, x)
                        )
                        for index in range(6)
                    ) / 6
                    shifted_candidates.append(
                        (residual, abs(row_shift), row_shift, shifted)
                    )
                unshifted_residual = next(
                    residual
                    for residual, _, row_shift, _ in shifted_candidates
                    if row_shift == 0
                )
                residual, _, row_shift, shifted = min(shifted_candidates)
                if (
                    row_shift
                    and unshifted_residual >= baseline_step * 0.55
                    and residual <= baseline_step * 0.18
                    and unshifted_residual - residual >= baseline_step * 0.45
                ):
                    normalized.append((x, shifted))
                else:
                    normalized.append((x, bounds))
            detected = normalized

    all_detected = detected
    consistent_detected = None
    for count in range(len(detected), 2, -1):
        for candidate in itertools.combinations(detected, count):
            if local_judgement_boundaries_are_consistent(list(candidate)):
                consistent_detected = list(candidate)
                break
        if consistent_detected is not None:
            break
    if consistent_detected is None:
        return None
    detected = consistent_detected

    selected_x = {x for x, _ in detected}
    baseline_steps = [
        sorted(
            right - left
            for left, right in zip(bounds, bounds[1:])
        )[2]
        for _, bounds in detected
    ]
    baseline_step = sorted(baseline_steps)[len(baseline_steps) // 2]
    for x, bounds in all_detected:
        if x in selected_x:
            continue
        gaps = sorted(
            right - left for left, right in zip(bounds, bounds[1:])
        )
        local_step = gaps[len(gaps) // 2]
        shifted_candidates = []
        for row_shift in range(-2, 3):
            shifted = [value + row_shift * local_step for value in bounds]
            residual = sum(
                abs(
                    shifted[index]
                    - regression_y(detected, index, x)
                )
                for index in range(6)
            ) / 6
            shifted_candidates.append((residual, abs(row_shift), shifted))
        residual, _, shifted = min(shifted_candidates)
        candidate = [*detected, (x, shifted)]
        if (
            residual <= baseline_step * 0.18
            and local_judgement_boundaries_are_consistent(candidate)
        ):
            detected = candidate
            selected_x.add(x)
    detected.sort(key=lambda item: item[0])

    def fitted_y(boundary_index: int, target_x: float) -> float:
        if target_x <= detected[0][0]:
            left, right = detected[0], detected[1]
        elif target_x >= detected[-1][0]:
            left, right = detected[-2], detected[-1]
        else:
            left, right = next(
                (left, right)
                for left, right in zip(detected, detected[1:])
                if left[0] <= target_x <= right[0]
            )
        left_x, left_bounds = left
        right_x, right_bounds = right
        ratio = (target_x - left_x) / (right_x - left_x)
        return (
            left_bounds[boundary_index]
            + (right_bounds[boundary_index] - left_bounds[boundary_index])
            * ratio
        )

    left = float(col_bounds[0])
    right = float(col_bounds[-1])
    top_left = fitted_y(0, left)
    top_right = fitted_y(0, right)
    bottom_left = fitted_y(5, left)
    bottom_right = fitted_y(5, right)
    left_height = bottom_left - top_left
    right_height = bottom_right - top_right
    if (
        right <= left
        or min(left_height, right_height) < image.height * 0.40
        or max(left_height, right_height) > image.height * 0.90
    ):
        return None

    output_width = max(500, int(round(right - left)))
    output_height = max(240, int(round((left_height + right_height) / 2)))
    mesh = []
    for column_index in range(5):
        source_left = float(col_bounds[column_index])
        source_right = float(col_bounds[column_index + 1])
        destination_left = int(round(output_width * column_index / 5))
        destination_right = int(round(output_width * (column_index + 1) / 5))
        for row_index in range(5):
            destination_top = int(round(output_height * row_index / 5))
            destination_bottom = int(round(output_height * (row_index + 1) / 5))
            source_top_left = fitted_y(row_index, source_left)
            source_top_right = fitted_y(row_index, source_right)
            source_bottom_left = fitted_y(row_index + 1, source_left)
            source_bottom_right = fitted_y(row_index + 1, source_right)
            mesh.append((
                (
                    destination_left,
                    destination_top,
                    destination_right,
                    destination_bottom,
                ),
                (
                    source_left,
                    source_top_left,
                    source_left,
                    source_bottom_left,
                    source_right,
                    source_bottom_right,
                    source_right,
                    source_top_right,
                ),
            ))
    return image.transform(
        (output_width, output_height),
        Image.Transform.MESH,
        mesh,
        resample=Image.Resampling.BICUBIC,
    )


def local_judgement_boundaries_are_consistent(
    detected: list[tuple[float, list[float]]],
) -> bool:
    """Reject columns that describe different row grids after JPEG damage."""
    if len(detected) < 3:
        return False

    column_steps = []
    for _, boundaries in detected:
        if len(boundaries) != 6:
            return False
        gaps = sorted(
            right - left for left, right in zip(boundaries, boundaries[1:])
        )
        column_steps.append(gaps[len(gaps) // 2])
    median_step = sorted(column_steps)[len(column_steps) // 2]
    if median_step <= 0 or any(
        step < median_step * 0.76 or step > median_step * 1.24
        for step in column_steps
    ):
        return False

    for boundary_index in range(6):
        points = [(x, boundaries[boundary_index]) for x, boundaries in detected]
        mean_x = sum(x for x, _ in points) / len(points)
        mean_y = sum(y for _, y in points) / len(points)
        denominator = sum((x - mean_x) ** 2 for x, _ in points)
        slope = (
            sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator
            if denominator
            else 0.0
        )
        if any(
            abs(y - (mean_y + slope * (x - mean_x))) > median_step * 0.34
            for x, y in points
        ):
            return False
    return True


def recognize_judgement_cells_direct(
    image: Image.Image,
    row_centers: list[float],
    col_bounds: list[int],
    row_gap: float,
    output_dir: str | Path | None,
    engine: PaddleOcrEngine,
) -> dict[str, dict[str, int]] | None:
    row_names = ("tap", "hold", "slide", "touch", "break")
    column_names = ("critical_perfect", "perfect", "great", "good", "miss")
    output = Path(output_dir) if output_dir is not None else None
    if output is not None:
        output.mkdir(parents=True, exist_ok=True)

    crops: list[Image.Image] = []
    slots: list[tuple[str, str]] = []
    local_row_boundaries = [
        detect_local_judgement_row_boundaries(
            image,
            col_bounds[index],
            col_bounds[index + 1],
        )
        for index in range(len(column_names))
    ]
    detected_local_boundaries = [
        (
            (col_bounds[index] + col_bounds[index + 1]) / 2,
            boundaries,
        )
        for index, boundaries in enumerate(local_row_boundaries)
        if boundaries is not None
    ]
    if (
        any(boundaries is None for boundaries in local_row_boundaries)
        or not local_judgement_boundaries_are_consistent(detected_local_boundaries)
    ):
        # Mixing locally detected rows with global rows shifts individual
        # columns when glare hides only part of the grid. Perspective
        # correction is useful only when all five columns describe one table.
        local_row_boundaries = [None] * len(column_names)
    for row_index, (row_name, center_y) in enumerate(zip(row_names, row_centers)):
        for index, column_name in enumerate(column_names):
            boundaries = local_row_boundaries[index]
            if boundaries:
                local_top = boundaries[row_index]
                local_bottom = boundaries[row_index + 1]
                local_height = local_bottom - local_top
                cell_top = max(0, int(round(local_top + local_height * 0.12)))
                cell_bottom = min(
                    image.height,
                    int(round(local_bottom - local_height * 0.12)),
                )
            else:
                cell_top = max(0, int(round(center_y - row_gap * 0.40)))
                cell_bottom = min(image.height, int(round(center_y + row_gap * 0.40)))
            cell_width = col_bounds[index + 1] - col_bounds[index]
            pad_x = max(8, int(cell_width * 0.16))
            cell_left = max(0, col_bounds[index] + pad_x)
            cell_right = min(image.width, col_bounds[index + 1] - pad_x)
            if cell_right <= cell_left or cell_bottom <= cell_top:
                return None
            cell = image.crop((cell_left, cell_top, cell_right, cell_bottom))
            crops.append(cell)
            slots.append((row_name, column_name))
            if output is not None:
                cell.save(output / f"direct_{row_name}_{column_name}.png")

    items = engine.read_cropped_lines(crops)
    if items is None:
        return None

    result: dict[str, dict[str, int]] = {row_name: {} for row_name in row_names}
    direct_scores: dict[tuple[str, str], float] = {}
    for (row_name, column_name), item in zip(slots, items):
        value = parse_column_int(str(item.get("text", "")))
        score = float(item.get("score", 0.0))
        if value is not None and (
            score >= 0.90
            or (
                column_name in {"critical_perfect", "perfect", "great"}
                and value >= 10
                and score >= 0.65
            )
            or (
                column_name in {"critical_perfect", "perfect"}
                and 2 <= value <= 9
                and score >= 0.60
            )
            or (value == 1 and score >= 0.60)
            or (value == 0 and score >= 0.80)
        ):
            result[row_name][column_name] = value
            direct_scores[(row_name, column_name)] = score

    secondary_images: list[Image.Image] = []
    secondary_slots: list[tuple[str, str, str]] = []
    for index, (row_name, column_name) in enumerate(slots):
        existing_value = result[row_name].get(column_name)
        crop = crops[index]
        if column_name in {"critical_perfect", "perfect"}:
            if existing_value == 0 or (
                existing_value is not None
                and (
                    crop.height >= 80
                    or direct_scores.get((row_name, column_name), 0.0) >= 0.90
                )
            ):
                continue
            secondary_images.append(
                ImageOps.autocontrast(crop.getchannel("B"), cutoff=1).convert("RGB")
            )
            secondary_slots.append((
                row_name,
                column_name,
                "lowres_blue" if existing_value is not None else "blue",
            ))
            if crop.height < 80:
                for left_ratio in (0.0, 0.15):
                    red_crop = crop.crop((
                        int(crop.width * left_ratio),
                        0,
                        crop.width,
                        max(1, int(crop.height * 0.90)),
                    )).getchannel("R")
                    secondary_images.append(
                        ImageOps.autocontrast(red_crop, cutoff=1).convert("RGB")
                    )
                    secondary_slots.append((row_name, column_name, "small_red"))
            continue
        if column_name == "great":
            if existing_value is not None:
                continue
            secondary_images.append(
                crop.crop((
                    int(crop.width * 0.12),
                    0,
                    crop.width,
                    max(1, int(crop.height * 0.80)),
                ))
            )
            secondary_slots.append((row_name, column_name, "tight"))
            secondary_images.append(enhance_judgement_color_contrast(crop))
            secondary_slots.append((row_name, column_name, "color_boost"))
            great_height_ratio = 0.84 if crop.height < 80 else 0.80
            for left_ratio in (0.0, 0.15):
                blue_crop = crop.crop((
                    int(crop.width * left_ratio),
                    0,
                    crop.width,
                    max(1, int(crop.height * great_height_ratio)),
                )).getchannel("B")
                secondary_images.append(
                    ImageOps.autocontrast(blue_crop, cutoff=1).convert("RGB")
                )
                secondary_slots.append((row_name, column_name, "great_blue"))
            continue
        if column_name not in {"good", "miss"}:
            continue
        if existing_value not in {None, 0}:
            continue

        grayscale = ImageOps.grayscale(crop)
        histogram = grayscale.histogram()
        pixel_count = sum(histogram)
        intensity_sum = sum(value * count for value, count in enumerate(histogram))
        background_count = 0
        background_sum = 0
        best_variance = -1.0
        otsu_threshold = 110
        for threshold, count in enumerate(histogram):
            background_count += count
            background_sum += threshold * count
            foreground_count = pixel_count - background_count
            if not background_count or not foreground_count:
                continue
            background_mean = background_sum / background_count
            foreground_mean = (intensity_sum - background_sum) / foreground_count
            variance = (
                background_count
                * foreground_count
                * (background_mean - foreground_mean) ** 2
            )
            if variance > best_variance:
                best_variance = variance
                otsu_threshold = threshold
        threshold_base = max(80, min(140, otsu_threshold))
        threshold = max(
            40,
            threshold_base - 20 if otsu_threshold > 160 else threshold_base,
        )
        secondary_images.extend([
            grayscale.point(
                lambda pixel, limit=threshold: 255 if pixel > limit else 0
            ).convert("RGB"),
            ImageOps.autocontrast(grayscale, cutoff=1).convert("RGB"),
            ImageOps.autocontrast(crop.getchannel("B"), cutoff=1).convert("RGB"),
            enhance_judgement_color_contrast(crop),
        ])
        secondary_slots.extend([
            (row_name, column_name, "threshold"),
            (row_name, column_name, "digit_gray"),
            (row_name, column_name, "digit_blue"),
            (row_name, column_name, "color_boost"),
        ])

    secondary_items = engine.read_cropped_lines(secondary_images) if secondary_images else []
    candidates: dict[tuple[str, str], list[tuple[int, float, str]]] = {}
    reliable_zeroes: set[tuple[str, str]] = set()
    if secondary_items is not None:
        for (row_name, column_name, mode), item in zip(secondary_slots, secondary_items):
            value = parse_column_int(str(item.get("text", "")))
            score = float(item.get("score", 0.0))
            if (
                value is None
                and mode == "great_blue"
                and normalize_text(str(item.get("text", ""))).upper() == "T"
            ):
                value = 1
            if (
                value == 0
                and mode in {"digit_gray", "digit_blue"}
                and score >= 0.80
            ):
                reliable_zeroes.add((row_name, column_name))
            if value is None or value <= 0:
                continue
            candidates.setdefault((row_name, column_name), []).append((
                value,
                score,
                mode,
            ))

    for (row_name, column_name), values in candidates.items():
        if (row_name, column_name) in reliable_zeroes:
            result[row_name][column_name] = 0
            continue
        blue_candidates = [
            (value, score)
            for value, score, mode in values
            if mode == "blue" and score >= 0.48
        ]
        if blue_candidates:
            result[row_name][column_name] = max(
                blue_candidates,
                key=lambda candidate: candidate[1],
            )[0]
            continue

        lowres_blue_candidates = [
            (value, score)
            for value, score, mode in values
            if mode == "lowres_blue" and score >= 0.78
        ]
        if lowres_blue_candidates:
            result[row_name][column_name] = max(
                lowres_blue_candidates,
                key=lambda candidate: candidate[1],
            )[0]
            continue

        small_red_groups: dict[int, list[float]] = {}
        for value, score, mode in values:
            if mode == "small_red" and score >= 0.55:
                small_red_groups.setdefault(value, []).append(score)
        agreed_small_red = [
            (value, scores)
            for value, scores in small_red_groups.items()
            if len(scores) >= 2
        ]
        if agreed_small_red:
            result[row_name][column_name] = max(
                agreed_small_red,
                key=lambda candidate: (len(candidate[1]), max(candidate[1])),
            )[0]
            continue

        tight_candidates = [
            (value, score)
            for value, score, mode in values
            if mode == "tight" and score >= 0.48
        ]
        if tight_candidates:
            result[row_name][column_name] = max(
                tight_candidates,
                key=lambda candidate: candidate[1],
            )[0]
            continue

        color_boost_candidates = [
            (value, score)
            for value, score, mode in values
            if mode == "color_boost" and score >= 0.58
        ]
        if color_boost_candidates:
            result[row_name][column_name] = max(
                color_boost_candidates,
                key=lambda candidate: candidate[1],
            )[0]
            continue

        great_blue_groups: dict[int, list[float]] = {}
        for value, score, mode in values:
            if mode == "great_blue" and score >= 0.25:
                great_blue_groups.setdefault(value, []).append(score)
        agreed_great = [
            (value, scores)
            for value, scores in great_blue_groups.items()
            if len(scores) >= 2
        ]
        if agreed_great:
            result[row_name][column_name] = max(
                agreed_great,
                key=lambda candidate: (len(candidate[1]), max(candidate[1])),
            )[0]
            continue

        isolated_digit_candidates = [
            (value, score)
            for value, score, mode in values
            if mode in {"digit_gray", "digit_blue"} and score >= 0.60
        ]
        if isolated_digit_candidates:
            result[row_name][column_name] = max(
                isolated_digit_candidates,
                key=lambda candidate: candidate[1],
            )[0]
            continue

        grouped: dict[int, list[float]] = {}
        for value, score, mode in values:
            if mode == "threshold" and score >= 0.50:
                grouped.setdefault(value, []).append(score)
        if not grouped:
            continue
        value, scores = max(
            grouped.items(),
            key=lambda item: (len(item[1]), max(item[1])),
        )
        if max(scores) >= 0.52:
            result[row_name][column_name] = value

    return {
        row_name: values
        for row_name, values in result.items()
        if values
    } or None


def recognize_judgement_cells_raw(
    image: Image.Image,
    row_centers: list[float],
    col_bounds: list[int],
    row_gap: float,
    engine: PaddleOcrEngine,
) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, float]]] | None:
    """Recognize isolated numeric cells without enhancement or value repair."""
    row_names = ("tap", "hold", "slide", "touch", "break")
    column_names = ("critical_perfect", "perfect", "great", "good", "miss")
    crops: list[Image.Image] = []
    slots: list[tuple[str, str]] = []
    for row_name, center_y in zip(row_names, row_centers):
        cell_top = max(0, int(round(center_y - row_gap * 0.40)))
        cell_bottom = min(image.height, int(round(center_y + row_gap * 0.40)))
        for index, column_name in enumerate(column_names):
            cell_width = col_bounds[index + 1] - col_bounds[index]
            pad_x = max(8, int(cell_width * 0.16))
            cell_left = max(0, col_bounds[index] + pad_x)
            cell_right = min(image.width, col_bounds[index + 1] - pad_x)
            if cell_right <= cell_left or cell_bottom <= cell_top:
                return None
            crops.append(image.crop((cell_left, cell_top, cell_right, cell_bottom)))
            slots.append((row_name, column_name))

    items = engine.read_cropped_lines(crops)
    if items is None:
        return None

    result: dict[str, dict[str, int]] = {row_name: {} for row_name in row_names}
    confidences: dict[str, dict[str, float]] = {
        row_name: {} for row_name in row_names
    }
    for (row_name, column_name), item in zip(slots, items):
        value = parse_column_int(str(item.get("text", "")))
        score = float(item.get("score", 0.0) or 0.0)
        if value is None or score < 0.90:
            continue
        result[row_name][column_name] = value
        confidences[row_name][column_name] = score
    return result, confidences


def recognize_judgement_by_columns(
    table_image_source: str | Path | Image.Image,
    output_dir: str | Path | None,
    engine: PaddleOcrEngine,
    layout_hint: str | None = None,
    confidence_out: dict[str, dict[str, float]] | None = None,
    target_rows: Iterable[str] | None = None,
) -> dict[str, dict[str, int]] | None:
    if isinstance(table_image_source, Image.Image):
        image = table_image_source.convert("RGB")
    else:
        with Image.open(table_image_source) as source:
            image = source.convert("RGB")
    width, height = image.size
    prefer_isolated_cells = False
    if layout_hint == "dxnet":
        row_centers = [
            height * ratio
            for ratio in (0.269, 0.431, 0.592, 0.756, 0.919)
        ]
        col_bounds = [
            int(round(width * ratio))
            for ratio in (0.173, 0.340, 0.504, 0.671, 0.830, 0.997)
        ]
        detect_row_labels = False
    elif layout_hint == "cropper_pt_pose_warp":
        layout = detect_judgement_rows_and_columns(image)
        has_left_header = cropper_judgement_has_left_header(image)
        prefer_isolated_cells = True
        if has_left_header:
            col_bounds = [
                int(round(width * ratio))
                for ratio in (0.184, 0.348, 0.513, 0.677, 0.842, 0.997)
            ]
        else:
            col_bounds = [
                int(round(width * index / 5))
                for index in range(6)
            ]
        if layout:
            row_centers, detected_col_bounds = layout
            if (
                not has_left_header
                or detected_col_bounds[0] <= width * 0.22
            ):
                col_bounds = detected_col_bounds
            if row_centers and row_centers[0] < height * 0.20:
                gaps = [b - a for a, b in zip(row_centers, row_centers[1:])]
                row_gap = sum(gaps) / len(gaps) if gaps else height / 7
                shifted_centers = row_centers[1:] + [row_centers[-1] + row_gap]
                if shifted_centers[-1] <= height * 0.98:
                    row_centers = shifted_centers
        else:
            row_centers = detect_cropper_numeric_row_centers(image, col_bounds)
            if row_centers is None:
                has_top_header = cropper_judgement_has_top_header(
                    image,
                    output_dir,
                    engine,
                )
                total_rows = 6 if has_top_header else 5
                first_data_row = 1 if has_top_header else 0
                row_centers = [
                    height * (first_data_row + index + 0.5) / total_rows
                    for index in range(5)
                ]
        detect_row_labels = False
    else:
        layout = detect_judgement_rows_and_columns(image)
        detect_row_labels = True
    if layout_hint not in FIXED_TABLE_LAYOUT_HINTS and not layout:
        # The cropper normalizes this field to the same table region. Use its
        # stable relative geometry when reflections hide the blue grid lines.
        row_centers = [height * (0.259 + index * 0.1205) for index in range(5)]
        col_bounds = [
            int(round(width * ratio))
            for ratio in (0.281, 0.410, 0.535, 0.659, 0.783, 0.906)
        ]
    elif layout_hint not in FIXED_TABLE_LAYOUT_HINTS:
        row_centers, col_bounds = layout

    row_names = ("tap", "hold", "slide", "touch", "break")
    column_names = ("critical_perfect", "perfect", "great", "good", "miss")
    target_row_set = (
        {row_name for row_name in target_rows if row_name in row_names}
        if target_rows is not None
        else set(row_names)
    )
    output = Path(output_dir) if output_dir is not None else None
    if output is not None:
        output.mkdir(parents=True, exist_ok=True)
    if layout_hint not in FIXED_TABLE_LAYOUT_HINTS:
        rectified = rectify_judgement_numeric_grid(image, col_bounds)
        if rectified is not None:
            image = rectified
            width, height = image.size
            row_centers = [height * (index + 0.5) / 5 for index in range(5)]
            col_bounds = [int(round(width * index / 5)) for index in range(6)]
            detect_row_labels = False
            if output is not None:
                image.save(output / "rectified_numeric_grid.png")
    if detect_row_labels:
        row_centers = recognize_judgement_row_centers(
            image,
            col_bounds,
            row_centers,
            output,
            engine,
        )
    gaps = [b - a for a, b in zip(row_centers, row_centers[1:])]
    row_gap = sum(gaps) / len(gaps) if gaps else max(44, height / 8)
    top = max(0, int(round(row_centers[0] - row_gap * 0.75)))
    bottom = min(height, int(round(row_centers[-1] + row_gap * 0.75)))
    row_targets = {
        row_name: (center - top) * SUB_JUDGEMENT_COLUMN_OCR_SCALE
        for row_name, center in zip(row_names, row_centers)
    }
    result: dict[str, dict[str, int]] = {row_name: {} for row_name in row_names}
    confidences: dict[str, dict[str, float]] = {row_name: {} for row_name in row_names}

    for index, column_name in enumerate(column_names):
        pad_x = max(5, int(width * 0.004))
        left = max(0, col_bounds[index] + pad_x)
        right = min(width, col_bounds[index + 1] - pad_x)
        if right <= left or bottom <= top:
            continue
        crop = image.crop((left, top, right, bottom))
        prepared = prepare_ocr_image_data(crop, "sub_judgement_column")
        if output is not None:
            crop.save(output / f"{column_name}.png")
            prepared.save(output / f"{column_name}_ocr.png")
        for item in engine.read(prepared):
            value = parse_column_int(str(item.get("text", "")))
            center = item_center(item)
            if value is None or center is None:
                continue
            try:
                item_score = float(item.get("score", 0.0) or 0.0)
            except (TypeError, ValueError):
                item_score = 0.0
            if layout_hint == "cropper_pt_pose_warp" and item_score < 0.50:
                continue
            box = item.get("box")
            if (
                isinstance(box, list)
                and len(box) == 4
                and all(isinstance(value, (int, float)) for value in box)
                and abs(float(box[3]) - float(box[1]))
                > row_gap * SUB_JUDGEMENT_COLUMN_OCR_SCALE * 1.45
            ):
                # A detector box spanning adjacent rows joins values such as
                # GOOD 5 and GOOD 0 into "50". Let isolated-cell OCR handle it.
                continue
            _, y = center
            row_name, target = min(row_targets.items(), key=lambda pair: abs(pair[1] - y))
            if abs(target - y) <= row_gap * SUB_JUDGEMENT_COLUMN_OCR_SCALE * 0.58:
                result[row_name][column_name] = value
                confidences[row_name][column_name] = item_score

    if prefer_isolated_cells and target_rows is None:
        isolated = recognize_judgement_cells_raw(
            image,
            row_centers,
            col_bounds,
            row_gap,
            engine,
        )
        if isolated is not None:
            isolated_values, isolated_confidences = isolated
            for row_name, values in isolated_values.items():
                for column_name, value in values.items():
                    result[row_name][column_name] = value
                    confidences[row_name][column_name] = (
                        isolated_confidences[row_name][column_name]
                    )

    if layout_hint not in FIXED_TABLE_LAYOUT_HINTS and target_rows is None:
        direct_values = recognize_judgement_cells_direct(
            image,
            row_centers,
            col_bounds,
            row_gap,
            output,
            engine,
        )
        if direct_values is not None:
            for row_name, values in direct_values.items():
                if row_name not in result:
                    continue
                for column_name, value in values.items():
                    if column_name not in result[row_name]:
                        result[row_name][column_name] = value
                        confidences[row_name][column_name] = 0.70

    for row_name, center_y in zip(row_names, row_centers):
        if row_name not in target_row_set:
            continue
        cell_top = max(0, int(round(center_y - row_gap * 0.32)))
        cell_bottom = min(height, int(round(center_y + row_gap * 0.32)))
        for index, column_name in enumerate(column_names):
            # MISS is especially prone to reading the hollow "0" as "8" when
            # OCR sees the whole column. Missing values are also rescanned as
            # isolated cells so small colored digits are not silently zeroed.
            existing_value = result[row_name].get(column_name)
            should_rescan_zero = (
                layout_hint == "cropper_pt_pose_warp"
                and existing_value == 0
                and row_name != "break"
                and column_name != "miss"
                and confidences[row_name].get(column_name, 0.0) < 0.90
            )
            if (
                existing_value is not None
                and not should_rescan_zero
                and not (column_name == "miss" and existing_value == 8)
            ):
                continue
            if layout_hint == "cropper_pt_pose_warp":
                pad_x = max(2, int(width * 0.004))
            else:
                pad_x = max(8, int(width * 0.008))
            cell_width = col_bounds[index + 1] - col_bounds[index]
            if column_name == "miss":
                cell_left = max(0, int(round(col_bounds[index] + cell_width * 0.40)))
            else:
                cell_left = max(0, col_bounds[index] + pad_x)
            cell_right = min(width, col_bounds[index + 1] - pad_x)
            if cell_right <= cell_left or cell_bottom <= cell_top:
                result[row_name][column_name] = 0
                continue
            cell = image.crop((cell_left, cell_top, cell_right, cell_bottom))
            prepared = prepare_ocr_image_data(cell, "sub_judgement_column")
            if output is not None:
                cell.save(output / f"{row_name}_{column_name}.png")
                prepared.save(output / f"{row_name}_{column_name}_ocr.png")
            cell_items = engine.read(prepared)
            value = None
            value_score = None
            low_confidence_value = None
            low_confidence_score = None
            for item in cell_items:
                candidate_value = parse_column_int(str(item.get("text", "")))
                if candidate_value is None:
                    continue
                score = item.get("score")
                if score is None or float(score) >= 0.90:
                    value = candidate_value
                    value_score = float(score) if score is not None else 1.0
                    break
                if low_confidence_value is None:
                    low_confidence_value = candidate_value
                    low_confidence_score = float(score)
            if value is None and column_name != "miss" and not should_rescan_zero:
                # Small models can lose the left edge of dim colored digits.
                # Retry only failed cells with a wider grayscale crop; applying
                # grayscale to the full table regresses otherwise clear values.
                fallback_top = max(0, int(round(center_y - row_gap * 0.42)))
                fallback_bottom = min(height, int(round(center_y + row_gap * 0.42)))
                fallback_left = max(
                    0,
                    int(round(col_bounds[index] - cell_width * 0.12)),
                )
                fallback_right = min(
                    width,
                    int(round(col_bounds[index + 1] + cell_width * 0.06)),
                )
                fallback_cell = image.crop((
                    fallback_left,
                    fallback_top,
                    fallback_right,
                    fallback_bottom,
                ))
                fallback_prepared = prepare_ocr_image_data(
                    fallback_cell,
                    "sub_judgement_column",
                )
                if output is not None:
                    fallback_cell.save(output / f"{row_name}_{column_name}_gray.png")
                    fallback_prepared.save(
                        output / f"{row_name}_{column_name}_gray_ocr.png"
                )
                for item in engine.read(fallback_prepared):
                    value = parse_column_int(str(item.get("text", "")))
                    if value is not None:
                        try:
                            value_score = float(item.get("score", 0.0) or 0.0)
                        except (TypeError, ValueError):
                            value_score = 0.0
                        break
            if value is None:
                if (
                    low_confidence_value is not None
                    and float(low_confidence_score or 0.0) >= 0.50
                ):
                    value = low_confidence_value
                    value_score = low_confidence_score
            if value is not None:
                result[row_name][column_name] = value
                confidences[row_name][column_name] = float(value_score or 0.0)
            else:
                result[row_name].setdefault(column_name, 0)
                confidences[row_name].setdefault(column_name, 0.0)

    for row_name in tuple(result):
        values = result[row_name]
        if (
            values.get("critical_perfect", 0) == 0
            and values.get("perfect", 0) == 0
            and values.get("great", 0) == 0
            and values.get("miss", 0) == 0
            and values.get("good", 0) > 0
        ):
            del result[row_name]

    result = {
        row: values
        for row, values in result.items()
        if row in target_row_set
        if values and any(int(value or 0) != 0 for value in values.values())
    }
    if confidence_out is not None:
        confidence_out.clear()
        confidence_out.update({
            row_name: {
                column_name: confidences.get(row_name, {}).get(column_name, 0.0)
                for column_name in values
            }
            for row_name, values in result.items()
        })
    return result or None


def parse_sub_judgement_items(items: list[dict[str, Any]]) -> dict[str, dict[str, int]] | None:
    labels = {
        "TAP": "tap",
        "HOLD": "hold",
        "SLIDE": "slide",
        "TOUCH": "touch",
        "BREAK": "break",
    }
    rows: list[tuple[str, float, float]] = []
    numeric_items: list[tuple[float, float, int]] = []

    for item in items:
        center = item_center(item)
        if center is None:
            continue
        x, y = center
        text = str(item.get("text", ""))
        label = normalize_label_text(text)
        for expected, row_name in labels.items():
            if expected == label:
                rows.append((row_name, x, y))
                break

        value = parse_item_int(text)
        if value is not None:
            numeric_items.append((x, y, value))

    if not rows:
        return None

    rows.sort(key=lambda row: row[2])
    y_values = [row[2] for row in rows]
    gaps = [b - a for a, b in zip(y_values, y_values[1:]) if b > a]
    row_tolerance = max(54.0, (sum(gaps) / len(gaps) * 0.58) if gaps else 64.0)

    result: dict[str, dict[str, int]] = {}
    for row_name, label_x, label_y in rows:
        row_values = [
            (x, value)
            for x, y, value in numeric_items
            if x > label_x + 40 and abs(y - label_y) <= row_tolerance
        ]
        row_values.sort(key=lambda value: value[0])
        if len(row_values) < 5:
            continue
        values = [value for _, value in row_values[:5]]
        result[row_name] = {
            "critical_perfect": values[0],
            "perfect": values[1],
            "great": values[2],
            "good": values[3],
            "miss": values[4],
        }

    return result or None


def normalize_judgement_table_values(
    values: dict[str, dict[str, int]] | None,
) -> dict[str, dict[str, int]] | None:
    if not values:
        return values
    normalized = {
        row_name: dict(row_values)
        for row_name, row_values in values.items()
    }
    break_values = normalized.get("break")
    if isinstance(break_values, dict):
        try:
            critical_perfect = int(break_values.get("critical_perfect", 0) or 0)
            perfect = int(break_values.get("perfect", 0) or 0)
            great = int(break_values.get("great", 0) or 0)
            good = int(break_values.get("good", 0) or 0)
            miss = int(break_values.get("miss", 0) or 0)
        except (TypeError, ValueError):
            return normalized
        if (
            critical_perfect == 0
            and perfect > 0
            and great > 0
            and good == 0
            and miss == 0
        ):
            normalized["break"] = {
                "critical_perfect": perfect,
                "perfect": great,
                "great": 0,
                "good": 0,
                "miss": 0,
            }
    return normalized


def parse_sub_judgement(text: str) -> dict[str, dict[str, int]] | None:
    normalized = unicodedata.normalize("NFKC", text or "").upper()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    labels = ("TAP", "HOLD", "SLIDE", "TOUCH", "BREAK")
    result: dict[str, dict[str, int]] = {}
    digit_pattern = r"([0-9OZ〇]{1,4})"
    separator_pattern = r"[^0-9OZ〇]+"
    for label in labels:
        match = re.search(
            label
            + separator_pattern
            + digit_pattern
            + separator_pattern
            + digit_pattern
            + separator_pattern
            + digit_pattern
            + separator_pattern
            + digit_pattern
            + separator_pattern
            + digit_pattern,
            normalized,
        )
        if not match:
            continue
        values = [parse_column_int(item) for item in match.groups()]
        if any(value is None for value in values):
            continue
        result[label.lower()] = {
            "critical_perfect": values[0],
            "perfect": values[1],
            "great": values[2],
            "good": values[3],
            "miss": values[4],
        }
    return result or None


def process_image_data(
    source_image: Image.Image,
    fields: Iterable[str],
    engine: PaddleOcrEngine,
    *,
    debug_output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run the production OCR pipeline entirely in memory."""
    started_at = time.perf_counter()
    debug_images = {} if debug_output_dir is not None else None
    metadata = crop_result_fields_in_memory(source_image, debug_images=debug_images)
    debug_metadata = None
    debug_input = None
    if debug_output_dir is not None:
        debug_metadata = save_crop_debug(source_image, metadata, debug_output_dir, debug_images=debug_images)
        debug_input = Path(debug_output_dir) / "ocr_input"
        debug_input.mkdir(parents=True, exist_ok=True)
    crop_seconds = time.perf_counter() - started_at
    selected_fields = tuple(fields)
    ocr_fields: dict[str, dict[str, Any]] = {}
    field_seconds: dict[str, float] = {}

    for field in selected_fields:
        field_started_at = time.perf_counter()
        field_meta = metadata["fields"].get(field)
        if not field_meta:
            continue
        if field == "sub_judgement_table":
            table_image = field_meta["image"]
            column_confidences: dict[str, dict[str, float]] = {}
            table_partial_values: dict[str, dict[str, int]] = {}
            column_values = recognize_judgement_with_table_model(
                table_image,
                partial_out=table_partial_values,
            )
            table_backend = "table_model"
            if column_values is None:
                table_backend = "column_fallback"
                fallback_image = table_image
                if field_meta.get("layout_hint") not in FIXED_TABLE_LAYOUT_HINTS:
                    fallback_image = prepare_ocr_image_data(table_image, field)
                if debug_input:
                    fallback_image.save(debug_input / f"{field}.png")
                fallback_target_rows = (
                    tuple(
                        row_name
                        for row_name in JUDGEMENT_ROW_NAMES
                        if row_name not in table_partial_values
                    )
                    if table_partial_values
                    else None
                )
                column_values = recognize_judgement_by_columns(
                    fallback_image,
                    debug_input / "sub_judgement_columns" if debug_input else None,
                    engine,
                    layout_hint=field_meta.get("layout_hint"),
                    confidence_out=column_confidences,
                    target_rows=fallback_target_rows,
                )
                if table_partial_values:
                    column_values = column_values or {}
                    column_values = {
                        **column_values,
                        **table_partial_values,
                    }
                    for row_name, row_values in table_partial_values.items():
                        column_confidences[row_name] = {
                            column_name: 1.0
                            for column_name in row_values
                        }
                    table_backend = "hybrid_table_column_fallback"
            column_values = normalize_judgement_table_values(column_values)
            logger.debug(
                "[Recognize] Judgement OCR result: backend=%s values=%s",
                table_backend,
                column_values,
            )
            ocr_fields[field] = {
                "items": [],
                "text": "",
                "column_values": column_values,
                "column_confidences": column_confidences,
            }
            if debug_metadata:
                ocr_fields[field]["crop"] = debug_metadata["fields"][field]["path"]
                ocr_fields[field]["prepared"] = str(debug_input / f"{field}.png") if table_backend != "table_model" else ocr_fields[field]["crop"]
            field_seconds[field] = time.perf_counter() - field_started_at
            continue

        prepared = prepare_ocr_image_data(field_meta["image"], field)
        if debug_input:
            prepared.save(debug_input / f"{field}.png")
        items = engine.read(prepared)
        ocr_fields[field] = {
            "items": items,
            "text": joined_text(items),
        }
        if debug_metadata:
            ocr_fields[field].update(crop=debug_metadata["fields"][field]["path"], prepared=str(debug_input / f"{field}.png"))
        field_seconds[field] = time.perf_counter() - field_started_at

    logger.debug(
        "[Recognize] Score OCR timing: layout=%s crop=%.3fs fields=%s total=%.3fs",
        metadata.get("layout", "arcade"),
        crop_seconds,
        ", ".join(
            f"{field}={seconds:.3f}s"
            for field, seconds in field_seconds.items()
        ),
        time.perf_counter() - started_at,
    )

    public_metadata = {
        "layout": metadata.get("layout", "arcade"),
        "screen": metadata["screen"],
        "fields": {
            name: {key: value for key, value in field.items() if key != "image"}
            for name, field in metadata["fields"].items()
        },
    }
    return {
        "source": "memory",
        "crop_metadata": debug_metadata or public_metadata,
        "ocr_fields": ocr_fields,
        "parsed": parse_result(ocr_fields),
    }


def process_image(
    image_path: str | Path,
    crop_output_dir: str | Path,
    fields: Iterable[str],
    engine: PaddleOcrEngine,
) -> dict[str, Any]:
    """Diagnostic file adapter; recognition uses the same production pipeline."""
    import shutil

    output = Path(crop_output_dir) / Path(image_path).stem
    if output.exists():
        shutil.rmtree(output)
    with Image.open(image_path) as image:
        result = process_image_data(image, fields, engine, debug_output_dir=output)
    result["source"] = str(image_path)
    result["crop_metadata"]["source"] = str(image_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR maimai result-screen field crops.")
    parser.add_argument("images", nargs="+", help="Image files or directories.")
    parser.add_argument("-o", "--output-dir", default="data/score_cropper_debug", help="Crop and OCR debug output directory.")
    parser.add_argument("--lang", default="japan", help="PaddleOCR language, for example japan, en, ch.")
    parser.add_argument("--fields", default=",".join(OCR_FIELDS), help="Comma-separated field names to OCR.")
    parser.add_argument("--pretty", action="store_true", help="Print a compact human-readable summary.")
    args = parser.parse_args()

    fields = tuple(item.strip() for item in args.fields.split(",") if item.strip())
    engine = PaddleOcrEngine(lang=args.lang)
    results = [process_image(path, args.output_dir, fields, engine) for path in iter_images(args.images)]

    if args.pretty:
        for result in results:
            parsed = result["parsed"]
            print(result["source"])
            print(f"  title: {parsed.get('title')}")
            print(f"  achievement: {parsed.get('achievement')}")
            print(f"  sub_judgement: {parsed.get('sub_judgement')}")
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
