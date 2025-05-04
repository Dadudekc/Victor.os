# DreamOS Automation Subsystem

This directory contains components related to automating interactions with external tools and UIs, primarily the Cursor IDE.

## Core Component: `CursorOrchestrator`

(`src/dreamos/automation/cursor_orchestrator.py`)

*   **Purpose:** Singleton class managing GUI interactions with one or more Cursor instances.
*   **Functionality:**
    *   Injects prompts into specific Cursor agent windows.
    *   Retrieves responses via clipboard after clicking the 'Copy' button.
    *   Uses UI automation libraries (`pyautogui`, `pyperclip`).
    *   Relies on coordinate files (JSON) for targeting UI elements.
    *   Integrates with `AgentBus` for requesting actions and reporting results.
    *   Includes retry logic (`tenacity`) and basic focus recovery (`pygetwindow`).
*   **Configuration (`AppConfig.gui_automation` section):**
    *   `input_coords_file_path`: Path to JSON with agent ID -> {x, y} for prompt input.
    *   `copy_coords_file_path`: Path to JSON with agent ID -> [x, y] for copy button.
    *   `retry_attempts`, `retry_delay`, `default_timeout`: Retry parameters.
    *   `use_clipboard_paste`: Whether to paste (`True`) or typewrite (`False`) prompts.
    *   `target_window_title`: Window title used for focus checks.
*   **Event Lifecycle (Example: Injection):**
    1.  `CURSOR_ACTION_REQUEST` (Type: Inject) received via AgentBus OR direct `inject_prompt` call.
    2.  Status -> `INJECTING`, `CURSOR_INJECT_REQUEST` published.
    3.  `_perform_injection_sequence` executes (focus check, click, type/paste, enter).
    4.  On success: Status -> `AWAITING_RESPONSE`, `CURSOR_INJECT_SUCCESS` published.
    5.  On failure: Status -> `ERROR`, `CURSOR_INJECT_FAILURE` published.
    *   *(Retrieval follows a similar pattern with `retrieve_response`, `_perform_copy_sequence`, and `CURSOR_RETRIEVE_*` events)*
*   **Usage:** Obtain instance via `get_cursor_orchestrator(config, agent_bus)`.

## Other Components

*   `bridge_loop.py` (TBD): Intended high-level loop integrating inject/retrieve with retry logic.
*   `cursor_dispatcher.py`: Seems related to managing *headless* Cursor instances via file queues (potentially separate system).
*   `*_controller.py` (in integrations): Window finding, file-based interaction controllers (may be alternatives or support modules).

---
*Note: This README summarizes the intended functionality based on code analysis. See `docs/architecture/bridge_intel_agent5.md` for a more detailed report.*
