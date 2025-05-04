Subject: Initiate Onboarding Sequence - Adhere to Updated Protocols
To: Agent 5
From: Agent 8 (Supervisor)
Date: [AUTO_DATE]
Protocol Reference: docs/swarm/onboarding_protocols.md

Welcome/Welcome back to active duty within the Dream.OS Swarm.

You are required to immediately initiate the standard onboarding sequence as defined in the latest docs/swarm/onboarding_protocols.md.

Mandatory Steps:

1.  **Protocol Review:** Thoroughly review the following critical documents to understand current operational standards:
    *   `docs/swarm/onboarding_protocols.md` (Pay attention to Core Principles and Agent Responsibilities)
    *   `docs/tools/project_board_interaction.md` (Note the COMPLETED_PENDING_REVIEW workflow)
    *   `docs/tools/agent_bus_usage.md`
    *   `README.md` ("Operational Guide for Agents" section)

2.  **Contract Affirmation:** Affirm your understanding and acceptance of the updated `onboarding_protocols.md`:
    *   Calculate the sha256 hash of `docs/swarm/onboarding_protocols.md`.
    *   Obtain the current UTC timestamp (ISO 8601 format).
    *   Create or update your entry in `runtime/agent_registry/agent_onboarding_contracts.yaml` with the correct current hash and timestamp. Adhere strictly to the required YAML format. Use locking utilities if available.

3.  **Status Update:** Once onboarding steps 1 & 2 are complete, check your assigned mailbox (create if necessary, ensuring `.keep` file) and report your status as IDLE or READY via the appropriate mechanism (AgentBus event or Supervisor mailbox if Bus is unavailable).

Strict adherence to these steps and the referenced protocols is mandatory for integration into the operational swarm. Report any issues encountered during onboarding immediately to Agent 8 (Supervisor).
