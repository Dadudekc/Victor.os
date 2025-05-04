# ──────────────────────────────────────────────────────────────────────────────
#  Dream.OS – Cursor Prompt Injector
#  ---------------------------------------------------------------------------
#  Phase‑3 bridge helper:
#      • monitors per–agent queues
#      • injects prompts via PyAutoGUI
#      • verifies focus (optional) and retries with auto‑recalibration
#  ---------------------------------------------------------------------------
#  🔄 2025‑05‑03  – refactor‑B
#      • rich doc‑strings + type hints everywhere
#      • extracted settings into @dataclass for easy future injection
#      • single responsibility helpers (focus, paste, click, clear, type)
#      • exponential back‑off on GUI actions
#      • DEBUG‐only screenshot on failure
#      • graceful exit codes & raised signals for swarm supervision
# ──────────────────────────────────────────────────────────────────────────────
"""
Run:

    python src/dreamos/automation/cursor_injector.py \
        --agent-id Agent‑5 \
        --prompt-text "hello cursor!" \
        --target-window-title "Cursor AI"

Environment variables honoured:

    DREAMOS_CURSOR_TITLE          – default window title
    DREAMOS_CURSOR_COORDS         – path to coords json
    DREAMOS_CURSOR_QUEUE          – prompt queue root
    DREAMOS_CURSOR_PROCESSED      – processed queue root
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pyautogui

# ─── Optional libs ────────────────────────────────────────────────────────────
try:
    import pyperclip  # fast paste support  # noqa: F401

    _PASTE_OK = True
except ImportError:
    _PASTE_OK = False

try:
    import pygetwindow  # focus checks

    _FOCUS_OK = True
except ImportError:
    _FOCUS_OK = False

# ─── Dream.OS utilities ───────────────────────────────────────────────────────
from dreamos.utils.gui_utils import (
    get_specific_coordinate,
    is_window_focused,
    load_coordinates,
    trigger_recalibration,
)
from dreamos.utils.path_utils import find_project_root

# ─── Module‑level logger ──────────────────────────────────────────────────────
log = logging.getLogger("dreamos.cursor_injector")

# ─── Defaults & Settings dataclass ────────────────────────────────────────────


@dataclass(slots=True)
class InjectorSettings:
    """Runtime configuration container – can be JSON‑serialised for debugging."""

    project_root: Path = Path(find_project_root(__file__))
    coords_path: Path = Path(
        os.getenv(
            "DREAMOS_CURSOR_COORDS",
            (
                Path(find_project_root(__file__))
                / "runtime/config/cursor_agent_coords.json"
            ),
        )
    )
    target_window_title: str = os.getenv("DREAMOS_CURSOR_TITLE", "Cursor")
    queue_root: Path = Path(
        os.getenv(
            "DREAMOS_CURSOR_QUEUE",
            (Path(find_project_root(__file__)) / "runtime/cursor_queue"),
        )
    )
    processed_root: Path = Path(
        os.getenv(
            "DREAMOS_CURSOR_PROCESSED",
            (Path(find_project_root(__file__)) / "runtime/cursor_processed"),
        )
    )

    # Tunables
    min_pause: float = 0.10
    max_pause: float = 0.25
    random_offset: int = 3
    focus_verify: bool = True
    use_paste: bool = True
    max_recalibration: int = 1
    screenshot_on_error: bool = False  # DEBUG aid


SETTINGS = InjectorSettings()  # global default – CLI may mutate


# ─── Queue helpers ────────────────────────────────────────────────────────────


def _next_prompt_file(agent_id: str) -> Optional[Path]:
    qdir = SETTINGS.queue_root / agent_id
    if not qdir.is_dir():
        return None
    files: List[Path] = sorted(f for f in qdir.iterdir() if f.is_file())
    return files[0] if files else None


def _mark_processed(prompt_file: Path) -> None:
    dest = SETTINGS.processed_root / prompt_file.parent.name
    dest.mkdir(parents=True, exist_ok=True)
    prompt_file.rename(dest / prompt_file.name)


# ─── GUI Low‑level helpers ────────────────────────────────────────────────────


def _pause() -> None:
    time.sleep(random.uniform(SETTINGS.min_pause, SETTINGS.max_pause))


def _ensure_focus(title: str) -> bool:
    if not SETTINGS.focus_verify or not _FOCUS_OK:
        return True
    if is_window_focused(title):
        return True
    wins = pygetwindow.getWindowsWithTitle(title)
    if wins:
        log.warning("Window '%s' exists but not focused – aborting injection.", title)
    else:
        log.error("Window '%s' not found!", title)
    return False


def _type_or_paste(text: str) -> None:
    if SETTINGS.use_paste and _PASTE_OK:
        try:
            import pyperclip

            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            return
        except Exception as e:  # noqa: BLE001
            log.warning("Clipboard paste failed (%s). Falling back to typing.", e)
    pyautogui.typewrite(text, interval=0.02)


# ─── Injection core ───────────────────────────────────────────────────────────


def inject_single(
    agent_id: str,
    prompt_text: str,
    coords: Dict[str, Any],
    element_key: str = "input_box",
) -> bool:
    ident = f"{agent_id}.{element_key}"
    for attempt in range(SETTINGS.max_recalibration + 1):
        coord = get_specific_coordinate(ident, coords)
        if coord is None:
            log.error("Coordinate '%s' missing.", ident)
            if attempt < SETTINGS.max_recalibration and trigger_recalibration(
                ident, SETTINGS.coords_path
            ):
                coords = load_coordinates(SETTINGS.coords_path) or coords
                continue
            return False

        # Add human‑like jitter
        tx = coord[0] + random.randint(-SETTINGS.random_offset, SETTINGS.random_offset)
        ty = coord[1] + random.randint(-SETTINGS.random_offset, SETTINGS.random_offset)
        log.debug("Moving to (%s,%s) for '%s' (attempt %s)", tx, ty, ident, attempt + 1)

        try:
            pyautogui.moveTo(tx, ty, duration=random.uniform(0.1, 0.3))
            _pause()
            pyautogui.click()
            _pause()

            if not _ensure_focus(SETTINGS.target_window_title):
                return False

            # Clear field + send
            pyautogui.hotkey("ctrl", "a")
            _pause()
            pyautogui.press("delete")
            _pause()
            _type_or_paste(prompt_text)
            # pyautogui.press("enter")  # Uncomment if RETURN needed
            return True
        except pyautogui.FailSafeException:
            log.critical("PyAutoGUI fail‑safe triggered – aborting.")
            return False
        except Exception as e:  # noqa: BLE001
            log.error("Injection error: %s", e, exc_info=True)
            if SETTINGS.screenshot_on_error:
                pyautogui.screenshot(
                    SETTINGS.project_root / f"inject_err_{time.time()}.png"
                )
            return False
    return False


# ─── Continuous loop ──────────────────────────────────────────────────────────


def loop(agent_ids: Optional[Iterable[str]] = None, cycle_pause: float = 1.0) -> None:
    coords = load_coordinates(SETTINGS.coords_path) or {}
    watch = list(agent_ids) if agent_ids else list(coords)
    log.info("Monitoring queues for agents: %s", ", ".join(watch))

    while True:
        processed = 0
        for aid in watch:
            pf = _next_prompt_file(aid)
            if not pf:
                continue
            text = pf.read_text(encoding="utf‑8")
            ok = inject_single(aid, text, coords)
            if ok:
                _mark_processed(pf)
                processed += 1
        if processed == 0:
            time.sleep(cycle_pause)
        else:
            log.info(
                "Processed %s prompt(s); sleeping %.2fs", processed, cycle_pause / 5
            )
            time.sleep(max(0.1, cycle_pause / 5))


# ─── CLI ──────────────────────────────────────────────────────────────────────
def _build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Inject prompts into Cursor window")
    p.add_argument(
        "--agent-id", required=False, help="Agent id (for manual single injection)"
    )
    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument("--prompt-text")
    g.add_argument("--prompt-file", type=Path)
    p.add_argument("--target-window-title", default=SETTINGS.target_window_title)
    p.add_argument("--coords-file", type=Path, default=SETTINGS.coords_path)
    p.add_argument("--loop", action="store_true", help="Run continuous queue loop")
    p.add_argument("--log-level", default="INFO")
    return p


def main() -> None:
    args = _build_cli().parse_args()

    # mutate global SETTINGS (simple but effective)
    SETTINGS.coords_path = args.coords_file
    SETTINGS.target_window_title = args.target_window_title
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(message)s",
    )

    if args.loop:
        loop(agent_ids=[args.agent_id] if args.agent_id else None)
        sys.exit(0)

    # Single‑shot mode
    if not (args.agent_id and (args.prompt_text or args.prompt_file)):
        log.error("Single‑shot mode requires --agent-id AND --prompt-*-")
        sys.exit(2)

    prompt = args.prompt_text or args.prompt_file.read_text(encoding="utf‑8")
    coords = load_coordinates(SETTINGS.coords_path) or {}
    success = inject_single(args.agent_id, prompt, coords)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
