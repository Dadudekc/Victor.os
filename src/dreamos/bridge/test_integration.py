"""
Tests for the Dream.OS Bridge Integration Module
"""

import unittest
import yaml
import os
from unittest.mock import Mock, patch
from .module4_integration import ExternalSystemIntegration

class TestExternalSystemIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'security': {
                'key': 'test_key',
                'algorithm': 'sha256',
                'token_expiry': 3600
            },
            'systems': {
                'test_system': {
                    'type': 'test',
                    'credentials': {
                        'api_key': 'test_key',
                        'secret': 'test_secret'
                    },
                    'transformers': {
                        'in': {
                            'fields': {
                                'message_id': 'id',
                                'content': 'text'
                            }
                        },
                        'out': {
                            'fields': {
                                'id': 'message_id',
                                'text': 'content'
                            }
                        }
                    }
                }
            }
        }
        self.integration = ExternalSystemIntegration(self.config)
        
    def test_authentication_success(self):
        """Test successful system authentication."""
        credentials = {
            'api_key': 'test_key',
            'secret': 'test_secret'
        }
        result = self.integration.authenticate_system('test_system', credentials)
        self.assertTrue(result)
        self.assertIn('test_system', self.integration.authenticated_systems)
        
    def test_authentication_failure(self):
        """Test failed system authentication."""
        credentials = {
            'api_key': 'wrong_key',
            'secret': 'wrong_secret'
        }
        result = self.integration.authenticate_system('test_system', credentials)
        self.assertFalse(result)
        self.assertNotIn('test_system', self.integration.authenticated_systems)
        
    def test_data_transformation_in(self):
        """Test data transformation from external to internal format."""
        external_data = {
            'id': '123',
            'text': 'test message'
        }
        internal_data = self.integration.transform_data('test_system', external_data, 'in')
        self.assertEqual(internal_data['message_id'], '123')
        self.assertEqual(internal_data['content'], 'test message')
        
    def test_data_transformation_out(self):
        """Test data transformation from internal to external format."""
        internal_data = {
            'message_id': '123',
            'content': 'test message'
        }
        external_data = self.integration.transform_data('test_system', internal_data, 'out')
        self.assertEqual(external_data['id'], '123')
        self.assertEqual(external_data['text'], 'test message')
        
    @patch('src.dreamos.bridge.module4_integration.ExternalSystemIntegration._get_transport')
    def test_send_message_success(self, mock_get_transport):
        """Test successful message sending."""
        # Mock transport
        mock_transport = Mock()
        mock_transport.send.return_value = True
        mock_get_transport.return_value = mock_transport
        
        # Authenticate system
        self.integration.authenticate_system('test_system', {
            'api_key': 'test_key',
            'secret': 'test_secret'
        })
        
        # Send message
        message = {
            'message_id': '123',
            'content': 'test message'
        }
        result = self.integration.send_message('test_system', message)
        
        self.assertTrue(result)
        mock_transport.send.assert_called_once()
        
    @patch('src.dreamos.bridge.module4_integration.ExternalSystemIntegration._get_transport')
    def test_send_message_failure(self, mock_get_transport):
        """Test failed message sending."""
        # Mock transport
        mock_transport = Mock()
        mock_transport.send.return_value = False
        mock_get_transport.return_value = mock_transport
        
        # Authenticate system
        self.integration.authenticate_system('test_system', {
            'api_key': 'test_key',
            'secret': 'test_secret'
        })
        
        # Send message
        message = {
            'message_id': '123',
            'content': 'test message'
        }
        result = self.integration.send_message('test_system', message)
        
        self.assertFalse(result)
        mock_transport.send.assert_called_once()
        
    def test_send_message_unauthenticated(self):
        """Test sending message to unauthenticated system."""
        message = {
            'message_id': '123',
            'content': 'test message'
        }
        result = self.integration.send_message('test_system', message)
        self.assertFalse(result)
        
    def test_config_loading(self):
        """Test loading configuration from YAML file."""
        config_path = os.path.join(os.path.dirname(__file__), 'integration_config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        integration = ExternalSystemIntegration(config)
        self.assertIsNotNone(integration)
        self.assertIn('cursor_ide', integration.config['systems'])
        self.assertIn('external_api', integration.config['systems'])

if __name__ == '__main__':
    unittest.main() 