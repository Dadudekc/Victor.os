#!/usr/bin/env python
import logging
import argparse
import time
from dream_os.core.crew_agent_base import CrewAgent
from dream_os.services.prompt_router_service import PromptRouterService
from dream_os.services.task_nexus import import import import add_task

logging.basicConfig(level=logging.INFO)

def main():
    ap = argparse.ArgumentParser(description="Boot Thea core loop")
    ap.add_argument("--add", nargs=2, metavar=("TYPE", "CONTENT"), help="Inject a task then exit")
    args = ap.parse_args()

    # Fast-path: just queue a task
    if args.add:
        tid = add_task(*args.add)
        print(f"Queued task {tid}")
        return

    # Spawn crew
    agents = [
        CrewAgent("Thea", "Strategist"),
        CrewAgent("Cursor", "Executor"),
        CrewAgent("Aria", "Outreach")
    ]
    router = PromptRouterService(agents)
    router.start()

    print("✨ Dream.OS Thea Loop — press Ctrl-C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutdown requested")

if __name__ == "__main__":
    main() 
