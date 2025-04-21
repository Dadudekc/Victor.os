#!/usr/bin/env python3
"""
run_dream_os.py

One-click entrypoint: launches the ChatGPT WebAgent and SwarmController in local-only mode.
"""
import os
import subprocess
import sys

# Ensure local blob channel is used
os.environ["USE_LOCAL_BLOB"] = "1"

# Paths for module launch
WEB_AGENT_CMD = [sys.executable, "-m", "dream_mode.agents.chatgpt_web_agent"]
SWARM_CMD = [sys.executable, "-m", "dream_mode.swarm_controller"]

def main():
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