"""
PyAutoGUI Control Module for GUI automation and screen interaction.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import asyncio
import logging
import time
import json
import os

# Optional imports - handle gracefully if not available
try:
    import pyautogui
    import cv2
    import numpy as np
    from PIL import Image, ImageGrab
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    pyautogui = None
    cv2 = None
    np = None
    Image = None
    ImageGrab = None

from ..utils.common_utils import get_logger


class ClipboardError(Exception):
    """Exception raised for clipboard-related errors."""
    pass


class PyAutoGUIError(Exception):
    """Exception raised for PyAutoGUI-related errors."""
    pass


class PyAutoGUIActionFailedError(Exception):
    """Exception raised when a PyAutoGUI action fails."""
    pass


class ImageNotFoundError(Exception):
    """Exception raised when an image is not found on screen."""
    pass


@dataclass
class ScreenRegion:
    """Represents a region on the screen."""
    
    x: int
    y: int
    width: int
    height: int
    
    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Width and height must be positive")
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get the center point of the region."""
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Get the bounds as (left, top, right, bottom)."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class ClickAction:
    """Represents a click action."""
    
    x: int
    y: int
    button: str = "left"
    clicks: int = 1
    interval: float = 0.0
    duration: float = 0.0


@dataclass
class TypingAction:
    """Represents a typing action."""
    
    text: str
    interval: float = 0.0
    duration: float = 0.0


class PyAutoGUIController:
    """Controller for PyAutoGUI operations."""
    
    def __init__(self, fail_safe: bool = True, pause: float = 0.1):
        if not PYAUTOGUI_AVAILABLE:
            raise ImportError("PyAutoGUI is not available. Install with: pip install pyautogui")
        
        self.logger = get_logger("PyAutoGUIController")
        
        # Configure PyAutoGUI
        pyautogui.FAILSAFE = fail_safe
        pyautogui.PAUSE = pause
        
        # Get screen size
        self.screen_width, self.screen_height = pyautogui.size()
        self.logger.info(f"Screen size: {self.screen_width}x{self.screen_height}")
        
        # Statistics
        self.stats = {
            "clicks_performed": 0,
            "keys_typed": 0,
            "screenshots_taken": 0,
            "images_found": 0,
            "errors_encountered": 0
        }
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get the screen size."""
        return (self.screen_width, self.screen_height)
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        return pyautogui.position()
    
    def move_mouse(self, x: int, y: int, duration: float = 0.0) -> bool:
        """Move mouse to specified position."""
        try:
            pyautogui.moveTo(x, y, duration=duration)
            self.logger.debug(f"Moved mouse to ({x}, {y})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to move mouse: {e}")
            self.stats["errors_encountered"] += 1
            return False
    
    def click(self, x: Optional[int] = None, y: Optional[int] = None,
              button: str = "left", clicks: int = 1, interval: float = 0.0) -> bool:
        """Perform a click action."""
        try:
            pyautogui.click(x, y, clicks=clicks, interval=interval, button=button)
            self.stats["clicks_performed"] += 1
            self.logger.debug(f"Clicked at ({x}, {y}) with {button} button")
            return True
        except Exception as e:
            self.logger.error(f"Failed to click: {e}")
            self.stats["errors_encountered"] += 1
            return False
    
    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Perform a double click."""
        return self.click(x, y, clicks=2)
    
    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Perform a right click."""
        return self.click(x, y, button="right")
    
    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int,
             duration: float = 0.0, button: str = "left") -> bool:
        """Drag from start position to end position."""
        try:
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration, button=button)
            self.logger.debug(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to drag: {e}")
            self.stats["errors_encountered"] += 1
            return False
    
    def type_text(self, text: str, interval: float = 0.0) -> bool:
        """Type text at current cursor position."""
        try:
            pyautogui.typewrite(text, interval=interval)
            self.stats["keys_typed"] += len(text)
            self.logger.debug(f"Typed text: {text[:50]}{'...' if len(text) > 50 else ''}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to type text: {e}")
            self.stats["errors_encountered"] += 1
            return False
    
    def press_key(self, key: str) -> bool:
        """Press a single key."""
        try:
            pyautogui.press(key)
            self.stats["keys_typed"] += 1
            self.logger.debug(f"Pressed key: {key}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to press key {key}: {e}")
            self.stats["errors_encountered"] += 1
            return False
    
    def hotkey(self, *keys: str) -> bool:
        """Press a combination of keys."""
        try:
            pyautogui.hotkey(*keys)
            self.stats["keys_typed"] += len(keys)
            self.logger.debug(f"Pressed hotkey: {'+'.join(keys)}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to press hotkey {'+'.join(keys)}: {e}")
            self.stats["errors_encountered"] += 1
            return False
    
    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Scroll at specified position."""
        try:
            pyautogui.scroll(clicks, x, y)
            self.logger.debug(f"Scrolled {clicks} clicks at ({x}, {y})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to scroll: {e}")
            self.stats["errors_encountered"] += 1
            return False
    
    def screenshot(self, region: Optional[ScreenRegion] = None, 
                  save_path: Optional[str] = None) -> Optional[str]:
        """Take a screenshot."""
        try:
            if region:
                screenshot = pyautogui.screenshot(region=(region.x, region.y, region.width, region.height))
            else:
                screenshot = pyautogui.screenshot()
            
            if save_path:
                screenshot.save(save_path)
                self.logger.debug(f"Screenshot saved to {save_path}")
                self.stats["screenshots_taken"] += 1
                return save_path
            else:
                # Return as base64 or save to temp file
                temp_path = f"screenshot_{int(time.time())}.png"
                screenshot.save(temp_path)
                self.stats["screenshots_taken"] += 1
                return temp_path
                
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            self.stats["errors_encountered"] += 1
            return None
    
    def locate_on_screen(self, image_path: str, confidence: float = 0.9,
                        region: Optional[ScreenRegion] = None) -> Optional[Tuple[int, int, int, int]]:
        """Locate an image on the screen."""
        try:
            if region:
                location = pyautogui.locateOnScreen(
                    image_path, 
                    confidence=confidence,
                    region=(region.x, region.y, region.width, region.height)
                )
            else:
                location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            
            if location:
                self.stats["images_found"] += 1
                self.logger.debug(f"Found image {image_path} at {location}")
                return (location.left, location.top, location.width, location.height)
            else:
                self.logger.debug(f"Image {image_path} not found on screen")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to locate image {image_path}: {e}")
            self.stats["errors_encountered"] += 1
            return None
    
    def click_on_image(self, image_path: str, confidence: float = 0.9,
                      region: Optional[ScreenRegion] = None) -> bool:
        """Click on an image found on screen."""
        location = self.locate_on_screen(image_path, confidence, region)
        if location:
            center_x = location[0] + location[2] // 2
            center_y = location[1] + location[3] // 2
            return self.click(center_x, center_y)
        return False
    
    def wait_for_image(self, image_path: str, timeout: float = 10.0,
                      confidence: float = 0.9, region: Optional[ScreenRegion] = None) -> Optional[Tuple[int, int, int, int]]:
        """Wait for an image to appear on screen."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            location = self.locate_on_screen(image_path, confidence, region)
            if location:
                return location
            time.sleep(0.1)
        
        self.logger.warning(f"Image {image_path} did not appear within {timeout} seconds")
        return None
    
    def get_pixel_color(self, x: int, y: int) -> Optional[Tuple[int, int, int]]:
        """Get the color of a pixel at specified coordinates."""
        try:
            pixel = pyautogui.pixel(x, y)
            return pixel
        except Exception as e:
            self.logger.error(f"Failed to get pixel color at ({x}, {y}): {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get controller statistics."""
        return {
            "screen_size": (self.screen_width, self.screen_height),
            "mouse_position": self.get_mouse_position(),
            "statistics": self.stats.copy(),
            "timestamp": datetime.utcnow().isoformat()
        }


class AutomationScript:
    """Represents an automation script with multiple actions."""
    
    def __init__(self, name: str, controller: PyAutoGUIController):
        self.name = name
        self.controller = controller
        self.actions: List[Dict[str, Any]] = []
        self.logger = get_logger(f"AutomationScript_{name}")
    
    def add_click(self, x: int, y: int, button: str = "left", 
                  clicks: int = 1, interval: float = 0.0) -> 'AutomationScript':
        """Add a click action to the script."""
        self.actions.append({
            "type": "click",
            "x": x,
            "y": y,
            "button": button,
            "clicks": clicks,
            "interval": interval
        })
        return self
    
    def add_type(self, text: str, interval: float = 0.0) -> 'AutomationScript':
        """Add a typing action to the script."""
        self.actions.append({
            "type": "type",
            "text": text,
            "interval": interval
        })
        return self
    
    def add_press(self, key: str) -> 'AutomationScript':
        """Add a key press action to the script."""
        self.actions.append({
            "type": "press",
            "key": key
        })
        return self
    
    def add_hotkey(self, *keys: str) -> 'AutomationScript':
        """Add a hotkey action to the script."""
        self.actions.append({
            "type": "hotkey",
            "keys": keys
        })
        return self
    
    def add_wait(self, seconds: float) -> 'AutomationScript':
        """Add a wait action to the script."""
        self.actions.append({
            "type": "wait",
            "seconds": seconds
        })
        return self
    
    def add_screenshot(self, save_path: Optional[str] = None) -> 'AutomationScript':
        """Add a screenshot action to the script."""
        self.actions.append({
            "type": "screenshot",
            "save_path": save_path
        })
        return self
    
    async def execute(self) -> Dict[str, Any]:
        """Execute the automation script."""
        self.logger.info(f"Executing automation script: {self.name}")
        
        results = {
            "script_name": self.name,
            "total_actions": len(self.actions),
            "successful_actions": 0,
            "failed_actions": 0,
            "execution_time": 0.0,
            "actions_results": []
        }
        
        start_time = time.time()
        
        for i, action in enumerate(self.actions):
            action_result = {
                "index": i,
                "type": action["type"],
                "success": False,
                "error": None
            }
            
            try:
                if action["type"] == "click":
                    success = self.controller.click(
                        action["x"], action["y"], 
                        action["button"], action["clicks"], action["interval"]
                    )
                    action_result["success"] = success
                    
                elif action["type"] == "type":
                    success = self.controller.type_text(action["text"], action["interval"])
                    action_result["success"] = success
                    
                elif action["type"] == "press":
                    success = self.controller.press_key(action["key"])
                    action_result["success"] = success
                    
                elif action["type"] == "hotkey":
                    success = self.controller.hotkey(*action["keys"])
                    action_result["success"] = success
                    
                elif action["type"] == "wait":
                    await asyncio.sleep(action["seconds"])
                    action_result["success"] = True
                    
                elif action["type"] == "screenshot":
                    result = self.controller.screenshot(save_path=action.get("save_path"))
                    action_result["success"] = result is not None
                    action_result["result"] = result
                
                if action_result["success"]:
                    results["successful_actions"] += 1
                else:
                    results["failed_actions"] += 1
                    
            except Exception as e:
                action_result["error"] = str(e)
                results["failed_actions"] += 1
                self.logger.error(f"Action {i} failed: {e}")
            
            results["actions_results"].append(action_result)
        
        results["execution_time"] = time.time() - start_time
        self.logger.info(f"Script {self.name} completed in {results['execution_time']:.2f}s")
        
        return results
    
    def save_to_file(self, file_path: str) -> bool:
        """Save the script to a JSON file."""
        try:
            script_data = {
                "name": self.name,
                "actions": self.actions,
                "created_at": datetime.utcnow().isoformat()
            }
            
            with open(file_path, 'w') as f:
                json.dump(script_data, f, indent=2)
            
            self.logger.info(f"Script saved to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save script: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, file_path: str, controller: PyAutoGUIController) -> 'AutomationScript':
        """Load a script from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                script_data = json.load(f)
            
            script = cls(script_data["name"], controller)
            script.actions = script_data["actions"]
            
            return script
            
        except Exception as e:
            raise ValueError(f"Failed to load script from {file_path}: {e}")


class PyAutoGUIControlModule:
    """Main module for PyAutoGUI control operations."""
    
    def __init__(self, fail_safe: bool = True, pause: float = 0.1):
        if not PYAUTOGUI_AVAILABLE:
            raise ImportError("PyAutoGUI is not available. Install with: pip install pyautogui")
        
        self.controller = PyAutoGUIController(fail_safe, pause)
        self.logger = get_logger("PyAutoGUIControlModule")
        self.scripts: Dict[str, AutomationScript] = {}
    
    def create_script(self, name: str) -> AutomationScript:
        """Create a new automation script."""
        script = AutomationScript(name, self.controller)
        self.scripts[name] = script
        return script
    
    def get_script(self, name: str) -> Optional[AutomationScript]:
        """Get a script by name."""
        return self.scripts.get(name)
    
    def list_scripts(self) -> List[str]:
        """List all available scripts."""
        return list(self.scripts.keys())
    
    async def execute_script(self, name: str) -> Optional[Dict[str, Any]]:
        """Execute a script by name."""
        script = self.get_script(name)
        if script:
            return await script.execute()
        else:
            self.logger.error(f"Script {name} not found")
            return None
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        return {
            "pyautogui_available": PYAUTOGUI_AVAILABLE,
            "controller_stats": self.controller.get_statistics(),
            "available_scripts": self.list_scripts(),
            "timestamp": datetime.utcnow().isoformat()
        } 