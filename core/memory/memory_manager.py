"""
Manages persistent storage and retrieval of narrative fragments.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Define default storage path relative to project root
DEFAULT_MEMORY_DIR = Path(__file__).parent.parent.parent / "runtime" / "memory"
DEFAULT_FRAGMENT_FILE = DEFAULT_MEMORY_DIR / "core_fragments.json"

class MemoryManager:
    """Handles loading and saving of dictionary-like fragments to a JSON file."""

    def __init__(self, fragment_file_path: Path = DEFAULT_FRAGMENT_FILE):
        """
        Initializes the MemoryManager.

        Args:
            fragment_file_path (Path): The path to the JSON file used for storage.
        """
        self.fragment_file_path = fragment_file_path
        self.memory: Dict[str, Dict[str, Any]] = {}
        self._ensure_storage_exists()
        self.load_memory()
        logger.info(f"MemoryManager initialized. Storage: {self.fragment_file_path}")

    def _ensure_storage_exists(self):
        """Ensures the storage directory and file exist."""
        try:
            self.fragment_file_path.parent.mkdir(parents=True, exist_ok=True)
            # Create the file with an empty object if it doesn't exist
            if not self.fragment_file_path.exists():
                with open(self.fragment_file_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                logger.info(f"Created fragment storage file: {self.fragment_file_path}")
        except Exception as e:
            logger.error(f"Failed to ensure storage directory/file exists at {self.fragment_file_path}: {e}", exc_info=True)
            # Depending on severity, might want to raise here

    def load_memory(self) -> bool:
        """Loads all fragments from the JSON file into memory."""
        if not self.fragment_file_path.exists():
            logger.warning(f"Fragment file {self.fragment_file_path} not found. Starting with empty memory.")
            self.memory = {}
            return False
        try:
            with open(self.fragment_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip(): # Handle empty file
                     self.memory = {}
                else:
                    self.memory = json.loads(content)
                if not isinstance(self.memory, dict):
                     logger.error(f"Invalid format in {self.fragment_file_path}. Expected JSON object. Resetting memory.")
                     self.memory = {}
                     return False
            logger.info(f"Loaded {len(self.memory)} fragments from {self.fragment_file_path}")
            return True
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from {self.fragment_file_path}. File might be corrupt. Resetting memory.", exc_info=True)
            self.memory = {}
            return False
        except Exception as e:
            logger.error(f"Failed to load memory from {self.fragment_file_path}: {e}", exc_info=True)
            self.memory = {} # Ensure memory is empty on failure
            return False

    def save_memory(self) -> bool:
        """Saves the current in-memory fragment dictionary back to the JSON file."""
        try:
            # Ensure directory exists just in case
            self.fragment_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.fragment_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, indent=2) # Use indent for readability
            logger.info(f"Saved {len(self.memory)} fragments to {self.fragment_file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save memory to {self.fragment_file_path}: {e}", exc_info=True)
            return False

    def save_fragment(self, fragment_id: str, fragment_data: Dict[str, Any]) -> bool:
        """Adds or updates a single fragment and saves the entire memory."""
        if not fragment_id:
             logger.error("Cannot save fragment: fragment_id is empty.")
             return False
        if not isinstance(fragment_data, dict):
            logger.error(f"Cannot save fragment '{fragment_id}': fragment_data is not a dictionary.")
            return False
            
        self.memory[fragment_id] = fragment_data
        logger.debug(f"Fragment '{fragment_id}' added/updated in memory.")
        return self.save_memory() # Persist change immediately

    def load_fragment(self, fragment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single fragment by its ID from the in-memory store."""
        fragment = self.memory.get(fragment_id)
        if fragment:
            logger.debug(f"Retrieved fragment '{fragment_id}' from memory.")
        else:
            logger.warning(f"Fragment '{fragment_id}' not found in memory.")
        return fragment

    def delete_fragment(self, fragment_id: str) -> bool:
         """Deletes a fragment by ID and saves the changes."""
         if fragment_id in self.memory:
              del self.memory[fragment_id]
              logger.info(f"Fragment '{fragment_id}' deleted from memory.")
              return self.save_memory()
         else:
              logger.warning(f"Fragment '{fragment_id}' not found, cannot delete.")
              return False
              
    def list_fragment_ids(self) -> List[str]:
         """Returns a list of all fragment IDs currently in memory."""
         return list(self.memory.keys())

# Example Usage
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    # Use a temporary file for isolated testing
    temp_dir = Path(__file__).parent.parent.parent / "runtime" / "temp_test_memory"
    temp_file = temp_dir / "test_fragments.json"
    if temp_file.exists(): temp_file.unlink()
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    manager = MemoryManager(fragment_file_path=temp_file)
    
    print("--- Initial State ---")
    print(f"Fragment IDs: {manager.list_fragment_ids()}")
    
    print("\n--- Saving Fragments ---")
    data1 = {"name": "Test 1", "core_text": "First fragment", "tags": ["test"], "rank": "B"}
    data2 = {"name": "Test 2", "core_text": "Second fragment", "tags": ["test", "example"], "rank": "A"}
    manager.save_fragment("frag_1", data1)
    manager.save_fragment("frag_2", data2)
    print(f"Fragment IDs after save: {manager.list_fragment_ids()}")

    print("\n--- Loading Fragment ---")
    loaded_frag = manager.load_fragment("frag_1")
    print(f"Loaded frag_1: {loaded_frag}")
    missing_frag = manager.load_fragment("frag_x")
    print(f"Loaded frag_x: {missing_frag}")

    print("\n--- Deleting Fragment ---")
    manager.delete_fragment("frag_1")
    print(f"Fragment IDs after delete: {manager.list_fragment_ids()}")
    
    print("\n--- Reloading from file ---")
    manager_reloaded = MemoryManager(fragment_file_path=temp_file)
    print(f"Reloaded Fragment IDs: {manager_reloaded.list_fragment_ids()}")
    print(f"Reloaded frag_2: {manager_reloaded.load_fragment('frag_2')}")

    # Clean up temp file
    # if temp_file.exists(): temp_file.unlink()
    # if temp_dir.exists() and not any(temp_dir.iterdir()): temp_dir.rmdir()
    print("\n--- Test Complete --- (")
    print(f"Check {temp_file} for content)") 