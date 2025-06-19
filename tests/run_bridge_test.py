#!/usr/bin/env python3
"""
Bridge Test Runner
-----------------
Demonstrates the functionality of the Injector and Telemetry modules.
"""

import os
import sys
import time
import json
import datetime
from typing import Dict, Any

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import modules to test
from bridge.injector import BridgeInjector
from bridge.telemetry import BridgeTelemetry
from bridge.logging import BridgeLogger, ErrorHandler

def create_test_logger():
    """Create a test logger."""
    test_log_dir = "runtime/logs/demo"
    os.makedirs(test_log_dir, exist_ok=True)
    
    logger_config = {
        'log_path': os.path.join(test_log_dir, "demo_logs.jsonl"),
        'enable_console': True,
        'min_log_level': 'INFO'
    }
    
    return BridgeLogger(logger_config), logger_config

def test_injector():
    """Test the Injector module."""
    print("\n=== Testing Module 1: Injector ===\n")
    
    # Create logger and error handler
    logger, logger_config = create_test_logger()
    error_handler = ErrorHandler(logger)
    
    # Create injector
    injector_config = {
        'logger_config': logger_config,
        'version': '1.0.0'
    }
    injector = BridgeInjector(injector_config)
    
    # Test valid command
    print("\n> Testing valid command...")
    valid_command = {
        'command_type': 'EXECUTE_TASK',
        'payload': {'task_id': 'TASK-123'},
        'source': 'demo_script'
    }
    
    result = injector.process_command(valid_command)
    print_json(result)
    
    # Test invalid command
    print("\n> Testing invalid command...")
    invalid_command = {
        'command_type': 'EXECUTE_TASK',
        # Missing required payload.task_id
        'payload': {},
        'source': 'demo_script'
    }
    
    result = injector.process_command(invalid_command)
    print_json(result)
    
    # Test health check
    print("\n> Testing health check...")
    health = injector.health_check()
    print_json(health)
    
    return injector

def test_telemetry():
    """Test the Telemetry module."""
    print("\n=== Testing Module 2: Telemetry ===\n")
    
    # Create logger and error handler
    logger, logger_config = create_test_logger()
    
    # Create telemetry
    telemetry_config = {
        'logger_config': logger_config,
        'version': '1.0.0',
        'storage_type': 'memory'
    }
    telemetry = BridgeTelemetry(telemetry_config)
    
    # Record an event
    print("\n> Recording an event...")
    event = {
        'event_type': 'USER_ACTION',
        'source': 'demo_script',
        'data': {
            'action': 'button_click',
            'component': 'submit_button',
            'user_id': 'user_123'
        }
    }
    
    result = telemetry.record_event(event)
    print_json(result)
    
    # Record multiple metrics
    print("\n> Recording metrics...")
    metrics = [
        ('page_load_time_ms', 345),
        ('memory_usage_mb', 125.7),
        ('cpu_usage_percent', 23.5),
        ('active_connections', 42),
        ('page_load_time_ms', 298),
    ]
    
    for name, value in metrics:
        result = telemetry.record_metric(name, value, {'source': 'demo_script'})
        print(f"Recorded metric {name}: {value} - {result['status']}")
    
    # Get aggregated metrics
    print("\n> Getting aggregated metrics...")
    now = datetime.datetime.utcnow()
    one_hour_ago = now - datetime.timedelta(hours=1)
    
    result = telemetry.get_metrics(
        metric_names=['page_load_time_ms', 'memory_usage_mb'],
        time_range=(one_hour_ago.isoformat(), now.isoformat()),
        aggregation="MEAN"
    )
    print_json(result)
    
    # Check health
    print("\n> Testing health check...")
    health = telemetry.health_check()
    print_json(health)
    
    return telemetry

def test_integration():
    """Test integration between Injector and Telemetry."""
    print("\n=== Testing Module 1 + Module 2 Integration ===\n")
    
    # Create logger and error handler
    logger, logger_config = create_test_logger()
    
    # Create telemetry
    telemetry_config = {
        'logger_config': logger_config,
        'version': '1.0.0',
        'storage_type': 'memory'
    }
    telemetry = BridgeTelemetry(telemetry_config)
    
    # Create injector with telemetry
    injector_config = {
        'logger_config': logger_config,
        'version': '1.0.0',
        'telemetry_config': telemetry_config
    }
    injector = BridgeInjector(injector_config)
    
    # Process multiple commands to generate metrics
    print("\n> Processing commands to generate metrics...")
    for i in range(5):
        command = {
            'command_type': 'EXECUTE_TASK',
            'payload': {'task_id': f'TASK-{i+1}'},
            'source': 'demo_script'
        }
        injector.process_command(command)
        
    # Wait a bit to simulate processing time
    time.sleep(1)
    
    # Get command processing metrics
    print("\n> Getting command processing metrics...")
    now = datetime.datetime.utcnow()
    one_hour_ago = now - datetime.timedelta(hours=1)
    
    result = telemetry.get_metrics(
        metric_names=['command_processing_time_ms'],
        time_range=(one_hour_ago.isoformat(), now.isoformat()),
        aggregation="MEAN"
    )
    print_json(result)
    
    return injector, telemetry

def print_json(data):
    """Print JSON data in a readable format."""
    print(json.dumps(data, indent=2))

def main():
    """Run the tests."""
    print("=== Dream.OS Bridge Test Runner ===")
    print(f"Running at: {datetime.datetime.now().isoformat()}")
    
    try:
        # Test injector
        injector = test_injector()
        
        # Test telemetry
        telemetry = test_telemetry()
        
        # Test integration
        test_integration()
        
        print("\n=== All tests completed successfully ===")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 