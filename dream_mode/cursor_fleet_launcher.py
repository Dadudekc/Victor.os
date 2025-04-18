# tools/cursor_fleet_launcher.py

import subprocess
import time
import os
import win32gui
import win32con
import pygetwindow as gw
from screeninfo import get_monitors

CURSOR_PATHS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Cursor\Cursor.exe"),
    r"C:\Program Files\Cursor\Cursor.exe", # Note: Escaped backslashes for Python string
]
CURSOR_PATH = next((p for p in CURSOR_PATHS if os.path.exists(p)), None)

if not CURSOR_PATH:
    raise FileNotFoundError("❌ Cursor.exe not found. Please adjust CURSOR_PATH.")

def launch_cursor_instance(index):
    print(f"🚀 Launching Cursor instance #{index+1}")
    # Ensure the path is correctly formatted for subprocess
    return subprocess.Popen([CURSOR_PATH])

def move_window(hwnd, x, y, width, height):
    # Restore window before moving/resizing to ensure it's not minimized/maximized
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.MoveWindow(hwnd, x, y, width, height, True)

def get_cursor_windows(target_count=8, timeout=30):
    print(f"🔍 Waiting for {target_count} Cursor windows to appear (timeout: {timeout}s)...")
    start_time = time.time()
    found_windows = {}

    while time.time() - start_time < timeout:
        # Use lower case for case-insensitive comparison
        current_windows = {w._hWnd: w for w in gw.getWindowsWithTitle("cursor") if w.title and "cursor" in w.title.lower()}

        # Add newly found windows, avoiding duplicates based on HWND
        for hwnd, window in current_windows.items():
            if hwnd not in found_windows:
                found_windows[hwnd] = window
                print(f"  [*] Found window: {window.title} (HWND: {hwnd}) - Total: {len(found_windows)}")

        if len(found_windows) >= target_count:
            print(f"✅ Found {len(found_windows)} Cursor windows.")
            # Return a list of window objects
            return list(found_windows.values())[:target_count]

        time.sleep(0.5) # Check less frequently

    # Timeout handling
    if len(found_windows) > 0:
        print(f"⚠️ Timed out, but found {len(found_windows)} windows. Proceeding with available ones.")
        return list(found_windows.values())
    else:
        raise TimeoutError(f"⌛ Timed out waiting for at least one Cursor window after {timeout} seconds.")

def assign_windows_to_monitors(cursor_windows):
    monitors = get_monitors()
    if len(monitors) < 2:
        print(f"⚠️ Warning: Found {len(monitors)} monitor(s). At least 2 are recommended for the intended layout.")
        if not monitors:
             raise RuntimeError("❌ No monitors detected. Cannot position windows.")
        # Fallback: Use only the primary monitor if less than 2 detected
        monitors = monitors * 2 # Duplicate monitor info to fill positions

    print(f"📺 Detected monitors: {[f'Monitor {i+1}: {m.width}x{m.height} @ ({m.x},{m.y})' for i, m in enumerate(monitors)]}")

    positions = []
    # Define positions for up to 8 windows across the first two monitors
    for monitor_index, m in enumerate(monitors[:2]): # Limit to first two monitors
        quad_width = m.width // 2
        quad_height = m.height // 2
        base_x, base_y = m.x, m.y

        # Define the 4 quadrants for this monitor
        positions.extend([
            (base_x, base_y, quad_width, quad_height),                     # Top-left
            (base_x + quad_width, base_y, quad_width, quad_height),       # Top-right
            (base_x, base_y + quad_height, quad_width, quad_height),     # Bottom-left
            (base_x + quad_width, base_y + quad_height, quad_width, quad_height), # Bottom-right
        ])

    print(f"🪟 Assigning {len(cursor_windows)} windows to {len(positions)} calculated positions...")

    assigned_count = 0
    for i, win in enumerate(cursor_windows):
        if i >= len(positions):
            print(f"  [!] No position available for window {i+1} ('{win.title}').")
            continue

        x, y, w, h = positions[i]
        try:
            # Ensure HWND is valid before attempting to move
            if win32gui.IsWindow(win._hWnd):
                move_window(win._hWnd, x, y, w, h)
                print(f"  [->] Moved: '{win.title}' (HWND: {win._hWnd}) -> Monitor { (i // 4) + 1 } Quadrant { (i % 4) + 1} @ ({x},{y}) {w}x{h}")
                assigned_count += 1
            else:
                print(f"  [!] Window {i+1} (HWND: {win._hWnd}, Title: '{win.title}') is no longer valid. Skipping.")
        except Exception as e:
             print(f"  [!] Error moving window {i+1} (HWND: {win._hWnd}, Title: '{win.title}'): {e}")

    print(f"✅ Finished assigning positions to {assigned_count} windows.")

def main():
    num_instances = 8 # Target number of instances
    processes = []
    print(f"--- Cursor Fleet Launcher ---")
    print(f"Attempting to launch {num_instances} Cursor instances...")

    for i in range(num_instances):
        try:
            p = launch_cursor_instance(i)
            processes.append(p)
            time.sleep(0.5) # Stagger launches slightly
        except Exception as e:
            print(f"❌ Failed to launch instance #{i+1}: {e}")
            # Optionally decide whether to continue or stop
            # return

    print(f"Launched {len(processes)} processes. Allowing time for windows to open...")
    # Increased sleep time to allow windows to fully initialize
    initial_wait = 10 # seconds
    print(f"⏳ Waiting {initial_wait} seconds before searching for windows...")
    time.sleep(initial_wait)

    try:
        windows = get_cursor_windows(target_count=len(processes), timeout=45) # Adjust timeout as needed
        if windows:
            assign_windows_to_monitors(windows)
        else:
            print("🤷 No Cursor windows found to position.")
    except (TimeoutError, RuntimeError, Exception) as e:
        print(f"❌ An error occurred during window detection or positioning: {e}")

    print("--- Launch sequence complete ---")
    # Keep the script running to keep processes alive? Or handle termination?
    # For now, the script exits, but the Cursor processes remain.
    # print("Press Enter to terminate launched Cursor processes...")
    # input()
    # for p in processes:
    #     p.terminate()

if __name__ == "__main__":
    # Check for dependencies
    try:
        import pygetwindow
        import win32gui
        import win32con
        import screeninfo
    except ImportError as e:
        print(f"❌ Missing dependency: {e.name}")
        print("Please install required packages:")
        print("pip install pygetwindow pywin32 screeninfo")
    else:
        main() 