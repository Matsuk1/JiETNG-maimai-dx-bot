"""Special command permissions, enforced by command dispatch before execution.

Keys are canonical command names (Command.name for table-driven commands).
Commands absent from this registry remain public. During the free rollout,
registered commands allow identified users unless their allowlist is configured.
Replace can_use_command's policy with entitlement lookup when adding paid access.
"""
import os


COMMAND_ACCESS_POLICIES = {
    "ai-rec": "JIETNG_AI_REC_ALLOWED_USERS",
}


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
    """Use the sender's trusted event identity, never a queried/mentioned user."""
    if not can_use_command(user_id, command_name):
        raise PermissionError(f"Command access denied: {command_name}")
