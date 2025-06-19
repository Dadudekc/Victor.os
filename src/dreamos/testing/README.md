# Dream.OS Testing Framework

This directory contains the testing and verification framework for Dream.OS, providing standardized approaches to testing various components of the system.

## Overview

The testing framework is designed to:

1. Provide standardized testing utilities for common operations
2. Support verification of system components
3. Enable automated testing of critical functionality
4. Integrate with the metrics collection system

## Packages

- `tools/`: Testing utilities for core tools and operations
  - `reliability.py`: Testing framework for tool reliability

## Usage

### Tool Reliability Testing

```python
from dreamos.testing.tools.reliability import ToolReliabilityTester

# Create a tester instance
tester = ToolReliabilityTester()

# Run a comprehensive test suite
results = tester.run_comprehensive_test()

# Generate a report
report = tester.generate_report()
print(report)

# Or test specific operations
read_results = tester.test_read_file("path/to/file.txt")
dir_results = tester.test_list_dir("path/to/directory")
```

## Integration

The testing framework integrates with the metrics collection system to provide real-time data on system performance and reliability. Tests automatically log metrics using the `MetricsLogger` from `dreamos.core.metrics_logger`.

## Extending

To extend the testing framework, create new modules in the appropriate subdirectory and follow the established patterns for metrics collection and reporting. 