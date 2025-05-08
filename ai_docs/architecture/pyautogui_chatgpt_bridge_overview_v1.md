# Dream.OS: PyAutoGUI-ChatGPT Bridge Architecture Overview (v1.0)

**Last Updated:** {{TIMESTAMP}} (Automatically set by agent)
**Version:** 1.0
**Status:** Active

## 1. Purpose

The PyAutoGUI-ChatGPT Bridge is a critical component within the Dream.OS ecosystem designed to facilitate automated interaction between various Dream.OS agents/services and the Cursor IDE. It achieves this by:

1.  **GUI Automation:** Leveraging PyAutoGUI to perform actions within the Cursor IDE, such as focusing the window, injecting text prompts into the chat interface, and capturing screenshots of response areas.
2.  **Web Interaction:** Utilizing the `ChatGPTScraper` utility to interact directly with the ChatGPT web interface for obtaining responses when direct API access is not used or available.
3.  **Service Interface:** Exposing its core functionalities via an HTTP service, allowing other Dream.OS components to request Cursor interactions programmatically.

This bridge is essential for tasks requiring programmatic control over Cursor and for enabling autonomous agents to use Cursor as a tool.

## 2. Core Components

The bridge consists of several key Python modules and scripts:

### 2.1. `src/dreamos/tools/cursor_bridge/cursor_bridge.py`

This is the heart of the bridge, containing the low-level GUI automation logic.

*   **Key Responsibilities:**
    *   Finding and focusing the Cursor application window (`find_and_focus_cursor_window`).
    *   Injecting prompt text into Cursor's chat input field (`inject_prompt_into_cursor`).
    *   Capturing screenshots of the Cursor response area (`capture_response_area`).
    *   Performing OCR on captured images to extract text (`extract_text_from_image` using Pytesseract).
    *   Monitoring the response area for stable text output (`monitor_and_extract_response`).
    *   Orchestrating the full interaction flow: inject, monitor, extract, summarize (`interact_with_cursor`).
    *   Relaying prompts to `ChatGPTScraper` and injecting the scraped response into Cursor (`relay_prompt_via_web_and_gui`).
*   **Features:**
    *   Configuration-driven behavior (see Section 3).
    *   Custom error handling (`CursorBridgeError`, `CursorInjectError`, `CursorExtractError`).
    *   Telemetry logging for key events and errors (`push_telemetry`).
    *   Basic thread-safety for GUI operations using `threading.Lock` (`gui_interaction_lock`) to prevent concurrent PyAutoGUI calls within the same process.

### 2.2. `src/dreamos/services/utils/chatgpt_scraper.py`

While potentially an external or shared utility, this component is a crucial dependency for the `relay_prompt_via_web_and_gui` functionality.

*   **Key Responsibilities:**
    *   Managing browser automation (e.g., Selenium) to interact with the ChatGPT web interface.
    *   Handling login, cookie management, sending prompts, and extracting responses.
*   **Note:** The `cursor_bridge.py` module expects this scraper to be available and configured correctly (e.g., cookie file path) if web relay functionality is used.

### 2.3. `src/dreamos/bridge/http_bridge_service.py`

This module provides an HTTP (FastAPI) wrapper around the `cursor_bridge.py` functionalities.

*   **Key Responsibilities:**
    *   Exposing an `/interact` endpoint (POST) that accepts a prompt, uses `cursor_bridge.interact_with_cursor` to process it, and returns the summarized response.
    *   Providing a `/health` endpoint (GET) to check the availability of bridge components and configuration.
*   **Features:**
    *   Robust error handling, returning appropriate HTTP status codes.
    *   Loads `AppConfig` for use by the underlying `cursor_bridge.py`.

### 2.4. `scripts/run_bridge_service.py`

A command-line script to launch the Uvicorn server for the `http_bridge_service.py`.

*   **Features:**
    *   Configurable host, port (via arguments or environment variables `CURSOR_BRIDGE_HOST`, `CURSOR_BRIDGE_PORT`).
    *   Option for Uvicorn's auto-reload feature (for development).
    *   Sets up basic logging.

## 3. Configuration (via `AppConfig`)

The bridge's behavior is heavily influenced by settings within the global `AppConfig` object. Key configuration sections include:

*   **`tools.cursor_bridge`**:
    *   `window_title_substring`: Substring to identify the Cursor window (e.g., "Cursor").
    *   `focus_wait_seconds`: Delay after attempting to focus the window.
    *   `paste_wait_seconds`: Delay during clipboard paste operations.
    *   `input_coord_x`, `input_coord_y`: Fallback X, Y coordinates for the Cursor input field if image location fails.
    *   `response_area_region`: Fallback [left, top, width, height] for the response area if image location fails.
    *   `response_timeout_seconds`: Max time to wait for a stable response.
    *   `response_stability_seconds`: Duration for which text must remain unchanged to be considered stable.
    *   `response_poll_interval_seconds`: How often to check the response area.
    *   `response_extract_max_retries`: Max retries for OCR if it fails.
    *   `tesseract_cmd_path`: Optional path to the Tesseract OCR executable.
    *   `telemetry_log_file`: Path to the bridge's telemetry log.
    *   `summary_max_length`: Max length for summarized responses.
    *   `chatgpt_cookie_file`: Path to the cookie file for `ChatGPTScraper`.
*   **`paths.gui_snippets`**:
    *   Directory path containing GUI image templates like `cursor_input_field.png` and `cursor_response_area.png`.
*   **`coordination.project_board`** (Relevant if tasks related to bridge operations are managed via `ProjectBoardManager`):
    *   `task_board_file`: Path to the central task board JSONL file.
    *   `task_board_lock_file`: Path to the lock file for the task board.

## 4. Key Operations & Flow

### 4.1. Direct Interaction (`interact_with_cursor`)

1.  Payload (prompt) is prepared.
2.  `handle_gpt_payload` calls `inject_prompt_into_cursor`.
    *   `find_and_focus_cursor_window` ensures Cursor is active.
    *   Prompt is typed/pasted into Cursor.
3.  `monitor_and_extract_response` is called.
    *   Continuously captures the response area (`capture_response_area`).
    *   Uses OCR (`extract_text_from_image`) on changes.
    *   Waits for text stability.
4.  Raw response is summarized (`summarize_cursor_output`).
5.  Summarized response is returned.

### 4.2. Web Relay (`relay_prompt_via_web_and_gui`)

1.  `ChatGPTScraper` is initialized.
2.  Prompt is sent to ChatGPT via the scraper.
3.  Response is extracted from the web page by the scraper.
4.  The scraped response is then injected into Cursor using `inject_prompt_into_cursor` (following the GUI-specific part of the flow above).

## 5. Error Handling & Telemetry

*   Specific exceptions (`CursorBridgeError`, `CursorInjectError`, `CursorExtractError`) are raised for different failure modes.
*   The HTTP service translates these into appropriate HTTP error responses.
*   Key events, successes, and failures are logged to a telemetry file (JSONL format, path configured via `tools.cursor_bridge.telemetry_log_file`). This helps in diagnosing issues and monitoring bridge performance.

## 6. Running the HTTP Service

The bridge can be run as a standalone HTTP service:

```bash
python scripts/run_bridge_service.py --host 0.0.0.0 --port 8000
```
Or with defaults: `python scripts/run_bridge_service.py`

## 7. GUI Snippets

The bridge can use image recognition (via `pyautogui.locateOnScreen`) to find UI elements if exact coordinates are not configured or are unreliable. This relies on PNG image files stored in the directory specified by `paths.gui_snippets` in `AppConfig`.

*   `cursor_input_field.png`: Template image of Cursor's chat input area.
*   `cursor_response_area.png`: Template image to help locate the region where Cursor displays responses.

If these files are missing, the bridge logs a warning and falls back to using configured coordinates (`input_coord_x/y`, `response_area_region`). If fallbacks are also unavailable, operations requiring them will fail. The accuracy of image-based location depends on the quality of these snippets and screen conditions.

## 8. Future Considerations (Out of Scope for v1.0)

*   Advanced GUI element detection (beyond simple image matching or fixed coordinates).
*   A dedicated calibration utility for GUI snippets and coordinates.
*   More sophisticated concurrency management if multiple bridge *processes* are needed system-wide (current lock is intra-process).
*   Direct integration with a system service manager (e.g., systemd) or containerization (e.g., Docker) for robust deployment.
*   Schema and validation for telemetry events. 