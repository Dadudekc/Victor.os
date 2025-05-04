# common_utils.py <- Renamed from core.py
"""Core, general-purpose utilities and base classes."""

import datetime


# --- Timestamp Function ---
def get_utc_iso_timestamp() -> str:
    """Returns the current UTC time as an ISO 8601 string with Z suffix."""
    # Consistent with the temporary fix used in manage_tasks.py
    return (
        datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds")
        + "Z"
    )


# ... (rest of file) ...
