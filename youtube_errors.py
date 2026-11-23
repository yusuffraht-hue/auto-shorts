"""Safe, offline classification of YouTube OAuth failures.

Do not include tokens, raw credential payloads, or exception strings in logs.
"""
from google.auth.exceptions import RefreshError


def youtube_upload_error(exc):
    """Return a safe actionable message for known refresh failures, else None."""
    if not isinstance(exc, RefreshError):
        return None
    # Google RefreshError.args may contain a dict with sensitive details.
    # Only use the standardized error code, never print the exception.
    code = None
    for arg in exc.args:
        if isinstance(arg, dict):
            code = arg.get("error")
            break
    if code is None and exc.args and isinstance(exc.args[0], str):
        if exc.args[0].startswith("invalid_grant"):
            code = "invalid_grant"
    if code == "invalid_grant":
        return (
            "YouTube OAuth refresh was rejected (invalid_grant). "
            "The stored refresh token may be expired or revoked. "
            "No video was uploaded by this attempt. "
            "Reauthorization must be performed by the account owner; "
            "never print or commit tokens."
        )
    return "YouTube OAuth refresh failed; upload stopped. Check authorization privately."
