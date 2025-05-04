{
  "timestamp_utc_iso": "2025-04-28T23:15:20.002Z",
  "sender": "Supervisor1",
  "target": "Agent2",
  "message_type": "DIRECTIVE",
  "payload": {
    "subject": "Cycle 2 Task Assignment",
    "body": "**Task:** Extend Context Router Prototype.\n**Details:**\n1. Locate the existing prototype code for context routing (search codebase if needed).\n2. Modify it to intercept task messages (e.g., specific types or topics) from the `AgentBus` API (assuming `dreamos.core.coordination.agent_bus`).\n3. Implement basic routing logic based on message content or metadata.\n4. Ensure the router correctly publishes the routed message back to the bus for the intended recipient agent(s).\n**Priority:** Medium.",
    "data": {"task_id": "C2-A2-CONTEXT-ROUTER-EXTEND"}
  }
}
