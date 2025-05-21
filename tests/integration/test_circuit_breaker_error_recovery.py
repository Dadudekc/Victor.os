"""
Integration tests for Circuit Breaker and Error Recovery integration.

These tests validate that the CircuitBreaker correctly integrates with
the error recovery system for error classification and logging.
"""
import unittest
from unittest.mock import patch, MagicMock
import time
import logging

from dreamos.skills.lifecycle import CircuitBreaker, CircuitState
from dreamos.skills.error_recovery import ErrorType


class TestCircuitBreakerErrorRecovery(unittest.TestCase):
    """Test the integration between CircuitBreaker and error recovery systems."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the circuit breaker registry before each test
        CircuitBreaker._registry = {}
        
        # Create a test circuit breaker
        self.breaker = CircuitBreaker(
            operation_name="test_operation",
            failure_threshold=3,
            reset_timeout=1  # Short timeout for testing
        )

    @patch('dreamos.skills.error_recovery.classify_error')
    @patch('dreamos.skills.error_recovery.log_error')
    def test_error_classification_integration(self, mock_log_error, mock_classify_error):
        """Test that CircuitBreaker uses error classification."""
        # Setup mocks
        mock_classify_error.return_value = ErrorType.TRANSIENT
        
        # Create a test exception
        test_exception = ValueError("Test error")
        
        # Use the circuit breaker with an error
        try:
            with self.breaker:
                raise test_exception
        except ValueError:
            pass  # Expected exception
        
        # Verify error classification was called
        mock_classify_error.assert_called_once_with(test_exception)
        
        # Verify error logging was called with the classified error type
        mock_log_error.assert_called_once()
        args, kwargs = mock_log_error.call_args
        self.assertEqual(kwargs['error'], test_exception)
        self.assertEqual(kwargs['error_type'], ErrorType.TRANSIENT)
        self.assertEqual(kwargs['operation'], "test_operation")
        self.assertIn('circuit_state', kwargs['context'])

    @patch('dreamos.skills.error_recovery.classify_error')
    def test_error_type_affects_failure_recording(self, mock_classify_error):
        """Test that different error types affect how failures are recorded."""
        # Setup error classification to return a persistent error
        mock_classify_error.return_value = ErrorType.PERSISTENT
        
        # Use circuit breaker with error
        for _ in range(3):  # Just below threshold
            try:
                with self.breaker:
                    raise ValueError("Persistent error")
            except ValueError:
                pass
                
        # Circuit should be open after 3 persistent errors (below normal threshold)
        self.assertEqual(self.breaker.state, CircuitState.OPEN)
        
        # Reset for next test
        self.breaker = CircuitBreaker(
            operation_name="test_operation2",
            failure_threshold=3,
            reset_timeout=1
        )
        
        # Now test with transient errors
        mock_classify_error.return_value = ErrorType.TRANSIENT
        
        # Use circuit breaker with transient errors
        for _ in range(3):  # Same number as before
            try:
                with self.breaker:
                    raise ValueError("Transient error")
            except ValueError:
                pass
                
        # Circuit should still be closed after same number of transient errors
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)

    def test_fallback_when_error_recovery_unavailable(self):
        """Test graceful fallback when error recovery is not available."""
        # Simulate ImportError when trying to import error recovery
        with patch('dreamos.skills.lifecycle.circuit_breaker.__import__', side_effect=ImportError):
            # Create a new circuit breaker (to avoid cached imports)
            breaker = CircuitBreaker(
                operation_name="fallback_test",
                failure_threshold=3
            )
            
            # Use the circuit breaker with an error
            try:
                with breaker:
                    raise ValueError("Test error without recovery system")
            except ValueError:
                pass
                
            # Should still record the failure without error
            self.assertEqual(breaker.failure_count, 1)
            
            # Complete the failure threshold
            for _ in range(2):
                try:
                    with breaker:
                        raise ValueError("Another test error")
                except ValueError:
                    pass
                    
            # Circuit should open at threshold even without error recovery
            self.assertEqual(breaker.state, CircuitState.OPEN)

    @patch('dreamos.skills.error_recovery.classify_error')
    @patch('dreamos.skills.error_recovery.log_error')
    def test_circuit_transition_logging(self, mock_log_error, mock_classify_error):
        """Test that circuit state transitions are logged with error context."""
        # Configure mocks
        mock_classify_error.return_value = ErrorType.PERSISTENT
        
        # Set up a logger to capture log messages
        logger = logging.getLogger('dreamos.skills.lifecycle.circuit_breaker')
        original_level = logger.level
        logger.setLevel(logging.INFO)
        log_capture = MagicMock()
        handler = logging.Handler()
        handler.emit = log_capture
        logger.addHandler(handler)
        
        try:
            # Trigger circuit state transition
            for _ in range(3):
                try:
                    with self.breaker:
                        raise ValueError("Test error")
                except ValueError:
                    pass
                    
            # Check that circuit opened
            self.assertEqual(self.breaker.state, CircuitState.OPEN)
            
            # Verify error was logged with circuit state context
            mock_log_error.assert_called()
            context_arg = mock_log_error.call_args[1]['context']
            self.assertIn('circuit_state', context_arg)
            
        finally:
            # Clean up logger changes
            logger.removeHandler(handler)
            logger.setLevel(original_level)

    def test_half_open_state_with_error_recovery(self):
        """Test circuit breaker half-open state with error recovery integration."""
        with patch('dreamos.skills.error_recovery.classify_error') as mock_classify:
            with patch('dreamos.skills.error_recovery.log_error') as mock_log:
                # Configure error classification
                mock_classify.return_value = ErrorType.TRANSIENT
                
                # Force circuit to open state
                self.breaker.state = CircuitState.OPEN
                self.breaker.last_failure_time = time.time() - 2  # Past the reset timeout
                
                # First call should transition to half-open
                try:
                    with self.breaker:
                        # Success this time
                        pass
                except RuntimeError:
                    self.fail("Should have allowed operation in half-open state")
                    
                # Verify state transition
                self.assertEqual(self.breaker.state, CircuitState.HALF_OPEN)
                
                # Now fail in half-open state
                try:
                    with self.breaker:
                        raise ValueError("Failure in half-open")
                except ValueError:
                    pass
                    
                # Should go back to open with increased timeout
                self.assertEqual(self.breaker.state, CircuitState.OPEN)
                self.assertGreater(self.breaker.current_timeout, 1)  # Should have increased
                
                # Verify error was logged with correct context
                mock_log.assert_called()
                context = mock_log.call_args[1]['context']
                self.assertEqual(context['circuit_state'], 'half_open')


if __name__ == '__main__':
    unittest.main() 