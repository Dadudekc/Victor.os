"""
Extract the last response from a target window (e.g. Cursor):

1. Move to a prerecorded copy-button coordinate (per-agent).
2. Click (optionally bringing the window to front).
3. Read the clipboard (with Ctrl+C fallback).
4. Save JSON under runtime/cursor_responses/<agent-id>/<timestamp>.json

Exit codes:
  0 = success
  1 = recoverable failure (empty clipboard, window not found)
  2 = missing pyperclip and no fallback
  3 = import or config error
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

import pyautogui  # Mandatory

# Optional imports
try:
    import pygetwindow

    _WINDOW_OK = True
except ImportError:
    pygetwindow = None  # type: ignore
    _WINDOW_OK = False

try:
    import pyperclip

    _CLIP_OK = True
except ImportError:
    pyperclip = None  # type: ignore
    _CLIP_OK = False

# DreamOS helpers (with sys.path fallback)
try:
    from dreamos.utils.gui_utils import (
        get_specific_coordinate,  # noqa: F401
        is_window_focused,
        load_coordinates,
    )
    from dreamos.utils.path_utils import find_project_root
except ImportError:
    _ROOT = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(_ROOT))
    from dreamos.utils.gui_utils import (  # noqa: E402
        is_window_focused,
        load_coordinates,
    )
    from dreamos.utils.path_utils import find_project_root  # noqa: E402

# Config & constants
DEFAULT_COORDS = (
    Path(find_project_root(__file__)) / "runtime/config/cursor_agent_coords.json"
)
DEFAULT_RESP_DIR = Path(find_project_root(__file__)) / "runtime/cursor_responses"
CLICK_PAUSE = (0.10, 0.25)
AFTER_COPY = (0.25, 0.45)
CLIP_RETRIES = 3
CLIP_WAIT = 0.15

log = logging.getLogger("dreamos.extractor")


def _rand_pause(bounds: Tuple[float, float]) -> None:
    time.sleep(random.uniform(*bounds))


def _save_response(text: str, out_dir: Path, meta: Dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    f = out_dir / f"{ts}.json"
    f.write_text(
        json.dumps({"meta": meta, "content": text}, ensure_ascii=False, indent=2)
    )
    return f


def _clipboard_changed(orig: str) -> bool:
    return _CLIP_OK and pyperclip.paste() != orig


def extract_response(
    agent_id: str,
    coords_file: Path,
    target_window: str,
    out_dir: Path | None = None,
) -> None:
    # 1️⃣ Window / focus check
    if _WINDOW_OK and not is_window_focused(target_window):
        wins = pygetwindow.getWindowsWithTitle(target_window)  # type: ignore
        if not wins:
            log.error("Window '%s' not found", target_window)
            sys.exit(1)
        log.warning("Window found but not focused; proceeding anyway")

    # 2️⃣ Load coords
    coords = load_coordinates(coords_file)
    key = f"{agent_id}.copy_button"
    if not coords or key not in coords:
        log.error("Coords for '%s' missing in %s", key, coords_file)
        sys.exit(3)
    x, y = coords[key]

    # 3️⃣ Click
    log.debug("Move to (%d, %d)", x, y)
    pyautogui.moveTo(x, y, duration=random.uniform(0.1, 0.3))
    _rand_pause(CLICK_PAUSE)
    pyautogui.click()
    log.info("Clicked copy button")
    _rand_pause(AFTER_COPY)

    # 4️⃣ Read clipboard / fallback
    orig = pyperclip.paste() if _CLIP_OK else ""
    content = ""
    for i in range(1, CLIP_RETRIES + 1):
        if _CLIP_OK:
            content = pyperclip.paste()
            if content and _clipboard_changed(orig):
                break
        else:
            pyautogui.hotkey("ctrl", "c")
            _rand_pause((CLIP_WAIT, CLIP_WAIT + 0.05))
            content = pyperclip.paste() if _CLIP_OK else ""
            if content:
                break
        log.debug("Empty clipboard on attempt %d/%d", i, CLIP_RETRIES)
        _rand_pause((CLIP_WAIT, CLIP_WAIT + 0.05))

    if not content:
        log.error("Clipboard empty after %d retries", CLIP_RETRIES)
        sys.exit(1)

    # 5️⃣ Persist
    save_dir = out_dir or (DEFAULT_RESP_DIR / agent_id)
    meta = {
        "agent": agent_id,
        "window": target_window,
        "copied_at": datetime.now(tz=timezone.utc).isoformat(),
        "length": len(content),
    }
    out_path = _save_response(content, save_dir, meta)
    log.info("Saved response → %s", out_path)
    print("OK")
    sys.exit(0)


def cli() -> None:
    p = argparse.ArgumentParser(prog="extract_cursor_response")
    p.add_argument("--agent-id", required=True)
    p.add_argument("--target-window-title", required=True)
    p.add_argument("--coords-file", type=Path, default=DEFAULT_COORDS)
    p.add_argument(
        "--output-dir",
        type=Path,
        help="Custom dir for responses (default runtime path)",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    args = p.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-8s %(message)s",
    )
    if not _CLIP_OK:
        log.critical("pyperclip missing; no clipboard fallback.")
        sys.exit(2)

    try:
        extract_response(
            agent_id=args.agent_id,
            coords_file=args.coords_file,
            target_window=args.target_window_title,
            out_dir=args.output_dir,
        )
    except pyautogui.FailSafeException:
        log.critical("PyAutoGUI fail‑safe triggered; aborting.")
        sys.exit(1)
    except Exception:
        log.exception("Unhandled exception")
        sys.exit(1)


if __name__ == "__main__":
    cli()
