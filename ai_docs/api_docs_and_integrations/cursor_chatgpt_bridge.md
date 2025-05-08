# Cursor to ChatGPT Bridge Documentation

## 1. Overview

The Cursor to ChatGPT Bridge facilitates communication between the Cursor environment and live ChatGPT sessions. It allows prompts originating from Cursor (or placed into a designated file) to be processed by ChatGPT, with the responses returned for Cursor to consume. This enables integration of live ChatGPT capabilities into automated workflows.

## 2. Architecture

The bridge consists of the following key components:

*   **`cursor_to_gpt.jsonl`**: A JSONL file located at `src/dreamos/bridge/cursor_to_gpt.jsonl`. This acts as the input queue. Each line is a JSON object representing a prompt to be sent to ChatGPT.
    *   Format: `{"prompt_id": "unique_id_string", "prompt": "Your prompt text here"}`
*   **`bridge_loop.py`**: A Python script located at `src/dreamos/bridge/bridge_loop.py`. This is the core orchestrator of the bridge.
    *   It polls `cursor_to_gpt.jsonl` for new prompts.
    *   It instantiates and uses `ChatGPTWebAgent` to process these prompts.
    *   It writes responses to `gpt_to_cursor.jsonl`.
    *   It logs interactions to `scraper_log.jsonl`.
*   **`ChatGPTWebAgent` (from `src/dreamos/agents/chatgpt_web_agent.py`)**: An agent responsible for all direct interactions with the ChatGPT web UI.
    *   Uses Selenium for primary browser automation (launching, navigation, element interaction).
    *   Uses PyAutoGUI for enhanced robustness (window focus checks, fallback mechanisms for UI interaction like clicking send buttons via image recognition).
    *   Injects prompts into the ChatGPT UI.
    *   Scrapes the response from the UI.
*   **`gpt_to_cursor.jsonl`**: A JSONL file located at `src/dreamos/bridge/gpt_to_cursor.jsonl`. This acts as the output queue. Each line is a JSON object containing ChatGPT's response.
    *   Format: `{"response_for_prompt_id": "original_prompt_id", "gpt_response_id": "scraper_log_id_or_generated", "response_content": "ChatGPT's response text", "timestamp_utc": "ISO_timestamp"}`
*   **`scraper_log.jsonl`**: A JSONL file at `runtime/modules/chatgpt_scraper/scraper_log.jsonl` where all successful prompt-response pairs are logged by the `log_interaction` function.
*   **Supporting Utilities**:
    *   `src/dreamos/utils/gui_utils.py`: Provides PyAutoGUI and window management helper functions.
    *   `runtime/modules/chatgpt_scraper/scraper.py`: Contains the `log_interaction` function.

**Data Flow:**
1.  A prompt is added to `cursor_to_gpt.jsonl`.
2.  `bridge_loop.py` detects the new prompt.
3.  `bridge_loop.py` calls `ChatGPTWebAgent.process_prompt_via_ui()` with the prompt text.
4.  `ChatGPTWebAgent` launches/controls a browser:
    a. Navigates to ChatGPT.
    b. Ensures user is logged in (manual step currently required before starting bridge).
    c. Injects the prompt text into the UI.
    d. Clicks the send button (using Selenium or PyAutoGUI fallback).
    e. Waits for and scrapes the response text from the UI.
5.  `ChatGPTWebAgent` returns the response to `bridge_loop.py`.
6.  `bridge_loop.py` calls `log_interaction()` to log the prompt and response to `scraper_log.jsonl`.
7.  `bridge_loop.py` writes the response to `gpt_to_cursor.jsonl`.

## 3. Operational Procedures

### Prerequisites
*   Python environment with dependencies (see `requirements.txt` or `pyproject.toml`). Key dependencies include `selenium`, `pyautogui`, `pygetwindow`, `webdriver_manager`, `pyyaml`.
*   A compatible web browser (e.g., Chrome) and its WebDriver.
*   User must be logged into `https://chat.openai.com/` in the browser *before* starting the bridge.
*   (If PyAutoGUI image fallback is active) The send button image asset (e.g., `assets/gui_elements/chatgpt_send_button.png`) must be correctly placed and match the UI.
*   **CRITICAL**: Configuration file `src/dreamos/bridge/bridge_config.yaml` **must be present and correctly populated**. This file is loaded by `bridge_loop.py` to configure both `AppConfig` generally and specific settings for the `ChatGPTWebAgent`. Its absence or misconfiguration will prevent the bridge from initializing.

### Running the Bridge
1.  Ensure all prerequisites are met.
2.  Open a terminal in the Dream.OS project root (`D:\Dream.os`).
3.  Execute the command: `python src/dreamos/bridge/bridge_loop.py`
4.  The bridge will start polling for prompts.

### Adding Prompts
*   Manually or programmatically append new JSON prompt entries to `src/dreamos/bridge/cursor_to_gpt.jsonl`.
*   Ensure each line is a valid JSON object with `prompt_id` and `prompt` fields.

### Retrieving Responses
*   Manually or programmatically read new JSON response entries from `src/dreamos/bridge/gpt_to_cursor.jsonl`.
*   Each line corresponds to a processed prompt.

### Logging
*   **Bridge Operations:** `src/dreamos/bridge/bridge_loop_status.log`
*   **Prompt/Response Pairs:** `runtime/modules/chatgpt_scraper/scraper_log.jsonl`
*   **Bridge Failures:** `src/dreamos/bridge/bridge_loop_failures.jsonl`

## 4. Configuration Points (within code)

*   **`bridge_loop.py`:**
    *   `POLL_INTERVAL_SECONDS`, `STALL_THRESHOLD_CYCLES`, etc. (defined as constants at the top of the file).
    *   File paths for input/output queues and logs (defined as constants).
    *   Loads its `AppConfig` and specific `ChatGPTWebAgent` settings from `src/dreamos/bridge/bridge_config.yaml` via `dreamos.core.config.load_config()` in its `main_loop`. This YAML file is the primary source for runtime configuration.
*   **`chatgpt_web_agent.py` (via `AppConfig` loaded from `bridge_config.yaml` in `bridge_loop.py`):**
    *   `

### Configuration Points

The primary configuration for the bridge, especially for the embedded `ChatGPTWebAgent`, is managed via `src/dreamos/bridge/bridge_config.yaml`. This file is loaded by `bridge_loop.py` at startup.

**`src/dreamos/bridge/bridge_config.yaml` Structure:**

This YAML file is used by `dreamos.core.config.load_config` to create an `AppConfig` instance. Additionally, `bridge_loop.py` directly parses a specific section for agent settings. A minimal example structure is:

```yaml
# Settings accessible via AppConfig (e.g., app_cfg.paths.task_list_file_for_bridge)
paths:
  log_dir: "runtime/logs/bridge"
  # ... other AppConfig paths as needed by core components or the agent

# Specific settings for the ChatGPTWebAgent instance used by the bridge
# These are loaded directly by bridge_loop.py from this YAML.
chatgpt_web_agent_settings:
  agent_id: "bridge_chatgpt_agent"
  conversation_url: "https://chat.openai.com/c/your-conversation-id" # MANDATORY: Update this
  simulate_interaction: false # Set to true for testing without live browser actions
  external_prompt_delay: 5 # Delay in seconds before processing a new external prompt

# Potentially other AppConfig sections relevant to the bridge's operation
# Example:
# agents:
#   chatgpt_web:
#     # Settings here might also be accessible via AppConfig if defined in its schema
#     # external_prompt_delay: 5 # This is an example of how AppConfig might structure it.
#     # bridge_loop.py specifically looks for external_prompt_delay under chatgpt_web_agent_settings.
```

**Key `chatgpt_web_agent_settings` fields:**
*   `agent_id`: A unique identifier for the agent instance.
*   `conversation_url`: **Crucial.** The direct URL to the ChatGPT conversation to interact with.
*   `simulate_interaction`: If `true`, the agent simulates UI interactions without actually controlling a browser. Useful for testing the bridge logic itself.
*   `external_prompt_delay`: (Optional, defaults in agent) Delay before the agent processes a prompt received via `process_external_prompt`.

The `bridge_loop.py` script specifically uses `dreamos.core.config.load_config(config_path="src/dreamos/bridge/bridge_config.yaml")` to obtain the `AppConfig` object. It then *also* re-opens and parses `bridge_config.yaml` directly to fetch the `chatgpt_web_agent_settings` block. Ensure this block and its fields are correctly defined.

**Operational Note:** The `bridge_loop.py` will fail to initialize if `src/dreamos/bridge/bridge_config.yaml` is missing or if the `chatgpt_web_agent_settings` (especially `conversation_url`) cannot be read from it.

**Developer Note on Configuration Loading:**
Currently, `bridge_loop.py` uses `dreamos.core.config.load_config()` for the main `AppConfig` and then separately re-parses `bridge_config.yaml` for the `chatgpt_web_agent_settings`. For future refinement, these agent-specific settings could be integrated into the main `AppConfig` schema (e.g., under a dedicated `agents.chatgpt_bridge` key) to streamline configuration loading into a single pass via `AppConfig`.