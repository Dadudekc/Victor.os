"""
Validator for Module Validation Framework.

This module provides validation capabilities for the Module Validation
Framework, verifying that modules implement the required interfaces.
"""

import os
import sys
import json
import time
import importlib
import inspect
from typing import Dict, Any, List, Optional

from dreamos.testing.module_validation.interface_spec import ModuleInterfaceSpec

class ModuleValidator:
    """
    Validator for the Module Validation Framework.
    
    This class validates that modules implement the required interfaces
    defined in interface specifications.
    """
    
    def __init__(self, specs_dir: Optional[str] = None):
        """
        Initialize the validator.
        
        Args:
            specs_dir: Directory containing interface specifications
        """
        self.specs_dir = specs_dir or "docs/specs/modules"
        self.specs = {}
        self.results = {}
    
    def load_specifications(self):
        """
        Load all interface specifications from the specifications directory.
        
        Raises:
            FileNotFoundError: If the specifications directory does not exist
        """
        if not os.path.exists(self.specs_dir):
            raise FileNotFoundError(f"Specifications directory not found: {self.specs_dir}")
        
        # Load all JSON files in the specifications directory
        for filename in os.listdir(self.specs_dir):
            if filename.endswith(".json"):
                try:
                    file_path = os.path.join(self.specs_dir, filename)
                    with open(file_path, "r") as f:
                        spec_data = json.load(f)
                    
                    # Create a ModuleInterfaceSpec from the JSON data
                    spec = ModuleInterfaceSpec.from_dict(spec_data)
                    self.specs[spec.name] = spec
                except Exception as e:
                    print(f"Error loading specification {filename}: {str(e)}")
    
    def validate_module(self, module, spec_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate a module against its interface specification.
        
        Args:
            module: Module to validate
            spec_name: Name of the specification to validate against
                      (default: derive from module name)
            
        Returns:
            dict: Validation results
        """
        if spec_name is None:
            # Try to derive spec name from module name
            if hasattr(module, "__name__"):
                module_path = module.__name__.split(".")
                spec_name = module_path[-1]
            else:
                raise ValueError("No specification name provided and could not derive from module")
        
        if spec_name not in self.specs:
            # Try to load specifications if not already loaded
            if not self.specs:
                self.load_specifications()
            
            if spec_name not in self.specs:
                return {
                    "valid": False,
                    "error": f"No specification found for module: {spec_name}"
                }
        
        spec = self.specs[spec_name]
        results = {
            "valid": True,
            "module": spec_name,
            "missing_methods": [],
            "invalid_methods": [],
            "missing_properties": [],
            "invalid_properties": []
        }
        
        # Check required methods
        for method_name, method_spec in spec.methods.items():
            if not hasattr(module, method_name):
                if method_spec.get("required", False):
                    results["valid"] = False
                    results["missing_methods"].append(method_name)
            else:
                method = getattr(module, method_name)
                if not callable(method):
                    results["valid"] = False
                    results["invalid_methods"].append(method_name)
                else:
                    # Check method signature
                    try:
                        sig = inspect.signature(method)
                        # Additional method validation could be added here
                    except (ValueError, TypeError):
                        # Can't get signature, but method exists
                        pass
        
        # Check required properties (if any)
        for prop_name, prop_spec in spec.properties.items() if hasattr(spec, "properties") else {}:
            if not hasattr(module, prop_name):
                if prop_spec.get("required", False):
                    results["valid"] = False
                    results["missing_properties"].append(prop_name)
            else:
                prop = getattr(module, prop_name)
                # Check property type
                if "type" in prop_spec:
                    prop_type = prop_spec["type"]
                    if prop_type == "str" and not isinstance(prop, str):
                        results["valid"] = False
                        results["invalid_properties"].append(prop_name)
                    elif prop_type == "int" and not isinstance(prop, int):
                        results["valid"] = False
                        results["invalid_properties"].append(prop_name)
                    elif prop_type == "float" and not isinstance(prop, (int, float)):
                        results["valid"] = False
                        results["invalid_properties"].append(prop_name)
                    elif prop_type == "bool" and not isinstance(prop, bool):
                        results["valid"] = False
                        results["invalid_properties"].append(prop_name)
                    elif prop_type == "dict" and not isinstance(prop, dict):
                        results["valid"] = False
                        results["invalid_properties"].append(prop_name)
                    elif prop_type == "list" and not isinstance(prop, list):
                        results["valid"] = False
                        results["invalid_properties"].append(prop_name)
        
        self.results[spec_name] = results
        return results
    
    def validate_all_modules(self, module_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Validate multiple modules.
        
        Args:
            module_names: List of module names to validate
            
        Returns:
            dict: Dictionary of validation results
        """
        results = {}
        
        for module_name in module_names:
            try:
                # Import the module
                module = importlib.import_module(f"dreamos.{module_name}")
                
                # Derive spec name from module name
                spec_name = module_name.split(".")[-1]
                
                # Validate the module
                results[spec_name] = self.validate_module(module, spec_name)
            except ImportError as e:
                results[module_name.split(".")[-1]] = {
                    "valid": False,
                    "error": f"Could not import module: {str(e)}"
                }
                
        self.results.update(results)
        return results
    
    def generate_report(self) -> str:
        """
        Generate a report of validation results.
        
        Returns:
            str: Report in markdown format
        """
        report = []
        report.append("# Module Validation Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not self.results:
            report.append("\nNo validation results available.")
            return "\n".join(report)
        
        # Summarize results
        total_modules = len(self.results)
        valid_modules = sum(1 for results in self.results.values() if results.get("valid", False))
        invalid_modules = total_modules - valid_modules
        
        report.append("\n## Summary")
        report.append(f"- Total modules: {total_modules}")
        report.append(f"- Valid modules: {valid_modules}")
        report.append(f"- Invalid modules: {invalid_modules}")
        report.append(f"- Compliance rate: {valid_modules / total_modules * 100:.2f}%")
        
        # Generate detailed results
        report.append("\n## Details")
        
        for module_name, results in sorted(self.results.items()):
            status = "✅ Pass" if results.get("valid", False) else "❌ Fail"
            report.append(f"\n### {module_name} ({status})")
            
            if "error" in results:
                report.append(f"**Error:** {results['error']}")
            else:
                # Check for missing methods
                missing_methods = results.get("missing_methods", [])
                if missing_methods:
                    report.append("\n#### Missing Methods")
                    for method in missing_methods:
                        report.append(f"- {method}")
                
                # Check for invalid methods
                invalid_methods = results.get("invalid_methods", [])
                if invalid_methods:
                    report.append("\n#### Invalid Methods")
                    for method in invalid_methods:
                        report.append(f"- {method}")
                
                # Check for missing properties
                missing_properties = results.get("missing_properties", [])
                if missing_properties:
                    report.append("\n#### Missing Properties")
                    for prop in missing_properties:
                        report.append(f"- {prop}")
                
                # Check for invalid properties
                invalid_properties = results.get("invalid_properties", [])
                if invalid_properties:
                    report.append("\n#### Invalid Properties")
                    for prop in invalid_properties:
                        report.append(f"- {prop}")
                
                if not missing_methods and not invalid_methods and not missing_properties and not invalid_properties:
                    report.append("\nAll required interfaces implemented correctly.")
        
        return "\n".join(report) 