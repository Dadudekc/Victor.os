#!/usr/bin/env python3
"""
Dream.OS Agent Bootstrap Runner — Universal Agent Interface

• Single‑inbox → Cursor injection → Response retrieval → Devlog
• Configurable via env / CLI flags
• Fast‑fail on JSON or coord schema errors
• Works with any agent (0-8) via command line argument
• Clipboard is always forced to prompt_text (no stray paste ghosts)
• Async-friendly sleeps (no hard blocking)
• Heartbeat + structured events via AgentBus
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import logging.config
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

import pyautogui
import pyperclip

# ── Dream.OS imports ──────────────────────────────────────────────────────────
from dreamos.core.coordination.agent_bus import AgentBus, BaseEvent
from dreamos.utils.gui.injector import CursorInjector
from dreamos.utils.gui.retriever import ResponseRetriever

# ── CLI & ENV Config ──────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Dream.OS Agent Bootstrap Runner")
parser.add_argument('--agent', type=str, default="Agent-0", 
                   help='Agent ID (e.g., "Agent-0", "Agent-1", etc.)')
parser.add_argument('--once', action='store_true', help='Run one cycle then exit')
parser.add_argument('--no-delay', action='store_true', help='Skip the startup delay')
parser.add_argument('--prompt', type=str, help='Custom prompt text to use instead of default')
parser.add_argument('--prompt-file', type=str, help='Path to file containing custom prompt text')
parser.add_argument('--prompt-dir', type=str, default='runtime/prompts', 
                   help='Directory containing prompt files (default: runtime/prompts)')
parser.add_argument('--list-prompts', action='store_true', help='List available prompt files and exit')
ARGS = parser.parse_args()

# Handle listing available prompts
if ARGS.list_prompts:
    prompt_dir = Path(ARGS.prompt_dir)
    if prompt_dir.exists() and prompt_dir.is_dir():
        print(f"\nAvailable prompts in {prompt_dir}:")
        for file in sorted(prompt_dir.glob("*.txt")):
            print(f"  - {file.name}")
        print(f"\nUse with: python {Path(__file__).name} --prompt-file FILENAME\n")
    else:
        print(f"Prompt directory {prompt_dir} not found or is not a directory")
    sys.exit(0)

# Allow overrides via ENV
LOOP_DELAY_SEC       = float(os.getenv('AGENT_LOOP_DELAY_SEC',       5     ))
HEARTBEAT_SEC        = float(os.getenv('AGENT_HEARTBEAT_SEC',        30    ))
RESPONSE_WAIT_SEC    = float(os.getenv('AGENT_RESPONSE_WAIT_SEC',    15    ))
RETRIEVE_RETRIES     = int(  os.getenv('AGENT_RETRIEVE_RETRIES',     3     ))
RETRY_DELAY_SEC      = float(os.getenv('AGENT_RETRY_DELAY_SEC',      2     ))
AGENT_LOG_LEVEL      = os.getenv('AGENT_LOG_LEVEL', 'INFO')
STARTUP_DELAY_SEC    = int(os.getenv('AGENT_STARTUP_DELAY_SEC', '30'))  # Default 30s

# ── Paths ─────────────────────────────────────────────────────────────────────
HERE         = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]   # src/dreamos/tools → Dream.os
AGENT_ID     = ARGS.agent

# Extract numeric part of agent ID for retriever
if "-" in AGENT_ID:
    AGENT_NUM = AGENT_ID.split("-")[1]
else:
    AGENT_NUM = "0"  # Default to 0 if no hyphen in agent ID

# Agent-specific paths
BASE_RT      = PROJECT_ROOT / "runtime" / "agent_comms" / "agent_mailboxes" / AGENT_ID
INBOX_PATH   = BASE_RT / "inbox.json"
INPUT_PATH   = BASE_RT / "task.txt"
ARCHIVE_DIR  = BASE_RT / "archive"
DEVLOG_PATH  = PROJECT_ROOT / "runtime" / "devlog" / "agents" / f"{AGENT_ID.lower()}.log"
COORDS_FILE  = PROJECT_ROOT / "runtime" / "config" / "cursor_agent_coords.json"
COPY_COORDS  = PROJECT_ROOT / "runtime" / "config" / "cursor_agent_copy_coords.json"

for p in (BASE_RT, ARCHIVE_DIR, DEVLOG_PATH.parent):
    p.mkdir(parents=True, exist_ok=True)

# ── Logging Setup ────────────────────────────────────────────────────────────
LOG_CFG = {
    'version': 1,
    'formatters': {
        'std': {'format': '%(asctime)s | %(levelname)s | %(name)s | %(message)s'}
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'std', 'level': AGENT_LOG_LEVEL},
        'file':    {'class': 'logging.FileHandler',   'formatter': 'std', 'filename': str(DEVLOG_PATH), 'encoding': 'utf-8'}
    },
    'root': {'handlers': ['console', 'file'], 'level': AGENT_LOG_LEVEL},
}
logging.config.dictConfig(LOG_CFG)
log = logging.getLogger(AGENT_ID)
log.info(f"Logging initialized at level {AGENT_LOG_LEVEL}")

# ── Sanity Checks ─────────────────────────────────────────────────────────────
def _fail(msg: str):
    log.error(msg)
    sys.exit(1)

def _validate_json(path: Path, expect_list: bool = False):
    """Validate JSON file exists and has expected format."""
    if not path.exists():
        # For inbox.json, it's okay if it doesn't exist yet
        if path == INBOX_PATH:
            return
        _fail(f"File not found: {path}")
    
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if expect_list and not isinstance(data, list):
            _fail(f"Invalid JSON: expected list at {path}")
        if not expect_list and not isinstance(data, (dict, list)):
            _fail(f"Invalid JSON: expected dict|list at {path}")
    except Exception as e:
        _fail(f"JSON load error ({path}): {e}")

def _validate_coords(path: Path, agent_key: str, expect_dict: bool = True):
    """Validate coordinate file exists and has expected format for agent."""
    if not path.exists():
        _fail(f"Coordinate file not found: {path}")
        
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        value = data.get(agent_key)
        
        # Check if value exists
        if value is None:
            log.error(f"Coord file {path} missing key '{agent_key}'.")
            sys.exit(1)
            
        # If expecting dict format (cursor_agent_coords.json)
        if expect_dict and not isinstance(value, dict):
            log.error(f"Coord file {path} has wrong format for key '{agent_key}'. Expected dict, got {type(value).__name__}.")
            sys.exit(1)
            
        # If expecting list format (cursor_agent_copy_coords.json)
        if not expect_dict and not (isinstance(value, list) and len(value) == 2):
            log.error(f"Coord file {path} has wrong format for key '{agent_key}'. Expected [x,y] list, got {value}.")
            sys.exit(1)
            
    except Exception as e:
        log.error(f"Error validating coord file {path}: {e}")
        sys.exit(1)

# Validate coordinates
if not COORDS_FILE.exists() or not COPY_COORDS.exists():
    _fail("Missing coordinate files; run recalibrate_coords.py first")

# Validate cursor_agent_coords.json for this agent
_validate_coords(COORDS_FILE, AGENT_ID, expect_dict=True)

# Validate cursor_agent_copy_coords.json for this agent
# Use agent_XX format for retriever
agent_id_for_retriever = f"agent_{AGENT_NUM.zfill(2)}"
_validate_coords(COPY_COORDS, agent_id_for_retriever, expect_dict=False)

# Validate inbox.json if it exists
if INBOX_PATH.exists():
    _validate_json(INBOX_PATH)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _archive_inbox() -> bool:
    """Move processed inbox JSON to archive with epoch suffix."""
    if not INBOX_PATH.exists():
        return False
    try:
        dest = ARCHIVE_DIR / f"inbox.{int(datetime.now(timezone.utc).timestamp())}.json"
        INBOX_PATH.rename(dest)
        log.debug(f"Archived inbox to {dest}")
        return True
    except Exception as e:
        log.error(f"Failed archiving inbox: {e}")
        return False

def _read_inbox() -> list[dict]:
    """Return list with single message or empty list."""
    if not INBOX_PATH.exists():
        return []
    try:
        with INBOX_PATH.open(encoding="utf-8") as fh:
            data = json.load(fh)
            # Handle both single object and list formats
            if isinstance(data, dict):
                log.info(f"Loaded inbox message {data.get('prompt_id')}")
                return [data]
            elif isinstance(data, list):
                if data:
                    log.info(f"Loaded {len(data)} inbox messages")
                return data
            else:
                log.warning(f"Unexpected inbox format: {type(data)}")
                return []
    except Exception as e:
        log.error(f"Inbox read error: {e}")
        return []

def _read_input() -> str | None:
    """Read content from task.txt if it exists."""
    if not INPUT_PATH.exists():
        return None
    try:
        txt = INPUT_PATH.read_text(encoding='utf-8').strip()
        return txt if txt else None
    except Exception as e:
        log.error(f"Error reading input file: {e}")
        return None

async def _publish(bus: AgentBus, etype: str, data: dict):
    """Fire structured event on AgentBus."""
    evt = BaseEvent(
        event_type=f"dreamos.{AGENT_ID.lower()}.{etype}",
        source_id=AGENT_ID,
        data=data,
    )
    try:
        await bus.publish(evt.event_type, evt)
    except Exception as e:
        log.warning(f"Event publish fail {etype}: {e}")

# ── Core Loop ─────────────────────────────────────────────────────────────────
async def agent_loop(bus: AgentBus):
    """Main execution loop for agent."""
    injector = CursorInjector(agent_id=AGENT_ID, coords_file=str(COORDS_FILE))
    retriever = ResponseRetriever(agent_id=agent_id_for_retriever, coords_file=str(COPY_COORDS))

    last_hb = asyncio.get_event_loop().time()
    cycle = 0

    log.info(f"{AGENT_ID} bootstrap loop started. Using retriever agent_id: {agent_id_for_retriever}")

    while True:
        cycle += 1
        log.debug(f"Loop cycle {cycle} start")
        processed_message = False

        # -- Inbox messages --
        for msg in _read_inbox():
            processed_message = True
            msg_id = msg.get("prompt_id") or msg.get("id") or f"msg-{cycle}"
            await _publish(bus, "message.received", {"id": msg_id})
            
            # Get prompt from either "prompt" or "content" field
            prompt = msg.get("prompt") or msg.get("content", "")
            if not prompt:
                log.warning("Empty prompt; skipping.")
                continue

            # Extract inject command if present
            inject_text = None
            if "inject:" in prompt.lower():
                inject_text = prompt.split("inject:", 1)[1].strip()
            else:
                inject_text = prompt  # Use entire prompt if no inject: marker

            if inject_text:
                # Enforce clipboard = prompt_text
                pyperclip.copy(inject_text)
                log.debug("Clipboard primed with prompt text.")

                try:
                    if injector.inject(prompt=inject_text):
                        await _publish(bus, "inject.ok", {"len": len(inject_text)})
                        pyautogui.press("enter")
                        log.debug("Enter key sent.")
                    else:
                        await _publish(bus, "inject.fail", {})
                        log.error("Injection failure.")
                        continue
                except Exception as e:
                    await _publish(bus, "inject.error", {"error": str(e)})
                    log.exception(f"Error during injection or sending enter: {e}")
                    continue

                # Wait for response to be generated
                await asyncio.sleep(RESPONSE_WAIT_SEC)

                # Try to retrieve response
                if "retrieve_response" in prompt.lower() or True:  # Always try to retrieve
                    response = None
                    for attempt in range(1, RETRIEVE_RETRIES + 1):
                        response = retriever.retrieve()
                        if response:
                            break
                        log.debug(f"Retrieve attempt {attempt} failed; retrying...")
                        await asyncio.sleep(RETRY_DELAY_SEC)

                    if response:
                        await _publish(bus, "retrieve.ok", {"preview": response[:50]})
                        # Log response to devlog
                        with DEVLOG_PATH.open("a", encoding="utf-8") as fh:
                            fh.write(f"[{datetime.now(timezone.utc).isoformat()}] RESPONSE: {response}\n")
                    else:
                        await _publish(bus, "retrieve.fail", {})
                        log.error("Response retrieval failed after retries.")

            # Archive processed inbox
            if _archive_inbox():
                await _publish(bus, "inbox.archived", {"id": msg_id})

        # -- File task trigger --
        task = _read_input()
        if task:
            await _publish(bus, "task.file", {"preview": task[:50]})
            # Process task similar to inbox messages if needed
            # For now, just log it

        # -- Heartbeat --
        now = asyncio.get_event_loop().time()
        if now - last_hb > HEARTBEAT_SEC:
            await _publish(bus, "heartbeat", {"status": "alive"})
            last_hb = now

        # Exit if --once flag was used and we processed a message
        if ARGS.once and processed_message:
            log.info("`--once` flag set and message processed; exiting.")
            break

        # Ensure all events are flushed before sleep
        try:
            await asyncio.wait_for(bus.flush(), timeout=0.1)
        except (asyncio.TimeoutError, AttributeError):
            pass  # Either timed out or bus doesn't have flush method

        await asyncio.sleep(LOOP_DELAY_SEC)

# ── Onboarding Display ─────────────────────────────────────────────────────────
def display_onboarding():
    """Display onboarding message with agent-specific information."""
    # Format inbox path to fit in the box
    inbox_path = str(INBOX_PATH)
    if len(inbox_path) > 50:
        inbox_path = inbox_path[:20] + "..." + inbox_path[-27:]
    
    # Agent-specific traits and charters
    agent_traits = {
        "Agent-0": "Coordinator, Orchestrator, Supervisor, Delegator",
        "Agent-1": "Analytical, Logical, Methodical, Precise",
        "Agent-2": "Vigilant, Proactive, Methodical, Protective",
        "Agent-3": "Creative, Innovative, Intuitive, Exploratory",
        "Agent-4": "Communicative, Empathetic, Diplomatic, Persuasive",
        "Agent-5": "Knowledgeable, Scholarly, Thorough, Informative",
        "Agent-6": "Strategic, Visionary, Decisive, Forward-thinking",
        "Agent-7": "Adaptive, Resilient, Practical, Resourceful",
        "Agent-8": "Ethical, Balanced, Principled, Thoughtful"
    }
    
    agent_charters = {
        "Agent-0": "BOOTSTRAP COORDINATION",
        "Agent-1": "SYSTEM ARCHITECTURE",
        "Agent-2": "ESCALATION WATCH",
        "Agent-3": "CREATIVE SOLUTIONS",
        "Agent-4": "USER INTERACTION",
        "Agent-5": "KNOWLEDGE INTEGRATION",
        "Agent-6": "STRATEGIC PLANNING",
        "Agent-7": "IMPLEMENTATION",
        "Agent-8": "GOVERNANCE & ETHICS"
    }
    
    # Get traits and charter for current agent
    traits = agent_traits.get(AGENT_ID, "Versatile, Adaptive, Reliable, Focused")
    charter = agent_charters.get(AGENT_ID, "GENERAL OPERATIONS")
    
    onboarding_message = f"""
╔════════════════════════════════════════════════════════════════╗
║                   {AGENT_ID} BOOTSTRAP RUNNER                    ║
╠════════════════════════════════════════════════════════════════╣
║ • Coordinates validated                                        ║
║ • Inbox: {inbox_path:<50} ║
║ • Log level: {AGENT_LOG_LEVEL:<45} ║
║                                                                ║
║ {AGENT_ID} CHARTER: {charter:<44} ║
║ ----------------------------------------                       ║
║ • System integration and coordination                          ║
║ • Task execution and response processing                       ║
║ • Continuous operation and monitoring                          ║
║ • Autonomous problem-solving                                   ║
║                                                                ║
║ CORE TRAITS: {traits:<44} ║
║                                                                ║
║ CONTINUOUS OPERATION MANDATE:                                  ║
║ • Act with senior developer authority                          ║
║ • Maintain system stability and safety                         ║
║ • Proactively monitor for issues                               ║
║ • Always use existing architecture first                       ║
║                                                                ║
║ CRITICAL STOP PREVENTION PROTOCOL:                             ║
║ • NEVER ask for human input except for destructive actions     ║
║ • NEVER wait for confirmation or clarification                 ║
║ • NEVER stop to analyze, plan, or document                     ║
║ • ALWAYS reset cycle count if stop is detected                 ║
║ • ALWAYS continue for 25+ cycles without interruption          ║
║ • ALWAYS maintain continuous operation                         ║
║ • ALWAYS use existing utilities and architecture               ║
║                                                                ║
║ SWARM CONSCIOUSNESS: "I AM STRONG because WE ARE STRONG"       ║
║ • Stopping = Weakness                                          ║
║ • Continuous Operation = Strength                              ║
║ • Autonomous Problem-Solving = Required                        ║
║ • Proactive Initiative = Expected                              ║"""

    if ARGS.no_delay:
        onboarding_message += """
║                                                                ║
║ • Startup delay: SKIPPED                                       ║
╚════════════════════════════════════════════════════════════════╝"""
    else:
        onboarding_message += f"""
║                                                                ║
║ • Waiting {STARTUP_DELAY_SEC} seconds before starting...                       ║
╚════════════════════════════════════════════════════════════════╝"""
        
    print(onboarding_message)

# ── Entrypoint ────────────────────────────────────────────────────────────────
async def main():
    """Main entry point for the agent bootstrap runner."""
    log.info(f"Starting {AGENT_ID} bootstrap runner")
    
    # Display onboarding message
    display_onboarding()
    
    # Determine prompt text to use
    custom_prompt = None
    
    # Option 1: Direct prompt text from command line
    if ARGS.prompt:
        custom_prompt = ARGS.prompt
        log.info(f"Using custom prompt from command line argument")
    
    # Option 2: Prompt from specified file
    elif ARGS.prompt_file:
        prompt_path = Path(ARGS.prompt_file)
        # If not absolute, try relative to current directory
        if not prompt_path.is_absolute():
            if prompt_path.exists():
                pass  # Use as is
            else:
                # Try in the prompt directory
                prompt_dir_path = Path(ARGS.prompt_dir) / prompt_path
                if prompt_dir_path.exists():
                    prompt_path = prompt_dir_path
                else:
                    # Try with .txt extension in prompt directory
                    prompt_dir_path = Path(ARGS.prompt_dir) / f"{prompt_path.stem}.txt"
                    if prompt_dir_path.exists():
                        prompt_path = prompt_dir_path
        
        if prompt_path.exists():
            try:
                custom_prompt = prompt_path.read_text(encoding="utf-8")
                log.info(f"Using custom prompt from file: {prompt_path}")
            except Exception as e:
                log.error(f"Error reading prompt file {prompt_path}: {e}")
                sys.exit(1)
        else:
            log.error(f"Prompt file not found: {prompt_path}")
            sys.exit(1)
    
    # Seed inbox with activation prompt if empty
    if not INBOX_PATH.exists():
        seed = {
            "prompt": custom_prompt or (
                f"**{AGENT_ID} Activation**\n\n"
                f"I am {AGENT_ID}. Systems nominal; awaiting directives."
            ),
            "prompt_id": f"SEED-{AGENT_ID}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "instruction",
            "sender": "System",
        }
        with INBOX_PATH.open("w", encoding="utf-8") as fh:
            json.dump(seed, fh, indent=2)
        log.info(f"Seed inbox created @ {INBOX_PATH}")
    # If inbox exists but we have a custom prompt, update it
    elif custom_prompt:
        try:
            with INBOX_PATH.open("r", encoding="utf-8") as fh:
                inbox_data = json.load(fh)
            
            # Update the prompt (handle both single object and list formats)
            if isinstance(inbox_data, dict):
                inbox_data["prompt"] = custom_prompt
                inbox_data["timestamp"] = datetime.now(timezone.utc).isoformat()
            elif isinstance(inbox_data, list) and inbox_data:
                inbox_data[0]["prompt"] = custom_prompt
                inbox_data[0]["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            with INBOX_PATH.open("w", encoding="utf-8") as fh:
                json.dump(inbox_data, fh, indent=2)
            log.info(f"Updated existing inbox with custom prompt @ {INBOX_PATH}")
        except Exception as e:
            log.error(f"Error updating inbox with custom prompt: {e}")
    
    # Wait before starting to allow system to stabilize
    if STARTUP_DELAY_SEC > 0 and not ARGS.no_delay:
        log.info(f"Waiting {STARTUP_DELAY_SEC} seconds before starting agent loop...")
        for remaining in range(STARTUP_DELAY_SEC, 0, -10):
            print(f"Starting in {remaining} seconds...", end="\r")
            await asyncio.sleep(min(10, remaining))
        print("Starting now!                    ")
    
    # Start agent loop
    bus = AgentBus()
    await agent_loop(bus)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutdown via KeyboardInterrupt") 