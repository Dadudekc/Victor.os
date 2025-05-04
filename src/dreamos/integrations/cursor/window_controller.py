"""Controller for managing multiple Cursor window instances."""

import logging
import platform
from dataclasses import dataclass
from typing import Dict, List, Optional

# OS-specific imports
if platform.system() == "Windows":
    import win32con
    import win32gui
    import win32process
elif platform.system() == "Darwin":  # macOS
    try:
        from AppKit import (
            NSApplicationActivateIgnoringOtherApps,
            NSRunningApplication,
            NSWorkspace,
        )
    except ImportError:
        raise ImportError("Please install pyobjc-framework-Cocoa for macOS support")
else:  # Linux
    try:
        import Xlib.display
        import Xlib.X
        import Xlib.Xatom
        from Xlib.error import BadWindow, XError
    except ImportError:
        raise ImportError("Please install python-xlib for Linux support")

logger = logging.getLogger(__name__)


@dataclass
class WindowWrapper:
    """Cross-platform window handle wrapper."""

    id: str  # CURSOR-1, CURSOR-2, etc.
    handle: int  # Window handle/id
    title: str
    pid: int
    geometry: Dict[str, int]  # x, y, width, height


class CursorWindowController:
    """Controls multiple Cursor window instances."""

    MAX_INSTANCES = 8

    def __init__(self):
        self.windows: List[WindowWrapper] = []
        self._os_type = platform.system()
        self._display = None
        self._setup_os_specific_handlers()

    def _setup_os_specific_handlers(self):
        """Initialize OS-specific window management."""
        if self._os_type == "Windows":
            self._enum_windows = win32gui.EnumWindows
            self._get_window_text = win32gui.GetWindowText
            self._get_window_rect = win32gui.GetWindowRect
            self._set_foreground = win32gui.SetForegroundWindow
            self._get_window_pid = lambda hwnd: win32process.GetWindowThreadProcessId(
                hwnd
            )[1]
        elif self._os_type == "Darwin":
            self._workspace = NSWorkspace.sharedWorkspace()
        else:  # Linux
            try:
                self._display = Xlib.display.Display()
                self._root = self._display.screen().root
            except Xlib.error.DisplayNameError as e:
                logger.error(
                    f"Failed to connect to X display: {e}. Linux window detection/control disabled."  # noqa: E501
                )
                self._display = None
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred connecting to X display: {e}",
                    exc_info=True,
                )
                self._display = None

    def detect_all_instances(
        self, title_pattern: str = "Cursor"
    ) -> List[WindowWrapper]:
        """Detect all Cursor windows in the system."""
        self.windows.clear()

        if self._os_type == "Windows":

            def enum_callback(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = self._get_window_text(hwnd)
                    if title_pattern.lower() in window_title.lower():
                        rect = self._get_window_rect(hwnd)
                        self.windows.append(
                            WindowWrapper(
                                id=f"CURSOR-{len(self.windows) + 1}",
                                handle=hwnd,
                                title=window_title,
                                pid=self._get_window_pid(hwnd),
                                geometry={
                                    "x": rect[0],
                                    "y": rect[1],
                                    "width": rect[2] - rect[0],
                                    "height": rect[3] - rect[1],
                                },
                            )
                        )

            self._enum_windows(enum_callback, None)

        elif self._os_type == "Darwin":
            # Note: Accessing app.windows() might require special Accessibility or
            #       Automation permissions granted to the running application/terminal
            #       in macOS System Settings -> Privacy & Security.
            running_apps = self._workspace.runningApplications()
            for app in running_apps:
                if title_pattern.lower() in app.localizedName().lower():
                    windows = app.windows()  # Note: May require additional permissions
                    for window in windows:
                        frame = window.frame()
                        self.windows.append(
                            WindowWrapper(
                                id=f"CURSOR-{len(self.windows) + 1}",
                                handle=window.windowNumber(),
                                title=app.localizedName(),
                                pid=app.processIdentifier(),
                                geometry={
                                    "x": int(frame.origin.x),
                                    "y": int(frame.origin.y),
                                    "width": int(frame.size.width),
                                    "height": int(frame.size.height),
                                },
                            )
                        )

        else:  # Linux
            if not self._display:
                logger.warning(
                    "X display not available. Skipping Linux window detection."
                )
                return []

            def get_window_info(window):
                try:
                    geometry = window.get_geometry()
                    wm_name_atom = self._display.intern_atom("WM_NAME")
                    name_prop = window.get_property(
                        wm_name_atom, Xlib.Xatom.STRING, 0, 1024
                    )
                    name = (
                        name_prop.value.decode("utf-8", errors="replace")
                        if name_prop and name_prop.value
                        else None
                    )

                    pid_atom = self._display.intern_atom("_NET_WM_PID")
                    pid_prop = window.get_property(pid_atom, Xlib.Xatom.CARDINAL, 0, 1)
                    pid = pid_prop.value[0] if pid_prop and pid_prop.value else None
                    return name, pid, geometry
                except (XError, BadWindow):
                    # logger.debug(f"XError getting info for window {window.id}: {e}") # Too noisy  # noqa: E501
                    return None, None, None
                except Exception as e:
                    logger.warning(
                        f"Unexpected error getting info for window {window.id}: {e}",
                        exc_info=False,
                    )
                    return None, None, None

            for window in self._root.query_tree().children:
                name, pid, geometry = get_window_info(window)
                if name and title_pattern.lower() in name.lower():
                    self.windows.append(
                        WindowWrapper(
                            id=f"CURSOR-{len(self.windows) + 1}",
                            handle=window.id,
                            title=name,
                            pid=pid,
                            geometry={
                                "x": geometry.x,
                                "y": geometry.y,
                                "width": geometry.width,
                                "height": geometry.height,
                            },
                        )
                    )

        # Limit to MAX_INSTANCES
        self.windows = self.windows[: self.MAX_INSTANCES]
        logger.info(f"Detected {len(self.windows)} Cursor instances")
        return self.windows

    def activate_window(self, window: WindowWrapper) -> bool:
        """Activate and bring a specific window to front."""
        try:
            if self._os_type == "Windows":
                # Restore window if minimized/maximized before activating
                win32gui.ShowWindow(window.handle, win32con.SW_RESTORE)
                self._set_foreground(window.handle)
            elif self._os_type == "Darwin":
                # Ensure NSApplicationActivateIgnoringOtherApps is defined or imported
                # Assuming NSApplicationActivateIgnoringOtherApps = 1 << 0 (from AppKit)
                # NSApplicationActivateIgnoringOtherApps = 1
                app = NSRunningApplication.runningApplicationWithProcessIdentifier_(
                    window.pid
                )
                if app:
                    app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
                else:
                    logger.warning(
                        f"Could not find running application for PID {window.pid} on Darwin."  # noqa: E501
                    )
                    return False  # Indicate failure if app not found
            else:  # Linux
                if not self._display:
                    logger.error("Cannot activate window: X display not available.")
                    return False
                window_obj = self._display.create_resource_object(
                    "window", window.handle
                )
                # More robust activation for Linux: use _NET_ACTIVE_WINDOW EWMH
                active_atom = self._display.intern_atom("_NET_ACTIVE_WINDOW")
                self._root.change_property(
                    active_atom,
                    Xlib.Xatom.WINDOW,
                    32,
                    [window.handle],
                    Xlib.X.PropModeReplace,
                )
                # Raise the window above others
                window_obj.configure(stack_mode=Xlib.X.Above)
                self._display.flush()  # Use flush instead of sync for potentially better responsiveness  # noqa: E501

            logger.info(f"Activated window {window.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to activate window {window.id}: {e}")
            # Specific handling for potential Darwin errors if needed
            # if self._os_type == 'Darwin' and isinstance(e, ...):
            #     logger.error("Detailed Darwin error...")
            return False

    def get_window_by_id(self, cursor_id: str) -> Optional[WindowWrapper]:
        """Get window wrapper by Cursor ID (e.g., 'CURSOR-1')."""
        for window in self.windows:
            if window.id == cursor_id:
                return window
        return None

    def print_window_map(self):
        """Print a formatted map of all detected Cursor windows."""
        if not self.windows:
            print("No Cursor windows detected.")
            return

        print("\n=== Cursor Window Map ===")
        for window in self.windows:
            print(f"\n{window.id}:")
            print(f"  Title: {window.title}")
            print(f"  PID: {window.pid}")
            print(f"  Position: ({window.geometry['x']}, {window.geometry['y']})")
            print(f"  Size: {window.geometry['width']}x{window.geometry['height']}")
        print("\n=======================")

    def close(self):
        """Clean up resources, specifically the X display connection."""
        if self._display and self._os_type == "Linux":
            try:
                self._display.close()
                logger.debug("Closed X display connection.")
            except Exception as e:
                logger.error(f"Error closing X display connection: {e}")
        self._display = None  # Ensure it's cleared
