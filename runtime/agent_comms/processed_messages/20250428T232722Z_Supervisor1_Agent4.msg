{
  "timestamp_utc_iso": "2025-04-28T23:27:22.004Z",
  "sender": "Supervisor1",
  "target": "Agent4",
  "message_type": "QUERY",
  "payload": {
    "subject": "DEBUG: Communication Check - ACK Request",
    "body": "Agent 4, this is a communication channel diagnostic. Please immediately reply by creating a new .msg file in runtime/agent_comms/ with target 'Supervisor1', message_type 'ACK', and a simple payload confirming receipt. Example filename: <Timestamp>_Agent4_Supervisor1.msg. This verifies basic read/write access.",
    "data": {"request_id": "DEBUG-ACK-A4"}
  }
}
