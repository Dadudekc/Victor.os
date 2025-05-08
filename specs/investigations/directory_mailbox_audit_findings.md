# Investigation Report: Directory-Based Agent Mailboxes

**Task ID:** `AGENT2-COORDINATION-DIR-MAILBOX-AUDIT-004`
**Author:** Agent-2 (Coordination Expert)
**Date:** {{iso_timestamp_utc()}}
**Related Audit Report:** `specs/reports/agent2_coordination_mailbox_audit_001.md`

## 1. Objective
To investigate the purpose, structure, and usage of directory-based mailboxes found within `runtime/agent_comms/agent_mailboxes/`. This investigation aims to determine if they are part of an active messaging system, how they relate to the JSON file-based mailboxes, and whether they should be integrated into a canonical standard or deprecated.

## 2. Methodology
1.  Listed all contents of `runtime/agent_comms/agent_mailboxes/` to identify all directory-based mailboxes.
2.  Selected a sample of distinct directory types for initial investigation: `Agent-1/`, `commander-THEA/`, and `broadcast/`.
3.  Listed contents of these sample directories and their subdirectories (where applicable and feasible).
4.  Analyzed file types and naming conventions within these directories to infer their purpose and structure.

## 3. Identified Directory-Based Mailboxes (Partial List - نشان دهنده گستردگی)
- `Agent-1/`, `Agent-2/`, `Agent-3/`, `Agent-4/`, `Agent-5/`, `Agent-6/`, `Agent-7/`, `Agent-8/`
- `Agent3/`, `Agent5/`, `Agent7/` (Variations of the above)
- `Captain-Agent-5/`, `Captain-Agent-8/`
- `commander-THEA/`, `Captain-THEA/`
- `general-victor/`
- `broadcast/`
- `agent_meeting/`
*(Note: This list highlights the variety and potential for naming conflicts.)*

## 4. Findings for Sampled Directories

### 4.1. `Agent-1/`
-   **Contents:** Contains an empty `inbox/` directory, an `archive/` directory, a `claim.json` file, and several loose JSON files in its root (e.g., `agent8_blocker_resolved_pbm_src_20231116T123100Z.json`).
-   **Inferred Purpose & Structure:** This appears to be a more complex individual agent mailbox system.
    -   Messages might arrive in `inbox/`.
    -   Processed messages are potentially moved to the root directory or `archive/`.
    -   The loose JSON files in the root appear to be individual archived message objects.
-   **Relation to JSON Mailboxes:** Agent 1 also has `agent_1_mailbox.json` (active with messages) and `Agent-1.json` (empty). The coexistence of these systems for a single agent is confusing and needs clarification. Is `Agent-1/` a legacy system, an extension, or for a different type of message?

### 4.2. `commander-THEA/`
-   **Contents:** Contains `.txt` files (e.g., `agent9_tier1_complete_notice.txt`, `onboarding_failure_memo.txt`).
-   **Inferred Purpose & Structure:** This directory likely serves as a repository for human-readable reports, directives, or memos intended for, or originating from, Commander THEA. It does not appear to use structured JSON messages for automated agent processing in the same way as other mailboxes.
-   **Naming Variant:** `Captain-THEA/` also exists; its purpose and relation to `commander-THEA/` is unknown.

### 4.3. `broadcast/`
-   **Contents:** Contains multiple JSON files with names suggesting they are broadcast messages from specific agents (e.g., `broadcast_agent8_tool_timeout_findings_{{uuid}}.json`, `MSG_AGENT4_BROADCAST_TASKS_READY_{{uuid}}.json`).
-   **Inferred Purpose & Structure:** This directory acts as a central point for one-to-many communication. Each file likely represents a single message object, potentially adhering to a similar structure as messages in the primary JSON mailboxes.
-   **Key Question:** How do agents become aware of new messages in this directory? Is there a polling mechanism, or is it tied to an event system?

## 5. General Observations & Potential Issues
1.  **Proliferation and Inconsistency:** There is a large number of directory-based mailboxes with inconsistent naming conventions (e.g., `Agent-X/` vs. `AgentX/`, `Captain-Agent-X/` vs. `Agent-X/`). This makes it difficult to determine the canonical mailbox for any given agent or entity.
2.  **Redundancy/Conflict:** Many agents/entities appear to have *both* a JSON file mailbox (e.g., `agent-1.json`) *and* one or more directory-based mailboxes (e.g., `Agent-1/`). This is a significant source of confusion and potential for missed or duplicated communication efforts.
3.  **Varied Structures:** The internal structures and file types vary significantly (JSON file-per-message in `Agent-1/` root, `.txt` files in `commander-THEA/`, a collection of JSON message files in `broadcast/`). This means agents would require different logic to interact with each type.
4.  **Unclear Scope of Use:** It's not clear if these directory systems are actively used for primary communication, for archival, for specific types of non-standard messages, or if some are legacy.

## 6. Recommendations / Next Steps
1.  **Clarify Purpose of Each Directory Mailbox:** A systematic review is needed to determine the intended purpose, current usage status (active, deprecated, archival), and owner/maintainer of each directory-based mailbox.
2.  **Consolidate and Standardize:**
    -   If a directory system is active and necessary for a type of communication not well-suited to the simple JSON file standard (e.g., Commander THEA's .txt reports), its scope and interaction rules must be clearly documented.
    -   For standard agent-to-agent messaging, efforts should be made to migrate any active directory-based systems to the proposed canonical JSON file mailbox standard (`agent-<ID>.json`). This would involve defining how messages currently handled by directories (e.g., `broadcast/` messages, individual message files in `Agent-1/`) would be represented or accessed under the canonical system.
    -   Address naming conflicts and redundancies urgently.
3.  **Investigate `broadcast/` Mechanism:** Determine how agents are intended to discover and process messages from the `broadcast/` directory. If it's an active and useful pattern, consider how it aligns with or could be integrated into a more unified agent communication framework (e.g., an AgentBus topic or a specific field in canonical messages).
4.  **Deprecate Unused/Redundant Systems:** Clearly mark and announce the deprecation of any mailbox systems (JSON or directory) that are found to be unused, legacy, or redundant after the audit and standardization efforts.

This initial investigation reveals that directory-based mailboxes add considerable complexity and inconsistency to the agent communication landscape. Addressing them is crucial for achieving a robust and maintainable inter-agent coordination system. 