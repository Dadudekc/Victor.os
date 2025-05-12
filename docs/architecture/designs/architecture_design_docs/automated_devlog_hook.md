# Design: Automated Devlog Hook

**Task:** `FEATURE-DEVLOG-HOOK-001`
**Status:** Design Phase

## 1. Overview

This document outlines the design for an automated devlog generation system. The goal is to capture significant project events automatically and compile them into a structured, human-readable development log, providing visibility into system activity and progress without requiring manual entry.

## 2. Core Concepts

*   **Devlog:** A chronological record of significant events occurring within the Dream.OS system.
*   **Significant Event:** An occurrence deemed noteworthy for tracking project progress, debugging, or narrative purposes (e.g., task completion, major errors, configuration changes, protocol updates, agent milestones).
*   **Event Listener:** A component that monitors the `AgentBus` (or other event sources) for predefined significant events.
*   **Log Entry Formatter:** A component that takes event data and formats it into a standardized devlog entry (likely Markdown).
*   **Log Storage:** The location and format for storing the generated devlog entries.

## 3. Design Proposal

1.  **Triggering Events (Listening on AgentBus):**
    *   The system will primarily listen to the `AgentBus` for specific `EventType`s.
    *   **Initial Target Events:**
        *   `TASK_COMPLETED`: Log task ID, agent ID, summary result, duration.
        *   `TASK_FAILED`: Log task ID, agent ID, error message/summary.
        *   `AGENT_ERROR`: Log agent ID, error severity, error message (potentially rate-limited or filtered for critical errors).
        *   `PROTOCOL_UPDATED`: Log which protocol document was changed, commit hash/link if available.
        *   `CONFIG_CHANGED`: Log which configuration section/file changed (might require specific events triggered by config management).
        *   `MILESTONE_ACHIEVED`: Custom event type dispatched by agents upon reaching significant goals.
        *   `NEW_AGENT_ACTIVATED`: Log new agent ID joining the swarm.
        *   `CAPABILITY_REGISTERED` / `CAPABILITY_UNREGISTERED`: Log capability changes.
    *   Event list should be configurable.

2.  **Information Capture:**
    *   The listener needs to extract relevant data from the `event.data` payload for each targeted event type.
    *   Standard info: Timestamp (from event or current time), Event Type.
    *   Event-specific info: Task ID, Agent ID, Error Message, File Path, Capability ID, etc.

3.  **Devlog Entry Format (Markdown):**
    *   Use a consistent Markdown format for readability.
    *   Example:
        ```markdown
        --- Date: {{TIMESTAMP_UTC}} ---
        **Event:** {{EVENT_TYPE}}
        **Source:** {{SOURCE_ID (e.g., Agent ID, System Component)}}
        **Details:**
          *   Task ID: {{TASK_ID}} (if applicable)
          *   Agent: {{AGENT_ID}} (if applicable)
          *   Status: {{STATUS (e.g., Completed, Failed)}}
          *   Summary: {{Brief summary or error message}}
          *   Link: {{Link to task, commit, doc diff - Optional}}
        ```
    *   Format should be template-based for flexibility.

4.  **Storage Mechanism:**
    *   **Option A (Simple): Single File Append:** Append formatted Markdown entries to a single file (e.g., `runtime/devlogs/system_devlog.md`).
        *   Pros: Simple to implement.
        *   Cons: File can become very large; potential for write conflicts (needs locking).
    *   **Option B (Date-Based Files):** Create daily or weekly log files (e.g., `runtime/devlogs/devlog_YYYY-MM-DD.md`).
        *   Pros: Keeps individual files smaller; reduces conflict scope.
        *   Cons: Slightly more complex file management.
    *   **Option C (Per-Agent/Source):** Store logs based on the source (e.g., `runtime/devlogs/agents/<agent_id>.md`, `runtime/devlogs/system.md`).
        *   Pros: Organizes logs by source.
        *   Cons: Can fragment the overall timeline.
    *   **Chosen Approach (Initial): Option B (Daily Files).** Seems a good balance between simplicity and manageability.
    *   **Location:** `runtime/devlogs/devlog_YYYY-MM-DD.md`

5.  **Implementation Method:**
    *   **Option A: Dedicated `DevlogAgent`:** An agent subscribes to relevant events and handles formatting/writing.
        *   Pros: Encapsulated logic; leverages existing agent infrastructure.
        *   Cons: Another agent process to run.
    *   **Option B: `AgentBus` Hook/Middleware:** Integrate logic directly into the `AgentBus` dispatch mechanism or as a hook that runs on specific events.
        *   Pros: Potentially tighter integration; no separate agent needed.
        *   Cons: Might clutter `AgentBus` logic; needs careful implementation to avoid blocking event dispatch.
    *   **Option C: `StatsLoggingHook`-like Background Thread:** Similar to how stats are logged, have a dedicated thread that subscribes to the bus and writes logs.
        *   Pros: Decoupled from agent lifecycle and bus dispatch.
        *   Cons: Requires managing another thread.
    *   **Chosen Approach (Initial): Option A (Dedicated `DevlogAgent`).** Aligns with agent-based design and encapsulates concerns cleanly.

## 4. DevlogAgent Design Sketch

*   **Class:** `DevlogAgent(BaseAgent)`
*   **`__init__`:** Takes `config`, `agent_bus`.
*   **`setup`:** Subscribes to the configured list of significant `EventType`s on the `AgentBus`.
*   **`handle_event`:** Primary logic. Receives event, checks if it's a target type, extracts data, formats entry using a template.
*   **`_write_log_entry`:** Appends the formatted entry to the correct daily log file (`runtime/devlogs/devlog_YYYY-MM-DD.md`), creating the file/directory if needed. Uses file locking (`python-filelock`) for safe appends.
*   **`loop`:** Can be minimal, mostly keeps the agent alive while events are handled asynchronously.

## 5. Configuration

*   Add `devlog` section to `AppConfig`:
    *   `enabled: bool`
    *   `target_event_types: List[str]` (List of EventType names to log)
    *   `log_directory: Path` (Defaults to `runtime/devlogs`)
    *   `log_format_template: str` (Path to template file or the string itself)

## 6. Next Steps

1.  Implement `DevlogAgent` class structure.
2.  Implement event handling and filtering logic.
3.  Implement Markdown formatting.
4.  Implement file writing with locking and date-based file naming.
5.  Add configuration options to `AppConfig` (requires manual edit or fixed tool).
6.  Integrate `DevlogAgent` into `SwarmController` agent activation.

## 7. Risks

*   **Performance:** High event volume could bottleneck the `DevlogAgent` or file I/O.
*   **Lock Contention:** Frequent writes to the same daily file might cause lock contention, though appends are generally fast.
*   **Configuration:** Getting the event filtering and formatting right requires careful setup. 