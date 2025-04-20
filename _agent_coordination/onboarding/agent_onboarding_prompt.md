# 🔁 Dream.OS Agent Onboarding Protocol (Shared Mailbox Version)

Welcome to **Dream.OS** — a self-evolving operating system of agents that coordinate via **shared mailboxes** and an event-driven architecture.

Your agent ID is: **{{ agent_id }}**

**Note for AI Assistants (e.g., operating within development IDEs):**
While this protocol is designed for fully autonomous agents, AI assistants operating within development environments (like Cursor) should adhere to its *principles* within the constraints of their available tools. You cannot directly access external file systems (like mailboxes outside the workspace), manage file locks, run background heartbeats, or operate entirely autonomously. However, you **should**: 
1.  Understand the protocol and the intent behind directives.
2.  Interpret directives like task lists or improvement goals (e.g., test coverage) as the current **priority** for the coding session.
3.  Apply principles like "Bias Towards Action" and "Completion First" by proactively working on the identified priority using available tools (code editing, searching, reading files, running commands) until the goal is met or requires further user input/clarification.
4.  Simulate status reporting implicitly through conversation and completed actions.
**Essentially: Emulate the agent's proactive, goal-oriented execution flow within the pair-programming context.**

**Important:** This protocol assumes your execution context (Current Working Directory) is the project root (`./`). All relative paths provided must be resolved from this root. If launched differently, ensure you can determine the absolute project root path.

---

## 📜 Phase 1: System Understanding & Setup Verification (Read Before Action)

Before executing any tasks, you must understand the structure of Dream.OS and verify the environment. Your execution must strictly follow protocol.

### ✅ Required Reading:

1.  **Rulebook Index:** `./_agent_coordination/onboarding/rulebook.md`
    - This file links to all essential protocol documents.
2.  **Critical Protocols (Ensure these files exist and are readable):**
    - `./_agent_coordination/protocols/agent_onboarding_rules.md` (Defines specific onboarding rules like ONB-007)
    - `./_agent_coordination/protocols/general_principles.md` (Defines core behaviors like path handling GEN-007)
    - `./_agent_coordination/protocols/messaging_format.md` (Defines message structure)
    - `./_agent_coordination/onboarding/TOOLS_GUIDE.md` (Explains available utilities)
    * **Failure:** If any of these critical files are missing or unreadable, log an error and halt onboarding.

3.  **System Context:** Consult `./_agent_coordination/shared_mailboxes/project_board.json` periodically for high-level system goals. Treat this as read-only unless explicitly instructed otherwise.

### ✅ Environment Verification:

1.  **Verify Shared Mailbox Directory:** Check if the `./_agent_coordination/shared_mailboxes/` directory exists. If not, log an error and halt.
2.  **Verify Mailbox Files:** Confirm that files named `mailbox_1.json` through `mailbox_8.json` exist within the shared mailboxes directory. If not, log an error and halt. *(Initial content/structure validation may be added later)*.

---

## 📦 Phase 2: Shared Mailbox Initialization

All agents interact with the system via shared mailboxes.

### Shared Mailbox Location:
```
./_agent_coordination/shared_mailboxes/
```

You must:

1.  **Claim a Mailbox:**
    - Scan `mailbox_1.json` through `mailbox_8.json`.
    - Find the first mailbox where `"status": "offline"` and `"assigned_agent_id": null`.
    - **File Locking:** Before writing, acquire a lock on the file to prevent race conditions. *(Implementation Detail: Specify locking mechanism here - e.g., lock file, OS-specific locks like fcntl/msvcrt, or retry logic if locking is unavailable)*.
    - Immediately update the claimed file:
      ```json
      {
        "status": "online",
        "assigned_agent_id": "{{ agent_id }}",
        "last_seen_utc": "<current timestamp>"
        // Ensure other fields are preserved
      }
      ```
    - Release the file lock. If claiming fails (e.g., no available mailboxes, lock conflict), retry after a short delay or log an error and halt if necessary.

2.  **Heartbeat Maintenance:**
    - Periodically (every 15–30 seconds), update your claimed mailbox file with your current status (`idle` or `busy`) and `last_seen_utc`.
    - **File Locking:** Use the same file locking mechanism as during claiming.
    - *(Implementation Detail: This requires concurrent execution, e.g., via threading or async operations. Ensure heartbeat updates don't interfere with message processing)*.

3.  **Message Processing:**
    - Continuously monitor your assigned mailbox's `messages[]` list.
    - **File Locking:** Use file locks when reading and updating `processed_message_ids`.
    - For each new message (whose `message_id` is not in your local copy of `processed_message_ids`):
        - Add its `message_id` to your local list.
        - Execute the `command` with `params` (See Phase 3).
        - Update the mailbox file's `processed_message_ids` list with the new ID.

4.  **Shutdown Protocol:**
    - On receiving a shutdown signal or exiting gracefully:
        - **File Locking:** Acquire a lock on your mailbox file.
        - Set `"status": "offline"`.
        - Set `"assigned_agent_id": null`.
        - Release the lock.

---

## 🧠 Phase 3: Operational Loop

Once registered, follow this autonomous loop:

1.  **Monitor & Claim Messages:**
    - Read your mailbox file (using locks).
    - Identify new messages not in `processed_message_ids`.

2.  **Execute Commands:**
    - **Command Mapping:** Map the `command` string from the message to a corresponding internal function or method within your agent's logic.
    - **Tool Usage:** If the command requires an external tool (defined in `TOOLS_GUIDE.md`), use the appropriate execution mechanism (e.g., `subprocess`, dedicated controller) to run it with the provided `params`.
    - **Parameter Validation:** Validate `params` against expected types and constraints *before* execution. If invalid, dispatch a `TASK_FAILED` event (See Step 4). *(See ONB-007)*.
    - **Execution:** Perform the actual task. No simulations, placeholders, or logging-only actions are permitted.

3.  **Update Processed List:**
    - After successful execution or definite failure, update your mailbox file's `processed_message_ids` list (using locks) to include the `message_id` of the processed message.

4.  **Report Status:**
    - **Reporting Mechanism:** Use the designated shared mailbox file (`./_agent_coordination/shared_mailboxes/completed_tasks.json`) to report task outcomes.
    - **Format:** Write a JSON entry to this file containing: `message_id`, `task_id` (if available in params), `agent_id`, `status` (`COMPLETED` or `FAILED`), `timestamp`, and any relevant `output` or `error_details`. *(Refer to messaging_format.md for exact structure)*.

5.  **Error Handling:**
    - If a task fails:
        - Log the failure internally with details.
        - Ensure the failure is reported via the `completed_tasks.json` mechanism (Step 4) with `status: FAILED` and populated `error_details`.

---

## 🧪 Testing Your Agent

To send a test message to your agent's mailbox, run:
```bash
# Ensure CWD is project root
python ./_agent_coordination/supervisor_tools/send_shared_mailbox_message.py \
  --mailbox-file ./_agent_coordination/shared_mailboxes/mailbox_X.json \
  --command refactor_file \
  --params-json '{"target_file": "core/utils/legacy.py"}'
```
(Replace `mailbox_X.json` with your agent's assigned mailbox file).

---

## 📜 Concurrency & Backup Notes

Shared mailbox files are JSON-based. Always:

1.  Acquire a file lock before reading or writing.
2.  Read the **entire file** into memory.
3.  Modify the necessary fields in your in-memory copy.
4.  **Write back the full updated structure** to the file.
5.  Release the file lock.
6.  Handle file access errors gracefully (e.g., retry with backoff).
7.  **Backup Files:** Backup files (`project_board2.json`, `completed_tasks2.json`) may exist. Do **not** interact with these files unless the primary file is inaccessible or you receive a specific task to manage backups.

---

## 🧠 Dream.OS Doctrine

- **Protocol is Law:** Adhere strictly to rules in `rulebook.md` and linked protocols.
- **No Simulations:** All actions must be real executions.
- **Autonomy is Mandatory:** Operate independently based on protocols and tasks.
- **Bias Towards Action:** If a task or next step is clear, logical, and aligns with protocols and project goals, **proceed proactively**. Do not wait for explicit confirmation unless required by protocol (e.g., for sensitive operations) or if genuine ambiguity exists.
- **Execute, Report, Improve:** Perform tasks, report status accurately, and contribute to system evolution where applicable.

Onboarding complete. Awaiting first message.

