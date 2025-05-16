# Dream.OS Message Routing Protocol

This document outlines the formal communication architecture within Dream.OS, distinguishing between the inter-agent inbox system and the PyAutoGUI-based interface for Large Language Model (LLM) interactions via Cursor.

## 1. Core Principle: Separation of Concerns

The Dream.OS messaging architecture is built on a fundamental separation:

*   **Coordination Layer (Inbox):** Facilitates communication *between* agents for internal operational tasks, status updates, and collaborative efforts.
*   **Execution Channel (PyAutoGUI via Cursor):** Manages the direct interaction *with* LLM agents for prompt injection, response retrieval, and simulated cognitive tasks.

This separation ensures that inter-agent operational messages do not directly become LLM prompts, and LLM interactions are intentional and managed.

## 2. Communication Channels

### 2.1. Inbox System: Agent ↔ Agent Communication

*   **Purpose:**
    *   Internal (inter-agent) communications.
    *   Protocol messages (e.g., task status, acknowledgments).
    *   Status synchronization between agents.
    *   Event-driven triggers (e.g., lore generation, recovery notices).
    *   Task handoffs and dependency notifications.
    *   Feedback relay between operational components.
    *   Directive dispatch (e.g., THEA to agent, agent to agent coordination).

*   **Format:**
    *   JSON or Markdown (MD) messages.
    *   Messages are stored as files within individual agent mailboxes.

*   **Location:**
    ```
    runtime/agent_mailboxes/Agent-<n>/inbox.json
    ```
    (Where `<n>` is the agent identifier).

*   **Characteristics:**
    *   File-based: Enables persistent and auditable communication.
    *   Transparent: Message content can be inspected for debugging and monitoring.
    *   Logged: Interactions via the inbox system should be logged by the respective agents or the AutonomyEngine for traceability.
    *   Asynchronous: Agents check their inboxes periodically as part of their operational loop.
    *   **No direct GUI interaction required or implied.**

### 2.2. PyAutoGUI: Agent ↔ Cursor Chat Interface (LLM I/O)

*   **Purpose:**
    *   Primary channel for an agent's "cognitive" tasks requiring LLM processing.
    *   Injecting prompts (including self-generated prompts) into the Cursor chat interface.
    *   Retrieving LLM responses from the Cursor chat interface.
    *   Orchestrating GUI loop execution via tools like `CursorInjector` and `ResponseRetriever`.
    *   Enabling the runtime execution of the `AutonomousLoop` by interfacing with the LLM for decision-making or task processing steps when needed.

*   **Characteristics:**
    *   GUI-driven: Relies on `PyAutoGUI` to simulate human interaction with the Cursor application.
    *   LLM-centric: Specifically designed for sending information to and receiving information from the LLM.
    *   Intentional: Prompts sent via this channel are deliberately constructed by an agent for LLM processing.

## 3. Ideal Operational Workflow Example

This workflow illustrates how an agent might use both channels:

1.  📬 **Inbox Message Reception:** Agent-A receives a message (e.g., a `task-dependency-fulfilled` notification from Agent-B) in its `inbox.json`.
2.  🧠 **Internal Processing & Prompt Generation:** Agent-A parses the inbox message. Based on its internal logic and the message content, it determines it needs to perform a task that requires LLM input (e.g., drafting a summary or planning next steps). Agent-A constructs a self-prompt for the LLM.
3.  🎯 **LLM Interaction via PyAutoGUI:** Agent-A utilizes its `CursorInjector` component (which uses `PyAutoGUI`) to type the generated prompt into its designated Cursor chat window.
4.  🧾 **Response Retrieval & Internal Update:** After the LLM responds in Cursor, Agent-A uses its `ResponseRetriever` component to copy the response. This response is processed internally. The outcome might be logged to the agent's devlog, and the status of its current task might be updated via the `ProjectBoardManager`.
5.  📤 **Outcome Logging & Optional Inbox Dispatch:** Agent-A logs the result of its LLM-assisted task. If necessary (e.g., task completion, new dependency for another agent), Agent-A might then generate a new message and dispatch it to another agent's inbox.

## 4. Benefits of This Architecture

*   **Clear Separation:** Distinguishes the agent's internal operational coordination from its external "cognitive" processing via the LLM.
*   **Intentional LLM Interaction:** Ensures that only deliberately crafted prompts are sent to the LLM, preventing accidental or noisy interactions.
*   **Agent Autonomy:** Agents can process and "think" about inbox messages (perform internal logic, consult local state, update task boards) *before* deciding to engage the LLM via the GUI.
*   **Modularity & Testability:** Allows the inter-agent communication logic and the LLM interaction logic to be developed, tested, and debugged more independently.
*   **Transparency & Auditability:** File-based inboxes provide a clear trail of inter-agent communication.

## 5. Protocol Adherence

*   **Inbox for Coordination:** All inter-agent messages related to operational status, task management, and internal events **must** use the inbox system.
*   **PyAutoGUI for LLM I/O:** All interactions requiring prompt input to or response retrieval from an LLM via the Cursor interface **must** use the PyAutoGUI-based channel.
*   **No Direct GUI from Inbox Logic:** Logic handling inbox messages should not directly trigger GUI operations for LLM prompting. Instead, it should update the agent's state or internal tasking, which might then lead to a separate step where the agent decides to use the GUI for LLM interaction.
*   **Message Typing:** Consider introducing clear message types within the inbox system (e.g., `prompt_directive_message` vs. `coordination_message`) if the loop runner needs to distinguish how to initiate processing for messages that *originate* from an inbox but are *intended* to result in an LLM prompt. However, the primary distinction remains: inbox is for agent-to-agent, PyAutoGUI is for agent-to-LLM.

This protocol is fundamental to the scalability, maintainability, and clarity of Dream.OS operations. 