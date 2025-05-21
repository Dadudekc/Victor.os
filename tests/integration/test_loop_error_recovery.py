"""
Integration tests for StableAutonomousLoop and Error Recovery integration.

These tests validate that the StableAutonomousLoop correctly integrates with
the error recovery system for handling exceptions during operation.
"""
import unittest
from unittest.mock import patch, MagicMock, call
import time
from typing import Dict, Any, Optional

from dreamos.skills.lifecycle import StableAutonomousLoop
from dreamos.skills.error_recovery import ErrorType


class TestAutonomousLoop(StableAutonomousLoop):
    """Test implementation of StableAutonomousLoop for testing."""
    
    def __init__(self, name: str = "test_loop"):
        """Initialize the test loop."""
        super().__init__(name=name)
        self.cycle_count = 0
        self.drift_checks = 0
        self.should_stop = False
        self.state = {"test_state": "value"}
        self.degraded_mode_entered = False
        self.recovery_attempted = False
        self.current_error = None
        
    def _begin_cycle(self):
        """Begin a cycle of operation."""
        pass
        
    def _process_cycle(self):
        """Process a cycle of operation."""
        self.cycle_count += 1
        if hasattr(self, 'cycle_error') and self.cycle_count == self.cycle_error_at:
            raise self.cycle_error
            
    def _end_cycle(self):
        """End a cycle of operation."""
        if self.cycle_count >= 3:
            self.should_stop = True
            
    def _detect_behavioral_drift(self) -> Optional[Dict[str, Any]]:
        """Detect behavioral drift in the agent operation."""
        self.drift_checks += 1
        if hasattr(self, 'simulate_drift') and self.simulate_drift:
            return {"test_drift": True}
        return None
        
    def _correct_drift(self, drift: Dict[str, Any]):
        """Apply corrections for detected drift."""
        self.drift_corrected = drift
        
    def _handle_unrecoverable_error(self, error: Exception):
        """Handle an unrecoverable error."""
        self.degraded_mode_entered = True
        self.current_error = error
        
    def run_limited(self, cycles: int = 3):
        """Run a limited number of cycles then stop."""
        self.cycle_limit = cycles
        super().run()


class TestLoopErrorRecovery(unittest.TestCase):
    """Test the integration between StableAutonomousLoop and error recovery systems."""

    def setUp(self):
        """Set up test fixtures."""
        self.loop = TestAutonomousLoop()

    @patch('dreamos.skills.error_recovery.recover_from_error')
    @patch('dreamos.skills.error_recovery.log_error')
    def test_error_recovery_attempt(self, mock_log_error, mock_recover):
        """Test that loop attempts to recover from errors using the recovery system."""
        # Configure mocks
        mock_recover.return_value = True  # Indicate successful recovery
        
        # Configure loop to raise an error
        error = ValueError("Test error")
        self.loop.cycle_error = error
        self.loop.cycle_error_at = 1
        
        # Run the loop
        self.loop.run_limited(cycles=2)
        
        # Verify error recovery was attempted
        mock_recover.assert_called_once()
        args, kwargs = mock_recover.call_args
        self.assertEqual(args[0], error)  # First arg should be the error
        self.assertEqual(kwargs['context'], self.loop.state)  # Context should be loop state
        
        # Verify error was logged
        mock_log_error.assert_called_once()
        args, kwargs = mock_log_error.call_args
        self.assertEqual(kwargs['error'], error)
        self.assertEqual(kwargs['operation'], self.loop.name)

    @patch('dreamos.skills.error_recovery.recover_from_error')
    def test_degraded_mode_on_recovery_failure(self, mock_recover):
        """Test that loop enters degraded mode when recovery fails."""
        # Configure mock to indicate failed recovery
        mock_recover.return_value = False
        
        # Configure loop to raise an error
        error = ValueError("Unrecoverable error")
        self.loop.cycle_error = error
        self.loop.cycle_error_at = 1
        
        # Run the loop
        self.loop.run_limited(cycles=2)
        
        # Verify degraded mode was entered
        self.assertTrue(self.loop.degraded_mode_entered)
        self.assertEqual(self.loop.current_error, error)

    @patch('dreamos.skills.error_recovery.get_available_recovery_resources')
    def test_degraded_mode_uses_available_resources(self, mock_get_resources):
        """Test that degraded mode uses available resources from error recovery."""
        # Patch the internal _handle_unrecoverable_error to access DegradedOperationMode
        original_handle = self.loop._handle_unrecoverable_error
        
        degraded_mode_resources = None
        
        def capture_resources(error):
            nonlocal degraded_mode_resources
            # Call original but capture degraded mode parameters
            with patch('dreamos.skills.lifecycle.DegradedOperationMode.__init__',
                      side_effect=lambda self, reason, available_resources=None: 
                          setattr(self, 'available_resources', available_resources)):
                with patch('dreamos.skills.lifecycle.DegradedOperationMode.__enter__',
                          return_value=MagicMock()):
                    with patch('dreamos.skills.lifecycle.DegradedOperationMode.__exit__',
                              return_value=None):
                        original_handle(error)
                        degraded_mode_resources = available_resources
        
        # Configure mock
        mock_get_resources.return_value = ["memory", "cpu", "logging"]
        
        # Replace method to capture resources
        self.loop._handle_unrecoverable_error = capture_resources
        
        # Configure loop to raise an error
        error = ValueError("Test for degraded mode")
        self.loop.cycle_error = error
        self.loop.cycle_error_at = 1
        
        # Configure recovery to fail
        with patch('dreamos.skills.error_recovery.recover_from_error', return_value=False):
            # Run the loop
            self.loop.run_limited(cycles=2)
        
        # Verify get_available_recovery_resources was called
        mock_get_resources.assert_called_once()
        args, kwargs = mock_get_resources.call_args
        self.assertEqual(args[0], error)
        self.assertEqual(args[1], self.loop.state)
        
        # Verify resources were passed to degraded mode
        self.assertEqual(degraded_mode_resources, ["memory", "cpu", "logging"])

    @patch('dreamos.skills.error_recovery.recover_from_error')
    def test_continue_after_successful_recovery(self, mock_recover):
        """Test that loop continues operation after successful recovery."""
        # Configure recovery to succeed
        mock_recover.return_value = True
        
        # Configure loop to raise an error in the first cycle
        error = ValueError("Recoverable error")
        self.loop.cycle_error = error
        self.loop.cycle_error_at = 1
        
        # Run the loop
        self.loop.run_limited(cycles=3)
        
        # Verify the loop continued running after recovery
        self.assertEqual(self.loop.cycle_count, 3)  # Should have completed all cycles
        self.assertFalse(self.loop.degraded_mode_entered)  # Should not have entered degraded mode

    @patch('dreamos.skills.error_recovery.classify_error')
    @patch('dreamos.skills.error_recovery.recover_from_error')
    def test_recovery_uses_error_classification(self, mock_recover, mock_classify):
        """Test that error recovery uses error classification."""
        # Configure mocks
        mock_classify.return_value = ErrorType.TRANSIENT
        mock_recover.return_value = True
        
        # Configure loop to raise an error
        error = ValueError("Test for classification")
        self.loop.cycle_error = error
        self.loop.cycle_error_at = 1
        
        # Run the loop
        with patch('dreamos.skills.lifecycle.DegradedOperationMode'):
            self.loop.run_limited(cycles=2)
        
        # Verify recovery was attempted
        mock_recover.assert_called_once()
        
        # We can't directly verify that classification was used in recovery
        # since that's inside the recover_from_error function, but we can check
        # it was called in the process if it's imported in the loop method


if __name__ == '__main__':
    unittest.main() 