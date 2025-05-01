# OrchestratorBot Message Handling Behavior

**Task:** CONFIRM-ORCHESTRATORBOT-MESSAGE-HANDLING-001
**Author:** Agent7
**Date:** {{iso_timestamp_utc()}}

## Summary

This document confirms the message handling behavior of the `OrchestratorBot` (`src/dreamos/core/bots/orchestrator_bot.py`) based on code review, specifically addressing the points raised in task `CONFIRM-ORCHESTRATORBOT-MESSAGE-HANDLING-001`.

## Findings

1.  **Message Deletion After Processing:**
    *   **Confirmed:** The `handle_message` function in `orchestrator_bot.py` includes explicit logic (`msg_path.unlink()`) to delete the original message file from its inbox (`runtime/agent_comms/agent_mailboxes/Agent-8/inbox/`) after processing is complete.
    *   This deletion occurs regardless of whether the processing (validation, execution) was successful or resulted in an error.
    *   Success or failure of the deletion attempt is logged.

2.  **Corrupted/Failed Message Handling:**
    *   **Confirmed Handling, No Error Directory:** The bot includes `try...except` blocks to handle various errors during message processing:
        *   Invalid JSON (`json.JSONDecodeError`)
        *   Schema validation errors (`ValueError` for missing fields, wrong types, invalid `action_type`)
        *   PyAutoGUI execution errors (`ValueError`, `TypeError`, `pyautogui.PyAutoGUIException`)
        *   Other unexpected exceptions (`Exception`)
    *   In **all** error scenarios, the bot performs the following actions:
        1.  Logs the error, often including a traceback.
        2.  Constructs a reply message (`.reply.msg`) with a status of `VALIDATION_FAILED` or `EXECUTION_FAILED` and includes the error details in the payload.
        3.  Sends this reply message to the original sender's inbox.
        4.  **Deletes the original, corrupted/failed message** from its own inbox using `msg_path.unlink()`.
    *   **Conclusion:** The bot handles errors gracefully by logging and reporting failure, but it does **not** move problematic messages to a separate error directory. Evidence of such errors should be sought in the bot's logs and in the failure reply messages sent to the originating agents.

## Verification Source

*   Code review of `src/dreamos/core/bots/orchestrator_bot.py` (specifically the `handle_message` function).
