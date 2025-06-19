import json
import time
from datetime import datetime
from pathlib import Path

import pyautogui
import pyperclip

COORDS_FILE = Path("runtime/config/cursor_agent_coords.json")
MAILBOX_FILE = Path("agent_tools/mailbox/thea/inbox.json")
AGENT_ID = "agent-2"


def load_coords() -> dict:
    with open(COORDS_FILE, "r") as f:
        return json.load(f)


def append_message(message: dict) -> None:
    MAILBOX_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.load(MAILBOX_FILE.open())
    except FileNotFoundError:
        data = []
    data.append(message)
    with open(MAILBOX_FILE, "w") as f:
        json.dump(data, f, indent=2)


def main() -> None:
    coords = load_coords()
    copy_xy = coords.get("Agent-2", {}).get("copy_button")
    if not copy_xy:
        raise ValueError("Copy button coordinates for Agent-2 not found")

    pyautogui.click(copy_xy["x"], copy_xy["y"])
    time.sleep(0.5)
    text = pyperclip.paste()

    message = {
        "sender": AGENT_ID,
        "type": "bridge_request",
        "content": text,
        "timestamp": datetime.utcnow().isoformat(),
    }
    append_message(message)


if __name__ == "__main__":
    main()
