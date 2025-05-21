"""
Dream.OS Component Registry

A centralized registry for managing component metadata in the Dream.OS ecosystem.
Provides CRUD operations for component metadata with transaction safety and validation.

Features:
- Persistent storage of component metadata
- Schema validation for component entries
- Transaction safety for concurrent access
- Search and filtering capabilities
"""

import os
import json
import time
import logging
import threading
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Union, Tuple

# Constants
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
ROOT_DIR = Path(os.getcwd()).resolve()
SHARED_RESOURCES_DIR = ROOT_DIR / "runtime" / "shared_resources" / "launcher"
METADATA_DIR = SHARED_RESOURCES_DIR / "metadata"
SCHEMAS_DIR = SHARED_RESOURCES_DIR / "schemas"
REGISTRY_PATH = METADATA_DIR / "component_registry.json"
REGISTRY_BACKUP_DIR = METADATA_DIR / "backups"
TRANSACTION_LOG_PATH = METADATA_DIR / "transaction_log.json"

# Ensure directories exist
for dir_path in [METADATA_DIR, SCHEMAS_DIR, REGISTRY_BACKUP_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dreamos.launcher.registry")


class ComponentRegistry:
    """
    A registry for managing Dream.OS component metadata.
    
    Provides CRUD operations for components with transaction safety,
    schema validation, and search capabilities.
    """
    
    def __init__(self):
        """Initialize the registry with lock for thread safety."""
        self._lock = threading.RLock()
        self._components = {}
        self._schema = self._load_schema()
        self._load_registry()
        
    def _load_schema(self) -> Dict[str, Any]:
        """
        Load the component schema with retry logic.
        
        Returns:
            Dict containing the schema or empty dict on failure
        """
        schema_path = SCHEMAS_DIR / "component_schema.json"
        
        for attempt in range(MAX_RETRIES):
            try:
                if schema_path.exists():
                    with open(schema_path, 'r') as f:
                        return json.load(f)
                else:
                    logger.warning(f"Schema file not found: {schema_path}")
                    # Return basic schema if file not found
                    return {
                        "type": "object",
                        "required": ["component_id", "name", "entry_point", "type"],
                        "properties": {
                            "component_id": {"type": "string"},
                            "name": {"type": "string"},
                            "entry_point": {"type": "string"},
                            "type": {"type": "string", "enum": ["agent", "service", "tool", "utility"]}
                        }
                    }
            except Exception as e:
                logger.error(f"Error loading schema (attempt {attempt+1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    
        logger.error(f"Failed to load schema after {MAX_RETRIES} attempts")
        return {}
    
    def _validate_component(self, component: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a component against the schema.
        
        Args:
            component: Component data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self._schema:
            logger.warning("No schema available for validation")
            return True, None
            
        # Basic required field validation
        required_fields = self._schema.get("required", [])
        for field in required_fields:
            if field not in component:
                return False, f"Missing required field: {field}"
                
        # Type validation for component_id
        if not isinstance(component.get("component_id", ""), str):
            return False, "component_id must be a string"
            
        # Type validation for name
        if not isinstance(component.get("name", ""), str):
            return False, "name must be a string"
            
        # Type validation for entry_point
        if not isinstance(component.get("entry_point", ""), str):
            return False, "entry_point must be a string"
            
        # Enum validation for type
        valid_types = self._schema.get("properties", {}).get("type", {}).get("enum", [])
        if valid_types and component.get("type") not in valid_types:
            return False, f"Invalid type: {component.get('type')}. Must be one of {valid_types}"
            
        return True, None
        
    def _resilient_read(self, file_path: Path) -> Optional[str]:
        """
        Read a file with retry logic.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            File contents as string or None on failure
        """
        for attempt in range(MAX_RETRIES):
            try:
                if not file_path.exists():
                    logger.warning(f"File does not exist: {file_path}")
                    return None
                    
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error reading {file_path} (attempt {attempt+1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    
        logger.error(f"Failed to read {file_path} after {MAX_RETRIES} attempts")
        return None
        
    def _resilient_write(self, file_path: Path, content: str) -> bool:
        """
        Write to a file with retry logic.
        
        Args:
            file_path: Path to the file to write
            content: Content to write
            
        Returns:
            True if successful, False otherwise
        """
        temp_file = file_path.with_suffix('.tmp')
        
        for attempt in range(MAX_RETRIES):
            try:
                # Write to temp file first
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                # Rename to target file (atomic on most file systems)
                if temp_file.exists():
                    temp_file.replace(file_path)
                    return True
            except Exception as e:
                logger.error(f"Error writing {file_path} (attempt {attempt+1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    
        logger.error(f"Failed to write {file_path} after {MAX_RETRIES} attempts")
        
        # Clean up temp file if it exists
        if temp_file.exists():
            try:
                temp_file.unlink()
            except:
                pass
                
        return False
    
    def _create_backup(self) -> bool:
        """
        Create a backup of the current registry.
        
        Returns:
            True if successful, False otherwise
        """
        if not REGISTRY_PATH.exists():
            logger.warning("No registry file to backup")
            return False
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = REGISTRY_BACKUP_DIR / f"registry_backup_{timestamp}.json"
        
        try:
            shutil.copy2(REGISTRY_PATH, backup_path)
            logger.info(f"Created registry backup: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
            
    def _load_registry(self) -> None:
        """Load the component registry from disk."""
        with self._lock:
            registry_content = self._resilient_read(REGISTRY_PATH)
            
            if registry_content:
                try:
                    registry_data = json.loads(registry_content)
                    raw_components = registry_data.get("components", {})
                    
                    # Clean up any None components or invalid entries
                    self._components = {}
                    for comp_id, comp in raw_components.items():
                        if comp is not None and isinstance(comp, dict):
                            self._components[comp_id] = comp
                        else:
                            logger.warning(f"Skipping invalid component with ID {comp_id}: {comp}")
                            
                    logger.info(f"Loaded {len(self._components)} components from registry")
                except Exception as e:
                    logger.error(f"Error parsing registry: {e}")
                    self._components = {}
            else:
                logger.info("Registry file not found, starting with empty registry")
                self._components = {}
                
    def _save_registry(self) -> bool:
        """
        Save the component registry to disk.
        
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            # Create backup first
            if REGISTRY_PATH.exists():
                self._create_backup()
                
            # Clean up any None or invalid components before saving
            clean_components = {}
            for comp_id, comp in self._components.items():
                if comp is not None and isinstance(comp, dict):
                    clean_components[comp_id] = comp
                else:
                    logger.warning(f"Skipping invalid component during save with ID {comp_id}: {comp}")
                    
            registry_data = {
                "components": clean_components,
                "last_updated": datetime.now().isoformat(),
                "version": "1.0.0"
            }
            
            success = self._resilient_write(
                REGISTRY_PATH,
                json.dumps(registry_data, indent=2)
            )
            
            if success:
                logger.info(f"Saved registry with {len(clean_components)} components")
            else:
                logger.error("Failed to save registry")
                
            return success
            
    def _log_transaction(self, operation: str, component_id: str, details: Dict[str, Any]) -> None:
        """
        Log a transaction to the transaction log.
        
        Args:
            operation: Operation type (CREATE, UPDATE, DELETE)
            component_id: ID of the component
            details: Additional transaction details
        """
        transaction_log_content = self._resilient_read(TRANSACTION_LOG_PATH)
        
        if transaction_log_content:
            try:
                transaction_log = json.loads(transaction_log_content)
            except:
                transaction_log = {"transactions": []}
        else:
            transaction_log = {"transactions": []}
            
        transaction = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "component_id": component_id,
            "details": details
        }
        
        transaction_log["transactions"].append(transaction)
        
        # Keep only the last 1000 transactions
        if len(transaction_log["transactions"]) > 1000:
            transaction_log["transactions"] = transaction_log["transactions"][-1000:]
            
        self._resilient_write(
            TRANSACTION_LOG_PATH,
            json.dumps(transaction_log, indent=2)
        )
    
    def get_all_components(self) -> Dict[str, Any]:
        """
        Get all components in the registry.
        
        Returns:
            Dictionary of component_id -> component data
        """
        with self._lock:
            # Return a copy to prevent modification and filter out None values
            return {k: v for k, v in self._components.items() if v is not None}
            
    def get_component(self, component_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a component by ID.
        
        Args:
            component_id: ID of the component to get
            
        Returns:
            Component data or None if not found
        """
        with self._lock:
            component = self._components.get(component_id)
            
            if component is not None:
                # Return a copy to prevent modification
                return dict(component)
            else:
                return None
                
    def create_component(self, component: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Create a new component in the registry.
        
        Args:
            component: Component data to add
            
        Returns:
            Tuple of (success, error_message)
        """
        with self._lock:
            # Get component ID
            component_id = component.get("component_id")
            
            if not component_id:
                return False, "Component ID is required"
                
            # Check if component already exists
            if component_id in self._components:
                return False, f"Component with ID {component_id} already exists"
                
            # Validate component
            is_valid, error = self._validate_component(component)
            if not is_valid:
                return False, error
                
            # Add timestamp
            component["created_at"] = datetime.now().isoformat()
            component["updated_at"] = component["created_at"]
            
            # Add to registry
            self._components[component_id] = component
            
            # Save registry
            if self._save_registry():
                self._log_transaction("CREATE", component_id, {"component": component})
                return True, None
            else:
                # Revert changes if save failed
                if component_id in self._components:
                    del self._components[component_id]
                return False, "Failed to save registry"
                
    def update_component(self, component_id: str, updates: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Update an existing component in the registry.
        
        Args:
            component_id: ID of the component to update
            updates: Fields to update
            
        Returns:
            Tuple of (success, error_message)
        """
        with self._lock:
            # Check if component exists
            if component_id not in self._components:
                return False, f"Component with ID {component_id} not found"
                
            # Get a copy of the current component
            component = self._components.get(component_id)
            if component is None:
                return False, f"Component with ID {component_id} is invalid"
                
            component = dict(component)
            
            # Store original for transaction log
            original = dict(component)
            
            # Apply updates
            for key, value in updates.items():
                if key != "component_id":  # Don't allow changing the ID
                    component[key] = value
                    
            # Update timestamp
            component["updated_at"] = datetime.now().isoformat()
            
            # Validate updated component
            is_valid, error = self._validate_component(component)
            if not is_valid:
                return False, error
                
            # Update in registry
            self._components[component_id] = component
            
            # Save registry
            if self._save_registry():
                self._log_transaction("UPDATE", component_id, {
                    "original": original,
                    "updates": updates,
                    "result": component
                })
                return True, None
            else:
                # Revert changes if save failed
                self._components[component_id] = original
                return False, "Failed to save registry"
                
    def delete_component(self, component_id: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a component from the registry.
        
        Args:
            component_id: ID of the component to delete
            
        Returns:
            Tuple of (success, error_message)
        """
        with self._lock:
            # Check if component exists
            if component_id not in self._components:
                # Already gone, consider it a success
                return True, None
                
            # Store original for transaction log if it exists
            component = self._components.get(component_id)
            original = dict(component) if component else {}
            
            # Remove from registry
            del self._components[component_id]
            
            # Save registry
            if self._save_registry():
                if original:  # Only log if component existed
                    self._log_transaction("DELETE", component_id, {"component": original})
                return True, None
            else:
                # Revert changes if save failed
                if original:
                    self._components[component_id] = original
                return False, "Failed to save registry"
                
    def search_components(self, 
                        filters: Dict[str, Any] = None, 
                        tags: List[str] = None) -> Dict[str, Any]:
        """
        Search for components matching filters.
        
        Args:
            filters: Dict of field:value pairs to filter by
            tags: List of tags to filter by (all must match)
            
        Returns:
            Dictionary of matching component_id -> component data
        """
        with self._lock:
            # Start with all components, filtering out None values
            results = {k: v for k, v in self._components.items() if v is not None}
            
            # Apply field filters
            if filters:
                for field, value in filters.items():
                    results = {
                        comp_id: comp for comp_id, comp in results.items()
                        if comp.get(field) == value
                    }
                    
            # Apply tag filters
            if tags:
                results = {
                    comp_id: comp for comp_id, comp in results.items()
                    if all(tag in comp.get("tags", []) for tag in tags)
                }
                
            return results
            
    def get_components_by_type(self, component_type: str) -> Dict[str, Any]:
        """
        Get all components of a specific type.
        
        Args:
            component_type: Type to filter by
            
        Returns:
            Dictionary of matching component_id -> component data
        """
        return self.search_components(filters={"type": component_type})
        
    def get_components_by_owner(self, owner_agent: str) -> Dict[str, Any]:
        """
        Get all components owned by a specific agent.
        
        Args:
            owner_agent: Owner to filter by
            
        Returns:
            Dictionary of matching component_id -> component data
        """
        return self.search_components(filters={"owner_agent": owner_agent})
        
    def refresh_from_disk(self) -> bool:
        """
        Refresh the registry from disk.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self._load_registry()
            return True
        except Exception as e:
            logger.error(f"Error refreshing registry: {e}")
            return False
            
    def restore_backup(self, backup_timestamp: str = None) -> Tuple[bool, Optional[str]]:
        """
        Restore a registry backup.
        
        Args:
            backup_timestamp: Timestamp of backup to restore (latest if None)
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Find the backup file
            if backup_timestamp:
                backup_path = REGISTRY_BACKUP_DIR / f"registry_backup_{backup_timestamp}.json"
                if not backup_path.exists():
                    return False, f"Backup with timestamp {backup_timestamp} not found"
            else:
                backup_files = list(REGISTRY_BACKUP_DIR.glob("registry_backup_*.json"))
                if not backup_files:
                    return False, "No backup files found"
                    
                # Sort by modification time (newest first)
                backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                backup_path = backup_files[0]
                
            # Copy backup to registry file
            shutil.copy2(backup_path, REGISTRY_PATH)
            
            # Reload the registry
            self._load_registry()
            
            logger.info(f"Restored registry from backup: {backup_path}")
            return True, None
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False, str(e) 