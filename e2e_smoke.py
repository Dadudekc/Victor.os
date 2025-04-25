import time
import threading
import os
import json
from dream_os.core.crew_agent_base import CrewAgent
from dream_os.services.prompt_router_service import PromptRouterService
from dream_os.services.task_nexus import add_task
from dream_os.adapters.base_adapter import AdapterRegistry


def main():
    # Add dummy adapter registration for smoke test
    class DummyAdapter:
        def __init__(self, *args, **kwargs):
            pass
        def execute(self, payload):
            return "dummy"

    # Override adapters to use DummyAdapter in smoke test
    AdapterRegistry.register("openai", DummyAdapter)
    AdapterRegistry.register("cursor", DummyAdapter)
    AdapterRegistry.register("discord", DummyAdapter)

    # Instantiate agents for each role
    agents = [
        CrewAgent(name="StrategistAgent", role_name="Strategist"),
        CrewAgent(name="ExecutorAgent", role_name="Executor"),
        CrewAgent(name="OutreachAgent", role_name="Outreach"),
    ]

    # Start the PromptRouterService in a daemon thread
    router = PromptRouterService(agents)
    router.start()

    # Inject sample tasks
    sample_tasks = [
        ("plan", "Sample plan task"),
        ("code", "Sample code task"),
        ("social", "Sample social task"),
    ]
    for t_type, content in sample_tasks:
        task_id = add_task(t_type, content)
        print(f"Injected task {task_id} (type={t_type})")

    # Determine nexus file path
    nexus_file = os.getenv("NEXUS_FILE", "runtime/task_nexus.json")

    # Wait until at least 3 log entries exist
    start_time = time.time()
    logs = []
    while time.time() - start_time < 60:
        if os.path.exists(nexus_file):
            with open(nexus_file, encoding="utf-8") as f:
                data = json.load(f)
            logs = data.get("log", [])
            if len(logs) >= len(sample_tasks):
                break
        time.sleep(1)

    if len(logs) < len(sample_tasks):
        print(f"Timeout waiting for {len(sample_tasks)} tasks to complete. Only got {len(logs)}.")
        return 1

    # Print summary timings
    print("\n=== E2E Smoke Summary ===")
    for entry in logs[-len(sample_tasks):]:
        agent_name = entry.get("agent")
        adapter = entry.get("adapter")
        latency = entry.get("latency_ms")
        status = entry.get("status")
        print(f"{agent_name} used {adapter} => {status} in {latency}ms")

    return 0


if __name__ == '__main__':
    exit(main()) 