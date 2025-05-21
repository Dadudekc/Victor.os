import unittest
from unittest.mock import Mock, patch
import time
from .scraper_state_machine import ScraperStateMachine, ScraperState
from ..io.file_manager import FileManager

class TestScraperStateMachine(unittest.TestCase):
    def setUp(self):
        self.file_manager = Mock(spec=FileManager)
        self.state_machine = ScraperStateMachine(self.file_manager)
        
    def test_initial_state(self):
        """Test that the state machine starts in INITIALIZING state."""
        self.assertEqual(self.state_machine.state, ScraperState.INITIALIZING)
        
    def test_state_transition(self):
        """Test basic state transition functionality."""
        self.state_machine.transition_to(ScraperState.READY)
        self.assertEqual(self.state_machine.state, ScraperState.READY)
        
    def test_context_update(self):
        """Test that context is updated during state transitions."""
        test_error = "Test error message"
        self.state_machine.transition_to(ScraperState.ERROR, error_message=test_error)
        self.assertEqual(self.state_machine.context.error_message, test_error)
        
    @patch('dreamos.core.agents.scraper.scraper_state_machine.ChatGPTScraper')
    def test_initialization_flow(self, mock_scraper_class):
        """Test the initialization flow of the state machine."""
        # Mock the scraper instance
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.ensure_login_session.return_value = True
        
        # Process through initialization
        self.state_machine.process()  # INITIALIZING -> AUTHENTICATING
        self.assertEqual(self.state_machine.state, ScraperState.AUTHENTICATING)
        
        self.state_machine.process()  # AUTHENTICATING -> READY
        self.assertEqual(self.state_machine.state, ScraperState.READY)
        
        # Verify scraper was initialized
        mock_scraper_class.assert_called_once()
        mock_scraper.ensure_login_session.assert_called_once()
        
    @patch('dreamos.core.agents.scraper.scraper_state_machine.ChatGPTScraper')
    def test_prompt_flow(self, mock_scraper_class):
        """Test the prompt sending and response flow."""
        # Setup
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.ensure_login_session.return_value = True
        mock_scraper.send_prompt.return_value = True
        
        # Initialize to READY state
        self.state_machine.transition_to(ScraperState.READY)
        
        # Send a prompt
        test_prompt = "Test prompt"
        self.state_machine.send_prompt(test_prompt)
        self.assertEqual(self.state_machine.state, ScraperState.SENDING_PROMPT)
        
        # Process sending
        self.state_machine.process()
        self.assertEqual(self.state_machine.state, ScraperState.WAITING_FOR_RESPONSE)
        mock_scraper.send_prompt.assert_called_once_with(test_prompt)
        
    def test_error_handling(self):
        """Test error state handling and recovery."""
        # Setup error state
        test_error = "Test error"
        self.state_machine.transition_to(ScraperState.ERROR, error_message=test_error)
        self.assertEqual(self.state_machine.context.error_message, test_error)
        
        # Process error state
        self.state_machine.process()
        # Should either transition to READY (if recovery successful) or SHUTDOWN
        self.assertIn(self.state_machine.state, [ScraperState.READY, ScraperState.SHUTDOWN])
        
    def test_shutdown(self):
        """Test shutdown functionality."""
        self.state_machine.shutdown()
        self.assertEqual(self.state_machine.state, ScraperState.SHUTDOWN)
        
if __name__ == '__main__':
    unittest.main() 