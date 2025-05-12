import json
import time
from datetime import datetime, timezone
from pathlib import Path

def update_status(agent_id, mailbox_path, task=None, loop_active=True, compliance_score=100):
    """Write or update status.json with heartbeat and agent state."""
    status_path = Path(mailbox_path) / "status.json"
    status = {
        "agent_id": agent_id,
        "last_ping": datetime.now(timezone.utc).isoformat(),
        "current_task": task or "",
        "loop_active": loop_active,
        "compliance_score": compliance_score
    }
    try:
        status_path.write_text(json.dumps(status, indent=2))
    except Exception as e:
        print(f"[WARN] Failed to write status.json for {agent_id}: {e}")

def append_devlog(agent_id, mailbox_path, entry):
    """Append a timestamped entry to devlog.json."""
    devlog_path = Path(mailbox_path) / "devlog.json"
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entry": entry
    }
    try:
        logs = []
        if devlog_path.exists():
            try:
                logs = json.loads(devlog_path.read_text())
            except Exception:
                logs = []
        logs.append(log_entry)
        devlog_path.write_text(json.dumps(logs, indent=2))
    except Exception as e:
        print(f"[WARN] Failed to append devlog for {agent_id}: {e}")

def check_drift(agent_id, mailbox_path, threshold_minutes=5):
    """Return True if last_ping in status.json is older than threshold_minutes."""
    status_path = Path(mailbox_path) / "status.json"
    if not status_path.exists():
        return True
    try:
        status = json.loads(status_path.read_text())
        last_ping = status.get("last_ping")
        if not last_ping:
            return True
        last_ping_ts = datetime.fromisoformat(last_ping.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = (now - last_ping_ts).total_seconds() / 60.0
        return delta > threshold_minutes
    except Exception as e:
        print(f"[WARN] Failed to check drift for {agent_id}: {e}")
        return True 