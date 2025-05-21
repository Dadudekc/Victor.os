import pyautogui
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CursorController:
    def __init__(self):
        # Set up PyAutoGUI settings
        pyautogui.FAILSAFE = True  # Move mouse to corner to abort
        pyautogui.PAUSE = 0.1  # Add small delay between actions
        
    def move_to(self, x: int, y: int):
        """Move cursor to specified coordinates"""
        try:
            pyautogui.moveTo(x, y)
            logger.debug(f"Moved cursor to ({x}, {y})")
        except Exception as e:
            logger.error(f"Error moving cursor: {e}")
            raise
            
    def click(self):
        """Perform a mouse click at current position"""
        try:
            pyautogui.click()
            logger.debug("Performed mouse click")
        except Exception as e:
            logger.error(f"Error performing click: {e}")
            raise
            
    def type_text(self, text: str):
        """Type text at current position"""
        try:
            pyautogui.write(text)
            logger.debug(f"Typed text: {text[:30]}...")
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            raise
            
    def press_enter(self):
        """Press Enter key"""
        try:
            pyautogui.press('enter')
            logger.debug("Pressed Enter key")
        except Exception as e:
            logger.error(f"Error pressing Enter: {e}")
            raise
            
    def press_ctrl_n(self):
        """Press Ctrl+N combination"""
        try:
            pyautogui.hotkey('ctrl', 'n')
            logger.debug("Pressed Ctrl+N")
        except Exception as e:
            logger.error(f"Error pressing Ctrl+N: {e}")
            raise
            
    def press_ctrl_v(self):
        """Press Ctrl+V combination"""
        try:
            pyautogui.hotkey('ctrl', 'v')
            logger.debug("Pressed Ctrl+V")
        except Exception as e:
            logger.error(f"Error pressing Ctrl+V: {e}")
            raise
            
    def press_ctrl_a(self):
        """Press Ctrl+A combination"""
        try:
            pyautogui.hotkey('ctrl', 'a')
            logger.debug("Pressed Ctrl+A")
        except Exception as e:
            logger.error(f"Error pressing Ctrl+A: {e}")
            raise 