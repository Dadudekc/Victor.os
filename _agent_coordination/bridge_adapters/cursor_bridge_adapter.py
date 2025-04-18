"""
CursorBridgeAdapter
-------------------
Interface for dispatching goals to the Cursor subsystem from Dream.OS.

- Launches the dispatcher at: dream_mode/agents/cursor_dispatcher.py
- Passes the goal string via CLI argument
- Captures stdout/stderr and wraps results
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger("CursorBridgeAdapter")

# Path to the cursor dispatcher script (relative to project root)
DISPATCHER_PATH = Path("dream_mode/agents/cursor_dispatcher.py")

class CursorGoal:
    def __init__(self, goal: str, agent_id: Optional[str] = None):
        self.goal = goal
        self.agent_id = agent_id or "UnknownAgent"
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "goal": self.goal,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp
        }

class CursorBridgeAdapter:
    """Adapter for communicating with Cursor via subprocess."""

    def __init__(self):
        if not DISPATCHER_PATH.exists():
            logger.warning(f"Cursor dispatcher not found at {DISPATCHER_PATH}")
        else:
            logger.debug(f"Cursor dispatcher path resolved: {DISPATCHER_PATH.resolve()}")

    def dispatch_goal(self, goal: CursorGoal) -> Dict:
        """Send a goal to Cursor and capture output."""
        try:
            cmd = [
                "python",
                str(DISPATCHER_PATH),
                "--goal", goal.goal,
                "--agent-id", goal.agent_id
            ]

            logger.info(f"Dispatching goal to Cursor: {goal.goal}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "status": "success",
                "goal": goal.to_dict(),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Cursor dispatch failed: {e.stderr}")
            return {
                "status": "error",
                "goal": goal.to_dict(),
                "error": e.stderr,
                "returncode": e.returncode
            }
        except Exception as e:
            logger.exception("Unexpected error dispatching to Cursor")
            return {
                "status": "exception",
                "goal": goal.to_dict(),
                "error": str(e)
            } 