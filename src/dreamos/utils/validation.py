"""General data validation utilities (potentially deprecated).

This module likely contained general validation functions. Much of this
functionality might now exist in schema_validator.py or specific modules.
"""

import logging

logger = logging.getLogger(__name__)

# TODO: Review if this module is needed. Consolidate specific validation
# logic into relevant modules (e.g., schema_validator.py, task validation
# within PBM, etc.) and remove this file if possible.


def is_valid_uuid(uuid_string: str) -> bool:
    """Placeholder for UUID validation."""
    # Example basic check (replace with actual logic if needed)
    import uuid

    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False


def validate_task_data(data: dict) -> bool:
    """Placeholder for generic task data validation."""
    # Deprecated: Use schema validation in PBM or specific task logic
    logger.warning("Call to deprecated validate_task_data. Use schema validation.")
    return isinstance(data, dict) and "task_id" in data  # Example minimal check


if __name__ == "__main__":
    print("validation.py - Deprecated generic validation utilities.")
    print(f"Is UUID valid? {is_valid_uuid('invalid-uuid')}")
    print(f"Is Task Data valid? {validate_task_data({})}")
