"""Canonical score rules shared by API, image and Flex presentation."""
from typing import Any

JUDGEMENT_ROWS = ("tap", "hold", "slide", "touch", "break")

DIFFICULTY_LABELS = {
    "basic": "BASIC",
    "advanced": "ADVANCED",
    "expert": "EXPERT",
    "master": "MASTER",
    "remaster": "Re:MASTER",
    "utage": "U·TA·GE",
}

DIFFICULTY_STYLES = {
    "basic": {"background": "#75B520", "text": "#FFFFFF", "metric": "#75B520"},
    "advanced": {"background": "#EFA508", "text": "#111111", "metric": "#B36F00"},
    "expert": {"background": "#CC4D59", "text": "#FFFFFF", "metric": "#CC4D59"},
    "master": {"background": "#9F51DC", "text": "#FFFFFF", "metric": "#8E44AD"},
    "remaster": {"background": "#E9D4F3", "text": "#72148D", "metric": "#B06FD3"},
    "utage": {"background": "#F52EDD", "text": "#FFFFFF", "metric": "#D10FBA"},
}

def nonnegative_count(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0

def score_rank(achievement: Any) -> str | None:
    if not isinstance(achievement, (int, float)):
        return None
    thresholds = (
        (100.5, "sss+"),
        (100.0, "sss"),
        (99.5, "ss+"),
        (99.0, "ss"),
        (98.0, "s+"),
        (97.0, "s"),
        (94.0, "aaa"),
        (90.0, "aa"),
        (80.0, "a"),
        (75.0, "bbb"),
        (70.0, "bb"),
        (60.0, "b"),
        (50.0, "c"),
        (0.0, "d"),
    )
    for threshold, rank in thresholds:
        if achievement >= threshold:
            return rank
    return "d"

def combo_status(achievement: Any, judgements: dict[str, dict[str, int]]) -> str | None:
    if any(not isinstance(judgements.get(row_name), dict) for row_name in JUDGEMENT_ROWS):
        return None
    totals = {"great": 0, "good": 0, "miss": 0}
    for row_name in JUDGEMENT_ROWS:
        row = judgements[row_name]
        for field_name in totals:
            totals[field_name] += nonnegative_count(row.get(field_name))
    rules = (
        ("ap+", isinstance(achievement, (int, float)) and achievement >= 100.99995),
        ("ap", totals["great"] == 0 and totals["good"] == 0 and totals["miss"] == 0),
        ("fc+", totals["good"] == 0 and totals["miss"] == 0),
        ("fc", totals["miss"] == 0),
    )
    return next((status for status, matched in rules if matched), None)
