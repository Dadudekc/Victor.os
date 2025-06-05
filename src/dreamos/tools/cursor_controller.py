try:
    import pyautogui  # type: ignore
except Exception:  # pragma: no cover - optional dependency may not be available
    pyautogui = None
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
        if pyautogui is not None:
            pyautogui.FAILSAFE = True  # Move mouse to corner to abort
            pyautogui.PAUSE = 0.1  # Add small delay between actions
        else:  # pragma: no cover - headless testing
            logger.warning("pyautogui not available; cursor actions will be skipped")
        
    def move_to(self, x: int, y: int):
        """Move cursor to specified coordinates"""
        try:
            if pyautogui:
                pyautogui.moveTo(x, y)
                logger.debug(f"Moved cursor to ({x}, {y})")
            else:
                logger.debug(f"TEST: move_to({x}, {y})")
        except Exception as e:
            logger.error(f"Error moving cursor: {e}")
            raise
            
    def click(self):
        """Perform a mouse click at current position"""
        try:
            if pyautogui:
                pyautogui.click()
                logger.debug("Performed mouse click")
            else:
                logger.debug("TEST: click")
        except Exception as e:
            logger.error(f"Error performing click: {e}")
            raise
            
    def type_text(self, text: str):
        """Type text at current position"""
        try:
            if pyautogui:
                pyautogui.write(text)
                logger.debug(f"Typed text: {text[:30]}...")
            else:
                logger.debug(f"TEST: type_text({text})")
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            raise
            
    def press_enter(self):
        """Press Enter key"""
        try:
            if pyautogui:
                pyautogui.press('enter')
                logger.debug("Pressed Enter key")
            else:
                logger.debug("TEST: press_enter")
        except Exception as e:
            logger.error(f"Error pressing Enter: {e}")
            raise
            
    def press_ctrl_n(self):
        """Press Ctrl+N combination"""
        try:
            if pyautogui:
                pyautogui.hotkey('ctrl', 'n')
                logger.debug("Pressed Ctrl+N")
            else:
                logger.debug("TEST: press_ctrl_n")
        except Exception as e:
            logger.error(f"Error pressing Ctrl+N: {e}")
            raise
            
    def press_ctrl_v(self):
        """Press Ctrl+V combination"""
        try:
            if pyautogui:
                pyautogui.hotkey('ctrl', 'v')
                logger.debug("Pressed Ctrl+V")
            else:
                logger.debug("TEST: press_ctrl_v")
        except Exception as e:
            logger.error(f"Error pressing Ctrl+V: {e}")
            raise
            
    def press_ctrl_a(self):
        """Press Ctrl+A combination"""
        try:
            if pyautogui:
                pyautogui.hotkey('ctrl', 'a')
                logger.debug("Pressed Ctrl+A")
            else:
                logger.debug("TEST: press_ctrl_a")
        except Exception as e:
            logger.error(f"Error pressing Ctrl+A: {e}")
            raise
