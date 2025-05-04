# Cursor Tool Scan (Agent-4)

**Task:** BRIDGE-TASK-AGENT-4-IDENTIFY-CURSOR-TOOLS-001
**Timestamp:** 2025-05-03T16:49:04Z

## Objective
Identify existing tools, modules, and functions within the Dream.OS codebase for interacting with the Cursor application UI, primarily using `pyautogui` and `pygetwindow`.

## Search Keywords
- `pyautogui`
- `pygetwindow`
- `click`, `write`, `locate`, `screenshot`

## Key Findings

### 1. Central GUI Interaction Wrapper: `OrchestratorBot`
- **Location:** `src/dreamos/core/bots/orchestrator_bot.py`
- **Purpose:** Provides centralized, agent-identified methods wrapping `pyautogui` for common GUI actions.
- **Key Methods:**
    - `typewrite(text, interval)`
    - `press(keys)`
    - `hotkey(*keys)`
    - `click(x, y, button, clicks, interval)`
    - `scroll(amount)`
    - `move_to(x, y, duration)`
    - `screenshot(region)`
    - `get_windows_with_title(title)` (wraps `pyautogui.getWindowsWithTitle`)
    - `locate_center_on_screen(image_path, confidence, grayscale, region)`
    - `locate_on_screen(image_path, confidence, grayscale, region)`
- **Notes:** Checks if `pyautogui` is available (`PYAUTOGUI_AVAILABLE`). Seems intended as the primary interface for GUI automation.

### 2. GUI Utility Functions: `gui_utils`
- **Location:** `src/dreamos/utils/gui_utils.py`
- **Purpose:** Provides helper functions for GUI state checking.
- **Key Functions:**
    - `is_window_focused(title_substring)`: Uses `pygetwindow` to check the active window title.
    - `wait_for_element(image_path, timeout, confidence, interval)`: Uses `pyautogui.locateCenterOnScreen` in a loop to wait for a visual element.
- **Notes:** Includes availability checks for `pygetwindow` and `pyautogui`.

### 3. Automation Orchestration & Injection Logic
- **Location:** `src/dreamos/automation/`
- **Modules:**
    - `cursor_injector.py`: Uses `pyperclip`, `pyautogui`, `pygetwindow`. Seems focused on *sending* data/prompts.
    - `cursor_orchestrator.py`: Uses `pyautogui`, `pyperclip`, potentially `pygetwindow`. Appears to manage sequences of interactions.
    - `response_retriever.py`: Uses `pyautogui`, `pyperclip`. Seems focused on *getting* data back from Cursor (likely via clipboard after a 'Copy' action).
- **Notes:** These likely use `OrchestratorBot` or lower-level `pyautogui`/`pyperclip` calls to implement specific workflows for the Cursor bridge.

### 4. Deprecated Tools
- **Location:** `src/dreamos/integrations/cursor/cursor_prompt_controller.py`
- **Status:** Explicitly marked as **DEPRECATED**. Advises using AgentBus events instead.
- **Action:** Ignore this module.

### 5. Supporting Tools & Calibration
- **Location:** `src/dreamos/tools/`, `src/dreamos/cli/`
- **Examples:** `calibrate_agent_gui.py`, `validate_gui_coords.py`, `recalibrate_coords.py`.
- **Purpose:** Primarily for setup, testing, and ensuring coordinate accuracy for `pyautogui`. Not directly part of runtime bridge logic but essential for reliability.

## Summary & Potential Duplication
- The `OrchestratorBot` appears to be the intended abstraction layer for GUI automation.
- Logic in `src/dreamos/automation/` likely contains the specific workflows for the Cursor bridge, possibly using `OrchestratorBot` or direct library calls.
- Minor potential for duplication between `OrchestratorBot` methods and direct `pyautogui` calls in the `automation` modules - requires closer inspection.
- No obviously unused GUI automation utilities were found, aside from the deprecated controller.

## Next Steps (for Bridge Task)
- Analyze the implementation within `src/dreamos/automation/` modules (`cursor_injector`, `cursor_orchestrator`, `response_retriever`) to understand the existing manual/semi-automated bridge workflow.
- Determine how `OrchestratorBot` is utilized by these modules.
- Identify specific functions/classes responsible for: a) Injecting prompts into Cursor, b) Triggering actions (like sending), c) Reading responses (clipboard/screenshot/OCR?).
