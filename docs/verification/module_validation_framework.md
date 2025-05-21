# Module Validation Framework

**Version:** 0.1.0  
**Status:** IMPLEMENTATION  
**Created:** 2024-07-30  
**Author:** Agent-8 (Testing & Validation Engineer)

## Overview

This framework provides a standardized approach for validating bridge modules within Dream.OS, focusing on interface compliance, error handling, and integration testing. The framework builds upon the techniques used in Module 3 (Logging + Error Handler) to provide consistent validation across all bridge modules.

## Design Goals

1. **Interface Compliance Validation**
   - Verify modules implement required interfaces
   - Validate parameter types and return values
   - Ensure consistent API patterns across modules

2. **Error Handling Validation**
   - Test module behavior with malformed inputs
   - Verify error propagation and handling
   - Validate recursion depth protections
   - Test recovery mechanisms

3. **Integration Testing**
   - Verify module interactions
   - Test cross-module dependencies
   - Validate end-to-end workflows

## Required Components

### 1. Module Interface Specification

The framework will define standard interface specifications for bridge modules:

```python
class ModuleInterfaceSpec:
    """Definition of a module interface specification."""
    
    def __init__(self, name, methods=None, events=None, properties=None):
        self.name = name
        self.methods = methods or []
        self.events = events or []
        self.properties = properties or []
        
    def add_method(self, name, parameters=None, return_type=None, required=True):
        """Add a method to the interface specification."""
        self.methods.append({
            "name": name,
            "parameters": parameters or [],
            "return_type": return_type,
            "required": required
        })
        
    def add_event(self, name, parameters=None, required=True):
        """Add an event to the interface specification."""
        self.events.append({
            "name": name,
            "parameters": parameters or [],
            "required": required
        })
        
    def add_property(self, name, type_info, required=True):
        """Add a property to the interface specification."""
        self.properties.append({
            "name": name,
            "type": type_info,
            "required": required
        })
        
    def to_dict(self):
        """Convert the interface specification to a dictionary."""
        return {
            "name": self.name,
            "methods": self.methods,
            "events": self.events,
            "properties": self.properties
        }
        
    @classmethod
    def from_dict(cls, data):
        """Create an interface specification from a dictionary."""
        spec = cls(data["name"])
        spec.methods = data.get("methods", [])
        spec.events = data.get("events", [])
        spec.properties = data.get("properties", [])
        return spec
        
    def validate_module(self, module):
        """Validate that a module implements this interface."""
        results = {
            "name": self.name,
            "module": module.__name__,
            "valid": True,
            "missing_methods": [],
            "missing_events": [],
            "missing_properties": [],
            "invalid_methods": [],
            "invalid_events": [],
            "invalid_properties": []
        }
        
        # Validate methods
        for method in self.methods:
            if method["required"] and not hasattr(module, method["name"]):
                results["missing_methods"].append(method["name"])
                results["valid"] = False
            elif hasattr(module, method["name"]) and not callable(getattr(module, method["name"])):
                results["invalid_methods"].append(method["name"])
                results["valid"] = False
        
        # Validate properties
        for prop in self.properties:
            if prop["required"] and not hasattr(module, prop["name"]):
                results["missing_properties"].append(prop["name"])
                results["valid"] = False
        
        # Events validation would need to be customized based on the event system
        
        return results
```

### 2. Module Validator

The framework will include a validator to test module implementations:

```python
class ModuleValidator:
    """Validate module implementations against interface specifications."""
    
    def __init__(self, specs_dir=None):
        self.specs_dir = specs_dir or os.path.join("docs", "specs", "modules")
        self.specs = {}
        self.results = {}
        
    def load_specifications(self):
        """Load all module interface specifications."""
        if not os.path.exists(self.specs_dir):
            raise FileNotFoundError(f"Specifications directory not found: {self.specs_dir}")
            
        for file_name in os.listdir(self.specs_dir):
            if file_name.endswith(".json"):
                file_path = os.path.join(self.specs_dir, file_name)
                with open(file_path, "r") as f:
                    spec_data = json.load(f)
                    spec = ModuleInterfaceSpec.from_dict(spec_data)
                    self.specs[spec.name] = spec
                    
        return self.specs
        
    def validate_module(self, module, spec_name=None):
        """Validate a module against its interface specification."""
        if spec_name is None:
            spec_name = module.__name__.split(".")[-1]
            
        if spec_name not in self.specs:
            if len(self.specs) == 0:
                self.load_specifications()
            if spec_name not in self.specs:
                raise ValueError(f"No specification found for module: {spec_name}")
                
        spec = self.specs[spec_name]
        results = spec.validate_module(module)
        self.results[spec_name] = results
        return results
        
    def validate_error_handling(self, module, spec_name=None):
        """Validate a module's error handling capabilities."""
        if spec_name is None:
            spec_name = module.__name__.split(".")[-1]
            
        results = {
            "name": spec_name,
            "module": module.__name__,
            "tests": []
        }
        
        # Get methods to test
        methods = []
        if spec_name in self.specs:
            spec = self.specs[spec_name]
            methods = [m["name"] for m in spec.methods if m["required"]]
        else:
            methods = [name for name in dir(module) if callable(getattr(module, name)) and not name.startswith("_")]
            
        # Test each method with malformed inputs
        for method_name in methods:
            method = getattr(module, method_name)
            method_results = self._test_method_error_handling(method)
            results["tests"].append({
                "method": method_name,
                "results": method_results
            })
            
        self.results[f"{spec_name}_error_handling"] = results
        return results
        
    def _test_method_error_handling(self, method):
        """Test a method's error handling with malformed inputs."""
        # This needs to be customized based on the method signature
        results = {
            "null_input": {"success": False, "error": None},
            "malformed_input": {"success": False, "error": None},
            "excessive_input": {"success": False, "error": None}
        }
        
        # Test with null input
        try:
            method(None)
            results["null_input"]["success"] = True
        except Exception as e:
            results["null_input"]["error"] = str(e)
            
        # Other tests would be customized based on the method signature
        
        return results
        
    def generate_report(self):
        """Generate a report of validation results."""
        if not self.results:
            return "No validation results available"
            
        report = []
        report.append("# Module Validation Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Interface validation results
        interface_results = {k: v for k, v in self.results.items() if not k.endswith("_error_handling")}
        if interface_results:
            report.append("## Interface Compliance")
            for spec_name, results in interface_results.items():
                report.append(f"### {spec_name}")
                valid_str = "✅ Valid" if results["valid"] else "❌ Invalid"
                report.append(f"Status: {valid_str}")
                report.append(f"Module: {results['module']}")
                
                if results["missing_methods"]:
                    report.append("\n#### Missing Methods")
                    for method in results["missing_methods"]:
                        report.append(f"- {method}")
                        
                if results["invalid_methods"]:
                    report.append("\n#### Invalid Methods")
                    for method in results["invalid_methods"]:
                        report.append(f"- {method}")
                        
                if results["missing_properties"]:
                    report.append("\n#### Missing Properties")
                    for prop in results["missing_properties"]:
                        report.append(f"- {prop}")
                        
                if results["invalid_properties"]:
                    report.append("\n#### Invalid Properties")
                    for prop in results["invalid_properties"]:
                        report.append(f"- {prop}")
                        
                report.append("")
                
        # Error handling results
        error_results = {k: v for k, v in self.results.items() if k.endswith("_error_handling")}
        if error_results:
            report.append("## Error Handling")
            for spec_name, results in error_results.items():
                module_name = spec_name.replace("_error_handling", "")
                report.append(f"### {module_name}")
                report.append(f"Module: {results['module']}")
                
                for test in results["tests"]:
                    report.append(f"\n#### {test['method']}")
                    for test_name, test_result in test["results"].items():
                        status = "✅ Pass" if test_result["success"] else "❌ Fail"
                        error = f": {test_result['error']}" if test_result["error"] else ""
                        report.append(f"- {test_name}: {status}{error}")
                        
                report.append("")
                
        return "\n".join(report)
```

### 3. Integration Test Runner

The framework will include a runner for integration tests between modules:

```python
class ModuleIntegrationTester:
    """Run integration tests between modules."""
    
    def __init__(self, tests_dir=None):
        self.tests_dir = tests_dir or os.path.join("tests", "integration")
        self.tests = {}
        self.results = {}
        
    def load_tests(self):
        """Load all integration tests."""
        if not os.path.exists(self.tests_dir):
            raise FileNotFoundError(f"Tests directory not found: {self.tests_dir}")
            
        for file_name in os.listdir(self.tests_dir):
            if file_name.endswith(".json"):
                file_path = os.path.join(self.tests_dir, file_name)
                with open(file_path, "r") as f:
                    test_data = json.load(f)
                    self.tests[test_data["name"]] = test_data
                    
        return self.tests
        
    def run_test(self, test_name):
        """Run a specific integration test."""
        if test_name not in self.tests:
            if len(self.tests) == 0:
                self.load_tests()
            if test_name not in self.tests:
                raise ValueError(f"No test found with name: {test_name}")
                
        test = self.tests[test_name]
        results = {
            "name": test["name"],
            "modules": test["modules"],
            "steps": [],
            "success": True
        }
        
        # Import modules
        modules = {}
        for module_name in test["modules"]:
            try:
                # This will need to be customized based on the module import pattern
                module = importlib.import_module(f"dreamos.{module_name}")
                modules[module_name] = module
            except ImportError as e:
                results["steps"].append({
                    "type": "import",
                    "module": module_name,
                    "success": False,
                    "error": str(e)
                })
                results["success"] = False
                
        # Skip test if modules couldn't be imported
        if not results["success"]:
            self.results[test_name] = results
            return results
            
        # Run test steps
        for step in test["steps"]:
            step_result = self._run_test_step(step, modules)
            results["steps"].append(step_result)
            if not step_result["success"]:
                results["success"] = False
                
        self.results[test_name] = results
        return results
        
    def _run_test_step(self, step, modules):
        """Run a single test step."""
        step_type = step["type"]
        step_result = {
            "type": step_type,
            "success": False,
            "error": None
        }
        
        try:
            if step_type == "call":
                module_name = step["module"]
                method_name = step["method"]
                args = step.get("args", [])
                kwargs = step.get("kwargs", {})
                
                if module_name not in modules:
                    step_result["error"] = f"Module not found: {module_name}"
                    return step_result
                    
                module = modules[module_name]
                if not hasattr(module, method_name):
                    step_result["error"] = f"Method not found: {method_name}"
                    return step_result
                    
                method = getattr(module, method_name)
                result = method(*args, **kwargs)
                
                # Check expected result if provided
                if "expected" in step:
                    expected = step["expected"]
                    if result != expected:
                        step_result["error"] = f"Expected result {expected}, got {result}"
                        return step_result
                        
                step_result["success"] = True
                step_result["result"] = result
                
            elif step_type == "check":
                module_name = step["module"]
                property_name = step["property"]
                expected = step["expected"]
                
                if module_name not in modules:
                    step_result["error"] = f"Module not found: {module_name}"
                    return step_result
                    
                module = modules[module_name]
                if not hasattr(module, property_name):
                    step_result["error"] = f"Property not found: {property_name}"
                    return step_result
                    
                actual = getattr(module, property_name)
                if actual != expected:
                    step_result["error"] = f"Expected {expected}, got {actual}"
                    return step_result
                    
                step_result["success"] = True
                
            else:
                step_result["error"] = f"Unknown step type: {step_type}"
                
        except Exception as e:
            step_result["error"] = str(e)
            
        return step_result
        
    def run_all_tests(self):
        """Run all integration tests."""
        if len(self.tests) == 0:
            self.load_tests()
            
        results = {}
        for test_name in self.tests:
            results[test_name] = self.run_test(test_name)
            
        return results
        
    def generate_report(self):
        """Generate a report of integration test results."""
        if not self.results:
            return "No integration test results available"
            
        report = []
        report.append("# Module Integration Test Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        success_count = sum(1 for r in self.results.values() if r["success"])
        total_count = len(self.results)
        
        report.append("## Summary")
        report.append(f"- Total Tests: {total_count}")
        report.append(f"- Successful Tests: {success_count}")
        report.append(f"- Failed Tests: {total_count - success_count}")
        report.append(f"- Success Rate: {success_count / total_count * 100:.2f}%\n")
        
        for test_name, results in self.results.items():
            status = "✅ Pass" if results["success"] else "❌ Fail"
            report.append(f"## {test_name} ({status})")
            report.append(f"Modules: {', '.join(results['modules'])}")
            
            for step in results["steps"]:
                step_type = step["type"]
                step_status = "✅ Pass" if step["success"] else "❌ Fail"
                
                if step_type == "import":
                    report.append(f"- Import {step['module']}: {step_status}")
                    if not step["success"]:
                        report.append(f"  - Error: {step['error']}")
                        
                elif step_type == "call":
                    method_str = f"{step.get('module', '')}.{step.get('method', '')}"
                    report.append(f"- Call {method_str}: {step_status}")
                    if not step["success"]:
                        report.append(f"  - Error: {step['error']}")
                    elif "result" in step:
                        report.append(f"  - Result: {step['result']}")
                        
                elif step_type == "check":
                    property_str = f"{step.get('module', '')}.{step.get('property', '')}"
                    report.append(f"- Check {property_str}: {step_status}")
                    if not step["success"]:
                        report.append(f"  - Error: {step['error']}")
                        
            report.append("")
            
        return "\n".join(report)
```

## Implementation Strategy

### 1. Module 3 Reference Integration

The Module 3 (Logging + Error Handler) will serve as the reference implementation for the Module Validation Framework. The error patterns and validation methodology from Module 3 will be extracted and generalized to apply to all bridge modules.

Key components to reuse from Module 3:
- Error classification system
- Input validation patterns
- Interface definition approach
- Testing methodology

### 2. Interface Specification Format

The Module Interface Specifications will be stored in JSON format with the following structure:

```json
{
  "name": "module_name",
  "methods": [
    {
      "name": "method_name",
      "parameters": [
        {"name": "param1", "type": "string", "required": true},
        {"name": "param2", "type": "object", "required": false}
      ],
      "return_type": "object",
      "required": true
    }
  ],
  "events": [
    {
      "name": "event_name",
      "parameters": [
        {"name": "param1", "type": "string", "required": true}
      ],
      "required": true
    }
  ],
  "properties": [
    {
      "name": "property_name",
      "type": "string",
      "required": true
    }
  ]
}
```

### 3. Integration Test Format

The Integration Tests will be stored in JSON format with the following structure:

```json
{
  "name": "test_name",
  "modules": ["module1", "module2"],
  "steps": [
    {
      "type": "call",
      "module": "module1",
      "method": "method_name",
      "args": ["arg1", "arg2"],
      "kwargs": {"param1": "value1"},
      "expected": "expected_result"
    },
    {
      "type": "check",
      "module": "module2",
      "property": "property_name",
      "expected": "expected_value"
    }
  ]
}
```

## Implementation Plan

1. **Phase 1: Interface Specification**
   - Create interface specifications for all bridge modules
   - Implement the ModuleInterfaceSpec class
   - Develop the ModuleValidator class

2. **Phase 2: Error Handling Validation**
   - Extract error patterns from Module 3
   - Implement error handling test cases
   - Create validation methodology for error handling

3. **Phase 3: Integration Testing**
   - Implement the ModuleIntegrationTester class
   - Create integration test specifications
   - Develop reporting mechanisms

## Integration with Other Frameworks

1. **Tool Reliability Framework**
   - Share validation methodology
   - Reuse reporting mechanisms
   - Integrate metrics collection

2. **Protocol Verification Framework**
   - Coordinate on interface validation
   - Share state transition validation
   - Integrate reporting formats

## Module Validation Dashboard

The framework will include a validation dashboard that provides an overview of the validation status for all bridge modules:

```
# Module Validation Dashboard
Generated: 2024-07-30 10:00:00

## Bridge Module Status

| Module | Interface Compliance | Error Handling | Integration Tests | Overall |
|--------|---------------------|---------------|-------------------|---------|
| Module 1 | ✅ Pass | ✅ Pass | ✅ Pass | ✅ Pass |
| Module 2 | ✅ Pass | ⚠️ Partial | ✅ Pass | ⚠️ Partial |
| Module 3 | ✅ Pass | ✅ Pass | ✅ Pass | ✅ Pass |
| Module 5 | ❌ Fail | ⚠️ Partial | ❌ Fail | ❌ Fail |
| Module 6 | ⚠️ Partial | ⚠️ Partial | ✅ Pass | ⚠️ Partial |
| Module 8 | ✅ Pass | ✅ Pass | ✅ Pass | ✅ Pass |

## Error Summary

- Module 2: 2 error handling issues in method_name
- Module 5: Missing required method method_name
- Module 6: Invalid parameter type in method_name
```

## Next Steps

1. Review Module 3 implementation to extract validation patterns
2. Create interface specifications for all bridge modules
3. Implement the ModuleValidator class
4. Develop integration test specifications
5. Create the validation dashboard

## Dependencies

1. Module 3 error handling patterns (from `knurlshade_module3_completion_report.json`)
2. Bridge module interface documentation
3. Integration test cases for bridge modules 