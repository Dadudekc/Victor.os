from unittest.mock import MagicMock, patch  # noqa: I001

import pytest
from dreamos.hooks.chatgpt_responder import ChatGPTResponder

# Remove the skipped stub function
# @pytest.mark.skip(reason='Test stub for coverage tracking')
# def test_stub_for_chatgpt_responder():
#     pass

# --- Mocks for dependencies ---


# Mock the scraper class if imported
@patch("dreamos.hooks.chatgpt_responder.ChatGPTScraper", MagicMock())
# Mock the adapter class if imported
@patch("dreamos.hooks.chatgpt_responder.OpenAIAdapter", MagicMock())
def test_responder_init_dev_mode():
    """Test initialization in dev mode (uses Scraper)."""
    responder = ChatGPTResponder(dev_mode=True)
    assert responder.dev_mode is True
    # Check if scraper attribute is set (mocked instance)
    assert responder.scraper is not None
    assert responder.adapter is None


# Patch dependencies for non-dev mode
@patch("dreamos.hooks.chatgpt_responder.ChatGPTScraper", MagicMock())
@patch("dreamos.hooks.chatgpt_responder.OpenAIAdapter", MagicMock())
def test_responder_init_prod_mode():
    """Test initialization in non-dev mode (uses Adapter)."""
    responder = ChatGPTResponder(dev_mode=False)
    assert responder.dev_mode is False
    assert responder.scraper is None
    # Check if adapter attribute is set (mocked instance)
    assert responder.adapter is not None


# Patch dependencies for dev mode test
@patch(
    "dreamos.hooks.chatgpt_responder.OpenAIAdapter", MagicMock()
)  # Need to patch both potential imports
@patch("dreamos.hooks.chatgpt_responder.ChatGPTScraper")
def test_get_response_dev_mode(MockScraper: MagicMock):
    """Test get_response calls scraper in dev mode."""
    mock_scraper_instance = MockScraper.return_value
    mock_scraper_instance.ask.return_value = "Scraper response"

    responder = ChatGPTResponder(dev_mode=True)
    # Ensure the mock instance was assigned
    assert responder.scraper == mock_scraper_instance

    response = responder.get_response("Dev prompt")

    mock_scraper_instance.ask.assert_called_once_with("Dev prompt")
    assert response == "Scraper response"


# Patch dependencies for prod mode test
@patch(
    "dreamos.hooks.chatgpt_responder.ChatGPTScraper", MagicMock()
)  # Need to patch both potential imports
@patch("dreamos.hooks.chatgpt_responder.OpenAIAdapter")
def test_get_response_prod_mode(MockAdapter: MagicMock):
    """Test get_response calls adapter in non-dev mode."""
    mock_adapter_instance = MockAdapter.return_value
    mock_adapter_instance.execute.return_value = "Adapter response"

    responder = ChatGPTResponder(dev_mode=False)
    # Ensure the mock instance was assigned
    assert responder.adapter == mock_adapter_instance

    response = responder.get_response("Prod prompt")

    mock_adapter_instance.execute.assert_called_once_with({"prompt": "Prod prompt"})
    assert response == "Adapter response"


@patch("dreamos.hooks.chatgpt_responder.ChatGPTScraper", MagicMock())
@patch("dreamos.hooks.chatgpt_responder.OpenAIAdapter", MagicMock())
@patch.object(ChatGPTResponder, "get_response")  # Mock the internal get_response call
def test_respond_to_mailbox(mock_get_response: MagicMock):
    """Test that respond_to_mailbox calls get_response and appends reply."""
    mock_get_response.return_value = "Mocked GPT Response"
    responder = ChatGPTResponder(
        dev_mode=False
    )  # Mode doesn't matter as get_response is mocked

    mailbox_data = {
        "messages": [{"message_id": "m1", "sender": "User", "content": "Hello there"}]
    }

    updated_mailbox = responder.respond_to_mailbox(mailbox_data)

    mock_get_response.assert_called_once_with("Hello there")

    assert "messages" in updated_mailbox
    assert len(updated_mailbox["messages"]) == 2
    reply = updated_mailbox["messages"][1]
    assert reply["sender"] == "ChatGPTResponder"
    assert reply["content"] == "Mocked GPT Response"
    assert "message_id" in reply
    assert "timestamp" in reply


@patch("dreamos.hooks.chatgpt_responder.ChatGPTScraper", MagicMock())
@patch("dreamos.hooks.chatgpt_responder.OpenAIAdapter", MagicMock())
def test_respond_to_mailbox_no_messages():
    """Test respond_to_mailbox handles empty messages list."""
    responder = ChatGPTResponder(dev_mode=False)
    mailbox_data = {"messages": []}
    updated_mailbox = responder.respond_to_mailbox(mailbox_data)
    assert updated_mailbox == mailbox_data  # Should return unchanged
    assert len(updated_mailbox["messages"]) == 0


# Test cases for when scraper/adapter is missing (optional, depends on desired robustness)  # noqa: E501
@patch("dreamos.hooks.chatgpt_responder.ChatGPTScraper", side_effect=ImportError)
@patch("dreamos.hooks.chatgpt_responder.OpenAIAdapter", MagicMock())
def test_responder_init_dev_mode_scraper_missing(MockAdapter, MockScraper):
    """Test init handles missing scraper gracefully in dev mode."""
    responder = ChatGPTResponder(dev_mode=True)
    assert responder.scraper is None  # Should be None if import failed
    assert responder.adapter is None
    # Calling get_response should raise RuntimeError
    with pytest.raises(RuntimeError, match="ChatGPTScraper not available"):
        responder.get_response("test")
