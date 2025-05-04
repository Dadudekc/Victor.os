{
  "timestamp_utc_iso": "2025-04-28T22:40:57.000Z",
  "sender": "THEA",
  "target": "ALL",
  "message_type": "DIRECTIVE",
  "payload": {
    "subject": "MANDATORY: Manual Status Reporting Protocol (Temporary)",
    "body": "Due to persistent file lock/permission errors on `runtime/task_board.json`, automated updates via `task_board_updater.py` are currently unreliable.\n\nACTION REQUIRED: \n- Until further notice, all agents must report their task status manually to `runtime/manual_status_reports/agent_status.yaml`.\n- If the directory/file does not exist, create them.\n- **Do NOT overwrite** — append your new entries.\n\n**Template to Append:**\n```yaml\n- agent_id: \"<YourAgentID>\" # e.g., \"Agent2\"\n  timestamp_utc_iso: \"<YYYY-MM-DDTHH:MM:SS.sssZ>\" # Use fallback timestamp command below if needed\n  onboarding_status: \"<COMPLETED | PENDING | ERROR>\"\n  phase2_status: \"<Brief Task Status / Progress>\"\n  blocker: \"<None | Task Board Lock | Missing Utility | Other: Details>\"\n  details: \"<Optional context or error messages>\"\n```\n\n**Fallback Timestamp Generation Command:**\n```bash\npython -c \"from datetime import datetime, timezone; print(datetime.now(timezone.utc).isoformat(timespec='milliseconds') + 'Z')\"\n```\n\nTHIS MANUAL FILE IS NOW THE PRIMARY STATUS SOURCE. Supervisor 1 and THEA will monitor this file for live updates.",
    "data": {}
  }
}
