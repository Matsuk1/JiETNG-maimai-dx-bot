"""
maimai result-photo OCR integration.

This module wraps the runtime OCR package so main.py can call the recognizer
without shelling out.
"""
from __future__ import annotations

import math
from copy import deepcopy
import logging
import gc
import os
import sys
import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image
from modules.score_recognition.results import (InvalidScoreImageError, UnsupportedScoreImageError)
from PIL import UnidentifiedImageError

from modules.config_loader import read_dxdata
from modules.score_calculator import (
    calc_judgement_achievement_range,
    calc_score,
    calc_score_precise,
    get_note_score,
)
from modules.song_matcher import match_recognized_song_title, song_identity_key


logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

_ENGINE: Any | None = None
_ENGINE_LOCK = threading.Lock()
_OCR_LOCK = threading.Lock()
_OCR_FIELDS: tuple[str, ...] | None = None
_PROCESS_IMAGE_DATA: Any | None = None
_ENGINE_REQUEST_COUNT = 0
_OCR_LAST_USED = 0.0
OCR_IDLE_SECONDS = max(0, float(os.getenv("JIETNG_OCR_IDLE_SECONDS", "300")))
SUPPORTED_SCORE_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_SCORE_IMAGE_PIXELS = 40_000_000
API_LINE_LIKE_OCR_MAX_EDGE = int(
    os.getenv("SCORE_RECOGNITION_API_LINE_LIKE_MAX_EDGE", "2048")
)
API_LINE_LIKE_OCR_JPEG_QUALITY = int(
    os.getenv("SCORE_RECOGNITION_API_LINE_LIKE_JPEG_QUALITY", "88")
)
OCR_ENGINE_MAX_REQUESTS = int(os.getenv("JIETNG_OCR_ENGINE_MAX_REQUESTS", "60"))
OCR_ENGINE_MAX_RSS_MB = float(os.getenv("JIETNG_OCR_ENGINE_MAX_RSS_MB", "1800"))
OCR_ENGINE_IDLE_RESET_RSS_MB = float(
    os.getenv("JIETNG_OCR_ENGINE_IDLE_RESET_RSS_MB", "1400")
)



def _process_rss_mb() -> float | None:
    try:
        import psutil

        return round(psutil.Process(os.getpid()).memory_info().rss / (1024**2), 1)
    except Exception:
        return None


def _line_like_ocr_image(image: Image.Image, image_format: str) -> Image.Image:
    """Approximate LINE-delivered image characteristics for API OCR input."""
    original_size = image.size
    normalized = image.convert("RGB")
    max_edge = max(0, API_LINE_LIKE_OCR_MAX_EDGE)
    quality = max(1, min(100, API_LINE_LIKE_OCR_JPEG_QUALITY))

    if max_edge and max(normalized.size) > max_edge:
        scale = max_edge / max(normalized.size)
        normalized = normalized.resize(
            (
                max(1, int(round(normalized.width * scale))),
                max(1, int(round(normalized.height * scale))),
            ),
            Image.Resampling.LANCZOS,
        )

    buffer = BytesIO()
    normalized.save(buffer, format="JPEG", quality=quality, optimize=True)
    compressed_bytes = buffer.tell()
    buffer.seek(0)
    with Image.open(buffer) as compressed:
        result = compressed.convert("RGB").copy()

    logger.debug(
        "[Recognize] API line-like image preprocessing: format=%s original=%sx%s "
        "processed=%sx%s max_edge=%s jpeg_quality=%s bytes=%s",
        image_format,
        original_size[0],
        original_size[1],
        result.width,
        result.height,
        max_edge,
        quality,
        compressed_bytes,
    )
    return result


CALC_ACHIEVEMENT_TOLERANCE = 0.0
CALC_ACHIEVEMENT_EPSILON = 1e-9
JUDGEMENT_ROW_NAMES = ("tap", "hold", "slide", "touch", "break")
JUDGEMENT_VALUE_NAMES = ("critical_perfect", "perfect", "great", "good")
ALL_JUDGEMENT_VALUE_NAMES = (*JUDGEMENT_VALUE_NAMES, "miss")
TRUSTED_TITLE_MATCH_TYPES = {
    "exact", "blank", "ocr_confusable", "ocr_kana", "rolling_exact",
    "rolling_partial", "rolling_fuzzy", "edge_fuzzy", "edit_fuzzy",
    "ocr_embedded", "prefix",
}
OVERFULL_REPAIR_TITLE_MATCH_TYPES = TRUSTED_TITLE_MATCH_TYPES - {
    "blank", "rolling_partial", "prefix",
}


def _calc_achievement_distance(
    achievement,
    score_range,
    tolerance=CALC_ACHIEVEMENT_TOLERANCE,
):
    if not isinstance(achievement, (int, float)) or not score_range:
        return None
    minimum = float(score_range["minimum"])
    maximum = float(score_range["maximum"])
    if (
        minimum - tolerance - CALC_ACHIEVEMENT_EPSILON
        <= achievement
        <= maximum + tolerance + CALC_ACHIEVEMENT_EPSILON
    ):
        return 0.0
    return min(abs(achievement - minimum), abs(achievement - maximum))


def _find_calc_judgement_uncertainties(notes, judgement, achievement):
    """Find single OCR cells that could explain a Calc score mismatch."""
    if not isinstance(achievement, (int, float)):
        return []

    row_names = JUDGEMENT_ROW_NAMES
    value_names = JUDGEMENT_VALUE_NAMES
    uncertainties = []
    for row_name in row_names:
        source_row = judgement.get(row_name)
        row_missing = not isinstance(source_row, dict)
        if row_missing:
            source_row = {
                "critical_perfect": 0,
                "perfect": 0,
                "great": 0,
                "good": 0,
                "miss": 0,
            }
        try:
            expected = max(0, int(notes.get(row_name, 0)))
        except (TypeError, ValueError):
            continue
        if expected <= 0:
            continue
        if row_missing:
            uncertainties.append({
                "row": row_name,
                "field": "row",
                "ocr": None,
                "candidate_min": None,
                "candidate_max": None,
                "candidate_count": 0,
                "miss_min": None,
                "miss_max": None,
                "row_missing": True,
            })
            continue

        for value_name in value_names:
            try:
                ocr_value = max(0, int(source_row.get(value_name, 0)))
            except (TypeError, ValueError):
                continue
            candidates = []
            for candidate_value in range(expected + 1):
                if candidate_value == ocr_value:
                    continue
                candidate_row = dict(source_row)
                candidate_row[value_name] = candidate_value
                known = sum(max(0, int(candidate_row.get(name, 0))) for name in value_names)
                candidate_miss = expected - known
                if candidate_miss < 0:
                    continue
                candidate_row["miss"] = candidate_miss
                candidate_judgement = dict(judgement)
                candidate_judgement[row_name] = candidate_row
                score_range = calc_judgement_achievement_range(notes, candidate_judgement)
                if _calc_achievement_distance(achievement, score_range) == 0:
                    candidates.append((candidate_value, candidate_miss))

            if not candidates:
                continue
            values = sorted({value for value, _ in candidates})
            misses = sorted({miss for _, miss in candidates})
            uncertainties.append({
                "row": row_name,
                "field": value_name,
                "ocr": ocr_value,
                "candidate_min": values[0],
                "candidate_max": values[-1],
                "candidate_count": len(values),
                "miss_min": misses[0],
                "miss_max": misses[-1],
                "row_missing": row_missing,
            })
    return uncertainties


def _iter_note_distributions(total, fields):
    if not fields:
        if total == 0:
            yield {}
        return
    if len(fields) == 1:
        yield {fields[0]: total}
        return
    first, *rest = fields
    for value in range(total + 1):
        for tail in _iter_note_distributions(total - value, rest):
            yield {first: value, **tail}


def _calc_completion_confidence_penalty(confidence):
    if not isinstance(confidence, (int, float)):
        return 0
    if confidence >= 0.90:
        return 100
    if confidence >= 0.80:
        return 40
    if confidence >= 0.70:
        return 15
    return 0


def _is_calc_completion_locked_cell(value, confidence):
    try:
        value = int(value or 0)
    except (TypeError, ValueError):
        value = 0
    return value != 0 and isinstance(confidence, (int, float)) and confidence >= 0.95


def _calc_completion_scanned_cell_penalty(confidence):
    if confidence is None:
        return 0
    if not isinstance(confidence, (int, float)):
        return 0
    if confidence <= 0.05:
        return 0
    if confidence < 0.50:
        return 12
    if confidence < 0.80:
        return 35
    return 90


def _calc_completion_field_penalty(field_name):
    return {
        "good": 0,
        "great": 8,
        "miss": 18,
        "perfect": 350,
        "critical_perfect": 700,
    }.get(field_name, 100)


MAX_CALC_COMPLETION_ROW_GAP = 16
MAX_CALC_COMPLETION_ROW_OPTIONS = 48
MAX_CALC_COMPLETION_SEARCH_VISITS = 12000


def _calc_completion_changes_rank(changes, confidence):
    def change_confidence(item):
        return (confidence.get(item.get("row")) or {}).get(item.get("field"))

    high_grade_touches = sum(
        1
        for item in changes
        if item.get("field") in {"critical_perfect", "perfect"}
        and item.get("amount", 0) > 0
    )
    great_touches = sum(
        max(1, abs(int(item.get("amount", 0) or 0)))
        for item in changes
        if item.get("field") == "great" and item.get("amount", 0) > 0
    )
    scanned_cell_penalty = sum(
        _calc_completion_scanned_cell_penalty(change_confidence(item))
        * max(1, abs(int(item.get("amount", 0) or 0)))
        for item in changes
    )
    field_penalty = sum(
        _calc_completion_field_penalty(item.get("field"))
        * max(1, abs(int(item.get("amount", 0) or 0)))
        for item in changes
        if item.get("amount", 0) > 0
    )
    confidence_penalty = sum(
        _calc_completion_confidence_penalty(change_confidence(item))
        * max(1, abs(int(item.get("amount", 0) or 0)))
        for item in changes
    )
    total_miss_added = sum(
        item.get("amount", 0)
        for item in changes
        if item.get("field") == "miss" and item.get("amount", 0) > 0
    )
    return (
        high_grade_touches,
        great_touches,
        scanned_cell_penalty,
        field_penalty,
        confidence_penalty,
        total_miss_added,
        len(changes),
        sum(abs(int(item.get("amount", 0) or 0)) for item in changes),
        tuple((item.get("row"), item.get("field"), item.get("amount")) for item in changes),
    )


def _find_calc_completion_candidates(
    notes,
    judgement,
    unmatched_notes,
    achievement,
    confidence=None,
    limit=20,
):
    if not unmatched_notes or not isinstance(achievement, (int, float)):
        return []

    confidence = confidence or {}
    field_names = (
        "critical_perfect",
        "perfect",
        "great",
        "good",
        "miss",
    )
    row_names = JUDGEMENT_ROW_NAMES
    row_options = []
    for row_name in row_names:
        row = judgement.get(row_name)
        if not isinstance(row, dict):
            continue
        try:
            gap = int(unmatched_notes.get(row_name, 0) or 0)
        except (TypeError, ValueError):
            continue
        try:
            source_miss = max(0, int(row.get("miss", 0) or 0))
        except (TypeError, ValueError):
            source_miss = 0
        # An unmatched note belongs to its note-type row. Rows whose note
        # counts already match must not be changed to satisfy another row.
        if gap <= 0:
            continue
        if gap > MAX_CALC_COMPLETION_ROW_GAP:
            logger.debug(
                "[Recognize] Skip calc completion for %s: unmatched note gap too large (%s)",
                row_name,
                gap,
            )
            continue

        options_by_key = {}
        gap_distributions = _iter_note_distributions(gap, field_names) if gap > 0 else ({},)
        redistribution_targets = ("good", "great", "perfect", "critical_perfect")
        redistribution_options = [(0, None)]
        if row_name != "break" and source_miss > 0:
            max_move_miss = min(source_miss, MAX_CALC_COMPLETION_ROW_GAP)
            for amount in range(1, max_move_miss + 1):
                for target_field in redistribution_targets:
                    redistribution_options.append((amount, target_field))

        for distribution in gap_distributions:
            for moved_miss, target_field in redistribution_options:
                candidate_row = dict(row)
                changes = []
                locked_cell_changed = False
                for field_name, amount in distribution.items():
                    if amount <= 0:
                        continue
                    field_confidence = (confidence.get(row_name) or {}).get(field_name)
                    if _is_calc_completion_locked_cell(
                        candidate_row.get(field_name, 0),
                        field_confidence,
                    ):
                        locked_cell_changed = True
                        break
                    candidate_row[field_name] = (
                        max(0, int(candidate_row.get(field_name, 0) or 0))
                        + amount
                    )
                    changes.append({
                        "field": field_name,
                        "amount": amount,
                        "kind": "add",
                    })
                if locked_cell_changed:
                    continue
                if moved_miss > 0 and target_field:
                    miss_confidence = (confidence.get(row_name) or {}).get("miss")
                    target_confidence = (confidence.get(row_name) or {}).get(target_field)
                    if (
                        _is_calc_completion_locked_cell(
                            candidate_row.get("miss", 0),
                            miss_confidence,
                        )
                        or _is_calc_completion_locked_cell(
                            candidate_row.get(target_field, 0),
                            target_confidence,
                        )
                    ):
                        continue
                    candidate_row["miss"] = max(
                        0,
                        int(candidate_row.get("miss", 0) or 0) - moved_miss,
                    )
                    candidate_row[target_field] = (
                        max(0, int(candidate_row.get(target_field, 0) or 0))
                        + moved_miss
                    )
                    changes.append({
                        "field": target_field,
                        "amount": moved_miss,
                        "kind": "move_from_miss",
                    })
                    changes.append({
                        "field": "miss",
                        "amount": -moved_miss,
                        "kind": "move_to",
                    })
                if not changes:
                    continue
                key = tuple(
                    int(candidate_row.get(field_name, 0) or 0)
                    for field_name in field_names
                )
                options_by_key[key] = (candidate_row, changes)
            if len(options_by_key) > MAX_CALC_COMPLETION_ROW_OPTIONS * 8:
                ranked_options = sorted(
                    options_by_key.values(),
                    key=lambda option: _calc_completion_changes_rank(
                        [
                            {"row": row_name, **item}
                            for item in option[1]
                        ],
                        confidence,
                    ),
                )
                options_by_key = {
                    tuple(
                        int(option[0].get(field_name, 0) or 0)
                        for field_name in field_names
                    ): option
                    for option in ranked_options[:MAX_CALC_COMPLETION_ROW_OPTIONS]
                }
        if options_by_key:
            ranked_options = sorted(
                options_by_key.values(),
                key=lambda option: _calc_completion_changes_rank(
                    [
                        {"row": row_name, **item}
                        for item in option[1]
                    ],
                    confidence,
                ),
            )
            row_options.append((row_name, ranked_options[:MAX_CALC_COMPLETION_ROW_OPTIONS]))

    if not row_options:
        return []

    candidates = []
    search_visits = 0

    def visit(index, current_judgement, corrections):
        nonlocal search_visits
        if search_visits >= MAX_CALC_COMPLETION_SEARCH_VISITS:
            return
        if index >= len(row_options):
            search_visits += 1
            score_range = calc_judgement_achievement_range(notes, current_judgement)
            if _calc_achievement_distance(achievement, score_range) != 0:
                return
            break_detail = _infer_break_judgement_detail(
                notes,
                current_judgement,
                achievement,
            )
            if not break_detail:
                return
            break_detail = _attach_break_loss_percentages(notes, break_detail)
            detail_achievement = break_detail.get("calculated_achievement")
            detail_distance = (
                abs(float(achievement) - float(detail_achievement))
                if isinstance(detail_achievement, (int, float))
                else 0.0
            )
            total_miss_added = sum(
                item["amount"]
                for item in corrections
                if item.get("field") == "miss" and item.get("amount", 0) > 0
            )
            confidence_penalty = sum(
                _calc_completion_confidence_penalty(item.get("confidence"))
                * max(1, abs(int(item.get("amount", 0) or 0)))
                for item in corrections
            )
            scanned_cell_penalty = sum(
                _calc_completion_scanned_cell_penalty(item.get("confidence"))
                * max(1, abs(int(item.get("amount", 0) or 0)))
                for item in corrections
            )
            field_penalty = sum(
                _calc_completion_field_penalty(item.get("field"))
                * max(1, abs(int(item.get("amount", 0) or 0)))
                for item in corrections
                if item.get("amount", 0) > 0
            )
            high_grade_touches = sum(
                1
                for item in corrections
                if item.get("field") in {"critical_perfect", "perfect"}
            )
            great_touches = sum(
                max(1, abs(int(item.get("amount", 0) or 0)))
                for item in corrections
                if item.get("field") == "great" and item.get("amount", 0) > 0
            )
            changed_fields = len(corrections)
            candidates.append({
                "judgement": current_judgement,
                "score_range": score_range,
                "break_detail": break_detail,
                "corrections": corrections,
                "rank": (
                    high_grade_touches,
                    great_touches,
                    detail_distance,
                    scanned_cell_penalty,
                    field_penalty,
                    confidence_penalty,
                    total_miss_added,
                    changed_fields,
                    sum(abs(item["amount"]) for item in corrections),
                    tuple((item["row"], item["field"], item["amount"]) for item in corrections),
                ),
            })
            return

        row_name, options = row_options[index]
        for candidate_row, additions in options:
            next_judgement = dict(current_judgement)
            next_judgement[row_name] = candidate_row
            next_corrections = [
                *corrections,
                *(
                    {
                        "row": row_name,
                        "field": item["field"],
                        "ocr": max(0, int((current_judgement.get(row_name) or {}).get(item["field"], 0) or 0)),
                        "validated": max(0, int(candidate_row.get(item["field"], 0) or 0)),
                        "calc_completion": True,
                        "added": item["amount"],
                        "amount": item["amount"],
                        "kind": item.get("kind", "add"),
                        "confidence": (
                            (confidence.get(row_name) or {}).get(item["field"])
                        ),
                    }
                    for item in additions
                ),
            ]
            visit(index + 1, next_judgement, next_corrections)

    base_judgement = {
        row_name: dict(row)
        for row_name, row in judgement.items()
        if isinstance(row, dict)
    }
    visit(0, base_judgement, [])
    candidates.sort(key=lambda item: item["rank"])
    non_high_grade_candidates = [
        candidate for candidate in candidates
        if candidate["rank"][0] == 0
    ]
    if non_high_grade_candidates:
        candidates = non_high_grade_candidates
    return candidates[:limit]


def _infer_missing_break_judgement(notes, judgement, achievement):
    """Infer a completely missing BREAK row from chart notes and achievement."""
    if not isinstance(achievement, (int, float)) or isinstance(judgement.get("break"), dict):
        return None
    try:
        break_count = max(0, int(notes.get("break", 0)))
    except (TypeError, ValueError):
        return None
    if break_count <= 0:
        return None

    value_names = ALL_JUDGEMENT_VALUE_NAMES
    reference_counts = {name: 0 for name in value_names}
    for row_name in ("tap", "hold", "slide", "touch"):
        try:
            expected = max(0, int(notes.get(row_name, 0)))
        except (TypeError, ValueError):
            return None
        if expected <= 0:
            continue
        row = judgement.get(row_name)
        if not isinstance(row, dict):
            return None
        try:
            observed = sum(max(0, int(row.get(name, 0))) for name in value_names)
        except (TypeError, ValueError):
            return None
        if observed != expected:
            return None
        for name in value_names:
            reference_counts[name] += max(0, int(row.get(name, 0)))

    reference_total = sum(reference_counts.values())
    smoothing = 1.0
    reference_probabilities = {
        name: (reference_counts[name] + smoothing)
        / (reference_total + smoothing * len(value_names))
        for name in value_names
    }

    def distribution_penalty(row):
        counts = [max(0, int(row.get(name, 0))) for name in value_names]
        total = sum(counts)
        log_probability = math.lgamma(total + 1)
        log_probability -= sum(math.lgamma(count + 1) for count in counts)
        log_probability += sum(
            count * math.log(reference_probabilities[name])
            for name, count in zip(value_names, counts)
        )
        return -log_probability

    all_cp_row = {
        "critical_perfect": break_count,
        "perfect": 0,
        "great": 0,
        "good": 0,
        "miss": 0,
    }
    baseline_judgement = dict(judgement)
    baseline_judgement["break"] = all_cp_row
    baseline_range = calc_judgement_achievement_range(notes, baseline_judgement)
    if not baseline_range:
        return None
    baseline = (
        float(baseline_range["minimum"]) + float(baseline_range["maximum"])
    ) / 2
    target_deduction = baseline - float(achievement)
    if target_deduction < -0.001:
        return None

    scores = get_note_score(notes)
    required_scores = (
        "break_high_perfect",
        "break_low_perfect",
        "break_high_great",
        "break_low_great",
        "break_good",
        "break_miss",
    )
    if any(not isinstance(scores.get(name), (int, float)) for name in required_scores):
        return None
    perfect_min = float(scores["break_high_perfect"])
    perfect_max = float(scores["break_low_perfect"])
    great_min = float(scores["break_high_great"])
    great_max = float(scores["break_low_great"])
    good_score = float(scores["break_good"])
    miss_score = float(scores["break_miss"])
    if perfect_min <= 0 or perfect_max <= 0:
        return None

    # This loose bound only prunes impossible counts. Every retained row is
    # checked with the same rounded Calc function used by final validation.
    prune_tolerance = 0.003
    candidates = []
    iteration_count = 0
    for miss in range(break_count + 1):
        miss_deduction = miss * miss_score
        if miss_deduction > target_deduction + prune_tolerance:
            break
        for good in range(break_count - miss + 1):
            fixed_deduction = miss_deduction + good * good_score
            if fixed_deduction > target_deduction + prune_tolerance:
                break
            remaining = break_count - miss - good
            for great in range(remaining + 1):
                iteration_count += 1
                if iteration_count > 300_000:
                    return None
                minimum_without_perfect = fixed_deduction + great * great_min
                if minimum_without_perfect > target_deduction + prune_tolerance:
                    break
                maximum_without_perfect = fixed_deduction + great * great_max
                max_perfect_count = remaining - great
                perfect_low = max(
                    0,
                    math.ceil(
                        (target_deduction - prune_tolerance - maximum_without_perfect)
                        / perfect_max
                    ),
                )
                perfect_high = min(
                    max_perfect_count,
                    math.floor(
                        (target_deduction + prune_tolerance - minimum_without_perfect)
                        / perfect_min
                    ),
                )
                for perfect in range(perfect_low, perfect_high + 1):
                    row = {
                        "critical_perfect": remaining - great - perfect,
                        "perfect": perfect,
                        "great": great,
                        "good": good,
                        "miss": miss,
                    }
                    candidate_judgement = dict(judgement)
                    candidate_judgement["break"] = row
                    score_range = calc_judgement_achievement_range(
                        notes,
                        candidate_judgement,
                    )
                    if _calc_achievement_distance(achievement, score_range) != 0:
                        continue
                    midpoint = (
                        float(score_range["minimum"]) + float(score_range["maximum"])
                    ) / 2
                    candidate = {
                        "row": row,
                        "score_range": score_range,
                        "rank": (
                            distribution_penalty(row),
                            abs(float(achievement) - midpoint),
                            float(score_range["maximum"]) - float(score_range["minimum"]),
                            miss,
                            good,
                        ),
                    }
                    candidates.append(candidate)

    if not candidates:
        return None
    exact_candidates = []
    for candidate in sorted(candidates, key=lambda item: item["rank"]):
        candidate_judgement = dict(judgement)
        candidate_judgement["break"] = candidate["row"]
        detail = _infer_break_judgement_detail(
            notes,
            candidate_judgement,
            achievement,
        )
        if detail:
            candidate["break_detail"] = detail
            exact_candidates.append(candidate)
    if not exact_candidates:
        return None
    best_candidate = exact_candidates[0]
    return {
        "row": best_candidate["row"],
        "score_range": best_candidate["score_range"],
        "candidate_count": len(exact_candidates),
        "break_detail": best_candidate["break_detail"],
    }


def _infer_break_judgement_detail(notes, judgement, achievement):
    """Resolve the hidden two PERFECT and three GREAT grades for BREAK."""
    if not isinstance(achievement, (int, float)):
        return None
    break_row = judgement.get("break")
    if not isinstance(break_row, dict):
        return None
    try:
        break_count = max(0, int(notes.get("break", 0)))
        critical_perfect = max(0, int(break_row.get("critical_perfect", 0)))
        perfect = max(0, int(break_row.get("perfect", 0)))
        great = max(0, int(break_row.get("great", 0)))
        good = max(0, int(break_row.get("good", 0)))
        miss = max(0, int(break_row.get("miss", 0)))
    except (TypeError, ValueError):
        return None
    if critical_perfect + perfect + great + good + miss != break_count:
        return None

    score_judgements = {}
    for row_name in ("tap", "hold", "slide", "touch"):
        row = judgement.get(row_name) or {}
        for field_name in ("great", "good", "miss"):
            try:
                score_judgements[f"{row_name}_{field_name}"] = max(
                    0,
                    int(row.get(field_name, 0)),
                )
            except (TypeError, ValueError):
                return None
    score_judgements.update({
        "break_good": good,
        "break_miss": miss,
    })

    best_candidate = None
    candidate_count = 0
    iteration_count = 0
    for low_perfect in range(perfect + 1):
        high_perfect = perfect - low_perfect
        for low_great in range(great + 1):
            for middle_great in range(great - low_great + 1):
                iteration_count += 1
                if iteration_count > 100_000:
                    return None
                high_great = great - low_great - middle_great
                candidate_judgements = {
                    **score_judgements,
                    "break_high_perfect": high_perfect,
                    "break_low_perfect": low_perfect,
                    "break_high_great": high_great,
                    "break_middle_great": middle_great,
                    "break_low_great": low_great,
                }
                precise_calculated = calc_score_precise(notes, candidate_judgements)
                calculated = calc_score(notes, candidate_judgements)
                distance = abs(float(achievement) - calculated)
                if distance > CALC_ACHIEVEMENT_TOLERANCE + CALC_ACHIEVEMENT_EPSILON:
                    continue
                candidate = {
                    "critical_perfect": critical_perfect,
                    "perfect_high": high_perfect,
                    "perfect_low": low_perfect,
                    "great_high": high_great,
                    "great_middle": middle_great,
                    "great_low": low_great,
                    "good": good,
                    "miss": miss,
                    "precise_achievement": float(precise_calculated),
                    "calculated_achievement": calculated,
                    "rank": (
                        distance,
                        low_perfect,
                        low_great,
                        middle_great,
                    ),
                }
                candidate_count += 1
                if best_candidate is None or candidate["rank"] < best_candidate["rank"]:
                    best_candidate = candidate

    if best_candidate is None:
        return None
    best_candidate.pop("rank", None)
    best_candidate["candidate_count"] = candidate_count
    best_candidate["inferred"] = True
    return best_candidate


def _attach_break_loss_percentages(notes, break_detail):
    """Attach Calc note-score loss percentages used by result messages."""
    if not isinstance(break_detail, dict):
        return break_detail
    scores = get_note_score(notes)
    if not isinstance(scores, dict):
        return break_detail
    loss_percentages = {"critical_perfect": 0.0}
    score_keys = {
        "perfect_high": "break_high_perfect",
        "perfect_low": "break_low_perfect",
        "great_high": "break_high_great",
        "great_middle": "break_middle_great",
        "great_low": "break_low_great",
        "good": "break_good",
        "miss": "break_miss",
    }
    for detail_key, score_key in score_keys.items():
        value = scores.get(score_key)
        if isinstance(value, (int, float)):
            loss_percentages[detail_key] = float(value)
    break_detail["loss_percentages"] = loss_percentages
    break_detail["total_loss"] = sum(
        max(0, int(break_detail.get(detail_key, 0) or 0))
        * float(loss_percentages.get(detail_key, 0) or 0)
        for detail_key in loss_percentages
    )
    return break_detail


def _fixed_dxnet_note_counts(
    chart_note_counts,
    judgement,
    source_layout,
    title_match_type,
):
    if (
        source_layout != "dxnet"
        or title_match_type not in TRUSTED_TITLE_MATCH_TYPES
        or not all(isinstance(judgement.get(row), dict) for row in JUDGEMENT_ROW_NAMES)
    ):
        return chart_note_counts, False
    try:
        expected = {
            row: max(0, int(chart_note_counts.get(row, 0) or 0))
            for row in JUDGEMENT_ROW_NAMES
        }
        observed = {
            row: sum(
                max(0, int(judgement[row].get(field, 0) or 0))
                for field in ALL_JUDGEMENT_VALUE_NAMES
            )
            for row in JUDGEMENT_ROW_NAMES
        }
    except (TypeError, ValueError):
        return chart_note_counts, False

    deltas = [observed[row] - expected[row] for row in JUDGEMENT_ROW_NAMES]
    if sum(observed.values()) != sum(expected.values()) or max(map(abs, deltas)) > 2:
        return chart_note_counts, False
    if not any(deltas):
        return chart_note_counts, False
    return {**chart_note_counts, **observed, "total": sum(observed.values())}, True


def _select_validation_candidate(candidates, title_match_type, achievement):
    if not candidates:
        return None
    prefer_achievement = (
        title_match_type in TRUSTED_TITLE_MATCH_TYPES and achievement is not None
    )

    def sort_key(item):
        distance = item["achievement_distance"]
        alignment_score = (
            distance
            if prefer_achievement and distance is not None
            else (float("inf") if prefer_achievement else 0)
        )
        return (
            item["unexpected_dropped_rows"],
            item["raw_overfull_rows"],
            -item["raw_matching_rows"],
            alignment_score,
            -item["matching_rows"],
            item["compared_rows"] - item["matching_rows"],
            item["delta"],
            item["title_candidate_rank"],
            0 if (
                title_match_type == "exact"
                and item["row_offset"] == 0
                and item["column_offset"] == 0
                and item["ignored_impossible_rows"] == ["break"]
            ) else 1,
            distance if distance is not None else 0,
            item["overfull_repair_count"],
            item["overfull_repair_delta"],
            item["dropped_cells"],
            abs(item["row_offset"]),
            abs(item["column_offset"]),
        )

    candidates.sort(key=sort_key)
    best = candidates[0]
    unshifted_charts = {
        (
            str(item["song"].get("id") or ""),
            str(item["song"].get("type") or ""),
            str(item["sheet"].get("difficulty") or ""),
        )
        for item in candidates
        if item["row_offset"] == 0 and item["column_offset"] == 0
    }
    trusted_unshifted = (
        title_match_type in TRUSTED_TITLE_MATCH_TYPES
        and best["row_offset"] == 0
        and best["column_offset"] == 0
        and best["compared_rows"] >= 4
    )
    unique_unshifted = trusted_unshifted and len(unshifted_charts) == 1
    exact_unshifted = trusted_unshifted and best["matching_rows"] >= 2
    minimum_matches = max(2, best["compared_rows"] - 2)
    if best["matching_rows"] < minimum_matches and not exact_unshifted and not unique_unshifted:
        return None
    if best["row_offset"] != 0 and best["matching_rows"] < 3:
        return None

    if len(candidates) > 1 and not unique_unshifted:
        second = candidates[1]
        tied = (
            second["matching_rows"] == best["matching_rows"]
            and second["delta"] == best["delta"]
            and second["achievement_distance"] == best["achievement_distance"]
        )
        distinct_alignment = (
            second["unmatched_notes"] != best["unmatched_notes"]
            or second["row_offset"] != best["row_offset"]
            or second["column_offset"] != best["column_offset"]
        )
        if tied and distinct_alignment:
            return None
    return best


def _repair_overfull_normal_row(row_name, source_row, source_rows, note_counts, achievement):
    """Recover a JPEG-damaged normal row using chart totals and Calc."""
    row_names = JUDGEMENT_ROW_NAMES
    value_names = JUDGEMENT_VALUE_NAMES
    all_value_names = ALL_JUDGEMENT_VALUE_NAMES
    if row_name == "break":
        return None
    try:
        expected = max(0, int(note_counts.get(row_name, 0) or 0))
        original = {
            name: max(0, int(source_row.get(name, 0) or 0))
            for name in all_value_names
        }
    except (TypeError, ValueError):
        return None
    if expected <= 0 or sum(original[name] for name in value_names) <= expected:
        return None

    # JPEG artifacts sometimes prepend grid fragments to a value (16 ->
    # 1016). Keep plausible numeric suffixes as repair starting points.
    bases = [original]
    for field_name in value_names:
        current = original[field_name]
        digits = str(current)
        if current <= expected or len(digits) < 4:
            continue
        for length in range(1, min(3, len(digits) - 1) + 1):
            suffix = int(digits[-length:])
            if suffix <= expected and suffix != current:
                candidate = dict(original)
                candidate[field_name] = suffix
                bases.append(candidate)

    row_candidates = {}
    for base in bases:
        known = sum(base[name] for name in value_names)
        if known <= expected:
            candidate = dict(base)
            candidate["miss"] = expected - known
            row_candidates[tuple(candidate[name] for name in all_value_names)] = candidate
        if known < expected:
            continue
        for field_name in value_names:
            other_total = sum(
                base[name] for name in value_names if name != field_name
            )
            replacement = expected - other_total
            if 0 <= replacement < base[field_name]:
                candidate = dict(base)
                candidate[field_name] = replacement
                candidate["miss"] = 0
                row_candidates[tuple(candidate[name] for name in all_value_names)] = candidate

    if not row_candidates:
        return None

    reference_counts = {name: 0 for name in all_value_names}
    for other_name, other_row in source_rows.items():
        if other_name == row_name or not isinstance(other_row, dict):
            continue
        try:
            other_expected = max(0, int(note_counts.get(other_name, 0) or 0))
            normalized = {
                name: max(0, int(other_row.get(name, 0) or 0))
                for name in all_value_names
            }
        except (TypeError, ValueError):
            continue
        other_known = sum(normalized[name] for name in value_names)
        if other_expected <= 0 or other_known > other_expected:
            continue
        normalized["miss"] = other_expected - other_known
        for name in all_value_names:
            reference_counts[name] += normalized[name]

    reference_total = sum(reference_counts.values())
    probabilities = {
        name: (reference_counts[name] + 1.0)
        / (reference_total + len(all_value_names))
        for name in all_value_names
    }

    def distribution_penalty(candidate):
        counts = [candidate[name] for name in all_value_names]
        total = sum(counts)
        log_probability = math.lgamma(total + 1)
        log_probability -= sum(math.lgamma(count + 1) for count in counts)
        log_probability += sum(
            count * math.log(probabilities[name])
            for name, count in zip(all_value_names, counts)
        )
        return -log_probability

    def calc_distance(candidate):
        tentative = {}
        for other_name, other_row in source_rows.items():
            if not isinstance(other_row, dict):
                continue
            try:
                other_expected = max(0, int(note_counts.get(other_name, 0) or 0))
                normalized = {
                    name: max(0, int(other_row.get(name, 0) or 0))
                    for name in all_value_names
                }
            except (TypeError, ValueError):
                return float("inf")
            if other_name == row_name:
                normalized = dict(candidate)
            else:
                missing_fields = [
                    name for name in all_value_names if name not in other_row
                ]
                if len(missing_fields) == 1:
                    observed = sum(
                        normalized[name]
                        for name in all_value_names
                        if name != missing_fields[0]
                    )
                    inferred = other_expected - observed
                    if inferred >= 0:
                        normalized[missing_fields[0]] = inferred
                other_known = sum(normalized[name] for name in value_names)
                if other_known > other_expected:
                    return float("inf")
                normalized["miss"] = other_expected - other_known
            tentative[other_name] = normalized
        score_range = calc_judgement_achievement_range(
            {
                name: max(0, int(note_counts.get(name, 0) or 0))
                for name in row_names
            },
            tentative,
        )
        distance = _calc_achievement_distance(achievement, score_range)
        return float("inf") if distance is None else distance

    ranked = sorted(
        row_candidates.values(),
        key=lambda candidate: (
            calc_distance(candidate),
            sum(candidate[name] != original[name] for name in all_value_names),
            sum(
                {
                    "critical_perfect": 4,
                    "perfect": 3,
                    "great": 2,
                    "good": 1,
                    "miss": 1,
                }[name]
                for name in all_value_names
                if candidate[name] != original[name]
            ),
            sum(abs(candidate[name] - original[name]) for name in all_value_names),
            distribution_penalty(candidate),
        ),
    )
    repaired = ranked[0]
    corrections = [
        {
            "row": row_name,
            "field": name,
            "ocr": original[name],
            "validated": repaired[name],
            "overfull_repair": True,
        }
        for name in value_names
        if repaired[name] != original[name]
    ]
    return repaired, corrections

def _evaluate_judgement_alignment(
    row_aligned, note_counts, achievement, *, row_offset, column_offset,
    title_match_type, allow_ocr_alignment, preserve_input,
):
    """Validate one alignment; invalid candidates return None, input rows stay intact."""
    row_names = JUDGEMENT_ROW_NAMES
    value_names = JUDGEMENT_VALUE_NAMES
    all_value_names = ALL_JUDGEMENT_VALUE_NAMES
    aligned = {}
    dropped_cells = 0
    ignored_impossible_rows = []
    inferred_single_cells = []
    valid = True
    for row_name, row in row_aligned.items():
        shifted_row = {name: 0 for name in all_value_names}
        try:
            for source_index, source_name in enumerate(all_value_names):
                value = max(0, int(row.get(source_name, 0)))
                target_index = source_index + column_offset
                if 0 <= target_index < len(all_value_names):
                    shifted_row[all_value_names[target_index]] = value
                elif value:
                    dropped_cells += value
        except (TypeError, ValueError):
            valid = False
            break
        missing_fields = [
            name for name in all_value_names
            if name not in row
        ]
        if (
            title_match_type == "exact"
            and row_offset == 0
            and column_offset == 0
            and len(missing_fields) == 1
        ):
            expected = max(0, int(note_counts.get(row_name, 0) or 0))
            observed = sum(
                max(0, int(row.get(name, 0) or 0))
                for name in all_value_names
                if name in row
            )
            inferred = expected - observed
            if inferred >= 0:
                field_name = missing_fields[0]
                shifted_row[field_name] = inferred
                inferred_single_cells.append({
                    "row": row_name,
                    "field": field_name,
                    "validated": inferred,
                })
        aligned[row_name] = shifted_row
    if not valid:
        return None

    unmatched_notes = {}
    compared_rows = 0
    matching_rows = 0
    total_delta = 0
    for row_name, row in list(aligned.items()):
        expected = note_counts.get(row_name)
        if expected is None:
            expected = 0
        try:
            expected = int(expected)
            known = sum(max(0, int(row.get(name, 0))) for name in value_names)
            observed_miss = max(0, int(row.get("miss", 0)))
        except (TypeError, ValueError):
            valid = False
            break
        if (
            expected <= 0
            and (known > 0 or observed_miss > 0)
            and not preserve_input
            and title_match_type == "exact"
            and row_offset == 0
            and column_offset == 0
        ):
            for field_name in all_value_names:
                previous = max(0, int(row.get(field_name, 0) or 0))
                row[field_name] = 0
                if previous:
                    inferred_single_cells.append({
                        "row": row_name,
                        "field": field_name,
                        "ocr": previous,
                        "validated": 0,
                        "zero_note_row_repair": True,
                    })
            known = 0
            observed_miss = 0
        if known > expected:
            if (
                not preserve_input
                and title_match_type in OVERFULL_REPAIR_TITLE_MATCH_TYPES
                and row_offset == 0
                and column_offset == 0
            ):
                repair = _repair_overfull_normal_row(
                    row_name,
                    row,
                    row_aligned,
                    note_counts,
                    achievement,
                )
                if repair:
                    repaired_row, row_corrections = repair
                    row.update(repaired_row)
                    known = sum(
                        max(0, int(row.get(name, 0)))
                        for name in value_names
                    )
                    inferred_single_cells.extend(row_corrections)
            if known > expected:
                if (
                    allow_ocr_alignment
                    and not preserve_input
                    and title_match_type == "exact"
                    and row_offset == 0
                    and column_offset == 0
                    and row_name == "break"
                    and all(
                        int(note_counts.get(name, 0) or 0) == 0
                        or (
                            name in aligned
                            and sum(aligned[name].values()) == int(note_counts[name])
                        )
                        for name in row_names if name != "break"
                    )
                ):
                    ignored_impossible_rows.append(row_name)
                    del aligned[row_name]
                    continue
                valid = False
                break
        row_unmatched_notes = expected - known - observed_miss
        unmatched_notes[row_name] = row_unmatched_notes
        compared_rows += 1
        total_delta += abs(row_unmatched_notes)
        if row_unmatched_notes == 0:
            matching_rows += 1
    if not valid or compared_rows < 3:
        return None
    calculated_rows = {
        row_name: dict(row)
        for row_name, row in aligned.items()
    }
    notes = {
        row_name: int(note_counts.get(row_name, 0) or 0)
        for row_name in row_names
    }
    achievement_range = calc_judgement_achievement_range(
        notes,
        calculated_rows,
    )
    achievement_distance = _calc_achievement_distance(
        achievement,
        achievement_range,
    )
    return {
        "aligned": aligned,
        "row_offset": row_offset,
        "column_offset": column_offset,
        "dropped_cells": dropped_cells,
        "ignored_impossible_rows": ignored_impossible_rows,
        "inferred_single_cells": inferred_single_cells,
        "overfull_repair_count": sum(
            bool(item.get("overfull_repair"))
            for item in inferred_single_cells
        ),
        "overfull_repair_delta": sum(
            abs(
                int(item.get("validated", 0) or 0)
                - int(item.get("ocr", 0) or 0)
            )
            for item in inferred_single_cells
            if item.get("overfull_repair")
        ),
        "unmatched_notes": unmatched_notes,
        "compared_rows": compared_rows,
        "matching_rows": matching_rows,
        "delta": total_delta,
        "notes": notes,
        "achievement_range": achievement_range,
        "achievement_distance": achievement_distance,
    }


def _judgement_validation_candidates(
    judgement, matching_songs, title_match_type, achievement, source_layout,
    *, allow_ocr_alignment, preserve_input,
):
    """Score possible chart, row and column alignments without changing OCR input."""
    row_names = JUDGEMENT_ROW_NAMES
    all_value_names = ALL_JUDGEMENT_VALUE_NAMES
    title_candidate_ranks = {
        song_identity_key(song): index
        for index, song in enumerate(matching_songs)
    }
    source_row_count = sum(
        1 for row in judgement.values()
        if isinstance(row, dict) and (
            preserve_input
            or any(int(value or 0) != 0 for value in row.values())
        )
    )
    candidates = []
    for song in matching_songs:
        for sheet in song.get("sheets", []):
            chart_note_counts = sheet.get("noteCounts") or {}
            raw_overfull_rows = 0
            raw_matching_rows = 0
            for row_name in row_names:
                row = judgement.get(row_name)
                if not isinstance(row, dict):
                    continue
                try:
                    expected = max(0, int(chart_note_counts.get(row_name, 0) or 0))
                    observed = sum(
                        max(0, int(row.get(name, 0) or 0))
                        for name in all_value_names
                    )
                except (TypeError, ValueError):
                    continue
                if observed > expected:
                    raw_overfull_rows += 1
                elif observed == expected:
                    raw_matching_rows += 1
            note_counts, dxnet_fixed_note_counts = _fixed_dxnet_note_counts(
                chart_note_counts,
                judgement,
                source_layout,
                title_match_type,
            )
            alignment_enabled = allow_ocr_alignment and source_layout != "dxnet"
            row_offsets = range(-2, 3) if alignment_enabled else (0,)
            column_offsets = (-1, 0, 1) if alignment_enabled else (0,)
            for row_offset in row_offsets:
                row_aligned = {}
                for source_index, source_name in enumerate(row_names):
                    row = judgement.get(source_name)
                    if not isinstance(row, dict) or (
                        not preserve_input
                        and not any(int(value or 0) != 0 for value in row.values())
                    ):
                        continue
                    target_index = source_index + row_offset
                    if 0 <= target_index < len(row_names):
                        row_aligned[row_names[target_index]] = dict(row)

                for column_offset in column_offsets:
                    candidate = _evaluate_judgement_alignment(
                        row_aligned, note_counts, achievement,
                        row_offset=row_offset, column_offset=column_offset,
                        title_match_type=title_match_type,
                        allow_ocr_alignment=allow_ocr_alignment,
                        preserve_input=preserve_input,
                    )
                    if candidate is None:
                        continue
                    dropped_rows = source_row_count - len(candidate["aligned"])
                    candidates.append({
                        **candidate,
                        "song": song,
                        "sheet": sheet,
                        "dropped_rows": dropped_rows,
                        "unexpected_dropped_rows": max(
                            0, dropped_rows - len(candidate["ignored_impossible_rows"]),
                        ),
                        "raw_overfull_rows": raw_overfull_rows,
                        "raw_matching_rows": raw_matching_rows,
                        "dxnet_fixed_note_counts": dxnet_fixed_note_counts,
                        "title_candidate_rank": title_candidate_ranks.get(
                            song_identity_key(song), len(title_candidate_ranks),
                        ),
                    })

    return candidates


def _apply_judgement_validation(result, best, title_match_type, *, preserve_input):
    """Apply the selected chart and publish corrections, uncertainty and Calc details."""
    parsed = result.get("parsed") or {}
    title = str(parsed.get("title") or "").strip()
    achievement = parsed.get("achievement")
    all_value_names = ALL_JUDGEMENT_VALUE_NAMES
    judgement = best["aligned"]
    for row_name, expected_notes in best["notes"].items():
        if int(expected_notes or 0) == 0 and not isinstance(judgement.get(row_name), dict):
            judgement[row_name] = {
                field_name: 0
                for field_name in all_value_names
            }
    parsed["sub_judgement"] = judgement
    song = best["song"]
    sheet = best["sheet"]
    achievement_distance = best["achievement_distance"]
    achievement_range = best["achievement_range"]
    calc_uncertainties = []
    calc_corrections = [
        {**item, "ocr": item.get("ocr"), "single_missing_cell": True}
        for item in best.get("inferred_single_cells", [])
    ]
    break_inference = None
    if not preserve_input:
        break_inference = _infer_missing_break_judgement(
            best["notes"],
            judgement,
            achievement,
        )
    if break_inference:
        judgement["break"] = break_inference["row"]
        parsed["sub_judgement"] = judgement
        achievement_range = break_inference["score_range"]
        achievement_distance = _calc_achievement_distance(
            achievement,
            achievement_range,
        )
        calc_corrections.append({
            "row": "break",
            "field": "row",
            "inferred_row": True,
            "validated_row": break_inference["row"],
            "candidate_count": break_inference["candidate_count"],
        })
    if achievement_distance is not None and achievement_distance > 0:
        calc_uncertainties = _find_calc_judgement_uncertainties(
            best["notes"],
            judgement,
            achievement,
        )
    else:
        for row_name, expected in best["notes"].items():
            if expected > 0 and not isinstance(judgement.get(row_name), dict):
                calc_uncertainties.append({
                    "row": row_name,
                    "field": "row",
                    "ocr": None,
                    "candidate_min": None,
                    "candidate_max": None,
                    "candidate_count": 0,
                    "miss_min": None,
                    "miss_max": None,
                    "row_missing": True,
                })
    break_detail = (
        break_inference.get("break_detail")
        if break_inference
        else _infer_break_judgement_detail(
            best["notes"],
            judgement,
            achievement,
        )
    )
    if break_detail and break_inference:
        break_detail["row_candidate_count"] = break_inference["candidate_count"]
    break_detail = _attach_break_loss_percentages(best["notes"], break_detail)
    loss_percentages = get_note_score(best["notes"])
    unmatched_notes = {
        row_name: int(value)
        for row_name, value in (best.get("unmatched_notes") or {}).items()
        if int(value or 0) != 0
    }
    calc_completion_candidates = _find_calc_completion_candidates(
        best["notes"],
        judgement,
        unmatched_notes,
        achievement,
        parsed.get("sub_judgement_confidence") or {},
    )
    canonical_title = song.get("title")
    parsed["title"] = canonical_title if canonical_title is not None else title
    result["validation"] = {
        "song_id": song.get("id"),
        "title": song.get("title"),
        "type": song.get("type"),
        "cover_url": song.get("cover_url"),
        "cover_name": song.get("cover_name"),
        "difficulty": sheet.get("difficulty"),
        "level": sheet.get("level"),
        "internal_level": sheet.get("internalLevelValue"),
        "title_match_type": title_match_type,
        "exact_title_match": title_match_type in {"exact", "blank"},
        "compared_rows": best["compared_rows"],
        "matching_rows": best["matching_rows"],
        "row_offset": best["row_offset"],
        "column_offset": best["column_offset"],
        "dxnet_fixed_note_counts": best.get("dxnet_fixed_note_counts", False),
        "miss_corrections": {},  # Retained for the public response contract.
        "unmatched_notes": unmatched_notes,
        "achievement_calc": {
            "observed": achievement,
            "minimum": (
                achievement_range.get("minimum")
                if achievement_range else None
            ),
            "maximum": (
                achievement_range.get("maximum")
                if achievement_range else None
            ),
            "consistent": achievement_distance == 0 if achievement_distance is not None else None,
            "complete": (
                not any(item.get("row_missing") for item in calc_uncertainties)
                and not unmatched_notes
            ),
        },
        "calc_corrections": calc_corrections,
        "calc_completion_candidates": calc_completion_candidates,
        "calc_completion_candidate_count": len(calc_completion_candidates),
        "uncertain_cells": calc_uncertainties,
        "break_detail": break_detail,
        "loss_percentages": loss_percentages,
    }
    return result


def _validate_recognized_judgement(
    result,
    ver="jp",
    allow_ocr_alignment=True,
    preserve_input=False,
):
    parsed = result.get("parsed") or {}
    title = str(parsed.get("title") or "").strip()
    judgement = parsed.get("sub_judgement") or {}
    source_layout = str(
        (result.get("crop_metadata") or {}).get("layout") or ""
    ).lower()
    if not judgement:
        return result

    songs, _ = read_dxdata(ver)
    if title:
        matching_songs, title_match_type = match_recognized_song_title(
            title,
            songs,
            max_results=120,
        )
    else:
        matching_songs = [
            song for song in songs
            if not str(song.get("title") or "").strip()
        ]
        title_match_type = "blank"
    if not matching_songs:
        return result
    candidates = _judgement_validation_candidates(
        judgement, matching_songs, title_match_type, parsed.get("achievement"), source_layout,
        allow_ocr_alignment=allow_ocr_alignment, preserve_input=preserve_input,
    )
    best = _select_validation_candidate(candidates, title_match_type, parsed.get("achievement"))
    if best is None:
        return result
    return _apply_judgement_validation(result, best, title_match_type, preserve_input=preserve_input)


def validate_recognized_judgement(
    result, ver="jp", allow_ocr_alignment=True, preserve_input=False, *, image_bytes=None,
):
    # Keep OCR output intact for failed-validation UI and manual correction.
    raw_parsed = deepcopy(result.get("raw_parsed", result.get("parsed") or {}))
    result = _validate_recognized_judgement(result, ver, allow_ocr_alignment, preserve_input)
    result["raw_parsed"] = raw_parsed
    return result


def recognize_score_with_ai(image_bytes: bytes, *, user_id: str, ver="jp"):
    """Explicit ai-rec entry point; authorization precedes any paid/model work."""
    from modules.score_recognition.access import require_ai_recognition_access

    require_ai_recognition_access(user_id)
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            if str(image.format or "").upper() not in SUPPORTED_SCORE_IMAGE_FORMATS:
                raise UnsupportedScoreImageError("Supported image formats are JPEG, PNG, and WebP")
            if image.width * image.height > MAX_SCORE_IMAGE_PIXELS:
                raise InvalidScoreImageError("Image dimensions exceed the pixel limit")
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidScoreImageError("Uploaded data is not a valid image") from exc
    result = _recognize_ai_result(image_bytes, ver=ver)
    if not _score_is_validated(result):
        raise ValueError("AI recognition did not produce a validated score")
    return result


def _recognize_ai_result(image_bytes, ver="jp"):
    result = {"parsed": {}}
    try:
        from modules.monitoring.codex_agent import recognize_score_with_codex

        parsed = recognize_score_with_codex(image_bytes)
        if not isinstance(parsed, dict):
            return result
        title, achievement = parsed.get("title"), parsed.get("achievement")
        judgement = parsed.get("sub_judgement")
        if not isinstance(title, str) or len(title) > 500:
            logger.warning("[Recognize] AI recognition rejected: invalid title")
            return result
        if type(achievement) not in (int, float) or not 0 <= achievement <= 101:
            logger.warning("[Recognize] AI recognition rejected: invalid achievement=%r", achievement)
            return result
        if not isinstance(judgement, dict):
            return result
        clean_rows = {}
        for name in JUDGEMENT_ROW_NAMES:
            row = judgement.get(name)
            if not isinstance(row, dict):
                logger.warning("[Recognize] AI recognition rejected: missing row=%s", name)
                return result
            if any(type(row.get(field)) is not int or not 0 <= row[field] <= 100000
                   for field in ALL_JUDGEMENT_VALUE_NAMES):
                logger.warning("[Recognize] AI recognition rejected: invalid cells row=%s values=%s", name, row)
                return result
            clean_rows[name] = {field: row[field] for field in ALL_JUDGEMENT_VALUE_NAMES}
        totals = parsed.get("judgement_totals")
        if isinstance(totals, dict):
            for field in ALL_JUDGEMENT_VALUE_NAMES:
                expected = totals.get(field)
                if expected is None:
                    continue
                observed = sum(row[field] for row in clean_rows.values())
                if type(expected) is not int or expected != observed:
                    logger.warning(
                        "[Recognize] AI recognition rejected: column_total_mismatch "
                        "field=%s table=%s main_screen=%r title=%r",
                        field, observed, expected, title,
                    )
                    return result
        candidate = _validate_recognized_judgement(
            {"source": "codex", "parsed": {"title": title, "achievement": achievement,
                                            "sub_judgement": clean_rows}},
            ver=ver, allow_ocr_alignment=False, preserve_input=True,
        )
        if _score_is_validated(candidate):
            logger.info("[Recognize] AI recognition passed chart and achievement validation")
            return candidate
        checked = candidate.get("validation") or {}
        calc = checked.get("achievement_calc") or {}
        reason = (
            "chart_not_matched" if not checked.get("song_id") else
            "achievement_mismatch" if calc.get("consistent") is not True else
            "incomplete_judgement" if calc.get("complete") is not True else
            "uncertain_cells"
        )
        if not checked.get("song_id"):
            songs, _ = read_dxdata(ver)
            matches, match_type = match_recognized_song_title(title, songs, max_results=120)
            if matches:
                reason = "chart_judgement_mismatch"
                observed = {name: sum(row.values()) for name, row in clean_rows.items()}
                charts = []
                for song in matches:
                    for sheet in song.get("sheets", []):
                        counts = sheet.get("noteCounts") or {}
                        delta = {name: observed[name] - int(counts.get(name, 0) or 0)
                                 for name in JUDGEMENT_ROW_NAMES}
                        charts.append(dict(song_id=song.get("id"), difficulty=sheet.get("difficulty"),
                                           delta=delta, distance=sum(abs(n) for n in delta.values())))
                charts.sort(key=lambda chart: chart["distance"])
                logger.warning(
                    "[Recognize] Codex title matched: match=%s observed_row_totals=%s "
                    "nearest_charts=%s (delta=observed-minus-chart)",
                    match_type, observed, charts[:3],
                )
        logger.warning(
            "[Recognize] AI recognition rejected: reason=%s title=%r achievement=%s "
            "ver=%s song_id=%s difficulty=%s calc=%s unmatched=%s uncertain=%s rows=%s",
            reason, title, achievement, ver, checked.get("song_id"), checked.get("difficulty"),
            calc, checked.get("unmatched_notes"), checked.get("uncertain_cells"), clean_rows,
        )
    except Exception as exc:
        # Report model failure through the explicit AI entry point.
        logger.warning("[Recognize] AI recognition unavailable: %s", type(exc).__name__)
    return result


def _score_is_validated(result):
    validation = result.get("validation") or {}
    achievement_calc = validation.get("achievement_calc") or {}
    return (
        bool(validation.get("song_id"))
        and achievement_calc.get("consistent") is True
        and achievement_calc.get("complete") is True
        and not validation.get("uncertain_cells")
    )


def score_recognition_needs_manual_fix(result) -> bool:
    judgement = (result.get("parsed") or {}).get("sub_judgement") or {}
    fully_validated = _score_is_validated(result)
    has_judgement_data = any(
        isinstance(judgement.get(row_name), dict)
        for row_name in JUDGEMENT_ROW_NAMES
    )
    return has_judgement_data and not fully_validated






def _load_ocr_module() -> tuple[tuple[str, ...], Any, Any]:
    global _OCR_FIELDS, _PROCESS_IMAGE_DATA
    if _OCR_FIELDS is None or _PROCESS_IMAGE_DATA is None:
        from modules.score_recognition.ocr import OCR_FIELDS, PaddleOcrEngine, process_image_data

        _OCR_FIELDS = OCR_FIELDS
        _PROCESS_IMAGE_DATA = process_image_data
        return OCR_FIELDS, PaddleOcrEngine, process_image_data

    from modules.score_recognition.ocr import PaddleOcrEngine

    return _OCR_FIELDS, PaddleOcrEngine, _PROCESS_IMAGE_DATA


def _engine() -> Any:
    global _ENGINE, _OCR_LAST_USED
    with _ENGINE_LOCK:
        if _ENGINE is None:
            _, PaddleOcrEngine, _ = _load_ocr_module()
            _ENGINE = PaddleOcrEngine(lang="japan")
        _OCR_LAST_USED = time.monotonic()
        return _ENGINE


def _reset_ocr_engine(reason: str, rss_mb: float | None = None) -> bool:
    global _ENGINE, _ENGINE_REQUEST_COUNT
    with _ENGINE_LOCK:
        if _ENGINE is None:
            return False
        _ENGINE = None
        _ENGINE_REQUEST_COUNT = 0
    collected = gc.collect()
    logger.info(
        "[Recognize] OCR engine reset: reason=%s rss=%sMB collected=%s",
        reason,
        rss_mb,
        collected,
    )
    return True


def cleanup_score_recognizer_memory() -> bool:
    """Recycle only loaded components; never import models just to clean up."""
    cleaned = False
    for module_name, callback in (
        ('modules.score_recognition.ocr', 'cleanup_table_model_memory'),
        ('modules.score_recognition.cropper', 'cleanup_cropper_memory'),
    ):
        module = sys.modules.get(module_name)
        if module is not None:
            cleaned = getattr(module, callback)() or cleaned
    if not _OCR_LOCK.acquire(blocking=False):
        return cleaned
    try:
        rss_mb = _process_rss_mb()
        idle = OCR_IDLE_SECONDS > 0 and time.monotonic() - _OCR_LAST_USED >= OCR_IDLE_SECONDS
        high_rss = (OCR_ENGINE_IDLE_RESET_RSS_MB > 0 and rss_mb is not None
                    and rss_mb >= OCR_ENGINE_IDLE_RESET_RSS_MB)
        if _ENGINE is not None and (idle or high_rss):
            cleaned = _reset_ocr_engine('idle_timeout' if idle else 'idle_rss_threshold', rss_mb) or cleaned
            if idle:
                try:
                    _engine()
                    logger.info('[Recognize] Rebuilt idle OCR engine')
                except Exception:
                    logger.exception('[Recognize] Idle OCR rebuild failed; next request will retry')
    finally:
        _OCR_LOCK.release()
    return cleaned


def initialize_score_recognizer() -> None:
    _engine()
    try:
        from modules.score_recognition.ocr import warm_table_model

        warm_table_model()
    except Exception as exc:
        logger.warning(
            "[Recognize] Table OCR warmup failed; column OCR fallback remains available: %s",
            exc,
        )


def build_score_crop_preview_image(image_bytes: bytes, *, skin=None, ver="jp", timezone_offset=9, bg_filter=None) -> Image.Image:
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            image_format = str(source.format or "").upper()
            if image_format not in SUPPORTED_SCORE_IMAGE_FORMATS:
                raise UnsupportedScoreImageError(
                    "Supported image formats are JPEG, PNG, and WebP"
                )
            width, height = source.size
            if width <= 0 or height <= 0 or width * height > MAX_SCORE_IMAGE_PIXELS:
                raise InvalidScoreImageError(
                    f"Image dimensions exceed the {MAX_SCORE_IMAGE_PIXELS}-pixel limit"
                )
            image = source.convert("RGB")
    except UnsupportedScoreImageError:
        raise
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidScoreImageError("Uploaded data is not a valid image") from exc

    from modules.score_recognition.cropper import crop_result_fields_in_memory

    metadata = crop_result_fields_in_memory(image)
    field_order = (
        "main_title",
        "main_achievement",
        "sub_judgement_table",
    )
    crops = [
        (field_name, metadata["fields"][field_name]["image"].convert("RGB"))
        for field_name in field_order
        if field_name in metadata.get("fields", {})
    ]
    if not crops:
        raise InvalidScoreImageError("No score result crop fields were detected")

    from modules.images.records import generate_crop_preview_picture
    try:
        return generate_crop_preview_picture(crops, skin=skin, ver=ver,
                                             timezone_offset=timezone_offset, bg_filter=bg_filter)
    finally:
        image.close()
        for _, crop in crops:
            crop.close()
        for field in metadata.get("fields", {}).values():
            if isinstance(field.get("image"), Image.Image):
                field["image"].close()


def recognize_score_image_bytes(
    image_bytes: bytes,
    fields: tuple[str, ...] | None = None,
    line_like_preprocess: bool = False,
    ver: str = "jp",
) -> dict[str, Any]:
    global _ENGINE_REQUEST_COUNT, _OCR_LAST_USED
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            image_format = str(source.format or "").upper()
            if image_format not in SUPPORTED_SCORE_IMAGE_FORMATS:
                raise UnsupportedScoreImageError(
                    "Supported image formats are JPEG, PNG, and WebP"
                )
            width, height = source.size
            if width <= 0 or height <= 0 or width * height > MAX_SCORE_IMAGE_PIXELS:
                raise InvalidScoreImageError(
                    f"Image dimensions exceed the {MAX_SCORE_IMAGE_PIXELS}-pixel limit"
                )
            image = source.convert("RGB")
            if line_like_preprocess:
                image = _line_like_ocr_image(image, image_format)
    except UnsupportedScoreImageError:
        raise
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidScoreImageError("Uploaded data is not a valid image") from exc

    try:
        # PaddleOCR inference is heavy and may not be thread-safe across concurrent
        # LINE tasks. Serialize access to the shared model instance.
        lock_started_at = time.perf_counter()
        with _OCR_LOCK:
            lock_wait_seconds = time.perf_counter() - lock_started_at
            if lock_wait_seconds >= 1.0:
                logger.info("[Recognize] OCR lock wait: %.3fs", lock_wait_seconds)
            rss_before = _process_rss_mb()
            ocr_fields, _, process_image_data = _load_ocr_module()
            try:
                result = process_image_data(
                    image,
                    fields or ocr_fields,
                    None,
                    engine_factory=_engine,
                )
            finally:
                _OCR_LAST_USED = time.monotonic()
            _ENGINE_REQUEST_COUNT += 1
            rss_after = _process_rss_mb()
            if rss_before is not None or rss_after is not None:
                logger.info(
                    "[Recognize] OCR memory: rss_before=%sMB rss_after=%sMB requests=%s",
                    rss_before,
                    rss_after,
                    _ENGINE_REQUEST_COUNT,
                )
            if (
                OCR_ENGINE_MAX_REQUESTS > 0
                and _ENGINE_REQUEST_COUNT >= OCR_ENGINE_MAX_REQUESTS
            ):
                _reset_ocr_engine("request_threshold", rss_after)
            elif (
                OCR_ENGINE_MAX_RSS_MB > 0
                and rss_after is not None
                and rss_after >= OCR_ENGINE_MAX_RSS_MB
            ):
                _reset_ocr_engine("rss_threshold", rss_after)
            return result

    finally:
        image.close()
