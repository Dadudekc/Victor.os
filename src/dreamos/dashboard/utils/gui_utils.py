import json
import pyautogui
import os
from typing import Dict, Tuple, Optional

COORDS_PATH = "runtime/config/agent_coords.json"

def _load_coords() -> Dict[str, Dict[str, int]]:
    if os.path.exists(COORDS_PATH):
        with open(COORDS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_coords(coords: Dict[str, Dict[str, int]]):
    os.makedirs(os.path.dirname(COORDS_PATH), exist_ok=True)
    with open(COORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(coords, f, indent=2)

def save_agent_spot(agent_id: str, spot_name: str, position: Tuple[int, int]):
    """Save a coordinate spot (e.g. text_input, send_button) for an agent."""
    coords = _load_coords()
    # ensure nested mapping
    if agent_id not in coords or not isinstance(coords[agent_id], dict) or "x" in coords[agent_id]:
        coords[agent_id] = {}
    coords[agent_id][spot_name] = {"x": position[0], "y": position[1]}
    _save_coords(coords)

def get_agent_spot(agent_id: str, spot_name: str) -> Optional[Tuple[int, int]]:
    """Retrieve saved coordinate for agent and spot name."""
    coords = _load_coords()
    agent_data = coords.get(agent_id, {})
    spot = agent_data.get(spot_name)
    if spot and "x" in spot and "y" in spot:
        return spot["x"], spot["y"]
    return None

def click_agent_spot(agent_id: str, spot_name: str, duration: float = 0.1):
    """Move to and click the saved spot for a given agent."""
    pos = get_agent_spot(agent_id, spot_name)
    if pos is None:
        raise ValueError(f"No saved coordinates for agent '{agent_id}' spot '{spot_name}'.")
    pyautogui.moveTo(pos[0], pos[1], duration=duration)
    pyautogui.click()

def screenshot_spot(agent_id: str, spot_name: str, width: int, height: int):
    """Take a screenshot of a region around the saved spot."""
    pos = get_agent_spot(agent_id, spot_name)
    if pos is None:
        raise ValueError(f"No saved coordinates for agent '{agent_id}' spot '{spot_name}'.")
    x, y = pos
    return pyautogui.screenshot(region=(x, y, width, height))

import pyperclip
def copy_to_clipboard(text: str) -> None:
    """Copy text to system clipboard."""
    pyperclip.copy(text)

def paste_from_clipboard() -> str:
    """Retrieve text from system clipboard."""
    return pyperclip.paste() 
