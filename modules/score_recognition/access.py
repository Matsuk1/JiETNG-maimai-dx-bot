"""Central entitlement boundary for AI score recognition.

Currently free for identified users. Set JIETNG_AI_REC_ALLOWED_USERS to a
comma-separated user-ID allowlist to restrict access (an empty value denies
everyone). Replace this policy with subscription/quota lookup for paid access.
User IDs must come from the verified event, never from command text.
"""
import os


def can_use_ai_recognition(user_id: str) -> bool:
    if not isinstance(user_id, str) or not user_id.strip():
        return False
    allowed = os.environ.get("JIETNG_AI_REC_ALLOWED_USERS")
    if allowed is None:
        return True
    return user_id in {value.strip() for value in allowed.split(",") if value.strip()}


def require_ai_recognition_access(user_id: str) -> None:
    if not can_use_ai_recognition(user_id):
        raise PermissionError("AI score recognition access denied")
