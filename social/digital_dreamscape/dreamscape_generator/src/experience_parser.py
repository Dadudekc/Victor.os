# Placeholder for ExperienceParser logic
# Responsibilities:
# - Take raw LLM response text
# - Extract the narrative part
# - Extract and validate the EXPERIENCE_UPDATE JSON block
# - Return (narrative, update_dict)

import logging
import re
import json
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)

class ExperienceParser:
    def __init__(self):
        logger.info("ExperienceParser initialized (stub).")

    def parse(self, llm_output: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        logger.warning("ExperienceParser.parse is using basic regex stub logic.")
        narrative = llm_output # Default to full output
        update_dict = None
        try:
            # Look for the block at the end, case-insensitive
            match = re.search(r"EXPERIENCE_UPDATE:\s*(\{.*?\})$", llm_output, re.DOTALL | re.IGNORECASE)
            if match:
                json_str = match.group(1).strip()
                narrative = llm_output[:match.start()].strip()
                # Simple cleanup of potential preceding heading
                narrative = re.sub(r'^Narrative:\s*', '', narrative, flags=re.IGNORECASE).strip()
                try:
                    update_dict = json.loads(json_str)
                    logger.info("Parsed EXPERIENCE_UPDATE block successfully.")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse EXPERIENCE_UPDATE JSON: {e}")
                    logger.debug(f"Invalid JSON string: {json_str}")
                    # Keep narrative, but update_dict remains None
            else:
                logger.warning("EXPERIENCE_UPDATE block not found in expected format.")
                # Narrative remains the full output if block isn't found
        except Exception as e:
            logger.error(f"Error during parsing LLM response: {e}", exc_info=True)
            # Return original output as narrative in case of error

        return narrative, update_dict

__all__ = ["ExperienceParser"] 