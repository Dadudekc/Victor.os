import os
import json
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
import copy # For deep merging

# Use project-level config for consistency
# import config as project_config
from dreamscape_generator import config as project_config

# Configure logging
logger = logging.getLogger("MemoryManager")
logger.setLevel(project_config.LOG_LEVEL)

# Default structure for the memory state data
DEFAULT_MEMORY_DATA = lambda: {
    "skills": {},
    "quests": {"active": [], "completed": []},
    "inventory": {},
    # Add other memory components as needed (e.g., reputation, locations)
}

# Constants for file names
MEMORY_STATE_FILE = "memory_state.json"

class MemoryManager:
    """Manages the consolidated RPG world state stored in a single JSON file."""

    def __init__(self, memory_dir: str = project_config.MEMORY_DIR):
        self.memory_dir = memory_dir
        os.makedirs(self.memory_dir, exist_ok=True)
        logger.info(f"MemoryManager initialized. Using directory: {self.memory_dir}")

        # File path
        self.memory_file_path = os.path.join(self.memory_dir, MEMORY_STATE_FILE)

        # Thread lock for safe file access
        self._lock = threading.Lock()

        # Load initial state
        self.memory_state: Dict[str, Any] = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Loads the consolidated memory state from JSON file safely."""
        default_state = {
            "version": 0,
            "last_updated": None,
            "data": DEFAULT_MEMORY_DATA()
        }
        with self._lock:
            if os.path.exists(self.memory_file_path):
                try:
                    with open(self.memory_file_path, 'r', encoding='utf-8') as file:
                        loaded_state = json.load(file)
                        # Ensure essential keys exist
                        if "version" not in loaded_state: loaded_state["version"] = 0
                        if "last_updated" not in loaded_state: loaded_state["last_updated"] = None
                        if "data" not in loaded_state: loaded_state["data"] = DEFAULT_MEMORY_DATA()
                        logger.info(f"✅ Loaded Memory State (v{loaded_state['version']}) from {self.memory_file_path}")
                        return loaded_state
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to decode JSON from {self.memory_file_path}: {e}. Using default state.")
                    return default_state
                except Exception as e:
                    logger.error(f"❌ Failed to load state from {self.memory_file_path}: {e}. Using default state.")
                    return default_state
            else:
                logger.warning(f"⚠️ No memory state file found at {self.memory_file_path}. Initializing with default state.")
                self._save_state(default_state) # Save the initial default state
                return default_state

    def _save_state(self, state_to_save: Dict[str, Any], is_async: bool = True) -> None:
        """Saves the provided state to the JSON file, optionally asynchronously."""
        # Create a deep copy to prevent modification during saving process
        state_copy = copy.deepcopy(state_to_save)

        def save_task() -> None:
            temp_file_path = self.memory_file_path + '.tmp'
            try:
                with self._lock: # Ensure write operation is atomic regarding self.memory_state updates
                    with open(temp_file_path, 'w', encoding='utf-8') as file:
                        json.dump(state_copy, file, indent=4, ensure_ascii=False)
                    os.replace(temp_file_path, self.memory_file_path)
                logger.debug(f"💾 Memory State (v{state_copy.get('version', 'N/A')}) saved to {self.memory_file_path}")
            except Exception as e:
                logger.error(f"❌ Failed to save Memory State to {self.memory_file_path}: {e}")
            finally:
                 if os.path.exists(temp_file_path):
                     try:
                         os.remove(temp_file_path)
                     except Exception as e_rem:
                         logger.error(f"Failed to remove temp file {temp_file_path}: {e_rem}")

        if is_async:
            threading.Thread(target=save_task, daemon=True).start()
        else:
            save_task() # Execute synchronously

    def get_current_state_data(self) -> Dict[str, Any]:
         """Returns a deep copy of the 'data' portion of the current memory state."""
         with self._lock:
            return copy.deepcopy(self.memory_state.get("data", DEFAULT_MEMORY_DATA()))

    def get_full_state(self) -> Dict[str, Any]:
        """Returns a deep copy of the entire current memory state, including metadata."""
        with self._lock:
            return copy.deepcopy(self.memory_state)

    def _deep_merge_dicts(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merges update dict into base dict."""
        for key, value in update.items():
            if isinstance(value, dict):
                # Get node or create one
                node = base.setdefault(key, {})
                if isinstance(node, dict):
                    self._deep_merge_dicts(node, value)
                else:
                    # Handle case where base has a non-dict at key
                    base[key] = value
            else:
                base[key] = value
        return base

    def update_state(self, update_dict: Dict[str, Any]) -> bool:
        """Updates the memory state['data'] based on a dictionary of updates.

        Uses merging logic similar to AletheiaPromptManager:
        - Appends unique items to lists.
        - Deep merges dictionaries.
        - Replaces scalar values.

        Increments version and updates timestamp on successful update.

        Returns:
            bool: True if the state was changed, False otherwise.
        """
        if not isinstance(update_dict, dict) or not update_dict:
            logger.warning(f"Received invalid or empty update_dict: {update_dict}. Skipping update.")
            return False

        logger.info(f"Applying memory updates: {json.dumps(update_dict)}")
        changed = False
        with self._lock:
            current_data = self.memory_state["data"]
            original_data_json = json.dumps(current_data, sort_keys=True) # For change detection

            for key, value in update_dict.items():
                if key not in current_data:
                    # If key is new, just add it
                    current_data[key] = copy.deepcopy(value)
                    changed = True
                    logger.debug(f"Added new key '{key}' to memory data.")
                    continue

                target = current_data[key]

                if isinstance(target, list) and isinstance(value, list):
                    # Append unique items from the update list
                    initial_len = len(target)
                    for item in value:
                        # Use deepcopy for complex items if necessary, basic check for now
                        if item not in target:
                            target.append(copy.deepcopy(item))
                    if len(target) > initial_len:
                         logger.debug(f"Appended {len(target) - initial_len} items to list '{key}'.")
                         changed = True
                elif isinstance(target, dict) and isinstance(value, dict):
                    # Deep merge dictionaries
                    initial_json = json.dumps(target, sort_keys=True)
                    merged_dict = self._deep_merge_dicts(target, value)
                    current_data[key] = merged_dict # Update the reference in current_data
                    if json.dumps(merged_dict, sort_keys=True) != initial_json:
                        logger.debug(f"Merged dictionary updates for key '{key}'.")
                        changed = True
                else:
                    # Replace scalar values or handle type mismatch by replacement
                    if target != value:
                         logger.debug(f"Replaced value for key '{key}'. Old: {target}, New: {value}")
                         current_data[key] = copy.deepcopy(value)
                         changed = True

            # Check if anything actually changed (more robust than just tracking flags)
            final_data_json = json.dumps(current_data, sort_keys=True)
            if final_data_json != original_data_json:
                 changed = True # Confirm change
                 self.memory_state["version"] = self.memory_state.get("version", 0) + 1
                 self.memory_state["last_updated"] = datetime.now(timezone.utc).isoformat()
                 logger.info(f"Memory state updated successfully to version {self.memory_state['version']}.")
                 self._save_state(self.memory_state, is_async=True) # Save changes asynchronously
            else:
                 logger.info("No effective changes applied to memory state.")
                 changed = False

        return changed

__all__ = ["MemoryManager"] 