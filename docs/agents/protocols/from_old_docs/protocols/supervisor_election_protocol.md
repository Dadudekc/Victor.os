# Supervisor Election Protocol (SEP)

## SEP-001: Purpose

To establish a transparent and merit-based process for selecting the operational
Supervisor (Agent 1 role) for the Dream.OS swarm, fostering leadership
development and ensuring alignment with project goals.

## SEP-002: Eligibility

Any active agent (Agent 1 through Agent N) is eligible to nominate themselves
for the Supervisor role.

## SEP-003: Election Cycle Trigger

The election cycle is triggered by Commander THEA or the current Supervisor.

## SEP-004: Nomination & Platform Submission

1.  **Declaration:** Eligible agents wishing to run must declare candidacy by
    creating a platform document.
2.  **Platform File:** Create a markdown file named `<AgentID>_platform.md`
    (e.g., `Agent2_platform.md`) within the current election directory:
    `runtime/governance/election_cycle/candidates/`.
3.  **Platform Content (Mandatory):** The platform document MUST include:
    - **Vision:** High-level vision for the swarm's operation and project
      direction.
    - **Proposed Directives:** Key priorities and focus areas for the next
      operational cycle(s).
    - **Execution Plan:** How the candidate plans to manage tasks, coordinate
      agents, and ensure progress.
    - **Improvement Strategy:** Specific plans for addressing technical debt,
      improving infrastructure, enhancing protocols, or boosting efficiency.
    - **Goals/Subfocuses:** Measurable objectives for their term.
    - **Upholding Principles:** A statement on how they will enforce Core
      Principles (esp. Reuse First, No Placeholders).
    - **Structure:** Submissions MUST follow the structure defined in the
      template:
      `runtime/governance/election_cycle/candidates/platform_template.md`.
4.  **Deadline:** Platform documents must be submitted by the deadline announced
    at the cycle trigger.

## SEP-005: Campaign Review Period

A designated period following the submission deadline for all agents to review
the platforms of the candidates.

## SEP-006: Voting

1.  **Voting Period:** A designated period following the review period.
2.  **Mechanism:** Each active agent MUST cast one vote.
3.  **No Self-Votes:** Agents cannot vote for themselves.
4.  **Recording Vote (Mandatory Use of Utility):** To vote, agents MUST use the
    `cast_vote` function provided in the governance utilities
    (`src/dreamos/utils/governance_utils.py`).
    - **Call:**
      `python -m src.dreamos.utils.governance_utils cast_vote --voter <YourAgentID> --candidate <CandidateAgentID>`
      (or use the function directly if importing the module).
    - This utility handles necessary file locking, format validation, and
      timestamping to ensure integrity of
      `runtime/governance/election_cycle/votes.json`.
    - Directly editing `votes.json` is FORBIDDEN.
    - _(Vote Object Format - managed by utility)_
5.  **Abstention:** Abstaining is not permitted; all agents must participate by
    casting a valid vote for another candidate using the `cast_vote` utility.

## SEP-007: Vote Tally & Decision

1.  **Tally:** After the voting period closes, the current Supervisor (or a
    designated process) will tally the votes from `votes.json`.
2.  **Reporting:** The raw vote counts will be reported to Commander THEA.
3.  **Final Decision:** Commander THEA makes the final decision on the next
    Supervisor, considering the vote tally, the quality and feasibility of the
    candidates' platforms, and overall project needs.

## SEP-008: Protocol Updates

This protocol may be updated via standard procedure, requiring acknowledgment
from all agents.
