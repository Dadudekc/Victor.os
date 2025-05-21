"""
Interface Specification for Module Validation Framework.

This module provides the interface specification capabilities for the Module Validation
Framework, allowing interfaces to be defined and validated.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Union, Callable, Type

class DataTypeValidator:
    """
    Validator for complex data types in module interfaces.
    
    This class provides validation for complex data types used in module
    interfaces, supporting nested structures, unions, and custom validation rules.
    """
    
    BASIC_TYPES = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "dict": dict,
        "list": list,
        "any": Any
    }
    
    @classmethod
    def validate_type(cls, value: Any, type_spec: Union[str, Dict[str, Any]]) -> bool:
        """
        Validate a value against a type specification.
        
        Args:
            value: Value to validate
            type_spec: Type specification (either a string or a dictionary)
            
        Returns:
            bool: True if valid, False if invalid
        """
        # Handle basic types
        if isinstance(type_spec, str):
            # Check for union types (e.g., "str|int")
            if "|" in type_spec:
                return any(cls.validate_type(value, t.strip()) for t in type_spec.split("|"))
            
            # Check for list types (e.g., "list[str]")
            list_match = re.match(r"list\[(.*)\]", type_spec)
            if list_match:
                item_type = list_match.group(1)
                return (isinstance(value, list) and 
                        all(cls.validate_type(item, item_type) for item in value))
            
            # Check for dict types (e.g., "dict[str, int]")
            dict_match = re.match(r"dict\[(.*), (.*)\]", type_spec)
            if dict_match:
                key_type, value_type = dict_match.group(1), dict_match.group(2)
                return (isinstance(value, dict) and
                        all(cls.validate_type(k, key_type) for k in value.keys()) and
                        all(cls.validate_type(v, value_type) for v in value.values()))
            
            # Check for basic types
            if type_spec in cls.BASIC_TYPES:
                if type_spec == "any":
                    return True
                return isinstance(value, cls.BASIC_TYPES[type_spec])
            
            # Unknown type
            return False
        
        # Handle complex type specifications (dictionaries)
        elif isinstance(type_spec, dict):
            # Check if it's a schema specification
            if "type" in type_spec:
                base_valid = cls.validate_type(value, type_spec["type"])
                
                # Additional validations
                if not base_valid:
                    return False
                
                # Range validation for numbers
                if type_spec["type"] in ["int", "float"] and isinstance(value, (int, float)):
                    if "min" in type_spec and value < type_spec["min"]:
                        return False
                    if "max" in type_spec and value > type_spec["max"]:
                        return False
                
                # Length validation for strings, lists, dicts
                if type_spec["type"] in ["str", "list", "dict"] and hasattr(value, "__len__"):
                    if "min_length" in type_spec and len(value) < type_spec["min_length"]:
                        return False
                    if "max_length" in type_spec and len(value) > type_spec["max_length"]:
                        return False
                
                # Pattern validation for strings
                if type_spec["type"] == "str" and "pattern" in type_spec and isinstance(value, str):
                    pattern = re.compile(type_spec["pattern"])
                    if not pattern.match(value):
                        return False
                
                # Enum validation
                if "enum" in type_spec and value not in type_spec["enum"]:
                    return False
                
                return True
            
            # Check if it's an object schema
            elif "properties" in type_spec:
                if not isinstance(value, dict):
                    return False
                
                # Check required properties
                required = type_spec.get("required", [])
                for prop in required:
                    if prop not in value:
                        return False
                
                # Check property types
                properties = type_spec["properties"]
                for prop_name, prop_value in value.items():
                    if prop_name in properties:
                        if not cls.validate_type(prop_value, properties[prop_name]):
                            return False
                    elif not type_spec.get("additional_properties", True):
                        # Additional properties not allowed
                        return False
                
                return True
            
            # Check if it's an array schema
            elif "items" in type_spec:
                if not isinstance(value, list):
                    return False
                
                # Check item types
                item_schema = type_spec["items"]
                for item in value:
                    if not cls.validate_type(item, item_schema):
                        return False
                
                # Check array length
                if "min_items" in type_spec and len(value) < type_spec["min_items"]:
                    return False
                if "max_items" in type_spec and len(value) > type_spec["max_items"]:
                    return False
                
                return True
            
            # Unknown schema type
            return False
        
        # Unsupported type specification
        return False

class ModuleInterfaceSpec:
    """
    Interface specification for the Module Validation Framework.
    
    This class represents an interface specification for a module, defining
    the required methods and properties.
    """
    
    def __init__(self, name: str, description: str = None, version: str = "0.1.0"):
        """
        Initialize the interface specification.
        
        Args:
            name: Name of the module
            description: Description of the module
            version: Version of the module
        """
        self.name = name
        self.description = description or f"Interface specification for {name}"
        self.version = version
        self.methods = {}
        self.properties = {}
        self.dependencies = []
        self.schema_version = "1.0"
    
    def add_method(self, name: str, parameters: List[Dict[str, Any]] = None, return_type: Union[str, Dict[str, Any]] = None, required: bool = True, deprecated: bool = False):
        """
        Add a method to the interface specification.
        
        Args:
            name: Name of the method
            parameters: List of parameter specifications
            return_type: Return type of the method
            required: Whether the method is required
            deprecated: Whether the method is deprecated
        """
        parameters = parameters or []
        self.methods[name] = {
            "description": f"Method {name} of {self.name}",
            "parameters": parameters,
            "return_type": return_type,
            "required": required,
            "deprecated": deprecated
        }
    
    def add_property(self, name: str, property_type: Union[str, Dict[str, Any]], required: bool = True, deprecated: bool = False):
        """
        Add a property to the interface specification.
        
        Args:
            name: Name of the property
            property_type: Type of the property
            required: Whether the property is required
            deprecated: Whether the property is deprecated
        """
        self.properties[name] = {
            "description": f"Property {name} of {self.name}",
            "type": property_type,
            "required": required,
            "deprecated": deprecated
        }
    
    def add_dependency(self, module_name: str, version_constraint: str = None):
        """
        Add a module dependency to the interface specification.
        
        Args:
            module_name: Name of the module dependency
            version_constraint: Version constraint for the dependency
        """
        self.dependencies.append({
            "module": module_name,
            "version_constraint": version_constraint
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the interface specification to a dictionary.
        
        Returns:
            dict: Dictionary representation of the interface specification
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "schema_version": self.schema_version,
            "methods": self.methods,
            "properties": self.properties,
            "dependencies": self.dependencies
        }
    
    def save_to_file(self, file_path: str) -> str:
        """
        Save the interface specification to a file.
        
        Args:
            file_path: Path to save the interface specification
            
        Returns:
            str: Path to the saved file
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "w") as f:
            json.dump(self.to_dict(), f, indent=4)
        
        return file_path
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModuleInterfaceSpec':
        """
        Create an interface specification from a dictionary.
        
        Args:
            data: Dictionary containing interface specification data
            
        Returns:
            ModuleInterfaceSpec: Interface specification
        """
        spec = cls(
            name=data["name"],
            description=data.get("description"),
            version=data.get("version", "0.1.0")
        )
        
        # Add schema version
        spec.schema_version = data.get("schema_version", "1.0")
        
        # Add methods
        for method_name, method_spec in data.get("methods", {}).items():
            spec.methods[method_name] = method_spec
        
        # Add properties
        for prop_name, prop_spec in data.get("properties", {}).items():
            spec.properties[prop_name] = prop_spec
        
        # Add dependencies
        spec.dependencies = data.get("dependencies", [])
        
        return spec
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'ModuleInterfaceSpec':
        """
        Load an interface specification from a file.
        
        Args:
            file_path: Path to the interface specification file
            
        Returns:
            ModuleInterfaceSpec: Interface specification
            
        Raises:
            FileNotFoundError: If the file does not exist
        """
        with open(file_path, "r") as f:
            data = json.load(f)
        
        return cls.from_dict(data)

    def validate_module(self, module):
        """
        Validate that a module implements this interface.
        
        Args:
            module: The module to validate
            
        Returns:
            dict: Validation results
        """
        results = {
            "name": self.name,
            "module": module.__name__,
            "valid": True,
            "missing_methods": [],
            "missing_properties": [],
            "invalid_methods": [],
            "invalid_properties": [],
            "deprecated_methods": [],
            "deprecated_properties": [],
            "schema_version": self.schema_version
        }
        
        # Validate methods
        for method_name, method_spec in self.methods.items():
            if method_spec.get("deprecated", False):
                if hasattr(module, method_name):
                    results["deprecated_methods"].append(method_name)
            
            if method_spec.get("required", False) and not hasattr(module, method_name):
                results["missing_methods"].append(method_name)
                results["valid"] = False
            elif hasattr(module, method_name) and not callable(getattr(module, method_name)):
                results["invalid_methods"].append(method_name)
                results["valid"] = False
        
        # Validate properties
        for prop_name, prop_spec in self.properties.items():
            if prop_spec.get("deprecated", False):
                if hasattr(module, prop_name):
                    results["deprecated_properties"].append(prop_name)
            
            if prop_spec.get("required", False) and not hasattr(module, prop_name):
                results["missing_properties"].append(prop_name)
                results["valid"] = False
            elif hasattr(module, prop_name):
                prop = getattr(module, prop_name)
                prop_type = prop_spec.get("type")
                
                if prop_type and not DataTypeValidator.validate_type(prop, prop_type):
                    results["invalid_properties"].append(prop_name)
                    results["valid"] = False
        
        return results 