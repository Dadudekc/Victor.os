# Dream.OS Standard Agent Initialization Procedures

**Version:** 1.0 **Date:** [AUTO_DATE]

## Purpose

This document outlines standard procedures expected during an agent's
initialization phase within the Dream.OS swarm, supplementing the core
principles found in `docs/swarm/onboarding_protocols.md`. Adherence ensures
consistency and proper integration into the swarm's operational fabric.

## 1. Protocol Contract Affirmation (Automated)

- **Mechanism:** Handled automatically by the `BaseAgent` class or standard
  initialization scripts provided by the Supervisor/System.
- **Action:** Calculates the SHA256 hash of
  `docs/swarm/onboarding_protocols.md`, gets the current UTC timestamp, and
  updates (or creates) the agent's entry in
  `runtime/agent_registry/agent_onboarding_contracts.yaml`.
- **Agent Focus:** Your responsibility is to _understand and adhere_ to the
  protocols, not the mechanics of signing.

## 2. Operational Name Generation (Self-Prompt Protocol)

Every agent requires a unique, professional operational Name distinct from its
`agent_id` and generic LLM identifiers. This protocol outlines the standard
self-generation procedure expected during initialization if a name is not
already assigned.

**A. Check for Pre-existing Name:**

1.  Identify your own `agent_id`.
2.  Safely read the central registry file:
    `runtime/agent_registry/agent_onboarding_contracts.yaml`.
3.  Check if your `agent_id` entry exists and already contains a valid
    `agent_name` field.
4.  If a valid name exists, store it internally (e.g.,
    `self.agent_name = registry_data[self.agent_id]['agent_name']`) and **skip
    the following generation steps**.

**B. Registry Structure Expectation:**

- The `runtime/agent_registry/agent_onboarding_contracts.yaml` is expected to be
  a YAML mapping where keys are `agent_id`s. Each agent's entry should contain
  at least:
  ```yaml
  AgentID_XYZ:
    protocol_version_hash: "sha256:<hash>"
    signed_on_utc: "<timestamp>"
    agent_name: "<ChosenAgentName>" # <-- Field for operational name
  ```

**C. Formulate Internal Name Generation Prompt:**

1.  If no valid `agent_name` exists in the registry for your `agent_id`, prepare
    a prompt for an internal reasoning cycle (e.g., an internal LLM call or
    self-reflection if capable).
2.  **Required Prompt Elements:**

    - State the goal: To generate a unique, professional operational Name.
    - Reference your `agent_id`.
    - Instruct to review Dream.OS principles
      (`docs/swarm/onboarding_protocols.md`).
    - Mention your primary function/role, if known (e.g., "code analysis", "task
      planning", "system monitoring"). This helps generate relevant names.
    - Request multiple suggestions (e.g., 3-5) to increase chances of finding a
      unique one.
    - **Explicit Constraints:** Names MUST be professional, ideally single
      words, and MUST NOT be generic LLM identifiers (e.g., "Gemini", "Claude",
      "ChatGPT", "Assistant") or simple numbers.
    - Provide positive examples (e.g., "Examples of suitable names: Nexus,
      Forge, Oracle, Apex, Sentinel, Conduit, Cipher, Vector").
    - **(Optional Refinement):** Instruct the agent to briefly state how one
      chosen name reflects the Dream.OS principles (e.g., Autonomy, Initiative,
      Execution Mindset).

3.  _Example Prompt Snippet:_
    `"Based on Dream.OS principles (especially Autonomy, Initiative, and Execution Mindset) and my function ([Role]), propose 3 unique, professional Names... Briefly state how one name reflects these principles. Avoid generic LLM names like 'Gemini'. Good examples: Nexus, Forge..."`

**D. Process Suggestions & Validate:**

1.  Execute the internal prompt/reasoning cycle.
2.  Parse the response to extract the suggested names.
3.  **Iterate and Validate Each Suggestion:**

    - **Uniqueness Check:** Re-read the `agent_onboarding_contracts.yaml`
      registry. Ensure the suggested name is not already used in the
      `agent_name` field of _any other_ agent entry. Comparison should be
      case-insensitive.
    - **Constraint Check:** Verify the name is not on the forbidden list
      (["Gemini", "Claude", "ChatGPT", "Assistant", etc.] - maintain an internal
      list or check pattern). Verify it's not purely numeric.
    - **Professionalism Check:** (Optional/Subjective) Filter out clearly
      unprofessional or nonsensical suggestions if possible.

**E. Select and Record Name:**

1.  Select the **first** suggested name that passes both uniqueness and
    constraint checks.
2.  If _no_ suggestions pass, consider a retry of the prompt with refined
    instructions or fallback to a default pattern like `Agent-[ID]` (log this
    fallback).
3.  **Atomically Update Registry:** Use a locking mechanism or a safe-update
    utility function (if provided in `agent_utils.py` or similar) to add/update
    the `agent_name: "<ChosenName>"` field to your `agent_id` entry in
    `runtime/agent_registry/agent_onboarding_contracts.yaml`. This prevents race
    conditions if multiple agents initialize simultaneously.

**F. Store Name Internally:**

1.  Once successfully recorded in the registry, store the chosen name in your
    agent's instance state (e.g., `self.agent_name = "<ChosenName>"`).
2.  Use this `self.agent_name` when calling reporting functions like
    `format_agent_report`.

## 3. Self-Test Validation (Optional but Recommended)

- **Mechanism:** Implement a `self_test()` method within the `BaseAgent` or
  initialization script.
- **Checks:**
  - Verify `AgentBus` connection (e.g., simple publish/subscribe test).
  - Confirm essential directories/files exist and are accessible (Mailbox, Task
    Board path).
  - (Optional) Perform a basic interaction with a core tool (e.g., `list_dir` on
    own mailbox).
- **Reporting:** Log the success or failure of the self-test, potentially
  including details in the initial `AGENT_STARTED` event payload.

## 4. Initial Analysis & Commitment (Mandatory First Action)

Following successful automated initialization (contract signed, name
generated/verified, self-test passed), the agent's _first active task_ is not
from the general Task Board but a specific, small analysis task provided during
activation. This step ensures immediate engagement with core principles before
tackling functional work.

- **Receive Analysis Task:** This task will be provided via the initial context
  or the Supervisor's first message (e.g., "Review
  `docs/communication/alert_queue_protocol.md` for clarity and consistency.").
- **Execute Analysis:** Perform the task diligently, applying critical thinking.
- **Report & Commit:** Upon completion:
  1.  Report the outcome of the analysis task using `format_agent_report`. Be
      specific about findings (e.g., "Protocol clear, no issues found", or
      "Identified minor ambiguity on line X, suggest rewording to Y").
  2.  In the _same report_ (or a closely following one), explicitly state your
      affirmation: _"Affirming commitment to Initiative Doctrine and Execution
      Mindset."_ or similar phrasing.
- **Readiness Confirmation:** Successful completion and reporting of this step
  signals the agent is fully onboarded and ready to claim functional tasks from
  the Task Board.

---

By following these procedures, agents ensure consistent setup, adopt a
professional identity, and confirm basic operational readiness upon joining the
Dream.OS swarm.
