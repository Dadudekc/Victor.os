# Cursor to ChatGPT Bridge Documentation

The Cursor to ChatGPT Bridge facilitates communication between the Cursor environment and live ChatGPT sessions. It allows prompts originating from Cursor (or placed into a designated file) to be processed by ChatGPT, with responses being captured and made available to the Cursor environment.

## Components

The bridge consists of the following key components:

*   **`cursor_to_gpt.jsonl`**: A JSONL file located at `src/dreamos/integrations/cursor/bridge/cursor_to_gpt.jsonl`. This acts as the input queue. Each line is a JSON object representing a prompt to be sent to ChatGPT.

*   **`bridge_loop.py`**: A Python script located at `src/dreamos/integrations/cursor/bridge/bridge_loop.py`. This is the core orchestrator of the bridge.

*   **`gpt_to_cursor.jsonl`**: A JSONL file located at `src/dreamos/integrations/cursor/bridge/gpt_to_cursor.jsonl`. This acts as the output queue. Each line is a JSON object containing ChatGPT's response.

## Flow

1.  A prompt is written to `cursor_to_gpt.jsonl`.
2.  `bridge_loop.py` detects the new prompt.
3.  `bridge_loop.py` calls `ChatGPTWebAgent.process_prompt_via_ui()` with the prompt text.
4.  `ChatGPTWebAgent`:
    a. Ensures user is logged in (manual step currently required before starting bridge).
    b. Injects the prompt into the ChatGPT web UI.
5.  `ChatGPTWebAgent` returns the response to `bridge_loop.py`.
6.  `bridge_loop.py` calls `log_interaction()` to log the prompt and response to `scraper_log.jsonl`.
7.  `bridge_loop.py` writes the response to `gpt_to_cursor.jsonl`.

## Prerequisites

*   User must be logged into `https://chat.openai.com/` in the browser *before* starting the bridge.

*   **CRITICAL**: Configuration file `src/dreamos/integrations/cursor/config/bridge_config.yaml` **must be present and correctly populated**. This file is loaded by `bridge_loop.py` to configure both `AppConfig` generally and specific settings for the `ChatGPTWebAgent`. Its absence or misconfiguration will prevent the bridge from initializing.

### Running the Bridge

1.  Ensure prerequisites are met.
2.  Navigate to the project root directory.
3.  Execute the command: `python -m dreamos.integrations.cursor.bridge.bridge_loop`
4.  The bridge will start polling for prompts.

## Usage

*   Manually or programmatically append new JSON prompt entries to `src/dreamos/integrations/cursor/bridge/cursor_to_gpt.jsonl`.
*   The bridge will process these prompts and write responses to `gpt_to_cursor.jsonl`.
*   Manually or programmatically read new JSON response entries from `src/dreamos/integrations/cursor/bridge/gpt_to_cursor.jsonl`.

## Logging

*   **Bridge Operations:** `src/dreamos/integrations/cursor/bridge/bridge_loop_status.log`
*   **Bridge Failures:** `src/dreamos/integrations/cursor/bridge/bridge_loop_failures.jsonl`

## Configuration

*   **`bridge_loop.py`:**
    *   Loads its `AppConfig` and specific `ChatGPTWebAgent` settings from `src/dreamos/integrations/cursor/config/bridge_config.yaml` via `dreamos.core.config.load_config()` in its `main_loop`. This YAML file is the primary source for runtime configuration.

*   **`chatgpt_web_agent.py` (via `AppConfig` loaded from `bridge_config.yaml` in `bridge_loop.py`):**
    *   Uses settings from the loaded `AppConfig` to configure its behavior.

The primary configuration for the bridge, especially for the embedded `ChatGPTWebAgent`, is managed via `src/dreamos/integrations/cursor/config/bridge_config.yaml`. This file is loaded by `bridge_loop.py` at startup.