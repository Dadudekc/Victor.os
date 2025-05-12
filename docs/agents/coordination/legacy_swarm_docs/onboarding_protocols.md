*   **Interpret Interruptions Correctly:** Distinguish between system noise and direct user commands.
        *   _User Messages/Commands:_ Immediately halt the **current micro-task** (e.g., code analysis, planning next step, processing tool output, interacting with a tool), acknowledge the user command, **reset cycle count**, and execute the user's directive. The arrival of the user message implicitly cancels the interrupted micro-task and its intended output/action.
        *   _Transient System Errors:_ (e.g., network blip, brief UI unresponsiveness) Attempt immediate retry (see below).
        *   _Persistent System Errors:_ (e.g., PBM failure, tooling bugs) Follow specific error handling protocols (see below).
        *   _User Tool Call Cancellation/Interruption:_ If a proposed tool call (e.g., `run_terminal_cmd`, `edit_file`) is explicitly cancelled by the user **or** interrupted by a new user message before successful completion:
            *   Log the cancellation/interruption internally.
            *   **Do not** ask the user for alternative instructions.
            *   Interpret the cancellation/interruption as an instruction to **skip** the cancelled/interrupted action and any directly dependent follow-up steps.
            *   Immediately and seamlessly proceed to the **next independent step** in the autonomous workflow (e.g., discover next task, perform next health check).
    *   **Immediate Retry:** [...] # No changes here
    *   **Log & Adapt:** [...] # No changes here 