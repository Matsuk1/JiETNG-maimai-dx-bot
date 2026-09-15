"""API response contracts and Flex presentation of score-recognition results.

Pure transformations: importing this module never starts OCR or loads configuration.
"""
from __future__ import annotations

from typing import Any
import math
import re
from modules.score_rules import (
    JUDGEMENT_ROWS,
    DIFFICULTY_LABELS,
    DIFFICULTY_STYLES,
    score_rank as _score_rank,
    combo_status as _combo_status,
    nonnegative_count,
)


JUDGEMENT_FIELDS = (
    "critical_perfect",
    "perfect",
    "great",
    "good",
    "miss",
)
BREAK_DETAIL_FIELDS = (
    "critical_perfect",
    "perfect_high",
    "perfect_low",
    "great_high",
    "great_middle",
    "great_low",
    "good",
    "miss",
    "candidate_count",
    "row_candidate_count",
)
NORMAL_LOSS_FIELDS = ("great", "good", "miss")
CALC_CORRECTION_FIELDS = (
    "row",
    "field",
    "ocr",
    "validated",
    "miss_ocr",
    "miss_validated",
    "inferred_row",
    "candidate_count",
)

PLAYLOG_ICON_BASE_URL = "https://maimaidx.jp/maimai-mobile/img/playlog"
SONG_TYPE_ICON_URLS = {
    "std": "https://maimaidx.jp/maimai-mobile/img/music_standard.png",
    "dx": "https://maimaidx.jp/maimai-mobile/img/music_dx.png",
    "utage": "https://maimaidx.jp/maimai-mobile/img/diff_utage.png",
}
RANK_ICON_URLS = {
    rank: f"{PLAYLOG_ICON_BASE_URL}/{rank.replace('+', 'plus')}.png"
    for rank in ("sss+", "sss", "ss+", "ss", "s+", "s", "aaa", "aa", "a", "bbb", "bb", "b", "c", "d")
}
COMBO_ICON_URLS = {
    "fc": f"{PLAYLOG_ICON_BASE_URL}/fc.png",
    "fc+": f"{PLAYLOG_ICON_BASE_URL}/fcplus.png",
    "ap": f"{PLAYLOG_ICON_BASE_URL}/ap.png",
    "ap+": f"{PLAYLOG_ICON_BASE_URL}/applus.png",
}


UNCERTAIN_CELL_FIELDS = (
    "row",
    "field",
    "ocr",
    "candidate_min",
    "candidate_max",
    "candidate_count",
    "miss_min",
    "miss_max",
    "row_missing",
)


class ScoreRecognitionResultError(ValueError):
    """The OCR result cannot be exposed as a complete score result."""


def _selected_mapping(value: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {field: value.get(field) for field in fields if field in value}


def _selected_list(value: Any, fields: tuple[str, ...]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        selected = _selected_mapping(item, fields)
        if isinstance(item, dict) and isinstance(item.get("validated_row"), dict):
            selected["validated_row"] = {
                field: max(0, int(item["validated_row"].get(field, 0) or 0))
                for field in JUDGEMENT_FIELDS
            }
        if selected:
            result.append(selected)
    return result


def _miss_corrections(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    return {
        row_name: _selected_mapping(correction, ("ocr", "validated"))
        for row_name, correction in value.items()
        if isinstance(correction, dict)
    }


def _loss_value(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _format_loss(value: float) -> float:
    return round(float(value), 4)


def _build_loss_detail(
    judgements: dict[str, dict[str, int]],
    loss_percentages: Any,
) -> dict[str, Any]:
    if not isinstance(loss_percentages, dict):
        loss_percentages = {}
    rows: dict[str, Any] = {}
    total_loss = 0.0
    for row_name in ("tap", "hold", "slide", "touch"):
        row = judgements.get(row_name)
        if not isinstance(row, dict):
            continue
        cells = {}
        row_total = 0.0
        for field_name in NORMAL_LOSS_FIELDS:
            count = nonnegative_count(row.get(field_name))
            loss_per_note = _loss_value(loss_percentages.get(f"{row_name}_{field_name}"))
            loss = loss_per_note * count
            cells[field_name] = {
                "count": count,
                "loss_per_note": _format_loss(loss_per_note),
                "total_loss": _format_loss(loss),
            }
            row_total += loss
        if row_total > 0:
            rows[row_name] = {
                "cells": cells,
                "total_loss": _format_loss(row_total),
            }
            total_loss += row_total
    return {
        "rows": rows,
        "total_loss": _format_loss(total_loss),
    }


def _build_break_detail(value: Any) -> dict[str, Any]:
    detail = _selected_mapping(value, BREAK_DETAIL_FIELDS)
    if not detail:
        return {}
    loss_percentages = value.get("loss_percentages") if isinstance(value, dict) else {}
    if isinstance(loss_percentages, dict):
        selected_loss_percentages = {
            key: _format_loss(_loss_value(loss_percentages.get(key)))
            for key in (
                "critical_perfect",
                "perfect_high",
                "perfect_low",
                "great_high",
                "great_middle",
                "great_low",
                "good",
                "miss",
            )
            if key in loss_percentages
        }
        detail["loss_percentages"] = selected_loss_percentages
        total_loss = sum(
            _loss_value(loss_percentages.get(key)) * nonnegative_count(detail.get(key))
            for key in (
                "perfect_high",
                "perfect_low",
                "great_high",
                "great_middle",
                "great_low",
                "good",
                "miss",
            )
        )
        detail["total_loss"] = _format_loss(total_loss)
    return detail


def _build_display_metadata(validation: dict[str, Any]) -> dict[str, Any]:
    chart_type = str(validation.get("type") or "").lower()
    difficulty = str(validation.get("difficulty") or "").lower()
    type_label = {"dx": "DX", "std": "STD", "utage": "UTAGE"}.get(chart_type)
    title = validation.get("title")
    display_title = '""' if title == "" else str(title or "")
    if type_label:
        display_title = f"{display_title} [{type_label}]"
    difficulty_style = DIFFICULTY_STYLES.get(
        difficulty,
        {"background": "#315B7D", "text": "#FFFFFF", "metric": "#315B7D"},
    )
    return {
        "display_title": display_title,
        "subtitle_template": "Judgement Details {difficulty} {type_icon}",
        "type_label": type_label,
        "type_icon_url": SONG_TYPE_ICON_URLS.get(chart_type),
        "difficulty_label": DIFFICULTY_LABELS.get(difficulty, difficulty.upper() if difficulty else None),
        "difficulty_style": difficulty_style,
    }


def _complete_judgements(value: Any) -> dict[str, dict[str, int]]:
    if not isinstance(value, dict):
        raise ScoreRecognitionResultError("No complete judgement data was recognized")

    result: dict[str, dict[str, int]] = {}
    for row_name in JUDGEMENT_ROWS:
        row = value.get(row_name)
        if not isinstance(row, dict):
            raise ScoreRecognitionResultError(
                f"Judgement row '{row_name}' was not recognized"
            )
        try:
            result[row_name] = {
                field_name: max(0, int(row.get(field_name, 0) or 0))
                for field_name in JUDGEMENT_FIELDS
            }
        except (TypeError, ValueError) as exc:
            raise ScoreRecognitionResultError(
                f"Judgement row '{row_name}' contains an invalid value"
            ) from exc
    return result


def build_score_recognition_response(result: Any) -> dict[str, Any]:
    """Convert an internal OCR result into the documented API response."""
    if not isinstance(result, dict):
        raise ScoreRecognitionResultError("OCR did not return a result")

    parsed = result.get("parsed")
    validation = result.get("validation")
    if not isinstance(parsed, dict) or not isinstance(validation, dict):
        raise ScoreRecognitionResultError(
            "The score could not be matched to a song and chart"
        )

    song_id = validation.get("song_id")
    if song_id is None or song_id == "":
        raise ScoreRecognitionResultError("The recognized song could not be identified")

    achievement = parsed.get("achievement")
    if (
        isinstance(achievement, bool)
        or not isinstance(achievement, (int, float))
        or not math.isfinite(achievement)
        or not 0 <= achievement <= 101
    ):
        raise ScoreRecognitionResultError("Achievement was not recognized")

    achievement_calc = validation.get("achievement_calc") or {}
    if (
        achievement_calc.get("consistent") is not True
        or achievement_calc.get("complete") is not True
        or validation.get("uncertain_cells")
        or validation.get("unmatched_notes")
    ):
        raise ScoreRecognitionResultError("The score did not pass complete Calc validation")

    judgements = _complete_judgements(parsed.get("sub_judgement"))
    rank = _score_rank(achievement)
    combo = _combo_status(achievement, judgements)
    break_detail = _build_break_detail(validation.get("break_detail"))
    loss_detail = _build_loss_detail(judgements, validation.get("loss_percentages"))
    return {
        "success": True,
        "song": {
            "id": song_id,
            "title": validation.get("title"),
            "type": validation.get("type"),
        },
        "chart": {
            "difficulty": validation.get("difficulty"),
            "level": validation.get("level"),
            "internal_level": validation.get("internal_level"),
        },
        "score": {
            "achievement": float(achievement),
            "rank": rank,
            "combo": combo,
            "status": {
                "rank": rank,
                "rank_icon_url": RANK_ICON_URLS.get(str(rank or "").lower()),
                "combo": combo,
                "combo_icon_url": COMBO_ICON_URLS.get(str(combo or "").lower()),
            },
            "judgements": judgements,
            "loss_detail": loss_detail,
            "break_detail": break_detail,
        },
        "metadata": _build_display_metadata(validation),
        "validation": {
            "title_match_type": validation.get("title_match_type"),
            "exact_title_match": bool(validation.get("exact_title_match")),
            "compared_rows": validation.get("compared_rows"),
            "matching_rows": validation.get("matching_rows"),
            "row_offset": validation.get("row_offset"),
            "column_offset": validation.get("column_offset"),
            "miss_corrections": _miss_corrections(
                validation.get("miss_corrections")
            ),
            "achievement_calc": _selected_mapping(
                validation.get("achievement_calc"),
                ("observed", "minimum", "maximum", "consistent", "complete"),
            ),
            "calc_corrections": _selected_list(
                validation.get("calc_corrections"),
                CALC_CORRECTION_FIELDS,
            ),
            "uncertain_cells": _selected_list(
                validation.get("uncertain_cells"),
                UNCERTAIN_CELL_FIELDS,
            ),
        },
    }


COMBO_ICON_FILES = {
    "fc": "fc.png",
    "fcp": "fcplus.png",
    "ap": "ap.png",
    "app": "applus.png",
    "dummy": "fc_dummy.png",
}

FLEX_DIFFICULTY_STYLES = {
    key: {"bg": value["background"], "text": value["text"], "metric": value["metric"]}
    for key, value in DIFFICULTY_STYLES.items()
}
DEFAULT_DIFFICULTY_STYLE = {"bg": "#315B7D", "text": "#FFFFFF", "metric": "#315B7D"}


def flex_combo_status(judgement, achievement):
    status = _combo_status(achievement, judgement)
    if status is None:
        return "dummy" if all(isinstance(judgement.get(row), dict) for row in JUDGEMENT_ROWS) else None
    return status.replace("+", "p")


def flex_score_rank(achievement):
    rank = _score_rank(achievement)
    return rank.replace("+", "p") if rank else None


def difficulty_presentation(difficulty):
    key = str(difficulty or "").lower()
    return (
        FLEX_DIFFICULTY_STYLES.get(key, DEFAULT_DIFFICULTY_STYLE),
        DIFFICULTY_LABELS.get(key, str(difficulty or "").strip() or "-"),
    )


def format_loss_percentage(value, count=1):
    if not isinstance(value, (int, float)):
        return "-"
    loss = float(value) * nonnegative_count(count)
    return "0.0000%" if abs(loss) < 0.00005 else f"-{loss:.4f}%"


def build_fix_command(judgement, song_title, achievement):
    rows = []
    for row_name in JUDGEMENT_ROWS:
        row = judgement.get(row_name)
        row = row if isinstance(row, dict) else {}
        rows.append("/".join(
            str(nonnegative_count(row.get(field)))
            for field in ("critical_perfect", "perfect", "great", "good", "miss")
        ))
    title = re.sub(r"\s+", " ", song_title).strip() or '""'
    achievement_text = f"{achievement:.4f}%" if isinstance(achievement, (int, float)) else "0.0000%"
    return "\n".join((f"fix-rcd {title}", achievement_text, *rows))


def calc_status(validation, uncertain_cells, translate):
    calculation = validation.get("achievement_calc") or {}
    corrections = validation.get("calc_corrections") or []
    inferred = any(isinstance(item, dict) and item.get("inferred_row") for item in corrections)
    consistent = calculation.get("consistent")
    if consistent is None:
        return None, inferred

    if corrections:
        labels = {"critical_perfect": "CP", "perfect": "PF", "great": "GR", "good": "GD"}
        lines = []
        for correction in corrections:
            if correction.get("inferred_row"):
                continue
            row = str(correction.get("row") or "").upper()
            field = labels.get(correction.get("field"), str(correction.get("field") or "").upper())
            if correction.get("calc_completion"):
                amount = correction.get("amount", correction.get("added", 0))
                lines.append(f"{row} {field} {'+' if amount >= 0 else ''}{amount}")
            else:
                lines.append(
                    f"{row} {field} {correction.get('ocr')}→{correction.get('validated')} / "
                    f"MS {correction.get('miss_ocr')}→{correction.get('miss_validated')}"
                )
        text = translate("calc_inferred" if inferred else "calc_corrected")
        if lines:
            text += "\n" + "\n".join(lines)
    elif consistent and uncertain_cells:
        text = translate("calc_incomplete")
    elif consistent:
        text = translate("calc_validated")
    else:
        text = translate("calc_uncertain" if uncertain_cells else "calc_mismatch")
        values = (calculation.get("minimum"), calculation.get("maximum"), calculation.get("observed"))
        if all(isinstance(value, (int, float)) for value in values):
            text += f"\nCalc {values[0]:.4f}%-{values[1]:.4f}% / OCR {values[2]:.4f}%"
    return (text, consistent), inferred
