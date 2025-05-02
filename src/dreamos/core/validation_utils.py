"""Core data validation utilities."""

# NOTE (Captain-Agent-5): These utilities provide basic manual validation.
# Consider reviewing their usage in relation to Pydantic models, which offer
# more comprehensive, declarative validation based on type hints and validators.
# These might be most useful for validating raw data before Pydantic parsing.

import logging
from typing import Any, Dict, List, Type

from .errors import ValidationError as CoreValidationError

logger = logging.getLogger(__name__)


def validate_required_fields(
    data: Dict[str, Any], fields: List[str], context: str = "Data"
) -> None:
    """Ensures required fields are present in a dictionary.

    Args:
        data: The dictionary to validate.
        fields: A list of keys that must be present.
        context: A descriptive string for the error message (e.g., 'Task data').

    Raises:
        CoreValidationError: If any required fields are missing.
    """
    missing = [f for f in fields if f not in data]
    if missing:
        raise CoreValidationError(f"{context} missing required fields: {missing}")
    logger.debug(f"{context} passed required fields check: {fields}")


def validate_field_type(
    value: Any, expected_type: Type, field_name: str, context: str = "Data"
) -> None:
    """Ensures a field's value matches the expected type.

    Args:
        value: The value to check.
        expected_type: The expected type (e.g., str, int, list).
        field_name: The name of the field being checked.
        context: A descriptive string for the error message.

    Raises:
        CoreValidationError: If the value's type does not match.
    """
    if not isinstance(value, expected_type):
        raise CoreValidationError(
            f"{context} field '{field_name}' expected type {expected_type.__name__}, got {type(value).__name__}"
        )
    logger.debug(
        f"{context} field '{field_name}' passed type check ({expected_type.__name__})."
    )


def validate_payload(
    payload: Dict[str, Any],
    required_fields: List[str],
    type_map: Dict[str, Type],
    context: str = "Payload",
) -> None:
    """Performs required field and type checks on a payload dictionary."""
    validate_required_fields(payload, required_fields, context=context)
    for field, expected_type in type_map.items():
        if field in payload:  # Only validate types for fields that are present
            validate_field_type(payload[field], expected_type, field, context=context)
    logger.info(f"{context} passed validation.")
