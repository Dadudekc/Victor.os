"""Module to launch, detect, and manage a swarm of Cursor instances."""

import logging
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional

# Attempt to import pyvda for virtual desktop management (optional)
try:
    import pyvda

    _pyvda_available = True
except ImportError:
    pyvda = None
    _pyvda_available = False

# Import the existing window controller
# Adjust path if necessary based on final project structure
try:
    from integrations.cursor.window_controller import (
        CursorWindowController,
        WindowWrapper,
    )
except ImportError as e:
    # Add fallback or raise critical error if controller is essential
    logging.critical(
        f"Failed to import CursorWindowController: {e}. SwarmBootloader cannot function."  # noqa: E501
    )

    # Define dummy classes if needed for type hinting downstream, though raising is better  # noqa: E501
    class WindowWrapper:
        pass

    class CursorWindowController:
        def detect_all_instances(self, *args, **kwargs):
            return []

    # Re-raise the error to prevent silent failure
    raise ImportError(
        f"Could not import CursorWindowController for SwarmBootloader: {e}"
    ) from e

logger = logging.getLogger(__name__)


class TheaSwarmBootloader:
    """Handles launching and preparing a swarm of Cursor instances."""

    # TODO: Consider moving these default paths to a configuration file
    DEFAULT_CURSOR_PATH_WIN = (
        "C:/Users/Default/AppData/Local/Programs/cursor/Cursor.exe"  # Example path
    )
    DEFAULT_CURSOR_PATH_MAC = "/Applications/Cursor.app"  # Example path
    DEFAULT_CURSOR_CMD_LINUX = "cursor"  # Assumes in PATH

    def __init__(
        self,
        cursor_executable_path: Optional[str] = None,
        window_controller: Optional[CursorWindowController] = None,
    ):
        """
        Initializes the bootloader.

        Args:
            cursor_executable_path (Optional[str]): Path to the Cursor executable or command.
                                                     If None, attempts OS-specific defaults.
            window_controller (Optional[CursorWindowController]): An instance to use for detection.
                                                                   If None, creates a new one.
        """  # noqa: E501
        self.cursor_path = self._resolve_cursor_path(cursor_executable_path)
        self.controller = window_controller or CursorWindowController()
        logger.info(f"TheaSwarmBootloader initialized. Cursor path: {self.cursor_path}")

    def _resolve_cursor_path(self, provided_path: Optional[str]) -> str:
        """Determines the path/command for the Cursor executable."""
        if provided_path:
            # Check if the provided path is an existing file/directory OR a command found in PATH  # noqa: E501
            if Path(provided_path).exists() or shutil.which(provided_path):
                logger.debug(f"Using provided Cursor path/command: {provided_path}")
                return provided_path
            else:
                logger.warning(
                    f"Provided Cursor path '{provided_path}' not found or not executable. Falling back to defaults."  # noqa: E501
                )

        # If no valid path provided, try defaults and PATH lookups
        os_type = platform.system()
        if os_type == "Windows":
            default_path = self.DEFAULT_CURSOR_PATH_WIN
            if Path(default_path).exists():
                logger.debug(f"Using default Windows Cursor path: {default_path}")
                return default_path
            else:
                logger.debug(
                    f"Default Windows Cursor path not found: {default_path}. Checking PATH for 'cursor'."  # noqa: E501
                )
                cursor_cmd = shutil.which("cursor")
                if cursor_cmd:
                    logger.debug("Using 'cursor' command found in PATH (Windows).")
                    return cursor_cmd
                else:
                    raise FileNotFoundError(
                        "Cannot find Cursor executable. Please provide a valid path or ensure the default exists or 'cursor' is in PATH."  # noqa: E501
                    )
        elif os_type == "Darwin":
            # On macOS, we typically launch via 'open -a', so check the .app path
            app_path = self.DEFAULT_CURSOR_PATH_MAC
            if Path(app_path).exists():
                logger.debug(
                    f"Using default macOS Cursor path for 'open -a': {app_path}"
                )
                return app_path  # Store path, but launch uses 'open -a'
            else:
                # Also check if 'cursor' command exists in PATH as a fallback
                cursor_cmd = shutil.which("cursor")
                if cursor_cmd:
                    logger.debug("Using 'cursor' command found in PATH (macOS).")
                    return cursor_cmd
                else:
                    raise FileNotFoundError(
                        "Cannot find Cursor.app at default location or 'cursor' command in PATH. Please provide path."  # noqa: E501
                    )
        else:  # Linux
            cursor_cmd = shutil.which(self.DEFAULT_CURSOR_CMD_LINUX)
            if cursor_cmd:
                logger.debug(
                    f"Using default Linux command '{self.DEFAULT_CURSOR_CMD_LINUX}' found in PATH."  # noqa: E501
                )
                return cursor_cmd
            else:
                # Allow providing a full path even on Linux
                if provided_path and Path(provided_path).exists():
                    logger.debug(f"Using provided path on Linux: {provided_path}")
                    return provided_path
                raise FileNotFoundError(
                    f"Cannot find '{self.DEFAULT_CURSOR_CMD_LINUX}' command in PATH. Please provide a path or ensure it's in PATH."  # noqa: E501
                )

    def launch_instances(self, count: int = 1) -> List[subprocess.Popen]:
        """Launches the specified number of Cursor instances."""
        launched_processes = []
        if not self.cursor_path:
            logger.error("Cursor path is not set. Cannot launch instances.")
            return []

        logger.info(f"Launching {count} Cursor instance(s)...")
        os_type = platform.system()

        for i in range(count):
            try:
                cmd = []
                if os_type == "Darwin":
                    # Use 'open -na' to launch new instance of application
                    cmd = ["open", "-na", self.cursor_path]
                else:
                    # Windows/Linux: directly execute path/command
                    cmd = [self.cursor_path]

                # Use Popen for non-blocking launch
                # Redirect stdout/stderr to prevent console spam (optional)
                process = subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                logger.debug(f"Launched instance {i+1}/{count} (PID: {process.pid})")
                launched_processes.append(process)
                # Optional brief delay between launches if needed
                time.sleep(0.5)
            except FileNotFoundError:
                logger.error(
                    f"Failed to launch instance {i+1}: Executable not found at {self.cursor_path}"  # noqa: E501
                )
                # Optionally stop launching more
                break
            except Exception as e:
                logger.error(f"Failed to launch instance {i+1}: {e}", exc_info=True)
                # Optionally stop launching more
                break
        logger.info(
            f"Launched {len(launched_processes)} process(es). Check system for windows."
        )
        return launched_processes

    def wait_for_detection(
        self, expected_count: int, timeout: int = 30, poll_interval: float = 1.0
    ) -> bool:
        """Waits until the specified number of Cursor windows are detected."""
        logger.info(
            f"Waiting up to {timeout}s for {expected_count} Cursor window(s) to be detected..."  # noqa: E501
        )
        start_time = time.time()
        while time.time() - start_time < timeout:
            detected_windows = (
                self.controller.detect_all_instances()
            )  # Use the controller
            if len(detected_windows) >= expected_count:
                logger.info(
                    f"Successfully detected {len(detected_windows)} Cursor window(s)."
                )
                return True
            logger.debug(
                f"Waiting... detected {len(detected_windows)}/{expected_count} windows."
            )
            time.sleep(poll_interval)

        logger.warning(
            f"Timeout: Only detected {len(self.controller.windows)}/{expected_count} Cursor window(s) after {timeout}s."  # noqa: E501
        )
        return False

    def move_windows_to_desktop(self, desktop_index: int = 1) -> int:
        """Moves all detected Cursor windows to the specified virtual desktop (Windows only).

        Args:
            desktop_index (int): The target virtual desktop number (usually 1-based).
                                   Note: pyvda.MoveWindowToDesktopNumber seems to expect 1-based index.
                                         Verification might be needed depending on pyvda version.

        Returns:
            int: The number of windows successfully moved.
        """  # noqa: E501
        if platform.system() != "Windows":
            logger.warning(
                "Virtual desktop management via pyvda is only supported on Windows."
            )
            return 0

        if not _pyvda_available:
            logger.warning(
                "pyvda library not installed. Cannot move windows to virtual desktop."
            )
            return 0

        if not self.controller.windows:
            logger.warning("No Cursor windows detected to move.")
            return 0

        moved_count = 0
        target_desktop_num = desktop_index  # pyvda seems to use 1-based for target
        logger.info(
            f"Attempting to move {len(self.controller.windows)} windows to Virtual Desktop {target_desktop_num}..."  # noqa: E501
        )

        # Ensure target desktop exists (pyvda provides GetDesktopCount)
        try:
            desktop_count = pyvda.GetDesktopCount()
            if target_desktop_num > desktop_count:
                logger.warning(
                    f"Target desktop {target_desktop_num} does not exist (only {desktop_count} desktops found). Moving to last desktop."  # noqa: E501
                )
                target_desktop_num = desktop_count  # Adjust to last valid desktop
        except Exception as e:
            logger.error(
                f"Failed to get desktop count via pyvda: {e}. Cannot verify target desktop."  # noqa: E501
            )
            # Proceed with caution or return error?
            # return 0

        for window in self.controller.windows:
            try:
                hwnd = window.handle
                pyvda.MoveWindowToDesktopNumber(hwnd, target_desktop_num)
                logger.debug(
                    f"Moved window {window.id} (HWND: {hwnd}) to Desktop {target_desktop_num}."  # noqa: E501
                )
                moved_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to move window {window.id} (HWND: {window.handle}) to Desktop {target_desktop_num}: {e}",  # noqa: E501
                    exc_info=False,
                )  # Keep log cleaner

        logger.info(
            f"Successfully moved {moved_count}/{len(self.controller.windows)} windows to Virtual Desktop {target_desktop_num}."  # noqa: E501
        )
        return moved_count

    def setup_swarm(
        self,
        count: int = 8,
        wait_timeout: int = 30,
        move_to_desktop: Optional[int] = None,
    ) -> List[WindowWrapper]:
        """Launches, waits for, and optionally moves Cursor instances.

        Args:
            count (int): Number of instances to launch.
            wait_timeout (int): Max seconds to wait for windows to be detected.
            move_to_desktop (Optional[int]): If set, move detected windows to this
                                             virtual desktop number (Windows only).

        Returns:
            List[WindowWrapper]: List of detected and potentially moved Cursor windows.
        """
        logger.info(f"--- Setting up Cursor Swarm (Count: {count}) ---")
        # 1. Launch Instances
        self.launch_instances(count=count)

        # 2. Wait for Detection
        if not self.wait_for_detection(expected_count=count, timeout=wait_timeout):
            logger.warning(
                "Detection timeout/failure. Proceeding with detected windows, if any."
            )

        # 3. (Optional) Move to Virtual Desktop
        if move_to_desktop is not None:
            self.move_windows_to_desktop(desktop_index=move_to_desktop)

        # 4. Return detected windows
        detected_windows = self.controller.windows
        logger.info(
            f"--- Cursor Swarm Setup Complete ({len(detected_windows)} detected) ---"
        )
        self.controller.print_window_map()  # Print map for user verification
        return detected_windows


# Example Usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Running TheaSwarmBootloader Example...")

    # --- Configuration for Example ---
    NUM_INSTANCES = 2  # Launch fewer for testing
    TARGET_DESKTOP = 2  # Move to Desktop 2 (if on Windows and pyvda installed)
    CURSOR_EXE_PATH = None  # Set to your actual path if default detection fails
    # e.g., CURSOR_EXE_PATH = "C:/path/to/your/Cursor.exe"

    try:
        bootloader = TheaSwarmBootloader(cursor_executable_path=CURSOR_EXE_PATH)

        # Run the full setup process
        final_windows = bootloader.setup_swarm(
            count=NUM_INSTANCES,
            wait_timeout=20,  # Shorter timeout for example
            move_to_desktop=TARGET_DESKTOP if platform.system() == "Windows" else None,
        )

        if final_windows:
            logger.info(
                f"Bootloader finished. {len(final_windows)} Cursor instances are ready."
            )
            # Add code here to assign tasks to these windows using the controller
            # e.g., activate window 1, send prompt via another mechanism, etc.
            if len(final_windows) > 0:
                first_window_id = final_windows[0].id
                logger.info(
                    f"Attempting to activate first detected window: {first_window_id}"
                )
                success = bootloader.controller.activate_window(final_windows[0])
                logger.info(f"Activation successful: {success}")
        else:
            logger.warning(
                "Bootloader finished, but no Cursor instances were successfully detected."  # noqa: E501
            )

    except FileNotFoundError as e:
        logger.critical(
            f"CRITICAL ERROR: {e}. Could not find Cursor. Please check path configuration."  # noqa: E501
        )
    except ImportError as e:
        logger.critical(
            f"CRITICAL ERROR: {e}. Missing required dependency (e.g., pywin32, pyobjc-framework-Cocoa, python-xlib, pyvda)?"  # noqa: E501
        )
    except Exception as e:
        logger.critical(
            f"An unexpected error occurred during bootloader execution: {e}",
            exc_info=True,
        )

    logger.info("Bootloader Example Finished.")
