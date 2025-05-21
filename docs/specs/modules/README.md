# Module Specifications

This directory contains interface specifications for Dream.OS bridge modules. These specifications are used by the Module Validation Framework to validate that module implementations conform to their expected interfaces.

## Specification Format

Module specifications are stored in JSON files with the following structure:

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

## Creating a New Specification

To create a new module specification, you can use the `ModuleInterfaceSpec` class from the Module Validation Framework:

```python
from dreamos.testing.module_validation.interface_spec import ModuleInterfaceSpec

# Create a new specification
spec = ModuleInterfaceSpec("module_name")

# Add methods
spec.add_method(
    "method_name",
    parameters=[
        {"name": "param1", "type": "string", "required": True},
        {"name": "param2", "type": "object", "required": False}
    ],
    return_type="object",
    required=True
)

# Add events
spec.add_event(
    "event_name",
    parameters=[
        {"name": "param1", "type": "string", "required": True}
    ],
    required=True
)

# Add properties
spec.add_property(
    "property_name",
    type_info="string",
    required=True
)

# Save the specification to a file
spec.save_to_file("docs/specs/modules/module_name.json")
```

## Using Specifications

Module specifications are used by the Module Validation Framework to validate that module implementations conform to their expected interfaces. You can use the `ModuleValidator` class to validate a module:

```python
from dreamos.testing.module_validation.validator import ModuleValidator
import my_module

# Create a validator
validator = ModuleValidator()

# Validate a module
results = validator.validate_module(my_module)

# Check validation results
if results["valid"]:
    print("Module is valid!")
else:
    print("Module is invalid!")
    print("Missing methods:", results["missing_methods"])
    print("Invalid methods:", results["invalid_methods"])
    print("Missing properties:", results["missing_properties"])
    print("Invalid properties:", results["invalid_properties"])
``` 