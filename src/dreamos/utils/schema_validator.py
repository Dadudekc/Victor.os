import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

# Attempt to import jsonschema
try:
    import jsonschema

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    jsonschema = None
    JSONSCHEMA_AVAILABLE = False

logger = logging.getLogger(__name__)

# Determine paths relative to this file's location
# Assumes src/dreamos/utils/schema_validator.py
UTILS_DIR = Path(__file__).resolve().parent
SCHEMAS_DIR = UTILS_DIR.parent / "schemas"

# Cache loaded schemas to avoid repeated file I/O
_schema_cache: Dict[str, Dict[str, Any]] = {}


def load_schema(schema_name: str) -> Optional[Dict[str, Any]]:
    """Loads a JSON schema from the schemas directory, using a cache."""
    if schema_name in _schema_cache:
        return _schema_cache[schema_name]

    schema_filename = f"{schema_name}.schema.json"
    schema_path = SCHEMAS_DIR / schema_filename

    if not schema_path.exists():
        logger.error(f"Schema file not found: {schema_path}")
        return None

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
            _schema_cache[schema_name] = schema  # Cache the loaded schema
            logger.debug(f"Successfully loaded and cached schema: {schema_filename}")
            return schema
    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to decode JSON from schema file {schema_path}: {e}", exc_info=True
        )
        return None
    except IOError as e:
        logger.error(f"IO error loading schema file {schema_path}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error loading schema {schema_path}: {e}", exc_info=True
        )
        return None


def validate_payload(payload: Dict[str, Any], schema_name: str) -> bool:
    """
    Validates a dictionary payload against a named JSON schema.

    Args:
        payload: The dictionary data to validate.
        schema_name: The name of the schema file (without .schema.json extension)
                     located in the src/dreamos/schemas/ directory.

    Returns:
        True if the payload is valid against the schema, False otherwise.
    """
    if not JSONSCHEMA_AVAILABLE:
        logger.warning(
            "jsonschema library not installed. Cannot perform schema validation. Returning True."
        )
        # Decide on behavior: fail open (True) or closed (False)? Open seems less disruptive for now.
        return True

    schema = load_schema(schema_name)
    if schema is None:
        logger.error(f"Schema '{schema_name}' could not be loaded. Validation failed.")
        return False

    try:
        jsonschema.validate(instance=payload, schema=schema)
        logger.debug(f"Payload successfully validated against schema: {schema_name}")
        return True
    except jsonschema.exceptions.ValidationError as e:
        logger.warning(f"Schema validation failed for '{schema_name}': {e.message}")
        # Log relevant part of payload for easier debugging?
        # logger.debug(f"Invalid payload snippet: {str(payload)[:200]}...")
        return False
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during schema validation for '{schema_name}': {e}",
            exc_info=True,
        )
        return False

    # Example Usage (if run directly)
    # if __name__ == "__main__":
    #     # ... (schema definition) ...
    #     # EDIT START: Remove commented-out print examples
    #     # print(f"Validating good payload: {validate_payload(test_payload_valid, 'scraped_response')}") # Should be True
    #     # print(f"Validating bad author: {validate_payload(test_payload_invalid_author, 'scraped_response')}") # Should be False
    #     # print(f"Validating missing content: {validate_payload(test_payload_missing_content, 'scraped_response')}") # Should be False
    #     # print(f"Validating non-existent schema: {validate_payload({}, 'non_existent')}") # Should be False
    #     # EDIT END
    pass  # Keep pass if the block becomes empty
