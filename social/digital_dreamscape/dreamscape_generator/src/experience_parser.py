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

# import config as project_config # For logging level
from dreamscape_generator import config as project_config # Corrected import

logger = logging.getLogger(__name__)
logger.setLevel(project_config.LOG_LEVEL)

class ExperienceParser:
    """Parses LLM responses to extract narrative and structured experience updates."""
    def __init__(self):
        logger.info("ExperienceParser initialized.")
        # Regex to find the EXPERIENCE_UPDATE block, potentially wrapped in ```json
        # Looks for the heading, optional whitespace, optional ```json, the JSON object, optional ```
        # Assumes the block is the last major element.
        self.update_block_regex = re.compile(
            r"EXPERIENCE_UPDATE:?\s*(?:```json)?\s*(\{.*?\})\s*(?:```)?\s*$",
            re.DOTALL | re.IGNORECASE
        )

    def parse(self, llm_output: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Parses the LLM output string.

        Args:
            llm_output: The raw string response from the LLM.

        Returns:
            A tuple containing:
                - narrative (str): The extracted narrative text.
                - update_dict (Optional[Dict[str, Any]]): The parsed JSON update block, or None if not found/invalid.
        """
        if not isinstance(llm_output, str):
            logger.error("ExperienceParser received non-string input.")
            return "", None # Return empty narrative and no update

        logger.debug("Parsing LLM response...")
        narrative = llm_output # Default to full output initially
        update_dict = None
        json_str = ""

        try:
            match = self.update_block_regex.search(llm_output.strip())
            if match:
                json_str = match.group(1).strip()
                # Extract narrative as text before the matched block
                narrative = llm_output[:match.start()].strip()
                # Simple cleanup of potential preceding heading
                narrative = re.sub(r'^Narrative:\s*', '', narrative, flags=re.IGNORECASE).strip()
                logger.debug(f"Found potential EXPERIENCE_UPDATE JSON block: {json_str[:100]}...")
                try:
                    update_dict = json.loads(json_str)
                    # Basic validation: ensure it's a dictionary
                    if isinstance(update_dict, dict):
                        logger.info("Parsed EXPERIENCE_UPDATE block successfully.")
                    else:
                         logger.error(f"Parsed EXPERIENCE_UPDATE block is not a dictionary (type: {type(update_dict)}). Discarding.")
                         update_dict = None # Discard if not a dict

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse EXPERIENCE_UPDATE JSON: {e}")
                    logger.debug(f"Invalid JSON string: {json_str}")
                    # Keep narrative, but update_dict remains None
            else:
                logger.warning("EXPERIENCE_UPDATE block not found in the expected format at the end of the response.")
                # Narrative remains the full output

        except Exception as e:
            logger.error(f"Error during parsing LLM response: {e}", exc_info=True)
            # Return original output as narrative in case of unexpected parsing error
            narrative = llm_output
            update_dict = None

        # Final check if narrative is empty after potential stripping
        if not narrative and llm_output:
             logger.warning("Narrative became empty after parsing, returning original LLM output as narrative.")
             narrative = llm_output

        return narrative, update_dict

__all__ = ["ExperienceParser"] 