# Module Validation Framework

A framework for validating Dream.OS bridge modules, focusing on interface compliance, error handling, and integration testing.

## Overview

The Module Validation Framework provides a standardized approach for validating bridge modules within Dream.OS. It ensures that modules implement the required interfaces, handle errors correctly, and interact with other modules as expected.

## Components

The framework consists of the following components:

- **ModuleInterfaceSpec**: Defines the expected interface for a module, including its methods, events, and properties.
- **ModuleValidator**: Validates a module against its interface specification and tests its error handling capabilities.
- **ModuleIntegrationTester**: Runs integration tests between modules to validate their interactions.
- **ModuleValidationDashboard**: Provides a dashboard for visualizing validation results across modules.

## Usage

### Command-Line Interface

The framework provides a command-line interface for running validations, integration tests, and generating reports:

```
# Validate modules
python -m dreamos.testing.module_validation validate --modules module1 module2 [--specs-dir docs/specs/modules] [--output-dir logs/validation]

# Run integration tests
python -m dreamos.testing.module_validation integration [--tests test1 test2] [--tests-dir tests/integration] [--output-dir logs/integration]

# Generate dashboard
python -m dreamos.testing.module_validation dashboard [--validation-results logs/validation/validation_results.json] [--integration-results logs/integration/integration_results.json] [--output-dir logs/module_validation]

# Run all validations and generate dashboard
python -m dreamos.testing.module_validation all --modules module1 module2 [--specs-dir docs/specs/modules] [--tests-dir tests/integration] [--output-dir logs/module_validation]
```

### Python API

You can also use the framework programmatically:

```python
from dreamos.testing.module_validation.interface_spec import ModuleInterfaceSpec
from dreamos.testing.module_validation.validator import ModuleValidator
from dreamos.testing.module_validation.integration import ModuleIntegrationTester
from dreamos.testing.module_validation.dashboard import ModuleValidationDashboard

# Create interface specifications
spec = ModuleInterfaceSpec("module_name")
spec.add_method("method_name", parameters=[{"name": "param1", "type": "string", "required": True}])
spec.save_to_file("docs/specs/modules/module_name.json")

# Validate modules
validator = ModuleValidator()
results = validator.validate_module(my_module)

# Run integration tests
tester = ModuleIntegrationTester()
test = tester.create_test("test_name", ["module1", "module2"])
tester.add_call_step("test_name", module="module1", method="method_name")
tester.save_test("test_name")
results = tester.run_test("test_name")

# Generate dashboard
dashboard = ModuleValidationDashboard()
dashboard.set_validation_status("module1", "Pass", results)
dashboard.generate_dashboard()
dashboard.save_dashboard()
```

## Directory Structure

The framework expects the following directory structure:

```
- docs/
  - specs/
    - modules/      # Module interface specifications
- tests/
  - integration/    # Integration tests
- logs/
  - validation/     # Validation reports
  - integration/    # Integration test reports
  - module_validation/ # Dashboard reports
```

## Documentation

For more information on using the framework, see the following documentation:

- [Module Specifications](../../docs/specs/modules/README.md)
- [Integration Tests](../../tests/integration/README.md)
- [Module Validation Framework Design](../../docs/verification/module_validation_framework.md) 