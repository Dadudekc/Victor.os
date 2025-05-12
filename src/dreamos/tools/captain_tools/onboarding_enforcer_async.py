"""
Dream.OS Onboarding Enforcer • Async

* One asyncio Task per agent
* Per-agent finite-state-machine  (NEED_COPY → GOT_COPY → …)
* Clipboard polling with timeout
* Resilient to UI lag; scalable to many agents
"""

from __future__ import annotations
import asyncio, json, logging, os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import pyautogui, pyperclip
from rich.logging import RichHandler
from rich.console import Console

# ── Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)])
log = logging.getLogger("onboard_async")
console = Console()

# ── Paths
ROOT = Path.cwd()
COORDS_PATH    = ROOT / "runtime/config/cursor_agent_coords.json"
MAILBOX_ROOT   = ROOT / "runtime/agent_comms/agent_mailboxes"
THEA_OUTBOX    = MAILBOX_ROOT / "commander-THEA" / "outbox"
ONBOARDING_DOC = ROOT / "runtime/governance/onboarding"
PROTOCOLS_DOC  = ROOT / "runtime/governance/protocols"
PROJECT_PLAN   = ROOT / "specs/PROJECT_PLAN.md"

# ── FSM States
NEED_COPY = "need_copy"
GOT_COPY = "got_copy"
SENDING = "sending"
WAITING = "waiting"

# ── Timing
CLIPBOARD_TIMEOUT = 15  # seconds to wait for clipboard text
POST_SEND_WAIT = 1.2    # seconds between paste & Enter
COOLDOWN = 30          # seconds to wait after sending prompt

# ─────────────────────────────────────────────────────────────
class AgentFSM:
    def __init__(self, agent: str, coords: Dict, dry=False):
        self.agent = agent
        self.ibox = coords["input_box"]
        self.cbtn = coords["copy_button"]
        self.state = NEED_COPY
        self.dry = dry
        self.last_action = datetime.utcnow()

    async def clipboard_after_click(self, timeout=CLIPBOARD_TIMEOUT) -> Optional[str]:
        """Clear clipboard, click copy button, poll until text appears or timeout."""
        pyperclip.copy("")
        if not self.dry:
            pyautogui.click(self.cbtn["x"], self.cbtn["y"])
        end = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < end:
            txt = pyperclip.paste().strip()
            if txt:
                return txt
            await asyncio.sleep(0.25)
        return None

    async def send_text(self, msg: str):
        """Send text to agent's input box with focus guard."""
        if self.dry:
            console.log(f"[grey58][DRY-RUN] {self.agent} ⇢ {msg[:60]}…")
            return
        try:
            # Focus guard
            win = pyautogui.getActiveWindow()
            if win and self.agent not in win.title:
                console.log(f"[yellow]⚠️ Focusing window for {self.agent}")
                pyautogui.click(self.ibox["x"], self.ibox["y"])
            
            # Send text
            pyautogui.click(self.ibox["x"], self.ibox["y"])
            pyperclip.copy(msg)
            pyautogui.hotkey("ctrl", "v")
            await asyncio.sleep(POST_SEND_WAIT)
            pyautogui.press("enter")
            console.log(f"📤 Sent to {self.agent}")
        except Exception as e:
            console.log(f"[red]❌ Failed to send to {self.agent}: {e}")

    def save_to_thea(self, response: str, kind="pending_onboarding"):
        """Save agent response to THEA's outbox."""
        try:
            THEA_OUTBOX.mkdir(parents=True, exist_ok=True)
            stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            p = THEA_OUTBOX / f"{self.agent}_{kind}_{stamp}.json"
            with p.open("w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": datetime.utcnow().isoformat(timespec="seconds")+"Z",
                    "agent_id": self.agent,
                    "prompt_type": kind,
                    "response": response
                }, f, indent=2)
            console.log(f"📩 Saved response to THEA: {p.name}")
        except Exception as e:
            console.log(f"[red]❌ Failed to save to THEA: {e}")

    def onboarding_msg(self) -> str:
        """Create onboarding message for this agent."""
        return f"""# ONBOARDING PROTOCOL ACTIVATED • {self.agent}

Welcome to Dream.OS! Please follow these steps:

1. Review onboarding ⇢ {ONBOARDING_DOC}
2. Review protocols ⇢ {PROTOCOLS_DOC}
3. Review project plan ⇢ {PROJECT_PLAN}

Remember:
• Stay in **continuous autonomy** mode
• Report only on task state changes
• Never stop unless absolutely necessary
• Complete at least **25 cycles** before any pause
"""

    async def run(self):
        """Main FSM loop for this agent."""
        console.rule(f"[bold cyan] {self.agent} FSM")
        while True:
            try:
                if self.state == NEED_COPY:
                    txt = await self.clipboard_after_click()
                    if txt and txt.startswith(self.agent):
                        self.save_to_thea(txt)
                        self.state = SENDING
                        await self.send_text("Resume autonomy — self-prompt loop triggered recovery.")
                        self.state = WAITING
                        self.last_action = datetime.utcnow()
                    else:
                        self.state = SENDING
                        await self.send_text(self.onboarding_msg())
                        self.state = WAITING
                        self.last_action = datetime.utcnow()

                elif self.state == WAITING:
                    # Wait for cooldown before next cycle
                    elapsed = (datetime.utcnow() - self.last_action).total_seconds()
                    if elapsed >= COOLDOWN:
                        self.state = NEED_COPY
                    else:
                        await asyncio.sleep(1)

                await asyncio.sleep(0.1)  # Cooperative yield

            except asyncio.CancelledError:
                console.log(f"[yellow]🛑 {self.agent} FSM cancelled")
                break
            except Exception as e:
                console.log(f"[red]❌ {self.agent} FSM error: {e}")
                await asyncio.sleep(5)  # Back off on error

# ─────────────────────────────────────────────────────────────
def load_coords() -> Dict[str, Dict]:
    """Load agent coordinates from config file."""
    try:
        with COORDS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        console.log(f"✅ Coordinates loaded for {len(data)} agents")
        return data
    except Exception as e:
        console.log(f"[red]❌ Cannot load coordinates!: {e}")
        return {}

async def main(dry=False, targets=None):
    """Main entry point - runs FSM for each agent in parallel."""
    coords = load_coords()
    if not coords:
        return 1

    targets = targets or list(coords.keys())
    tasks = []
    
    for agent in targets:
        if agent not in coords:
            console.log(f"[red]❌ No coords for {agent}, skipping")
            continue
        task = asyncio.create_task(AgentFSM(agent, coords[agent], dry).run())
        tasks.append(task)

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        console.log("\n[yellow]👋 Shutting down...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    return 0

if __name__ == "__main__":
    import argparse, sys
    ap = argparse.ArgumentParser(description="Dream.OS Onboarding Enforcer • Async")
    ap.add_argument("--dry-run", action="store_true", help="Simulate without clicking/pasting")
    ap.add_argument("--agents", nargs="*", help="Agent IDs (Agent-1 …). Default: all")
    args = ap.parse_args()
    try:
        sys.exit(asyncio.run(main(args.dry_run, args.agents)))
    except KeyboardInterrupt:
        console.log("\n[yellow]👋 Shutdown")
        sys.exit(0) 