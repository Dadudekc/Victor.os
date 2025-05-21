"""
Agent Messenger Tool for Dream.OS

This tool enables direct agent-to-agent messaging using PyAutoGUI to interact with
the Cursor interface. It uses pre-configured coordinates for each agent's input box
and copy button.
"""

import json
import time
import logging
from pathlib import Path
import pyautogui
import pyperclip

logger = logging.getLogger(__name__)

class AgentMessenger:
    def __init__(self):
        self.coords = self._load_coordinates()
        
    def _load_coordinates(self) -> dict:
        """Load agent coordinates from the config file."""
        coords_path = Path("src/runtime/config/cursor_agent_coords.json")
        if not coords_path.exists():
            raise FileNotFoundError(f"Coordinates file not found at {coords_path}")
            
        with coords_path.open("r") as f:
            return json.load(f)
            
    def send_message(self, target_agent: str, message: str, dry_run: bool = False) -> bool:
        """
        Send a message directly to another agent's input box.
        
        Args:
            target_agent: The ID of the target agent (e.g., "Agent-1")
            message: The message to send
            dry_run: If True, only simulate the action without actually sending
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if target_agent not in self.coords:
            logger.error(f"❌ No coordinates found for {target_agent}")
            return False
            
        try:
            input_box = self.coords[target_agent]["input_box"]
            
            if not dry_run:
                # Click input box
                pyautogui.click(input_box["x"], input_box["y"])
                time.sleep(0.5)
                
                # Accept any pending changes
                pyautogui.hotkey("ctrl", "enter")
                time.sleep(1.0)
                
                # Send message
                pyperclip.copy(message)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.5)
                pyautogui.press("enter")
                logger.info(f"✅ Sent message to {target_agent}")
                return True
            else:
                logger.info(f"[DRY-RUN] Would send message to {target_agent}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error sending message to {target_agent}: {e}")
            return False
            
    def get_available_agents(self) -> list:
        """Get list of agents with configured coordinates."""
        return list(self.coords.keys())
        
    def validate_coordinates(self, agent_id: str) -> bool:
        """Validate that coordinates exist for an agent."""
        return agent_id in self.coords 