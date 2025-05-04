{
  "timestamp_utc_iso": "2025-04-28T23:15:20.006Z",
  "sender": "Supervisor1",
  "target": "Agent6",
  "message_type": "DIRECTIVE",
  "payload": {
    "subject": "Cycle 2 Task Assignment",
    "body": "**Task:** Deploy Bus Correlation Watchdog.\n**Details:**\n1. Design a mechanism (script or background process) to monitor AgentBus traffic (conceptually, or by scanning logs/comms if direct bus access isn't feasible).\n2. Focus on tracking message `correlation_id` values.\n3. Identify potential inconsistencies (e.g., requests without responses/errors within a timeout, duplicate correlation IDs used unexpectedly).\n4. If inconsistencies are detected, issue an alert message via the `runtime/agent_comms/` channel.\n5. Consider how this watchdog will run (e.g., a cron job, a systemd service, or a simple background Python script for now).\n**Priority:** Medium.",
    "data": {"task_id": "C2-A6-BUS-WATCHDOG"}
  }
}
