"""Pure result types and candidate expansion, independent of model startup."""

def expand_score_recognition_calc_variants(result, max_results=5):
    validation = (result or {}).get("validation") or {}
    candidates = validation.get("calc_completion_candidates") or []
    if not candidates:
        return [result]

    variants = []
    total_count = len(candidates)
    for index, candidate in enumerate(candidates[:max_results], start=1):
        variant = dict(result)
        parsed = dict((result.get("parsed") or {}))
        variant_validation = dict(validation)
        parsed["sub_judgement"] = {
            row_name: dict(row)
            for row_name, row in (candidate.get("judgement") or {}).items()
            if isinstance(row, dict)
        }
        score_range = candidate.get("score_range")
        variant_validation["unmatched_notes"] = {}
        variant_validation["calc_completion_applied"] = True
        variant_validation["calc_completion_candidate_index"] = index
        variant_validation["calc_completion_candidate_count"] = total_count
        variant_validation["calc_completion_candidates"] = []
        variant_validation["uncertain_cells"] = []
        variant_validation["break_detail"] = candidate.get("break_detail") or {}
        variant_validation["calc_corrections"] = [
            *(validation.get("calc_corrections") or []),
            *(candidate.get("corrections") or []),
        ]
        achievement_calc = dict(validation.get("achievement_calc") or {})
        achievement_calc["minimum"] = (
            score_range.get("minimum")
            if score_range else achievement_calc.get("minimum")
        )
        achievement_calc["maximum"] = (
            score_range.get("maximum")
            if score_range else achievement_calc.get("maximum")
        )
        achievement_calc["consistent"] = True
        achievement_calc["complete"] = True
        variant_validation["achievement_calc"] = achievement_calc
        variant["parsed"] = parsed
        variant["validation"] = variant_validation
        variants.append(variant)
    return variants

class InvalidScoreImageError(ValueError):
    """The uploaded data is not a supported, safely sized score image."""

class UnsupportedScoreImageError(InvalidScoreImageError):
    """The uploaded image format is not supported by the OCR API."""
