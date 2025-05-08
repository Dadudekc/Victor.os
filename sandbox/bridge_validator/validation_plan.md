# Module 8: Final Integration Validator - Plan

## Objective
Validate the end-to-end functionality of the ChatGPT-to-Cursor bridge by executing a sample task that utilizes all core components.

## Dependencies
*   **Module 1 (Relay Interface):** Location/API TBD. Assumed function: Takes GPT command payload, injects into Cursor.
*   **Module 2 (Feedback Loop):** Location/API TBD. Assumed function: Reads Cursor output, pushes status/result back.
*   **Module 3 (Logging):** Provided by Knurlshade. Location/Format TBD. Assume validator can tap into logs.
*   **Module 5 (State Sync):** Location/API TBD. Assume validator can query agent/bridge state.
*   **Module 6 (Demo Harness):** Location/Script TBD. May provide trigger mechanism.
*   **Module 7 (Summarizer):** Location/API TBD. May be called post-validation.

## Sample End-to-End Task Flow (Conceptual)
1.  **Trigger:** Initiate a task via Module 6 (Demo Harness) or manual trigger if harness unavailable.
    *   *Sample Task:* "Read the file `sandbox/sample_task_input.txt` and write its contents to `sandbox/sample_task_output.txt`."
2.  **Relay (Module 1):** The task is formulated into a GPT command payload and relayed to Cursor via Module 1.
3.  **Execution (Simulated Cursor Interaction):** (Requires understanding how Cursor interaction is mocked or handled by the bridge).
4.  **Feedback (Module 2):** Cursor's execution status (e.g., 'File Read', 'Writing Output', 'Complete', 'Error') is captured by Module 2 and pushed back.
5.  **State Check (Module 5):** Query bridge/agent state via Module 5 to confirm progress.
6.  **Logging Check (Module 3):** Verify relevant steps are logged by Module 3.
7.  **Validation:**
    *   Did the relay (Module 1) successfully inject the command?
    *   Did the feedback loop (Module 2) report expected statuses?
    *   Does the final state (Module 5) indicate success?
    *   Do the logs (Module 3) corroborate the execution?
    *   *Crucially:* Does `sandbox/sample_task_output.txt` contain the content of `sandbox/sample_task_input.txt`?
8.  **Summarization (Module 7):** If validation passes, potentially call Module 7 to summarize.

## Validator Implementation Plan
*   Create `sandbox/bridge_validator/validator.py` script.
*   Script will take paths/endpoints for Modules 1, 2, 3, 5, 6 as arguments (or use config).
*   Implement functions to call each module's assumed API.
*   Implement file I/O for sample task files.
*   Implement assertion logic based on the validation steps above.
*   Output results to `sandbox/bridge_validator/validation_results.json`.

## TODO
*   Create sample input file `sandbox/sample_task_input.txt`.
*   Refine validation steps once dependent module details are available.
*   Implement `validator.py`.
*   Monitor devlog/mailbox for updates from other agents. 