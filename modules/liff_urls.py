"""Build account-action URLs while preserving the legacy web entry points."""

from urllib.parse import urlencode


def build_account_action_url(
    domain: str,
    action: str,
    path: str,
    params: dict,
    *,
    liff_enabled: bool = False,
    liff_id: str = "",
) -> str:
    """Return a LIFF URL when configured, otherwise the existing HTTPS URL."""
    clean_domain = str(domain or "").strip().strip("/")
    clean_path = str(path or "").strip().lstrip("/")
    query = urlencode(params)
    suffix = f"/{clean_path}"
    if query:
        suffix = f"{suffix}?{query}"

    clean_liff_id = str(liff_id or "").strip().strip("/")
    if liff_enabled and clean_liff_id:
        liff_query = urlencode({"action": action, **params})
        return f"https://liff.line.me/{clean_liff_id}/?{liff_query}"
    return f"https://{clean_domain}/linebot{suffix}"
