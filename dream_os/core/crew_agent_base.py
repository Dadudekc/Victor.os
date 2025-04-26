import uuid
import logging
import time
from collections import deque
from typing import Dict, Any, List
from .crew_roles import get_role, CrewRole
from dream_os.adapters.base_adapter import AdapterRegistry

log = logging.getLogger(__name__)

class CrewAgent:
    def __init__(self, name: str, role_name: str):
        self.id: str = str(uuid.uuid4())[:8]
        self.name: str = name
        self.role: CrewRole = get_role(role_name)
        self.memory: deque = deque(maxlen=50)
        self.stats: Dict[str, Any] = {"tasks": 0, "fail": 0, "avg_ms": 0}
        # Initialize adapters according to role defaults
        self.adapters = [AdapterRegistry.get(tool) for tool in self.role.default_tools]

    def can_handle(self, task_type: str) -> bool:
        """Check if this agent has the skill for the given task type."""
        return task_type in self.role.skills

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task, record metrics, and return status/output."""
        t0 = time.time()
        try:
            # Call the default adapter if available
            if self.adapters:
                result = self.adapters[0].execute(task)
            else:
                result = f"{self.name} handled «{task['type']}»"
            status = "ok"
            return {"status": status, "output": result}
        except Exception as e:
            status = "error"
            result = str(e)
            self.stats["fail"] += 1
            return {"status": status, "output": result}
        finally:
            dt = int((time.time() - t0) * 1000)
            # update rolling average
            self.stats["avg_ms"] = (self.stats["avg_ms"] + dt) // 2
            self.stats["tasks"] += 1
            self.memory.append(task)
            log.debug(f"{self.name} ⟶ {status} in {dt} ms") 
