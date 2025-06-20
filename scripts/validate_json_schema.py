#!/usr/bin/env python
"""
JSON Schema Validator for Dream.OS

This tool validates JSON files against predefined schemas, ensuring data consistency 
across the Dream.OS ecosystem.

Usage:
    python validate_json_schema.py <file_or_directory_path> [--schema <schema_name>]

Examples:
    python validate_json_schema.py runtime/tasks/future_tasks.json
    python validate_json_schema.py runtime/tasks/ --schema task
"""

import json
import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple


# Task JSON schema definition
TASK_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["task_id", "description", "status"],
        "properties": {
            "task_id": {"type": "string"},
            "description": {"type": "string"},
            "status": {"type": "string", "enum": ["PENDING", "IN_PROGRESS", "COMPLETED", "BLOCKED", "CANCELED"]},
            "priority": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
            "assignee_suggestion": {"type": "string"},
            "assigned_to": {"type": "string"},
            "created_by": {"type": "string"},
            "created_at": {"type": "string"},
            "updated_at": {"type": "string"},
            "outcome": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "dependencies": {"type": "array", "items": {"type": "string"}},
            "sub_tasks": {"type": "array", "items": {"type": "string"}},
            "details": {"type": "object"},
            "name": {"type": "string"},
            "title": {"type": "string"}
        },
        "additionalProperties": True
    }
}

# Episode JSON schema definition
EPISODE_TASK_SCHEMA = {
    "type": "object",
    "required": ["episode_id", "tasks"],
    "properties": {
        "episode_id": {"type": "string"},
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["task_id", "description", "agent"],
                "properties": {
                    "task_id": {"type": "string"},
                    "description": {"type": "string"},
                    "agent": {"type": "string"},
                    "status": {"type": "string"},
                    "dependencies": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    }
}

# Registry of all available schemas
SCHEMAS = {
    "task": TASK_SCHEMA,
    "episode_task": EPISODE_TASK_SCHEMA
}

class SchemaValidationError(Exception):
    """Exception raised for schema validation errors."""
    pass

def validate_json_against_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate JSON data against a schema.
    
    Args:
        data: JSON data to validate
        schema: Schema to validate against
        
    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []
    
    # Basic type validation
    if schema.get("type") == "array" and not isinstance(data, list):
        errors.append(f"Expected array, got {type(data).__name__}")
        return False, errors
    
    if schema.get("type") == "object" and not isinstance(data, dict):
        errors.append(f"Expected object, got {type(data).__name__}")
        return False, errors
    
    # Array validation
    if schema.get("type") == "array" and isinstance(data, list):
        item_schema = schema.get("items", {})
        for i, item in enumerate(data):
            if item_schema.get("type") == "object":
                # Check required fields
                for req_field in item_schema.get("required", []):
                    if req_field not in item:
                        errors.append(f"Item {i}: Missing required field '{req_field}'")
                
                # Check property types
                for prop_name, prop_value in item.items():
                    if prop_name in item_schema.get("properties", {}):
                        prop_schema = item_schema["properties"][prop_name]
                        
                        # Check enum values
                        if "enum" in prop_schema and prop_value not in prop_schema["enum"]:
                            errors.append(f"Item {i}: Field '{prop_name}' value '{prop_value}' not in allowed values: {prop_schema['enum']}")
                        
                        # Check types
                        if prop_schema.get("type") == "string" and not isinstance(prop_value, str):
                            errors.append(f"Item {i}: Field '{prop_name}' should be string, got {type(prop_value).__name__}")
                        
                        if prop_schema.get("type") == "array" and not isinstance(prop_value, list):
                            errors.append(f"Item {i}: Field '{prop_name}' should be array, got {type(prop_value).__name__}")
                        
                        if prop_schema.get("type") == "object" and not isinstance(prop_value, dict):
                            errors.append(f"Item {i}: Field '{prop_name}' should be object, got {type(prop_value).__name__}")
    
    # Object validation
    if schema.get("type") == "object" and isinstance(data, dict):
        # Check required fields
        for req_field in schema.get("required", []):
            if req_field not in data:
                errors.append(f"Missing required field '{req_field}'")
        
        # Validate properties
        for prop_name, prop_value in data.items():
            if prop_name in schema.get("properties", {}):
                prop_schema = schema["properties"][prop_name]
                
                # Recursively validate nested objects
                if prop_schema.get("type") == "object" and isinstance(prop_value, dict):
                    is_valid, nested_errors = validate_json_against_schema(prop_value, prop_schema)
                    if not is_valid:
                        errors.extend([f"In '{prop_name}': {err}" for err in nested_errors])
                
                # Validate arrays
                if prop_schema.get("type") == "array" and isinstance(prop_value, list):
                    if "items" in prop_schema:
                        item_schema = prop_schema["items"]
                        for i, item in enumerate(prop_value):
                            if item_schema.get("type") == "object" and isinstance(item, dict):
                                is_valid, nested_errors = validate_json_against_schema(item, item_schema)
                                if not is_valid:
                                    errors.extend([f"In '{prop_name}[{i}]': {err}" for err in nested_errors])
    
    return len(errors) == 0, errors

def detect_schema_type(file_path: Path) -> str:
    """
    Auto-detect schema type based on file path or content.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Detected schema type
    """
    name = file_path.name.lower()
    
    if "task" in name or name in ["future_tasks.json", "working_tasks.json", "completed_tasks.json"]:
        return "task"
    
    if "episode" in name and "parsed" in name:
        return "episode_task"
    
    # Default to task schema
    return "task"

def validate_file(file_path: Path, schema_name: Optional[str] = None) -> bool:
    """
    Validate a single JSON file against a schema.
    
    Args:
        file_path: Path to the JSON file
        schema_name: Name of schema to use (auto-detected if not provided)
        
    Returns:
        True if validation passed, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ {file_path}: Invalid JSON - {str(e)}")
        return False
    except Exception as e:
        print(f"❌ {file_path}: Error reading file - {str(e)}")
        return False
    
    # Auto-detect schema if not provided
    if not schema_name:
        schema_name = detect_schema_type(file_path)
    
    if schema_name not in SCHEMAS:
        print(f"❌ {file_path}: Unknown schema '{schema_name}'")
        return False
    
    schema = SCHEMAS[schema_name]
    is_valid, errors = validate_json_against_schema(data, schema)
    
    if is_valid:
        print(f"✅ {file_path}: Valid {schema_name} schema")
        return True
    else:
        print(f"❌ {file_path}: Schema validation failed")
        for error in errors:
            print(f"   - {error}")
        return False

def validate_directory(dir_path: Path, schema_name: Optional[str] = None) -> Tuple[int, int]:
    """
    Validate all JSON files in a directory.
    
    Args:
        dir_path: Path to directory
        schema_name: Name of schema to use (auto-detected if not provided)
        
    Returns:
        Tuple of (valid_count, invalid_count)
    """
    valid_count = 0
    invalid_count = 0
    
    for file_path in dir_path.glob("**/*.json"):
        if validate_file(file_path, schema_name):
            valid_count += 1
        else:
            invalid_count += 1
    
    return valid_count, invalid_count

def main():
    parser = argparse.ArgumentParser(description="Validate JSON files against predefined schemas")
    parser.add_argument("path", help="Path to JSON file or directory to validate")
    parser.add_argument("--schema", help="Schema to validate against (task, episode_task)")
    
    args = parser.parse_args()
    path = Path(args.path)
    
    if not path.exists():
        print(f"Error: Path '{path}' does not exist")
        sys.exit(1)
    
    print(f"🔍 Validating {path}")
    
    if path.is_file():
        if validate_file(path, args.schema):
            print("✅ Validation succeeded")
            sys.exit(0)
        else:
            print("❌ Validation failed")
            sys.exit(1)
    
    elif path.is_dir():
        valid_count, invalid_count = validate_directory(path, args.schema)
        total = valid_count + invalid_count
        
        print(f"📊 Validation summary: {valid_count}/{total} files valid")
        
        if invalid_count > 0:
            print(f"❌ {invalid_count} files failed validation")
            sys.exit(1)
        else:
            print("✅ All files valid")
            sys.exit(0)

if __name__ == "__main__":
    main() 