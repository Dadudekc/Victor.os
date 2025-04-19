import os
import json
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable

# Use project-level config for consistency
import config as project_config

# Configure logging
logger = logging.getLogger("MemoryManager")
logger.setLevel(project_config.LOG_LEVEL)

# Define structure for memory components
DEFAULT_SKILLS = lambda: {}
DEFAULT_QUESTS = lambda: {"active": [], "completed": []}
DEFAULT_INVENTORY = lambda: {}
# Add other memory components as needed (e.g., reputation, locations)

# Constants for file names
SKILLS_FILE = "skills.json"
QUESTS_FILE = "quests.json"
INVENTORY_FILE = "inventory.json"

class MemoryManager:
    """Manages the RPG world state (skills, quests, inventory) stored in JSON files."""

    def __init__(self, memory_dir: str = project_config.MEMORY_DIR):
        self.memory_dir = memory_dir
        os.makedirs(self.memory_dir, exist_ok=True)
        logger.info(f"MemoryManager initialized. Using directory: {self.memory_dir}")

        # File paths
        self.skills_file_path = os.path.join(self.memory_dir, SKILLS_FILE)
        self.quests_file_path = os.path.join(self.memory_dir, QUESTS_FILE)
        self.inventory_file_path = os.path.join(self.memory_dir, INVENTORY_FILE)

        # Thread lock for safe file access
        self._lock = threading.Lock()

        # Load initial state
        self.skills: Dict[str, Dict[str, Any]] = self._load_json_file(self.skills_file_path, DEFAULT_SKILLS(), "Skills")
        self.quests: Dict[str, List[str]] = self._load_json_file(self.quests_file_path, DEFAULT_QUESTS(), "Quests")
        self.inventory: Dict[str, int] = self._load_json_file(self.inventory_file_path, DEFAULT_INVENTORY(), "Inventory")

    def _load_json_file(self, file_path: str, default_factory: Callable[[], Any], state_name: str) -> Any:
        """Loads a JSON file safely, returning default if not found or invalid."""
        with self._lock:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        logger.info(f"✅ Loaded {state_name} from {file_path}")
                        return data
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to decode JSON from {state_name} file {file_path}: {e}. Using default.")
                    return default_factory()
                except Exception as e:
                    logger.error(f"❌ Failed to load {state_name} from {file_path}: {e}. Using default.")
                    return default_factory()
            else:
                logger.warning(f"⚠️ No {state_name} file found at {file_path}. Initializing with default state.")
                return default_factory()

    def _async_save_json_file(self, file_path: str, data: Any, state_name: str) -> None:
        """Saves data to a JSON file asynchronously and safely."""
        # Create a deep copy to prevent modification during saving process
        data_copy = json.loads(json.dumps(data))

        def save_task() -> None:
            temp_file_path = file_path + '.tmp'
            try:
                with open(temp_file_path, 'w', encoding='utf-8') as file:
                    json.dump(data_copy, file, indent=4, ensure_ascii=False)
                os.replace(temp_file_path, file_path)
                logger.debug(f"💾 {state_name} saved asynchronously to {file_path}")
            except Exception as e:
                logger.error(f"❌ Failed to save {state_name} to {file_path}: {e}")
            finally:
                 if os.path.exists(temp_file_path):
                     try:
                         os.remove(temp_file_path)
                     except Exception as e_rem:
                         logger.error(f"Failed to remove temp file {temp_file_path}: {e_rem}")

        threading.Thread(target=save_task, daemon=True).start()

    def save_all_memory_states(self) -> None:
        """Saves all current memory components to their respective files."""
        logger.info("💾 Saving all memory states...")
        self._async_save_json_file(self.skills_file_path, self.skills, "Skills")
        self._async_save_json_file(self.quests_file_path, self.quests, "Quests")
        self._async_save_json_file(self.inventory_file_path, self.inventory, "Inventory")

    def get_current_state(self) -> Dict[str, Any]:
         """Returns a dictionary representing the current RPG world state."""
         # Return copies to prevent external modification
         return {
            "skills": json.loads(json.dumps(self.skills)),
            "quests": json.loads(json.dumps(self.quests)),
            "inventory": json.loads(json.dumps(self.inventory)),
            # Add other state components here
         }

    def update_state(self, update_dict: Dict[str, Any]) -> None:
        """Updates the memory state based on a parsed EXPERIENCE_UPDATE dictionary."""
        if not isinstance(update_dict, dict):
            logger.warning("Received invalid update_dict (not a dict). Skipping update.")
            return

        logger.info(f"Applying memory updates: {json.dumps(update_dict)}")
        updated = False
        with self._lock:
            # --- Update Skills --- (Handles XP gain, level calculation could be added)
            if isinstance(update_dict.get("skills"), dict):
                for skill_name, skill_update in update_dict["skills"].items():
                    if isinstance(skill_update, dict) and "xp_gain" in skill_update:
                        xp_gain = skill_update.get("xp_gain", 0)
                        if isinstance(xp_gain, (int, float)) and xp_gain > 0:
                            if skill_name not in self.skills:
                                self.skills[skill_name] = {"level": 1, "xp": 0}
                            self.skills[skill_name]["xp"] = self.skills[skill_name].get("xp", 0) + xp_gain
                            # TODO: Add level up logic based on XP thresholds if desired
                            logger.debug(f"Updated skill '{skill_name}': +{xp_gain} XP -> Total {self.skills[skill_name]['xp']}")
                            updated = True

            # --- Update Quests --- (Handles new quests and status changes)
            if isinstance(update_dict.get("quests_new"), list):
                for quest_name in update_dict["quests_new"]:
                    if isinstance(quest_name, str) and quest_name not in self.quests.get("active", []) and quest_name not in self.quests.get("completed", []):
                        self.quests.setdefault("active", []).append(quest_name)
                        logger.debug(f"Added new active quest: '{quest_name}'")
                        updated = True

            if isinstance(update_dict.get("quests_updated"), list):
                for quest_update in update_dict["quests_updated"]:
                    if isinstance(quest_update, dict) and "name" in quest_update and "status" in quest_update:
                        quest_name = quest_update["name"]
                        new_status = quest_update["status"]
                        # Move from active to completed
                        if new_status == "completed" and quest_name in self.quests.get("active", []):
                            self.quests["active"].remove(quest_name)
                            self.quests.setdefault("completed", []).append(quest_name)
                            logger.debug(f"Moved quest '{quest_name}' to completed.")
                            updated = True
                        # Add other status transitions if needed (e.g., failed, active)

            # --- Update Inventory --- (Handles adding/removing items)
            if isinstance(update_dict.get("inventory_added"), dict):
                for item_name, count in update_dict["inventory_added"].items():
                    if isinstance(item_name, str) and isinstance(count, int) and count > 0:
                        self.inventory[item_name] = self.inventory.get(item_name, 0) + count
                        logger.debug(f"Added inventory: +{count} '{item_name}'")
                        updated = True

            if isinstance(update_dict.get("inventory_removed"), dict):
                 for item_name, count in update_dict["inventory_removed"].items():
                    if isinstance(item_name, str) and isinstance(count, int) and count > 0:
                         current_count = self.inventory.get(item_name, 0)
                         new_count = max(0, current_count - count)
                         if new_count == 0:
                             if item_name in self.inventory: del self.inventory[item_name]
                             logger.debug(f"Removed inventory: All '{item_name}'")
                         else:
                             self.inventory[item_name] = new_count
                             logger.debug(f"Removed inventory: -{count} '{item_name}'")
                         updated = True

            # --- Add other update logic here (reputation, locations, etc.) ---

        if updated:
            logger.info("Memory state updated successfully.")
            self.save_all_memory_states() # Save changes asynchronously
        else:
            logger.info("No applicable memory updates found in the provided dictionary.")

__all__ = ["MemoryManager"] 