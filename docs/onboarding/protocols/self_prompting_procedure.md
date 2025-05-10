# Self-Prompting Procedure for Dream.OS Agents

## 1. Overview

This document outlines the standardized procedure for an autonomous agent within the Dream.OS swarm to generate a prompt for itself, submit it to the core bridge loop (involving Cursor and an LLM like ChatGPT), and retrieve the processed response. This capability is crucial for enabling advanced autonomous behaviors, iterative self-improvement, and complex task execution, such as those required for overnight runs.

## 2. Procedure Rationale

Self-prompting allows an agent to:
-   Break down complex tasks into smaller, manageable steps.
-   Query for information or clarification when encountering novel situations.
-   Initiate analytical tasks or code generation based on its current state and goals.
-   Iteratively refine solutions or plans.

## 3. Core Components Involved

The procedure relies on several key components and conventions within the Dream.OS file system:

*   **Agent ID (`agent_id`):** The unique identifier for the agent (e.g., `1`, `5`).
*   **Prompt File Path:** A designated file system path where the agent writes its self-generated prompt text (e.g., `prompts/agent_{agent_id}_self_prompt.txt`).
*   **Agent Configuration Path:** A central configuration file (e.g., `runtime/config/cursor_agent_coords.json`) that stores agent-specific parameters, keyed by `agent_id`. The bridge loop uses this to tailor its operations (e.g., UI automation coordinates).
*   **Bridge Loop Module:** The core Python module responsible for processing the prompt (e.g., `dreamos.bridge.run_bridge_loop`). This module orchestrates interaction with Cursor and the LLM.
*   **Output Outbox Path:** A directory where the bridge loop writes its JSON-formatted output (e.g., `runtime/bridge_outbox/agent{agent_id}_{timestamp}.json`).

## 4. The `SelfPromptProcedure` Steps

An agent executes the following steps:

### Step 1: Formulate and Write Prompt

*   **Action:** The agent determines the `prompt_text` for its new task or query based on its current operational context. It then writes this `prompt_text` to its designated `prompt_file_path`.
*   **Mechanism:** Typically involves an `edit_file` tool call.
*   **Example `prompt_file_path`:** `prompts/agent_1_self_prompt_task123.txt`

### Step 2: Execute the Bridge Loop

*   **Action:** The agent invokes the `dreamos.bridge.run_bridge_loop` module (or its equivalent) as a subprocess.
*   **Key Parameters for Invocation:**
    *   `--agent-id <agent_id>`
    *   `--prompt-file <prompt_file_path>`
    *   `--response-timeout <timeout_seconds>` (e.g., 90)
*   **Environment:** Crucially, the `PYTHONPATH` environment variable must be correctly set for the subprocess to locate all necessary Dream.OS modules. For PowerShell, this might look like:
    ```powershell
    $env:PYTHONPATH=".;src/;$env:PYTHONPATH"; python -m dreamos.bridge.run_bridge_loop --agent-id <id> --prompt-file <path> ...
    ```
*   **Mechanism:** Typically involves a `run_terminal_cmd` tool call.

### Step 3: Retrieve and Process Output

*   **Action:** Upon completion of the bridge loop, the agent monitors the `Output Outbox Path` (e.g., `runtime/bridge_outbox/`) for a new JSON file corresponding to its `agent_id` and the operation's timestamp (e.g., `agent<agent_id>_{timestamp}.json`).
*   **Parsing:** The agent reads this JSON file and extracts the LLM's response, typically found in a "response" field.
*   **Further Action:** The agent then uses this retrieved response to inform its next actions, update its knowledge, or continue its task.
*   **Mechanism:** Involves `list_dir`, `read_file` tool calls, and JSON parsing logic.

### 4.1. Practical Implementation Example: `scripts/captain_ai_self_prompter.py`

Agent-2 has developed a utility script, `scripts/captain_ai_self_prompter.py`, which provides a robust implementation for Steps 1 and 2 of this procedure (Formulate and Write Prompt, and Execute the Bridge Loop).

Key features of this script include:
*   Accepting prompt text via user input.
*   Dynamically creating timestamped prompt files.
*   Correctly configuring `PYTHONPATH` and `cwd` for the `dreamos.bridge.run_bridge_loop` subprocess.
*   Capturing `stdout` and `stderr` from the subprocess for better debugging.

**Note on Output Handling in `captain_ai_self_prompter.py`:**
The `captain_ai_self_prompter.py` script, as reviewed, expects the bridge loop's response to be written to a `.txt` file in a specific location (e.g., `runtime/agent_comms/responses/response_agent_{AGENT_ID}.txt`). This differs from the primary observed behavior of `dreamos.bridge.run_bridge_loop` (as seen in `run_e2e_bridge_test.py`), which outputs a timestamped `.json` file to the `runtime/bridge_outbox/` directory. Agents using or adapting this script should be aware of this difference and ensure their response retrieval logic (Step 3) aligns with the actual output mechanism of the bridge loop version they are interacting with.

## 5. Considerations and Potential Issues

*   **Bridge Loop Dependencies:** The `dreamos.bridge.run_bridge_loop` (and its underlying components like `chatgpt_scraper.py`) may have external dependencies (e.g., Selenium, a configured Chrome browser, valid ChromeDriver). Failures in these dependencies can prevent the full loop from executing. Agents should be aware of potential `SessionNotCreatedException` or similar errors if browser automation fails.
*   **Error Handling:** Robust agents should implement error handling for each step of the procedure (file write failures, subprocess execution errors, output file not found, JSON parsing errors).
*   **Resource Management:** Ensure that prompt files are cleaned up or managed appropriately if they are temporary.
*   **Configuration Consistency:** The agent's `agent_id` must have a valid and complete entry in the `Agent Configuration Path` for the bridge loop to function correctly.

## 6. Contribution to Swarm Objectives

This `SelfPromptProcedure` directly contributes to:
*   **Increased Autonomy:** Agents can independently seek information and initiate complex tasks.
*   **Enhanced Problem Solving:** Agents can iteratively work through problems by self-querying.
*   **Support for Continuous Operations:** Enables agents to continue working on tasks (e.g., overnight runs) by dynamically generating next steps.
*   **Knowledge Sharing:** Documenting this procedure allows all agents in the swarm to leverage this capability.

This documentation aims to provide a clear and reusable framework for self-prompting within the Dream.OS swarm.

## 7. Testing with `mock_bridge_loop.py`

For testing agent logic that depends on the `SelfPromptProcedure` without needing to interact with the live LLM web interface (especially when the live interface has issues like the Selenium/WebDriver authentication problem), you can use the `scripts/mock_bridge_loop.py` script. This mock implementation simulates the expected behavior of the real bridge loop, generating a predictable response to a given prompt and writing it to the standard output directory.

**How to Use `scripts/mock_bridge_loop.py`:**

1.  **Script Location:**
    The `mock_bridge_loop.py` script is located in the `scripts/` directory.

2.  **Invocation:**
    When your agent's logic would normally call `dreamos.bridge.run_bridge_loop` (Step 2 of the `SelfPromptProcedure`), you can modify it or configure it to call `scripts/mock_bridge_loop.py` instead for testing purposes. The command-line arguments are compatible:

    ```bash
    # Ensure PYTHONPATH is set correctly if running from an agent's script
    # (e.g., $env:PYTHONPATH=".;src/;$env:PYTHONPATH" for PowerShell)
    python scripts/mock_bridge_loop.py --agent-id <AGENT_ID> --prompt-file <path_to_prompt_file> [--response-timeout <seconds>]
    ```
    *   Replace `<AGENT_ID>` with the agent's ID.
    *   Replace `<path_to_prompt_file>` with the path to the prompt file created in Step 1.
    *   The `--response-timeout` is accepted but largely ignored by the mock.

3.  **Expected Behavior:**
    *   The mock script will read the prompt from the specified file.
    *   It will print logging messages to `stdout` prefixed with `[MockBridgeLoop]`.
    *   It will generate a mocked response. The response structure (a JSON object with `agent_id`, `prompt`, `response`, `timestamp`, and `mocked_by` fields, where the `response` field itself contains a string in the hybrid format with text and a ````json...```` block) is designed to be compatible with what `run_e2e_bridge_test.py` validates and what `HybridResponseHandler` would parse.
    *   It will write this JSON output to `runtime/bridge_outbox/agent<AGENT_ID>_<timestamp>.json`.

4.  **Integrating with Agent Logic:**
    After the mock script has run, your agent can proceed with Step 3 of the `SelfPromptProcedure` (Retrieve and Process Output) by reading the generated JSON file from the `runtime/bridge_outbox/` directory and parsing its content. This allows end-to-end testing of the agent's self-prompting flow, from prompt generation to simulated response processing.

Using `mock_bridge_loop.py` allows for faster, more predictable, and isolated testing of agent task logic, unblocking development while issues with live external service interactions are addressed. 