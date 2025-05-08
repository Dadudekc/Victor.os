"""File I/O utilities, including safe JSONL appending."""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def read_json_file(
    file_path: Path, description: Optional[str] = None
) -> Union[Dict[str, Any], List[Any], None]:
    """Reads and parses a JSON file.

    Args:
        file_path: Path object for the target .json file.
        description: Optional description for logging.

    Returns:
        Parsed JSON data (dict or list), or None if an error occurs.
    """
    if description:
        logger.info(f"Reading {description} from {file_path}...")
    else:
        logger.debug(f"Reading JSON file: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        logger.warning(f"JSON file not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading JSON file {file_path}: {e}", exc_info=True)
        return None


def write_json_atomic(
    file_path: Path,
    data: Union[Dict[str, Any], List[Any]],
    indent: Optional[int] = None,
):
    """Writes data to a JSON file atomically using a temporary file.

    Args:
        file_path: Path object for the target .json file.
        data: The dictionary or list to write.
        indent: Indentation level for pretty-printing. None for compact.
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # Use a temporary file in the same directory to ensure atomic move
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=file_path.parent,
            suffix=".tmp",
        ) as tmp_file:
            json.dump(data, tmp_file, ensure_ascii=False, indent=indent)
            temp_file_path = tmp_file.name
        os.replace(temp_file_path, file_path)  # Atomic replace
        logger.debug(f"Successfully wrote JSON data atomically to {file_path}")
        return True
    except Exception as e:
        logger.error(
            f"Error writing JSON atomically to {file_path}: {e}", exc_info=True
        )
        # Clean up temporary file if it still exists
        if "temp_file_path" in locals() and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e_remove:
                logger.error(
                    f"Error removing temporary file {temp_file_path}: {e_remove}"
                )
        return False


def read_jsonl_file(file_path: Path) -> List[Dict[str, Any]]:
    """Reads all lines from a JSONL file.

    Skips lines that are not valid JSON.

    Args:
        file_path: Path object for the target .jsonl file.

    Returns:
        A list of dictionaries, or an empty list if an error occurs or file not found.
    """
    records = []
    if not file_path.exists():
        logger.warning(f"JSONL file not found: {file_path}")
        return records
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    records.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    logger.warning(
                        f"Skipping invalid JSON line in {file_path}: {line.strip()}"
                    )
        return records
    except Exception as e:
        logger.error(f"Error reading JSONL file {file_path}: {e}", exc_info=True)
        return []


def append_jsonl(file_path: Path, data_dict: Dict[str, Any]):
    """Safely appends a dictionary as a JSON line to a file.

    Ensures the directory exists and handles potential file/JSON errors.

    Args:
        file_path: Path object for the target .jsonl file.
        data_dict: The dictionary to append.
    """
    try:
        # Ensure the directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize data to JSON string (use separators for more compact output, common for JSONL)
        json_string = json.dumps(data_dict, ensure_ascii=False, separators=(",", ":"))

        # Append to file with a newline
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(
                json_string + os.linesep
            )  # Use os.linesep for platform compatibility

        logger.debug(f"Successfully appended data to {file_path}")
        return True

    except TypeError as e:
        logger.error(f"Data dictionary is not JSON serializable for {file_path}: {e}")
        return False
    except IOError as e:
        logger.error(f"Error writing to file {file_path}: {e}")
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error during append_jsonl for {file_path}: {e}", exc_info=True
        )
        return False


def read_text_file(file_path: Path) -> Optional[str]:
    """Reads content from a text file.

    Args:
        file_path: Path object for the target text file.

    Returns:
        The file content as a string, or None if an error occurs.
    """
    try:
        if not file_path.is_file():
            logger.warning(f"Text file not found or is not a file: {file_path}")
            return None
        content = file_path.read_text(encoding="utf-8")
        logger.debug(f"Successfully read text file: {file_path}")
        return content
    except Exception as e:
        logger.error(f"Error reading text file {file_path}: {e}", exc_info=True)
        return None


def write_text_file_atomic(file_path: Path, content: str):
    """Writes text content to a file atomically using a temporary file.

    Args:
        file_path: Path object for the target text file.
        content: The string content to write.
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=file_path.parent,
            suffix=".tmp",
        ) as tmp_file:
            tmp_file.write(content)
            temp_file_path = tmp_file.name
        os.replace(temp_file_path, file_path)  # Atomic replace
        logger.debug(f"Successfully wrote text content atomically to {file_path}")
        return True
    except Exception as e:
        logger.error(
            f"Error writing text file atomically {file_path}: {e}", exc_info=True
        )
        if "temp_file_path" in locals() and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e_remove:
                logger.error(
                    f"Error removing temporary file {temp_file_path}: {e_remove}"
                )
        return False


# Constants for safe_read_with_tool
WARMUP_READ_END_LINE = 200  # Min lines for a chunked read as per tool spec
FALLBACK_READ_END_LINE = 250  # Max lines for a chunked read as per tool spec


def _extract_content_from_tool_response(
    response: Dict[str, Any], file_path: str
) -> Optional[str]:
    # Ensure logger is defined at module level as: logger = logging.getLogger(__name__)
    if not response:
        logger.warning(f"No response from read_file tool for {file_path}.")
        return None
    try:
        read_response_data = response.get("read_file_response", {})
        content_list = read_response_data.get("results")

        if content_list and isinstance(content_list, list) and len(content_list) > 0:
            first_item = content_list[0]
            if isinstance(first_item, str):
                # Check if the content itself is an error message from the tool
                if first_item.startswith("Error calling tool:"):
                    logger.warning(
                        f"read_file tool reported an error for {file_path}: {first_item}"
                    )
                    return None
                return first_item  # Actual content
            elif first_item is None:
                logger.warning(
                    f"read_file tool returned None as content for {file_path}."
                )
                return None
            else:  # Unexpected type
                logger.warning(
                    f"read_file tool returned unexpected content type for {file_path}: {type(first_item)}. Full response: {response}"
                )
                return None
        elif (
            "error" in read_response_data
        ):  # Check for a top-level error key in read_file_response
            logger.warning(
                f"read_file tool response indicates an error for {file_path}: {read_response_data['error']}. Full response: {response}"
            )
            return None
        else:
            # This case handles if "results" is missing, empty, or not a list as expected
            logger.warning(
                f"Content not found or in unexpected format in read_file response for {file_path}. Response: {response}"
            )
            return None
    except Exception as e:
        logger.error(
            f"Error parsing read_file response dictionary for {file_path}: {e}. Response: {response}",
            exc_info=True,
        )
        return None


def safe_read_with_tool(
    target_file: str, read_full_file_if_possible: bool = False
) -> Optional[str]:
    # Ensure logger is defined at module level
    # Assumes default_api.read_file is available in the calling agent's scope.
    content: Optional[str] = None
    explanation_prefix = f"Safely reading {target_file}:"

    try:
        # 1. Warm-up chunked read
        # Its primary purpose is to make the file "not stale" for subsequent full reads
        # and to log any immediate errors during this first interaction.
        logger.debug(
            f"{explanation_prefix} Performing warm-up read (lines 1-{WARMUP_READ_END_LINE})."
        )
        warmup_response = default_api.read_file(
            target_file=target_file,
            start_line_one_indexed=1,
            end_line_one_indexed_inclusive=WARMUP_READ_END_LINE,
            should_read_entire_file=False,
            explanation=f"{explanation_prefix} Warm-up chunked read.",
        )
        # Call _extract_content_from_tool_response to log any issues found during warm-up.
        # The actual content from warm-up isn't typically used if a full or fallback read is planned.
        _extract_content_from_tool_response(warmup_response, target_file)

        # 2. Attempt full read if requested
        if read_full_file_if_possible:
            logger.debug(f"{explanation_prefix} Attempting full read after warm-up.")
            try:
                full_read_response = default_api.read_file(
                    target_file=target_file,
                    should_read_entire_file=True,
                    start_line_one_indexed=1,  # Required by API, but ignored if should_read_entire_file=True
                    end_line_one_indexed_inclusive=1,  # Required by API, but ignored
                    explanation=f"{explanation_prefix} Attempting full read.",
                )
                content = _extract_content_from_tool_response(
                    full_read_response, target_file
                )
                if content:
                    logger.info(f"{explanation_prefix} Successfully read entire file.")
                    return content
                else:
                    # Logged by _extract_content_from_tool_response if no content or error in response
                    logger.warning(
                        f"{explanation_prefix} Full read did not yield usable content. Proceeding to fallback chunk."
                    )
            except Exception as e:  # Catches exceptions from the tool call itself
                logger.error(
                    f"{explanation_prefix} Exception during full read attempt for {target_file}: {e}",
                    exc_info=True,
                )
                # Fall through to chunked fallback if full read tool call itself fails

        # 3. Fallback to a defined chunk if full read not attempted or failed to return content
        if not content:
            logger.debug(
                f"{explanation_prefix} Attempting fallback chunked read (lines 1-{FALLBACK_READ_END_LINE})."
            )
            try:
                fallback_response = default_api.read_file(
                    target_file=target_file,
                    start_line_one_indexed=1,
                    end_line_one_indexed_inclusive=FALLBACK_READ_END_LINE,
                    should_read_entire_file=False,
                    explanation=f"{explanation_prefix} Fallback chunked read.",
                )
                content = _extract_content_from_tool_response(
                    fallback_response, target_file
                )
                if content:
                    logger.info(
                        f"{explanation_prefix} Successfully read fallback chunk."
                    )
                    return content
                else:
                    # Logged by _extract_content_from_tool_response
                    logger.warning(
                        f"{explanation_prefix} Fallback chunk read also yielded no usable content."
                    )
                    return None
            except Exception as e:  # Catches exceptions from the tool call itself
                logger.error(
                    f"{explanation_prefix} Exception during fallback chunked read for {target_file}: {e}",
                    exc_info=True,
                )
                return None

        return content  # This will be None if full read was requested but failed, and fallback also failed.
    # Or if full read was not requested and fallback failed.

    except Exception as e:  # Catch-all for unexpected issues in this function's outer logic (e.g., variable name errors)
        logger.error(
            f"{explanation_prefix} Unexpected fatal error in safe_read_with_tool function logic for {target_file}: {e}",
            exc_info=True,
        )
        return None
