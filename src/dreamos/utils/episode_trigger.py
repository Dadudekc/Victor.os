"""
Utility for monitoring agent logs and activating episode triggers based on defined patterns.
"""
import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Setup basic logging for the utility itself
logger = logging.getLogger(__name__)

EPISODE_REGISTRY_PATH = Path("runtime/episodes/active_episode.json")

class EpisodeManager:
    """Manages loading and accessing episode data."""

    def __init__(self, registry_path: Path = EPISODE_REGISTRY_PATH):
        self.registry_path = registry_path
        self._episode_data: Optional[Dict[str, Any]] = None
        self._load_registry()

    def _load_registry(self):
        """Loads the episode registry from the JSON file."""
        try:
            if self.registry_path.exists():
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    self._episode_data = json.load(f)
                logger.info(f"Successfully loaded episode registry from {self.registry_path}")
            else:
                logger.warning(f"Episode registry file not found at {self.registry_path}")
                self._episode_data = None
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.registry_path}: {e}")
            self._episode_data = None
        except Exception as e:
            logger.error(f"Unexpected error loading episode registry: {e}", exc_info=True)
            self._episode_data = None

    def get_active_episode_id(self) -> Optional[str]:
        """Returns the ID of the currently active episode."""
        if self._episode_data:
            return self._episode_data.get("active_episode_id")
        return None

    def get_episode_details(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """Returns the details for a specific episode ID."""
        if self._episode_data and "episodes" in self._episode_data:
            return self._episode_data["episodes"].get(episode_id)
        return None

    def get_active_episode_details(self) -> Optional[Dict[str, Any]]:
        """Returns the details for the currently active episode."""
        active_id = self.get_active_episode_id()
        if active_id:
            return self.get_episode_details(active_id)
        return None

    def check_log_for_triggers(self, log_content: str, agent_id_context: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Checks the given log content against triggers defined in the active episode.

        Args:
            log_content: The content of the log to check.
            agent_id_context: The ID of the agent whose log is being checked, for context.

        Returns:
            A list of matched trigger actions. Each item in the list is a dictionary
            representing the trigger, augmented with any captured groups from regex.
        """
        active_episode = self.get_active_episode_details()
        matched_triggers: List[Dict[str, Any]] = []

        if not active_episode or "triggers" not in active_episode:
            logger.debug("No active episode or no triggers defined in the active episode.")
            return matched_triggers

        for trigger in active_episode["triggers"]:
            pattern = trigger.get("log_pattern")
            pattern_type = trigger.get("log_pattern_type", "literal") # Default to literal match

            if not pattern:
                logger.warning(f"Trigger {trigger.get('id')} has no log_pattern defined. Skipping.")
                continue
            
            match_found = False
            captured_groups = {}

            try:
                if pattern_type == "regex":
                    match = re.search(pattern, log_content)
                    if match:
                        match_found = True
                        captured_groups = match.groupdict()
                        # Ensure agent_id from pattern overrides context if present
                        if 'agent_id' in captured_groups and captured_groups['agent_id']:
                            trigger_agent_id = captured_groups['agent_id']
                        elif agent_id_context:
                            trigger_agent_id = agent_id_context
                        else:
                            trigger_agent_id = 'UNKNOWN_AGENT'
                        
                        # Substitute {agent_id} in activation message if present
                        if 'activation_message_to_log' in trigger:
                            trigger['activation_message_to_log'] = trigger['activation_message_to_log'].format(agent_id=trigger_agent_id)

                elif pattern_type == "literal":
                    if pattern in log_content:
                        match_found = True
                else:
                    logger.warning(f"Unsupported log_pattern_type: {pattern_type} for trigger {trigger.get('id')}")
                    continue

                if match_found:
                    logger.info(f"Log trigger '{trigger.get('id')}' matched for agent '{agent_id_context or 'any'}'. Pattern: '{pattern}'")
                    action_info = trigger.copy() # Copy to avoid modifying the original registry data
                    action_info['captured_data'] = captured_groups
                    matched_triggers.append(action_info)
            except re.error as e:
                logger.error(f"Regex error for trigger '{trigger.get('id')}' with pattern '{pattern}': {e}")
            except Exception as e:
                logger.error(f"Error processing trigger '{trigger.get('id')}': {e}", exc_info=True)
        
        return matched_triggers

# Example Usage (Illustrative - not typically run directly like this)
if __name__ == "__main__":
    # Configure basic logging for example run
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    logger.info("Initializing EpisodeManager for example usage...")
    manager = EpisodeManager()
    active_episode_id = manager.get_active_episode_id()

    if active_episode_id:
        logger.info(f"Active episode ID: {active_episode_id}")
        active_details = manager.get_active_episode_details()
        if active_details:
            logger.info(f"Active episode description: {active_details.get('description')}")
            # print(f"Full active episode details: {json.dumps(active_details, indent=2)}")

            # Example log content simulation
            sample_log_from_agent1 = "INFO - Agent Agent-Test007_UNIFIED_ONBOARDING_COMPLETE_20231026 has completed onboarding steps."
            sample_log_from_agent2 = "INFO - Agent Agent-Alpha_TASK_EXECUTION_START task_id=123 some other details."
            
            logger.info(f"\nChecking sample log 1: '{sample_log_from_agent1}'")
            triggered_actions1 = manager.check_log_for_triggers(sample_log_from_agent1, agent_id_context="Agent-Test007")
            if triggered_actions1:
                for action in triggered_actions1:
                    logger.info(f"  Matched Trigger ID: {action.get('id')}, Action Type: {action.get('action_type')}, Payload: {action.get('action_payload')}")
                    if action.get('activation_message_to_log'):
                        logger.info(f"    Activation message: {action.get('activation_message_to_log')}")
                    if action.get('captured_data'):
                        logger.info(f"    Captured data: {action.get('captured_data')}")
            else:
                logger.info("  No triggers matched.")

            logger.info(f"\nChecking sample log 2: '{sample_log_from_agent2}'")
            triggered_actions2 = manager.check_log_for_triggers(sample_log_from_agent2, agent_id_context="Agent-Alpha")
            if triggered_actions2:
                 for action in triggered_actions2:
                    logger.info(f"  Matched Trigger ID: {action.get('id')}, Action Type: {action.get('action_type')}, Payload: {action.get('action_payload')}")
            else:
                logger.info("  No triggers matched.")
    else:
        logger.warning("No active episode found.")

    # Example of what might happen if the registry file is missing or malformed
    # manager_bad = EpisodeManager(registry_path=Path("runtime/episodes/non_existent.json"))
    # logger.info(f"Active episode ID (bad registry): {manager_bad.get_active_episode_id()}") 