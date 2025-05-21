#!/usr/bin/env python3
"""
Test script for Dream.OS Component Registry

This script tests the functionality of the Component Registry API.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dreamos.launcher.registry import ComponentRegistry

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dreamos.launcher.test_registry")


def test_registry():
    """Run tests for the Component Registry API."""
    logger.info("Starting Component Registry tests")
    
    # Initialize registry
    registry = ComponentRegistry()
    initial_component_count = len(registry.get_all_components())
    logger.info(f"Starting with {initial_component_count} components in registry")
    
    # Test component data
    test_components = [
        {
            "component_id": "test-agent-1",
            "name": "Test Agent 1",
            "description": "A test agent component",
            "entry_point": "src/dreamos/agents/test_agent.py",
            "type": "agent",
            "owner_agent": "agent-5",
            "dependencies": ["test-service-1"],
            "required_env_vars": ["TEST_API_KEY", "TEST_MODE"],
            "tags": ["test", "agent", "experimental"]
        },
        {
            "component_id": "test-service-1",
            "name": "Test Service 1",
            "description": "A test service component",
            "entry_point": "src/dreamos/services/test_service.py",
            "type": "service",
            "owner_agent": "agent-5",
            "dependencies": [],
            "required_env_vars": ["SERVICE_PORT"],
            "tags": ["test", "service"]
        },
        {
            "component_id": "test-tool-1",
            "name": "Test Tool 1",
            "description": "A test tool component",
            "entry_point": "src/dreamos/tools/test_tool.py",
            "type": "tool",
            "owner_agent": "agent-5",
            "dependencies": [],
            "tags": ["test", "tool"]
        }
    ]
    
    # Clean up existing test components if they exist
    logger.info("Cleaning up any existing test components")
    for component in test_components:
        registry.delete_component(component["component_id"])
    
    # Test 1: Create components
    logger.info("Test 1: Creating components")
    for component in test_components:
        success, error = registry.create_component(component)
        if success:
            logger.info(f"Created component: {component['name']}")
        else:
            logger.error(f"Failed to create component: {error}")
            return False
    
    # Test 2: Verify all test components exist
    logger.info("Test 2: Verifying test components exist")
    for component in test_components:
        comp = registry.get_component(component["component_id"])
        if not comp:
            logger.error(f"Component not found: {component['component_id']}")
            return False
    logger.info("All test components verified")
    
    # Test 3: Get component by ID
    logger.info("Test 3: Getting component by ID")
    component = registry.get_component("test-agent-1")
    if not component:
        logger.error("Failed to get component by ID")
        return False
    logger.info(f"Got component: {component['name']}")
    
    # Test 4: Update component
    logger.info("Test 4: Updating component")
    updates = {
        "description": "Updated test agent component",
        "tags": ["test", "agent", "experimental", "updated"]
    }
    success, error = registry.update_component("test-agent-1", updates)
    if not success:
        logger.error(f"Failed to update component: {error}")
        return False
    
    # Verify update
    component = registry.get_component("test-agent-1")
    if component["description"] != updates["description"]:
        logger.error("Update failed: description not updated")
        return False
    logger.info("Component updated successfully")
    
    # Test 5: Search components
    logger.info("Test 5: Searching components by type")
    service_components = registry.search_components(filters={"type": "service", "owner_agent": "agent-5"})
    service_count = 0
    for comp_id, comp in service_components.items():
        if comp_id == "test-service-1":
            service_count += 1
    
    if service_count != 1:
        logger.error(f"Expected 1 service test component, got {service_count}")
        return False
    logger.info(f"Found {service_count} service test components")
    
    # Test 6: Filter by tags
    logger.info("Test 6: Filtering by tags")
    tool_components = registry.search_components(filters={"type": "tool"}, tags=["test", "tool"])
    tool_count = 0
    for comp_id, comp in tool_components.items():
        if comp_id == "test-tool-1":
            tool_count += 1
    
    if tool_count != 1:
        logger.error(f"Expected 1 tool test component, got {tool_count}")
        return False
    logger.info(f"Found {tool_count} tool test components")
    
    # Test 7: Delete component
    logger.info("Test 7: Deleting component")
    success, error = registry.delete_component("test-tool-1")
    if not success:
        logger.error(f"Failed to delete component: {error}")
        return False
    
    # Verify deletion
    component = registry.get_component("test-tool-1")
    if component:
        logger.error("Component still exists after deletion")
        return False
    logger.info("Component deleted successfully")
    
    # Test 8: Create component with invalid data
    logger.info("Test 8: Creating component with invalid data")
    invalid_component = {
        "component_id": "invalid-component",
        "name": "Invalid Component",
        "description": "A component with invalid data",
        "type": "invalid-type"  # Invalid type
    }
    success, error = registry.create_component(invalid_component)
    if success:
        logger.error("Created component with invalid data")
        # Clean up if it somehow succeeded
        registry.delete_component("invalid-component")
        return False
    logger.info(f"Validation worked: {error}")
    
    # Test 9: Backup and restore
    logger.info("Test 9: Testing backup and restore")
    # Get current state before test
    current_state = registry.get_all_components()
    target_test_components = ["test-agent-1", "test-service-1"]  # test-tool-1 was deleted
    
    # Create backup
    registry._create_backup()
    
    # Add a new component
    new_component = {
        "component_id": "temporary-component",
        "name": "Temporary Component",
        "description": "This component will be removed after restore",
        "entry_point": "src/dreamos/tools/temp.py",
        "type": "tool",
        "owner_agent": "agent-5"
    }
    success, _ = registry.create_component(new_component)
    if not success:
        logger.error("Failed to add temporary component")
        return False
    
    # Verify new component was added
    if not registry.get_component("temporary-component"):
        logger.error("Temporary component not found after adding")
        return False
    
    # Restore backup
    success, error = registry.restore_backup()
    if not success:
        logger.error(f"Failed to restore backup: {error}")
        return False
    
    # Verify state was restored
    for comp_id in target_test_components:
        if not registry.get_component(comp_id):
            logger.error(f"Test component {comp_id} missing after restore")
            return False
    
    # Verify temporary component was removed
    if registry.get_component("temporary-component"):
        logger.error("Temporary component still exists after restore")
        return False
    
    logger.info("Backup and restore successful")
    
    # Clean up - delete remaining test components
    logger.info("Cleaning up test components")
    for component in test_components:
        registry.delete_component(component["component_id"])
    
    # Verify we're back to the initial state
    final_component_count = len(registry.get_all_components())
    logger.info(f"Final component count: {final_component_count}")
    
    logger.info("All tests passed successfully")
    return True


if __name__ == "__main__":
    if test_registry():
        print("Registry API implementation verified successfully")
        sys.exit(0)
    else:
        print("Registry API tests failed")
        sys.exit(1) 