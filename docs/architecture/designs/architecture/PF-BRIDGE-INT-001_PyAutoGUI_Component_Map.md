# PyAutoGUI Bridge Integration: Preliminary Component Map

**Task ID**: `PF-BRIDGE-INT-001`
**Agent**: `agent-1` (Pathfinder)
**Date**: {{TODAY_YYYY-MM-DD}}

## 1. Objective

This document outlines existing GUI automation components within the `src/dreamos/` codebase that can be leveraged for the PyAutoGUI to ChatGPTScraper bridge integration. The goal is to identify reusable utilities and understand current methodologies for GUI interaction and coordinate management.

## 2. Key Files Analyzed

*   `src/dreamos/utils/gui_utils.py`: Core GUI automation utilities.
*   `src/dreamos/utils/coords.py`: Basic loading/saving of coordinate files.
*   `src/dreamos/cli/calibrate_gui_coords.py`: Interactive script for generating/updating coordinate files.

## 3. Identified Components & Relevance to Bridge

### 3.1. Coordinate Management

*   **Source Files**:
    *   `src/dreamos/utils/coords.py`
    *   `src/dreamos/cli/calibrate_gui_coords.py`
    *   `src/dreamos/utils/gui_utils.py` (uses coordinate loading)
*   **Components**:
    *   `coords.load_coordinates(path)`: Loads a JSON file containing coordinate data.
    *   `coords.save_coordinates(path, data)`: Saves coordinate data to a JSON file.
    *   `calibrate_gui_coords.py` (CLI script):
        *   Provides an interactive way to capture `(x, y)` coordinates for named UI elements using `pyautogui.position()`.
        *   Manages multiple coordinate files (e.g., `cursor_agent_coords.json`, `cursor_agent_copy_coords.json`, `cursor_agent_session_start_coords.json`).
        *   Suggests a system of human-in-the-loop calibration for GUI targets.
    *   `gui_utils.load_coordinates(path)`: Similar to `coords.load_coordinates` but with more extensive logging and error handling.
    *   `gui_utils.get_specific_coordinate(identifier, full_coords)`: Retrieves specific `(x,y)` for an identifier like `"agent_id.element_key"` from loaded coordinate data.
    *   `gui_utils.trigger_recalibration(identifier, coords_file_path, project_root)`: Programmatically calls the `recalibrate_coords.py` script if a coordinate seems invalid.
*   **Relevance to Bridge**:
    *   The bridge will likely need to interact with specific UI elements in the target application (e.g., ChatGPT or a browser).
    *   This existing coordinate management system can be directly used or adapted if the bridge requires clicking/typing at fixed, pre-calibrated screen locations.
    *   The concept of named identifiers for coordinates (`"agent_id.element_key"`) is a good practice for maintainability.
    *   The recalibration mechanism could be useful for long-term robustness of the bridge if UI layouts change.

### 3.2. Visual Automation Primitives

*   **Source File**: `src/dreamos/utils/gui_utils.py`
*   **Components**:
    *   `gui_utils.wait_for_element(image_path, timeout, confidence, ...)`:
        *   Uses `pyautogui.locateCenterOnScreen()` to find a given image on the screen.
        *   Includes timeout, polling, confidence levels, and grayscale options for robustness.
        *   Essential for dynamic UIs where fixed coordinates are unreliable. The bridge can use this to locate buttons, input fields, or specific content areas based on reference images.
    *   `pyautogui` direct calls (implied by usage in `copy_thea_reply` and `wait_for_element`):
        *   `pyautogui.moveTo()`, `pyautogui.click()`, `pyautogui.hotkey()`
*   **Relevance to Bridge**:
    *   These are fundamental for the PyAutoGUI side of the bridge.
    *   `wait_for_element` allows the bridge to synchronize with the UI state before attempting interactions.
    *   Direct `pyautogui` functions for mouse movement, clicks, and keyboard hotkeys will be the primary means of controlling the GUI.

### 3.3. Higher-Level GUI Operations

*   **Source File**: `src/dreamos/utils/gui_utils.py`
*   **Components**:
    *   `gui_utils.copy_thea_reply(config)`:
        *   A complex operation that:
            1.  Locates an anchor image (`thea_reply_anchor.png`).
            2.  Clicks at an offset relative to the anchor.
            3.  Performs "select all" (`Ctrl/Cmd+A`).
            4.  Performs "copy" (`Ctrl/Cmd+C`).
            5.  Retrieves text from the clipboard via `pyperclip`.
        *   Configurable via `AppConfig` (e.g., anchor image path, offsets, retries).
        *   Demonstrates a pattern for multi-step GUI interactions.
*   **Relevance to Bridge**:
    *   This function or its pattern is highly relevant if the ChatGPTScraper needs to extract text from a specific, visually identifiable UI region.
    *   The bridge could adapt this to:
        *   Locate the ChatGPT response area using a visual anchor.
        *   Click into the area if needed.
        *   Select and copy the response text.

### 3.4. Window and Clipboard Management

*   **Source File**: `src/dreamos/utils/gui_utils.py`
*   **Components**:
    *   `gui_utils.is_window_focused(target_title_substring)`: Uses `pygetwindow` to check if the active window title contains a specific substring.
    *   `gui_utils.get_clipboard_content_safe()`: Uses `pyperclip` to get clipboard content (with a note that its internal helper `safe_paste_from_clipboard` is currently missing from this file and likely resides in `src/dreamos/services/utils/cursor.py`).
*   **Relevance to Bridge**:
    *   `is_window_focused` is crucial for ensuring the bridge interacts with the correct application window before sending PyAutoGUI commands.
    *   Clipboard utilities are essential if the bridge's method of data extraction involves copy-pasting.

### 3.5. Placeholder/Planned Utilities

*   **Source File**: `src/dreamos/utils/gui_utils.py`
*   **Components (Placeholders only)**:
    *   `copy_text_from_cursor`
    *   `close_browser`, `launch_browser`, `navigate_to_page` (browser control)
    *   `inject_text_via_mouse`, `perform_mouse_action` (generic mouse actions)
    *   `wait_for_login`
*   **Relevance to Bridge**:
    *   These placeholders indicate areas where GUI automation functionality was anticipated.
    *   If the bridge requires browser interaction (e.g., if ChatGPT is accessed via a web interface rather than an API or a dedicated app that `pyautogui` can control), then implementing robust browser control utilities (potentially using Selenium or Playwright, rather than just PyAutoGUI for browser tasks) would be a separate, significant sub-task. PyAutoGUI can work with browsers but is less ideal for complex web scraping than dedicated browser automation tools.
    *   If the "ChatGPTScraper" part of the bridge implies scraping from a web page, these browser-related functions, once implemented, would be key.

## 4. Preliminary Integration Strategy Considerations

1.  **Configuration**: The bridge should leverage `AppConfig` for its PyAutoGUI-related settings (e.g., image paths for anchors, timeouts, confidence levels), similar to how `copy_thea_reply` is structured.
2.  **Targeting Elements**:
    *   For static elements, the existing coordinate system (`coords.json` files, `calibrate_gui_coords.py`, `gui_utils.get_specific_coordinate`) can be used.
    *   For dynamic elements or to improve robustness, visual identification via `gui_utils.wait_for_element` (using reference images of UI elements) is preferred.
3.  **Interaction Flow**:
    *   Ensure target window is focused using `gui_utils.is_window_focused`.
    *   Use `gui_utils.wait_for_element` to confirm UI elements are present before interaction.
    *   Employ `pyautogui` functions for clicks, typing, and hotkeys.
    *   Use `gui_utils.get_clipboard_content_safe` or similar for text extraction if relying on copy-paste.
4.  **Error Handling & Retries**: Implement retry mechanisms for visual searches and interactions, drawing inspiration from `copy_thea_reply`. The recalibration trigger (`gui_utils.trigger_recalibration`) is an advanced error recovery option for coordinate-based targeting.
5.  **Browser Interaction**: If the "scraper" targets a web browser, a decision needs to be made:
    *   Use PyAutoGUI for all browser interactions (simpler to integrate initially but can be brittle).
    *   Integrate a dedicated browser automation library (e.g., Selenium, Playwright) for web-specific tasks, and use PyAutoGUI for interactions *outside* the browser window if needed (e.g., controlling the Cursor application itself to *trigger* the browser actions). This would likely involve defining a clearer interface between the PyAutoGUI module and the browser automation module.

## 5. Next Steps (for PF-BRIDGE-INT-001 / Agent-1)

*   ~~Investigate `src/dreamos/automation/cursor_orchestrator.py` and `src/dreamos/integrations/cursor/window_controller.py` to understand how high-level GUI automation sequences are currently managed, if at all.~~ (Completed)
*   Refine this document with findings from those files.
*   Formulate a more detailed recommendation for the PyAutoGUI module's API interface based on these existing components.

## 6. Additional Components Analysis (CursorOrchestrator & WindowController)

### 6.1. `src/dreamos/automation/cursor_orchestrator.py`

*   **Purpose**: A high-level, asynchronous singleton orchestrator for managing and automating multiple "Cursor" UI instances. It handles prompt injection, response retrieval, and state management for these instances.
*   **Key Components & Features**:
    *   **Configuration-Driven**: Heavily relies on `AppConfig` (specifically `gui_automation` section) for settings like coordinate file paths, retry attempts, delays, and target window titles.
    *   **Coordinate Usage**: Loads and uses `input_coordinates` and `copy_coordinates` (presumably from files like `cursor_agent_coords.json` and `cursor_agent_copy_coords.json`).
    *   **State Management**: Tracks the status of each managed Cursor instance/agent (e.g., `IDLE`, `INJECTING`, `AWAITING_RESPONSE`, `COPYING`, `ERROR`).
    *   **Core Methods**:
        *   `inject_prompt(agent_id, prompt, ...)`: Orchestrates the full sequence of injecting a prompt. This includes status updates, event dispatch, and calling `_perform_injection_sequence` with retry logic.
        *   `retrieve_response(agent_id, ...)`: Orchestrates response retrieval, including status changes, events, and calling `_perform_copy_sequence` with retries.
    *   **Internal Helper Sequences (Low-level PyAutoGUI usage)**:
        *   `_perform_injection_sequence(...)`: Executes actual PyAutoGUI commands (move, click, clear field, paste/type text, press Enter). Crucially, it uses `wait_for_element` (from `gui_utils.py`) to wait for a visual readiness indicator after submission instead of fixed delays.
        *   `_perform_copy_sequence(...)`: Executes PyAutoGUI clicks for a copy action and manages clipboard interaction carefully (clearing clipboard before copy, polling for new content with timeout).
    *   **Robustness**: Employs `tenacity` for retrying UI operations (`RETRYABLE_UI_EXCEPTIONS`). Includes focus checking (`_check_and_recover_focus`) and window health checks (`check_window_health`).
    *   **Event Integration**: Communicates via `AgentBus`, dispatching events like `CURSOR_INJECT_REQUEST`, `CURSOR_INJECT_SUCCESS`, `CURSOR_INJECT_FAILURE`, `CURSOR_RETRIEVE_SUCCESS`, `CURSOR_RETRIEVE_FAILURE`.
    *   **Asynchronous Design**: Uses `asyncio.to_thread` to run blocking PyAutoGUI calls in a non-blocking way.
*   **Relevance to Bridge**:
    *   Provides an excellent architectural template for the PyAutoGUI-ChatGPTScraper bridge if it needs to manage interactions with a target application in a stateful, robust, and event-driven manner.
    *   The detailed sequences for injection and copying, including visual waits and careful clipboard handling, are directly applicable patterns.
    *   The use of `AppConfig` for all operational parameters is a best practice to follow.

### 6.2. `src/dreamos/integrations/cursor/window_controller.py`

*   **Purpose**: Provides OS-level control for detecting and managing application windows, specifically tailored for "Cursor" instances but adaptable.
*   **Key Components & Features**:
    *   **Cross-Platform**: Includes specific implementations for Windows (win32api), macOS (AppKit/pyobjc), and Linux (python-xlib).
    *   `WindowWrapper`: Dataclass to store window handle, title, PID, geometry.
    *   `detect_all_instances(title_pattern)`: Finds all visible windows matching a title pattern and stores them.
    *   `activate_window(window_wrapper)`: Brings a specific window to the foreground using OS-specific calls.
*   **Relevance to Bridge**:
    *   Essential for ensuring the bridge interacts with the correct application window, especially before sending any PyAutoGUI commands.
    *   If the bridge needs to manage multiple instances of the target application (e.g., multiple browser profiles or ChatGPT app instances), this controller provides a model.
    *   The cross-platform approach is valuable if the bridge needs to run in different OS environments.
    *   Likely used by `CursorOrchestrator` (or a similar higher-level component) to ensure the correct "Cursor" window is active before automation sequences begin.

## 7. Updated Preliminary Integration Strategy Considerations

1.  **Layered Architecture**: The bridge design should consider a layered approach similar to what's observed:
    *   **Low-Level Window Control** (like `WindowController`): For finding and activating the target application window (ChatGPTScraper's target: browser or app).
    *   **GUI Interaction Primitives** (like `gui_utils`): For atomic actions like `wait_for_element_on_screen`, `click_image`, `type_text_at_coords`, `get_clipboard_text`.
    *   **Orchestration Layer** (like `CursorOrchestrator`): To manage complex sequences (e.g., full login, prompt submission, response extraction), handle state, implement retries, and integrate with `AppConfig` and potentially an event bus.
2.  **Target Application Identification**: The bridge will need its own `WindowController`-equivalent to reliably find and activate the specific browser window or ChatGPT application window it intends to automate. The `title_pattern` used in `detect_all_instances` will need to be specific to the bridge's target.
3.  **Visual Anchors and Readiness Cues**: Adopt the strategy seen in `_perform_injection_sequence` of using `wait_for_element` with visual cues (images of buttons, status indicators) to synchronize actions with the UI state, rather than relying on fixed `time.sleep()` calls. This is critical for robustness.
4.  **Configuration**: All configurable aspects (image paths, timeouts, retry counts, coordinates if used, target window titles) should be managed via `AppConfig`.
5.  **Error Handling and Retries**: Implement comprehensive retry logic (e.g., using `tenacity` or the existing `@retry_on_exception` decorator) for all PyAutoGUI interactions and for steps like waiting for elements or clipboard changes.
6.  **Clipboard Management**: If extracting text via clipboard, follow the pattern of priming/clearing the clipboard before the copy action and polling for new content with a timeout, as seen in `_perform_copy_sequence`.

## 8. Refined Next Steps (for PF-BRIDGE-INT-001 / Agent-1)

*   Based on the analyzed components, draft an API proposal for a `PyAutoGUIControlModule`. This module would encapsulate the core PyAutoGUI interactions needed by the bridge (e.g., `find_and_click_image`, `type_at_location`, `get_text_from_region_via_clipboard`, `ensure_window_focused`). (Completed - `ai_docs/api_proposals/PF-BRIDGE-INT-001_PyAutoGUIControlModule_API.md`)
*   Consider how this module would integrate with the `AppConfig` for its settings. (Completed - `PyAutoGUIBridgeConfig` added to `AppConfig`)
*   Outline potential error types this module should raise. (Completed - Defined in API proposal and module implementation)
*   Propose how this module might be used by a higher-level service responsible for the ChatGPTScraper logic. (Completed - Section 8 in API proposal)
*   Implement the `PyAutoGUIControlModule` with core functionalities. (Completed for initial feature set as per API proposal. Tooling blocker for this file resolved via recreation. Further refactoring tracked in `REFACTOR-PYAUTOGUI-MODULE-001`. General tooling instability `BLOCK-002` may impact future extensive edits.)
*   Identify and prepare for collection of necessary image assets. (Completed - Section 10 added below; `runtime/assets/bridge_gui_snippets/README.md` created)

## 10. Preliminary Image Asset Identification

Based on the assumed target of interacting with a web-based ChatGPT interface (as suggested by the "ChatGPTScraper" name and the potential need for browser automation mentioned in Section 9), the following UI elements would likely require reference image files (`.png`) for visual automation using `find_element_on_screen` within the `PyAutoGUIControlModule`:

**Note**: Filenames are suggestions. Actual images need to be captured from the target interface.

*   **Login / Authentication (if required)**:
    *   `chatgpt_login_button.png`
    *   `chatgpt_email_field_active.png` / `chatgpt_email_field_inactive.png`
    *   `chatgpt_password_field_active.png`
    *   `chatgpt_continue_button.png`
    *   `chatgpt_captcha_checkbox.png` (if Cloudflare/etc. challenges appear)
    *   `chatgpt_logged_in_indicator.png` (e.g., user profile icon, main chat interface element)

*   **Main Chat Interface**:
    *   `chatgpt_new_chat_button.png` (if needing to start fresh)
    *   `chatgpt_prompt_input_field_active.png` / `chatgpt_prompt_input_field_empty.png`
    *   `chatgpt_send_button_enabled.png` / `chatgpt_send_button_disabled.png` (Crucial readiness cue)
    *   `chatgpt_stop_generating_button.png` (Potential readiness cue - disappears when done)
    *   `chatgpt_regenerate_button.png` (May appear after a response)
    *   `chatgpt_response_area_anchor.png` (A stable visual element near the latest response area, for use with `find_click_select_all_copy`)
    *   `chatgpt_copy_button.png` (If a dedicated copy button exists per response block)
    *   `chatgpt_response_complete_indicator.png` (Any subtle visual cue indicating generation is finished, if Send/Stop buttons aren't reliable enough)

*   **Error/Notification States**:
    *   `chatgpt_error_message_banner.png`
    *   `chatgpt_network_error_indicator.png`
    *   `chatgpt_rate_limit_message.png`

**Asset Storage**: These images should be stored in the configured `image_assets_path` (default: `runtime/assets/bridge_gui_snippets/`) as per the `PyAutoGUIBridgeConfig`.

**Next Step**: Capture these images from the actual target interface (e.g., `chat.openai.com`) and save them with appropriate names in the assets directory.

---
This document will be further updated as the design of the PyAutoGUI bridge progresses. 