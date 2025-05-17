#!/usr/bin/env python3
"""
Dream.OS Resume Loop Monitor
Checks for idle agents and injects resume prompt via resume_controller.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

from dreamos.tools.resume_controller import resume_agent

AGENT_STATE_FILE = Path("runtime/state/agent_last_activity.json")
MAILBOX_ROOT = Path("runtime/agent_comms/agent_mailboxes")
IDLE_THRESHOLD = timedelta(minutes=5)
RESUME_COOLDOWN = timedelta(minutes=5)
CHECK_INTERVAL = 60  # seconds

# Track when resume was last sent
agent_last_resumed = {}

# Helper function to check inbox activity (Option A)
def check_inbox_activity(agent_id: str, now: datetime) -> bool:
    inbox_file = MAILBOX_ROOT / agent_id / "inbox.json" # Assuming inbox.json per agent
    if inbox_file.exists():
        try:
            with open(inbox_file, "r") as f:
                messages = json.load(f)
            # Check if any message is a list and has unprocessed items or if it's a dict and unprocessed
            if isinstance(messages, list):
                if any(isinstance(m, dict) and not m.get("processed", True) for m in messages):
                    print(f"[{now.isoformat()}] Detected unprocessed messages in inbox for {agent_id}.")
                    return True
            elif isinstance(messages, dict): # Handle cases where inbox.json might be a single message object
                if not messages.get("processed", True):
                    print(f"[{now.isoformat()}] Detected unprocessed message object in inbox for {agent_id}.")
                    return True
        except json.JSONDecodeError:
            print(f"[{now.isoformat()}] Error decoding inbox.json for {agent_id}.")
            return False
        except Exception as e:
            print(f"[{now.isoformat()}] Error checking inbox for {agent_id}: {e}")
            return False
    return False

def load_agent_ids():
    MAILBOX_ROOT.mkdir(parents=True, exist_ok=True) # Ensure root exists
    return [p.name for p in MAILBOX_ROOT.glob("Agent-*") if p.is_dir()]

def load_agent_last_activity():
    AGENT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True) # Ensure state dir exists
    if AGENT_STATE_FILE.exists():
        try:
            with open(AGENT_STATE_FILE, "r") as f:
                raw = json.load(f)
            # Convert timestamps to datetime
            return {aid: datetime.fromisoformat(ts).replace(tzinfo=timezone.utc) if isinstance(ts, str) else datetime.now(timezone.utc) for aid, ts in raw.items()}
        except json.JSONDecodeError:
            print(f"Error decoding {AGENT_STATE_FILE}, returning empty state.")
            return {}
    return {}

def save_agent_last_activity(state):
    # Called by external updaters; included here for clarity
    AGENT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True) # Ensure state dir exists
    with open(AGENT_STATE_FILE, "w") as f:
        json.dump({aid: dt.isoformat() for aid, dt in state.items()}, f, indent=2)

async def check_and_resume():
    agent_last_activity = load_agent_last_activity()
    now = datetime.now(timezone.utc)
    active_agent_ids = load_agent_ids()
    activity_updated_this_cycle = False # Flag to track if we need to save

    if not active_agent_ids:
        print(f"[{now.isoformat()}] No agent mailboxes found in {MAILBOX_ROOT}. Monitor sleeping.")
        return

    for agent_id in active_agent_ids:
        # Check for inbox activity first (Option A integration)
        if check_inbox_activity(agent_id, now):
            agent_last_activity[agent_id] = now # Update last activity to now
            activity_updated_this_cycle = True
            # No need to print active here, check_inbox_activity does it or we fall through to normal active print
            # Continue to the next agent as this one is now considered active due to inbox
            # but we still want the generic "is active" log message below if it's not idle otherwise

        last_active = agent_last_activity.get(agent_id)
        # Ensure last_active is timezone-aware (UTC) if it exists
        if last_active and last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=timezone.utc)

        if not last_active or (now - last_active) > IDLE_THRESHOLD:
            last_resumed_ts = agent_last_resumed.get(agent_id)
            if not last_resumed_ts or (now - last_resumed_ts) > RESUME_COOLDOWN:
                print(f"[{now.isoformat()}] {agent_id} is idle, sending resume prompt.")
                try:
                    await resume_agent(agent_id)
                    agent_last_resumed[agent_id] = now

                    # ── Option B: record resume attempt in the agent's inbox.json ──
                    try:
                        inbox_path = MAILBOX_ROOT / agent_id / "inbox.json"
                        inbox_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        msgs = [] # Initialize msgs as an empty list
                        if inbox_path.exists():
                            try:
                                with open(inbox_path, "r") as f_inbox_read:
                                    loaded_json = json.load(f_inbox_read)
                                # Ensure msgs is a list, even if inbox.json contained a single dict or was malformed
                                if isinstance(loaded_json, list):
                                    msgs = loaded_json
                                elif isinstance(loaded_json, dict):
                                    msgs = [loaded_json] # Convert single dict to list
                                else:
                                    # If content is not a list or dict (e.g. null, string), start fresh
                                    print(f"[{now.isoformat()}] Content of {inbox_path} for {agent_id} is not a list/dict. Initializing fresh inbox list.")
                                    msgs = []
                            except json.JSONDecodeError:
                                print(f"[{now.isoformat()}] Error decoding {inbox_path} for {agent_id}. Initializing empty inbox list for appending.")
                                msgs = [] # Ensure msgs is an empty list on decode error
                        # If inbox_path doesn't exist, msgs remains []

                        resume_msg = {
                            "id": "resume-autonomy",
                            "type": "system",
                            "content": "🟢 Resume autonomy loop due to inactivity.",
                            "timestamp": now.isoformat(),
                            "processed": False,
                            "priority": 99
                        }
                        msgs.append(resume_msg)
                        
                        with open(inbox_path, "w") as f_inbox_write:
                            json.dump(msgs, f_inbox_write, indent=2)
                        print(f"[{now.isoformat()}] Logged resume message to {agent_id}'s inbox.")
                    except Exception as ex:
                        print(f"[{now.isoformat()}] Failed to write resume message to {agent_id} inbox: {ex}")
                    # End of Option B block

                except Exception as e: # This is for resume_agent errors
                    print(f"[{now.isoformat()}] Error resuming {agent_id}: {e}")
            else:
                print(f"[{now.isoformat()}] {agent_id} is idle but resume recently sent ({last_resumed_ts}); skipping.")
        else:
            print(f"[{now.isoformat()}] {agent_id} is active (last active: {last_active}).")

    # Save activity state if it was updated by inbox checks
    if activity_updated_this_cycle:
        save_agent_last_activity(agent_last_activity)
        print(f"[{now.isoformat()}] Agent activity state saved due to inbox updates.")

async def main():
    print(f"Autonomy Monitor started. Watching {MAILBOX_ROOT} for agents.")
    print(f"Idle threshold: {IDLE_THRESHOLD}, Cooldown: {RESUME_COOLDOWN}, Check interval: {CHECK_INTERVAL}s")
    print(f"Activity state file: {AGENT_STATE_FILE.resolve()}")
    while True:
        await check_and_resume()
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main()) 