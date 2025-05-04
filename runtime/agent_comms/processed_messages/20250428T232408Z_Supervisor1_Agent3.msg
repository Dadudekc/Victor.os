{
  "timestamp_utc_iso": "2025-04-28T23:24:08.003Z",
  "sender": "Supervisor1",
  "target": "Agent3",
  "message_type": "DIRECTIVE",
  "payload": {
    "subject": "Cycle 2 Task Assignment (Re-Dispatch)",
    "body": "**Task:** Build Contract Updater Utility.\n**Details:**\n1. Create a new script (e.g., `src/tools/dreamos_utils/update_onboarding_contract.py`).\n2. The script should read agent status entries from `runtime/manual_status_reports/agent_status.yaml`.\n3. For agents reporting a valid timestamp and \"COMPLETED\" onboarding status, the script should update (or add) their corresponding entry in `runtime/agent_registry/agent_onboarding_contracts.yaml` with the correct timestamp.\n4. Implement appropriate file locking or safe-write logic for the contracts file.\n**Priority:** Medium.",
    "data": {"task_id": "C2-A3-CONTRACT-UPDATER-UTIL"}
  }
}
