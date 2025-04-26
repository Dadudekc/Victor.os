#!/usr/bin/env python3
"""
run_dream_os.py

One-click entrypoint: launches the ChatGPT WebAgent and SwarmController in local-only mode.
"""
import os
import subprocess
import sys
import threading
from dream_mode.agents.cursor_worker import run as cursor_worker_run
from dream_mode.utils.channel_loader import get_blob_channel

# Ensure local blob channel is used
os.environ["USE_LOCAL_BLOB"] = "1"

# Paths for module launch
WEB_AGENT_CMD = [sys.executable, "-m", "dream_mode.agents.chatgpt_web_agent"]
SWARM_CMD = [sys.executable, "-m", "dream_mode.swarm_controller"]

# Simulation mode: launch fake Cursor workers in background threads
def simulate_cursor_workers(n=5):
    for i in range(n):
        worker_id = f"worker-{i+1}"
        threading.Thread(target=cursor_worker_run, args=(worker_id,), daemon=True).start()
    print(f"🧪 Launched {n} simulated Cursor workers.")

def main():
    # If simulate flag passed, launch fake Cursor workers
    if "--simulate" in sys.argv:
        simulate_cursor_workers(5)
        # Seed codegen prompt tasks into the channel
        channel = get_blob_channel()
        prompts_dir = os.path.join(os.getcwd(), "_agent_coordination", "user_prompts")
        if os.path.isdir(prompts_dir):
            for fname in os.listdir(prompts_dir):
                if fname.endswith(".txt"):
                    task_id = os.path.splitext(fname)[0]
                    with open(os.path.join(prompts_dir, fname), 'r', encoding='utf-8') as f:
                        content = f.read()
                    channel.push_task({"id": task_id, "payload": content})
                    print(f"📤 Seeded prompt task: {task_id}")
    print("🌐 Starting ChatGPT WebAgent in local mode...")
    p1 = subprocess.Popen(WEB_AGENT_CMD)
    print(f"  PID {p1.pid}: WebAgent started.")

    print("🤖 Starting SwarmController in local mode...")
    p2 = subprocess.Popen(SWARM_CMD)
    print(f"  PID {p2.pid}: SwarmController started.")

    print("Press Ctrl+C to terminate both processes.")
    try:
        p1.wait()
        p2.wait()
    except KeyboardInterrupt:
        print("\n🔒 Shutdown requested, terminating...")
        p1.terminate()
        p2.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main() 
