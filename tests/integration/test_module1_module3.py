"""
Integration Test: Module 1 + Module 3
-------------------------------------
Tests the integration between the Injector module and the Logging & Error Handling Layer.
"""

import os
import sys
import json
import uuid
import shutil
import datetime
import unittest
from typing import Dict, Any

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

# Import modules to test
from bridge.modules.module1 import BridgeInjector
from bridge.modules.module3 import BridgeLogger, ErrorHandler

class TestModule1Module3Integration(unittest.TestCase):
    """Test case for Module 1 and Module 3 integration."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create test directory for logs
        self.test_log_dir = "runtime/logs/integration_test"
        os.makedirs(self.test_log_dir, exist_ok=True)
        
        # Initialize configuration
        self.logger_config = {
            'log_path': os.path.join(self.test_log_dir, "test_logs.jsonl"),
            'enable_console': True,
            'min_log_level': 'INFO'
        }
        
        # Initialize Module 3 components
        self.logger = BridgeLogger(self.logger_config)
        self.error_handler = ErrorHandler(self.logger)
        
        # Create custom handlers for testing
        def test_command_router(cmd):
            """Test command router for integration testing."""
            # Check if we should trigger an error
            if cmd.get('payload', {}).get('trigger_error', False):
                raise ValueError("Test error triggered")
                
            # Check if we should simulate a loop
            if cmd.get('payload', {}).get('loop', False):
                return {
                    "status": "success",
                    "command_id": cmd.get("command_id"),
                    "result": {
                        "message": "Loop iteration processed",
                        "data": {
                            "iteration": cmd.get('payload', {}).get('iteration', 1)
                        }
                    }
                }
                
            # Regular success response
            return {
                "status": "success",
                "command_id": cmd.get("command_id"),
                "result": {
                    "message": "Test command executed successfully",
                    "data": {
                        "execution_id": str(uuid.uuid4()),
                        "status": "COMPLETED"
                    }
                }
            }
        
        # Initialize injector with test handlers
        self.injector_config = {
            'logger_config': self.logger_config,
            'command_routers': {
                'TEST_COMMAND': test_command_router
            }
        }
        self.injector = BridgeInjector(self.injector_config)
        
        # Create test commands
        self.valid_command = {
            'command_type': 'TEST_COMMAND',
            'payload': {'param1': 'value1', 'param2': 'value2'},
            'source': 'integration_test',
            'metadata': {'test_id': 'module1_module3_integration'}
        }
        
        self.invalid_command = {
            'command_type': 'TEST_COMMAND',
            # Missing required payload
            'source': 'integration_test',
            'metadata': {'test_id': 'module1_module3_integration'}
        }
        
        self.error_command = {
            'command_type': 'TEST_COMMAND',
            'payload': {'trigger_error': True},
            'source': 'integration_test',
            'metadata': {'test_id': 'module1_module3_integration'}
        }
        
        self.loop_command = {
            'command_type': 'TEST_COMMAND',
            'payload': {'loop': True},
            'source': 'integration_test',
            'metadata': {'test_id': 'module1_module3_integration'}
        }
    
    def tearDown(self):
        """Clean up after tests."""
        # Archive test logs if needed
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = os.path.join(self.test_log_dir, "archive")
        os.makedirs(archive_dir, exist_ok=True)
        
        try:
            if os.path.exists(self.logger_config['log_path']):
                shutil.copy2(
                    self.logger_config['log_path'], 
                    os.path.join(archive_dir, f"test_logs_{timestamp}.jsonl")
                )
        except Exception as e:
            print(f"Warning: Could not archive logs: {e}")
    
    def read_log_entries(self):
        """Read log entries from the log file."""
        entries = []
        
        if os.path.exists(self.logger_config['log_path']):
            with open(self.logger_config['log_path'], 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue
                        
        return entries
    
    def test_valid_command(self):
        """Test processing a valid command."""
        # Process valid command
        result = self.injector.process_command(self.valid_command)
        
        # Verify result
        self.assertEqual(result["status"], "success")
        self.assertIn("command_id", result)
        self.assertIn("metadata", result)
        self.assertEqual(result["metadata"]["source_module"], "injector")
        
        # Verify log entry was created
        log_entries = self.read_log_entries()
        command_logs = [entry for entry in log_entries 
                      if "payload" in entry and 
                         "command_id" in entry["payload"] and
                         entry["payload"]["command_id"] == result["command_id"]]
        
        self.assertGreaterEqual(len(command_logs), 1)
        self.assertTrue(any(entry.get("logLevel") == "INFO" for entry in command_logs))
    
    def test_invalid_command(self):
        """Test processing an invalid command."""
        # Process invalid command
        result = self.injector.process_command(self.invalid_command)
        
        # Verify error response
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], "INVALID_COMMAND")
        
        # Verify error was logged
        log_entries = self.read_log_entries()
        error_logs = [entry for entry in log_entries 
                    if entry.get("logLevel") == "ERROR" and
                       "errorDetails" in entry and
                       entry["errorDetails"].get("errorCode") == "INVALID_COMMAND"]
        
        self.assertGreaterEqual(len(error_logs), 1)
    
    def test_exception_handling(self):
        """Test handling of exceptions."""
        # Process command that triggers an exception
        result = self.injector.process_command(self.error_command)
        
        # Verify error response
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], "INVALID_VALUE")
        
        # Verify exception was logged
        log_entries = self.read_log_entries()
        exception_logs = [entry for entry in log_entries 
                        if entry.get("logLevel") == "ERROR" and
                           "errorDetails" in entry and
                           "Test error triggered" in entry["errorDetails"].get("errorMessage", "")]
        
        self.assertGreaterEqual(len(exception_logs), 1)
    
    def test_infinite_loop_detection(self):
        """Test detection of infinite loops."""
        # Process the same command multiple times to trigger loop detection
        results = []
        loop_detected = False
        
        # Send the same command many times
        for i in range(15):
            # Update the loop command with the iteration number
            self.loop_command['payload']['iteration'] = i
            
            # Process the command
            result = self.injector.process_command(self.loop_command)
            results.append(result)
            
            # Check if loop was detected
            if result["status"] == "error" and result.get("error", {}).get("code") == "LOOP_DETECTED":
                loop_detected = True
                break
        
        # After several iterations, loop should be detected
        self.assertTrue(loop_detected, "Infinite loop was not detected")
        
        # Verify loop detection was logged
        log_entries = self.read_log_entries()
        loop_logs = [entry for entry in log_entries 
                   if entry.get("logLevel") == "ERROR" and
                      "errorDetails" in entry and
                      entry["errorDetails"].get("errorCode") == "LOOP_DETECTED"]
        
        self.assertGreaterEqual(len(loop_logs), 1)

if __name__ == "__main__":
    unittest.main() 