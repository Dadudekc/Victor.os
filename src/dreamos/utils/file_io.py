"""File I/O utilities, including safe JSONL appending."""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Union, Optional

logger = logging.getLogger(__name__)


def read_json_file(file_path: Path, description: Optional[str] = None) -> Union[Dict[str, Any], List[Any], None]:
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


def write_json_atomic(file_path: Path, data: Union[Dict[str, Any], List[Any]], indent: Optional[int] = None):
    """Writes data to a JSON file atomically using a temporary file.

    Args:
        file_path: Path object for the target .json file.
        data: The dictionary or list to write.
        indent: Indentation level for pretty-printing. None for compact.
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # Use a temporary file in the same directory to ensure atomic move
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, dir=file_path.parent, suffix='.tmp') as tmp_file:
            json.dump(data, tmp_file, ensure_ascii=False, indent=indent)
            temp_file_path = tmp_file.name
        os.replace(temp_file_path, file_path) # Atomic replace
        logger.debug(f"Successfully wrote JSON data atomically to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error writing JSON atomically to {file_path}: {e}", exc_info=True)
        # Clean up temporary file if it still exists
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e_remove:
                logger.error(f"Error removing temporary file {temp_file_path}: {e_remove}")
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
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    records.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    logger.warning(f"Skipping invalid JSON line in {file_path}: {line.strip()}")
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
        json_string = json.dumps(data_dict, ensure_ascii=False, separators=(',', ':'))

        # Append to file with a newline
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json_string + os.linesep) # Use os.linesep for platform compatibility

        logger.debug(f"Successfully appended data to {file_path}")
        return True

    except TypeError as e:
        logger.error(f"Data dictionary is not JSON serializable for {file_path}: {e}")
        return False
    except IOError as e:
        logger.error(f"Error writing to file {file_path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during append_jsonl for {file_path}: {e}", exc_info=True)
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
        content = file_path.read_text(encoding='utf-8')
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
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, dir=file_path.parent, suffix='.tmp') as tmp_file:
            tmp_file.write(content)
            temp_file_path = tmp_file.name
        os.replace(temp_file_path, file_path) # Atomic replace
        logger.debug(f"Successfully wrote text content atomically to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error writing text file atomically {file_path}: {e}", exc_info=True)
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e_remove:
                logger.error(f"Error removing temporary file {temp_file_path}: {e_remove}")
        return False
