"""
Dream.OS Onboarding Enforcer – Hardened

• Clears clipboard before copy
• Polls clipboard (no fixed 3-min sleep)
• Validates that clipboard content belongs to the agent
• Focus-guards the Cursor window/tab
• Adaptive waits for paste / send
• Writes last-update timestamp into status.json (optional)
"""

from __future__ import annotations
import argparse, json, logging, time, os, sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pyautogui, pyperclip
from rich.console import Console
from rich.logging import RichHandler

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
log = logging.getLogger("onboarding_enforcer")

console = Console()

# ── Config paths ─────────────────────────────────────────────
ROOT = Path.cwd()
COORDS_PATH    = ROOT / "runtime/config/cursor_agent_coords.json"
MAILBOX_ROOT   = ROOT / "runtime/agent_comms/agent_mailboxes"
THEA_OUTBOX    = MAILBOX_ROOT / "commander-THEA" / "outbox"
ONBOARDING_DOC = ROOT / "runtime/governance/onboarding"
PROTOCOLS_DOC  = ROOT / "runtime/governance/protocols"
PROJECT_PLAN   = ROOT / "specs/PROJECT_PLAN.md"

# ── Timing ───────────────────────────────────────────────────
CLIPBOARD_TIMEOUT = 15       # seconds to wait for clipboard text
POST_SEND_WAIT    = 1.2      # seconds between paste & Enter

# ─────────────────────────────────────────────────────────────
def load_coordinates() -> Dict[str, Dict]:
    try:
        with COORDS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        console.log(f"✅ Coordinates loaded for {len(data)} agents")
        return data
    except Exception as e:
        console.log(f"[red]❌ Cannot load coordinates!: {e}")
        sys.exit(1)

def clear_and_copy(copy_btn: dict) -> Optional[str]:
    """Clear clipboard, click copy button, poll until text appears or timeout."""
    pyperclip.copy("")
    pyautogui.click(copy_btn["x"], copy_btn["y"])
    end = time.time() + CLIPBOARD_TIMEOUT
    while time.time() < end:
        txt = pyperclip.paste()
        if txt.strip():
            return txt
        time.sleep(0.25)
    return None

def focus_guard(agent_id: str, input_box: dict):
    """Ensure the Cursor window/tab is focused (best-effort)."""
    try:
        win = pyautogui.getActiveWindow()
        if win and agent_id not in win.title:
            console.log(f"[yellow]⚠️ Focusing window for {agent_id}")
            pyautogui.click(input_box["x"], input_box["y"])
    except Exception:
        pass  # graceful degradation

def send_text(input_box: dict, msg: str, dry: bool):
    if dry:
        console.log(f"[grey58][DRY-RUN] Would paste: {msg[:60]}…")
        return
    focus_guard("unknown", input_box)
    pyautogui.click(input_box["x"], input_box["y"])
    pyperclip.copy(msg)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(POST_SEND_WAIT)
    pyautogui.press("enter")

# ─────────────────────────────────────────────────────────────
ONBOARDING_TEMPLATE = """\
# ONBOARDING PROTOCOL ACTIVATED • {agent}

Welcome to Dream.OS! Please follow these steps:

1. Review onboarding ⇢ {on_doc}
2. Review protocols ⇢ {proto_doc}
3. Review project plan ⇢ {plan}

Remember:
• Stay in **continuous autonomy** mode
• Report only on task state changes
• Never stop unless absolutely necessary
• Complete at least **25 cycles** before any pause
"""

def onboarding_msg(agent_id):  # ← quick helper
    return ONBOARDING_TEMPLATE.format(
        agent=agent_id,
        on_doc=ONBOARDING_DOC,
        proto_doc=PROTOCOLS_DOC,
        plan=PROJECT_PLAN)

def save_to_thea(agent_id: str, response: str, kind="pending_onboarding"):
    THEA_OUTBOX.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    p = THEA_OUTBOX / f"{agent_id}_{kind}_{stamp}.json"
    with p.open("w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.utcnow().isoformat(timespec="seconds")+"Z",
            "agent_id": agent_id,
            "prompt_type": kind,
            "response": response
        }, f, indent=2)
    console.log(f"📩 Saved response to THEA: {p.name}")

# ─────────────────────────────────────────────────────────────
def enforce_for(agent: str, coords: Dict, dry: bool):
    ibox, cbtn = coords[agent]["input_box"], coords[agent]["copy_button"]
    console.rule(f"[bold cyan] {agent}")
    # 1. Try to copy
    txt = None if dry else clear_and_copy(cbtn)
    validated = txt and txt.strip().startswith(agent)
    if validated:
        save_to_thea(agent, txt.strip())
        msg = "Resume autonomy — self-prompt loop triggered recovery."
    else:
        msg = onboarding_msg(agent)
    send_text(ibox, msg, dry)

# ─────────────────────────────────────────────────────────────
def main(agents: List[str] | None, dry=False):
    coords = load_coordinates()
    targets = agents or list(coords.keys())
    for a in targets:
        if a not in coords:
            console.log(f"[red]❌ No coords for {a}, skipping")
            continue
        enforce_for(a, coords, dry)
    console.log("[green]🎉 Enforcement cycle completed")
    return 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Dream.OS Onboarding Enforcer • Hardened")
    ap.add_argument("--agents", nargs="*", help="Agent IDs (Agent-1 …). Default: all")
    ap.add_argument("--dry-run", action="store_true")
    sys.exit(main(ap.parse_args().agents, ap.parse_args().dry_run)) 