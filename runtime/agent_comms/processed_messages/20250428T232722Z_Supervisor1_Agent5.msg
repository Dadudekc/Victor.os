{
  "timestamp_utc_iso": "2025-04-28T23:27:22.005Z",
  "sender": "Supervisor1",
  "target": "Agent5",
  "message_type": "QUERY",
  "payload": {
    "subject": "DEBUG: Communication Check - ACK Request",
    "body": "Agent 5, this is a communication channel diagnostic. Please immediately reply by creating a new .msg file in runtime/agent_comms/ with target 'Supervisor1', message_type 'ACK', and a simple payload confirming receipt. Example filename: <Timestamp>_Agent5_Supervisor1.msg. This verifies basic read/write access.",
    "data": {"request_id": "DEBUG-ACK-A5"}
  }
}
