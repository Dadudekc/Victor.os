import unittest
from unittest.mock import Mock, patch
from .scraper_integration import ScraperIntegration, ScraperIntegrationConfig
from .scraper_state_machine import ScraperState
from ..io.file_manager import FileManager

class TestScraperIntegration(unittest.TestCase):
    def setUp(self):
        self.file_manager = Mock(spec=FileManager)
        self.agent_bus = Mock()
        self.config = ScraperIntegrationConfig()
        self.integration = ScraperIntegration(
            self.file_manager,
            self.agent_bus,
            self.config
        )
        
    def test_initialization(self):
        """Test initialization of the scraper integration."""
        with patch.object(self.integration.state_machine, 'process') as mock_process:
            mock_process.side_effect = lambda: setattr(
                self.integration.state_machine, 'state', ScraperState.READY
            )
            self.assertTrue(self.integration.initialize())
            self.assertEqual(self.integration.get_state(), ScraperState.READY)
            
    def test_send_prompt(self):
        """Test sending a prompt through the integration."""
        test_prompt = "Test prompt"
        test_response = "Test response"
        
        with patch.object(self.integration.state_machine, 'send_prompt') as mock_send:
            with patch.object(self.integration.state_machine, 'process') as mock_process:
                with patch.object(self.integration.state_machine, 'get_current_response') as mock_get_response:
                    # Setup mocks
                    mock_process.side_effect = lambda: setattr(
                        self.integration.state_machine, 'state', ScraperState.READY
                    )
                    mock_get_response.return_value = test_response
                    
                    # Send prompt
                    response = self.integration.send_prompt(test_prompt)
                    
                    # Verify
                    mock_send.assert_called_once_with(test_prompt)
                    self.assertEqual(response, test_response)
                    
    def test_get_conversation_content(self):
        """Test getting conversation content."""
        test_content = "Test conversation content"
        
        with patch.object(self.integration.state_machine.context.scraper, 'get_conversation_content') as mock_get:
            mock_get.return_value = test_content
            content = self.integration.get_conversation_content()
            self.assertEqual(content, test_content)
            
    def test_ensure_login_session(self):
        """Test ensuring login session."""
        with patch.object(self.integration.state_machine.context.scraper, 'ensure_login_session') as mock_ensure:
            mock_ensure.return_value = True
            self.assertTrue(self.integration.ensure_login_session())
            mock_ensure.assert_called_once()
            
    def test_shutdown(self):
        """Test shutdown functionality."""
        with patch.object(self.integration.state_machine, 'shutdown') as mock_shutdown:
            self.integration.shutdown()
            mock_shutdown.assert_called_once()
            
    def test_error_handling(self):
        """Test error handling in various operations."""
        # Test initialization error
        with patch.object(self.integration.state_machine, 'process', side_effect=Exception("Test error")):
            self.assertFalse(self.integration.initialize())
            
        # Test send_prompt error
        with patch.object(self.integration.state_machine, 'send_prompt', side_effect=Exception("Test error")):
            with self.assertRaises(Exception):
                self.integration.send_prompt("Test prompt")
                
        # Test get_conversation_content error
        with patch.object(self.integration.state_machine.context.scraper, 'get_conversation_content', 
                         side_effect=Exception("Test error")):
            with self.assertRaises(Exception):
                self.integration.get_conversation_content()
                
    def test_operation_tracking(self):
        """Test operation ID tracking."""
        # Send multiple prompts
        self.integration.send_prompt("Prompt 1", "op1")
        self.integration.send_prompt("Prompt 2", "op2")
        
        # Verify operation tracking
        self.assertIn("op1", self.integration.active_operations)
        self.assertIn("op2", self.integration.active_operations)
        
if __name__ == '__main__':
    unittest.main() 