# common_utils.py <- Renamed from core.py
"""Core, general-purpose utilities and base classes."""

import datetime


# --- Timestamp Function ---
def get_utc_iso_timestamp() -> str:
    """Returns the current UTC time as an ISO 8601 string with Z suffix."""
    # Consistent with the temporary fix used in manage_tasks.py
    # Get current UTC time
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    # Format to ISO 8601 with millisecond precision and replace +00:00 with Z
    return now_utc.isoformat(timespec="milliseconds").replace("+00:00", "Z")


# ... (rest of file) ...
