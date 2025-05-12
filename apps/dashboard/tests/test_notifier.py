import pytest
import pytest_asyncio
import json
from pathlib import Path
from apps.dashboard.modules.notifier import Notifier

@pytest.fixture
def config_path(tmp_path):
    """Create a temporary config file for testing"""
    config = {
        "discord": {
            "enabled": True,
            "webhook_url": "https://discord.com/api/webhooks/test",
            "channel_id": "test_channel",
            "username": "Test Bot",
            "avatar_url": "https://example.com/avatar.png",
            "alert_levels": {
                "info": {"emoji": "ℹ️", "color": 3447003},
                "warning": {"emoji": "⚠️", "color": 16776960},
                "error": {"emoji": "🚨", "color": 15158332},
                "success": {"emoji": "✅", "color": 3066993}
            }
        },
        "slack": {
            "enabled": True,
            "webhook_url": "https://hooks.slack.com/services/test",
            "channel": "#test-channel",
            "username": "Test Bot",
            "icon_emoji": ":robot_face:",
            "alert_levels": {
                "info": {"emoji": "ℹ️"},
                "warning": {"emoji": "⚠️"},
                "error": {"emoji": "🚨"},
                "success": {"emoji": "✅"}
            }
        },
        "alert_thresholds": {
            "drift_confidence": 85.0,
            "response_timeout": 30.0,
            "error_rate": 5.0,
            "memory_usage": 80.0,
            "cpu_usage": 90.0
        },
        "dashboard_url": "http://localhost:8000/dashboard",
        "episode": {
            "number": 5,
            "name": "Jarvis Integration",
            "status": "active"
        }
    }
    
    config_file = tmp_path / "notifier_config.json"
    config_file.write_text(json.dumps(config), encoding='utf-8')
    return config_file

@pytest_asyncio.fixture
async def notifier(config_path):
    """Create a notifier instance for testing"""
    notifier = Notifier(config_path)
    await notifier.initialize()
    yield notifier
    await notifier.close()

@pytest.mark.asyncio
async def test_notifier_initialization(notifier):
    """Test notifier initialization and config loading"""
    assert notifier.session is not None
    assert notifier.config["episode"]["number"] == 5
    assert notifier.config["episode"]["name"] == "Jarvis Integration"
    assert notifier.config["episode"]["status"] == "active"

@pytest.mark.asyncio
async def test_discord_alert(notifier, mocker):
    """Test Discord alert sending"""
    # Mock the session post method
    mock_post = mocker.patch.object(notifier.session, 'post')
    mock_response = mocker.AsyncMock()
    mock_response.status = 204
    mock_post.return_value.__aenter__.return_value = mock_response
    
    # Test THEA escalation alert
    await notifier.alert_thea_escalation(
        agent_id="test_agent",
        task_id="test_task",
        reason="Test escalation"
    )
    
    # Verify both Discord and Slack were called
    assert mock_post.call_count == 2
    
    # Get all calls
    calls = mock_post.call_args_list
    
    # Find Discord call (first call should be Discord since it's checked first in send_alert)
    discord_call = calls[0]
    discord_payload = discord_call[1]["json"]
    
    # Verify Discord payload
    assert "embeds" in discord_payload
    assert len(discord_payload["embeds"]) == 1
    embed = discord_payload["embeds"][0]
    assert "THEA Escalation" in embed["title"]
    assert "test_agent" in embed["fields"][0]["value"]
    
    # Find Slack call (second call)
    slack_call = calls[1]
    slack_payload = slack_call[1]["json"]
    
    # Verify Slack payload
    assert "blocks" in slack_payload
    assert len(slack_payload["blocks"]) > 0
    assert "THEA Escalation" in slack_payload["blocks"][0]["text"]["text"]
    
    # Test drift detection alert
    await notifier.alert_drift_detected(
        confidence=75.0,
        details="Test drift"
    )
    
    # Verify both Discord and Slack were called again
    assert mock_post.call_count == 4
    
    # Get new calls
    calls = mock_post.call_args_list[2:]
    
    # Find Discord call
    discord_call = calls[0]
    discord_payload = discord_call[1]["json"]
    
    # Verify Discord payload
    assert "embeds" in discord_payload
    assert len(discord_payload["embeds"]) == 1
    embed = discord_payload["embeds"][0]
    assert "Drift Detected" in embed["title"]
    assert "75.0%" in embed["fields"][0]["value"]
    
    # Find Slack call
    slack_call = calls[1]
    slack_payload = slack_call[1]["json"]
    
    # Verify Slack payload
    assert "blocks" in slack_payload
    assert len(slack_payload["blocks"]) > 0
    assert "Drift Detected" in slack_payload["blocks"][0]["text"]["text"]

@pytest.mark.asyncio
async def test_slack_alert(notifier, mocker):
    """Test Slack alert sending"""
    # Mock the session post method
    mock_post = mocker.patch.object(notifier.session, 'post')
    mock_response = mocker.AsyncMock()
    mock_response.status = 200
    mock_post.return_value.__aenter__.return_value = mock_response
    
    # Test resource warning alert
    await notifier.alert_resource_warning(
        resource="CPU",
        usage=95.0
    )
    
    # Verify the alert was sent
    assert mock_post.called
    call_args = mock_post.call_args[1]
    assert "json" in call_args
    payload = call_args["json"]
    assert payload["channel"] == "#test-channel"
    assert payload["username"] == "Test Bot"
    assert len(payload["blocks"]) > 0
    assert "Resource Warning" in payload["blocks"][0]["text"]["text"]
    assert "95.0%" in payload["blocks"][2]["text"]["text"]

@pytest.mark.asyncio
async def test_alert_error_handling(notifier, mocker):
    """Test error handling in alert sending"""
    # Mock the session post method to raise an exception
    mock_post = mocker.patch.object(notifier.session, 'post')
    mock_post.side_effect = Exception("Test error")
    
    # Test that alert sending doesn't raise an exception
    await notifier.alert_loop_halt(
        agent_id="test_agent",
        reason="Test halt"
    )
    
    # Verify the error was handled
    assert mock_post.called

@pytest.mark.asyncio
async def test_missing_webhook(notifier, mocker):
    """Test behavior when webhook URLs are missing"""
    # Remove webhook URLs from config
    notifier.config["discord"]["webhook_url"] = ""
    notifier.config["slack"]["webhook_url"] = ""
    
    # Mock the session post method
    mock_post = mocker.patch.object(notifier.session, 'post')
    
    # Test alert sending
    await notifier.send_alert(
        level="info",
        title="Test Alert",
        message="Test message"
    )
    
    # Verify no alerts were sent
    assert not mock_post.called 