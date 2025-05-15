"""
Real-time status monitor for Dream.OS agents
Provides live overview of agent health, uptime, and performance metrics
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
import psutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
LOG_DIR = Path("runtime/parallel_logs")
STATE_FILE = LOG_DIR / "launcher_state.json"
METRICS_DIR = Path("runtime/analytics")
METRICS_FILE = METRICS_DIR / "agent_metrics.json"
DEVLOG_DIR = Path("runtime/devlog/agents")

# Status indicators with ANSI colors
STATUS_SYMBOLS = {
    "running": ("\033[92m✅\033[0m", "\033[92mrunning\033[0m"),  # Green
    "crashed": ("\033[91m⚠️\033[0m", "\033[91mcrashed\033[0m"),  # Red
    "stopped": ("\033[93m⏸️\033[0m", "\033[93mstopped\033[0m"),  # Yellow
    "unknown": ("\033[90m❓\033[0m", "\033[90munknown\033[0m"),  # Gray
    "restarting": ("\033[94m🔄\033[0m", "\033[94mrestarting\033[0m")  # Blue
}

class AgentStatus:
    """Represents an agent's current status and metrics"""
    
    def __init__(self, agent_id: str, state_data: Optional[Dict] = None):
        self.agent_id = agent_id
        self.pid = state_data.get("pid") if state_data else None
        self.start_time = datetime.fromisoformat(state_data["start_time"]) if state_data and "start_time" in state_data else None
        self.restart_count = state_data.get("restart_count", 0) if state_data else 0
        self.last_restart = datetime.fromisoformat(state_data["last_restart"]) if state_data and "last_restart" in state_data else None
        self.log_file = Path(state_data["log_file"]) if state_data and "log_file" in state_data else None
        
    def check_process(self) -> Tuple[str, Optional[int]]:
        """
        Check if the agent process is running
        
        Returns:
            Tuple[str, Optional[int]]: Status and exit code if available
        """
        if not self.pid:
            return "stopped", None
            
        try:
            # Use psutil for cross-platform process checking
            process = psutil.Process(self.pid)
            if process.is_running():
                return "running", None
            return "crashed", process.wait()  # Get exit code if available
        except psutil.NoSuchProcess:
            return "crashed", None
        except psutil.AccessDenied:
            return "unknown", None
        except Exception:
            return "unknown", None
            
    def get_uptime(self) -> Optional[float]:
        """Get agent uptime in seconds"""
        if not self.start_time:
            return None
        return (datetime.now(timezone.utc) - self.start_time.replace(tzinfo=timezone.utc)).total_seconds()
        
    def get_last_activity(self) -> Optional[float]:
        """Get time since last activity in seconds"""
        devlog = DEVLOG_DIR / f"{self.agent_id.lower()}.log"
        if not devlog.exists():
            return None
            
        return time.time() - devlog.stat().st_mtime
        
    def format_status(self) -> str:
        """Format agent status for display"""
        status, exit_code = self.check_process()
        symbol, status_text = STATUS_SYMBOLS.get(status, STATUS_SYMBOLS["unknown"])
        
        # Build status line
        parts = [f"{self.agent_id} {symbol}"]
        
        # Add status and PID
        if status == "running":
            parts.append(f"{status_text} (PID {self.pid})")
        elif status == "crashed":
            parts.append(f"{status_text}{f' (exit {exit_code})' if exit_code else ''}")
        else:
            parts.append(status_text)
            
        # Add uptime if available
        uptime = self.get_uptime()
        if uptime:
            parts.append(f"uptime: {format_duration(uptime)}")
            
        # Add restart count if any
        if self.restart_count:
            parts.append(f"restarts: {self.restart_count}")
            
        # Add last activity if available
        last_activity = self.get_last_activity()
        if last_activity:
            parts.append(f"last active: {format_duration(last_activity)} ago")
            
        return " | ".join(parts)

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    elif seconds < 86400:
        return f"{seconds/3600:.1f}h"
    else:
        return f"{seconds/86400:.1f}d"

def load_state() -> Dict:
    """Load launcher state from file"""
    try:
        if STATE_FILE.exists():
            with STATE_FILE.open() as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load state file: {e}")
    return {}

def load_metrics() -> Dict:
    """Load agent metrics from file"""
    try:
        if METRICS_FILE.exists():
            with METRICS_FILE.open() as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load metrics file: {e}")
    return {}

def update_metrics(agent_id: str, status: str, uptime: Optional[float]):
    """Update agent metrics"""
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    
    metrics = load_metrics()
    agent_metrics = metrics.get(agent_id, {
        "total_restarts": 0,
        "total_runtime_seconds": 0,
        "crashes": 0,
        "last_crash": None
    })
    
    if status == "crashed" and (
        not agent_metrics["last_crash"] or 
        datetime.fromisoformat(agent_metrics["last_crash"]) < datetime.now(timezone.utc)
    ):
        agent_metrics["crashes"] += 1
        agent_metrics["last_crash"] = datetime.now(timezone.utc).isoformat()
        
    if uptime:
        agent_metrics["total_runtime_seconds"] += uptime
        
    metrics[agent_id] = agent_metrics
    
    with METRICS_FILE.open("w") as f:
        json.dump(metrics, f, indent=2)

def show_status(watch: bool = False, interval: int = 5):
    """
    Show status of all agents
    
    Args:
        watch: Whether to continuously watch status
        interval: Update interval in seconds for watch mode
    """
    def display_status():
        state = load_state()
        print("\033[2J\033[H", end="")  # Clear screen
        print("🧬 \033[1mDream.OS Agent Status\033[0m\n")  # Bold title
        
        if not state:
            print("\033[93mNo agents are currently running.\033[0m")  # Yellow warning
            print("\nTo launch agents, run:")
            print("\033[96mpython src/dreamos/tools/launch_all_agents.py\033[0m")  # Cyan command
            return
            
        for agent_id in sorted(state.keys()):
            agent = AgentStatus(agent_id, state.get(agent_id))
            print(agent.format_status())
            
            # Update metrics
            status, _ = agent.check_process()
            update_metrics(agent_id, status, agent.get_uptime())
            
        if watch:
            print(f"\nUpdating every {interval}s (Ctrl+C to exit)")
    
    try:
        while True:
            display_status()
            if not watch:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStatus watch stopped")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Show Dream.OS agent status")
    parser.add_argument(
        "-w", "--watch",
        action="store_true",
        help="Watch mode - continuously update status"
    )
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=5,
        help="Update interval in seconds for watch mode"
    )
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_args()
    show_status(watch=args.watch, interval=args.interval)

if __name__ == "__main__":
    main() 