"""
Dry-Run Simulator for Dream.OS Agent Bridge Loop

This script simulates the bridge loop without performing actual clicks or clipboard operations.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

from rich.console import Console
from rich.logging import RichHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("dry_run_simulator")

# Constants
PROMPT = "RESUME AUTONOMY"
COORDS_PATH = Path("runtime/config/cursor_agent_coords.json")
AGENTS = [f"Agent-{i}" for i in range(1, 9)]

console = Console()

def load_coordinates() -> Optional[Dict]:
    """Load agent coordinates from config file."""
    try:
        if not COORDS_PATH.exists():
            logger.error(f"❌ Coordinates file not found: {COORDS_PATH}")
            return None
        coords = json.loads(COORDS_PATH.read_text())
        logger.info(f"✅ Loaded coordinates for {len(coords)} agents")
        return coords
    except json.JSONDecodeError:
        logger.error("❌ Invalid JSON in coordinates file")
        return None
    except Exception as e:
        logger.error(f"❌ Error loading coordinates: {e}")
        return None

def main() -> int:
    """Simulate the bridge loop without performing actual actions."""
    console.print("[bold cyan]🚀 Starting Dry-Run Simulator[/bold cyan]")
    console.print("[bold yellow]⚠️ Dry-run mode: No clicks or clipboard operations[/bold yellow]")

    coords = load_coordinates()
    if not coords:
        return 1

    for agent_id in AGENTS:
        if agent_id not in coords:
            logger.error(f"❌ Missing coordinates for {agent_id}")
            continue

        input_box = coords[agent_id]["input_box"]
        copy_button = coords[agent_id]["copy_button"]

        logger.info(f"✅ Would send to {agent_id} → {PROMPT}")
        logger.info(f"✅ Would click copy button for {agent_id}")
        logger.info(f"[DRY-RUN] Would route clipboard content for {agent_id}")

    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dry-Run Simulator for Dream.OS Agent Bridge Loop")
    args = parser.parse_args()
    sys.exit(main()) 