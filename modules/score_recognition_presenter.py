"""Presentation values derived from score-recognition results."""

import re
from modules.score_rules import (JUDGEMENT_ROWS, DIFFICULTY_LABELS, DIFFICULTY_STYLES as SHARED_DIFFICULTY_STYLES, score_rank as canonical_rank, combo_status as canonical_combo, nonnegative_count)



COMBO_ICON_FILES = {
    "fc": "fc.png",
    "fcp": "fcplus.png",
    "ap": "ap.png",
    "app": "applus.png",
    "dummy": "fc_dummy.png",
}

DIFFICULTY_STYLES = {key: {"bg": value["background"], "text": value["text"], "metric": value["metric"]} for key, value in SHARED_DIFFICULTY_STYLES.items()}
DEFAULT_DIFFICULTY_STYLE = {"bg": "#315B7D", "text": "#FFFFFF", "metric": "#315B7D"}






def combo_status(judgement, achievement):
    status = canonical_combo(achievement, judgement)
    if status is None:
        return "dummy" if all(isinstance(judgement.get(row), dict) for row in JUDGEMENT_ROWS) else None
    return status.replace("+", "p")


def score_rank(achievement):
    rank = canonical_rank(achievement)
    return rank.replace("+", "p") if rank else None


def difficulty_presentation(difficulty):
    key = str(difficulty or "").lower()
    return (
        DIFFICULTY_STYLES.get(key, DEFAULT_DIFFICULTY_STYLE),
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
