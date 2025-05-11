#!/usr/bin/env python3
"""
Virtual Desktop Runner
----------------------
Launches a hidden Cursor session on a separate virtual desktop (Windows)
or Xvfb display (Linux), and allows background key‐injection (e.g. injecting ChatGPT replies
into the Cursor chat) without stealing focus from your main desktop.

Usage:
    from virtual_desktop_runner import VirtualDesktopController

    vdc = VirtualDesktopController()
    vdc.launch_cursor_headless(cursor_exe_path="C:/Path/To/Cursor.exe")
    # Now vdc.inject_keystrokes(...) will go to the invisible desktop
    vdc.inject_keystrokes("Hello from the background!")
    vdc.teardown()
"""  # noqa: E501

import os  # Added os import
import platform
import subprocess
import sys
import time

import pyautogui

if platform.system() == "Linux":
    try:  # Added try-except for Linux dependency
        from pyvirtualdisplay import Display
    except ImportError:
        raise ImportError(
            "Please install pyvirtualdisplay: pip install pyvirtualdisplay"
        )
elif platform.system() == "Windows":
    try:
        import pyvda
    except ImportError:
        raise ImportError("Please install pyvda: pip install pyvda")
else:
    raise RuntimeError("Unsupported OS for Virtual Desktop Runner")


class VirtualDesktopController:
    def __init__(self):
        self.os = platform.system()
        self._setup_done = False
        self._display = None  # Initialize _display
        self._process = None  # Initialize _process to hold the subprocess
        self._orig_desktop = None  # Windows specific
        self._new_desktop = None  # Windows specific

    def launch_cursor_headless(self, cursor_exe_path: str, args=None):
        """
        Launch Cursor on a new hidden desktop/display.
        - Windows: creates a new Virtual Desktop (assumed #2), switches to it, then launches Cursor.
        - Linux: starts an Xvfb display and runs Cursor under that DISPLAY.
        """  # noqa: E501
        if self.os == "Linux":
            self._display = Display(visible=0, size=(1920, 1080))
            self._display.start()
            env = dict(**os.environ, DISPLAY=self._display.display)
            self._process = subprocess.Popen([cursor_exe_path] + (args or []), env=env)
            print(
                f"Launched Cursor headless on Linux (PID: {self._process.pid}) under DISPLAY {self._display.display}"  # noqa: E501
            )
            time.sleep(5)

        elif self.os == "Windows":
            print("Setting up virtual desktop for Cursor...")
            try:
                # Attempt Class-based API for current desktop
                self._orig_desktop = pyvda.VirtualDesktop.current().number
                print(f"Original desktop: {self._orig_desktop}")
            except Exception as e:
                print(
                    f"Warning: Could not get current desktop number via VirtualDesktop.current(): {e}. Assuming 1."  # noqa: E501
                )
                self._orig_desktop = 1

            self._new_desktop = self._orig_desktop + 1
            print(f"Targeting desktop number: {self._new_desktop}")
            desktop_created = False

            desktop_count_verified = False
            try:
                # Attempt Class-based API for desktop count
                desktop_count = pyvda.VirtualDesktop.count()
                print(f"System has {desktop_count} desktops.")
                desktop_count_verified = True  # Mark as verified  # noqa: F841
                if self._new_desktop > desktop_count:
                    print(
                        f"Target desktop {self._new_desktop} does not exist. Attempting creation..."  # noqa: E501
                    )
                    try:
                        # Attempt to create the desktop
                        pyvda.create_virtual_desktop()
                        print(
                            f"Attempted to create virtual desktop {self._new_desktop}."
                        )
                        desktop_created = True  # noqa: F841
                        time.sleep(1)  # Pause briefly after creation attempt
                    except AttributeError:
                        print(
                            "Warning: pyvda module has no attribute 'create_virtual_desktop'. Cannot create."  # noqa: E501
                        )
                        raise RuntimeError(
                            f"Target virtual desktop {self._new_desktop} does not exist and cannot be created."  # noqa: E501
                        )
                    except Exception as create_err:
                        print(
                            f"Warning: Error calling create_virtual_desktop(): {create_err}. Cannot guarantee creation."  # noqa: E501
                        )
            except AttributeError:
                # Specifically handle the case where .count() doesn't exist
                print(
                    f"Warning: Could not verify desktop count via VirtualDesktop.count() (AttributeError). Assuming target {self._new_desktop} exists."  # noqa: E501
                )
            except RuntimeError as e:
                print(f"Runtime Error: {e}")
                raise
            except Exception as e_count:  # Catch other errors during count
                # Now 'e_count' is defined in this scope
                print(
                    f"Warning: Could not verify desktop count: {e_count}. Assuming target {self._new_desktop} exists."  # noqa: E501
                )

            try:
                print(f"Switching to desktop: {self._new_desktop}")
                pyvda.VirtualDesktop(self._new_desktop).go()
            except Exception as e:
                print(
                    f"ERROR switching to desktop {self._new_desktop} via VirtualDesktop(n).go(): {e}"  # noqa: E501
                )
                print(
                    f"Launching on original desktop {self._orig_desktop} due to switch failure."  # noqa: E501
                )
                self._new_desktop = (
                    self._orig_desktop
                )  # Keep track of where we actually launch

            print(f"Launching Cursor on virtual desktop {self._new_desktop}")
            try:
                self._process = subprocess.Popen([cursor_exe_path] + (args or []))
                print(
                    f"Launched Cursor (PID: {self._process.pid}) on virtual desktop {self._new_desktop}"  # noqa: E501
                )
                time.sleep(5)
            except Exception as e:
                print(f"ERROR launching Cursor process: {e}")
                if self._new_desktop != self._orig_desktop:
                    try:
                        # Attempt Class-based API for switching back
                        pyvda.VirtualDesktop(self._orig_desktop).go()
                    except Exception as switch_err:
                        print(
                            f"Could not switch back to original desktop {self._orig_desktop} after launch failure: {switch_err}"  # noqa: E501
                        )
                raise

        else:
            raise RuntimeError(f"Unsupported OS: {self.os}")

        self._setup_done = True
        print("Headless Cursor setup complete.")

    def inject_keystrokes(self, text: str, interval: float = 0.01):
        """
        Inject text via pyautogui into the headless Cursor session.
        Must be called after launch_cursor_headless().
        """
        if not self._setup_done:
            raise RuntimeError("Call launch_cursor_headless() first")

        print(
            f"Injecting text to virtual desktop {self._new_desktop if self.os == 'Windows' else 'Xvfb'}: '{text[:50]}...'"  # noqa: E501
        )  # Adjusted log
        # Ensure we are on the correct desktop before injecting (Windows specific precaution)  # noqa: E501
        if self.os == "Windows":
            try:
                # Attempt Class-based API for current desktop
                current_desk = pyvda.VirtualDesktop.current().number
                if current_desk != self._new_desktop:
                    print(
                        f"Warning: Current desktop ({current_desk}) is not the target ({self._new_desktop}). Switching back..."  # noqa: E501
                    )
                    # Attempt Class-based API for switching
                    pyvda.VirtualDesktop(self._new_desktop).go()
                    time.sleep(0.5)
            except Exception as e:
                print(
                    f"Warning: Could not verify/switch current desktop before injection: {e}. Proceeding anyway."  # noqa: E501
                )
        # Send the keystrokes—these go to the active desktop/display
        try:
            pyautogui.write(text, interval=interval)
            pyautogui.press("enter")
            print("Keystrokes injected successfully.")
        except Exception as e:
            print(f"Error during keystroke injection: {e}")
            if self.os == "Windows" and self._orig_desktop is not None:
                print("Attempting to switch back to original desktop due to error...")
                try:
                    # Attempt Class-based API for switching
                    pyvda.VirtualDesktop(self._orig_desktop).go()
                except Exception as switch_err:
                    print(
                        f"Could not switch back to original desktop {self._orig_desktop}: {switch_err}"  # noqa: E501
                    )
            raise  # Re-raise the exception - Ensure this is aligned with the outer try/except  # noqa: E501

    def teardown(self):
        """
        Restore original desktop/display and clean up.
        """
        if not self._setup_done:
            return

        print("Tearing down virtual desktop environment...")
        if self.os == "Linux":
            if self._process:
                print(f"Terminating headless Cursor process (PID: {self._process.pid})")
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)  # Wait for termination
                    print("Cursor process terminated.")
                except subprocess.TimeoutExpired:
                    print("Cursor process did not terminate gracefully, killing.")
                    self._process.kill()
            if self._display:
                print("Stopping Xvfb display...")
                self._display.stop()
                print("Xvfb display stopped.")

        elif self.os == "Windows":
            # Terminate process first (might be on the target desktop)
            if self._process:
                print(
                    f"Terminating Cursor process (PID: {self._process.pid}) (likely on virtual desktop {self._new_desktop})"  # noqa: E501
                )
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                    print("Cursor process terminated.")
                except subprocess.TimeoutExpired:
                    print("Cursor process did not terminate gracefully, killing.")
                    self._process.kill()
            else:
                print("No Cursor process handle found to terminate.")

            # Switch back to the original desktop
            if (
                self._orig_desktop is not None
                and self._new_desktop != self._orig_desktop
            ):
                print(f"Switching back to original desktop: {self._orig_desktop}")
                try:
                    # Attempt Class-based API for switching
                    pyvda.VirtualDesktop(self._orig_desktop).go()
                except Exception as e:
                    print(
                        f"ERROR switching back to original desktop {self._orig_desktop}: {e}"  # noqa: E501
                    )
            elif self._new_desktop == self._orig_desktop:
                print("Was already on original desktop, no switch needed.")
            else:
                print("Original desktop number not recorded, cannot switch back.")

            # Attempt removal ONLY if we ended up on the new desktop AND creation might have occurred  # noqa: E501
            # This is heuristic - might need refinement
            if (
                self._new_desktop is not None
                and self._new_desktop != self._orig_desktop
            ):
                print(f"Attempting removal of virtual desktop: {self._new_desktop}")
                try:
                    # Find the desktop object to remove it (API is unclear for v0.5.0)
                    # desktop_to_remove = pyvda.VirtualDesktop(self._new_desktop)
                    # desktop_to_remove.remove() # Hypothetical API
                    # OR maybe pyvda.remove_virtual_desktop(number=self._new_desktop)?
                    # Since the API is unclear and removal can fail if it's the last desktop,  # noqa: E501
                    # we will skip actual removal for now to avoid errors.
                    print(
                        f"INFO: Automatic removal of desktop {self._new_desktop} skipped (API unclear/potential issues)."  # noqa: E501
                    )
                except Exception as remove_err:
                    print(
                        f"Error attempting removal of desktop {self._new_desktop}: {remove_err}"  # noqa: E501
                    )
            else:
                print(
                    f"Skipping removal of virtual desktop {self._new_desktop} (was original or not targeted)."  # noqa: E501
                )

        self._setup_done = False
        print("Teardown complete.")


# Example usage
if __name__ == "__main__":
    # Check OS and set path accordingly
    if platform.system() == "Windows":
        # Common locations for Cursor on Windows
        possible_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Cursor\Cursor.exe"),
            r"C:\Program Files\Cursor\cursor.exe",
            # Add other potential paths if needed
        ]
        CURSOR_PATH = next(
            (path for path in possible_paths if os.path.exists(path)), None
        )
        if not CURSOR_PATH:
            raise FileNotFoundError(
                "Could not automatically find Cursor.exe. Please set CURSOR_PATH manually."  # noqa: E501
            )
    elif platform.system() == "Linux":
        # Common locations for Cursor on Linux
        possible_paths = [
            "/usr/bin/cursor",
            "/opt/Cursor/cursor",
            os.path.expanduser("~/Applications/Cursor.AppImage"),  # If using AppImage
            # Add other potential paths if needed
        ]
        CURSOR_PATH = next(
            (path for path in possible_paths if os.path.exists(path)), None
        )
        if not CURSOR_PATH:
            raise FileNotFoundError(
                "Could not automatically find cursor executable. Please set CURSOR_PATH manually."  # noqa: E501
            )
    else:
        raise RuntimeError("Unsupported OS for example usage.")

    print(f"Using Cursor path: {CURSOR_PATH}")

    # Check if dependencies are met
    if platform.system() == "Linux":
        try:
            from pyvirtualdisplay import Display
        except ImportError:
            print(
                "Error: pyvirtualdisplay is required on Linux. pip install pyvirtualdisplay"  # noqa: E501
            )
            sys.exit(1)
        if not any(
            os.access(os.path.join(path, "Xvfb"), os.X_OK)
            for path in os.environ["PATH"].split(os.pathsep)
        ):
            print(
                "Error: Xvfb is required on Linux but not found in PATH. Please install it (e.g., sudo apt-get install xvfb)."  # noqa: E501
            )
            sys.exit(1)

    elif platform.system() == "Windows":
        try:
            import pyvda
        except ImportError:
            print("Error: pyvda is required on Windows. pip install pyvda")
            sys.exit(1)

    try:
        import pyautogui
    except ImportError:
        print("Error: pyautogui is required. pip install pyautogui")
        sys.exit(1)

    print("\n--- Starting Virtual Desktop Test ---")
    vdc = VirtualDesktopController()
    try:
        print("Launching Cursor headlessly...")
        vdc.launch_cursor_headless(cursor_exe_path=CURSOR_PATH)

        print("\nWaiting a bit...")
        time.sleep(2)  # Give window time to settle

        print("Injecting first message...")
        vdc.inject_keystrokes("🚀 Hello from the hidden desktop via script!")

        print("\nWaiting...")
        time.sleep(3)

        print("Injecting second message...")
        vdc.inject_keystrokes("This should appear without stealing focus.")

        print("\nWaiting before teardown...")
        time.sleep(3)

    except Exception as e:
        print(f"\n--- An error occurred during the test: {e} ---")
    finally:
        print("\nCleaning up...")
        vdc.teardown()
        print("--- Test Finished ---")
