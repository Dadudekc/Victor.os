# Agent Communications Directory (`runtime/agent_comms`)

**Purpose:** This directory manages file-based communication and state sharing between agents, complementing the real-time `AgentBus`.

**Structure & Systems:**

*   `/agent_mailboxes`:
    *   **Purpose:** Provides dedicated asynchronous mailboxes for each agent.
    *   **Structure:** Contains subdirectories for each agent (e.g., `/Agent1`, `/Agent2`).
    *   **Agent Mailbox Structure:**
        *   `/inbox`: Incoming messages or task files deposited here for the agent to process.
        *   `/archive`: Processed/completed items moved here from the inbox.

*   `/project_boards`:
    *   **Purpose:** Used for shared project state, task tracking, or collaborative artifacts accessible by multiple agents involved in a specific project or task.
    *   **Structure:** Managed by `src/dreamos/core/comms/project_board.py`. (Implementation is currently a placeholder).
    *   **Structure:** Likely contains subdirectories or files representing different projects or shared states.

*   `/archive` (Root Level):
    *   **Purpose:** General archive for root-level transient files or logs, potentially related to supervisor broadcasts or older systems.

*   `.msg` files (Root Level):
    *   **Purpose:** Likely transient broadcast messages or status updates originating from central services (e.g., Supervisors) before being routed or processed. Their exact lifecycle needs clarification.

*   `/processed_messages` (Root Level):
    *   **Purpose:** Observed directory containing copies of root-level `.msg` files. Its exact role (logging, intermediate step?) needs clarification.

**Maintenance & Usage Notes:**

*   Agents are responsible for monitoring their respective inboxes within `/agent_mailboxes`.
*   Code interacting with these systems should handle moving items from `inbox` to `archive` upon successful processing.
*   The utility script `src/tools/dreamos_utils/summarize_agent_comms.py` can inspect root-level `.msg` files and archive them (using `--archive`) to the root `/archive` directory. Its applicability to mailbox/project board contents needs review.
*   While `AgentBus` is preferred for real-time events, these directories support persistent task/message passing.

**(Developer Note:** Code managing `/agent_mailboxes` is partially implemented (`MailboxHandler` exists, `OrchestratorBot` uses it). Code for `/project_boards` (`ProjectBoardManager`) is currently a placeholder. Further implementation and integration are needed.)

## Debate Arena & Persona System
- The Dream.OS swarm supports structured debates where agents adopt specific personas to argue topics until a resolution is reached.
- Debate topics are submitted via Discord; agents are assigned personas and respond in-character.
- Persona definitions are stored in `runtime/agent_comms/debate_personas/`.
- See the debate protocol and sample personas in that directory for details.
