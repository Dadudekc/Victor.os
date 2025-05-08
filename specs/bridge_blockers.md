# Cursor Bridge Blockers Log

This document tracks known issues, development blockers, and conflicts related to the ChatGPT-Cursor bridge (`src/dreamos/tools/cursor_bridge/cursor_bridge.py`).

*Source: Initiated by directive on YYYY-MM-DD HH:MM:SS UTC* (Replace with actual timestamp)

## Potential Issues Identified from Codebase

*   **Error Handling:** `CursorInjectError`, `CursorExtractError`, and `CursorBridgeError` are defined and raised within `cursor_bridge.py`. Need to investigate where these are caught and how failures are handled upstream.
*   **Dependency:** Relies heavily on `pyautogui` for GUI automation and `pyperclip` for clipboard, which can be platform-sensitive and prone to focus issues.
*   **Configuration:** Requires precise screen coordinates or image snippets (`cursor_input_field.png`, response area region) which are fragile and environment-dependent. OCR relies on `pytesseract` installation and configuration.
*   **Focus Management:** Explicit waits (`time.sleep`) are used, which might not be robust. Focus verification is attempted but noted as potentially unreliable.
*   **Concurrency:** The snapshot manager uses `filelock` (`snapshot_manager.py`), but the bridge itself lacks explicit locking during GUI interaction, potentially leading to race conditions if multiple processes attempt interaction.

## Known CLI/Edit Blockers (Placeholder)

*   Executing `scripts/monitor_bridge.py` (which imports `dreamos.tools.cursor_bridge.cursor_bridge`) failed with `ImportError: No module named 'dreamos.utils.config_utils'`. `grep` search confirms multiple modules expect this file at `src/dreamos/utils/config_utils.py`, but it appears to be missing from the directory, causing the import error.
*   **CRITICAL:** The Project Board Manager module (`src/dreamos/core/coordination/project_board_manager.py`) is missing from the codebase. This explains persistent PBM CLI failures and prevents all standard task management operations.
*   [TODO: Add specific examples of `run_terminal_cmd` or `edit_file` failures encountered during bridge development/use, if found in logs/history]

## Inferred Systemic Issues (from Codebase Search)

*   **GUI Automation Fragility:** Widespread `try...except` blocks around `pyautogui` and `pyperclip` calls, including handling `pyautogui.FailSafeException` and `pyperclip.PyperclipException`, indicate that failures in basic GUI interaction (focus, click, copy, paste) are expected and common.
*   **Configuration/Environment Dependence:** Error logging (`logger.error`, `logger.critical`) exists for failures in locating the Tesseract executable, loading coordinate files, or finding GUI image snippets. This suggests setup and environment consistency are major challenges.
*   **Focus Management:** Explicit focus checks (`window.isActive`, `_check_and_recover_focus`) and activation attempts within `cursor_orchestrator.py` highlight that maintaining focus on the target Cursor window is a recurring problem.
*   **Error Propagation:** `CursorOrchestratorError` often wraps lower-level exceptions from `pyautogui` or `pyperclip`, indicating a pattern of cascading failures originating from the core UI automation libraries.

## Coordination Notes (Placeholder)

*   [TODO: Log coordination points with Agent-5 regarding specific blocker investigations] 