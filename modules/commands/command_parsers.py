from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional


_BPM_RANGE_PATTERN = re.compile(
    r"^(\d+(?:\.\d+)?)\s*[-~〜]\s*(\d+(?:\.\d+)?)(?:\s+(\d+))?$"
)


@dataclass(frozen=True, slots=True)
class BpmQuery:
    minimum: float
    maximum: Optional[float] = None
    page: int = 1


FilterMode = Literal["uncleared", "unplayed", "cleared"]
FILTER_MODES: dict[str, FilterMode] = {
    "uc": "uncleared",
    "up": "unplayed",
    "c": "cleared",
}
NOTE_NAMES = ("tap", "hold", "slide", "touch", "break")
PROGRESS_RANK_PATTERN = r"(sss\+|ss\+|s\+|ap\+|fc\+|fdx\+|sss|ss|ap|fc|fdx|s)"
PROGRESS_CATEGORY_ALIASES = {
    "vocaloid": "niconico＆ボーカロイド", "popani": "POPS＆アニメ",
    "touhou": "東方Project", "gekichu": "オンゲキ＆CHUNITHM",
    "game": "ゲーム＆バラエティ", "maimai": "maimai",
}


def parse_paginated_keyword(text: str) -> tuple[str, int]:
    """Parse `<command> <keyword> [page]` after routing matched the command."""
    parts = text.split()
    if len(parts) >= 3 and parts[-1].isdigit():
        return " ".join(parts[1:-1]), int(parts[-1])
    return " ".join(parts[1:]), 1


def parse_bpm_query(text: str) -> Optional[BpmQuery]:
    """Parse exact BPM, range, and optional page forms used by the BPM command."""
    raw = re.sub(r"^bpm\s+", "", text, flags=re.IGNORECASE).strip()
    tokens = raw.split()
    minimum = None
    maximum = None
    page = 1

    range_match = _BPM_RANGE_PATTERN.fullmatch(raw)
    if range_match:
        minimum = parse_bpm_number(range_match.group(1))
        maximum = parse_bpm_number(range_match.group(2))
        if range_match.group(3):
            page = int(range_match.group(3))
    elif len(tokens) == 1:
        minimum = parse_bpm_number(tokens[0])
    elif len(tokens) == 2:
        first = parse_bpm_number(tokens[0])
        second = parse_bpm_number(tokens[1])
        if first is not None and second is not None and second > first:
            minimum, maximum = first, second
        elif first is not None and tokens[1].isdigit():
            minimum = first
            page = int(tokens[1])
    elif len(tokens) == 3 and tokens[2].isdigit():
        minimum = parse_bpm_number(tokens[0])
        maximum = parse_bpm_number(tokens[1])
        page = int(tokens[2])

    if (
        minimum is None
        or page < 1
        or (maximum is not None and maximum < minimum)
    ):
        return None
    return BpmQuery(minimum, maximum, page)


def parse_plate_query(text: str) -> tuple[str, Optional[FilterMode]]:
    filter_mode = parse_filter_mode(text)
    body = re.sub(r"\s*-(uc|up|c)\s*$", "", text, flags=re.IGNORECASE)
    title = re.sub(
        r"\s+plate$",
        "",
        body,
        flags=re.IGNORECASE,
    ).strip()
    return title, filter_mode


def parse_filter_mode(text: str) -> Optional[FilterMode]:
    match = re.search(r"-(uc|up|c)\s*$", text, flags=re.IGNORECASE)
    return FILTER_MODES.get(match.group(1).lower()) if match else None


def parse_level_records_query(text: str) -> tuple[str, int]:
    level = re.sub(
        r"\s+records[ 　]*\d*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    page_match = re.search(r"(\d+)\s*$", text)
    page = int(page_match.group(1)) if page_match else 1
    return level, page


def parse_note_counts(text: str) -> Optional[dict[str, int]]:
    body = re.sub(r"^calc\s+", "", text, count=1, flags=re.IGNORECASE)
    try:
        counts = [int(value) for value in body.split()]
    except ValueError:
        return None
    if len(counts) == 4:
        counts.insert(3, 0)
    if len(counts) != len(NOTE_NAMES) or any(value < 0 for value in counts):
        return None
    return dict(zip(NOTE_NAMES, counts))


def parse_bpm_number(value: object) -> Optional[float]:
    try:
        bpm = float(value)
    except (TypeError, ValueError):
        return None
    return bpm if bpm >= 0 else None


def format_bpm_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def resolve_progress_category(target):
    return PROGRESS_CATEGORY_ALIASES.get(str(target or "").strip().lower())


def parse_level_rank_progress(text):
    body = re.sub(r"\s+", " ", text.strip().lower())
    body = re.sub(r"\s*-(uc|up|c)\s*$", "", body).strip()
    body = re.sub(r"\s*prog\s*$", "", body).strip()
    match = re.search(fr"{PROGRESS_RANK_PATTERN}\s*$", body)
    return (body[:match.start()].strip(), match.group(1)) if match else (None, None)


def parse_fix_record_command(command_text):
    lines = [line.strip() for line in str(command_text or "").splitlines() if line.strip()]
    if not lines or lines[0].lower() == "fix-rcd-help":
        return None
    title_match = re.fullmatch(r"fix-rcd\s+(.+)", lines[0], re.IGNORECASE)
    if not title_match:
        return None
    if len(lines) != 7:
        raise ValueError("fix-rcd requires a title, achievement, and five judgement rows")

    title = re.sub(r"\s+\[(?:DX|STD)\]\s*$", "", title_match.group(1), flags=re.IGNORECASE).strip()
    if title in {'""', "''"}:
        title = ""

    achievement_match = re.fullmatch(r"(\d{1,3}(?:[.,]\d{1,4})?)%?", lines[1])
    if not achievement_match:
        raise ValueError("achievement must be a percentage between 0 and 101")
    achievement = float(achievement_match.group(1).replace(",", "."))
    if not 0 <= achievement <= 101:
        raise ValueError("achievement must be a percentage between 0 and 101")

    field_names = ("critical_perfect", "perfect", "great", "good", "miss")
    judgement = {}
    for row_name, line in zip(NOTE_NAMES, lines[2:]):
        row_match = re.fullmatch(r"(\d{1,4})/(\d{1,4})/(\d{1,4})/(\d{1,4})/(\d{1,4})", line)
        if not row_match:
            raise ValueError("each judgement row must contain five slash-separated integers")
        judgement[row_name] = {
            field_name: int(value)
            for field_name, value in zip(field_names, row_match.groups())
        }
    return title, achievement, judgement
