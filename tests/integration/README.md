# Integration Tests

This directory contains integration tests for Dream.OS bridge modules. These tests are used by the Module Validation Framework to validate interactions between modules and ensure they work together correctly.

## Test Format

Integration tests are stored in JSON files with the following structure:

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

## Creating a New Test

To create a new integration test, you can use the `ModuleIntegrationTester` class from the Module Validation Framework:

```python
from dreamos.testing.module_validation.integration import ModuleIntegrationTester

# Create a new tester
tester = ModuleIntegrationTester()

# Create a new test
test = tester.create_test("test_name", ["module1", "module2"])

# Add a call step
tester.add_call_step(
    "test_name",
    module="module1",
    method="method_name",
    args=["arg1", "arg2"],
    kwargs={"param1": "value1"},
    expected="expected_result"
)

# Add a check step
tester.add_check_step(
    "test_name",
    module="module2",
    property="property_name",
    expected="expected_value"
)

# Save the test to a file
tester.save_test("test_name")
```

## Running Tests

Integration tests are run by the Module Validation Framework using the `ModuleIntegrationTester` class:

```python
from dreamos.testing.module_validation.integration import ModuleIntegrationTester

# Create a tester
tester = ModuleIntegrationTester()

# Load tests
tester.load_tests()

# Run a specific test
results = tester.run_test("test_name")

# Run all tests
results = tester.run_all_tests()

# Generate a report
report = tester.generate_report()
print(report)
```

You can also run tests using the command-line interface:

```
python -m dreamos.testing.module_validation integration [--tests test1 test2] [--tests-dir tests/integration] [--output-dir logs/integration]
``` 