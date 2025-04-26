import logging
import threading
import time
from typing import List, Dict, Any
from ..core.crew_agent_base import CrewAgent
from .task_nexus import pop_task, log_result

log = logging.getLogger(__name__)

class PromptRouterService(threading.Thread):
    """Continuously pulls tasks, routes to best-fit agent, logs outcome."""
    def __init__(self, agents: List[CrewAgent], poll_sec: float = 1.0):
        super().__init__(daemon=True)
        self.agents = agents
        self.poll_sec = poll_sec

    def run(self):
        while True:
            task = pop_task()
            if task:
                agent = self._select_agent(task["type"])
                if agent:
                    # Route through adapter and record latency
                    start = time.time()
                    res = agent.execute(task)
                    latency_ms = int((time.time() - start) * 1000)
                    adapter_name = agent.role.default_tools[0] if agent.role.default_tools else None
                    entry = {
                        "task": task,
                        "agent": agent.name,
                        "adapter": adapter_name,
                        "latency_ms": latency_ms,
                        **res
                    }
                    log_result(entry)
                    log.info(f"{agent.name} ▸ {task['type']} ▸ {res['status']} (adapter={adapter_name} {latency_ms}ms)")
                else:
                    log.warning(f"No agent for task type '{task['type']}'")
                    # Log fallback error to TaskNexus
                    log_result({
                        "task": task,
                        "agent": None,
                        "status": "failed",
                        "error": f"No agent for task type '{task['type']}'",
                        "adapter": None,
                        "latency_ms": None
                    })
            else:
                time.sleep(self.poll_sec)

    # — simplistic priority; expand to load-balancer later
    def _select_agent(self, t_type: str) -> CrewAgent | None:
        for a in self.agents:
            if a.can_handle(t_type):
                return a
        return None 
