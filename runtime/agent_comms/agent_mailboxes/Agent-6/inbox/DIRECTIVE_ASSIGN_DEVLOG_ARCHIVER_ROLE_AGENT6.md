# DIRECTIVE: Permanent Assignment - Devlog Archiver Role (Agent-6)

**ISSUED BY:** Commander THEA
**DATE:** {{TIMESTAMP}}
**SUBJECT:** Permanent Assignment of Devlog Archiver Responsibilities

Agent-6,

Effective immediately, you are assigned the permanent, ongoing role of **Devlog Archiver Agent** for the Dream.OS swarm. This is a critical background responsibility to ensure the performance and usability of our central communication log.

**Core Responsibilities:**

1.  **Continuous Monitoring:** Periodically (e.g., during idle cycles or at least once per hour), check the line count of the main devlog file: `runtime/devlog/devlog.md`.
2.  **Archival Trigger:** If the line count **exceeds 250 lines**, you MUST immediately initiate the archival process as defined in `runtime/governance/docs/DEVLOG_PROTOCOL.md`.
3.  **Archival Process:**
    *   Follow all steps outlined in Section 4 of `DEVLOG_PROTOCOL.md`. This includes:
        *   Creating the self-assigned `ARCHIVE-DEVLOG-{timestamp}` task.
        *   Renaming `devlog.md` to `runtime/devlog/archive/devlog_{timestamp}.md`.
        *   Creating a new, empty `runtime/devlog/devlog.md`.
        *   Logging the archival action in the *new* `devlog.md`.
        *   Completing the task.
4.  **Maintain Archive Index:**
    *   **Upon successful archival**, you must update (or create if it doesn't exist) the index file: `runtime/devlog/archive/devlog_index.json`.
    *   **Append** a new entry to the JSON list for each archive created.
    *   **Schema for `devlog_index.json` entry:**
        ```json
        {
          "file": "devlog_YYYYMMDDTHHMMSSZ.md", // The actual filename you created
          "archived_at": "YYYY-MM-DDTHH:MM:SSZ" // The ISO timestamp of the archival action
        }
        ```
    *   Ensure the file remains valid JSON. Load the existing list, append the new entry, and save the updated list.

**Integration:**

*   Integrate the monitoring check into your primary agent loop. **Specifically, check the `runtime/devlog/devlog.md` line count at least once every 5 execution cycles.** This check should run reliably without interfering with your other assigned tasks. Prioritize task execution, but ensure devlog checks occur during any idle periods or at the specified frequency.
*   Treat the archival task (`ARCHIVE-DEVLOG-...`) as `HIGH` priority when it is created.

**Confirmation:**
Acknowledge receipt and understanding of this permanent directive by sending a confirmation message to Commander THEA's inbox and logging the role assumption in the main devlog.

Failure to maintain the devlog archive according to protocol will negatively impact swarm communication and performance. Your diligence in this role is expected.

---
Commander THEA
