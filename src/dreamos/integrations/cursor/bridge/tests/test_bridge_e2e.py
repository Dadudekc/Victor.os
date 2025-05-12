"""End-to-end tests for the Cursor-ChatGPT bridge integration."""

import json
import os
import time
from pathlib import Path
import pytest
from dreamos.integrations.cursor.bridge import BridgeLoop
from dreamos.core.config import AppConfig

# Test configuration
TEST_PROMPT = "Hello, this is a test prompt from the bridge e2e test."
TEST_TIMEOUT = 30  # seconds to wait for response

@pytest.fixture
def bridge_config():
    """Create a test configuration for the bridge."""
    config = {
        "paths": {
            "log_dir": "runtime/logs/bridge/test",
            "task_list_file_for_bridge": "runtime/tasks/bridge_test_tasks.json"
        },
        "chatgpt_web_agent_settings": {
            "agent_id": "test_bridge_agent",
            "conversation_url": "https://chat.openai.com/",
            "simulate_interaction": True  # Use simulation mode for testing
        }
    }
    
    # Ensure test directories exist
    Path("runtime/logs/bridge/test").mkdir(parents=True, exist_ok=True)
    Path("runtime/tasks").mkdir(parents=True, exist_ok=True)
    
    # Write test config
    config_path = Path("src/dreamos/integrations/cursor/config/test_bridge_config.yaml")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    import yaml
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    
    return config_path

@pytest.fixture
def bridge_loop(bridge_config):
    """Create a bridge loop instance for testing."""
    app_config = AppConfig()
    loop = BridgeLoop(
        app_config=app_config,
        agent_id=1,
        prompt_source=Path("test_prompts.txt"),
        outbox_dir=Path("runtime/bridge_outbox/test"),
        window_title="Cursor",
        coords_cfg=Path("runtime/config/test_cursor_coords.json"),
        chat_url="https://chat.openai.com/",
        poll_interval=1.0,
        response_timeout=TEST_TIMEOUT
    )
    return loop

def test_bridge_prompt_response_flow(bridge_loop, tmp_path):
    """Test the complete flow from prompt injection to response retrieval."""
    # Create test prompt file
    prompt_file = tmp_path / "test_prompt.jsonl"
    prompt_id = "test_" + str(int(time.time()))
    prompt_data = {
        "prompt_id": prompt_id,
        "prompt": TEST_PROMPT
    }
    
    with open(prompt_file, "w") as f:
        f.write(json.dumps(prompt_data) + "\n")
    
    # Start bridge loop in a separate thread
    import threading
    bridge_thread = threading.Thread(target=bridge_loop.run)
    bridge_thread.daemon = True
    bridge_thread.start()
    
    try:
        # Wait for response
        start_time = time.time()
        response_found = False
        
        while time.time() - start_time < TEST_TIMEOUT:
            # Check for response file
            response_files = list(Path("runtime/bridge_outbox/test").glob(f"*{prompt_id}*.json"))
            if response_files:
                with open(response_files[0]) as f:
                    response_data = json.load(f)
                    assert response_data["response_for_prompt_id"] == prompt_id
                    assert "response_content" in response_data
                    response_found = True
                    break
            time.sleep(1)
        
        assert response_found, "No response received within timeout period"
        
    finally:
        # Cleanup
        bridge_loop._should_stop = True
        bridge_thread.join(timeout=5)
        
        # Clean up test files
        if prompt_file.exists():
            prompt_file.unlink()
        for response_file in Path("runtime/bridge_outbox/test").glob(f"*{prompt_id}*.json"):
            response_file.unlink()

def test_bridge_config_loading(bridge_config):
    """Test that bridge configuration is loaded correctly."""
    app_config = AppConfig()
    assert app_config.paths.log_dir == "runtime/logs/bridge/test"
    assert app_config.paths.task_list_file_for_bridge == "runtime/tasks/bridge_test_tasks.json"
    
    # Verify ChatGPTWebAgent settings
    with open(bridge_config) as f:
        import yaml
        config = yaml.safe_load(f)
        assert config["chatgpt_web_agent_settings"]["agent_id"] == "test_bridge_agent"
        assert config["chatgpt_web_agent_settings"]["simulate_interaction"] is True 