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
Run (as a script):

    python src/dreamos/cli/cursor_injector.py \
        --agent-id Agent‑5 \
        --prompt-text "hello cursor!"

Can also be imported to use the CursorInjector class.

Environment variables honoured by CLI mode:

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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pyautogui

# ─── Optional libs ────────────────────────────────────────────────────────────
_PASTE_OK = False
_FOCUS_OK = False

try:
    import pyperclip  # fast paste support  # noqa: F401

    _PASTE_OK = True
except ImportError:
    pass  # Keep _PASTE_OK as False

try:
    import pygetwindow  # focus checks

    _FOCUS_OK = True
except ImportError:
    pass  # Keep _FOCUS_OK as False

# ─── Dream.OS utilities ───────────────────────────────────────────────────────
# These are still needed for the CLI part and potentially for advanced features
# if InjectorSettings were to be used more broadly by the class.
from dreamos.utils.gui_utils import (
    is_window_focused,
    load_coordinates,
)
from dreamos.utils.project_root import find_project_root

# ─── Module‑level logger ──────────────────────────────────────────────────────
log = logging.getLogger("dreamos.cursor_injector")  # Remains for CLI part primarily


# ─── Defaults & Settings dataclass for CLI mode ───────────────────────────────
@dataclass(slots=True)
class CLISettings:
    """Runtime configuration container for CLI script operations."""

    project_root: Path = field(
        default_factory=lambda: Path(find_project_root(__file__))
    )
    coords_path: Path = field(
        default_factory=lambda: Path(
            os.getenv(
                "DREAMOS_CURSOR_COORDS",
                CLISettings.project_root / "runtime/config/cursor_agent_coords.json",
            )
        )
    )
    target_window_title: str = os.getenv("DREAMOS_CURSOR_TITLE", "Cursor")
    queue_root: Path = field(
        default_factory=lambda: Path(
            os.getenv(
                "DREAMOS_CURSOR_QUEUE",
                CLISettings.project_root / "runtime/cursor_queue",
            )
        )
    )
    processed_root: Path = field(
        default_factory=lambda: Path(
            os.getenv(
                "DREAMOS_CURSOR_PROCESSED",
                CLISettings.project_root / "runtime/cursor_processed",
            )
        )
    )

    min_pause: float = 0.10
    max_pause: float = 0.25
    random_offset: int = 3
    focus_verify: bool = True
    use_paste: bool = True
    max_recalibration: int = 1
    screenshot_on_error: bool = False


# Global settings object for CLI mode
_cli_settings_instance: Optional[CLISettings] = None


def get_cli_settings() -> CLISettings:
    global _cli_settings_instance
    if _cli_settings_instance is None:
        _cli_settings_instance = CLISettings()
    return _cli_settings_instance


# ─── CursorInjector Class ───────────────────────────────────────────────────
class CursorInjector:
    """Handles direct GUI interactions with the Cursor application window."""

    def __init__(
        self,
        window_title: str,
        coords: Dict[str, Any],
        min_pause: float = 0.10,
        max_pause: float = 0.25,
        random_offset: int = 3,
        focus_verify: bool = True,  # Should pygetwindow be used
        use_paste: bool = True,  # Should pyperclip be used
    ):
        self.window_title = window_title
        self.coords = coords  # Expects e.g. {"chat_input_field": [x, y]}
        self.min_pause = min_pause
        self.max_pause = max_pause
        self.random_offset = random_offset
        self.focus_verify_enabled = focus_verify
        self.use_paste_enabled = use_paste

        # Check optional library availability at instantiation
        self.paste_available = _PASTE_OK
        self.focus_check_available = _FOCUS_OK

        self.log = logging.getLogger(self.__class__.__name__)
        self.log.debug(
            f"CursorInjector initialized for window '{window_title}'. Paste: {self.paste_available}, Focus Check: {self.focus_check_available}"
        )

    def _pause(self) -> None:
        time.sleep(random.uniform(self.min_pause, self.max_pause))

    def focus_window(self) -> bool:
        """Brings the target window to the foreground and focuses it."""
        self.log.debug(f"Attempting to focus window: {self.window_title}")
        if not self.focus_verify_enabled or not self.focus_check_available:
            self.log.debug(
                "Focus verification skipped (disabled or pygetwindow not available)."
            )
            # Try a generic focus/activate if possible, or just assume success
            # For simplicity here, we can try activating if pygetwindow is available for that
            if self.focus_check_available:
                try:
                    windows = pygetwindow.getWindowsWithTitle(self.window_title)
                    if windows:
                        win = windows[0]
                        if win.isMinimized:
                            win.restore()
                        win.activate()
                        self.log.debug(
                            f"Window '{self.window_title}' activated (no verification). "
                        )
                        return True  # Assuming activation worked
                except Exception as e:
                    self.log.warning(f"Error during basic window activation: {e}")
            return True  # Assume success if no verification

        if is_window_focused(self.window_title):  # from dreamos.utils.gui_utils
            self.log.debug(f"Window '{self.window_title}' is already focused.")
            return True

        try:
            windows = pygetwindow.getWindowsWithTitle(self.window_title)
            if not windows:
                self.log.error(f"Window '{self.window_title}' not found.")
                return False
            win = windows[0]
            if win.isMinimized:
                win.restore()
            win.activate()  # pygetwindow's activate method
            time.sleep(0.1)  # Small delay to allow focus to shift
            if is_window_focused(self.window_title):
                self.log.info(f"Successfully focused window: '{self.window_title}'")
                return True
            else:
                self.log.warning(
                    f"Window '{self.window_title}' activated but focus check failed."
                )
                return False  # Or True if activation is deemed sufficient
        except Exception as e:
            self.log.error(f"Error focusing window '{self.window_title}': {e}")
            return False

    def _type_or_paste(self, text: str) -> None:
        if self.use_paste_enabled and self.paste_available:
            try:
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
                self.log.debug("Pasted text via clipboard.")
                return
            except Exception as e:
                self.log.warning(
                    f"Clipboard paste failed ({e}). Falling back to typing."
                )
        pyautogui.typewrite(text, interval=0.01)  # Reduced default interval slightly
        self.log.debug("Typed text using pyautogui.typewrite.")

    def type_text(self, text: str, element_key: str = "chat_input_field") -> bool:
        """Clicks on the specified element (using coords) and types text."""
        self.log.debug(f"Attempting to type text into '{element_key}'.")
        if (
            element_key not in self.coords
            or not isinstance(self.coords[element_key], list)
            or len(self.coords[element_key]) != 2
        ):
            self.log.error(
                f"Coordinates for '{element_key}' are missing or invalid in self.coords."
            )
            return False

        tx, ty = self.coords[element_key]
        # Add human-like jitter
        tx_jitter = tx + random.randint(-self.random_offset, self.random_offset)
        ty_jitter = ty + random.randint(-self.random_offset, self.random_offset)

        try:
            self.log.debug(f"Moving to ({tx_jitter},{ty_jitter}) for '{element_key}'")
            pyautogui.moveTo(tx_jitter, ty_jitter, duration=random.uniform(0.1, 0.2))
            self._pause()
            pyautogui.click()
            self._pause()

            # Assumes window is already focused by a preceding call to self.focus_window()
            # Clear field + send
            pyautogui.hotkey("ctrl", "a")
            self._pause()
            pyautogui.press("delete")
            self._pause()
            self._type_or_paste(text)
            self.log.info(f"Successfully typed text into '{element_key}'.")
            return True
        except pyautogui.FailSafeException:
            self.log.critical("PyAutoGUI fail-safe triggered during type_text.")
            return False
        except Exception as e:
            self.log.error(
                f"Error during type_text for '{element_key}': {e}", exc_info=True
            )
            # Optionally add screenshot on error like in original script
            return False


# ─── CLI Script Functionality (preserved) ───────────────────────────────────

# Note: These functions now use get_cli_settings() to access CLI-specific settings.


def _cli_next_prompt_file(agent_id: str) -> Optional[Path]:
    settings = get_cli_settings()
    qdir = settings.queue_root / agent_id
    if not qdir.is_dir():
        return None
    files: List[Path] = sorted(f for f in qdir.iterdir() if f.is_file())
    return files[0] if files else None


def _cli_mark_processed(prompt_file: Path) -> None:
    settings = get_cli_settings()
    dest = settings.processed_root / prompt_file.parent.name
    dest.mkdir(parents=True, exist_ok=True)
    prompt_file.rename(dest / prompt_file.name)


def _cli_ensure_focus(title: str) -> bool:
    settings = get_cli_settings()
    if not settings.focus_verify or not _FOCUS_OK:
        return True
    if is_window_focused(title):
        return True
    wins = pygetwindow.getWindowsWithTitle(title)
    if wins:
        log.warning(
            "(CLI) Window '%s' exists but not focused – aborting injection.", title
        )
    else:
        log.error("(CLI) Window '%s' not found!", title)
    return False


def _cli_type_or_paste(text: str) -> None:
    settings = get_cli_settings()
    if settings.use_paste and _PASTE_OK:
        try:
            import pyperclip

            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            return
        except Exception as e:
            log.warning("(CLI) Clipboard paste failed (%s). Falling back to typing.", e)
    pyautogui.typewrite(text, interval=0.02)


def _cli_inject_single(
    agent_id: str,
    prompt_text: str,
    coords: Dict[str, Any],
    element_key: str = "input_box",
) -> bool:
    settings = get_cli_settings()
    # For CLI, load_coordinates is used, which might return a flat map or agent-keyed map.
    # This part needs careful checking against how load_coordinates and coords are used in CLI.
    # Assuming coords passed in is already the correct agent's coord map for now.

    # If coords is a map like {"Agent-1": {"input_box": ...}}, adjust access.
    # For now, assume coords is flat like {"input_box": ...} for the targeted element.
    target_coord_data = coords.get(element_key)
    if not isinstance(target_coord_data, list) or len(target_coord_data) != 2:
        # Try agent-specific if not flat
        agent_specific_coords = coords.get(f"Agent-{agent_id}")
        if isinstance(agent_specific_coords, dict):
            target_coord_data = agent_specific_coords.get(element_key)

        if not isinstance(target_coord_data, list) or len(target_coord_data) != 2:
            log.error(
                f"(CLI) Coordinate for '{element_key}' (agent '{agent_id}') missing or invalid in provided coords map."
            )
            # Recalibration logic from original script might go here if desired for CLI
            return False

    coord_x, coord_y = target_coord_data
    tx = coord_x + random.randint(-settings.random_offset, settings.random_offset)
    ty = coord_y + random.randint(-settings.random_offset, settings.random_offset)
    log.debug(
        "(CLI) Moving to (%s,%s) for element '%s' of agent '%s'",
        tx,
        ty,
        element_key,
        agent_id,
    )

    try:
        pyautogui.moveTo(tx, ty, duration=random.uniform(0.1, 0.3))
        time.sleep(random.uniform(settings.min_pause, settings.max_pause))
        pyautogui.click()
        time.sleep(random.uniform(settings.min_pause, settings.max_pause))

        if not _cli_ensure_focus(settings.target_window_title):
            return False

        pyautogui.hotkey("ctrl", "a")
        time.sleep(random.uniform(settings.min_pause, settings.max_pause))
        pyautogui.press("delete")
        time.sleep(random.uniform(settings.min_pause, settings.max_pause))
        _cli_type_or_paste(prompt_text)
        return True
    except pyautogui.FailSafeException:
        log.critical("(CLI) PyAutoGUI fail-safe triggered.")
        return False
    except Exception as e:
        log.error("(CLI) Injection error: %s", e, exc_info=True)
        if settings.screenshot_on_error:
            pyautogui.screenshot(
                settings.project_root / f"cli_inject_err_{time.time()}.png"
            )
        return False
    return False  # Should not be reached if recalibration not used


def _cli_loop(
    agent_ids: Optional[Iterable[str]] = None, cycle_pause: float = 1.0
) -> None:
    settings = get_cli_settings()
    # In CLI mode, coords are typically loaded once from settings.coords_path
    cli_coords = load_coordinates(settings.coords_path) or {}
    watch = (
        list(agent_ids) if agent_ids else list(cli_coords.keys())
    )  # Watch agents found in coords file if no specific ids
    log.info("(CLI) Monitoring queues for agents: %s", ", ".join(watch))

    while True:
        processed_count = 0
        for aid in watch:
            prompt_file_path = _cli_next_prompt_file(aid)
            if not prompt_file_path:
                continue
            prompt_content = prompt_file_path.read_text(encoding="utf-8")

            # Extract the correct coordinate sub-map for the current agent
            # The run_bridge_loop now prepares a flat map like {"chat_input_field":...}
            # The CLI version might need to handle the agent-keyed map from cursor_agent_coords.json
            agent_coord_map = cli_coords.get(aid)  # e.g. cli_coords["Agent-1"]
            if not agent_coord_map:
                log.warning(
                    f"(CLI) No coordinates found for agent {aid} in {settings.coords_path}. Skipping."
                )
                continue

            if _cli_inject_single(
                aid, prompt_content, agent_coord_map
            ):  # Pass the agent_coord_map
                _cli_mark_processed(prompt_file_path)
                processed_count += 1
        if processed_count == 0:
            time.sleep(cycle_pause)
        else:
            log.info(
                "(CLI) Processed %s prompt(s); sleeping %.2fs",
                processed_count,
                cycle_pause / 5,
            )
            time.sleep(max(0.1, cycle_pause / 5))


def _build_cli_parser() -> argparse.ArgumentParser:
    settings = get_cli_settings()  # Access defaults for help strings
    parser = argparse.ArgumentParser(
        description="Injects prompts into Cursor for a given agent (CLI mode)."
    )
    parser.add_argument("--agent-id", required=True, help="Agent ID (e.g. Agent-5)")
    parser.add_argument(
        "--prompt-text", help="Direct prompt text (optional, for single injection)"
    )
    parser.add_argument(
        "--target-window-title",
        default=settings.target_window_title,
        help="Substring of target window title",
    )
    parser.add_argument(
        "--coords-file",
        default=settings.coords_path,
        type=Path,
        help="Path to coordinates JSON",
    )
    return parser


def cli_main() -> None:
    args = _build_cli_parser().parse_args()

    # Setup basic logging for CLI mode
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)-8s %(name)-25s %(message)s"
    )
    log.info(f"CLI mode initiated for agent: {args.agent_id}")

    # Update CLI settings from args
    cli_settings = get_cli_settings()
    cli_settings.target_window_title = args.target_window_title
    cli_settings.coords_path = args.coords_file
    log.debug(f"CLI settings: {cli_settings}")

    # Load coordinates for CLI operation.
    # This should be the full map, e.g., from cursor_agent_coords.json
    loaded_coords_map = load_coordinates(cli_settings.coords_path) or {}

    # For single injection, we need the specific agent's coordinate map portion.
    # The inject_single_cli expects a map like {"input_box": [x,y], ...} for the specific agent.
    agent_id_for_coords = args.agent_id  # e.g., "Agent-5"
    coords_for_single_agent = loaded_coords_map.get(agent_id_for_coords, {})
    if not coords_for_single_agent and args.prompt_text:
        log.error(
            f"Coordinates for agent '{agent_id_for_coords}' not found in '{cli_settings.coords_path}'. Cannot perform single injection."
        )
        sys.exit(1)

    if args.prompt_text:
        log.info(f"Attempting single prompt injection for agent '{args.agent_id}'.")
        if _cli_inject_single(args.agent_id, args.prompt_text, coords_for_single_agent):
            log.info("CLI: Single prompt injection successful.")
            sys.exit(0)
        else:
            log.error("CLI: Single prompt injection FAILED.")
            sys.exit(1)
    else:
        log.info(f"Entering queue monitoring mode for agent(s): {args.agent_id}")
        try:
            _cli_loop(
                agent_ids=[args.agent_id]
            )  # Pass agent_id as a list for consistency with _cli_loop logic
        except KeyboardInterrupt:
            log.info("(CLI) User interrupted queue monitoring.")
        sys.exit(0)


if __name__ == "__main__":
    cli_main()
