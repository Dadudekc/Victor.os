from datetime import datetime  # Re-add timezone
from pathlib import Path

# from dreamos.coordination.agent_bus import BaseEvent, EventType # F401 Unused
from dreamos.core.tasks.nexus.task_nexus import TaskNexus

# Updated import path - assuming file_io provides append_jsonl or similar
from ..utils.file_io import append_jsonl  # Use utility function


class StatsLoggingHook:
    """
    Logs periodic snapshots of TaskNexus stats to a JSON file.
    """

    # E501 Fix
    def __init__(
        self,
        nexus: TaskNexus,
        log_path: str = "runtime/logs/stats/task_stats.json",  # Updated path
    ):
        self.nexus = nexus
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_snapshot(self):
        tasks = self.nexus.get_all_tasks()
        total = len(tasks)
        # E501 Fix
        completed = sum(1 for t in tasks if t.get("status") in ("completed", "done"))
        failed = sum(1 for t in tasks if t.get("status") == "failed")
        # E501 Fix
        running = sum(1 for t in tasks if t.get("status") in ("claimed", "running"))
        agents = sorted(
            {
                t.get("claimed_by") or t.get("agent")
                for t in tasks
                if t.get("claimed_by") or t.get("agent")
            }
        )

        last = tasks[-1] if tasks else {}
        last_task = {
            "id": last.get("id"),
            "agent": last.get("claimed_by") or last.get("agent"),
            "status": last.get("status"),
            # duration calculation requires timestamp fields
            "duration_seconds": None,
        }

        success_rate = (completed / total) if total > 0 else None

        # average duration if timestamps present
        durations = []
        for t in tasks:
            start = t.get("timestamp")
            end = t.get("processed_at") or t.get("timestamp")
            if start and end:
                # Assuming timestamps are ISO strings, need parsing
                try:
                    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                    durations.append((end_dt - start_dt).total_seconds())
                except (TypeError, ValueError):
                    pass  # Ignore tasks with invalid timestamps
        # E501 Fix
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
            "agent_stats": agent_stats,
        }

        # Use append_jsonl from file_io
        try:
            append_jsonl(self.log_path, snapshot)
        except Exception as e:
            # Log error, but don't crash the hook
            logger.error(  # noqa: F821
                f"Failed to write stats snapshot to {self.log_path}: {e}", exc_info=True
            )
