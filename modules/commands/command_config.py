"""Shared command metadata and result limits."""

import os

MAX_SEARCH_RESULTS = 10
API_MAX_SEARCH_RESULTS = 50

RANK_COMMANDS = {
    ("b50", "best50"): "best50",
    ("b40", "best40"): "best40",
    ("b35", "best35"): "best35",
    ("b15", "best15"): "best15",
    ("ab35", "allb35"): "allb35",
    ("ab50", "allb50"): "allb50",
    ("apb50", "ap50"): "apb50",
    ("fdxb50", "fdx50"): "fdxb50",
    ("rct50", "r50"): "rct50",
    ("idealb50", "idlb50"): "idlb50",
    ("s50", "sun50", "寸止め", "寸50"): "sun50",
    ("unknown",): "unknown",
}
COMMAND_ACCESS_POLICIES = {"ai-rec": "JIETNG_AI_REC_ALLOWED_USERS"}


def rank_command_words(*, hidden=()):
    """Return every rank-command alias except explicitly hidden words."""
    hidden = set(hidden)
    return tuple(sorted(alias for aliases in RANK_COMMANDS for alias in aliases if alias not in hidden))


def can_use_command(user_id: str, command_name: str) -> bool:
    allowlist_env = COMMAND_ACCESS_POLICIES.get(command_name)
    if allowlist_env is None:
        return True
    if not isinstance(user_id, str) or not user_id.strip():
        return False
    allowed = os.environ.get(allowlist_env)
    if allowed is None:
        return True
    return user_id in {value.strip() for value in allowed.split(",") if value.strip()}


def require_command_access(user_id: str, command_name: str) -> None:
    if not can_use_command(user_id, command_name):
        raise PermissionError(f"Command access denied: {command_name}")
