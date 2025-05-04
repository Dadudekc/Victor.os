#!/usr/bin/env python3
"""
scripts/testing/load_generator_recovery_test.py

Dream.OS Load Generator: RecoveryCoordinatorAgent Stress Test
Injects a wave of intentionally fail-prone tasks to trigger RecoveryCoordinatorAgent's retry and escalation logic.

MOVED FROM: src/dreamos/tools/scripts/ by Agent 5 (2025-04-28)
"""  # noqa: E501

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

# --- Configuration ---

TARGET_AGENT_ID = "agent_02"  # Target worker agent expected to fail tasks
# Resolve BUS_FILE path relative to the script's new location
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]  # Assumes script is in root/scripts/testing
BUS_FILE_TEMPLATE = PROJECT_ROOT / "runtime" / "bus" / "agent.{agent_id}.command.json"
# BUS_FILE = Path("runtime/bus/agent.{agent_id}.command.json").resolve() # Original less robust path  # noqa: E501
NUM_TASKS = 10  # Number of tasks to inject
INJECTION_INTERVAL_SECONDS = 1.0  # Delay between task injections

# --- Task Template ---


def create_fail_test_task() -> dict:
    """Create a task intentionally designed to fail."""
    now = datetime.now(timezone.utc).isoformat()
    task_id = str(uuid.uuid4())
    return {
        "type": "task_message",
        "task_id": task_id,
        "agent_id": TARGET_AGENT_ID,
        "command": "fail_test_task",
        "args": {},
        "status": "pending",
        "priority": "normal",
        "created_at": now,
        "updated_at": now,
        "retry_count": 0,
    }


# --- Bus Write Utility ---


async def inject_task(task: dict):
    """Inject a task into the bus by writing to a file.

    NOTE: This simulates message injection by writing to a specific file
          that a file-based bus monitor might pick up. This is NOT direct
          AgentBus interaction.
    """
    payload = {
        "type": "agent.command",  # Matches format expected by BaseAgent._handle_command
        "correlation_id": str(uuid.uuid4()),  # Add correlation ID for tracking
        "sender_id": "LoadGeneratorTestScript",
        "data": task,
    }
    # Construct the specific bus file path for the target agent
    target_bus_path = Path(
        str(BUS_FILE_TEMPLATE).replace("{agent_id}", TARGET_AGENT_ID)
    )

    print(
        f"[*] Attempting to inject task {task['task_id']} to bus file: {target_bus_path.resolve()}"  # noqa: E501
    )

    try:
        # Ensure the directory exists before writing
        target_bus_path.parent.mkdir(parents=True, exist_ok=True)

        with open(target_bus_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(
            f"[+] Injected task {task['task_id']} -> {TARGET_AGENT_ID} (File: {target_bus_path.name})"  # noqa: E501
        )
    except Exception as e:
        print(f"[!] Failed to inject task {task['task_id']} to {target_bus_path}")
        print("    Error:", e)
        # print("    Traceback:", traceback.format_exc()) # Reduce verbosity


# --- Main Execution ---


async def main():
    print("--- Starting Load Generator Recovery Test --- ")
    for i in range(NUM_TASKS):
        print(f"\n--- Generating Task {i + 1}/{NUM_TASKS} ---")
        task = create_fail_test_task()
        await inject_task(task)
        if i < NUM_TASKS - 1:
            print(f"--- Waiting {INJECTION_INTERVAL_SECONDS}s before next task --- ")
            await asyncio.sleep(INJECTION_INTERVAL_SECONDS)
    print("\n--- Load Generator Finished --- ")


if __name__ == "__main__":
    asyncio.run(main())
