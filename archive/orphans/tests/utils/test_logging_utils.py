# tests/utils/test_logging_utils.py
import unittest
from unittest.mock import patch

# Assuming the utility function is importable
from dreamos.utils.logging_utils import log_handler_exception


class TestLogHandlerException(unittest.TestCase):
    @patch("dreamos.utils.logging_utils.logger")  # Patch the logger within the module
    def test_log_handler_exception_basic(self, mock_logger):
        """Test basic logging of an exception from a handler."""

        def sample_handler(event_data):
            # A dummy handler function
            pass

        event_data_example = {"key": "value", "id": 123}
        exception_example = ValueError("Something went wrong")

        try:
            # Simulate catching the exception and logging it
            raise exception_example
        except Exception as e:
            log_handler_exception(sample_handler, event_data_example, e)

        # Assertions: Check if logger.error was called
        mock_logger.error.assert_called_once()
        call_args, call_kwargs = mock_logger.error.call_args

        # Check if key information is present in the logged message
        log_message = call_args[0]
        self.assertIn("Exception caught in handler 'sample_handler'", log_message)
        self.assertIn("Event Data Keys: ['key', 'id']", log_message)
        self.assertIn("Exception Type: ValueError", log_message)
        self.assertIn("Exception Args: ('Something went wrong',)", log_message)
        self.assertIn("Traceback:", log_message)

    @patch("dreamos.utils.logging_utils.logger")
    def test_log_handler_exception_no_handler_name(self, mock_logger):
        """Test logging when the handler object has no standard name attributes."""

        handler_obj = object()  # A plain object without __name__ or __qualname__
        event_data_example = {"data": "simple"}
        exception_example = TypeError("Invalid type")

        try:
            raise exception_example
        except Exception as e:
            log_handler_exception(handler_obj, event_data_example, e)

        mock_logger.error.assert_called_once()
        call_args, call_kwargs = mock_logger.error.call_args
        log_message = call_args[0]
        # Check if it falls back to a generic representation or 'unknown_handler'
        self.assertIn(
            "handler 'unknown_handler'", log_message
        )  # Or check for repr(handler_obj)
        self.assertIn("Exception Type: TypeError", log_message)


if __name__ == "__main__":
    unittest.main()
