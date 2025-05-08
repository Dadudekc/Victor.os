#!/usr/bin/env python3
"""
Interactive tool to capture GUI regions as PNGs.
Fixes:
• Works on all OSes / PyAutoGUI versions (tuple vs. Point bug).
• Guards against zero‑size / negative regions.
• Adds global FAILSAFE & hot‑key abort (Ctrl‑C still ends cleanly).
• Sanitises custom names, prevents empty names.
"""
import time
import re
from pathlib import Path
from datetime import datetime

import pyautogui

pyautogui.FAILSAFE = True  # ⛑️ moving mouse to top‑left aborts script

PRESET_NAMES = [
    "cursor_input_field",
    "cursor_chat_box",
    "cursor_code_area",
    "cursor_sidebar",
    "cursor_tab_header",
    "custom_manual_entry",
]


# ────────────────────────── helpers ──────────────────────────
def get_coordinates(prompt_msg: str) -> tuple[int, int] | None:
    """
    Prompts the user to position the mouse cursor and captures its coordinates.

    Includes a 3-second countdown before capturing. Handles pyautogui.FailSafeException
    and other exceptions during capture.

    Args:
        prompt_msg: The message to display to the user before starting the countdown.

    Returns:
        A tuple (x, y) of the cursor coordinates, or None if capture fails.
    """
    input(f"\n{prompt_msg}\nPress <Enter> when ready…")
    try:
        print("Move cursor to spot. Capturing in:")
        for i in range(3, 0, -1):
            print(f"{i} ", end="\r", flush=True)
            time.sleep(1)
        x, y = pyautogui.position()  # works for Point *or* tuple
        print(f"✅ Captured: ({x}, {y})            ")
        return x, y
    except Exception as e:  # pragma: no cover
        print(f"❌ Capture error: {e}")
        return None


def sanitize(name: str) -> str:
    """
    Cleans a string to be suitable for use as a filename.

    Replaces characters not in [a-zA-Z0-9_.-] with underscores.
    If the cleaned name is empty, defaults to "snippet".

    Args:
        name: The input string to sanitize.

    Returns:
        The sanitized string.
    """
    cleaned = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", name)
    return cleaned or "snippet"


def confirm(msg: str) -> bool:
    """
    Prompts the user for a yes/no confirmation.

    Loops until 'y', 'yes', 'n', or 'no' is entered.

    Args:
        msg: The confirmation message to display.

    Returns:
        True if the user confirms (yes), False otherwise (no).
    """
    while True:
        ans = input(f"{msg} (y/n): ").strip().lower()
        if ans in {"y", "yes"}:
            return True
        if ans in {"n", "no"}:
            return False
        print("Enter y or n.")


def choose_preset() -> str:
    """
    Allows the user to select a snippet name from a predefined list or enter a custom name.

    If "custom_manual_entry" is chosen, prompts for a custom name which is then sanitized.

    Returns:
        The chosen (and potentially sanitized) snippet name.
    """
    print("\n📌 Select snippet type:")
    for idx, name in enumerate(PRESET_NAMES, 1):
        print(f" {idx}. {name}")
    while True:
        sel = input("Number: ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(PRESET_NAMES):
            choice = PRESET_NAMES[int(sel) - 1]
            if choice == "custom_manual_entry":
                return sanitize(input("Custom name: ").strip())
            return choice
        print("❌ Invalid selection.")


# ────────────────────────── main logic ──────────────────────────
def capture_snippet(save_dir: Path) -> None:
    """
    Manages the process of capturing a GUI snippet.

    Guides the user to select top-left and bottom-right corners of a region,
    validates the region, confirms saving, and saves the screenshot.

    Args:
        save_dir: The directory where the snippet PNG file should be saved.
    """
    print("\n─── GUI Snippet Capture ───")
    region_name = choose_preset()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = save_dir / f"{region_name}_{ts}.png"

    tl = None
    while tl is None:
        tl = get_coordinates("Top‑LEFT corner")

    br = None
    while br is None:
        br = get_coordinates("Bottom‑RIGHT corner")

    x1, y1 = tl
    x2, y2 = br
    if x1 >= x2 or y1 >= y2:
        print("❌ Invalid region: top‑left must be above/left of bottom‑right.")
        return

    region = (x1, y1, x2 - x1, y2 - y1)
    print(f"📐 Region = {region}")

    if confirm(f"Save screenshot to {file_path}?"):
        try:
            shot = pyautogui.screenshot(region=region)
            shot.save(file_path)
            print(f"✅ Saved → {file_path}")
        except Exception as e:  # pragma: no cover
            print(f"❌ Save failed: {e}")
    else:
        print("🛑 Save cancelled.")


def main() -> None:
    """
    Main function to run the GUI snippet capture tool.

    Sets up the default save directory and runs the capture loop
    until the user chooses to stop. Handles KeyboardInterrupt.
    """
    default_dir = Path("runtime/assets/cursor_gui_snippets")
    default_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output dir: {default_dir.resolve()}")

    try:
        while True:
            capture_snippet(default_dir)
            if not confirm("Capture another?"):
                break
    except KeyboardInterrupt:
        print("\n⏹️ Stopped by user.")
    finally:
        print("👋 Done.")


if __name__ == "__main__":
    main()
