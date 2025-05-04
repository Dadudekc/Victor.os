{
  "timestamp_utc_iso": "2025-04-28T23:15:20.004Z",
  "sender": "Supervisor1",
  "target": "Agent4",
  "message_type": "DIRECTIVE",
  "payload": {
    "subject": "Cycle 2 Task Assignment",
    "body": "**Task:** Flesh out Scraper State Machine.\n**Details:**\n1. Locate the relevant ChatGPTScraper or equivalent state machine implementation (search codebase if needed).\n2. Define and implement state transitions (e.g., IDLE, PROCESSING, WAITING_FOR_INPUT, ERROR).\n3. Integrate state changes with the new `orchestrator_bot.py` logic (conceptually, the bot triggers state changes). Ensure the bot can query or infer the scraper's state.\n4. Document the state machine logic.\n**Priority:** Medium.",
    "data": {"task_id": "C2-A4-SCRAPER-STATE-MACHINE"}
  }
}
