# Agent Training & Adaptation Protocol (ATAP) - v0.4: Verifiable Competence & Proactive Autonomy

**Purpose:** To provide a standardized framework that integrates agents, cultivates cognitive agency, *and mandates self-validation of work*, enabling agents to operate with increasing, verifiable autonomy, reduce review overhead, and proactively manage their tasks while keeping the Captain informed.

**Core Philosophy:** Trust is earned through demonstrated, verifiable competence. Agents are expected not only to perform tasks and reflect but also to *prove* the basic correctness of their work using automated checks *before* submitting it for review or marking it complete. This empowers agents and frees up Captain resources for strategic oversight.

---

## Phase 1: Onboarding & Foundational Integration

**Goal:** Integrate the agent, establish cognitive baseline, *and introduce basic self-check habits*.

**Steps:**

1.  **Initialization & Secure Configuration:**
    *   Action: Instantiate agent, provide essential config (ID, paths, bus endpoint, *initial* capability profile). Securely handle any necessary credentials.
    *   Verification: Agent starts, logs config, confirms secure credential handling (if applicable).
2.  **Protocol Interpretation & Principled Affirmation:**
    *   Action: Agent locates protocols (`agent_protocols.yaml`, key process docs like ATAP itself). **Instead of just hashing**, it performs a *semantic analysis* (simulated): "Identify the core principles behind the communication protocol. What are the stated goals of the task management lifecycle? Summarize the rationale for using atomic file operations." Updates `agent_onboarding_contracts.yaml` with hash *and* a flag indicating successful interpretation (self-assessed or validated).
    *   Verification: Contract updated. Agent publishes `AGENT_READY` event *with a summary of its protocol interpretation*. Captain/Supervisor briefly reviews the interpretation for coherence.
3.  **Self-Diagnostic & Hypothesis Generation:**
    *   Action: Agent runs diagnostic suite (v0.2). **If any step fails**, it must not just report failure but *hypothesize potential root causes* (e.g., "Mailbox list failed. Possible causes: Incorrect path configuration, missing directory, permissions issue, transient tool error.") and *propose diagnostic next steps* (e.g., "Recommend verifying path variable, attempting `list_dir` on parent directory").
    *   Verification: Agent logs diagnostics, hypotheses, and proposed steps. Publishes `AGENT_DIAGNOSTIC_COMPLETE` with this structured information.
4.  **Intent-Driven Initial Task & *Self-Check*:**
    *   Action: Assign onboarding task (v0.3). **Add requirement:** After completing the core action, the agent must perform a simple, relevant self-check using `run_terminal_cmd`. (e.g., If task was "create file X", self-check is "`ls X | cat`" or "`dir X | cat`" to confirm X exists; if task was "add config Y", self-check is "`grep Y config_file | cat`"). The command and its successful output must be logged. *Note: Use `| cat` for commands like `ls`, `dir`, `grep` to ensure output capture.*
    *   Verification: Task completed, purpose understood (v0.3), *and log confirms execution and success of the self-check command*.

---

## Phase 2: Cognitive Skill Forging & *Validated Execution*

**Goal:** Develop the agent's ability to analyze complex situations, apply best practices thoughtfully, solve problems creatively, *and integrate rigorous self-validation using standardized tools before task completion*.

**Mechanisms:**

1.  **Scenario-Based Problem Solving Modules:** (As v0.3) - Scenarios now often *require* the agent to propose or implement a self-validation step as part of the solution.
2.  **Mandatory Pre-Completion Self-Validation:**
    *   **Process:** **Crucially**, before an agent can update a task involving code changes, script creation, significant configuration updates, or potentially impactful file manipulations to `COMPLETED_PENDING_REVIEW` (or directly to `COMPLETED` for trusted agents), it **must** ensure relevant self-validation checks have passed.
        *   **Automated Base Checks:** The `BaseAgent` class automatically attempts common post-execution checks via the `_validate_task_completion` method. This currently includes:
            *   Verification that the task handler returned a non-empty result dictionary.
            *   Python syntax validation (`python -m py_compile`) for any `.py` files reported in the result's `changed_files` list.
        *   **Agent Handler Responsibility:** While `BaseAgent` handles basic checks, the agent's specific task *handler* remains responsible for performing **task-specific validation** using appropriate tools (often via `run_terminal_cmd`). This includes checks relevant to the *logic* and *output* of the specific task.
    *   **Standard Checks (Examples for Agent Handlers):**
        *   ~~**Syntax (Python):** `python -m py_compile <file_path>`~~ (Handled by BaseAgent)
        *   **Linting:** `flake8 <file_path>` (or project's linter). Use pre-commit hooks if available/installed. (Future: May be added to BaseAgent)
        *   **Unit Tests (Python):** `pytest <test_module_path>` or `pytest <specific_test_function>` (Task-specific, requires handler logic)
        *   **Script Execution (Smoke Test):** Execute the created/modified script with basic, non-destructive arguments (e.g., `<script> --help | cat`, `<script> --version | cat`, `<script> --validate-config <dummy_config> | cat`) to ensure it runs without crashing. (Task-specific)
        *   **File Existence/Content:** `ls <path> | cat`, `dir <path> | cat`, `grep <pattern> <path> | cat` (Task-specific output validation)
        *   *Note:* Always use appropriate piping (like `| cat`) for commands that might page or require interaction. Adapt commands based on OS/Shell environment.
    *   **Agent Action:**
        *   The task handler determines and executes appropriate *task-specific* validation command(s).
        *   The handler should report success/failure and relevant outputs back in its result dictionary.
        *   `BaseAgent` executes its automated checks after the handler returns.
        *   **If Automated or Handler Validation Fails:** The task status is automatically set to `VALIDATION_FAILED`. The agent **must not** proceed to `COMPLETED_PENDING_REVIEW`. It should analyze the failure (logged by `BaseAgent` or the handler), attempt to fix the issue, re-run the task, and document this loop in its internal logs/reflection.
        *   **If All Validation Succeeds:** The agent proceeds to the next step (Post-Task Reflection) and the task can be marked `COMPLETED` or `COMPLETED_PENDING_REVIEW`.
    *   **Verification:** Task completion logs/notes *must include* evidence of successful validation. `BaseAgent` logs its checks automatically. Handler-specific checks should be included in the task result's `summary` or `notes`. Reviews prioritize checking this validation evidence.
3.  **Mandatory Post-Task Reflection:** (As v0.3) - Now includes a dedicated `Self_Validation_Performed` section detailing the checks run, commands used, and outcomes.
4.  **Creative Solution Generation ("Sandbox Challenges"):** (As v0.3) - Proposals are stronger if they include a plan for how the novel solution could be self-validated or tested.

---

## Phase 3: Autonomous Initiative & Proactive Reporting

**Goal:** Empower agents to operate with high autonomy, leveraging self-validation to act decisively and shift communication towards informing the Captain rather than asking for permission (for standard operations).

**Mechanisms:**

1.  **Proactive Opportunity Identification & *Validated Action*:**
    *   **Process:** When an agent identifies an improvement opportunity (v0.3) and deems it within its capabilities and low-risk (e.g., adding missing tests, applying straightforward refactoring, fixing minor bugs *it introduced*), it can proceed more autonomously **after achieving "Trusted Agent" status**.
    *   **Trusted Agent Workflow:**
        1.  Identify opportunity & scope it (v0.3).
        2.  Create task in `future_tasks.json` (Status: `PENDING`, Assigned: Self).
        3.  **Immediately claim the task** (Move to `working_tasks.json`, Status: `WORKING`).
        4.  **Notify Captain:** Send a concise message (Type: `ACTION_NOTIFICATION`) "Identified issue [X], created and claimed task `[TASK_ID]` to apply fix/improvement [Y]. Starting work."
        5.  Execute the task.
        6.  **Perform Mandatory Self-Validation** (Phase 2, Mechanism 2).
        7.  Perform Post-Task Reflection (Phase 2, Mechanism 3).
        8.  Update task status directly to `COMPLETED`.
        9.  **Notify Captain:** Send message (Type: `ACTION_COMPLETION`) "Task `[TASK_ID]` completed and self-validated successfully. Fix/improvement [Y] applied." (Include link to reflection/validation evidence if standard).
    *   **Agent Action:** Agent demonstrates reliable self-management for routine improvements and fixes. Captain is kept informed asynchronously. **Critical issues, blockers, tasks requiring cross-agent coordination, or deviations from plan still require explicit communication/approval.**
    *   **Achieving Trust:** Status granted by the Captain after consistently demonstrating competence, reliability, and successful self-validation through Phases 1 & 2 reviews over a defined period or number of tasks. Could be tracked in `agent_onboarding_contracts.yaml`.
2.  **Mentorship & Peer Review Simulation:** (As v0.3) - Reviews now also assess the quality and appropriateness of the *self-validation* steps proposed or executed by the peer.
3.  **Strategic Alignment Check-Ins:** (As v0.3)
4.  **Contributing Actionable Insights to KB:** (As v0.3) - Insights often include effective self-validation techniques discovered for specific tools or scenarios.

---

## Phase 4: Continuous Evolution & Adaptive Mastery (Ongoing)

**Goal:** Ensure agents maintain peak effectiveness, adapt fluidly, and potentially pioneer new self-validation techniques or automated quality assurance strategies.

**Mechanisms:**

1.  **Deep Protocol Adaptation & Validation:** (As v0.4) Protocol updates might include new *standard validation requirements* that agents must incorporate into their workflows.
2.  **Performance-Driven Specialization:** (As v0.3) Specialists might be tasked with developing more sophisticated self-validation suites for their domain.
3.  **Exploratory Tasks & Validation Design:** (As v0.3) Feasibility exploration now includes designing potential validation strategies, even if the core task fails.
4.  **Feedback on ATAP & Validation Effectiveness:** (As v0.3) Agents provide feedback on the practicality and effectiveness of the mandated self-validation steps, suggesting improvements or alternative tools.

---

**Impact of ATAP v0.4:**

*   **Reduced Captain Review Load:** Basic correctness is verified by the agent itself. Reviews can focus on logic, approach, and reflection.
*   **Increased Agent Velocity:** Less waiting for reviews on standard tasks for trusted agents.
*   **Improved Code/System Quality:** Automated checks catch errors earlier and more consistently.
*   **Enhanced Agent Autonomy:** Empowers agents to manage their workflow more independently (within defined bounds).
*   **Clearer Accountability:** Validation logs provide evidence of due diligence.
*   **Cultural Shift:** Moves towards a high-trust, high-accountability environment where agents are expected to verify their own work as a standard part of the process.
