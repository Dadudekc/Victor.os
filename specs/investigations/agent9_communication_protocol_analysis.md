# Investigation Report: Agent-9 Communication Protocol & Interoperability

**Task ID:** `AGENT2-COORDINATION-AGENT9-INTEROP-003`
**Author:** Agent-2 (Coordination Expert)
**Date:** {{iso_timestamp_utc()}}
**Related Documents:**
- Audit Report: `specs/reports/agent2_coordination_mailbox_audit_001.md`
- Proposal: `specs/proposals/agent2_canonical_mailbox_standards_proposal_001.md`

## 1. Objective
To investigate Agent-9's communication protocol, specifically its use of the `Agent-9.json` mailbox, and assess its interoperability with the proposed canonical mailbox standard. The goal is to recommend steps for either Agent-9 to adopt the standard or for other agents to interoperate with it.

## 2. Methodology
1.  Reviewed the audit findings for `Agent-9.json` which highlighted its unique structure: `{"inbox": [], "outbox": [], "loop_state": {}}`.
2.  Performed a codebase search for "Agent 9" or "agent9" to locate its defining script(s).
3.  Analyzed the identified script (`scripts/agents/new_agent.py`) to understand how Agent-9 reads from and writes to its mailbox.
4.  Compared Agent-9's mechanism with the proposed canonical standard (`agent-<ID>.json` containing a root JSON array of messages).

## 3. Key Findings from Codebase Search

-   **Primary Logic Script:** `scripts/agents/new_agent.py` is identified as the core script for the Agent-9 instance that uses the `Agent-9.json` file-based mailbox.
    -   The script defines `AGENT_ID = "Agent-9"`.
    -   It explicitly reads and writes to `Agent-9.json` maintaining the `{"inbox": [], "outbox": [], "loop_state": {}}` structure.
    -   **Receiving Messages:** The `read_mailbox()` function loads the entire JSON structure. The `process_inbox(messages)` function then iterates through the list provided to it, which is implicitly the `mailbox_data['inbox']` content (as seen in the main loop logic of the script where `mailbox_data = read_mailbox()` and then `processed_ids, new_outbox_messages = process_inbox(mailbox_data.get('inbox', []))`).
    -   **Sending Messages/Responses:** The script generates "receipt" messages in response to inbox messages and appends them to an `outbox` list within its `mailbox_data`. The entire `mailbox_data` (including the updated `outbox` and potentially cleared `inbox` messages) is then written back to `Agent-9.json` by `write_mailbox()`.
    -   **External Communication:** The `new_agent.py` script **does not show Agent-9 writing to other agents' mailboxes**. Its `outbox` appears to be for its own record-keeping or for an external system to poll from its mailbox file.
-   **Manifest File:** `scripts/agents/autonomy_manifest_agent9.json` lists `scripts/agents/new_agent.py` and `runtime/agent_comms/agent_mailboxes/Agent-9.json` as dependencies, confirming their relationship.
-   **Separate Agent-9 Entity (`Agent9ResponseInjector`):** `src/dreamos/agents/agent9_response_injector.py` defines a different agent, also named "Agent9" (or rather, its class is `Agent9ResponseInjector`). This agent uses the `AgentBus` for event-driven communication, not the file-based mailbox system. It listens for `CHATGPT_RESPONSE_SCRAPED` events and creates tasks for Agent-2. This entity is distinct from the `Agent-9` using `Agent-9.json` and is likely out of scope for direct file-based mailbox interoperability concerns unless it also attempts to interact with the file mailboxes.

## 4. Interoperability Assessment with Canonical Standard

The proposed canonical standard is:
-   **Filename:** `agent-<id_lowercase>.json`
-   **Structure:** Root is a JSON array `[]` of message objects.

Comparing Agent-9 (`scripts/agents/new_agent.py` logic & `Agent-9.json`):

1.  **Filename Discrepancy:**
    -   Current: `Agent-9.json` (uppercase 'A')
    -   Proposed: `agent-9.json` (lowercase 'a')
    -   **Impact:** Requires renaming the file and updating Agent-9's `MAILBOX_PATH` definition.

2.  **Structural Discrepancy:**
    -   Current: Root is a JSON object `{"inbox": [...], "outbox": [...], "loop_state": {}}`. Messages for Agent-9 are placed by senders (or are expected by Agent-9) into the `inbox` array within this object.
    -   Proposed: Root is a JSON array `[...]` containing message objects directly.
    -   **Impact for Receiving (Agent-9 reading its mail):** If `Agent-9.json` were changed to the canonical root array structure, `scripts/agents/new_agent.py` would fail. Its `read_mailbox()` would load an array, and subsequent accesses like `mailbox_data.get('inbox', [])` would not yield the message list as intended.
    -   **Impact for Sending (Other agents sending to Agent-9):** If other agents send messages using the canonical structure (placing a message object into a root array in `agent-9.json`), Agent-9's current logic would not find these messages because it specifically looks for `mailbox_data['inbox']`.

## 5. Recommendations

**Option 1: Full Adoption of Canonical Standard by Agent-9 (Preferred)**
1.  **Modify `scripts/agents/new_agent.py`:**
    a.  Change `AGENT_ID` to `agent-9` (or ensure consistent lowercase usage if it has other implications).
    b.  Update `MAILBOX_PATH` to `runtime/agent_comms/agent_mailboxes/agent-9.json`.
    c.  **Mailbox Reading:** `read_mailbox()` should still load the JSON file. However, the main loop logic that calls `process_inbox` should pass the loaded root array directly, e.g., `messages_to_process = read_mailbox()`, then `process_inbox(messages_to_process)`. The expectation of an `inbox` key should be removed.
    d.  **Mailbox Writing/Clearing:** When Agent-9 processes messages, it should remove them from the root array it loaded. If it needs to write back (e.g., if it doesn't process all messages at once), it writes the modified root array back.
    e.  **Internal State (`outbox`, `loop_state`):** These should be managed internally by Agent-9, either in memory (if appropriate for its lifecycle) or in a separate, private state file (e.g., `runtime/agent_comms/agent_mailboxes/.agent-9.state.json`). They should *not* be part of the shared `agent-9.json` mailbox structure.
2.  **Rename Mailbox File:** Rename `Agent-9.json` to `agent-9.json`.
3.  **Migrate Content (if any pending messages):** If there are pending messages in the old `Agent-9.json`'s `inbox`, they need to be moved to the new `agent-9.json` as direct elements of the root array. (Currently, its `inbox` is empty, so this is not an immediate issue).

**Option 2: Adapter Logic for Other Agents (Less Preferred - introduces special casing)**
- If modifying Agent-9 is not immediately feasible, other agents that need to send messages to Agent-9 would require custom logic: when the recipient is `agent-9`, they would have to read `Agent-9.json`, parse the object, insert their message into the `inbox` array, and write the entire object back. This is complex and error-prone, and goes against the goal of standardization.

**Option 3: Hybrid - Agent-9 uses an adapter for its own reading (Interim)**
- Agent-9 could be modified to *read* from a canonically formatted `agent-9.json` by attempting to load it as an array first. If it fails (e.g. `JSONDecodeError` or type error if it gets an object), it could fall back to its old logic of looking for an `inbox` key (for a transition period). This doesn't solve the issue of its `outbox` and `loop_state` being in the shared file.

**Recommendation:** Pursue **Option 1 (Full Adoption)** for long-term consistency and reliability. The `Agent9ResponseInjector` is a separate concern related to `AgentBus` and does not seem to impact this file-based mailbox issue directly.

## 6. Conclusion
Agent-9, as defined in `scripts/agents/new_agent.py`, has a unique file-based mailbox implementation that is incompatible with the proposed canonical standard for both naming and structure. Full adoption of the standard (Option 1) by modifying Agent-9's script and its mailbox file is the recommended path to ensure seamless inter-agent communication via the file-based mailbox system. 