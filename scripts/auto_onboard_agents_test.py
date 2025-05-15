"""
Auto-Onboard Agents • Dream.OS (Test Mode)
Simulates the onboarding process without actually injecting prompts.
"""

import json
import time
import pathlib
from datetime import datetime
from typing import Dict, Optional

# Configuration constants - using test paths
COORDS_FILE = pathlib.Path("runtime/test_onboarding/config/cursor_agent_coords.json")
MAILBOX_DIR = pathlib.Path("runtime/test_onboarding/agent_mailboxes")
OUTBOX_DIR = pathlib.Path("runtime/test_onboarding/bridge_outbox")
RESPONSE_WAIT_SEC = 1  # Reduced for testing
RESPONSE_TIMEOUT_SEC = 2  # Reduced for testing

def validate_paths() -> bool:
    """Validate that required paths and files exist."""
    if not COORDS_FILE.exists():
        print(f"❌ Missing coordinates file: {COORDS_FILE}")
        return False
    if not MAILBOX_DIR.exists():
        print(f"❌ Missing mailbox directory: {MAILBOX_DIR}")
        return False
    return True

def load_coords(agent_id: int) -> Optional[Dict]:
    """Load coordinates for an agent with error handling."""
    try:
        coords = json.loads(COORDS_FILE.read_text())
        agent_key = f"Agent-{agent_id}"
        if agent_key not in coords:
            print(f"❌ No coordinates found for {agent_key}")
            return None
        return coords[agent_key]
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in coordinates file: {COORDS_FILE}")
        return None
    except Exception as e:
        print(f"❌ Error loading coordinates: {e}")
        return None

def load_inbox_prompt(agent_id: int) -> Optional[str]:
    """Load and mark the first unprocessed message from agent's inbox."""
    try:
        inbox_file = MAILBOX_DIR / f"Agent-{agent_id}" / "inbox.json"
        if not inbox_file.exists():
            print(f"❌ Missing inbox file: {inbox_file}")
            return None

        inbox = json.loads(inbox_file.read_text())
        if not isinstance(inbox, list):
            print(f"❌ Invalid inbox format for Agent-{agent_id}: expected list")
            return None

        # Find first unprocessed message
        for msg in inbox:
            if not msg.get("processed", False):
                msg["processed"] = True
                inbox_file.write_text(json.dumps(inbox, indent=2))
                return msg.get("content")

        print(f"⚠️ Agent-{agent_id} inbox is empty or already processed.")
        return None

    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in inbox file: {inbox_file}")
        return None
    except Exception as e:
        print(f"❌ Error loading inbox for Agent-{agent_id}: {e}")
        return None

def save_response(agent_id: int, response: str) -> bool:
    """Save agent's response to outbox with error handling."""
    try:
        OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.utcnow().isoformat()
        out_file = OUTBOX_DIR / f"Agent-{agent_id}.json"
        payload = {
            "timestamp": stamp,
            "response": response,
            "agent_id": f"Agent-{agent_id}",
            "test_mode": True
        }
        out_file.write_text(json.dumps(payload, indent=2))
        return True
    except Exception as e:
        print(f"❌ Error saving response for Agent-{agent_id}: {e}")
        return False

def onboard_agent(agent_id: int) -> bool:
    """Simulate onboarding a single agent."""
    print(f"\n🔄 Simulating onboarding for Agent-{agent_id}...")

    # Load coordinates
    coords = load_coords(agent_id)
    if not coords:
        return False

    # Load prompt
    prompt = load_inbox_prompt(agent_id)
    if not prompt:
        return False

    try:
        # Simulate prompt injection
        print(f"📤 Would inject prompt to Agent-{agent_id} at coordinates {coords['input_box']}")
        print(f"📝 Prompt content: {prompt[:50]}...")

        # Simulate waiting for response
        print("⏳ Waiting for response...")
        time.sleep(RESPONSE_WAIT_SEC)

        # Simulate response
        simulated_response = f"✅ Agent-{agent_id} initialized and ready. Starting UNIVERSAL_AGENT_LOOP v6.1"
        
        if save_response(agent_id, simulated_response):
            print(f"Agent-{agent_id} ✅ simulated onboarding successful.")
            return True
        return False

    except Exception as e:
        print(f"Agent-{agent_id} ❌ error during simulated onboarding: {e}")
        return False

def main() -> int:
    """Main entry point with error handling."""
    print("🚀 Dream.OS Agent Auto-Onboarding (TEST MODE)")
    
    if not validate_paths():
        return 1

    success_count = 0
    for agent_id in range(1, 3):  # Testing with just 2 agents
        if onboard_agent(agent_id):
            success_count += 1

    total = 2  # Testing with 2 agents
    print(f"\n📊 Summary: {success_count}/{total} agents simulated successfully")
    return 0 if success_count == total else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Simulation interrupted by user")
        exit(130)
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        exit(1) 