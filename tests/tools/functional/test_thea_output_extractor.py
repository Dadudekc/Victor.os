"""Tests for the THEA output extractor."""

import time
from unittest.mock import MagicMock, patch

import pytest
from dreamos.core.config import AppConfig
from dreamos.tools.functional.thea_output_extractor import TheaOutputExtractor, extract_thea_response

@pytest.fixture
def config():
    """Create a test configuration."""
    config = AppConfig()
    config.set("paths.gui_images", "tests/assets/gui_templates")
    return config

@pytest.fixture
def extractor(config):
    """Create a test extractor instance."""
    return TheaOutputExtractor(config)

def test_extractor_initialization(extractor, config):
    """Test extractor initialization."""
    assert extractor.config == config
    assert extractor.gui_images_dir == config.get("paths.gui_images")
    assert extractor.response_complete_cue is not None

@patch("pyautogui.locateOnScreen")
@patch("pyperclip.paste")
def test_extract_with_visual_cue(mock_paste, mock_locate, extractor):
    """Test extraction using visual cue detection."""
    # Mock clipboard content
    mock_paste.side_effect = ["old content", "new content"]
    
    # Mock visual cue detection
    mock_locate.return_value = (100, 100, 50, 50)  # x, y, width, height
    
    # Test extraction
    result = extractor._extract_with_visual_cue()
    assert result == "new content"
    mock_locate.assert_called_once()

@patch("pyperclip.paste")
def test_extract_with_clipboard_monitoring(mock_paste, extractor):
    """Test extraction using clipboard monitoring."""
    # Mock clipboard content changes
    mock_paste.side_effect = ["old content", "new content", "new content"]
    
    # Test extraction
    result = extractor._extract_with_clipboard_monitoring()
    assert result == "new content"
    assert mock_paste.call_count >= 2

@patch("pyperclip.paste")
def test_extract_timeout(mock_paste, extractor):
    """Test extraction timeout."""
    # Mock unchanging clipboard content
    mock_paste.return_value = "unchanged content"
    
    # Test extraction with short timeout
    with patch.object(extractor, "MAX_WAIT_TIME", 0.1):
        result = extractor.extract_response()
        assert result is None

def test_get_clipboard_text(extractor):
    """Test clipboard text retrieval."""
    with patch("pyperclip.paste") as mock_paste:
        # Test valid content
        mock_paste.return_value = "test content"
        assert extractor._get_clipboard_text() == "test content"
        
        # Test empty content
        mock_paste.return_value = ""
        assert extractor._get_clipboard_text() is None
        
        # Test whitespace content
        mock_paste.return_value = "   \n\t  "
        assert extractor._get_clipboard_text() is None
        
        # Test error handling
        mock_paste.side_effect = Exception("Clipboard error")
        assert extractor._get_clipboard_text() is None

@patch("dreamos.tools.functional.thea_output_extractor.TheaOutputExtractor")
def test_extract_thea_response(mock_extractor_class, config):
    """Test the convenience function."""
    # Mock extractor instance
    mock_extractor = MagicMock()
    mock_extractor_class.return_value = mock_extractor
    mock_extractor.extract_response.return_value = "test response"
    
    # Test extraction
    result = extract_thea_response(config)
    assert result == "test response"
    mock_extractor_class.assert_called_once_with(config)
    mock_extractor.extract_response.assert_called_once() 