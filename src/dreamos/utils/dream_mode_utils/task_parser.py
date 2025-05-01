# dream_mode/utils/task_parser.py

import json
import logging
import re

logger = logging.getLogger("TaskParser")

# --- JSON Extraction Logic ---
JSON_BLOCK_PATTERN = re.compile(r"```json\s*({.*?})\s*```", re.DOTALL)
REQUIRED_JSON_KEYS = {"task_id", "feedback", "details", "raw_reply"}


def _extract_json_block(text: str) -> dict | None:
    match = JSON_BLOCK_PATTERN.search(text)
    if not match:
        return None

    json_str = match.group(1)
    try:
        data = json.loads(json_str)
        # Basic validation
        if isinstance(data, dict) and REQUIRED_JSON_KEYS.issubset(data.keys()):
            logger.info("✅ Successfully parsed JSON block from response.")
            return data
        else:
            logger.warning(
                f"⚠️ Found JSON block, but missing required keys: {REQUIRED_JSON_KEYS - set(data.keys())}"
            )
            return None
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ Found ```json block, but failed to parse: {e}")
        return None


# --- Regex Fallback Logic ---
TASK_ID_PATTERN_REGEX = re.compile(r"(?i)task\s*id[:\-\s]*([a-zA-Z0-9_\-]+)")
FEEDBACK_PATTERN_REGEX = re.compile(
    r"(?i)^\s*(APPROVED|REVISE|REJECTED)(?::\s*(.+))?", re.MULTILINE
)


def _extract_regex_fallback(text: str) -> dict:
    result = {}
    # Extract Task ID (if present)
    task_id_match = TASK_ID_PATTERN_REGEX.search(text)
    if task_id_match:
        result["task_id"] = task_id_match.group(1).strip()

    # Extract Feedback Type + Optional Details (now expects it at start of a line)
    feedback_match = FEEDBACK_PATTERN_REGEX.search(text)
    if feedback_match:
        result["feedback"] = feedback_match.group(1).strip().upper()
        result["details"] = (
            feedback_match.group(2).strip() if feedback_match.group(2) else ""
        )
        # Add raw reply from the original text if using regex
        result["raw_reply"] = text
        logger.info("✅ Parsed feedback via regex fallback.")
    else:
        logger.warning("⚠️ Could not extract feedback directive via regex fallback.")

    return result


# --- Main Parsing Function ---
def extract_task_metadata(text: str) -> dict:
    """
    Parses ChatGPT's response to extract task metadata.
    Prioritizes finding a valid JSON block like:
    ```json
    {
      "task_id": "...",
      "feedback": "APPROVED|REVISE|REJECTED",
      "details": "...",
      "raw_reply": "..."
    }
    ```
    If JSON parsing fails, falls back to regex parsing for:
        APPROVED
        REVISE: Use better variable names
        REJECTED: Not relevant
    And optionally a Task ID header.

    Returns a dictionary containing extracted data, or an empty dict if parsing fails.
    """
    if not text:
        return {}

    # 1. Try JSON extraction first
    json_data = _extract_json_block(text)
    if json_data:
        return json_data

    # 2. Fallback to Regex if JSON fails
    logger.warning("⚠️ JSON block not found or invalid, attempting regex fallback.")
    regex_data = _extract_regex_fallback(text)

    # Return regex data only if feedback was found
    if "feedback" in regex_data:
        # Ensure all keys expected by downstream exist, even if empty
        regex_data.setdefault("task_id", None)
        regex_data.setdefault("details", "")
        regex_data.setdefault("raw_reply", text)
        return regex_data

    # If neither worked, return empty
    logger.error("❌ Failed to parse metadata via JSON or Regex.")
    return {}
