#!/usr/bin/env python3
"""
Demo for LocalBlobChannel:
- Push a task
- Worker thread pulls task, processes it, and pushes a result
- Main thread pulls and displays the result
"""
import os
import sys
# Ensure workspace root is in sys.path for importing dream_mode package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
import time
import threading
import json
from dream_mode.local_blob_channel import LocalBlobChannel


def worker(channel):
    while True:
        tasks = channel.pull_tasks()
        for task in tasks:
            print(f"[Worker] Received task: {task}")
            # Simulate processing by echoing back with timestamp
            result = {
                "id": task.get("id"),
                "content": f"Processed {task.get('payload', {}).get('module_path')}",
                "timestamp_processed": time.time()
            }
            channel.push_result(result)
            print(f"[Worker] Pushed result: {result}")
        time.sleep(1)


def main():
    try:
        # Determine workspace root and set absolute base directory
        script_dir = os.path.dirname(__file__)
        workspace_root = os.path.abspath(os.path.join(script_dir, os.pardir))
        base_dir = os.path.join(workspace_root, "runtime", "local_blob")
        channel = LocalBlobChannel(base_dir=base_dir)

        # 1. Push a demo task
        task = {
            "id": "demo-1",
            "task_type": "generate_unit_tests",
            "payload": {"module_path": "cli.py", "description": "Demo test generation"},
            "timestamp_created": time.time()
        }
        print(f"[Controller] Pushing task: {task}")
        channel.push_task(task)

        # 2. Start worker thread
        print("[Controller] Starting worker thread...")
        thr = threading.Thread(target=worker, args=(channel,), daemon=True)
        thr.start()

        # 3. Pull results in main thread after delay
        time.sleep(3)
        results = channel.pull_results()
        for res in results:
            print(f"[Controller] Got result: {res}")

        print("Demo complete.")
    except Exception as e:
        import traceback
        print("Demo encountered an error:")
        traceback.print_exc()


if __name__ == '__main__':
    main() 
