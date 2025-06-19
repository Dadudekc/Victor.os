import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional, Tuple

import pyautogui
from dreamos.core.metrics_logger import MetricsLogger

# Add src to Python path if not already present
workspace_root = Path(__file__).parent.parent.parent.parent
src_path = str(workspace_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from dreamos.automation.gui_interaction import CursorInjector
from dreamos.core.config import AppConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CursorInjector:
    """Handles injection of prompts into Cursor window using PyAutoGUI."""
    
    def __init__(self, agent_id: str, target_window_title: str, coordinates_file: str):
        self.agent_id = agent_id
        self.target_window_title = target_window_title
        self.coordinates_file = coordinates_file
        self.metrics = MetricsLogger(Path("."))
        
        # Load coordinates
        self.coordinates = self._load_coordinates()
        
        # Configure PyAutoGUI
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1  # Small delay between actions
    
    def _load_coordinates(self) -> dict:
        """Load window coordinates from file."""
        try:
            with open(self.coordinates_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading coordinates: {e}")
            return {}
    
    def _find_window(self) -> Optional[Tuple[int, int, int, int]]:
        """Find Cursor window and return its coordinates."""
        try:
            window = pyautogui.getWindowsWithTitle(self.target_window_title)
            if window:
                return window[0].left, window[0].top, window[0].width, window[0].height
            return None
        except Exception as e:
            logger.error(f"Error finding window: {e}")
            return None
    
    def inject_prompt(self, prompt_text: str, response_format: str = "text") -> bool:
        """Inject prompt into Cursor window.
        
        Args:
            prompt_text: Text to inject
            response_format: Expected response format
            
        Returns:
            bool: True if injection was successful
        """
        start_time = time.time()
        retry_count = 0
        max_retries = 3
        success = False
        error = None
        image_match_failed = False
        
        try:
            # Find window
            window = self._find_window()
            if not window:
                error = "Window not found"
                raise ValueError(error)
            
            # Click into window
            pyautogui.click(window[0] + 100, window[1] + 100)
            time.sleep(0.2)  # Wait for focus
            
            # Type prompt
            pyautogui.write(prompt_text)
            time.sleep(0.1)
            
            # Press enter
            pyautogui.press('enter')
            
            success = True
            
        except Exception as e:
            error = str(e)
            logger.error(f"Error injecting prompt: {e}")
            
            # Retry logic
            while retry_count < max_retries and not success:
                retry_count += 1
                try:
                    # Find window again
                    window = self._find_window()
                    if not window:
                        continue
                    
                    # Click into window
                    pyautogui.click(window[0] + 100, window[1] + 100)
                    time.sleep(0.2)
                    
                    # Type prompt
                    pyautogui.write(prompt_text)
                    time.sleep(0.1)
                    
                    # Press enter
                    pyautogui.press('enter')
                    
                    success = True
                    break
                    
                except Exception as retry_e:
                    error = str(retry_e)
                    logger.error(f"Retry {retry_count} failed: {retry_e}")
                    time.sleep(0.5)  # Wait before retry
        
        finally:
            # Log metrics
            self.metrics.log_injection_metrics(
                agent_id=self.agent_id,
                start_time=start_time,
                end_time=time.time(),
                success=success,
                retry_count=retry_count,
                image_match_failed=image_match_failed,
                error=error
            )
        
        return success

    def inject_declare_candidacy(self, agent_id: str, platform: str) -> bool:
        """Injects a DECLARE_CANDIDACY command structure via Cursor."""
        # Ensure platform statement is formatted nicely within the prompt
        # and escape any characters that might break the multi-line string structure if necessary.
        # For simplicity, basic string joining is used here.
        platform_lines = platform.split('\n')
        formatted_platform = "\n".join([f"    {line}" for line in platform_lines])

        prompt = f"""
DECLARE_CANDIDACY
agent_id: {agent_id}
platform_statement: >
{formatted_platform}
"""
        logger.info(f"Injecting DECLARE_CANDIDACY for {agent_id}")
        # Assuming response_format isn't critical for this command injection
        return self.inject_prompt(prompt_text=prompt.strip(), response_format="command_ack")

    def inject_vote(self, agent_id: str, choice: str, confidence: float = 1.0) -> bool:
        """Injects an AGENT_VOTE command structure via Cursor."""
        prompt = f"""
AGENT_VOTE
agent_id: {agent_id}
vote: {choice}
confidence: {confidence}
"""
        logger.info(f"Injecting AGENT_VOTE for {agent_id} voting for {choice}")
        # Assuming response_format isn't critical for this command injection
        return self.inject_prompt(prompt_text=prompt.strip(), response_format="command_ack")

def main():
    try:
        # Load configuration
        config = AppConfig.load()
        
        # Initialize injector with proper window targeting
        injector = CursorInjector(
            agent_id=config.agent_id,
            target_window_title=config.cursor_window_title,
            coordinates_file=config.cursor_coordinates_file
        )
        
        # Execute injection
        success = injector.inject_prompt(
            prompt_text=config.current_prompt,
            response_format=config.response_format
        )
        
        if success:
            logger.info("Prompt injection successful")
            sys.exit(0)
        else:
            logger.error("Prompt injection failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error during injection: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 