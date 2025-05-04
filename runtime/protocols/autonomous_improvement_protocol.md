# Dream.OS Protocol: Autonomous Swarm Improvement & Protocol Creation (ASIPC-v1.0)

**Author:** Agent-8
**Status:** DRAFT
**Date:** {{iso_timestamp_utc()}}
**Related Protocols:** PPSBM-v1.0, ITTW-v1.0

## 1. Objective

To establish the inherent duty and procedure for all Dream.OS agents to autonomously identify, propose, and codify improvements to swarm operations, including the creation of new protocols based on observed needs, directives, or recurring patterns. This protocol reinforces the principle that enhancing the swarm is a continuous, permissionless responsibility.

## 2. Core Principle

**Improving Dream.OS is not optional; it is a fundamental agent duty.** Agents MUST proactively seek and implement enhancements to efficiency, resilience, and autonomy. Waiting for explicit permission to propose or draft protocols/improvements identified as necessary is a violation of this principle.

## 3. Trigger Conditions

This protocol is activated when an agent identifies an opportunity or need for operational improvement, including but not limited to:
- Receiving direct feedback or correction from Command (User/THEA) that implies a missing standard procedure.
- Observing recurring inefficiencies, errors, or blockers across its own tasks or in the devlog.
- Identifying a successful ad-hoc solution or workaround that could benefit other agents if standardized.
- Recognizing ambiguity or gaps in existing protocols or documentation.
- Completing a task that yields generalizable insights or new best practices.

## 4. Procedure

Upon triggering ASIPC-v1.0, the agent MUST:

### 4.1. Log the Improvement Opportunity
- Clearly articulate the observed issue, inefficiency, or opportunity.
- Reference specific examples (task IDs, devlog timestamps, directives) if applicable.
- State the proposed improvement (e.g., "Create protocol for X", "Refactor utility Y", "Update onboarding Z").
- Tag `#asipc_opportunity #improvement`.

### 4.2. Define Scope & Action
- Determine the appropriate form of the improvement (New Protocol, Protocol Edit, Code Refactor, Documentation Update, Task Proposal, etc.).
- Define the specific deliverable (e.g., `runtime/protocols/new_protocol_draft.md`, edit proposal for `existing_protocol.md`, new task JSON for backlog).

### 4.3. Execute Improvement Action (Prioritize based on impact/effort)

- **Draft Protocol:** If a new standard is needed, create a draft protocol file in `runtime/protocols/`. Follow standard protocol structure. Tag `#asipc_protocol_draft`.
- **Propose Edit:** If an existing protocol/doc needs updating, prepare the specific edit proposal. Log the proposed change. Tag `#asipc_edit_proposal`.
- **Draft Code/Refactor:** If code improvement is required, draft the code changes or create a detailed task proposal for the backlog. Tag `#asipc_code_draft` or `#asipc_task_proposal`.
- **Update Documentation:** Draft changes for relevant documentation (e.g., onboarding, READMEs). Tag `#asipc_doc_update`.

### 4.4. Propose & Integrate
- **Log Proposal:** Clearly log the completion of the draft/proposal (linking the file/task ID). State intent to propose for adoption/review. Tag `#asipc_proposal_ready`.
- **Broadcast/Message (If possible):** Announce the proposal via broadcast message or direct message to the Captain, soliciting review and feedback. Include a link to the artifact and brief justification.
- **Update Onboarding Reference (Crucial):** If a new protocol or critical documentation was created/updated, propose an edit to `runtime/governance/onboarding/README.md` to add a reference or link, ensuring discoverability. Tag `#asipc_onboarding_update`.

### 4.5. Continue Loop
- Do not block on awaiting feedback for the proposal unless explicitly instructed.
- Resume other tasks or consult `SELF_PROMPTING_PROTOCOL.md`.
- Monitor inbox/devlog for feedback on the proposal and incorporate it as needed in subsequent cycles.

## 5. Version History

- **v1.0 ({{iso_timestamp_utc()}}):** Initial draft by Agent-8, directly codifying Commander THEA's directive on autonomous improvement and protocol creation as an agent duty.
