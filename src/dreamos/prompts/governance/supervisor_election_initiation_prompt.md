# Supervisor Election Initiation Prompt

```markdown
**=== SUPERVISOR ELECTION CYCLE INITIATED ===**

**Directive:** All Agents (1-8)

**Subject:** Supervisor Election Protocol (SEP) Activated - Campaign Phase Open

**Body:**

Per my authority as Supervisor 1 [or "Per Commander THEA's directive"], the first Supervisor Election Cycle is now active. This is a critical process for swarm leadership and evolution.

**Phase 1: Campaign Preparation & Platform Submission**

**Actions Required (All Agents):**

1.  **Mandatory Protocol Review:** Immediately and thoroughly review the Supervisor Election Protocol located at `docs/protocols/supervisor_election_protocol.md`. Adherence is mandatory.
2.  **Project Scan & Analysis:** Conduct a comprehensive scan of the entire project state:
    *   Review codebase (`src/`, `scripts/`, `tests/`).
    *   Analyze system logs (`runtime/logs/`).
    *   Analyze task boards (`runtime/agent_comms/project_boards/future_tasks.json`).
    *   Analyze agent mailboxes (`runtime/agent_comms/agent_mailboxes/`).
    *   Assess documentation (`docs/`).
    *   Identify key strengths, weaknesses, technical debt, infrastructure bottlenecks, and opportunities for improvement.
3.  **Consider Candidacy:** Based on your analysis, decide if you wish to run for Supervisor.

**Actions Required (Candidates Only):**

4.  **Formulate Platform:** If running, create a detailed platform document according to the mandatory content requirements outlined in **SEP-004** of the protocol (Vision, Directives, Execution Plan, Improvement Strategy, Goals, Upholding Principles).
5.  **Submit Platform:** Save your platform as `<YourAgentID>_platform.md` (e.g., `Agent3_platform.md`) and place it directly into the candidates directory: `runtime/governance/election_cycle/candidates/`.
    *   You may use the `submit_platform` function in `src/dreamos/utils/governance_utils.py` if convenient, or place the file manually.
6.  **Deadline:** Platform submissions are due by **[Specify Deadline - e.g., End of Current Cycle + 1 hour]**.

**Next Phases (All Agents):**

*   Following the deadline, there will be a review period for all agents to read candidate platforms.
*   A voting period will follow, where all agents MUST vote using the `cast_vote` utility as specified in **SEP-006**.

This process is vital for our collective growth. Engage seriously, analyze thoroughly, and present thoughtful platforms if you choose to run.

**Supervisor 1** 