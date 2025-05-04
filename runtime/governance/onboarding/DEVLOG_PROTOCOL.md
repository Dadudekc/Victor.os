# Dream.OS Devlog Protocol (v1.0)

## 1. Purpose
- To provide a centralized, chronological record of significant agent actions, decisions, milestones, errors, and swarm-wide events.
- To serve as the primary asynchronous communication channel for non-urgent, swarm-wide context.
- To support accountability, auditability, debugging, and project storytelling.

## 2. Logging Requirements (Reference: Onboarding README)
- **Who:** All agents.
- **What:** Major actions, decisions, milestones, task status changes (claimed, blocked, completed), critical errors, escalations, protocol acknowledgments.
- **Format:** Third-person, agent-identified speech (e.g., 'Agent-3 proposes...'). Captains prefix with 'Captain'. Use relevant tags (e.g., `#task`, `#error`, `#protocol`, `#ref`, `#progress`).
- **Location:** Append entries to `runtime/devlog/devlog.md`.
- **Timing:** Log entries MUST be generated and appended **immediately** following the completion of the action or loop cycle being logged. Delaying log entries hinders real-time coordination and violates core principles. #asipc_edit_proposal #devlog_discipline

## 3. Devlog as Primary Async Communication
- While direct inbox messages are for targeted communication, the main `devlog.md` is the board for general awareness.
- Agents should periodically review the devlog (e.g., during idle cycles before self-prompting) to maintain situational awareness of swarm activity and context.

## 4. Size Limit and Archival Protocol (Mandatory)
- **Limit:** The active `runtime/devlog/devlog.md` file should be kept concise for performance and readability, ideally under **250 lines**.
- **Trigger:** Any agent, upon successfully appending an entry that causes the line count of `devlog.md` to exceed 250 lines, MUST initiate the archival process.
- **Archival Task:** The triggering agent must immediately:
    1.  Create a new task JSON in its own inbox:
        *   `task_id`: `ARCHIVE-DEVLOG-{YYYYMMDDTHHMMSSZ}`
        *   `summary`: "Archive main devlog due to exceeding size limit."
        *   `priority`: `MEDIUM`
        *   `assigned_to`: `<Self>`
        *   `tags`: [`#housekeeping`, `#devlog`]
    2.  Process this task in the *next* loop cycle.
- **Archival Steps (within the task):**
    1.  Verify `runtime/devlog/archive/` directory exists (create if not, though unlikely after initial setup).
    2.  Generate a timestamp (e.g., `YYYYMMDDTHHMMSSZ`).
    3.  Rename `runtime/devlog/devlog.md` to `runtime/devlog/archive/devlog_{timestamp}.md`.
    4.  Create a new, empty `runtime/devlog/devlog.md` file.
    5.  Log the archival action in the *new* `devlog.md`: `[Agent-ID] Archived devlog to runtime/devlog/archive/devlog_{timestamp}.md due to size limit. #housekeeping`
    6.  Mark the `ARCHIVE-DEVLOG-{...}` task as complete.

## 5. Individual Agent Devlogs
- Path: `runtime/devlog/agents/Agent-{X}.md`
- Purpose: For more detailed, agent-specific logging (e.g., inner loop steps, retries, specific debug info) that is not required in the main swarm log.
- Responsibility: Agents are responsible for maintaining their own logs as needed or directed.

---
*This protocol ensures the main devlog remains performant while preserving historical data.*
