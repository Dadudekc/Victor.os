# config.py
from typing import Tuple

class Config:
    """Central configuration for Dream.OS Auto-Fix Loop"""
    AGENT_ID: str = "agent_001"
    COPY_REGION: Tuple[int, int] = (500, 300)    # width x height for screenshot
    CLIPBOARD_WAIT: float = 0.3                  # seconds to wait for clipboard update
    CHATGPT_URL: str = "http://127.0.0.1:8000/patch"
    CURSOR_CLI: str = "cursor"
    USE_GUI: bool = False                        # toggle headless CLI vs GUI automation
    # Named spots: text_input, send_button, response_area, scroll_up, status_indicator 
