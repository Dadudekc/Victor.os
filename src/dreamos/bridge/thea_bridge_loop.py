import json
import time
from datetime import datetime
from pathlib import Path

import pyautogui

from logins.chatgpt_scraper import ChatGPTScraper

MAILBOX_ROOT = Path("agent_tools/mailbox")
THEA_INBOX = MAILBOX_ROOT / "thea" / "inbox.json"
COORDS_FILE = Path("runtime/config/cursor_agent_coords.json")


def load_json(path: Path):
    if not path.exists():
        return []
    with open(path, "r") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_input_coords(agent_id: str):
    with open(COORDS_FILE, "r") as f:
        coords = json.load(f)
    return coords.get(agent_id, {}).get("input_box")


def send_to_chatgpt(prompt: str) -> str:
    scraper = ChatGPTScraper()
    if scraper.send_prompt(prompt):
        return scraper.wait_for_stable_response()
    return ""


def type_reply(agent_id: str, text: str) -> None:
    xy = get_input_coords(agent_id)
    if not xy:
        raise ValueError(f"Input box coordinates not found for {agent_id}")
    pyautogui.click(xy["x"], xy["y"])
    pyautogui.typewrite(text, interval=0.01)


def process_messages():
    while True:
        messages = load_json(THEA_INBOX)
        if not messages:
            time.sleep(1)
            continue

        message = messages.pop(0)
        save_json(THEA_INBOX, messages)

        response = send_to_chatgpt(message.get("content", ""))
        reply = {
            "sender": "thea",
            "type": "bridge_reply",
            "content": response,
            "timestamp": datetime.utcnow().isoformat(),
        }

        target_agent = "agent-2"
        target_inbox = MAILBOX_ROOT / target_agent / "inbox.json"
        agent_messages = load_json(target_inbox)
        agent_messages.append(reply)
        save_json(target_inbox, agent_messages)
        type_reply("Agent-2", response)


if __name__ == "__main__":
    process_messages()
