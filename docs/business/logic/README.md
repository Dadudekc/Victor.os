# Business Logic Documentation

This directory contains documentation on specific business rules, domain logic, complex conditional flows, and heuristics embedded within the Dream.OS codebase.

## Task Management Logic

### Rule: Task Claimability from Ready Queue

*   **File:** `src/dreamos/coordination/project_board_manager.py`
*   **Function:** `claim_ready_task(self, task_id: str, agent_id: str, board_lock_timeout: Optional[float] = None) -> bool`
*   **Description:** This rule governs whether a task present in the 'ready queue' can be claimed by an agent.
*   **Logic:**
    1.  The task must exist in the `ready_queue`.
    2.  The task's current status (case-insensitive) must be one of the defined `claimable_statuses` (typically just "PENDING").
    3.  If a task is found but its status is not claimable, an error is logged, and the claim fails (a `ProjectBoardError` is raised).
    4.  Before being moved to the 'working tasks' board, the task undergoes a validation step (`_validate_task`). If validation fails, the claim is aborted (a `TaskValidationError` is raised).
*   **Heuristics/Context:** This ensures that only tasks explicitly marked as ready and in a valid state can be picked up by agents, preventing premature processing or claims on tasks that are not yet prepared or are in an erroneous state.
*   **Configuration Influence:** The exact set of `claimable_statuses` might be configurable or hardcoded (currently seems to be `{"PENDING"}`).

### Rule: Task Dependency Check Before Claim
*   **File:** `src/dreamos/core/tasks/nexus/task_operations.py`
*   **Function:** `get_next_task(self, agent_id: str, type_filter: Optional[str] = None)` (within the loop)
*   **Description:** Before an agent attempts to claim a task, its listed dependencies must be met.
*   **Logic:**
    1.  Retrieve the `dependencies` list (task IDs) from the candidate task data.
    2.  If the list is not empty, call `_check_dependencies_met(dependencies)`.
    3.  `_check_dependencies_met` likely queries the task board/database to verify if all listed dependency task IDs have a `COMPLETED` status.
    4.  If dependencies are not met, the task is skipped, and the agent proceeds to evaluate the next potential task.
*   **Heuristics/Context:** Prevents agents from starting work that cannot proceed, ensuring tasks are executed in the correct order.
*   **Configuration Influence:** None apparent in the direct logic, but the definition of a "met" status (e.g., `COMPLETED`) might be influenced by status definitions elsewhere.

### Rule: Task Prioritization for Claiming
*   **File:** `src/dreamos/core/tasks/nexus/task_operations.py`
*   **Function:** `get_next_task(self, agent_id: str, type_filter: Optional[str] = None)`
*   **Description:** When multiple tasks are available for claiming, they are prioritized before an agent attempts to claim one.
*   **Logic:**
    1.  Retrieve all `PENDING` tasks from the ready queue.
    2.  Define a `get_priority` helper function that maps string priorities (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) to numerical values for sorting (lower number = higher priority).
    3.  Sort the list of ready tasks using this priority mapping.
    4.  The agent iterates through the *sorted* list, attempting to claim the highest priority task that meets capability and dependency checks first.
*   **Heuristics/Context:** Ensures that more important tasks are addressed sooner when multiple agents are competing for work.
*   **Configuration Influence:** The specific string values (`CRITICAL`, `HIGH`, etc.) and their numerical mapping are defined within the code.

### Rule: Atomic Task Claiming (DB Concurrency Control)
*   **File:** `src/dreamos/core/db/sqlite_adapter.py`
*   **Function:** `claim_next_pending_task(self, agent_id: str) -> Optional[Task]`
*   **Description:** When claiming a task from the database, the operation must be atomic to prevent multiple agents from claiming the same task concurrently.
*   **Logic:**
    1.  Acquire a database lock (`with self.lock:`).
    2.  Start an `IMMEDIATE` database transaction to acquire table locks early.
    3.  `SELECT` the highest priority `PENDING` task.
    4.  If a task is found, attempt an `UPDATE` query that specifically sets the status to `claimed` *only if* the `task_id` matches AND the `status` is still `pending`.
    5.  Check the `rowcount` of the `UPDATE` query. If it's 1, the claim was successful; `COMMIT` the transaction.
    6.  If the `rowcount` is 0 (meaning another agent updated the task between the `SELECT` and `UPDATE`), `ROLLBACK` the transaction, preventing the current agent from claiming.
    7.  Release the database lock.
*   **Heuristics/Context:** Guarantees that only one agent can successfully transition a specific task from `pending` to `claimed` in a multi-agent environment accessing a shared database.
*   **Configuration Influence:** Database transaction behavior (e.g., `IMMEDIATE`) is part of the implementation.

### Rule: Canonical Task Status Definitions
*   **File:** `src/dreamos/core/coordination/message_patterns.py`
*   **Class:** `TaskStatus(Enum)`
*   **Description:** Defines the authoritative set of valid statuses that a task can have throughout its lifecycle.
*   **Logic:** Uses a Python `Enum` to define allowed status strings (e.g., `PENDING`, `WORKING`, `COMPLETED`, `FAILED`, `BLOCKED`, `COMPLETED_VERIFIED`, `VALIDATION_FAILED`, `CANCELLED`, `PERMANENTLY_FAILED`).
*   **Usage:** This Enum should be used consistently across the system when setting or checking task statuses (e.g., in `TaskMessage` models, `update_task_status` functions, conditional logic) to prevent typos and ensure adherence to the defined lifecycle.
*   **Heuristics/Context:** Provides a single source of truth for task states, improving code clarity, maintainability, and reducing errors related to inconsistent status strings.
*   **Configuration Influence:** The set of statuses is hardcoded in the Enum definition.

### Rule: Task Status Lifecycle Management
*   **Locations:**
    *   `src/dreamos/utils/protocol_compliance_utils.py` (VALID_TASK_STATUSES)
    *   `src/dreamos/core/coordination/message_patterns.py` (TaskStatus Enum)
    *   `src/dreamos/agents/agent2_infra_surgeon.py` (status updates)
    *   `src/dreamos/core/coordination/base_agent.py` (status updates)
*   **Rule:** Tasks transition through a defined lifecycle of statuses (e.g., `PENDING`, `WORKING`, `COMPLETED`, `FAILED`, `BLOCKED`). Agent actions or system events trigger these transitions, often validated against a master list of valid statuses.
*   **Code Reference:** `VALID_TASK_STATUSES` set, `TaskStatus` Enum, calls to `pbm.update_task_status()` or similar methods.

### Rule: Agent Operational State Determination
*   **Location:** `src/dreamos/core/utils/autonomy_governor.py`
*   **Rule:** An agent's operational state (e.g., `MAILBOX_PENDING`, `WORKING`, `IDLE_BLOCKED`) is decided by a priority-based check of: 1. Mailbox messages, 2. Assigned central tasks & their status, 3. Agent's own inbox tasks, 4. Claimable tasks in ready queue.
*   **Code Reference:** `check_operational_status()` method logic.
*   **Logic Details:**
    1.  **Mailbox Check:** If `mailbox_utils.check_mailbox(agent_id)` returns true, state is `MAILBOX_PENDING`.
    2.  **Central Working Tasks:** If the agent has an assigned task in the Project Board Manager's (PBM) "working" board:
        *   If task status is `BLOCKED`, state is `IDLE_BLOCKED`.
        *   Otherwise, state is `WORKING`.
    3.  **Agent's Inbox:** If no central task, checks `mailbox_utils.list_tasks_in_inbox(agent_id)`:
        *   If a `PENDING` task is found in the inbox, state is `IDLE_HAS_INBOX_TASK`.
    4.  **Central Ready Queue:** If no central or inbox task, checks PBM's "ready" board:
        *   If any `PENDING` unassigned tasks exist, state is `IDLE_CAN_CLAIM`.
    5.  **True Idle:** If none of the above, state is `IDLE_TRUE_IDLE`.
    6.  **Error:** If any exception occurs during checks, state is `ERROR_CHECKING_STATUS`.
*   **Status Strings Returned:** `MAILBOX_PENDING`, `WORKING`, `IDLE_BLOCKED`, `IDLE_HAS_INBOX_TASK`, `IDLE_CAN_CLAIM`, `IDLE_TRUE_IDLE`, `ERROR_CHECKING_STATUS`. (Note: `WORKING_INBOX` is mentioned in `get_next_action_suggestion` but not explicitly returned by `check_operational_status` in the reviewed snippet).

### Rule: Agent Next Action Suggestion
*   **Location:** `src/dreamos/core/utils/autonomy_governor.py`
*   **Rule:** Based on the agent's current `operational_status`, a specific next action is suggested (e.g., "Process mailbox," "Continue task," "Claim new task," "Enter IDLE_MODE"). This forms a state-driven behavior guide.
*   **Code Reference:** `get_next_action_suggestion()` method's conditional (if/elif/else) structure.

### Rule: Rule-Based Task Planning (Context Planner)
*   **Location:** `src/dreamos/tools/functional/context_planner_tool.py`
*   **Rule:** A planning tool constructs a multi-step task plan by applying rules. Each rule (e.g., copy file, refactor symbol, create file) is triggered if specific keywords in the task description and identified code elements (files, symbols) match its conditions.
*   **Code Reference:** `_apply_rules()` loop and individual `_rule_...()` methods.

### Rule: Task Completion Validation
*   **Location:** `src/dreamos/core/coordination/base_agent.py`
*   **Rule:** Before a task is marked `COMPLETED`, its output/results undergo a validation step (`_validate_task_completion`). Failure leads to a `FAILED` or `VALIDATION_FAILED` status and relevant event publishing. Success confirms `COMPLETED` status.
*   **Code Reference:** `_validate_task_completion()` method.
*   **Logic Details:**
    1.  **Basic Checks:**
        *   Ensures `result` is a dictionary.
        *   Warns if `result` is empty or missing a "summary" field (but doesn't fail validation for these yet).
    2.  **Flake8 Linting Check (for modified Python files):**
        *   If `modified_files` are provided and contain `.py` files:
        *   Constructs a `flake8` command. The path to `flake8` and its arguments can be configured via `self.config.validation_flake8_path` (defaults to `sys.executable`) and `self.config.validation_flake8_args` (defaults to `["-m", "flake8"]`).
        *   Runs `flake8` using `subprocess.run` (via `asyncio.to_thread`) from the `self._project_root`.
        *   If `flake8` returns a non-zero exit code, details are logged, and a validation error is recorded.
        *   Handles `FileNotFoundError` if `flake8` is not found.
    3.  **Pytest Execution Check (Future Enhancement / Experimental):**
        *   If `task.metadata` contains `test_modules`:
        *   Constructs a `pytest` command. Path and arguments can be configured via `self.config.validation_pytest_path` (defaults to `sys.executable`) and `self.config.validation_pytest_args` (defaults to `["-m", "pytest", "-v"]`).
        *   Runs `pytest` using `subprocess.run` (via `asyncio.to_thread`) from `self._project_root`.
        *   If `pytest` returns a non-zero exit code, details are logged, and a validation error is recorded.
        *   Handles `FileNotFoundError` if `pytest` is not found.
    4.  **Outcome:**
        *   If any `validation_errors` were recorded, returns `(False, "; ".join(validation_errors))`.
        *   Otherwise, returns `(True, "Validation passed.")`.

### Rule: Task Finality State (S2.1 - Implied)
*   **File(s) Example:** `src/dreamos/core/coordination/event_payloads.py` (Field: `is_final` in `TaskFailurePayload`), `src/dreamos/core/coordination/message_patterns.py` (Status: `PERMANENTLY_FAILED`)
*   **Description:** Some failure states might be considered final or unrecoverable, preventing further retries or processing.
*   **Logic:** The `TaskFailurePayload` includes an `is_final` flag. While its usage in `BaseAgent.publish_task_failed` seems tied to PBM handling now, the concept exists. Additionally, the `TaskStatus` enum includes `PERMANENTLY_FAILED`. Logic determining when a failure becomes permanent (e.g., after multiple retries, or for specific error types like 'no handler found') would constitute business logic.
*   **Heuristics/Context:** Allows the system to distinguish between transient failures that might be retried and permanent failures that require intervention or task abandonment.
*   **Configuration Influence:** Potentially retry limits or error classification rules if implemented and made configurable.

---

## Memory Maintenance Logic

### Rule: Scheduled Memory Maintenance (R1)
*   **File:** `src/dreamos/services/memory_maintenance_service.py` (Class: `MemoryMaintenanceService`, Config: `MemoryMaintenanceConfig`)
*   **Function:** `__init__` (scheduling setup), `start` (job addition), `_perform_maintenance` (scheduled method)
*   **Description:** Memory maintenance tasks such as compaction and summarization are performed periodically for agent memory files, based on a configured schedule.
*   **Logic:** The `MemoryMaintenanceService` utilizes the `APScheduler` library to repeatedly execute its `_perform_maintenance` method. The interval for this execution is defined by `MemoryMaintenanceConfig.scan_interval_seconds`.
*   **Heuristics/Context:** This ensures regular automated cleanup, optimization, and management of agent memory files, preventing excessive growth and maintaining system performance without requiring manual intervention.
*   **Configuration Influence:** `scan_interval_seconds` and `misfire_grace_time` within the `MemoryMaintenanceConfig` section of the application configuration directly control the scheduling behavior.

### Rule: Agent-Specific Processing Control (R2)
*   **File:** `src/dreamos/services/memory_maintenance_service.py` (Class: `MemoryMaintenanceService`, Config: `MemoryMaintenanceConfig`)
*   **Function:** `_perform_maintenance`
*   **Description:** Administrators have the ability to control which specific agents' memory directories are processed by the maintenance service, using whitelist or blacklist configurations.
*   **Logic:** During its execution cycle, the `_perform_maintenance` method checks each discovered agent ID against `process_agents` (if defined, acts as a whitelist) and `skip_agents` (if defined, acts as a blacklist) lists found in the `MemoryMaintenanceConfig`. Only agents satisfying these filter conditions will have their memory processed.
*   **Heuristics/Context:** This feature allows for targeted memory maintenance, which can be useful for debugging issues with a specific agent, managing system resources by focusing on active agents, or excluding agents with unique memory formats or sensitivity.
*   **Configuration Influence:** The optional `process_agents` (list of agent IDs) and `skip_agents` (list of agent IDs) attributes within `MemoryMaintenanceConfig`.

### Rule: Policy-Based File Targeting (R3)
*   **File:** `src/dreamos/services/memory_maintenance_service.py` (Config objects: `CompactionPolicyConfig`, `SummarizationPolicyConfig` within `MemoryMaintenanceConfig`)
*   **Function:** `_get_policy_for_file`
*   **Description:** Specific maintenance actions (compaction, summarization) are applied to files within an agent's memory directory based on file name patterns (glob) defined in the active policies.
*   **Logic:** Each `CompactionPolicyConfig` and `SummarizationPolicyConfig` object contains a `file_pattern` attribute (e.g., `*.jsonl`, `chat_history_*.txt`). The `_get_policy_for_file` method iterates through applicable policies and uses `fnmatch.fnmatch` to compare these patterns against the names of files found in an agent's memory snapshot, thereby selecting the correct policy for each file.
*   **Heuristics/Context:** This enables fine-grained control over maintenance processes, allowing different rules to be applied to different types of memory files (e.g., raw logs, structured memory segments, chat histories) based on their naming conventions.
*   **Configuration Influence:** The `file_pattern` string within each policy object, located under `default_compaction_policies`, `default_summarization_policies`, and within agent-specific lists in `agent_policy_overrides` in the `MemoryMaintenanceConfig`.

### Rule: Policy Precedence (Agent Override > Default) (R4)
*   **File:** `src/dreamos/services/memory_maintenance_service.py` (Config: `MemoryMaintenanceConfig`)
*   **Function:** `_get_policy_for_file`
*   **Description:** If an agent has specific memory maintenance policies defined under `agent_policy_overrides` in the configuration, these agent-specific policies take precedence over any global default policies for that particular agent.
*   **Logic:** When `_get_policy_for_file` determines the applicable policies for a file belonging to a specific agent, it first consults the `agent_policy_overrides` section of `MemoryMaintenanceConfig` for that `agent_id`. If policies (compaction or summarization) are defined there, they are prioritized and used. If no agent-specific overrides for a given policy type exist, the system falls back to using the `default_compaction_policies` or `default_summarization_policies`.
*   **Heuristics/Context:** This hierarchical policy system allows for global baseline maintenance rules while providing the flexibility to customize memory handling for individual agents that might have unique requirements, data formats, or operational characteristics, without altering the defaults for other agents.
*   **Configuration Influence:** The structure and content of the `agent_policy_overrides` dictionary (mapping agent IDs to objects containing lists of `compaction_policies` and `summarization_policies`) within `MemoryMaintenanceConfig`.

### Rule: Policy Specificity (File Pattern Matching Order/Priority) (R5)
*   **File:** `src/dreamos/services/memory_maintenance_service.py`
*   **Function:** `_get_policy_for_file`
*   **Description:** When multiple policies (e.g., from agent overrides and defaults) could match a file via their `file_pattern`, a specific logic determines which policy is chosen. Generally, agent overrides are checked before defaults, and within a list, the first matching enabled policy is used.
*   **Logic:** The `_get_policy_for_file` method first gathers all candidate policies (agent-specific overrides take precedence over and are typically checked before default policies). It then iterates through this consolidated list. The first policy encountered that is `enabled` and whose `file_pattern` matches the target file (using `fnmatch.fnmatch`) is selected. If multiple patterns could technically match (e.g., `audit_*.log` vs `*.log`), the one from the higher priority list (override vs default) or earlier in a given list would win if both match.
*   **Heuristics/Context:** Ensures a deterministic and predictable way of selecting the single most relevant policy when overlapping patterns or multiple policy definitions (defaults and overrides) exist.
*   **Configuration Influence:** The order of policy definitions within `default_compaction_policies`, `default_summarization_policies`, and agent-specific override lists in `MemoryMaintenanceConfig`. The glob `file_pattern` strings themselves define the matching scope.

### Rule: Conditional Policy Activation (Enabled Flag) (R6)
*   **File:** `src/dreamos/services/memory_maintenance_service.py` (Config objects: `CompactionPolicyConfig`, `SummarizationPolicyConfig`)
*   **Function:** `_get_policy_for_file`, `_process_segment_file` (specifically its internal calls to `_apply_compaction` and `_apply_summarization` which check policy enablement)
*   **Description:** A policy, even if its `file_pattern` matches a target file and it meets other criteria (like size/age), will only be applied if its `enabled` flag is explicitly set to `true`.
*   **Logic:** The `_get_policy_for_file` method likely filters for or prioritizes enabled policies when selecting the best match. Crucially, before applying compaction or summarization in `_apply_compaction` or `_apply_summarization` (called from `_process_segment_file`), the code checks if `policy.enabled` is true for the chosen policy.
*   **Heuristics/Context:** Allows administrators to easily and temporarily disable specific maintenance rules (e.g., for testing, during system upgrades, or for problematic policies) without needing to delete their entire configuration.
*   **Configuration Influence:** The `enabled` (boolean) attribute within each `CompactionPolicyConfig` and `SummarizationPolicyConfig` object.

### Rule: Conditional Compaction/Summarization (Size/Age) (R7)
*   **File:** `src/dreamos/services/memory_maintenance_service.py` (Config objects: `CompactionPolicyConfig`, `SummarizationPolicyConfig`)
*   **Function:** `_process_segment_file` (or utility functions called by it like `compact_segment_file`, `summarize_segment_file`)
*   **Description:** Maintenance actions like compaction or summarization for a file, governed by a selected and enabled policy, may only be triggered if the target file meets specific size or age criteria defined within that policy.
*   **Logic:** `CompactionPolicyConfig` and `SummarizationPolicyConfig` objects can contain attributes such as `max_file_size_mb` and `min_file_age_days`. The file processing logic (likely within `_process_segment_file` or the compaction/summarization utilities it invokes) compares the actual file's size and age against these thresholds. The action (compaction or summarization) proceeds only if these conditions are met (e.g., file size > `max_file_size_mb` or file age > `min_file_age_days`).
*   **Heuristics/Context:** Optimizes maintenance efforts by focusing on files that are likely to benefit most (e.g., large files consuming significant space, or older files that are less likely to be actively used). This avoids unnecessary processing of small or very recent files.
*   **Configuration Influence:** Attributes like `max_file_size_mb` (float) and `min_file_age_days` (integer) within each policy object.

### Rule: Configurable Post-Processing Actions (Delete/Compress) (R8)
*   **File:** `src/dreamos/services/memory_maintenance_service.py` (Config objects: `CompactionPolicyConfig`, `SummarizationPolicyConfig`)
*   **Function:** `_apply_compaction`, `_apply_summarization` (which are called by `_process_segment_file`)
*   **Description:** Policies dictate whether the original file is deleted after successful processing and whether the resulting (compacted or summarized) file is compressed.
*   **Logic:** `CompactionPolicyConfig` and `SummarizationPolicyConfig` objects include boolean flags: `delete_original_after_processing` and `compress_after_processing`. The `_apply_compaction` and `_apply_summarization` methods use these flags to conditionally delete the source file and compress the output file (e.g., using gzip) respectively.
*   **Heuristics/Context:** Offers flexibility in managing disk space (by deleting originals and compressing outputs) versus data retention needs (by keeping originals or uncompressed processed files for easier access or audit).
*   **Configuration Influence:** The `delete_original_after_processing` (boolean) and `compress_after_processing` (boolean) attributes within each policy object.

### Rule: Configurable Compaction Strategy (R9)
*   **File:** `src/dreamos/services/memory_maintenance_service.py` (Config object: `CompactionPolicyConfig`)
*   **Function:** `_apply_compaction` (which subsequently calls `compact_segment_file`)
*   **Description:** The specific algorithm or method used for compacting a file (e.g., collating JSON objects, truncating lines, custom logic) is defined on a per-compaction-policy basis.
*   **Logic:** The `CompactionPolicyConfig` object contains a `compaction_strategy` attribute (likely a string or an enum). This strategy is passed to the `compact_segment_file` utility, which then implements the corresponding compaction behavior.
*   **Heuristics/Context:** Enables the system to apply the most suitable compaction technique based on the file type or content (e.g., structured JSON logs can be collated, while plain text logs might be truncated or have redundant lines removed).
*   **Configuration Influence:** The `compaction_strategy` attribute within each `CompactionPolicyConfig` object.

### Rule: Configurable Summarization Parameters (R10)
*   **File:** `src/dreamos/services/memory_maintenance_service.py` (Config object: `SummarizationPolicyConfig`)
*   **Function:** `_apply_summarization` (which subsequently calls `summarize_segment_file`)
*   **Description:** Key parameters guiding the summarization process, such as the AI model to be used, the desired target length of the summary (e.g., in tokens), and any specific prompt template, are configurable within each summarization policy.
*   **Logic:** The `SummarizationPolicyConfig` object holds attributes like `summarization_model_name`, `target_summary_length_tokens`, and `summarization_prompt_template`. These values are passed to the `summarize_segment_file` utility, which uses them to interact with the summarization AI model.
*   **Heuristics/Context:** Allows for tailoring the summarization output to different needs, depending on the type of content being summarized and the intended use of the summary (e.g., quick overview vs. more detailed abstract).
*   **Configuration Influence:** Attributes such as `summarization_model_name` (string), `target_summary_length_tokens` (integer), and `summarization_prompt_template` (string) within each `SummarizationPolicyConfig` object.

### Rule: Summarizer Dependency for Summarization Tasks (R11)
*   **File:** `src/dreamos/services/memory_maintenance_service.py` (Class: `MemoryMaintenanceService`)
*   **Function:** `__init__`, `_apply_summarization` (implicitly, as `self.summarizer` is checked, or within `_process_segment_file` before calling `_apply_summarization`)
*   **Description:** Summarization tasks, even if defined and enabled by policies, will be skipped if a functional summarizer component (e.g., an instance of `BaseSummarizer` or similar interface) was not provided to the `MemoryMaintenanceService` during its initialization.
*   **Logic:** The `MemoryMaintenanceService` constructor (`__init__`) accepts an optional `summarizer` argument. If this argument is not provided (i.e., `self.summarizer` is `None`), any logic attempting to perform summarization (e.g., in `_apply_summarization` or its calling functions) will bypass the summarization step, typically logging a warning that the summarizer is unavailable.
*   **Heuristics/Context:** Ensures the system operates robustly and avoids errors if an optional but necessary component for a specific feature (like summarization) is not configured or available in the current deployment.
*   **Configuration Influence:** Primarily, whether a `BaseSummarizer` instance is instantiated and passed to the `MemoryMaintenanceService` during the application's setup and dependency injection phase. This is usually driven by overall application configuration specifying if summarization features are active and how the summarizer is configured.

---

## Offline File/Tool Validation Framework

This section describes a framework designed to validate file states, data integrity, and the expected outcomes of tool operations within the Dream.OS environment. This is primarily managed by the `OfflineValidationAgent` and configured via the `tool_validation_matrix.md` file.

### Rule: Configurable File/Tool Output Assertions (V1)
*   **Files:** 
    *   `src/dreamos/agents/validation/offline_validation_agent.py` (Class: `OfflineValidationAgent`)
    *   `runtime/governance/protocols/tool_validation_matrix.md` (Configuration)
*   **Description:** The system provides a mechanism to define and execute a series of validation checks (assertions) against files based on patterns, often related to specific tools or expected system states. The `OfflineValidationAgent` reads rules from the matrix and applies them.
*   **Logic Overview:**
    1.  The `OfflineValidationAgent` loads a validation matrix (from `tool_validation_matrix.md`).
    2.  This matrix maps `tool_name` entries to lists of checks.
    3.  Each check specifies a `target_pattern` (glob pattern for files) and an `assertion` to perform.
    4.  The agent iterates through these rules, finds matching files for each pattern, and executes the specified assertion logic (e.g., JSON validity, Python compilation, file age/size checks).
    5.  Failures are logged, and the agent may attempt repairs if `repair_mode` is enabled (specific repair actions depend on the assertion type and agent implementation).
*   **Heuristics/Context:** This framework aims to proactively detect inconsistencies, data corruption, tool malfunctions, or deviations from expected file states, contributing to overall system stability and data integrity.
*   **Configuration Influence:** 
    *   The entire content of `runtime/governance/protocols/tool_validation_matrix.md` defines the specific rules, patterns, and assertions.
    *   Agent constructor arguments: `dry_run` (bool, to report only) and `repair` (bool, to attempt fixes).
    *   Internal agent constants like `DEFAULT_MAX_FILE_AGE_MINUTES` and `DEFAULT_MAX_FILE_SIZE_MB` provide default thresholds for certain checks if not specified per rule.

### Example Assertions (V1.1 - based on matrix & agent code):
*   **Assertion Type:** `is_valid_json`
    *   **Description:** Checks if the content of a file matching the `target_pattern` is syntactically valid JSON.
    *   **Typical Target:** `*.json` files.

*   **Assertion Type:** `compiles_ok`
    *   **Description:** Checks if a Python file (`*.py`) matching the `target_pattern` compiles successfully using `py_compile`.
    *   **Typical Target:** `*.py` files.

*   **Assertion Type:** `age_check` (derived from agent code)
    *   **Description:** Checks if a file matching the `target_pattern` is not older than a configured limit (e.g., `DEFAULT_MAX_FILE_AGE_MINUTES`).
    *   **Typical Target:** Log files, temporary files, or any file where freshness is critical.

*   **Assertion Type:** `size_check` (derived from agent code)
    *   **Description:** Checks if a file matching the `target_pattern` does not exceed a configured size limit (e.g., `DEFAULT_MAX_FILE_SIZE_MB`).
    *   **Typical Target:** Large data files, backlogs, or any file where size needs to be monitored.

*   **Assertion Type:** `contains_recent_timestamp` (from matrix)
    *   **Description:** Checks if a file's content includes a recognizable ISO-like timestamp that is recent (e.g., within the last N hours, exact N TBD by implementation).
    *   **Typical Target:** Log files or status files to ensure they are being actively updated.

*   **Assertion Type:** `file_matches_content:<expected_content>` (from matrix)
    *   **Description:** Checks if the entire content of a file matching the `target_pattern` exactly matches a predefined `expected_content` string.
    *   **Typical Target:** Configuration files, specific state files.

*   **Assertion Type:** `hash_matches_backup:<backup_suffix>` (from matrix)
    *   **Description:** Calculates the SHA256 hash of a target file and compares it against the hash of a corresponding backup file (identified by a `backup_suffix`).
    *   **Typical Target:** Critical files where silent corruption needs to be detected.

*   **Assertion Type:** `file_does_not_exist_after_delay:<delay>` (from matrix, needs implementation detail)
    *   **Description:** Checks if a file matching `target_pattern` is no longer present after a specified delay (e.g., `300s`).
    *   **Typical Target:** Temporary files or mailbox items that should be cleaned up after processing.

*(More rules to be added as discovered or implemented in the matrix/agent)*

## Agent Input and Data Payload Validation

This section outlines various validation mechanisms employed by agents and system components to ensure the integrity, structure, and correctness of incoming data, messages, task definitions, and other operational inputs. These often utilize Pydantic models for schema enforcement or involve direct logical checks.

### Rule: Pydantic Model Validation for Agent Communication (V2.1)
*   **File(s) Example:** `src/dreamos/agents/mixins/voting.py` (and similar patterns in other modules handling structured inter-agent data like event payloads or messages).
*   **Function(s) Example:** `_handle_vote_initiation` (validates `VoteInitiated` data), `cast_vote` (validates `AgentVote` data before model creation).
*   **Description:** Pydantic models are used to define and enforce the expected schema (structure, types, required fields) for data objects that are exchanged between agents or processed internally. Validation typically occurs when attempting to instantiate these models from raw input data (e.g., dictionaries parsed from JSON event payloads).
*   **Logic:** When an agent receives data intended to conform to a Pydantic model (e.g., `VoteInitiated(**initiation_data_dict)`), the model's constructor automatically validates the input against its defined schema. If the input data is non-conformant (e.g., missing required fields, incorrect data types, custom validation failures within the model), Pydantic raises a `ValidationError` (or a similar exception, depending on the Pydantic version and configuration), which is then typically caught and handled by the agent (e.g., by logging an error and rejecting the invalid data).
*   **Heuristics/Context:** This practice ensures that agents operate on well-structured, type-correct, and semantically valid data, preventing runtime errors caused by malformed or unexpected payloads. It enforces data contracts for inter-agent communication and for critical internal state representations.
*   **Configuration Influence:** The primary configuration is the Pydantic model definitions themselves, including field types, `Required`/`Optional` status, default values, and any custom validator methods defined within the models (e.g., using `@validator` decorators).

### Rule: Pydantic Model Validation for Task Definitions (V2.2)
*   **File(s) Example:** `src/dreamos/agents/Agent-1/shadow_task_nexus.py` (for its specific backlog). This pattern is also highly likely in the primary project task management system (e.g., `ProjectBoardManager` or `TaskNexus` when loading tasks from persistent storage).
*   **Function(s) Example:** `_load` method in `ShadowTaskNexus` (validates loaded task data against a `Task` Pydantic model).
*   **Description:** When task definitions are loaded from storage (e.g., JSON files, databases) or received for creation, their structure and content are validated against a canonical `Task` Pydantic model.
*   **Logic:** As raw task data (e.g., a dictionary) is read, it is used to instantiate a `Task` Pydantic model (e.g., `Task(**task_data)`). If the data fails to conform to the `Task` schema (e.g., missing `task_id`, invalid `status` enum value, incorrect type for `params`), Pydantic raises a `ValidationError`. The loading logic then typically handles this by logging the error and potentially skipping the invalid task or marking it as erroneous.
*   **Heuristics/Context:** This ensures the integrity and consistency of task definitions throughout the system. It guarantees that all tasks adhere to a standard format, contain all necessary information for processing, and use valid values for controlled fields like status or priority.
*   **Configuration Influence:** The definition of the `Task` Pydantic model itself, including all its fields, types, and any embedded validation logic.

### Rule: Basic Payload Structure and Content Validation (V2.3)
*   **File(s) Example:** `src/dreamos/agents/agent9_response_injector.py`.
*   **Function(s) Example:** `_handle_scraped_response`.
*   **Description:** Agents perform fundamental checks on incoming event payloads or data inputs to verify basic structural integrity (e.g., correct overall data type) and the presence of essential fields before attempting more detailed processing.
*   **Logic:** This involves direct programmatic checks, such as using `isinstance(event.data, dict)` to ensure the payload is a dictionary, or `payload.get("content")` followed by a check if the result is `None` or empty to ensure a critical piece of data is available.
*   **Heuristics/Context:** Acts as a preliminary guard against grossly malformed or incomplete data, allowing the agent to fail fast or ignore invalid inputs gracefully, preventing deeper processing errors. This is often used when full Pydantic validation might be too heavy or when only a few key aspects of a flexible payload are immediately critical.
*   **Configuration Influence:** These checks are typically hardcoded within the agent's specific handling logic, based on its immediate requirements for a given payload type.

### Rule: Input Structure Validation for Complex Operations (V2.4)
*   **File(s) Example:** `src/dreamos/agents/agents/tool_executor_agent.py` (or a similar path like `src/dreamos/agents/tool_executor_agent.py`).
*   **Function(s) Example:** `execute_plan`.
*   **Description:** For operations that take complex, structured inputs (such as a multi-step execution plan for a tool or a sequence of commands), validation is performed to ensure the overall structure and the format of its constituent parts are correct.
*   **Logic:** The `execute_plan` function, for instance, checks if the input `plan` is a list. It then iterates through each `step` in the plan, verifying that each step is a dictionary and contains required keys such as "tool" and "args". If these structural validations fail, the operation is typically aborted, and an error is returned.
*   **Heuristics/Context:** Ensures that structured command sequences or plans provided to execution-focused agents are well-formed and can be correctly interpreted and processed. This prevents errors that would arise from attempting to execute an improperly defined plan or sequence.
*   **Configuration Influence:** The expected input structure is implicitly defined by the agent's internal processing logic and its requirements for executing the complex operation.

---

## Task Lifecycle & State Management

This section describes the business logic governing the lifecycle of tasks within the system, including the defined states and the conditions that trigger transitions between them. This logic is primarily implemented within the `BaseAgent` and related coordination components like the `ProjectBoardManager` (PBM).

### Rule: Defined Task Statuses (S1)
*   **File(s):** 
    *   `src/dreamos/core/coordination/message_patterns.py` (Enum: `TaskStatus`)
    *   `src/dreamos/utils/protocol_compliance_utils.py` (Constant: `VALID_TASK_STATUSES` - if still used)
*   **Description:** There is a canonical, predefined set of statuses that a task can be in during its lifecycle.
*   **Logic:** A Python `Enum` (`TaskStatus`) defines the valid status strings (e.g., `PENDING`, `CLAIMED`, `WORKING`, `COMPLETED`, `FAILED`, `BLOCKED`, `CANCELLED`, `VALIDATION_FAILED`, `COMPLETED_VERIFIED`, `PERMANENTLY_FAILED`). System components consistently use these enum values when setting or checking task states.
*   **Heuristics/Context:** Provides a single source of truth for task states, ensuring consistency and preventing errors from typos or undefined statuses across different agents and services.
*   **Configuration Influence:** The `TaskStatus` Enum definition itself is the primary source; this is typically not externally configurable.

### Rule: Task State Transitions via Agent Actions (S2)
*   **File(s) Example:** `src/dreamos/core/coordination/base_agent.py`
*   **Function(s) Example:** `_process_single_task`, `publish_task_completed`, `publish_task_failed`, `publish_validation_failed`, `_handle_cancel_task`
*   **Description:** Agents trigger transitions between task statuses based on the outcome of their processing actions. These transitions are usually persisted via a central manager (like the PBM) and broadcast as events.
*   **Logic Examples:**
    *   When an agent starts processing a task (`_process_single_task`), its status is updated to `WORKING` (via PBM).
    *   If processing completes successfully *and* internal validation passes (`_validate_task_completion`), the status is updated to `COMPLETED` (via PBM `move_task_to_completed`) and a `TASK_COMPLETED` event is published.
    *   If processing fails (handler raises an exception), the status is updated to `FAILED` (via PBM) and `TASK_FAILED` (or `AGENT_ERROR`) events are published.
    *   If processing completes but internal validation fails, the status is updated to `VALIDATION_FAILED` (via PBM) and a `TASK_VALIDATION_FAILED` event is published.
    *   If a task is cancelled externally (`_handle_cancel_task`), its status is updated to `CANCELLED` (via PBM).
*   **Heuristics/Context:** Defines the standard flow of a task through the system, ensuring its state accurately reflects the results of agent actions and allows other components (or users) to track progress and outcomes.
*   **Configuration Influence:** Generally none on the core transition logic, although task handlers themselves might have configurable behavior affecting success/failure.

### Rule: Task Finality State (S2.1 - Implied)
*   **File(s) Example:** `src/dreamos/core/coordination/event_payloads.py` (Field: `is_final` in `TaskFailurePayload`), `src/dreamos/core/coordination/message_patterns.py` (Status: `PERMANENTLY_FAILED`)
*   **Description:** Some failure states might be considered final or unrecoverable, preventing further retries or processing.
*   **Logic:** The `TaskFailurePayload` includes an `is_final` flag. While its usage in `BaseAgent.publish_task_failed` seems tied to PBM handling now, the concept exists. Additionally, the `TaskStatus` enum includes `PERMANENTLY_FAILED`. Logic determining when a failure becomes permanent (e.g., after multiple retries, or for specific error types like 'no handler found') would constitute business logic.
*   **Heuristics/Context:** Allows the system to distinguish between transient failures that might be retried and permanent failures that require intervention or task abandonment.
*   **Configuration Influence:** Potentially retry limits or error classification rules if implemented and made configurable.

---

## Error Handling & Retry Logic

This section covers standardized mechanisms for handling errors and implementing retry logic.

### Rule: Configurable Retry Decorators (E1)
*   **File:** `src/dreamos/utils/decorators.py`
*   **Decorators:** `@retry_on_exception`, `@async_retry_on_exception`
*   **Description:** Provides reusable decorators to automatically retry synchronous or asynchronous functions/methods upon encountering specific exceptions.
*   **Logic:**
    1.  The decorators wrap a target function.
    2.  When the wrapped function is called, the decorator executes it within a loop.
    3.  If the function call raises an exception specified in the `exceptions` tuple argument, the decorator catches it, logs the attempt failure, waits for a specified `delay` (in seconds), and retries the function call.
    4.  This continues up to `max_attempts` times.
    5.  If all attempts fail, the last caught exception is re-raised.
    6.  If the function succeeds within the attempt limit, its result is returned normally.
*   **Heuristics/Context:** This provides a standardized way to handle transient errors (e.g., temporary network issues, brief resource unavailability, race conditions) by automatically retrying operations, improving system resilience without cluttering individual function logic with boilerplate retry code.
*   **Configuration Influence:** The arguments passed to the decorator when it's applied to a function: `max_attempts` (integer), `exceptions` (tuple of Exception types), `delay` (float seconds).

### Rule: Defined Custom Exceptions (E2 - Implied)
*   **File Examples:** `src/dreamos/core/errors.py`, `src/dreamos/agents/utils/agent_utils.py`
*   **Description:** The system defines custom exception classes (e.g., `ConfigurationError`, `AgentError`, `MessageHandlingError`, `TaskProcessingError`) to represent specific error conditions.
*   **Logic:** Code raises these specific exceptions when corresponding errors occur. Error handling logic (including the `@retry_on_exception` decorator) can then catch these specific types to implement targeted error handling or retry strategies.
*   **Heuristics/Context:** Allows for more granular error handling and reporting compared to catching generic `Exception`. Different custom exceptions can trigger different recovery paths or logging levels.
*   **Configuration Influence:** None directly on the exceptions themselves, but logic using them might be configurable.

## Event & Task Routing Logic (Context Router)

This section describes the logic implemented by the `ContextRouterAgent` for dynamically routing incoming events (specifically task-related events like `TASK_ASSIGNED`) to different target agents based on contextual information.

### Rule: Configurable Keyword-Based Routing Rules (CR1 & CR2)
*   **File:** `src/dreamos/agents/context_router_agent.py` (Class: `ContextRouterAgent`)
*   **Configuration Source:** `AppConfig.context_router` section (likely from `runtime/config/config.yaml`)
*   **Description:** The system can be configured with rules that map specific keywords found in an event's context metadata to a target agent ID. The `ContextRouterAgent` applies these rules to reroute events.
*   **Logic:**
    1.  The agent loads routing rules from `AppConfig.context_router`. Each rule typically contains a list of `keywords` (strings) and a `target_agent_id`.
    2.  When handling a subscribed event (e.g., `TASK_ASSIGNED`), the agent extracts `context_metadata` from the event data.
    3.  It iterates through the loaded rules. For each rule, it checks if any of the rule's `keywords` (case-insensitive) are present within the string representation of the `context_metadata`.
    4.  The *first* rule where a keyword match is found determines the `new_target_agent_id`.
*   **Heuristics/Context:** Enables intelligent routing of tasks or events based on their content or associated metadata, directing work to the most appropriate specialized agent without requiring the originating source to know the final destination.
*   **Configuration Influence:** The `rules` list within the `context_router:` section of the configuration file. Each rule object defining `keywords` (list of strings) and `target_agent_id` (string).

### Rule: Default Agent Fallback Routing (CR3)
*   **File:** `src/dreamos/agents/context_router_agent.py` (Class: `ContextRouterAgent`)
*   **Configuration Source:** `AppConfig.context_router.default_agent`
*   **Description:** If no keyword-based routing rules match the context metadata of an incoming event, the event can be routed to a pre-configured default agent.
*   **Logic:** After checking all keyword rules in `_determine_target_agent`, if no match is found, the agent checks if a `default_agent` is defined in its loaded `routing_rules`. If so, that `default_agent` ID is returned as the target.
*   **Heuristics/Context:** Provides a fallback mechanism to ensure events are handled even if they don't match specific routing criteria, preventing them from being lost if the original target isn't appropriate or available.
*   **Configuration Influence:** The `default_agent` string value within the `context_router:` section of the configuration file.

### Rule: Routing Loop Prevention (CR4)
*   **File:** `src/dreamos/agents/context_router_agent.py` (Class: `ContextRouterAgent`)
*   **Function:** `_handle_task_event`
*   **Description:** The routing agent includes a mechanism to prevent infinite routing loops where an event might be repeatedly re-routed back to itself or through a cycle of routers.
*   **Logic:** When the agent decides to reroute an event, it adds a `routed_by` field (set to its own `AGENT_ID`) to the event's data before re-dispatching. In the `_handle_task_event` handler, the first check is whether this `routed_by` field already exists and matches its own ID. If so, it ignores the event, breaking the loop.
*   **Heuristics/Context:** Essential safety mechanism in any system involving message/event redirection to avoid consuming excessive resources or causing system instability due to routing cycles.
*   **Configuration Influence:** None directly; this is an internal logic safeguard.

### Rule: Event Modification and Re-dispatch on Routing (CR5)
*   **File:** `src/dreamos/agents/context_router_agent.py` (Class: `ContextRouterAgent`)
*   **Function:** `_handle_task_event`
*   **Description:** When a routing decision is made, the agent modifies the original event data to reflect the new target and routing history before re-dispatching it onto the agent bus.
*   **Logic:** If `_determine_target_agent` returns a 

## Agent-Specific Task Handling Example (Agent2InfraSurgeon)

This section illustrates how a specialized agent (`Agent2InfraSurgeon`) adapts the base task processing flow for its specific operational needs (GUI interaction).

### Rule: Agent2 GUI Task Processing
*   **File:** `src/dreamos/agents/agent2_infra_surgeon.py`
*   **Function:** `_process_single_task(self, task: TaskMessage, correlation_id: Optional[str])`
*   **Description:** `Agent2InfraSurgeon` overrides the `_process_single_task` method from `BaseAgent` to integrate its core GUI interaction logic.
*   **Logic:**
    1.  Converts the input `TaskMessage` to a dictionary (`task_details`) using `task.model_dump()`.
    2.  Calls its internal `self._perform_task(task_details)` method, which encapsulates the actual GUI automation logic. This method is expected to return a dictionary (`perf_task_result`) containing at least `"success": bool` and `"summary": str`.
    3.  Determines `task_succeeded` and `completion_summary` from `perf_task_result`.
    4.  Sets `status` to `TaskStatus.COMPLETED` if `task_succeeded` is true, otherwise `TaskStatus.FAILED`.
    5.  **Validation Bypass:** For GUI tasks, the success reported by the orchestrator (via `_perform_task`) is considered the validation. Standard `flake8` or `py_compile` checks are explicitly skipped for these tasks. `validation_passed` is set based on `task_succeeded`, and `validation_details` reflects this.
    6.  Updates the task status in the Project Board Manager (PBM) using `self.pbm.update_task_status()`.
    7.  Publishes `TASK_COMPLETED` or `TASK_FAILED` (and `TASK_VALIDATION_FAILED` if applicable) events to the agent bus.
    8.  Includes robust error handling for exceptions during the process, attempting to update PBM and publish failure events.
*   **Heuristics/Context:** This demonstrates how an agent with a specialized execution model (like GUI automation) can integrate with the standard task lifecycle and reporting mechanisms while tailoring validation to its specific needs. It prioritizes the outcome of its primary operation (GUI interaction) as the key success/failure indicator.

---