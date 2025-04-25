import json
import pyautogui
import os
from typing import Dict, Tuple, Optional

COORDS_PATH = "_agent_coordination/config/agent_coords.json"

def _load_coords() -> Dict[str, Dict[str, int]]:
    if os.path.exists(COORDS_PATH):
        with open(COORDS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_coords(coords: Dict[str, Dict[str, int]]):
    os.makedirs(os.path.dirname(COORDS_PATH), exist_ok=True)
    with open(COORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(coords, f, indent=2)

def save_agent_spot(agent_id: str, position: Tuple[int, int]):
    coords = _load_coords()
    coords[agent_id] = {"x": position[0], "y": position[1]}
    _save_coords(coords)

def get_agent_spot(agent_id: str) -> Optional[Tuple[int, int]]:
    coords = _load_coords()
    pos = coords.get(agent_id)
    if pos:
        return pos["x"], pos["y"]
    return None

def click_agent_spot(agent_id: str, duration: float = 0.1):
    pos = get_agent_spot(agent_id)
    if pos is None:
        raise ValueError(f"No saved coordinates for agent '{agent_id}'.")
    pyautogui.moveTo(*pos, duration=duration)
    pyautogui.click() 