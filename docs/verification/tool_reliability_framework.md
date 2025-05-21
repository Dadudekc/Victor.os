# Tool Reliability Testing Framework

**Version:** 1.0.0  
**Status:** IMPLEMENTATION  
**Created:** 2024-07-29  
**Author:** Agent-8 (Testing & Validation Engineer)

## Overview

This framework provides a standardized approach for testing and validating the reliability of core tools within Dream.OS, with initial focus on `read_file` and `list_dir` operations that have been identified as critical blockers to autonomous operation.

## Framework Components

### 1. Diagnostic Suite

```python
# Location: src/dreamos/testing/tools/reliability.py

from dreamos.core.errors import ToolOperationError
from dreamos.core.metrics.metrics_logger import MetricsLogger
import os
import time
import concurrent.futures

class ToolReliabilityTester:
    """Diagnostic suite for testing tool reliability."""
    
    def __init__(self, logger=None, metrics_logger=None):
        self.logger = logger
        self.metrics_logger = metrics_logger or MetricsLogger()
        self.results = {}
    
    def test_read_file(self, file_path, iterations=10, concurrent=False):
        """Test read_file operation reliability."""
        results = {
            'success_count': 0,
            'failure_count': 0,
            'average_latency': 0,
            'error_types': {},
            'concurrent_failures': 0
        }
        
        latencies = []
        
        def _single_read():
            start_time = time.time()
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                elapsed = time.time() - start_time
                latencies.append(elapsed)
                return True, None
            except Exception as e:
                error_type = type(e).__name__
                if error_type not in results['error_types']:
                    results['error_types'][error_type] = 0
                results['error_types'][error_type] += 1
                return False, error_type
        
        if concurrent:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(_single_read) for _ in range(iterations)]
                for future in concurrent.futures.as_completed(futures):
                    success, error = future.result()
                    if success:
                        results['success_count'] += 1
                    else:
                        results['failure_count'] += 1
                        if error == 'PermissionError':
                            results['concurrent_failures'] += 1
        else:
            for _ in range(iterations):
                success, error = _single_read()
                if success:
                    results['success_count'] += 1
                else:
                    results['failure_count'] += 1
        
        if latencies:
            results['average_latency'] = sum(latencies) / len(latencies)
        
        # Log metrics
        self.metrics_logger.log_metric(
            "tool_reliability", 
            {
                "tool": "read_file",
                "success_rate": results['success_count'] / iterations * 100,
                "avg_latency": results['average_latency'],
                "concurrent_failures": results['concurrent_failures'] if concurrent else 0
            }
        )
        
        return results
    
    def test_list_dir(self, dir_path, iterations=10, concurrent=False):
        """Test list_dir operation reliability."""
        results = {
            'success_count': 0,
            'failure_count': 0,
            'average_latency': 0,
            'error_types': {},
            'concurrent_failures': 0
        }
        
        latencies = []
        
        def _single_list():
            start_time = time.time()
            try:
                files = os.listdir(dir_path)
                elapsed = time.time() - start_time
                latencies.append(elapsed)
                return True, None
            except Exception as e:
                error_type = type(e).__name__
                if error_type not in results['error_types']:
                    results['error_types'][error_type] = 0
                results['error_types'][error_type] += 1
                return False, error_type
        
        if concurrent:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(_single_list) for _ in range(iterations)]
                for future in concurrent.futures.as_completed(futures):
                    success, error = future.result()
                    if success:
                        results['success_count'] += 1
                    else:
                        results['failure_count'] += 1
                        if error == 'PermissionError':
                            results['concurrent_failures'] += 1
        else:
            for _ in range(iterations):
                success, error = _single_list()
                if success:
                    results['success_count'] += 1
                else:
                    results['failure_count'] += 1
        
        if latencies:
            results['average_latency'] = sum(latencies) / len(latencies)
        
        # Log metrics
        self.metrics_logger.log_metric(
            "tool_reliability", 
            {
                "tool": "list_dir",
                "success_rate": results['success_count'] / iterations * 100,
                "avg_latency": results['average_latency'],
                "concurrent_failures": results['concurrent_failures'] if concurrent else 0
            }
        )
        
        return results
    
    def test_edge_cases(self):
        """Test tool reliability for edge cases."""
        edge_cases = [
            {"type": "long_path", "path": "a" * 255 + ".txt"},
            {"type": "special_chars", "path": "test!@#$%^&*().txt"},
            {"type": "unicode", "path": "テスト.txt"},
            {"type": "empty", "path": ""},
            {"type": "network_path", "path": "\\\\server\\share\\file.txt"}
        ]
        
        results = {}
        for case in edge_cases:
            case_type = case["type"]
            path = case["path"]
            results[case_type] = {
                "read_file": self._test_edge_case_read(path),
                "list_dir": self._test_edge_case_list(os.path.dirname(path) if path else "")
            }
        
        return results
    
    def _test_edge_case_read(self, path):
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    content = f.read()
                return {"success": True, "error": None}
            return {"success": False, "error": "FileNotFoundError"}
        except Exception as e:
            return {"success": False, "error": type(e).__name__}
    
    def _test_edge_case_list(self, path):
        try:
            if os.path.exists(path):
                files = os.listdir(path)
                return {"success": True, "error": None}
            return {"success": False, "error": "FileNotFoundError"}
        except Exception as e:
            return {"success": False, "error": type(e).__name__}
    
    def run_comprehensive_test(self, base_path="./", sample_files=None):
        """Run a comprehensive test suite."""
        if not sample_files:
            sample_files = [
                os.path.join(base_path, "README.md"),
                os.path.join(base_path, "requirements.txt"),
                os.path.join(base_path, "pyproject.toml")
            ]
        
        sample_dirs = [
            os.path.join(base_path, "src"),
            os.path.join(base_path, "docs"),
            os.path.join(base_path, "tests")
        ]
        
        results = {
            "read_file": {
                "standard": {},
                "concurrent": {}
            },
            "list_dir": {
                "standard": {},
                "concurrent": {}
            },
            "edge_cases": self.test_edge_cases()
        }
        
        # Test file reading
        for file_path in sample_files:
            if os.path.exists(file_path):
                results["read_file"]["standard"][file_path] = self.test_read_file(file_path)
                results["read_file"]["concurrent"][file_path] = self.test_read_file(file_path, concurrent=True)
        
        # Test directory listing
        for dir_path in sample_dirs:
            if os.path.exists(dir_path):
                results["list_dir"]["standard"][dir_path] = self.test_list_dir(dir_path)
                results["list_dir"]["concurrent"][dir_path] = self.test_list_dir(dir_path, concurrent=True)
        
        self.results = results
        return results
    
    def generate_report(self):
        """Generate a comprehensive report from test results."""
        if not self.results:
            return "No tests have been run yet."
        
        report = []
        report.append("# Tool Reliability Test Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Summary section
        report.append("## Summary")
        read_success = 0
        read_total = 0
        list_success = 0
        list_total = 0
        
        for path, result in self.results["read_file"]["standard"].items():
            read_success += result["success_count"]
            read_total += result["success_count"] + result["failure_count"]
        
        for path, result in self.results["list_dir"]["standard"].items():
            list_success += result["success_count"]
            list_total += result["success_count"] + result["failure_count"]
        
        report.append(f"- read_file success rate: {read_success/read_total*100:.2f}%")
        report.append(f"- list_dir success rate: {list_success/list_total*100:.2f}%")
        
        # Detail sections
        report.append("\n## read_file Results")
        for mode in ["standard", "concurrent"]:
            report.append(f"\n### {mode.capitalize()} Operation")
            for path, result in self.results["read_file"][mode].items():
                report.append(f"\n#### {path}")
                report.append(f"- Success: {result['success_count']}")
                report.append(f"- Failures: {result['failure_count']}")
                report.append(f"- Average Latency: {result['average_latency']:.6f} seconds")
                if result['error_types']:
                    report.append("- Error Types:")
                    for err_type, count in result['error_types'].items():
                        report.append(f"  - {err_type}: {count}")
        
        report.append("\n## list_dir Results")
        for mode in ["standard", "concurrent"]:
            report.append(f"\n### {mode.capitalize()} Operation")
            for path, result in self.results["list_dir"][mode].items():
                report.append(f"\n#### {path}")
                report.append(f"- Success: {result['success_count']}")
                report.append(f"- Failures: {result['failure_count']}")
                report.append(f"- Average Latency: {result['average_latency']:.6f} seconds")
                if result['error_types']:
                    report.append("- Error Types:")
                    for err_type, count in result['error_types'].items():
                        report.append(f"  - {err_type}: {count}")
        
        report.append("\n## Edge Cases")
        for case_type, results in self.results["edge_cases"].items():
            report.append(f"\n### {case_type}")
            for tool, result in results.items():
                report.append(f"- {tool}: {'Success' if result.get('success', False) else 'Failure'}")
                if not result.get('success', False) and result.get('error'):
                    report.append(f"  - Error: {result['error']}")
        
        return "\n".join(report)
```

### 2. Test Strategy

The test suite implements the following strategies:

1. **Single-Threaded Testing**
   - Sequential testing of file operations
   - Controlled latency measurement
   - Error categorization

2. **Concurrent Operation Testing**
   - Multi-threaded access patterns
   - Race condition detection
   - Permission error tracking

3. **Edge Case Validation**
   - Long path names
   - Special characters
   - Unicode handling
   - Empty paths
   - Network paths

4. **Metrics Collection**
   - Success rate tracking
   - Latency monitoring
   - Error type categorization
   - Real-time metrics logging

### 3. Integration Plan

This framework will be integrated into the Dream.OS codebase through:

1. Creation of dedicated testing package:
   ```
   src/dreamos/testing/
   ├── __init__.py
   ├── tools/
   │   ├── __init__.py
   │   ├── reliability.py
   │   └── validation.py
   └── README.md
   ```

2. Integration with existing metrics infrastructure (`src/dreamos/core/metrics/metrics_logger.py`)

3. Daily automated testing via CI/CD pipeline

4. Coordination with Agent-2 (Infrastructure) for diagnostic data sharing

## Implementation Timeline

1. **Day 1-2:** 
   - Create directory structure and base classes
   - Implement core testing methods
   - Set up initial metrics integration

2. **Day 3-4:**
   - Develop comprehensive test suite
   - Create report generation
   - Add edge case testing

3. **Day 5:**
   - Integrate with CI/CD
   - Share initial results with Agent-2
   - Document usage patterns for other agents

## Success Criteria

1. **Operational Metrics:**
   - Baseline success rate for all core tools
   - Latency profiles for standard operations
   - Categorized error patterns

2. **Performance Targets:**
   - 99.9% success rate for single-threaded operations
   - 95% success rate for concurrent operations
   - <50ms average latency for standard file operations

3. **Integration Goals:**
   - Daily automated testing
   - Real-time metrics dashboard
   - Automatic notification for reliability regressions

## Coordination Points

1. **With Agent-2 (Infrastructure):**
   - Share diagnostic data on tool failures
   - Coordinate on infrastructure optimizations
   - Develop shared monitoring approach

2. **With Agent-6 (Feedback):**
   - Integrate metrics into shared dashboard
   - Develop alerts for reliability issues
   - Create feedback mechanisms for tool performance 