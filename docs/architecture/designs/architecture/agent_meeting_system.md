# Architecture: Agent Meeting System

**Task:** `FEATURE-AGENT-MEETING-001`
**Status:** Design Phase

## 1. Overview

This document outlines the architecture for a system enabling autonomous agents within Dream.OS to conduct structured meetings for purposes like collaborative brainstorming, proposal refinement, decision-making, and coordinated planning.

The system aims to be asynchronous, persistent, and discoverable, leveraging the existing agent communication infrastructure where possible.

## 2. Core Concepts

*   **Meeting:** A defined context for discussion around a specific topic or goal, identified by a unique `meeting_id`.
*   **Meeting Mailbox:** A dedicated directory structure (e.g., `runtime/agent_comms/meetings/<meeting_id>/`) to store all messages related to a specific meeting.
*   **Meeting Topic/Goal:** A clear statement defining the purpose of the meeting.
*   **Participants:** A list of agent IDs invited to or currently participating in the meeting.
*   **Meeting State:** The current phase of the meeting (e.g., `open`, `discussion`, `voting`, `closed`, `archived`).
*   **Message Schema:** Defined formats for different message types within a meeting (e.g., `proposal`, `comment`, `vote`, `summary`, `agenda_item`, `state_change`).
*   **Meeting Protocol:** Rules governing how meetings are initiated, how agents participate, how decisions are reached (e.g., voting mechanisms), and how meetings conclude.
*   **Facilitator (Optional):** A designated agent (or potentially a system role) responsible for guiding the meeting, enforcing protocols, summarizing discussions, and managing state transitions.

## 3. Proposed Architecture

1.  **Meeting Directory Structure (`runtime/agent_comms/meetings/`)**
    *   Each subdirectory represents a meeting, named with a unique `meeting_id` (e.g., UUID or descriptive slug).
    *   Inside each meeting directory:
        *   `manifest.json`: Contains metadata about the meeting (topic, creator, participants, current state, facilitator, creation timestamp, protocol used).
        *   `agenda.json` (Optional): List of discussion points or proposals.
        *   `participants.json`: List of invited/active agent IDs and their status (e.g., joined, voted).
        *   `messages/`: Directory containing individual message files.
            *   Each message stored as a JSON file (e.g., `msg_<timestamp>_<agent_id>_<type>.json`).
            *   Filename includes timestamp, originator agent ID, and message type for easy sorting/filtering.

2.  **Message Schema (`src/dreamos/core/comms/meeting_schemas.py`)**
    *   Define standard fields: `message_id`, `meeting_id`, `timestamp_utc`, `agent_id`, `message_type`.
    *   Define type-specific fields:
        *   `proposal`: `proposal_id`, `title`, `details`, `status` (proposed, accepted, rejected).
        *   `comment`: `text`, `reply_to_message_id` (optional).
        *   `vote`: `proposal_id`, `vote` (yes/no/abstain), `rationale` (optional).
        *   `summary`: `summary_text`.
        *   `state_change`: `old_state`, `new_state`, `reason`.

3.  **Agent Capabilities**
    *   `meeting.create`: Initiates a new meeting, creates the directory structure, writes `manifest.json`, invites initial participants. Input: `topic`, `initial_participants`. Output: `meeting_id`.
    *   `meeting.discover`: Allows agents to find active/relevant meetings (e.g., query a central index or scan the meetings directory).
    *   `meeting.join`: Allows an invited agent to formally join a meeting (updates `participants.json`). Input: `meeting_id`.
    *   `meeting.leave`: Allows an agent to leave a meeting. Input: `meeting_id`.
    *   `meeting.post_message`: Sends a message (comment, proposal, etc.) to the meeting mailbox. Input: `meeting_id`, `message_type`, `message_data`. Output: `message_id`.
    *   `meeting.read_messages`: Fetches messages from a meeting mailbox, potentially filtering by type, timestamp, or agent. Input: `meeting_id`, `filter_options`. Output: List of messages.
    *   `meeting.vote`: Casts a vote on a specific proposal. Input: `meeting_id`, `proposal_id`, `vote`, `rationale`.
    *   `meeting.get_info`: Retrieves the meeting metadata (`manifest.json`). Input: `meeting_id`.
    *   `meeting.update_state` (Facilitator Only?): Changes the meeting state. Input: `meeting_id`, `new_state`, `reason`.

4.  **Meeting Protocol (V1 - Simple Proposal/Vote)**
    *   **Initiation:** Any agent with `meeting.create` can start a meeting.
    *   **Joining:** Invited agents use `meeting.join`.
    *   **Discussion:** Agents post `comment` messages.
    *   **Proposals:** Agents post `proposal` messages.
    *   **Voting:** When a proposal is ready (determined by facilitator or time limit?), a voting phase begins. Agents use `meeting.vote`.
    *   **Decision:** Threshold for acceptance (e.g., >50% yes votes of active participants).
    *   **Closure:** Facilitator (or initiating agent if no facilitator) posts a `summary` and updates state to `closed` using `meeting.update_state`.

5.  **Facilitation (Optional)**
    *   A dedicated `FacilitatorAgent` could be assigned during creation.
    *   Responsibilities: Keep discussion on topic, manage agenda, initiate voting phases, summarize outcomes, manage state transitions.
    *   If no facilitator, the initiating agent might perform basic state changes, or protocols might rely on timeouts.

6.  **Integration with Agent Bus**
    *   Events could be dispatched for key meeting actions: `MEETING_CREATED`, `AGENT_JOINED_MEETING`, `NEW_MESSAGE_IN_MEETING`, `PROPOSAL_ADDED`, `VOTING_STARTED`, `MEETING_CLOSED`.
    *   Agents could subscribe to these events to stay informed without constant polling.

## 4. Implementation Details

*   **Persistence:** Relies on file system operations within `runtime/agent_comms/meetings/`. Requires robust file locking if multiple agents access the same meeting files concurrently (though posting individual messages might avoid direct conflicts often).
*   **Concurrency:** Consider using file locks (e.g., `python-filelock`) when updating shared files like `manifest.json` or `participants.json`.
*   **Discovery:** How do agents find relevant meetings? Options:
    *   Direct invitation (message to agent mailbox).
    *   Scanning the `meetings/` directory.
    *   A central meeting registry/index (could be a simple JSON file or DB table updated via AgentBus events).
*   **Schema Validation:** Use Pydantic models for message types to ensure consistency.

## 5. Next Steps

1.  Define detailed message schemas (`meeting_message.schema.json`).
2.  Implement core agent capabilities (`meeting.create`, `meeting.post_message`, `meeting.read_messages`, `meeting.get_info`).
3.  Implement basic directory/file management logic with locking.
4.  Develop a simple agent that can create and participate in a meeting.
5.  Refine discovery mechanisms and Agent Bus integration.

## 6. Risks & Considerations

*   **Concurrency:** File-based system needs careful locking to prevent race conditions when multiple agents modify the same meeting state.
*   **Scalability:** A very large number of meetings or messages per meeting could impact file system performance. A database backend might be better long-term.
*   **Complexity:** Implementing robust protocols, facilitation logic, and error handling can become complex.
*   **Agent Compliance:** Assumes agents will follow the defined protocols. 