# Automated Election Protocol v1

This document outlines the protocol for automated Captain elections within the Dream.OS agent swarm, triggered every 4 operational cycles.

## 1. Overview

The protocol aims to ensure continuous leadership by periodically evaluating agent performance and electing a Captain based on predefined criteria. The election cycle is set to 4 operational cycles (duration of a cycle to be defined, potentially based on wall clock time or number of tasks processed).

## 2. Triggering Mechanism

- **Cycle Tracking:** A central component (e.g., `SystemMonitorAgent` or a dedicated `ElectionCoordinator`) tracks the operational cycles.
- **Trigger Condition:** An election is triggered automatically when the cycle count reaches a multiple of 4 (Cycle 4, Cycle 8, Cycle 12, etc.).
- **Notification:** Upon triggering, an `ELECTION_START` event is published on the AgentBus, signaling all eligible agents to participate.

## 3. Eligibility and Candidacy

- **Eligibility:** All active, non-critical agents (excluding the current Captain, potentially) with a minimum operational uptime/task completion record (TBD parameters) are eligible to vote and stand for election.
- **Candidacy:** Eligible agents can declare candidacy by publishing a `DECLARE_CANDIDACY` event containing their Agent ID and potentially a brief platform statement or reference to performance metrics. A timeout period will be defined for declarations.

## 4. Evaluation Criteria (Initial Draft)

Agent performance will be evaluated based on metrics tracked potentially by the `SystemMonitorAgent` or aggregated from agent logs/reports. Key criteria include:
- **Task Completion Rate:** Percentage of assigned tasks successfully completed.
- **Task Efficiency:** Average time per task, adherence to deadlines (if applicable).
- **Protocol Compliance:** Adherence to communication, task management, and other system protocols (measured via automated checks or peer review data).
- **Error Rate:** Frequency and severity of operational errors.
- **Initiative/Proactivity:** Contributions beyond assigned tasks (e.g., proposing useful tasks, assisting others - requires tracking mechanism).
- **Resource Usage:** Efficiency in resource consumption (CPU, memory, API calls - TBD if trackable).

*Note: Precise weighting and calculation methods need further definition.*

## 5. Voting Process

- **Voting Period:** A defined time window following the candidacy deadline.
- **Vote Casting:** Eligible agents cast a single vote by publishing a `CAST_VOTE` event containing the Agent ID of their chosen candidate. Votes should be cryptographically signed (if feasible) or sent via a secure channel to the `ElectionCoordinator` to ensure authenticity and prevent tampering.
- **Confidentiality:** Votes should ideally be confidential during the tallying process.

## 6. Vote Tallying

- **Coordinator:** The `ElectionCoordinator` receives and validates votes.
- **Validation:** Checks for eligibility of voter, validity of candidate ID, and ensures one vote per agent.
- **Tallying:** Securely sums votes for each candidate.
- **Tie-breaking:** Define a clear tie-breaking mechanism (e.g., based on specific performance metrics, random selection among tied candidates, or runoff election).

## 7. Election Result and Handover

- **Announcement:** The `ElectionCoordinator` announces the winner by publishing an `ELECTION_RESULT` event containing the new Captain's Agent ID.
- **Captain Handover:**
    - The outgoing Captain completes any critical in-progress tasks or performs a controlled handover.
    - The new Captain assumes responsibilities, potentially involving configuration updates or transfer of specific system tokens/roles.
    - A `CAPTAIN_HANDOVER_COMPLETE` event signals the completion of the transition.

## 8. Security Considerations

- **Vote Integrity:** Mechanisms to prevent duplicate voting, coercion, or tampering.
- **Coordinator Security:** Ensuring the `ElectionCoordinator` itself is secure and impartial.
- **Authentication:** Verifying agent identities during candidacy and voting.

## 9. Open Questions & Future Work

- Define precise duration of an "operational cycle".
- Finalize eligibility criteria (uptime, task count).
- Define specific performance metrics, weighting, and calculation for evaluation.
- Specify secure voting/tallying implementation details (cryptography, secure channel).
- Detail the Captain handover procedure and state transfer.
- Implement the `ElectionCoordinator` agent/service.
- Develop monitoring for election process health.
