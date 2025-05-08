# src/dreamos/skills/pyautogui_control_module.py

import asyncio
import logging
import platform
import time # Added time for delays
from pathlib import Path # Ensure Path is imported
from typing import Any, Dict, List, Optional, Tuple, Type # Added List, Type

import pyautogui
import pyperclip

# Optional: pygetwindow for focus check, handle if not available
try:
    import pygetwindow
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    pygetwindow = None
    PYGETWINDOW_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "pygetwindow not found. Window focus checks will be limited."
    )

from dreamos.core.config import AppConfig
from dreamos.core.errors import ToolError
# Assuming retry decorator might live in utils or a dedicated decorators module
# from dreamos.utils.decorators import retry_on_exception # Example

# --- Module Specific Exceptions --- #

class PyAutoGUIControlError(ToolError):
    """Base exception for PyAutoGUIControlModule errors."""
    pass

class WindowNotFoundError(PyAutoGUIControlError):
    """Target application window not found or couldn't be focused."""
    pass

class ImageNotFoundError(PyAutoGUIControlError):
    """A visual element (image) could not be located on screen within timeout."""
    pass

class InteractionTimeoutError(PyAutoGUIControlError):
    """An action (e.g., waiting for clipboard) timed out."""
    pass

class ClipboardError(PyAutoGUIControlError):
    """Issues with reading from or writing to the clipboard."""
    pass

class PyAutoGUIActionFailedError(PyAutoGUIControlError):
    """Wrapper for underlying PyAutoGUI exceptions if not fitting other categories."""
    pass

# Define a tuple of retryable exceptions for internal use or decorator
RETRYABLE_GUI_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    pyautogui.FailSafeException,
    ImageNotFoundError, # If we want to retry image finding specifically
    InteractionTimeoutError,
    ClipboardError, # Some clipboard errors might be transient
    # Add other pyautogui or custom exceptions that are deemed retryable
)

class PyAutoGUIControlModule:
    """
    Provides a controlled interface for PyAutoGUI operations, including window management,
    visual element interaction, keyboard/mouse control, and clipboard operations.
    Integrates with AppConfig for settings and provides robust error handling.
    """

    def __init__(self, config: AppConfig, target_window_title_pattern: str):
        """
        Initializes the module with AppConfig and a specific target window title pattern.

        Args:
            config: The loaded AppConfig instance.
            target_window_title_pattern: A string pattern to identify the target window(s).
                                        Case-insensitive containment check will be used.
        """
        self.app_config: AppConfig = config
        self.logger: logging.Logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.target_window_title_pattern: str = target_window_title_pattern.lower()

        # Extract relevant pyautogui_bridge settings from AppConfig
        gui_auto_config = getattr(self.app_config, 'gui_automation', None)
        module_config_raw = getattr(gui_auto_config, 'pyautogui_bridge', {})
        
        # Ensure module_config is a dictionary for consistent access
        if hasattr(module_config_raw, 'model_dump'): # Check for Pydantic v2
             self.module_config: Dict[str, Any] = module_config_raw.model_dump()
        elif hasattr(module_config_raw, 'dict'): # Check for Pydantic v1
             self.module_config: Dict[str, Any] = module_config_raw.dict()
        elif isinstance(module_config_raw, Dict):
             self.module_config: Dict[str, Any] = module_config_raw
        else:
             self.logger.warning("Could not convert pyautogui_bridge config to dict, using empty defaults.")
             self.module_config: Dict[str, Any] = {}

        # --- Get Configurable Defaults (with type hints) --- #
        self.default_confidence: float = self.module_config.get('default_confidence', 0.9)
        self.default_timeout_seconds: float = self.module_config.get('default_timeout_seconds', 10.0)
        self.default_retry_attempts: int = self.module_config.get('default_retry_attempts', 3)
        self.default_retry_delay_seconds: float = self.module_config.get('default_retry_delay_seconds', 0.5)
        self.type_interval_seconds: float = self.module_config.get('type_interval_seconds', 0.01)
        
        image_assets_rel_path: str = self.module_config.get('image_assets_path', "runtime/assets/bridge_gui_snippets/")
        self.image_assets_base_path: Path = Path(image_assets_rel_path)
        if self.app_config.paths and self.app_config.paths.project_root:
            self.image_assets_base_path = self.app_config.paths.project_root / image_assets_rel_path
        else:
            self.logger.warning(f"Project root not found in AppConfig. Image assets path '{self.image_assets_base_path}' might be incorrect.")

        self.logger.info(
            f"PyAutoGUIControlModule initialized for target window pattern: '{target_window_title_pattern}'"
        )
        self.logger.debug(f"Image assets base path: {self.image_assets_base_path}")
        self.logger.debug(f"Loaded module config: {self.module_config}")

    async def _run_blocking_io(self, func: callable, *args: Any, **kwargs: Any) -> Any:
        """
        Helper to run blocking sync functions (like PyAutoGUI calls) 
        in a separate thread to avoid blocking the asyncio event loop.

        Args:
            func: The blocking function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            The result of the blocking function.
            
        Raises:
             Any exception raised by the underlying function `func`.
        """
        loop = asyncio.get_running_loop()
        # Ensure the function and its arguments are passed correctly to lambda
        # Using default arguments in lambda to capture current values
        try:
            result = await loop.run_in_executor(None, lambda f=func, a=args, k=kwargs: f(*a, **k))
            return result
        except Exception as e:
            # Log the error originating from the blocking call
            self.logger.error(f"Error during blocking I/O call to {func.__name__}: {e}", exc_info=True)
            # Re-raise the original exception to be handled by the calling method
            raise e

    # --- Window Management --- #
    async def ensure_window_focused(self, attempts: int = 3) -> bool:
        """
        Ensures the target application window (matching `self.target_window_title_pattern`)
        is active and in the foreground. Uses OS-level controls if `pygetwindow` is available.

        Retries focusing the window up to the specified number of attempts.

        Args:
            attempts: The maximum number of attempts to find and focus the window.

        Returns:
            `True` if the target window is successfully focused (or if focus check is skipped
            due to `pygetwindow` unavailability). 
            `False` if focusing fails after all attempts.

        Raises:
            WindowNotFoundError: If the window cannot be found after all attempts, 
                                 or if an error occurs during activation that persists.
            PyAutoGUIControlError: For other unexpected errors during the process.
        """
        if not PYGETWINDOW_AVAILABLE or pygetwindow is None:
            self.logger.warning(
                "Cannot ensure window focus: pygetwindow not available. Proceeding with caution."
            )
            return True # Optimistically assume focus is okay if we cannot check/control it

        target_pattern: str = self.target_window_title_pattern
        self.logger.debug(f"Ensuring window focus for pattern: '{target_pattern}'")

        for attempt_num in range(attempts):
            self.logger.debug(f"Focus check/ensure attempt {attempt_num + 1}/{attempts}")
            try:
                target_windows: List[Any] = await self._run_blocking_io(
                    pygetwindow.getWindowsWithTitle, target_pattern
                )

                if not target_windows:
                    self.logger.warning(f"No windows found matching pattern '{target_pattern}'.")
                    if attempt_num < attempts - 1:
                        await asyncio.sleep(self.default_retry_delay_seconds) 
                        continue
                    else:
                        raise WindowNotFoundError(f"Target window pattern '{target_pattern}' not found after {attempts} attempts.")

                active_window: Optional[Any] = await self._run_blocking_io(pygetwindow.getActiveWindow)
                target_window_to_activate: Any = target_windows[0] # Default to first match
                
                is_already_active = False
                if active_window:
                    # Compare based on available attributes (e.g., _hWnd on Windows, title as fallback)
                    active_title_lower = getattr(active_window, 'title', '').lower()
                    for win in target_windows:
                        win_title_lower = getattr(win, 'title', '').lower()
                        if platform.system() == "Windows" and hasattr(win, '_hWnd') and hasattr(active_window, '_hWnd'):
                            if win._hWnd == active_window._hWnd:
                                is_already_active = True
                                target_window_to_activate = win
                                break
                        # Add more specific checks for macOS/Linux if needed, or rely on title
                        elif target_pattern in active_title_lower and target_pattern in win_title_lower and active_title_lower == win_title_lower:
                             # Fallback to title match if specific handles aren't directly comparable or available
                            is_already_active = True
                            target_window_to_activate = win
                            break 
                    
                if is_already_active:
                    self.logger.debug(f"Target window '{target_window_to_activate.title}' is already active.")
                    return True

                self.logger.warning(
                    f"Target window '{target_window_to_activate.title}' found but not active. Attempting to activate..."
                )
                
                def activate_sync(window_to_activate: Any) -> bool:
                    try:
                        if hasattr(window_to_activate, 'activate') and callable(window_to_activate.activate):
                            window_to_activate.activate()
                            time.sleep(0.2) # Give OS a moment to process activation
                            return window_to_activate.isActive # Check if activation succeeded
                        else:
                            self.logger.warning(f"Window object for '{window_to_activate.title}' does not have an 'activate' method.")
                            return False # Cannot activate if method missing
                    except Exception as e:
                        self.logger.error(f"Error during sync window activation for '{getattr(window_to_activate, 'title', 'UnknownTitle')}': {e}", exc_info=False)
                        return False

                activated: bool = await self._run_blocking_io(activate_sync, target_window_to_activate)

                if activated:
                    await asyncio.sleep(0.3) # Further pause for OS to settle focus
                    final_active_window: Optional[Any] = await self._run_blocking_io(pygetwindow.getActiveWindow)
                    if final_active_window and getattr(final_active_window, 'title', '').lower() == getattr(target_window_to_activate, 'title', ' ').lower():
                         # Compare titles as a more general check post-activation
                        self.logger.info(f"Successfully activated target window '{target_window_to_activate.title}'.")
                        return True
                    else:
                        current_active_title = getattr(final_active_window, 'title', "None")
                        self.logger.warning(f"Activation attempt for '{target_window_to_activate.title}' made, but window '{current_active_title}' is now active instead.")
                else:
                     self.logger.warning(f"Call to activate window '{target_window_to_activate.title}' did not succeed or returned False.")

            except WindowNotFoundError:
                raise # Re-raise if explicitly raised from within the loop
            except Exception as e:
                self.logger.error(f"Error during focus check/activation attempt {attempt_num + 1}: {e}", exc_info=True)
                if attempt_num >= attempts - 1:
                     raise PyAutoGUIControlError(f"Failed to ensure window focus after {attempts} attempts due to: {e}") from e

            if attempt_num < attempts - 1:
                self.logger.debug(f"Waiting {self.default_retry_delay_seconds}s before next focus attempt...")
                await asyncio.sleep(self.default_retry_delay_seconds)

        self.logger.error(f"Failed to ensure window focus for pattern '{target_pattern}' after {attempts} attempts.")
        # Ensure WindowNotFoundError is raised if loop completes without success
        raise WindowNotFoundError(f"Failed to ensure window focus for pattern '{target_pattern}' after {attempts} attempts.")

    # --- Visual Element Interaction --- #
    async def find_element_on_screen(
        self,
        image_path: str, 
        confidence: Optional[float] = None, 
        timeout: Optional[float] = None,    
        region: Optional[Tuple[int, int, int, int]] = None, 
        grayscale: bool = True, 
        poll_interval: float = 0.5 
    ) -> Tuple[int, int]: # Changed return type to non-optional as it raises on failure
        """
        Locates an image on the screen and returns its center coordinates.

        This method repeatedly attempts to find the specified image file on the screen
        until it is found or the timeout is reached. It uses the image_assets_base_path
        resolved during initialization if a relative path is given for image_path.

        Args:
            image_path: Path to the image file to locate. Can be relative to the
                        configured image_assets_base_path or an absolute path.
            confidence: The confidence level for image recognition (0.0 to 1.0).
                        If None, uses self.default_confidence.
            timeout: Maximum time in seconds to search for the image.
                     If None, uses self.default_timeout_seconds.
            region: An optional tuple (left, top, width, height) defining the
                    screen region to search within.
            grayscale: If True, converts the image and screen to grayscale for matching,
                       which can improve performance and accuracy.
            poll_interval: Time in seconds to wait between search attempts.

        Returns:
            A tuple (x, y) representing the center coordinates of the found image.

        Raises:
            FileNotFoundError: If the specified image_path does not exist.
            ImageNotFoundError: If the image cannot be found on screen within the timeout.
            PyAutoGUIActionFailedError: If PyAutoGUI's FailSafeException is triggered.
            PyAutoGUIControlError: For other unexpected errors during the process.
        """
        start_time = time.monotonic()
        
        img_full_path: Path = Path(image_path)
        if not img_full_path.is_absolute():
            img_full_path = self.image_assets_base_path / image_path
            
        if not img_full_path.exists():
            self.logger.error(f"Image file not found: {img_full_path}")
            raise FileNotFoundError(f"Image file not found: {img_full_path}")
            
        img_filename: str = img_full_path.name

        conf_to_use: float = confidence if confidence is not None else self.default_confidence
        timeout_to_use: float = timeout if timeout is not None else self.default_timeout_seconds
        
        self.logger.debug(f"Attempting to find element '{img_filename}' (confidence={conf_to_use:.2f}, timeout={timeout_to_use:.1f}s)")
        
        while time.monotonic() - start_time < timeout_to_use:
            try:
                locate_kwargs: Dict[str, Any] = {
                    'image': str(img_full_path),
                    'confidence': conf_to_use,
                    'grayscale': grayscale,
                }
                if region:
                    locate_kwargs['region'] = region

                # PyAutoGUI.locateCenterOnScreen can return None or Point, or raise ImageNotFoundException
                center_pos_pyautogui: Optional[Any] = await self._run_blocking_io(
                    pyautogui.locateCenterOnScreen, **locate_kwargs
                )

                if center_pos_pyautogui is not None:
                    coords: Tuple[int, int] = (center_pos_pyautogui.x, center_pos_pyautogui.y)
                    self.logger.info(
                        f"Element '{img_filename}' found at {coords} after {time.monotonic() - start_time:.2f}s."
                    )
                    return coords
                # else: Image not found yet by locateCenterOnScreen, continue loop
                self.logger.debug(f"Element '{img_filename}' not located in this attempt via locateCenterOnScreen.")

            except pyautogui.ImageNotFoundException:
                 # This specific exception is from older pyautogui or if all attempts within a single call fail.
                 # Our loop handles polling, so this is just one poll failing.
                self.logger.debug(f"Element '{img_filename}' not found on this attempt (ImageNotFoundException).")
            except pyautogui.FailSafeException as e:
                 self.logger.error(f"PyAutoGUI fail-safe triggered during find_element_on_screen for '{img_filename}'.")
                 raise PyAutoGUIActionFailedError(f"Fail-safe triggered finding {img_filename}") from e
            except Exception as e:
                self.logger.error(f"Unexpected error finding '{img_filename}': {e}", exc_info=True)
                raise PyAutoGUIControlError(f"Unexpected error finding {img_filename}: {e}") from e

            await asyncio.sleep(poll_interval)

        self.logger.error(
            f"Timeout: Element '{img_filename}' not found after {timeout_to_use:.1f} seconds."
        )
        raise ImageNotFoundError(f"Element '{img_filename}' not found within timeout.")

    async def click_element(
        self,
        image_path: Optional[str] = None,
        coords: Optional[Tuple[int, int]] = None,
        button: str = 'left',
        clicks: int = 1,
        interval: float = 0.0, # Interval between clicks if clicks > 1
        confidence: Optional[float] = None,
        timeout: Optional[float] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        move_duration: float = 0.1 # Duration of mouse move
    ) -> bool:
        """
        Clicks at the location of a found image or at specified coordinates.

        Ensures window focus before interacting.

        Args:
            image_path: Path to the reference image file to find and click.
            coords: Specific (x, y) coordinates to click.
                    One of image_path or coords must be provided.
            button: Mouse button ('left', 'middle', 'right').
            clicks: Number of times to click.
            interval: Delay between clicks if clicks > 1.
            confidence: Confidence level for image matching (if image_path is used).
            timeout: Timeout for finding the image (if image_path is used).
            region: Screen region to search within (if image_path is used).
            move_duration: Duration (in seconds) for the mouse cursor movement.

        Returns:
            True if the click was successfully attempted, False otherwise.
            
        Raises:
            ValueError: If neither image_path nor coords is provided.
            ImageNotFoundError: If image_path is provided but the image is not found.
            PyAutoGUIControlError: For underlying pyautogui errors or focus issues.
        """
        if not image_path and not coords:
            raise ValueError("Either image_path or coords must be provided to click_element.")

        target_coords: Optional[Tuple[int, int]] = None

        # 1. Ensure window is focused
        if not await self.ensure_window_focused():
            # Error already logged by ensure_window_focused
            # Raise specific error indicating focus failure before action
            raise WindowNotFoundError(f"Target window '{self.target_window_title_pattern}' could not be focused before click.")

        # 2. Determine target coordinates
        if image_path:
            self.logger.debug(f"Finding element '{image_path}' before clicking.")
            # Reuse find_element_on_screen, which handles errors/timeout internally
            # It raises ImageNotFoundError if not found, which we let propagate
            target_coords = await self.find_element_on_screen(
                image_path=image_path,
                confidence=confidence,
                timeout=timeout,
                region=region
                # grayscale is handled by find_element_on_screen default
            )
            if target_coords is None:
                 # This case should ideally not be reached if find_element_on_screen raises properly 
                 self.logger.error(f"Element '{image_path}' could not be found (returned None unexpectedly). Cannot click.")
                 return False # Or raise error?
        elif coords:
            target_coords = coords

        if not target_coords:
            # This should only happen if coords were provided but were None/empty somehow, 
            # or if find_element_on_screen logic failed to raise.
            self.logger.error("No valid target coordinates determined for click.")
            return False

        # 3. Perform the click action
        self.logger.debug(f"Attempting to click {clicks} time(s) with {button} button at {target_coords}")
        try:
            # Run click in executor
            await self._run_blocking_io(
                pyautogui.click,
                x=target_coords[0],
                y=target_coords[1],
                clicks=clicks,
                interval=interval,
                button=button,
                duration=move_duration
            )
            self.logger.info(f"Successfully clicked at {target_coords}.")
            return True
            
        except pyautogui.FailSafeException as e:
            self.logger.error(f"PyAutoGUI fail-safe triggered during click at {target_coords}.")
            raise PyAutoGUIActionFailedError(f"Fail-safe triggered during click at {target_coords}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error during click at {target_coords}: {e}", exc_info=True)
            raise PyAutoGUIControlError(f"Unexpected error during click at {target_coords}: {e}") from e

    # --- Keyboard & Text Input --- #
    async def type_text(
        self,
        text: str,
        interval: Optional[float] = None, # Defaults from AppConfig (e.g., config.type_interval_seconds)
        target_image_path: Optional[str] = None, # Optional: click this image first
        target_coords: Optional[Tuple[int, int]] = None, # Optional: click these coords first
        clear_before_typing: bool = False, # Optional: Clear field with Ctrl+A, Del
    ) -> bool:
        """
        Types the given text, optionally clicking a target location first and clearing the field.

        Ensures window focus before interacting.

        Args:
            text: The string to type.
            interval: Interval between keystrokes (overrides config default).
            target_image_path: Image of an element to click before typing.
            target_coords: Coordinates (x, y) to click before typing.
                             If both image and coords are given, image takes precedence.
            clear_before_typing: If True, attempt to clear the field (Ctrl+A, Del) after clicking.

        Returns:
            True if typing was successfully attempted, False otherwise.
            
        Raises:
            ImageNotFoundError: If target_image_path is provided but the image is not found.
            PyAutoGUIControlError: For underlying pyautogui errors or focus issues.
            WindowNotFoundError: If the target window cannot be focused.
        """
        # 1. Ensure window is focused
        if not await self.ensure_window_focused():
            raise WindowNotFoundError(f"Target window '{self.target_window_title_pattern}' could not be focused before typing.")

        # 2. Click target if specified
        if target_image_path or target_coords:
            self.logger.debug("Clicking target location before typing.")
            # Use click_element to handle finding/clicking and its errors
            clicked = await self.click_element(
                image_path=target_image_path, 
                coords=target_coords,
                # Use defaults for confidence/timeout from config via click_element
            )
            if not clicked:
                self.logger.error("Failed to click target location before typing. Aborting type.")
                return False # click_element already logged/raised specific error

            # Short pause after click before potentially clearing/typing
            await asyncio.sleep(self.default_retry_delay_seconds)

        # 3. Clear field if requested
        if clear_before_typing:
            self.logger.debug("Clearing field before typing (Ctrl+A, Del)")
            try:
                await self._run_blocking_io(pyautogui.hotkey, 'ctrl', 'a')
                await asyncio.sleep(0.1) # Brief pause between hotkeys
                await self._run_blocking_io(pyautogui.press, 'delete')
                await asyncio.sleep(0.1) # Brief pause after clearing
            except pyautogui.FailSafeException as e:
                self.logger.error("PyAutoGUI fail-safe triggered during field clearing.")
                raise PyAutoGUIActionFailedError("Fail-safe triggered during field clearing") from e
            except Exception as e:
                self.logger.error(f"Unexpected error during field clearing: {e}", exc_info=True)
                raise PyAutoGUIControlError(f"Unexpected error during field clearing: {e}") from e

        # 4. Perform the typing action
        type_interval_to_use = interval if interval is not None else self.type_interval_seconds
        self.logger.debug(f"Attempting to type text (length: {len(text)}) with interval {type_interval_to_use:.3f}s")
        
        try:
            # Prefer clipboard paste for longer text if pyperclip is available
            if len(text) > 50 and pyperclip: # Arbitrary threshold
                 self.logger.debug("Using clipboard paste for longer text.")
                 await self._run_blocking_io(pyperclip.copy, text)
                 await asyncio.sleep(0.1) # Allow clipboard to settle
                 await self._run_blocking_io(pyautogui.hotkey, 'ctrl', 'v')
            else:
                self.logger.debug("Using direct typing.")
                await self._run_blocking_io(pyautogui.write, text, interval=type_interval_to_use)
            
            self.logger.info("Successfully typed text.")
            return True
            
        except pyautogui.FailSafeException as e:
            self.logger.error("PyAutoGUI fail-safe triggered during typing.")
            raise PyAutoGUIActionFailedError("Fail-safe triggered during typing") from e
        except Exception as e:
            self.logger.error(f"Unexpected error during typing: {e}", exc_info=True)
            raise PyAutoGUIControlError(f"Unexpected error during typing: {e}") from e

    async def press_hotkey(self, *keys: str) -> bool:
        """
        Presses a sequence of keys simultaneously (hotkey).
        Example: press_hotkey('ctrl', 'c')
        Uses pyautogui.hotkey.
        Ensures window focus before acting.

        Args:
            *keys: Sequence of keys to press (e.g., 'ctrl', 'alt', 'delete').

        Returns:
            True if the hotkey was successfully attempted, False otherwise.
        
        Raises:
            PyAutoGUIControlError: For underlying pyautogui errors or focus issues.
            WindowNotFoundError: If the target window cannot be focused.
        """
        if not await self.ensure_window_focused():
            raise WindowNotFoundError(f"Target window '{self.target_window_title_pattern}' could not be focused before pressing hotkey.")
        
        self.logger.debug(f"Attempting to press hotkey: {keys}")
        try:
            await self._run_blocking_io(pyautogui.hotkey, *keys)
            self.logger.info(f"Successfully pressed hotkey: {keys}")
            return True
        except pyautogui.FailSafeException as e:
            self.logger.error(f"PyAutoGUI fail-safe triggered during hotkey press: {keys}")
            raise PyAutoGUIActionFailedError(f"Fail-safe triggered during hotkey press: {keys}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error during hotkey press {keys}: {e}", exc_info=True)
            raise PyAutoGUIControlError(f"Unexpected error during hotkey press {keys}: {e}") from e

    async def press_key(self, key: str) -> bool:
        """
        Presses a single key.
        Example: press_key('enter')
        Uses pyautogui.press.
        Ensures window focus before acting.

        Args:
            key: The key to press (e.g., 'enter', 'f5', 'a').

        Returns:
            True if the key press was successfully attempted, False otherwise.
        
        Raises:
            PyAutoGUIControlError: For underlying pyautogui errors or focus issues.
            WindowNotFoundError: If the target window cannot be focused.
        """
        if not await self.ensure_window_focused():
            raise WindowNotFoundError(f"Target window '{self.target_window_title_pattern}' could not be focused before pressing key '{key}'.")
            
        self.logger.debug(f"Attempting to press key: {key}")
        try:
            await self._run_blocking_io(pyautogui.press, key)
            self.logger.info(f"Successfully pressed key: {key}")
            return True
        except pyautogui.FailSafeException as e:
            self.logger.error(f"PyAutoGUI fail-safe triggered during key press: {key}")
            raise PyAutoGUIActionFailedError(f"Fail-safe triggered during key press: {key}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error during key press {key}: {e}", exc_info=True)
            raise PyAutoGUIControlError(f"Unexpected error during key press {key}: {e}") from e

    # --- Clipboard Operations --- #
    async def get_clipboard_text(self) -> Optional[str]:
        """
        Safely retrieves text from the clipboard.
        Uses pyperclip.paste, wrapped in executor, with error handling.
        Inspired by gui_utils.get_clipboard_content_safe.

        Returns:
            The text content from the clipboard, or None if an error occurs.
        """
        self.logger.debug("Attempting to get clipboard text.")
        if not pyperclip:
            self.logger.error("Cannot get clipboard text: pyperclip is not available.")
            raise ClipboardError("pyperclip library not available.")
        try:
            # pyperclip.paste() can sometimes be slow or hang, run in executor
            content = await self._run_blocking_io(pyperclip.paste)
            # Explicitly check for None or empty string if that constitutes "no content"
            # Pyperclip typically returns empty string if clipboard is empty/non-text
            self.logger.info(f"Retrieved clipboard text (length: {len(content)})")
            return content
        except Exception as e:
            # Catch potential pyperclip specific errors if they exist, or general exceptions
            self.logger.error(f"Error getting text from clipboard: {e}", exc_info=True)
            # Do not raise here, return None as per docstring/API proposal intent?
            # Or should we raise ClipboardError? Let's raise for clarity.
            raise ClipboardError(f"Failed to get clipboard content: {e}") from e

    async def set_clipboard_text(self, text: str) -> bool:
        """
        Safely sets text to the clipboard.
        Uses pyperclip.copy, wrapped in executor, with error handling.

        Args:
            text: The string to set to the clipboard.

        Returns:
            True if successful, False otherwise (though it raises on error).
            
        Raises:
            ClipboardError: If setting clipboard fails or pyperclip is unavailable.
        """
        self.logger.debug(f"Attempting to set clipboard text (length: {len(text)}).")
        if not pyperclip:
            self.logger.error("Cannot set clipboard text: pyperclip is not available.")
            raise ClipboardError("pyperclip library not available.")
        try:
            # pyperclip.copy() can also potentially block
            await self._run_blocking_io(pyperclip.copy, text)
            self.logger.info("Successfully set clipboard text.")
            return True
        except Exception as e:
            self.logger.error(f"Error setting clipboard text: {e}", exc_info=True)
            raise ClipboardError(f"Failed to set clipboard content: {e}") from e

    # --- Combined Operations (examples) --- #
    async def find_type_and_enter(
        self,
        target_image_to_click: str,
        text_to_type: str,
        confidence: Optional[float] = None,
        find_timeout: Optional[float] = None,
        type_interval: Optional[float] = None,
        clear_before_typing: bool = True, # Default to clearing before typing
        wait_for_readiness_image: Optional[str] = None, # Image to appear after Enter
        readiness_timeout: Optional[float] = None # Timeout for readiness image
    ) -> bool:
        """
        A higher-level operation: finds an element (e.g., input field based on image),
        clicks it, optionally clears it, types text, presses Enter,
        and optionally waits for a readiness cue image.

        Ensures window focus before starting.

        Args:
            target_image_to_click: Image file path of the element to click before typing.
            text_to_type: The text to input.
            confidence: Confidence level for finding target_image_to_click.
            find_timeout: Timeout for finding target_image_to_click.
            type_interval: Interval for typing (overrides config default).
            clear_before_typing: Whether to clear the field before typing (default True).
            wait_for_readiness_image: Optional image file path to wait for after pressing Enter.
            readiness_timeout: Timeout for waiting for the readiness image.

        Returns:
            True if the entire sequence completes successfully, False otherwise.

        Raises:
            ImageNotFoundError: If target_image_to_click or wait_for_readiness_image not found.
            PyAutoGUIControlError: For underlying automation errors.
            WindowNotFoundError: If the target window cannot be focused.
            FileNotFoundError: If image files themselves are missing.
        """
        self.logger.info(f"Executing find_type_and_enter sequence for image '{target_image_to_click}'")
        
        # 1. Ensure window is focused (already done implicitly by type_text, but good practice)
        if not await self.ensure_window_focused():
            raise WindowNotFoundError(f"Target window '{self.target_window_title_pattern}' could not be focused.")

        # 2. Find, click, clear (if requested), and type text using type_text method
        # This leverages the error handling and logic within type_text
        try:
            type_success = await self.type_text(
                text=text_to_type,
                interval=type_interval,
                target_image_path=target_image_to_click,
                clear_before_typing=clear_before_typing,
                # Pass relevant args down to the underlying find/click
                # Note: type_text internally calls click_element which calls find_element_on_screen
                # We rely on those methods picking up confidence/timeout from defaults if not overridden here.
                # If specific overrides are needed for the *initial* find in this sequence, 
                # we might need to call find_element_on_screen first, then click_element(coords=...), then type_text(target_coords=...).
                # For simplicity now, assume click_element within type_text is sufficient or uses good defaults.
            )
            
            if not type_success:
                 # Error should have been raised by type_text or its sub-calls
                 self.logger.error("type_text step failed within find_type_and_enter sequence.")
                 return False # Should not be reached if exceptions are working

        except (WindowNotFoundError, ImageNotFoundError, PyAutoGUIControlError, FileNotFoundError) as e:
             self.logger.error(f"Error during type_text step in sequence: {e}")
             raise # Re-raise the specific error caught from type_text

        # 3. Press Enter
        try:
            await self.press_key('enter')
        except (WindowNotFoundError, PyAutoGUIControlError) as e:
            self.logger.error(f"Error pressing Enter in sequence: {e}")
            raise # Re-raise

        # 4. Wait for readiness image if specified
        if wait_for_readiness_image:
            self.logger.info(f"Waiting for readiness indicator: '{wait_for_readiness_image}'")
            try:
                readiness_coords = await self.find_element_on_screen(
                    image_path=wait_for_readiness_image,
                    timeout=readiness_timeout # Use specific timeout for this wait
                    # Confidence uses default unless specified for this specific wait
                )
                if readiness_coords:
                    self.logger.info("Readiness indicator found.")
                else:
                    # Should be unreachable if find_element_on_screen raises ImageNotFoundError on timeout
                    self.logger.error("Readiness indicator not found (timeout likely occurred). Sequence failed.")
                    return False
            except (ImageNotFoundError, PyAutoGUIControlError, FileNotFoundError) as e:
                self.logger.error(f"Error waiting for readiness image '{wait_for_readiness_image}': {e}")
                raise # Re-raise error encountered during readiness check

        self.logger.info("find_type_and_enter sequence completed successfully.")
        return True

    async def find_click_select_all_copy(
        self,
        anchor_image_to_click: str, # Image of the text area or a nearby anchor
        confidence: Optional[float] = None,
        find_timeout: Optional[float] = None,
        click_offset: Tuple[int, int] = (0, 0), # Offset from anchor center to click
        clipboard_wait_timeout: Optional[float] = None, # Defaults from AppConfig or internal default
        clipboard_clear_wait: float = 0.1 # Small pause after clearing clipboard
    ) -> Optional[str]:
        """
        Higher-level: finds an anchor image, clicks relative to it (or on it),
        performs select-all (Ctrl/Cmd+A), then copy (Ctrl/Cmd+C),
        polls the clipboard for new content, and returns it.

        Ensures window focus before starting.

        Args:
            anchor_image_to_click: Image file path of the element/anchor to click near.
            confidence: Confidence level for finding the anchor image.
            find_timeout: Timeout for finding the anchor image.
            click_offset: (x, y) offset from the center of the found anchor to click.
                          Use (0,0) to click the center of the anchor itself.
            clipboard_wait_timeout: Max seconds to wait for clipboard content to update.
            clipboard_clear_wait: Seconds to wait after clearing clipboard before copying.

        Returns:
            The copied text content as a string, or None if retrieval fails.

        Raises:
            ImageNotFoundError: If anchor_image_to_click is not found.
            PyAutoGUIControlError: For underlying automation errors.
            WindowNotFoundError: If the target window cannot be focused.
            FileNotFoundError: If anchor_image_to_click file is missing.
            ClipboardError: If clipboard operations fail critically.
        """
        self.logger.info(f"Executing find_click_select_all_copy sequence for anchor '{anchor_image_to_click}'")

        # 1. Ensure window focus
        if not await self.ensure_window_focused():
            raise WindowNotFoundError(f"Target window '{self.target_window_title_pattern}' could not be focused.")

        # 2. Find the anchor element
        # Let find_element_on_screen handle timeout/error raising
        anchor_coords = await self.find_element_on_screen(
            image_path=anchor_image_to_click,
            confidence=confidence,
            timeout=find_timeout
        )
        if not anchor_coords:
             # Should be unreachable if find_element_on_screen raises ImageNotFoundError
             self.logger.error(f"Anchor image '{anchor_image_to_click}' not found (returned None unexpectedly).")
             return None 

        # 3. Calculate click coordinates with offset
        click_coords = (anchor_coords[0] + click_offset[0], anchor_coords[1] + click_offset[1])

        # 4. Perform click at the target coordinates
        # Use click_element for consistency, although we already found the coords
        clicked = await self.click_element(coords=click_coords)
        if not clicked:
            # Should be unreachable if click_element raises error on failure
            self.logger.error(f"Failed to click at offset {click_offset} from anchor '{anchor_image_to_click}'.")
            return None 

        # Short pause after click before hotkeys
        await asyncio.sleep(self.default_retry_delay_seconds)

        # 5. Prime clipboard and execute Select All + Copy
        initial_clipboard_content = None
        try:
            initial_clipboard_content = await self.get_clipboard_text() # Get initial state
            await self.set_clipboard_text("") # Clear clipboard
            await asyncio.sleep(clipboard_clear_wait) # Wait briefly

            # Platform specific hotkeys
            if platform.system() == "Darwin": # macOS
                await self.press_hotkey('command', 'a')
                await asyncio.sleep(0.1)
                await self.press_hotkey('command', 'c')
            else: # Windows, Linux
                await self.press_hotkey('ctrl', 'a')
                await asyncio.sleep(0.1)
                await self.press_hotkey('ctrl', 'c')
                
            self.logger.info("Executed Select All and Copy hotkeys.")

        except (WindowNotFoundError, PyAutoGUIControlError, ClipboardError) as e:
            self.logger.error(f"Error during select/copy hotkeys: {e}")
            raise # Re-raise the error
            
        # 6. Poll clipboard for new content
        wait_start_time = time.monotonic()
        effective_clipboard_timeout = clipboard_wait_timeout if clipboard_wait_timeout is not None else self.module_config.get('clipboard_wait_timeout', 5.0)
        
        self.logger.debug(f"Polling clipboard for new content (timeout: {effective_clipboard_timeout}s)")
        while time.monotonic() - wait_start_time < effective_clipboard_timeout:
            try:
                current_content = await self.get_clipboard_text()
                # Check if content is not None, not empty, and different from initial state
                if current_content is not None and current_content != initial_clipboard_content:
                    self.logger.info(f"Successfully retrieved new clipboard content (length: {len(current_content)}). Sequence complete.")
                    return current_content
            except ClipboardError as e:
                # Log clipboard errors during polling but continue polling
                self.logger.warning(f"Error reading clipboard during polling: {e}")
                # Consider adding a check here to break if clipboard errors persist?
                
            await asyncio.sleep(0.1) # Poll interval

        # If loop finishes without new content
        self.logger.error("Timeout waiting for clipboard to update with new content.")
        raise InteractionTimeoutError("Clipboard content did not update after copy action within timeout.")

    # --- Screen Capture (Optional Extension) --- #
    async def capture_region(
        self,
        region: Tuple[int, int, int, int], # (left, top, width, height)
        save_path: Optional[str] = None # If provided, saves to file relative to project root or absolute
    ) -> Any: # Returns PIL Image object or path string if saved
        """
        Captures a specified region of the screen.

        Ensures window focus before capture (optional but good practice).

        Args:
            region: Tuple (left, top, width, height) specifying the screen region.
            save_path: Optional file path to save the screenshot. If relative, 
                       it's saved relative to the project root.

        Returns:
            A PIL Image object of the captured region, or the absolute string path 
            to the saved file if save_path was provided.
            
        Raises:
            PyAutoGUIControlError: For underlying pyautogui errors or focus issues.
            WindowNotFoundError: If the target window cannot be focused.
            ValueError: If region is invalid.
            IOError: If saving the file fails.
        """
        self.logger.debug(f"Attempting to capture screen region: {region}")

        # Validate region
        if not (isinstance(region, tuple) and len(region) == 4 and all(isinstance(x, int) for x in region)):
             raise ValueError(f"Invalid region format provided: {region}. Expected (left, top, width, height).")
        if region[2] <= 0 or region[3] <= 0:
            raise ValueError(f"Invalid region dimensions: width and height must be positive. Got {region}")

        # Ensure focus (optional but recommended before screen actions)
        if not await self.ensure_window_focused():
            # Log warning but proceed? Or raise error? Let's raise for consistency.
             raise WindowNotFoundError(f"Target window '{self.target_window_title_pattern}' could not be focused before capture.")

        # Perform capture
        try:
            screenshot = await self._run_blocking_io(
                pyautogui.screenshot,
                region=region
            )
            self.logger.info(f"Successfully captured screen region: {region}")
            
            # Save if path provided
            if save_path:
                save_full_path = Path(save_path)
                if not save_full_path.is_absolute():
                    if self.app_config.paths and self.app_config.paths.project_root:
                         save_full_path = self.app_config.paths.project_root / save_path
                    else:
                         self.logger.warning("Cannot resolve relative save_path: project_root not in AppConfig. Using CWD.")
                         save_full_path = Path.cwd() / save_path
                
                try:
                    # Ensure directory exists
                    save_full_path.parent.mkdir(parents=True, exist_ok=True)
                    # Save the PIL image object returned by screenshot
                    await self._run_blocking_io(screenshot.save, str(save_full_path))
                    self.logger.info(f"Screenshot saved to: {save_full_path}")
                    return str(save_full_path)
                except Exception as e_save:
                    self.logger.error(f"Failed to save screenshot to {save_full_path}: {e_save}", exc_info=True)
                    raise IOError(f"Failed to save screenshot to {save_full_path}: {e_save}") from e_save
            else:
                # Return PIL image object if not saving
                return screenshot

        except pyautogui.FailSafeException as e:
            self.logger.error(f"PyAutoGUI fail-safe triggered during screen capture of region {region}.")
            raise PyAutoGUIActionFailedError(f"Fail-safe triggered during screen capture of {region}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error during screen capture of {region}: {e}", exc_info=True)
            raise PyAutoGUIControlError(f"Unexpected error during screen capture of {region}: {e}") from e

# End of File Ensure Correctness 

</rewritten_file> 