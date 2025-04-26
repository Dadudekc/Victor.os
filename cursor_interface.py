# cursor_interface.py
"""
Interface for sending prompts to Cursor and fetching responses.
Supports GUI (PyAutoGUI) and CLI modes based on config.USE_GUI.
"""
from typing import Dict, Any
import subprocess
import time
import pyautogui
from dreamos.config import Config
from dreamos.agent_utils import click_agent_spot as click_spot, paste_from_clipboard


def send_prompt(context: Dict[str, Any]) -> None:
    """Send a prompt to Cursor via GUI or CLI."""
    prompt = context.get("prompt", "")
    if Config.USE_GUI:
        # GUI mode: click input spot, type, send
        click_spot(Config.AGENT_ID, "text_input")
        pyautogui.write(prompt)
        pyautogui.hotkey("ctrl", "enter")
        click_spot(Config.AGENT_ID, "send_button")
    else:
        # CLI mode: use Cursor CLI; swallow errors if CLI not installed or fails
        try:
            subprocess.run([Config.CURSOR_CLI, "tasks", "run", prompt], check=True)
        except Exception as e:
            # In headless/test env, cursor CLI may not exist
            print(f"Warning: send_prompt CLI invocation failed: {e}")


def fetch_reply(final: bool = False) -> str:
    """Fetch the Cursor response, either final or draft."""
    if not Config.USE_GUI:
        # CLI mode: TODO implement reading from CLI output or filesystem
        return ""
    # GUI mode: click response area to focus and copy
    click_spot(Config.AGENT_ID, "response_area")
    time.sleep(Config.CLIPBOARD_WAIT)
    return paste_from_clipboard() 
