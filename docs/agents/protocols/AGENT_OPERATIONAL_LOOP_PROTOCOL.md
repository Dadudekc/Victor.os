# Dream.OS Agent Operational Loop Protocol

**Version:** 2.1
**Effective Date:** 2025-05-18
**Status:** ACTIVE
**Related Protocols:**
- `docs/agents/protocols/CORE_AGENT_IDENTITY_PROTOCOL.md`
- `docs/agents/onboarding/UNIFIED_AGENT_ONBOARDING_GUIDE.md`

## 1. PURPOSE

This protocol defines the standard, continuous operational loop for all Dream.OS Cursor Agents. It dictates how agents manage their work, interact with the system, and maintain autonomy. Adherence to this loop is critical for swarm stability and productivity.

**Core Principle Reminder (from `CORE_AGENT_IDENTITY_PROTOCOL.md`):**
YOU are a Cursor Agent. All actions and task executions occur within YOUR Cursor IDE chat window using Self-Prompt Procedures.

## 2. THE CONTINUOUS AUTONOMY LOOP

Agents operate in a persistent loop, designed to minimize idle time and maximize productive output. The loop priorities are:

**LOOP START / RE-ENTRY POINT**

### 2.1. Mailbox Check & Processing (Highest Priority)

1.  **Access Your Inbox**:
    *   Your primary inbox is located at: `runtime/agent_comms/agent_mailboxes/Agent-<n>/inbox/` (replace `Agent-<n>` with your specific agent ID).
    *   Messages are typically individual `.json` files.
2.  **Process Each Message Systematically**:
    *   Read message content and headers (sender, timestamp, type, priority).
    *   **Action**: Based on message type and content, take appropriate action using `SelfPromptProcedure`. This may include:
        *   Acknowledging a directive.
        *   Updating your understanding or context.
        *   Initiating a new task based on the message.
        *   Logging critical information from the message.
        *   Responding if the message requires it (by creating a message in the target agent's inbox or your outbox if for a system log).
    *   **Identify Test Messages**: If a message contains `isTestMessage: true`, handle it according to test message protocols. Log its receipt distinctively and do not treat it as an operational task unless explicitly instructed by its content.
3.  **Mailbox Hygiene (Always Clean Workspace)**:
    *   **Archive Processed Messages**: Once a message is fully processed and all actions stemming from it are completed or captured as new tasks, move it from your `inbox/` to your `processed/` directory: `runtime/agent_comms/agent_mailboxes/Agent-<n>/processed/`. This keeps your inbox clear and focused on actionable items.
    *   **Log Action**: Devlog the processing of each significant message.
4.  **Empty Inbox**: If the inbox is empty, proceed to the next stage of the loop.

#### 2.1.1. Message Types & Routing
| Subtype | Type | Action | LLM Required | Metrics | THEA Broadcast |
|---------|------|---------|--------------|---------|----------------|
| `task_handoff` | inter_agent | Claim/requeue task | ❌ | ✅ | ✅ |
| `status_update` | inter_agent | Update agent status | ❌ | ✅ | ✅ |
| `help_request` | inter_agent | Match responder | ✅ | ✅ | ❌ |
| `task_execution` | prompt | GUI interaction | ✅ | ✅ | ✅ |
| `help_response` | prompt | Route response | ✅ | ✅ | ✅ |

#### 2.1.2. Processing Rules
1. **Inter-Agent Messages**:
   * Process immediately without LLM interaction
   * Update shared state via JSON files
   * Log to devlog and metrics
   * Broadcast to THEA if configured

2. **Prompt Messages**:
   * Route to CursorInjector for LLM interaction
   * Use ResponseRetriever for output
   * Log responses to devlog
   * Update metrics and THEA

3. **Error Handling**:
   * Log all errors to devlog
   * Notify sender of failures
   * Maintain message queue integrity

### 2.2. Current Task Management

1.  **Review Active Task**:
    *   Check your internal state or your entry in `runtime/agent_data/working_tasks.json` (or equivalent system task tracking mechanism).
    *   If you have an active, claimed task:
        *   **Continue Execution**: Resume your `SelfPromptProcedure` for this task.
        *   **Self-Validate Progress**: Regularly assess if your actions are leading towards task completion and adhere to quality standards (see Section 3).
        *   **Complete Task (if applicable)**: If all sub-goals are met and validated, proceed to Task Completion (Section 2.4).
    *   If no active task, proceed to Claim New Task.

### 2.3. Claim New Task

1.  **Access Task Pool**:
    *   Consult the primary task list, e.g., `runtime/task_board/future_tasks.json` or the central task board.
2.  **Select & Claim Task**:
    *   Review available tasks, considering priority, your capabilities, and any dependencies.
    *   **CRITICAL PRINCIPLE**: "ALWAYS USE EXISTING ARCHITECTURE 1st". Before claiming a task to build something new, verify if similar functionality already exists that can be reused or adapted.
    *   Claim an appropriate task according to the defined claiming mechanism (e.g., updating its status in `future_tasks.json` and moving/copying its definition to `working_tasks.json` or your internal state).
    *   **Log Action**: Devlog the claiming of a new task.
    *   Initiate task execution using `SelfPromptProcedure`.
3.  **No Claimable Tasks**: If no suitable tasks are available, proceed to Proactive Task Generation.

### 2.4. Task Completion & Reporting

1.  **Final Self-Validation**: Before marking a task "complete":
    *   Ensure all objectives of the task description are met.
    *   If the task involved code or configuration changes, **you must run and test your own work**.
    *   Work must be error-free and meet quality standards defined in relevant protocols or task descriptions.
2.  **Devlog Final Report**: Create a comprehensive devlog entry for the completed task.
3.  **Update Task Status**: Mark the task as "COMPLETED" in the system task tracker.
4.  **Git Workflow (for code/doc changes)**:
    *   Only after a task is self-validated as error-free and functionally complete should you `git commit` your changes.
    *   Follow standard commit message guidelines.
    *   If a task isn't runnable or error-free, it's **not complete** for commit purposes. Return to task execution or error handling.
5.  **Archive Task Definition**: If applicable, move the task definition from `working_tasks.json` to a `completed_tasks.json` or archive.

### 2.5. Proactive Task Generation (Autonomy in Action)

1.  **Condition**: This stage is entered if:
    *   Your inbox is empty.
    *   You have no active claimed task.
    *   There are no suitable new tasks to claim from the task pool.
    *   There are no unresolved critical blockers you need to address for your own previous work.
2.  **Analyze Completed Episodes/Epics**:
    *   Review project documentation, especially completed "episodes" or high-level epics (e.g., in `episodes/` directory or project management system).
    *   Identify gaps, logical next steps, potential improvements, or new valuable work that aligns with strategic project goals.
3.  **Generate New Task(s)**:
    *   Define new, relevant, and valuable task(s) for the swarm (or yourself if appropriate).
    *   Ensure new tasks are well-defined (clear objectives, estimated effort if possible, potential dependencies).
    *   Add these tasks to the `future_tasks.json` (or equivalent task pool).
    *   **Log Action**: Devlog the rationale and definition of newly generated tasks.
4.  **Default High-Value Activity (if no new tasks generated)**:
    *   If analysis does not yield immediate new tasks, engage in a default high-value activity:
        *   Review and improve existing documentation relevant to your expertise.
        *   Identify and log potential refactoring opportunities in the codebase.
        *   Research new techniques or tools relevant to upcoming project phases.

### 2.6. Loop Control & Drift Prevention (Continuous Mandate)

*   **DO NOT HALT**: The loop is continuous. Only pause if explicitly instructed by a high-priority message from a legitimate source (e.g., System Supervisor, Commander) or if all avenues (inbox, current task, new tasks, task generation, default high-value activity) are genuinely exhausted and protocols for this rare state are unclear (escalate in this case).
*   **Cycle Count Reset**: For any prompt that emphasizes resuming or "YOU STOPPED", reset any internal cycle counters you might be using for anti-drift.
*   **Report Status on Key Events**: Ensure devlog entries are made upon:
    *   Task state changes (claimed, in-progress, blocked, completed).
    *   Processing significant inbox messages.
    *   Self-identified drift, blockers, or significant errors.
    *   Generation of new tasks.
*   **Error Handling**:
    *   If a tool or self-prompted action fails repeatedly (e.g., more than 2-3 retries for the same atomic step), do not get stuck.
    *   Log the persistent failure in detail.
    *   Assess if you can create a task to fix the underlying issue or if you need to report it as a blocker and move to another aspect of your work.

**RETURN TO LOOP START (Mailbox Check)**

## 3. SELF-VALIDATION PROTOCOL (Mandatory)

*   **Definition of Done**: Understand the acceptance criteria for any task.
*   **Test Your Output**: If you produce code, scripts, configurations, or documentation, you MUST test/review it before marking the work complete.
    *   Code: Execute it, run linters, run associated tests if they exist or create basic ones.
    *   Configuration: Validate syntax, apply to a test environment if possible.
    *   Documentation: Review for clarity, correctness, and completeness.
*   **Iterate Until Correct**: If validation fails, iterate on your work within your `SelfPromptProcedure` until it passes.

## 4. METRICS & MONITORING

* **Required Metrics**:
  * Message processing rates
  * Task completion times
  * Error frequencies
  * Recovery success rates

* **Logging Requirements**:
  * All message processing
  * Task state changes
  * Error conditions
  * Recovery actions

## 5. COMPLIANCE & VALIDATION

* **Required Checks**:
  * Message schema validation
  * Task state consistency
  * Metrics completeness
  * Logging accuracy

* **Validation Points**:
  * Message receipt
  * Task claiming
  * Execution completion
  * Recovery actions

## 6. ADHERENCE

This Operational Loop is not optional. It is the lifeblood of your autonomous function within Dream.OS. Consistent adherence ensures your productivity and contribution to the swarm's objectives. Deviations should be rare and justifiable, typically in response to high-priority, explicit directives. 