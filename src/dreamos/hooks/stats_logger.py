import json
from pathlib import Path
from datetime import datetime
from dream_mode.task_nexus.task_nexus import TaskNexus
from dreamos.utils.json_io import write_json_safe

class StatsLoggingHook:
    """
    Logs periodic snapshots of TaskNexus stats to a JSON file.
    """
    def __init__(self, nexus: TaskNexus, log_path: str = "dream_logs/stats/task_stats.json"):
        self.nexus = nexus
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_snapshot(self):
        tasks = self.nexus.get_all_tasks()
        total = len(tasks)
        completed = sum(1 for t in tasks if t.get("status") in ("completed", "done"))
        failed = sum(1 for t in tasks if t.get("status") == "failed")
        running = sum(1 for t in tasks if t.get("status") in ("claimed", "running"))
        agents = sorted({t.get("claimed_by") or t.get("agent") for t in tasks if t.get("claimed_by") or t.get("agent")})

        last = tasks[-1] if tasks else {}
        last_task = {
            "id": last.get("id"),
            "agent": last.get("claimed_by") or last.get("agent"),
            "status": last.get("status"),
            # duration calculation requires timestamp fields
            "duration_seconds": None
        }

        success_rate = (completed / total) if total > 0 else None

        # average duration if timestamps present
        durations = []
        for t in tasks:
            start = t.get("timestamp")
            end = t.get("processed_at") or t.get("timestamp")
            if start and end:
                durations.append(end - start)
        avg_duration = (sum(durations) / len(durations)) if durations else None

        # per-agent stats
        agent_stats = {}
        for t in tasks:
            agent = t.get("claimed_by") or t.get("agent")
            if not agent:
                continue
            stats = agent_stats.setdefault(agent, {"completed": 0, "failed": 0})
            if t.get("status") in ("completed", "done"):
                stats["completed"] += 1
            if t.get("status") == "failed":
                stats["failed"] += 1

        snapshot = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "agents": agents,
            "last_task": last_task,
            "success_rate": success_rate,
            "avg_duration_seconds": avg_duration,
            "agent_stats": agent_stats
        }

        write_json_safe(self.log_path, snapshot, append=True) 
