#!/usr/bin/env python3
"""
Prototype maimai result-screen cropper.

This script is intentionally standalone. It is not imported by main.py and does
not register any bot command. It detects the colorful circular result display in
arcade cabinet photos, then exports fixed relative regions for later OCR tests.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps


_CROPPER_MODEL = None
_CROPPER_MODEL_UNAVAILABLE = False
_MAIN_SCREEN_MODEL = None
_MAIN_SCREEN_MODEL_UNAVAILABLE = False


@dataclass(frozen=True)
class Box:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def clamp(self, width: int, height: int) -> "Box":
        return Box(
            max(0, min(width, self.left)),
            max(0, min(height, self.top)),
            max(0, min(width, self.right)),
            max(0, min(height, self.bottom)),
        )

    def to_tuple(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.right, self.bottom


def _sample_mask_points(
    image: Image.Image,
    step: int = 4,
    main_screen_only: bool | None = None,
) -> list[tuple[int, int]]:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    points: list[tuple[int, int]] = []

    # Portrait machine photos place the sub-monitor above the circular screen.
    # Near-square crops contain only the main screen, so scanning from 34%
    # would discard its title/header and shift the detected circle downward.
    if main_screen_only is None:
        main_screen_only = height <= width * 1.16
    y_start = int(height * (0.10 if main_screen_only else 0.34))
    y_end = int(height * 0.96)
    x_margin = int(width * 0.035)

    for y in range(y_start, y_end, step):
        for x in range(x_margin, width - x_margin, step):
            r, g, b = pixels[x, y]
            mx = max(r, g, b)
            mn = min(r, g, b)
            saturation = mx - mn
            # Keep vivid result-screen pixels while dropping the white cabinet
            # glow and the dark plastic bezel.
            if mx >= 115 and saturation >= 42:
                # Blue/purple cabinet glow has high saturation too; require
                # enough red/yellow/green contribution to bias toward the UI.
                if r >= 90 or g >= 105:
                    points.append((x, y))
    return points


def _percentile(values: list[int], ratio: float) -> int:
    if not values:
        return 0
    values = sorted(values)
    index = int((len(values) - 1) * ratio)
    return values[index]


def detect_result_screen(
    image: Image.Image,
    main_screen_only: bool | None = None,
) -> Box:
    image = ImageOps.exif_transpose(image)
    width, height = image.size
    points = _sample_mask_points(image, main_screen_only=main_screen_only)
    if len(points) < 200:
        raise ValueError("could not find enough colorful result-screen pixels")

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    raw = Box(
        _percentile(xs, 0.015),
        _percentile(ys, 0.015),
        _percentile(xs, 0.985),
        _percentile(ys, 0.985),
    )

    # The mask mostly captures colorful UI, not the whole round screen. Expand
    # it into a near-square inner-screen box and bias slightly upward so the
    # song title/header are retained.
    cx = (raw.left + raw.right) / 2
    cy = (raw.top + raw.bottom) / 2
    side = max(raw.width * 1.17, raw.height * 1.10)
    side = min(side, width * 0.90, height * 0.72)
    cy -= side * 0.025

    box = Box(
        int(round(cx - side / 2)),
        int(round(cy - side / 2)),
        int(round(cx + side / 2)),
        int(round(cy + side / 2)),
    ).clamp(width, height)

    return box


def _sample_sub_screen_points(image: Image.Image, step: int = 4) -> list[tuple[int, int]]:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    points: list[tuple[int, int]] = []

    y_start = 0
    y_end = int(height * 0.255)
    x_margin = int(width * 0.12)

    for y in range(y_start, y_end, step):
        for x in range(x_margin, width - x_margin, step):
            r, g, b = pixels[x, y]
            mx = max(r, g, b)
            mn = min(r, g, b)
            saturation = mx - mn
            brightness = (r + g + b) / 3
            # The upper LCD is dim, but still has a rectangular block of lit
            # content. The cabinet and acrylic are darker or strongly pink.
            if brightness >= 82 and mx >= 95 and not (r > 150 and b > 120 and g < 85):
                if saturation <= 115 or b >= 85 or g >= 85:
                    points.append((x, y))
    return points


def _cluster_ranges(values: list[int], max_gap: int = 3) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start: int | None = None
    previous: int | None = None
    for value in values:
        if start is None:
            start = previous = value
            continue
        if previous is not None and value - previous <= max_gap:
            previous = value
            continue
        ranges.append((start, previous if previous is not None else value))
        start = previous = value
    if start is not None:
        ranges.append((start, previous if previous is not None else start))
    return ranges


def _load_cropper_model():
    global _CROPPER_MODEL, _CROPPER_MODEL_UNAVAILABLE
    if _CROPPER_MODEL_UNAVAILABLE:
        return None
    if _CROPPER_MODEL is not None:
        return _CROPPER_MODEL

    model_path = Path(__file__).with_name("judgement_table.pt")
    if not model_path.exists():
        _CROPPER_MODEL_UNAVAILABLE = True
        return None

    try:
        os.environ.setdefault(
            "MPLCONFIGDIR",
            str(Path(os.getenv("TMPDIR", "/tmp")) / "jietng_matplotlib"),
        )
        from ultralytics import YOLO

        _CROPPER_MODEL = YOLO(str(model_path))
    except Exception:
        _CROPPER_MODEL_UNAVAILABLE = True
        return None
    return _CROPPER_MODEL


def _load_main_screen_model():
    global _MAIN_SCREEN_MODEL, _MAIN_SCREEN_MODEL_UNAVAILABLE
    if _MAIN_SCREEN_MODEL_UNAVAILABLE:
        return None
    if _MAIN_SCREEN_MODEL is not None:
        return _MAIN_SCREEN_MODEL

    model_path = Path(__file__).with_name("main_screen.pt")
    if not model_path.exists():
        _MAIN_SCREEN_MODEL_UNAVAILABLE = True
        return None

    try:
        os.environ.setdefault(
            "MPLCONFIGDIR",
            str(Path(os.getenv("TMPDIR", "/tmp")) / "jietng_matplotlib"),
        )
        from ultralytics import YOLO

        _MAIN_SCREEN_MODEL = YOLO(str(model_path))
    except Exception:
        _MAIN_SCREEN_MODEL_UNAVAILABLE = True
        return None
    return _MAIN_SCREEN_MODEL


def _order_quad_points(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float32)
    if points.shape != (4, 2):
        raise ValueError(f"points must be (4, 2), got {points.shape}")

    ordered = np.zeros((4, 2), dtype=np.float32)
    point_sum = points.sum(axis=1)
    point_diff = np.diff(points, axis=1).reshape(-1)
    ordered[0] = points[np.argmin(point_sum)]
    ordered[2] = points[np.argmax(point_sum)]
    ordered[1] = points[np.argmin(point_diff)]
    ordered[3] = points[np.argmax(point_diff)]
    return ordered


def _box_from_quad(points: np.ndarray, width: int, height: int) -> Box:
    points = np.asarray(points, dtype=np.float32)
    left = int(np.floor(points[:, 0].min()))
    top = int(np.floor(points[:, 1].min()))
    right = int(np.ceil(points[:, 0].max()))
    bottom = int(np.ceil(points[:, 1].max()))
    return Box(left, top, right, bottom).clamp(width, height)


def _warp_quad(
    image: Image.Image,
    points: np.ndarray,
    *,
    expand_table_edges: bool = True,
    edge_expansion: dict[str, float] | None = None,
    y_adjust: dict[str, float] | None = None,
) -> Image.Image | None:
    try:
        rect = _order_quad_points(points)
    except ValueError:
        return None

    if expand_table_edges:
        edge_expansion = edge_expansion or {}
        top_expand = edge_expansion.get("top", 0.015)
        bottom_expand = edge_expansion.get("bottom", 0.060)
        left_expand = edge_expansion.get("left", 0.006)
        right_expand = edge_expansion.get("right", 0.008)
        left_top_expand = edge_expansion.get("left_top", left_expand)
        left_bottom_expand = edge_expansion.get("left_bottom", left_expand)
        right_top_expand = edge_expansion.get("right_top", right_expand)
        right_bottom_expand = edge_expansion.get("right_bottom", right_expand)
        top_left, top_right, bottom_right, bottom_left = rect
        left_vertical = bottom_left - top_left
        right_vertical = bottom_right - top_right
        top_horizontal = top_right - top_left
        bottom_horizontal = bottom_right - bottom_left
        rect[0] = rect[0] - left_vertical * top_expand - top_horizontal * left_top_expand
        rect[1] = rect[1] - right_vertical * top_expand + top_horizontal * right_top_expand
        rect[2] = rect[2] + right_vertical * bottom_expand + bottom_horizontal * right_bottom_expand
        rect[3] = rect[3] + left_vertical * bottom_expand - bottom_horizontal * left_bottom_expand

    if y_adjust:
        top_left, top_right, bottom_right, bottom_left = rect
        height_left = np.linalg.norm(bottom_left - top_left)
        height_right = np.linalg.norm(bottom_right - top_right)
        rect[0][1] += height_left * y_adjust.get("left_top", 0.0)
        rect[3][1] += height_left * y_adjust.get("left_bottom", 0.0)
        rect[1][1] += height_right * y_adjust.get("right_top", 0.0)
        rect[2][1] += height_right * y_adjust.get("right_bottom", 0.0)

    if expand_table_edges or y_adjust:
        rect[:, 0] = np.clip(rect[:, 0], 0, image.width - 1)
        rect[:, 1] = np.clip(rect[:, 1], 0, image.height - 1)

    top_left, top_right, bottom_right, bottom_left = rect
    width_top = np.linalg.norm(top_right - top_left)
    width_bottom = np.linalg.norm(bottom_right - bottom_left)
    height_left = np.linalg.norm(bottom_left - top_left)
    height_right = np.linalg.norm(bottom_right - top_right)
    output_width = int(round(max(width_top, width_bottom)))
    output_height = int(round(max(height_left, height_right)))
    if output_width < 120 or output_height < 40:
        return None

    destination = np.array(
        [
            [0, 0],
            [output_width - 1, 0],
            [output_width - 1, output_height - 1],
            [0, output_height - 1],
        ],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(rect, destination)
    source = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    warped = cv2.warpPerspective(
        source,
        matrix,
        (output_width, output_height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB))


def _warp_judgement_table_quad(image: Image.Image, points: np.ndarray) -> Image.Image | None:
    return _warp_quad(image, points)


def _main_screen_pose_image(image: Image.Image) -> tuple[Box | None, Image.Image | None]:
    model = _load_main_screen_model()
    if model is None:
        return None, None

    try:
        prediction = model.predict(image, imgsz=640, conf=0.15, verbose=False)[0]
    except Exception:
        return None, None

    keypoints = getattr(prediction, "keypoints", None)
    points_tensor = getattr(keypoints, "xy", None)
    if points_tensor is None or len(points_tensor) == 0:
        return None, None

    confidence_tensor = getattr(keypoints, "conf", None)
    width, height = image.size
    image_area = max(1, width * height)
    candidates: list[tuple[float, Box, Image.Image]] = []
    for index, raw_points in enumerate(points_tensor):
        points = np.asarray(raw_points.cpu(), dtype=np.float32)
        if points.shape != (4, 2) or not np.isfinite(points).all():
            continue
        box = _box_from_quad(points, width, height)
        if box.width <= 0 or box.height <= 0:
            continue
        aspect = box.width / max(1, box.height)
        area_ratio = (box.width * box.height) / image_area
        if aspect < 1.8 or area_ratio < 0.025:
            continue

        warped = _warp_main_screen_quad(image, points)
        if warped is None:
            continue
        warped_aspect = warped.width / max(1, warped.height)
        if warped_aspect < 1.8:
            continue

        if confidence_tensor is not None:
            confidence = float(np.asarray(confidence_tensor[index].cpu(), dtype=np.float32).mean())
        else:
            confidence = 0.5
        score = confidence * 10.0 + min(aspect, 5.0) * 0.35 + min(area_ratio * 10.0, 2.0)
        candidates.append((score, box, warped))

    if not candidates:
        return None, None
    _, box, warped = max(candidates, key=lambda item: item[0])
    return box, warped


def detect_main_screen_with_cropper_model(
    image: Image.Image,
) -> tuple[Box | None, Image.Image | None]:
    return _main_screen_pose_image(image)


def _warp_main_screen_quad(image: Image.Image, points: np.ndarray) -> Image.Image | None:
    return _warp_quad(
        image,
        points,
        expand_table_edges=True,
        edge_expansion={
            "top": 0.002,
            "bottom": 0.045,
            "left_top": 0.026,
            "left_bottom": 0.040,
            "right": 0.006,
        },
    )


def _cropper_pose_table(image: Image.Image) -> tuple[Box | None, Image.Image | None]:
    model = _load_cropper_model()
    if model is None:
        return None, None

    try:
        prediction = model.predict(image, imgsz=640, conf=0.15, verbose=False)[0]
    except Exception:
        return None, None

    keypoints = getattr(prediction, "keypoints", None)
    points_tensor = getattr(keypoints, "xy", None)
    if points_tensor is None or len(points_tensor) == 0:
        return None, None

    confidence_tensor = getattr(keypoints, "conf", None)
    width, height = image.size
    candidates: list[tuple[float, Box, Image.Image]] = []
    for index, raw_points in enumerate(points_tensor):
        points = np.asarray(raw_points.cpu(), dtype=np.float32)
        if points.shape != (4, 2) or not np.isfinite(points).all():
            continue
        box = _box_from_quad(points, width, height)
        if box.width <= 0 or box.height <= 0:
            continue
        aspect = box.width / max(1, box.height)
        center_y_ratio = ((box.top + box.bottom) / 2) / max(1, height)
        if center_y_ratio > 0.42 or aspect < 1.45:
            continue

        warped = _warp_judgement_table_quad(image, points)
        if warped is None:
            continue

        if confidence_tensor is not None:
            confidence = float(np.asarray(confidence_tensor[index].cpu(), dtype=np.float32).mean())
        else:
            confidence = 0.5
        score = confidence * 10.0 + (1.0 - abs(center_y_ratio - 0.14)) + min(aspect, 4.0) * 0.25
        candidates.append((score, box, warped))

    if not candidates:
        return None, None
    _, box, warped = max(candidates, key=lambda item: item[0])
    return box, warped


def detect_sub_screen_by_cropper_model(image: Image.Image) -> Box | None:
    model = _load_cropper_model()
    if model is None:
        return None

    try:
        prediction = model.predict(image, imgsz=640, conf=0.15, verbose=False)[0]
    except Exception:
        return None

    names = getattr(model, "names", {}) or getattr(prediction, "names", {}) or {}
    width, height = image.size
    candidates: list[tuple[float, Box]] = []
    for raw_box in getattr(prediction, "boxes", []) or []:
        try:
            cls_id = int(raw_box.cls[0])
            confidence = float(raw_box.conf[0])
            x1, y1, x2, y2 = [float(value) for value in raw_box.xyxy[0]]
        except (TypeError, ValueError, IndexError):
            continue

        box = Box(
            int(round(x1)),
            int(round(y1)),
            int(round(x2)),
            int(round(y2)),
        ).clamp(width, height)
        if box.width <= 0 or box.height <= 0:
            continue

        class_name = str(names.get(cls_id, "")).lower()
        aspect = box.width / max(1, box.height)
        center_y_ratio = ((box.top + box.bottom) / 2) / max(1, height)
        if center_y_ratio > 0.42 or aspect < 1.45:
            continue

        label_score = 2.0 if "screen" in class_name or "upper" in class_name else 0.0
        position_score = 1.0 - abs(center_y_ratio - 0.14)
        score = confidence * 10.0 + label_score + position_score + min(aspect, 4.0) * 0.25
        candidates.append((score, box))

    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def detect_sub_judgement_table_with_cropper_model(
    image: Image.Image,
) -> tuple[Box | None, Box | None, str, Image.Image | None]:
    table_box, table_image = _cropper_pose_table(image)
    if table_box is None or table_image is None:
        return None, None, "cropper_pt_missing", None
    return table_box, table_box, "cropper_pt_pose_warp", table_image


def detect_sub_screen(image: Image.Image) -> Box:
    image = ImageOps.exif_transpose(image)
    width, height = image.size
    points = _sample_sub_screen_points(image)
    if len(points) < 200:
        return Box(
            int(width * 0.220),
            0,
            int(width * 0.790),
            int(height * 0.225),
        )

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    raw = Box(
        _percentile(xs, 0.060),
        _percentile(ys, 0.045),
        _percentile(xs, 0.955),
        _percentile(ys, 0.960),
    )

    pad_x = int(raw.width * 0.025)
    pad_top = max(int(raw.height * 0.090), int(height * 0.012))
    return Box(
        raw.left - pad_x,
        raw.top - pad_top,
        raw.right + pad_x,
        raw.bottom,
    ).clamp(width, height)


def _is_table_blue_pixel(r: int, g: int, b: int) -> bool:
    brightness = (r + g + b) / 3
    blue_line = b >= 90 and g >= 45 and b >= r + 18 and 42 <= brightness <= 215
    row_label = b >= 70 and r <= 85 and g <= 120 and b >= r + 22 and brightness <= 145
    return blue_line or row_label


def detect_sub_judgement_table(image: Image.Image, sub_screen: Box) -> Box | None:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    search_bottom = min(
        height,
        sub_screen.bottom + max(1, int(sub_screen.height * 0.12)),
    )

    search = Box(
        max(0, sub_screen.left - int(sub_screen.width * 0.08)),
        sub_screen.top,
        min(width, sub_screen.left + int(sub_screen.width * 0.770)),
        search_bottom,
    )
    label_left = max(0, sub_screen.left - int(sub_screen.width * 0.100))
    label_right = min(width, sub_screen.left + int(sub_screen.width * 0.360))
    label_rows: list[int] = []
    label_points_by_row: dict[int, list[int]] = {}
    label_sample_count = max(1, len(range(label_left, label_right, 2)))
    label_threshold = max(1, int(label_sample_count * 0.10))

    for y in range(search.top, search.bottom):
        score = 0
        row_points: list[int] = []
        for x in range(label_left, label_right, 2):
            r, g, b = pixels[x, y]
            brightness = (r + g + b) / 3
            if b >= 70 and r <= 88 and g <= 125 and b >= r + 22 and brightness <= 150:
                score += 1
                row_points.append(x)
        if score >= label_threshold:
            label_rows.append(y)
            label_points_by_row[y] = row_points

    ranges = [
        row_range
        for row_range in _cluster_ranges(
            label_rows,
            max_gap=max(1, int(sub_screen.height * 0.006)),
        )
        if row_range[1] - row_range[0] >= max(
            1,
            int(sub_screen.height * 0.018),
        )
    ]
    if not ranges:
        return None

    label_range = max(ranges, key=lambda row_range: row_range[1] - row_range[0])
    top, bottom = label_range

    minimum_row_height = max(1.0, sub_screen.height * 0.055)
    row_height = max(minimum_row_height, (bottom - top) / 5)
    label_index = ranges.index(label_range)
    for row_range in ranges[label_index + 1:]:
        gap = row_range[0] - bottom
        row_range_height = row_range[1] - row_range[0]
        if 0 < gap <= row_height * 0.85 and row_range_height >= row_height * 0.25:
            bottom = row_range[1]
            row_height = max(minimum_row_height, (bottom - top) / 5)
            continue
        break
    header_candidates = [
        row_range for row_range in ranges[:label_index]
        if top - row_range[1] <= row_height * 1.80
    ]
    if header_candidates:
        table_top = min(
            header_candidates,
            key=lambda row_range: abs(
                (bottom - row_range[0]) / row_height - 6.8
            ),
        )[0]
    else:
        table_top = int(round(top - row_height * 1.15))
    table_bottom = bottom

    label_xs: list[int] = []
    for y in range(top, bottom + 1):
        label_xs.extend(label_points_by_row.get(y, []))
    if len(label_xs) < max(1, int(sub_screen.width * 0.15)):
        return None

    edge_padding = max(1, int(width * 0.010))
    table_left = _percentile(label_xs, 0.005) - edge_padding

    points: list[tuple[int, int]] = []
    for y in range(max(search.top, table_top), min(search.bottom, table_bottom), 2):
        for x in range(search.left, search.right, 2):
            r, g, b = pixels[x, y]
            if _is_table_blue_pixel(r, g, b):
                points.append((x, y))

    sampled_area = max(
        1,
        len(range(max(search.top, table_top), min(search.bottom, table_bottom), 2))
        * len(range(search.left, search.right, 2)),
    )
    if len(points) < max(1, int(sampled_area * 0.004)):
        return None

    xs = [point[0] for point in points]
    right = _percentile(xs, 0.975) + edge_padding
    right += max(edge_padding, int((right - table_left) * 0.08))
    vertical_padding = max(1, int(height * 0.003))
    bottom_padding = max(vertical_padding, int(round(row_height * 0.22)))
    table_width = max(1, right - table_left)
    detected_height = max(1, table_bottom - table_top)
    if detected_height / table_width < 0.24:
        # Bright cabinets and localized reflections can make the row-label scan
        # stop after only the upper half of the judgement table. Once the table
        # is found horizontally, keep the standard 6-row table height instead
        # of discarding the sub-monitor entirely.
        expected_height = int(round(table_width * 0.31))
        table_bottom = max(
            table_bottom,
            min(search_bottom, table_top + expected_height),
        )
    return Box(
        table_left,
        table_top - vertical_padding,
        right,
        table_bottom + bottom_padding,
    ).clamp(width, height)


def is_complete_sub_judgement_table(table: Box | None) -> bool:
    if table is None or table.width <= 0:
        return False
    # A complete table contains one header and five judgement rows. Partial
    # sub-monitor crops are visibly flatter even after perspective correction.
    return table.height / table.width >= 0.25


def refine_sub_screen(sub_screen: Box, sub_judgement_table: Box | None) -> Box:
    if sub_judgement_table is None:
        return sub_screen
    bottom = min(
        sub_screen.bottom,
        sub_judgement_table.bottom + max(1, int(sub_screen.height * 0.010)),
    )
    return Box(sub_screen.left, sub_screen.top, sub_screen.right, bottom)


def main_content_box(screen: Box) -> Box:
    return relative_box(screen, (0.110, 0.110, 0.890, 0.705))


def _is_orange_achievement_digit_pixel(r: int, g: int, b: int) -> bool:
    brightness = (r + g + b) / 3
    return (
        r >= 130
        and g >= 55
        and b <= 105
        and r >= g + 12
        and brightness >= 70
    )


def _is_red_achievement_digit_pixel(r: int, g: int, b: int) -> bool:
    return (
        r >= 105
        and r >= g + 18
        and r >= b + 8
        and max(r, g, b) - min(r, g, b) >= 25
    )


def _detect_main_achievement_by_color(
    image: Image.Image,
    screen: Box,
    pixel_matches: Callable[[int, int, int], bool],
) -> tuple[Box, int] | None:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    # Strong perspective can push the achievement block well below the usual
    # 45% screen position. Keep the upper bound broad and let the large digit
    # color/area score distinguish it from CLEAR and the difficulty header.
    search = relative_box(screen, (0.030, 0.255, 0.720, 0.620)).clamp(width, height)

    candidate_rows: list[int] = []
    row_scores: dict[int, int] = {}
    row_threshold = max(8, int((search.width / 4) * 0.08))
    for y in range(search.top, search.bottom):
        score = 0
        for x in range(search.left, search.right, 4):
            r, g, b = pixels[x, y]
            if pixel_matches(r, g, b):
                score += 1
        if score >= row_threshold:
            candidate_rows.append(y)
            row_scores[y] = score

    row_ranges = [
        row_range
        for row_range in _cluster_ranges(
            candidate_rows,
            max_gap=max(2, int(screen.height * 0.0016)),
        )
        if row_range[1] - row_range[0] >= max(4, int(screen.height * 0.0045))
    ]
    if not row_ranges:
        return None

    def row_range_score(row_range: tuple[int, int]) -> int:
        return sum(row_scores.get(y, 0) for y in range(row_range[0], row_range[1] + 1))

    expected_band_ranges = []
    for row_range in row_ranges:
        center_ratio = (((row_range[0] + row_range[1]) / 2) - screen.top) / screen.height
        bottom_ratio = (row_range[1] - screen.top) / screen.height
        if 0.315 <= center_ratio <= 0.435 and bottom_ratio <= 0.470:
            expected_band_ranges.append(row_range)

    # Rank text such as SS/SSS uses the same warm colors as the achievement
    # digits and is often larger. Prefer the normal achievement band before
    # falling back to the largest color block.
    digit_range = max(expected_band_ranges or row_ranges, key=row_range_score)
    points: list[tuple[int, int]] = []
    for y in range(digit_range[0], digit_range[1] + 1, 2):
        for x in range(search.left, search.right, 2):
            r, g, b = pixels[x, y]
            if pixel_matches(r, g, b):
                points.append((x, y))

    minimum_points = max(80, int(screen.width * screen.height * 0.00006))
    if len(points) < minimum_points:
        return None

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    horizontal_padding = max(4, int(screen.width * 0.0077))
    top_padding = max(6, int(screen.height * 0.0131))
    bottom_padding = max(4, int(screen.height * 0.0077))
    return (
        Box(
            _percentile(xs, 0.010) - horizontal_padding,
            _percentile(ys, 0.010) - top_padding,
            _percentile(xs, 0.990) + horizontal_padding,
            _percentile(ys, 0.990) + bottom_padding,
        ).clamp(width, height),
        digit_range[1] - digit_range[0],
    )


def detect_main_achievement(image: Image.Image, screen: Box) -> Box | None:
    orange = _detect_main_achievement_by_color(
        image,
        screen,
        _is_orange_achievement_digit_pixel,
    )
    minimum_full_digit_height = max(8, int(screen.height * 0.030))
    if orange is not None and orange[1] >= minimum_full_digit_height:
        return orange[0]

    red = _detect_main_achievement_by_color(
        image,
        screen,
        _is_red_achievement_digit_pixel,
    )
    if red is not None:
        return red[0]
    return orange[0] if orange is not None else None


def detect_main_title(
    image: Image.Image,
    screen: Box,
    achievement: Box | None = None,
) -> Box | None:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    x_start = screen.left + int(screen.width * 0.180)
    x_end = screen.left + int(screen.width * 0.860)
    if achievement is not None:
        y_start = max(
            screen.top + int(screen.height * 0.120),
            achievement.top - int(screen.height * 0.180),
        )
        y_end = min(
            screen.top + int(screen.height * 0.400),
            achievement.top - int(screen.height * 0.015),
        )
    else:
        y_start = screen.top + int(screen.height * 0.120)
        y_end = screen.top + int(screen.height * 0.360)

    scores: list[tuple[int, int]] = []
    for y in range(y_start, y_end):
        score = 0
        for x in range(x_start, x_end, 4):
            r, g, b = pixels[x, y]
            mx = max(r, g, b)
            mn = min(r, g, b)
            brightness = (r + g + b) / 3
            if brightness <= 125 and mx - mn >= 22:
                score += 1
        scores.append((y, score))
    if not scores:
        return None

    peak_score = max(score for _, score in scores)
    row_threshold = max(1, int(peak_score * 0.68))
    rows: list[int] = []
    row_scores: dict[int, int] = {}
    for y, score in scores:
        if score >= row_threshold:
            rows.append(y)
            row_scores[y] = score

    row_ranges = [
        row_range
        for row_range in _cluster_ranges(
            rows,
            max_gap=max(1, int(screen.height * 0.002)),
        )
        if row_range[1] - row_range[0] >= max(
            1,
            int(screen.height * 0.008),
        )
    ]
    merged_ranges: list[tuple[int, int]] = []
    maximum_title_height = screen.height * 0.040
    for row_range in row_ranges:
        if (
            merged_ranges
            and row_range[1] - merged_ranges[-1][0] <= maximum_title_height
        ):
            merged_ranges[-1] = (merged_ranges[-1][0], row_range[1])
        else:
            merged_ranges.append(row_range)
    row_ranges = merged_ranges
    if not row_ranges:
        return None

    title_range = max(
        row_ranges,
        key=lambda row_range: sum(row_scores.get(y, 0) for y in range(row_range[0], row_range[1] + 1)),
    )
    vertical_padding = max(1, int(screen.height * 0.0023))
    top = title_range[0] + vertical_padding
    band_bottom = title_range[1] - vertical_padding

    # The title text always sits in a dark bar immediately above the
    # achievement block, while CLEAR and the difficulty header can use any
    # theme color. Find the bottom edge of that bar first, then recover its
    # full height. This is more stable than selecting the strongest colored
    # row, which can be only a thin border on red/yellow/green headers.
    if achievement is not None:
        anchor_top = max(y_start, achievement.top - int(screen.height * 0.145))
        anchor_bottom = min(y_end, achievement.top - int(screen.height * 0.025))
        sample_left = screen.left + int(screen.width * 0.380)
        sample_right = screen.left + int(screen.width * 0.750)
        dark_rows: list[int] = []
        for y in range(anchor_top, anchor_bottom):
            samples = 0
            dark_samples = 0
            for x in range(sample_left, sample_right, 4):
                r, g, b = pixels[x, y]
                samples += 1
                if (r + g + b) / 3 <= 125:
                    dark_samples += 1
            if samples and dark_samples / samples >= 0.50:
                dark_rows.append(y)

        dark_ranges = [
            row_range
            for row_range in _cluster_ranges(
                dark_rows,
                max_gap=max(1, int(screen.height * 0.008)),
            )
            if row_range[1] - row_range[0] >= screen.height * 0.005
        ]
        if dark_ranges:
            title_bar = max(dark_ranges, key=lambda row_range: row_range[1])
            band_bottom = min(
                anchor_bottom,
                title_bar[1] + max(1, int(screen.height * 0.002)),
            )
            top = max(
                anchor_top,
                band_bottom - max(1, int(screen.height * 0.045)),
            )

    minimum_title_height = max(8, int(screen.height * 0.026))
    if band_bottom - top < minimum_title_height:
        top = max(
            screen.top + int(screen.height * 0.085),
            band_bottom - minimum_title_height,
        )

    band_height = max(1, band_bottom - top)
    column_scores: dict[int, int] = {}
    candidate_columns: list[int] = []
    bar_search_left = screen.left + int(screen.width * 0.140)
    bar_search_right = screen.left + int(screen.width * 0.900)
    threshold = max(1, int((band_height / 2) * 0.28))
    for x in range(bar_search_left, bar_search_right):
        score = 0
        for y in range(top, band_bottom, 2):
            r, g, b = pixels[x, y]
            brightness = (r + g + b) / 3
            saturation = max(r, g, b) - min(r, g, b)
            if brightness <= 150 and saturation >= 14:
                score += 1
        if score >= threshold:
            candidate_columns.append(x)
            column_scores[x] = score

    column_ranges = [
        column_range
        for column_range in _cluster_ranges(
            candidate_columns,
            max_gap=max(1, int(screen.width * 0.018)),
        )
        if column_range[1] - column_range[0] >= screen.width * 0.30
    ]
    if column_ranges:
        screen_center = (screen.left + screen.right) / 2
        bar_left, bar_right = min(
            column_ranges,
            key=lambda column_range: (
                abs((column_range[0] + column_range[1]) / 2 - screen_center),
                -sum(column_scores.get(x, 0) for x in range(column_range[0], column_range[1] + 1)),
            ),
        )
        horizontal_padding = max(1, int(screen.width * 0.010))
        left = max(
            bar_left + horizontal_padding,
            screen.left + int(screen.width * 0.350),
        )
        right = min(
            bar_right - horizontal_padding,
            screen.left + int(screen.width * 0.800),
        )
    else:
        left = screen.left + int(screen.width * 0.285)
        right = screen.left + int(screen.width * 0.790)

    candidate = Box(
        left,
        top,
        right,
        band_bottom,
    ).clamp(width, height)
    center_ratio = (
        ((candidate.top + candidate.bottom) / 2) - screen.top
    ) / max(1, screen.height)
    if center_ratio < 0.230:
        # The outer ring and CLEAR glow can form a dark strip above the actual
        # song title. When that happens, fall back to the fixed in-screen title
        # lane instead of feeding an obviously high crop to OCR.
        return relative_box(screen, (0.300, 0.322, 0.800, 0.372)).clamp(
            width,
            height,
        )
    return candidate


def relative_box(screen: Box, relative: tuple[float, float, float, float]) -> Box:
    x1, y1, x2, y2 = relative
    return Box(
        int(round(screen.left + screen.width * x1)),
        int(round(screen.top + screen.height * y1)),
        int(round(screen.left + screen.width * x2)),
        int(round(screen.top + screen.height * y2)),
    )


def main_screen_model_field_boxes(screen: Box, width: int, height: int) -> tuple[Box, Box]:
    title = relative_box(screen, (0.300, 0.000, 0.985, 0.220)).clamp(width, height)
    achievement = relative_box(screen, (0.000, 0.480, 0.760, 0.960)).clamp(width, height)
    return title, achievement


def enhance_judgement_table_for_ocr(image: Image.Image) -> Image.Image:
    rgb = np.asarray(image.convert("RGB"))
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    lightness, channel_a, channel_b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=1.08, tileGridSize=(8, 4))
    lightness = clahe.apply(lightness)
    clahe_rgb = cv2.cvtColor(cv2.merge((lightness, channel_a, channel_b)), cv2.COLOR_LAB2RGB)
    blended = cv2.addWeighted(rgb, 0.86, clahe_rgb, 0.14, 0)

    image = Image.fromarray(blended, "RGB")
    image = ImageEnhance.Contrast(image).enhance(1.30)
    image = ImageEnhance.Sharpness(image).enhance(1.42)
    return image.filter(ImageFilter.UnsharpMask(radius=0.8, percent=55, threshold=4))


def sharpen_for_ocr(image: Image.Image, field_name: str | None = None) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    if field_name == "sub_judgement_table":
        return enhance_judgement_table_for_ocr(image)
    image = ImageEnhance.Contrast(image).enhance(1.35)
    image = ImageEnhance.Sharpness(image).enhance(1.45)
    return image


def is_dxnet_result_screenshot(image: Image.Image) -> bool:
    """Detect a DX NET page only when its judgement table is also present."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    width, height = image.size
    if width <= 0 or height / width < 1.2:
        return False
    sample = image.resize((80, 80), Image.Resampling.BILINEAR)
    pixels = sample.load()
    vivid_cyan = sum(
        1
        for y in range(sample.height)
        for x in range(sample.width)
        if (
            pixels[x, y][0] < 120
            and pixels[x, y][1] > 140
            and pixels[x, y][2] > 180
        )
    )
    if vivid_cyan / (sample.width * sample.height) < 0.08:
        return False
    judgement_table = detect_dxnet_judgement_table(image)
    return (
        judgement_table is not None
        and judgement_table.top >= height * 0.28
    )


def _dxnet_grid_line_pixel(pixel: tuple[int, int, int]) -> bool:
    r, g, b = pixel
    return (
        50 <= r <= 130
        and 115 <= g <= 170
        and 180 <= b <= 230
        and b - r >= 70
        and b - g >= 30
    )


def detect_dxnet_judgement_table(image: Image.Image) -> Box | None:
    """Find the stable blue outer border of the DX NET judgement table."""
    image = image.convert("RGB")
    width, height = image.size
    pixels = image.load()
    scan_right = min(width, int(round(width * 0.72)))
    minimum_score = max(40, int(round(width * 0.30)))
    candidate_rows: list[tuple[int, int]] = []

    for y in range(height):
        score = sum(
            _dxnet_grid_line_pixel(pixels[x, y])
            for x in range(scan_right)
        )
        if score >= minimum_score:
            candidate_rows.append((y, score))

    clusters: list[list[tuple[int, int]]] = []
    for y, score in candidate_rows:
        if not clusters or y > clusters[-1][-1][0] + 1:
            clusters.append([])
        clusters[-1].append((y, score))

    # The table is about 31% of the page width high. Pairing both outer
    # borders avoids depending on the page's vertical scroll position.
    borders = [
        max(cluster, key=lambda item: item[1])
        for cluster in clusters
    ]
    expected_height = width * 0.307
    candidates: list[tuple[float, int, int]] = []
    for top, top_score in borders:
        for bottom, bottom_score in borders:
            table_height = bottom - top
            if not width * 0.25 <= table_height <= width * 0.38:
                continue
            height_error = abs(table_height - expected_height) / width
            strength = min(top_score, bottom_score) / width
            candidates.append((height_error - strength * 0.08, top, bottom))

    if not candidates:
        return None
    _, top, bottom = min(candidates)
    return Box(
        int(round(width * 0.030)),
        top,
        int(round(width * 0.662)),
        bottom + 1,
    ).clamp(width, height)


def detect_dxnet_title_bar(
    image: Image.Image,
    judgement_table: Box,
) -> Box | None:
    """Find the wide white song-title bar above a DX NET judgement table."""
    rgb = np.asarray(image.convert("RGB"))
    height, width = rgb.shape[:2]
    left = int(round(width * 0.035))
    right = int(round(width * 0.850))
    search_top = max(0, int(round(judgement_table.top - width * 0.90)))
    search_bottom = min(
        height,
        int(round(judgement_table.top - width * 0.42)),
    )
    if right <= left or search_bottom <= search_top:
        return None

    region = rgb[search_top:search_bottom, left:right]
    channel_min = region.min(axis=2)
    channel_spread = region.max(axis=2) - channel_min
    white_rows = ((channel_min >= 215) & (channel_spread <= 32)).mean(axis=1)
    indexes = np.flatnonzero(white_rows >= 0.70).tolist()
    clusters = _cluster_ranges(indexes, max_gap=1)
    candidates = []
    for start, end in clusters:
        bar_height = end - start + 1
        if not width * 0.035 <= bar_height <= width * 0.12:
            continue
        coverage = float(white_rows[start:end + 1].mean())
        candidates.append((coverage, bar_height, start, end))
    if not candidates:
        return None

    _, _, start, end = max(candidates)
    absolute_top = search_top + start
    absolute_bottom = search_top + end + 1
    title_region = rgb[absolute_top:absolute_bottom]
    title_min = title_region.min(axis=2)
    title_spread = title_region.max(axis=2) - title_min
    white_columns = (
        (title_min >= 215) & (title_spread <= 32)
    ).mean(axis=0)
    column_clusters = _cluster_ranges(
        np.flatnonzero(white_columns >= 0.55).tolist(),
        max_gap=1,
    )
    wide_columns = [
        (column_end - column_start + 1, column_start, column_end)
        for column_start, column_end in column_clusters
        if column_end - column_start + 1 >= width * 0.45
    ]
    if not wide_columns:
        return None
    _, column_start, column_end = max(wide_columns)
    margin = max(2, int(round(width * 0.004)))
    return Box(
        max(0, column_start - margin),
        max(0, absolute_top - margin),
        min(width, column_end + 1 + margin),
        min(height, absolute_bottom + margin),
    )


def dxnet_result_field_boxes(image: Image.Image) -> dict[str, Box]:
    """Locate mobile DX NET fields relative to the judgement table."""
    width, height = image.size
    judgement_table = detect_dxnet_judgement_table(image)
    if judgement_table is None:
        raise ValueError("Could not locate the DX NET judgement table")

    def anchored_box(
        x1: float,
        top_offset: float,
        x2: float,
        bottom_offset: float,
    ) -> Box:
        box = Box(
            int(round(width * x1)),
            int(round(judgement_table.top + width * top_offset)),
            int(round(width * x2)),
            int(round(judgement_table.top + width * bottom_offset)),
        )
        if (
            box.left < 0
            or box.top < 0
            or box.right > width
            or box.bottom > height
        ):
            raise ValueError(
                "DX NET screenshot must include the title, achievement, and judgement table"
            )
        return box

    title_bar = detect_dxnet_title_bar(image, judgement_table)
    if title_bar is None:
        main_title = anchored_box(0.035, -0.633, 0.850, -0.562)
        main_achievement = anchored_box(0.465, -0.517, 0.800, -0.418)
    else:
        main_title = title_bar
        main_achievement = Box(
            int(round(width * 0.450)),
            min(height, title_bar.bottom + int(round(width * 0.010))),
            int(round(width * 0.830)),
            min(height, title_bar.bottom + int(round(width * 0.160))),
        )

    fields = {
        "main_title": main_title,
        "main_achievement": main_achievement,
        "sub_judgement_table": judgement_table,
    }
    if any(box.width <= 0 or box.height <= 0 for box in fields.values()):
        raise ValueError(
            "DX NET screenshot must include the title, achievement, and judgement table"
        )
    return fields


def _dxnet_fields_in_memory(image: Image.Image) -> dict:
    field_boxes = dxnet_result_field_boxes(image)
    fields = {}
    for name, field_box in field_boxes.items():
        fields[name] = {
            "image": sharpen_for_ocr(image.crop(field_box.to_tuple()), name),
            "left": field_box.left,
            "top": field_box.top,
            "right": field_box.right,
            "bottom": field_box.bottom,
            "detector": "dxnet_blue_grid_anchor",
            "layout_hint": "dxnet" if name == "sub_judgement_table" else None,
        }
    return {
        "layout": "dxnet",
        "screen": {
            "left": 0,
            "top": 0,
            "right": image.width,
            "bottom": image.height,
            "width": image.width,
            "height": image.height,
        },
        "fields": fields,
    }


def crop_result_fields_in_memory(source_image: Image.Image) -> dict:
    """Crop only OCR fields without creating debug files."""
    image = ImageOps.exif_transpose(source_image).convert("RGB")
    if is_dxnet_result_screenshot(image):
        return _dxnet_fields_in_memory(image)
    screen = detect_result_screen(image)
    main_source = image
    main_screen_box, main_screen_image = detect_main_screen_with_cropper_model(image)
    if main_screen_image is not None:
        main_source = main_screen_image
        screen = Box(0, 0, main_source.width, main_source.height)
        main_title, main_achievement = main_screen_model_field_boxes(
            screen,
            main_source.width,
            main_source.height,
        )
    else:
        main_achievement = detect_main_achievement(main_source, screen)
        main_title = detect_main_title(main_source, screen, main_achievement)
    main_screen_only = image.height <= image.width * 1.16
    sub_judgement_table = None
    sub_judgement_image = None
    sub_judgement_detector = "blue_grid"
    if not main_screen_only:
        candidate, _, detector, warped_table = detect_sub_judgement_table_with_cropper_model(image)
        if is_complete_sub_judgement_table(candidate):
            sub_judgement_table = candidate
            sub_judgement_image = warped_table
            sub_judgement_detector = detector
        else:
            sub_screen = detect_sub_screen(image)
            fallback_table = detect_sub_judgement_table(image, sub_screen)
            if is_complete_sub_judgement_table(fallback_table):
                sub_judgement_table = fallback_table
            if sub_screen.bottom < image.height * 0.08:
                # A portrait photo can still contain only the round main screen.
                # Rescan from near the top instead of treating its upper half as a
                # cabinet sub-monitor and shifting every main-screen field down.
                if main_screen_image is None:
                    screen = detect_result_screen(image, main_screen_only=True)
                    main_achievement = detect_main_achievement(image, screen)
                    main_title = detect_main_title(image, screen, main_achievement)

    if main_title is None:
        main_title = relative_box(screen, (0.285, 0.222, 0.790, 0.282)).clamp(
            main_source.width,
            main_source.height,
        )
        title_detector = (
            "main_screen_pt_fallback_relative"
            if main_screen_image is not None
            else "fallback_relative"
        )
    else:
        title_detector = "main_screen_pt_title_bar" if main_screen_image is not None else "title_bar"

    if main_achievement is None:
        main_achievement = relative_box(screen, (0.055, 0.300, 0.650, 0.395)).clamp(
            main_source.width,
            main_source.height,
        )
        achievement_detector = (
            "main_screen_pt_fallback_relative"
            if main_screen_image is not None
            else "fallback_relative"
        )
    else:
        achievement_detector = (
            "main_screen_pt_achievement_digits"
            if main_screen_image is not None
            else "achievement_digits"
        )

    field_boxes = {
        "main_title": (main_title, title_detector),
        "main_achievement": (main_achievement, achievement_detector),
    }
    if sub_judgement_table is not None:
        field_boxes["sub_judgement_table"] = (sub_judgement_table, sub_judgement_detector)

    fields = {}
    for name, (field_box, detector) in field_boxes.items():
        crop_source = main_source if name in {"main_title", "main_achievement"} else image
        crop_image = crop_source.crop(field_box.to_tuple())
        if name == "sub_judgement_table" and sub_judgement_image is not None:
            crop_image = sub_judgement_image
        fields[name] = {
            "image": sharpen_for_ocr(crop_image, name),
            "left": field_box.left,
            "top": field_box.top,
            "right": field_box.right,
            "bottom": field_box.bottom,
            "detector": detector,
            "layout_hint": (
                "cropper_pt_pose_warp"
                if name == "sub_judgement_table" and detector == "cropper_pt_pose_warp"
                else "main_screen_pt_pose_warp"
                if name in {"main_title", "main_achievement"} and main_screen_image is not None
                else None
            ),
        }

    return {
        "main_screen": {
            "left": main_screen_box.left,
            "top": main_screen_box.top,
            "right": main_screen_box.right,
            "bottom": main_screen_box.bottom,
            "width": main_screen_box.width,
            "height": main_screen_box.height,
            "detector": "main_screen_pt_pose_warp",
        }
        if main_screen_box is not None
        else None,
        "screen": {
            "left": screen.left,
            "top": screen.top,
            "right": screen.right,
            "bottom": screen.bottom,
            "width": screen.width,
            "height": screen.height,
        },
        "fields": fields,
    }


def crop_result_fields(image_path: str | os.PathLike[str], output_dir: str | os.PathLike[str]) -> dict:
    source = Path(image_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as raw_image:
        image = ImageOps.exif_transpose(raw_image).convert("RGB")
    if is_dxnet_result_screenshot(image):
        metadata = _dxnet_fields_in_memory(image)
        sample_dir = output / source.stem
        if sample_dir.exists():
            shutil.rmtree(sample_dir)
        sample_dir.mkdir(parents=True, exist_ok=True)
        overlay = image.copy()
        draw = ImageDraw.Draw(overlay)
        result = {
            "source": str(source),
            "layout": "dxnet",
            "screen": metadata["screen"],
            "fields": {},
        }
        for name, field in metadata["fields"].items():
            crop_path = sample_dir / f"{name}.png"
            field["image"].save(crop_path)
            box = Box(field["left"], field["top"], field["right"], field["bottom"])
            draw.rectangle(box.to_tuple(), outline=(255, 80, 0), width=2)
            draw.text((box.left + 4, box.top + 4), name, fill=(255, 255, 255))
            result["fields"][name] = {
                key: value
                for key, value in field.items()
                if key != "image"
            }
            result["fields"][name]["path"] = str(crop_path)
        overlay.save(sample_dir / "debug_overlay.png")
        with open(sample_dir / "metadata.json", "w", encoding="utf-8") as fp:
            json.dump(result, fp, ensure_ascii=False, indent=2)
        return result
    screen = detect_result_screen(image)
    stem = source.stem
    sample_dir = output / stem
    if sample_dir.exists():
        shutil.rmtree(sample_dir)
    sample_dir.mkdir(parents=True, exist_ok=True)

    sub_judgement_table, model_sub_screen, sub_judgement_detector, sub_judgement_image = (
        detect_sub_judgement_table_with_cropper_model(image)
    )
    sub_screen = model_sub_screen or detect_sub_screen(image)
    main_screen_only = image.height <= image.width * 1.16
    if main_screen_only:
        sub_judgement_table = None
        sub_judgement_image = None
    elif not is_complete_sub_judgement_table(sub_judgement_table):
        sub_judgement_table = None
        sub_judgement_image = None
        sub_screen = detect_sub_screen(image)
        fallback_table = detect_sub_judgement_table(image, sub_screen)
        if is_complete_sub_judgement_table(fallback_table):
            sub_judgement_table = fallback_table
            sub_judgement_detector = "blue_grid"
        if sub_screen.bottom < image.height * 0.08:
            screen = detect_result_screen(image, main_screen_only=True)
    content_screen = main_content_box(screen).clamp(image.width, image.height)
    main_source = image
    main_field_screen = screen
    main_screen_box, main_screen_image = detect_main_screen_with_cropper_model(image)
    if main_screen_image is not None:
        main_source = main_screen_image
        main_field_screen = Box(0, 0, main_source.width, main_source.height)
        main_title, main_achievement = main_screen_model_field_boxes(
            main_field_screen,
            main_source.width,
            main_source.height,
        )
    else:
        main_achievement = detect_main_achievement(main_source, main_field_screen)
        main_title = detect_main_title(main_source, main_field_screen, main_achievement)
    refined_sub_screen = refine_sub_screen(sub_screen, sub_judgement_table).clamp(image.width, image.height)
    image.crop(screen.to_tuple()).save(sample_dir / "screen.png")
    image.crop(content_screen.to_tuple()).save(sample_dir / "main_content.png")
    image.crop(refined_sub_screen.to_tuple()).save(sample_dir / "sub_screen.png")
    if main_screen_image is not None:
        main_screen_image.save(sample_dir / "main_screen_rectified.png")

    overlay = image.copy()
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(screen.to_tuple(), outline=(0, 255, 80), width=max(4, image.width // 300))
    draw.rectangle(content_screen.to_tuple(), outline=(0, 255, 180), width=max(3, image.width // 420))

    result = {
        "source": str(source),
        "screen": {
            "left": screen.left,
            "top": screen.top,
            "right": screen.right,
            "bottom": screen.bottom,
            "width": screen.width,
            "height": screen.height,
        },
        "main_content": {
            "left": content_screen.left,
            "top": content_screen.top,
            "right": content_screen.right,
            "bottom": content_screen.bottom,
            "width": content_screen.width,
            "height": content_screen.height,
        },
        "sub_screen": {
            "left": refined_sub_screen.left,
            "top": refined_sub_screen.top,
            "right": refined_sub_screen.right,
            "bottom": refined_sub_screen.bottom,
            "width": refined_sub_screen.width,
            "height": refined_sub_screen.height,
        },
        "sub_screen_raw": {
            "left": sub_screen.left,
            "top": sub_screen.top,
            "right": sub_screen.right,
            "bottom": sub_screen.bottom,
            "width": sub_screen.width,
            "height": sub_screen.height,
            "detector": "cropper_pt" if model_sub_screen is not None and sub_screen == model_sub_screen else "color_scan",
        },
        "main_screen_model": {
            "left": main_screen_box.left,
            "top": main_screen_box.top,
            "right": main_screen_box.right,
            "bottom": main_screen_box.bottom,
            "width": main_screen_box.width,
            "height": main_screen_box.height,
            "detector": "main_screen_pt_pose_warp",
            "path": str(sample_dir / "main_screen_rectified.png"),
        }
        if main_screen_box is not None
        else None,
        "fields": {},
    }

    draw.rectangle(refined_sub_screen.to_tuple(), outline=(0, 180, 255), width=max(4, image.width // 300))

    if main_title is not None:
        crop = sharpen_for_ocr(main_source.crop(main_title.to_tuple()), "main_title")
        crop_path = sample_dir / "main_title.png"
        crop.save(crop_path)
        if main_screen_image is None:
            draw.rectangle(main_title.to_tuple(), outline=(255, 80, 0), width=max(2, image.width // 500))
            draw.text((main_title.left + 4, main_title.top + 4), "main_title", fill=(255, 255, 255))
        result["fields"]["main_title"] = {
            "path": str(crop_path),
            "left": main_title.left,
            "top": main_title.top,
            "right": main_title.right,
            "bottom": main_title.bottom,
            "detector": "main_screen_pt_title_bar" if main_screen_image is not None else "title_bar",
            "layout_hint": "main_screen_pt_pose_warp" if main_screen_image is not None else None,
        }
    else:
        fallback = relative_box(main_field_screen, (0.285, 0.222, 0.790, 0.282)).clamp(
            main_source.width,
            main_source.height,
        )
        crop = sharpen_for_ocr(main_source.crop(fallback.to_tuple()), "main_title")
        crop_path = sample_dir / "main_title.png"
        crop.save(crop_path)
        if main_screen_image is None:
            draw.rectangle(fallback.to_tuple(), outline=(255, 80, 0), width=max(2, image.width // 500))
            draw.text((fallback.left + 4, fallback.top + 4), "main_title", fill=(255, 255, 255))
        result["fields"]["main_title"] = {
            "path": str(crop_path),
            "left": fallback.left,
            "top": fallback.top,
            "right": fallback.right,
            "bottom": fallback.bottom,
            "detector": "main_screen_pt_fallback_relative" if main_screen_image is not None else "fallback_relative",
            "layout_hint": "main_screen_pt_pose_warp" if main_screen_image is not None else None,
        }

    if main_achievement is not None:
        crop = sharpen_for_ocr(main_source.crop(main_achievement.to_tuple()), "main_achievement")
        crop_path = sample_dir / "main_achievement.png"
        crop.save(crop_path)
        if main_screen_image is None:
            draw.rectangle(main_achievement.to_tuple(), outline=(255, 80, 0), width=max(2, image.width // 500))
            draw.text((main_achievement.left + 4, main_achievement.top + 4), "main_achievement", fill=(255, 255, 255))
        result["fields"]["main_achievement"] = {
            "path": str(crop_path),
            "left": main_achievement.left,
            "top": main_achievement.top,
            "right": main_achievement.right,
            "bottom": main_achievement.bottom,
            "detector": (
                "main_screen_pt_achievement_digits"
                if main_screen_image is not None
                else "orange_digits"
            ),
            "layout_hint": "main_screen_pt_pose_warp" if main_screen_image is not None else None,
        }
    else:
        fallback = relative_box(main_field_screen, (0.055, 0.300, 0.650, 0.395)).clamp(
            main_source.width,
            main_source.height,
        )
        crop = sharpen_for_ocr(main_source.crop(fallback.to_tuple()), "main_achievement")
        crop_path = sample_dir / "main_achievement.png"
        crop.save(crop_path)
        if main_screen_image is None:
            draw.rectangle(fallback.to_tuple(), outline=(255, 80, 0), width=max(2, image.width // 500))
            draw.text((fallback.left + 4, fallback.top + 4), "main_achievement", fill=(255, 255, 255))
        result["fields"]["main_achievement"] = {
            "path": str(crop_path),
            "left": fallback.left,
            "top": fallback.top,
            "right": fallback.right,
            "bottom": fallback.bottom,
            "detector": "main_screen_pt_fallback_relative" if main_screen_image is not None else "fallback_relative",
            "layout_hint": "main_screen_pt_pose_warp" if main_screen_image is not None else None,
        }

    if sub_judgement_table is not None:
        crop_source = sub_judgement_image or image.crop(sub_judgement_table.to_tuple())
        crop = sharpen_for_ocr(crop_source, "sub_judgement_table")
        crop_path = sample_dir / "sub_judgement_table.png"
        crop.save(crop_path)
        draw.rectangle(sub_judgement_table.to_tuple(), outline=(255, 80, 0), width=max(2, image.width // 500))
        draw.text((sub_judgement_table.left + 4, sub_judgement_table.top + 4), "sub_judgement_table", fill=(255, 255, 255))
        result["fields"]["sub_judgement_table"] = {
            "path": str(crop_path),
            "left": sub_judgement_table.left,
            "top": sub_judgement_table.top,
            "right": sub_judgement_table.right,
            "bottom": sub_judgement_table.bottom,
            "detector": sub_judgement_detector,
            "layout_hint": "cropper_pt_pose_warp"
            if sub_judgement_detector == "cropper_pt_pose_warp"
            else None,
        }

    overlay.save(sample_dir / "debug_overlay.png")
    with open(sample_dir / "metadata.json", "w", encoding="utf-8") as fp:
        json.dump(result, fp, ensure_ascii=False, indent=2)

    return result


def iter_images(paths: Iterable[str]) -> Iterable[Path]:
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            for item in sorted(path.iterdir()):
                if item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                    yield item
        else:
            yield path


def main() -> int:
    parser = argparse.ArgumentParser(description="Crop maimai result-screen fields for OCR prototyping.")
    parser.add_argument("images", nargs="+", help="Image files or directories.")
    parser.add_argument("-o", "--output-dir", default="data/score_cropper_debug", help="Output directory.")
    parser.add_argument("--json", action="store_true", help="Print JSON metadata to stdout.")
    args = parser.parse_args()

    results = []
    for image_path in iter_images(args.images):
        results.append(crop_result_fields(image_path, args.output_dir))

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for item in results:
            print(f"{item['source']} -> {Path(args.output_dir) / Path(item['source']).stem}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
