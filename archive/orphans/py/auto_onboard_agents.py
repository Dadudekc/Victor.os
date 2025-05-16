"""
Auto-Onboard Agents • Dream.OS
Injects the onboarding prompt into every Cursor-based agent,
captures the first reply, and logs it.

Features:
- Direct cursor control using PyAutoGUI
- Realistic agent response timing
- Test mode for simulation without GUI interaction
- Production mode for actual agent interaction

Usage:
    python scripts/auto_onboard_agents.py [--test] [--agents N M...]
"""

import argparse
import json
import pathlib
import time
from datetime import datetime
from typing import Dict, Optional

import pyautogui
import pyperclip

# Configuration constants
TEST_MODE = False  # Can be overridden by --test flag

# Timing configuration (in seconds)
TIMING = {
    "test": {"response_wait": 1, "timeout": 2, "click_delay": 0.1},
    "prod": {
        "response_wait": 300,  # 5 minutes between checks
        "timeout": 900,  # 15 minutes total timeout
        "click_delay": 0.5,  # Delay between clicks for stability
    },
}


def get_paths(test_mode: bool = False) -> Dict[str, pathlib.Path]:
    """Get appropriate paths based on mode."""
    base = "runtime/test_onboarding" if test_mode else "runtime"
    return {
        "coords": pathlib.Path(f"{base}/config/cursor_agent_coords.json"),
        "mailbox": pathlib.Path(
            f"{base}/{'agent_mailboxes' if test_mode else 'agent_comms/agent_mailboxes'}"
        ),
        "outbox": pathlib.Path(f"{base}/bridge_outbox"),
    }


def validate_paths(paths: Dict[str, pathlib.Path]) -> bool:
    """Validate that required paths and files exist."""
    if not paths["coords"].exists():
        print(f"❌ Missing coordinates file: {paths['coords']}")
        return False
    if not paths["mailbox"].exists():
        print(f"❌ Missing mailbox directory: {paths['mailbox']}")
        return False
    return True


def safe_click(x: int, y: int, delay: float = 0.5):
    """Safely move to and click at coordinates with delay."""
    pyautogui.moveTo(x, y, duration=0.5)  # Smooth movement
    time.sleep(delay)  # Wait for UI
    pyautogui.click()
    time.sleep(delay)  # Wait after click


def inject_prompt(
    coords: Dict[str, Dict[int, int]],
    agent_id: int,
    prompt: str,
    test_mode: bool = False,
) -> bool:
    """Inject prompt using PyAutoGUI with proper coordinates."""
    try:
        if test_mode:
            print(f"📤 Would inject prompt to Agent-{agent_id} at coordinates {coords}")
            return True

        timing = TIMING["test" if test_mode else "prod"]

        # Copy prompt to clipboard
        pyperclip.copy(prompt)

        # Click input box
        input_coords = coords["input_box"]
        safe_click(input_coords["x"], input_coords["y"], timing["click_delay"])

        # Paste prompt
        pyautogui.hotkey("ctrl", "v")
        time.sleep(timing["click_delay"])

        # Press Enter to send
        pyautogui.press("enter")
        time.sleep(timing["click_delay"])

        return True
    except Exception as e:
        print(f"❌ Error injecting prompt: {e}")
        return False


def load_coords(paths: Dict[str, pathlib.Path], agent_id: int) -> Optional[Dict]:
    """Load coordinates for an agent with error handling."""
    try:
        coords = json.loads(paths["coords"].read_text())
        agent_key = f"Agent-{agent_id}"
        if agent_key not in coords:
            print(f"❌ No coordinates found for {agent_key}")
            return None
        return coords[agent_key]
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in coordinates file: {paths['coords']}")
        return None
    except Exception as e:
        print(f"❌ Error loading coordinates: {e}")
        return None


def load_inbox_prompt(paths: Dict[str, pathlib.Path], agent_id: int) -> Optional[str]:
    """Load and mark the first unprocessed message from agent's inbox."""
    try:
        inbox_file = paths["mailbox"] / f"Agent-{agent_id}" / "inbox.json"
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


def save_response(
    paths: Dict[str, pathlib.Path],
    agent_id: int,
    response: str,
    test_mode: bool = False,
) -> bool:
    """Save agent's response to outbox with error handling."""
    try:
        paths["outbox"].mkdir(parents=True, exist_ok=True)
        stamp = datetime.utcnow().isoformat()
        out_file = paths["outbox"] / f"Agent-{agent_id}.json"
        payload = {
            "timestamp": stamp,
            "response": response,
            "agent_id": f"Agent-{agent_id}",
        }
        if test_mode:
            payload["test_mode"] = True
        out_file.write_text(json.dumps(payload, indent=2))
        return True
    except Exception as e:
        print(f"❌ Error saving response for Agent-{agent_id}: {e}")
        return False


def onboard_agent(
    paths: Dict[str, pathlib.Path], agent_id: int, test_mode: bool = False
) -> bool:
    """Onboard or simulate onboarding for a single agent."""
    print(
        f"\n{'🔄 Simulating' if test_mode else '🚀 Starting'} onboarding for Agent-{agent_id}..."
    )

    # Load coordinates
    coords = load_coords(paths, agent_id)
    if not coords:
        return False

    # Load prompt
    prompt = load_inbox_prompt(paths, agent_id)
    if not prompt:
        return False

    try:
        timing = TIMING["test" if test_mode else "prod"]

        # Inject prompt using PyAutoGUI
        if not inject_prompt(coords, agent_id, prompt, test_mode):
            return False

        if test_mode:
            # Simulate response
            time.sleep(timing["response_wait"])
            response = f"✅ Agent-{agent_id} initialized and ready. Starting UNIVERSAL_AGENT_LOOP v6.1"
        else:
            # Wait for and capture real response
            print(f"⏳ Waiting for response (timeout: {timing['timeout']}s)...")
            t0 = time.time()
            response = None

            while time.time() - t0 < timing["timeout"]:
                # Click response area
                response_coords = coords.get("response_box", coords["input_box"])
                safe_click(
                    response_coords["x"], response_coords["y"], timing["click_delay"]
                )

                # Try to get response
                pyautogui.hotkey("ctrl", "a")  # Select all
                pyautogui.hotkey("ctrl", "c")  # Copy
                time.sleep(timing["click_delay"])

                response = pyperclip.paste()
                if response and response.strip():
                    break

                print("⏳ No response yet, waiting...")
                time.sleep(timing["response_wait"])

            if not response:
                print(
                    f"Agent-{agent_id} ⚠️ no reply within {timing['timeout']}s timeout."
                )
                return False

        # Save response (both real and simulated)
        if save_response(paths, agent_id, response, test_mode):
            print(
                f"Agent-{agent_id} ✅ {'simulated ' if test_mode else ''}onboarding successful."
            )
            return True
        return False

    except Exception as e:
        print(
            f"Agent-{agent_id} ❌ error during {'simulated ' if test_mode else ''}onboarding: {e}"
        )
        return False


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Dream.OS Agent Auto-Onboarding")
    parser.add_argument(
        "--test", action="store_true", help="Run in test mode without GUI interaction"
    )
    parser.add_argument(
        "--agents",
        type=int,
        nargs="+",
        help="Specific agent IDs to onboard (e.g. 1 2 3)",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point with error handling."""
    args = parse_args()
    global TEST_MODE
    TEST_MODE = args.test

    print(f"🚀 Dream.OS Agent Auto-Onboarding {'(TEST MODE)' if TEST_MODE else ''}")

    paths = get_paths(TEST_MODE)
    if not validate_paths(paths):
        return 1

    # Determine which agents to process
    agent_ids = args.agents if args.agents else range(1, 3 if TEST_MODE else 9)
    total = len(list(agent_ids))

    success_count = 0
    for agent_id in agent_ids:
        if onboard_agent(paths, agent_id, TEST_MODE):
            success_count += 1

    print(
        f"\n📊 Summary: {success_count}/{total} agents {'simulated' if TEST_MODE else 'onboarded'} successfully"
    )
    return 0 if success_count == total else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Process interrupted by user")
        exit(130)
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        exit(1)
