"""
Configuration settings for Agent Bootstrap Runner
"""

import os
import logging
import argparse
import re
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Get project root
PROJECT_ROOT = Path(__file__).resolve().parents[4]  # src/dreamos/tools/agent2_bootstrap_runner -> Dream.os

# Default agent identity - can be overridden via CLI args
AGENT_ID: str = "Agent-1"  # Default agent for universal runner

# Validate agent number is in valid range
def validate_agent_id(agent_id: str) -> bool:
    """Validate agent ID is in the correct format and range."""
    try:
        if not agent_id.startswith("Agent-"):
            return False
        agent_num = int(agent_id.split("-")[1])
        return 1 <= agent_num <= 8  # Agent-0 is not valid
    except (ValueError, IndexError):
        return False

# Runtime configuration with env var overrides
HEARTBEAT_SEC = float(os.getenv("AGENT_HEARTBEAT_SEC", "30"))
LOOP_DELAY_SEC = float(os.getenv("AGENT_LOOP_DELAY_SEC", "5"))
RESPONSE_WAIT_SEC = float(os.getenv("AGENT_RESPONSE_WAIT_SEC", "15"))
RETRIEVE_RETRIES = int(os.getenv("AGENT_RETRIEVE_RETRIES", "3"))
RETRY_DELAY_SEC = float(os.getenv("AGENT_RETRY_DELAY_SEC", "2"))
STARTUP_DELAY_SEC = int(os.getenv("AGENT_STARTUP_DELAY_SEC", "30"))  # Default 30s
LOG_LEVEL = os.getenv("AGENT_LOG_LEVEL", "INFO").upper()

# Default prompt directory
DEFAULT_PROMPT_DIR = "runtime/prompts"

# Agent-specific traits and charters
AGENT_TRAITS = {
    "Agent-1": "Strategic, Analytical, Decisive",
    "Agent-2": "Creative, Innovative, Adaptable",
    "Agent-3": "Methodical, Precise, Detail-oriented",
    "Agent-4": "Collaborative, Communicative, Supportive",
    "Agent-5": "Investigative, Thorough, Persistent",
    "Agent-6": "Efficient, Organized, Systematic",
    "Agent-7": "Intuitive, Perceptive, Insightful",
    "Agent-8": "Balanced, Reliable, Consistent"
}

AGENT_CHARTERS = {
    "Agent-1": "Strategic Planning and Decision Making",
    "Agent-2": "Innovation and Creative Problem Solving",
    "Agent-3": "Quality Assurance and Verification",
    "Agent-4": "Team Coordination and Support",
    "Agent-5": "Research and Analysis",
    "Agent-6": "Process Optimization and Automation",
    "Agent-7": "Pattern Recognition and Insights",
    "Agent-8": "System Stability and Reliability"
}

# Performance limits
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_LINES_PER_EDIT = 600
MAX_SEARCH_DEPTH = 10
MAX_SUBDIRS = 5
MAX_RECOVERY_ATTEMPTS = 3

# Target latencies (in milliseconds)
TARGET_FILE_OPS_MS = 50
TARGET_SEARCH_MS = 200
TARGET_VALIDATION_MS = 150

# Maintenance configuration
MAINTENANCE_INTERVAL_HOURS = int(os.getenv("AGENT_MAINTENANCE_INTERVAL_HOURS", "24"))
MAINTENANCE_BACKUP_RETENTION_DAYS = int(os.getenv("AGENT_MAINTENANCE_BACKUP_RETENTION_DAYS", "30"))

class AgentConfig:
    """Configuration for agent bootstrap runner"""
    
    def __init__(
        self,
        agent_id: str,
        base_runtime: Optional[Path] = None,
        loop_delay_sec: int = LOOP_DELAY_SEC,
        retry_delay_sec: int = RETRY_DELAY_SEC,
        heartbeat_sec: int = HEARTBEAT_SEC,
        startup_delay_sec: Optional[int] = None,
        retrieve_retries: int = RETRIEVE_RETRIES,
        response_wait_sec: float = RESPONSE_WAIT_SEC,
        max_file_size_bytes: int = MAX_FILE_SIZE_BYTES,
        max_lines_per_edit: int = MAX_LINES_PER_EDIT,
        max_search_depth: int = MAX_SEARCH_DEPTH,
        max_subdirs: int = MAX_SUBDIRS,
        max_recovery_attempts: int = MAX_RECOVERY_ATTEMPTS,
        target_file_ops_ms: int = TARGET_FILE_OPS_MS,
        target_search_ms: int = TARGET_SEARCH_MS,
        target_validation_ms: int = TARGET_VALIDATION_MS
    ):
        """
        Initialize agent configuration
        
        Args:
            agent_id: Unique identifier for the agent
            base_runtime: Base directory for runtime files
            loop_delay_sec: Delay between loop cycles
            retry_delay_sec: Delay before retrying after error
            heartbeat_sec: Interval for heartbeat messages
            startup_delay_sec: Override for startup delay (None uses default)
            retrieve_retries: Number of times to retry retrieving response
            response_wait_sec: Time to wait between response checks
            max_file_size_bytes: Maximum file size to process
            max_lines_per_edit: Maximum lines per edit operation
            max_search_depth: Maximum directory depth for searches
            max_subdirs: Maximum number of subdirectories to search
            max_recovery_attempts: Maximum number of recovery attempts
            target_file_ops_ms: Target latency for file operations
            target_search_ms: Target latency for search operations
            target_validation_ms: Target latency for validation operations
        """
        if not re.match(r"^Agent-[1-8]$", agent_id):
            raise ValueError(f"Invalid agent ID: {agent_id}. Must be in format 'Agent-N' where N is 1-8")
            
        self.agent_id = agent_id
        
        # Extract numeric part of agent ID for retriever
        self.agent_num = agent_id.split("-")[1]
        
        # Timing configuration
        self.loop_delay_sec = loop_delay_sec
        self.retry_delay_sec = retry_delay_sec
        self.heartbeat_sec = heartbeat_sec
        self.startup_delay_sec = startup_delay_sec if startup_delay_sec is not None else STARTUP_DELAY_SEC
        self.retrieve_retries = retrieve_retries
        self.response_wait_sec = response_wait_sec
            
        # Agent-specific paths
        self.base_runtime = base_runtime or PROJECT_ROOT / "runtime/agent_comms/agent_mailboxes" / agent_id
        
        # Standard mailbox directories
        self.inbox_dir = self.base_runtime / "inbox"
        self.outbox_dir = self.base_runtime / "outbox"
        self.processed_dir = self.base_runtime / "processed"
        self.state_dir = self.base_runtime / "state"
        self.workspace_dir = self.base_runtime / "workspace"
        
        # State tracking
        self.state_file = self.state_dir / "agent_state.json"
        
        # Devlog path
        self.devlog_path = PROJECT_ROOT / f"runtime/devlog/agents/{agent_id.lower()}.log"
        
        # Coordinates file paths
        self.coords_file = PROJECT_ROOT / "runtime/config/cursor_agent_coords.json"
        self.copy_coords_file = PROJECT_ROOT / "runtime/config/cursor_agent_copy_coords.json"
        
        # Protocol paths
        self.protocol_dir = PROJECT_ROOT / "runtime/governance/protocols"
        self.inbox_loop_protocol = self.protocol_dir / "INBOX_LOOP_PROTOCOL.md"
        
        # Agent traits and charter
        self.traits = AGENT_TRAITS.get(agent_id, "Versatile, Adaptive, Reliable, Focused")
        self.charter = AGENT_CHARTERS.get(agent_id, "General Purpose Agent")
        
        # Agent ID for retriever (format: agent_XX)
        self.agent_id_for_retriever = f"agent_{self.agent_num.zfill(2)}"
        
        # Performance limits
        self.max_file_size_bytes = max_file_size_bytes
        self.max_lines_per_edit = max_lines_per_edit
        self.max_search_depth = max_search_depth
        self.max_subdirs = max_subdirs
        self.max_recovery_attempts = max_recovery_attempts
        
        # Target latencies
        self.target_file_ops_ms = target_file_ops_ms
        self.target_search_ms = target_search_ms
        self.target_validation_ms = target_validation_ms
        
        # Maintenance configuration
        self.maintenance_interval_hours = MAINTENANCE_INTERVAL_HOURS
        self.maintenance_backup_retention_days = MAINTENANCE_BACKUP_RETENTION_DAYS
        
        # Project root for maintenance tasks
        self.project_root = PROJECT_ROOT
        
        # Create directories
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure all required directories exist"""
        directories = [
            self.base_runtime,
            self.inbox_dir,
            self.outbox_dir,
            self.processed_dir,
            self.state_dir,
            self.workspace_dir,
            self.devlog_path.parent,
            self.protocol_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Log the directory creation
        logging.info(f"Created directories for {self.agent_id}")
        
        # Create empty state file if it doesn't exist
        if not self.state_file.exists():
            import json
            from datetime import datetime, timezone
            
            initial_state = {
                "cycle_count": 0,
                "last_active": datetime.now(timezone.utc).isoformat(),
                "current_task": "initializing",
                "messages_processed": 0
            }
            
            try:
                with self.state_file.open("w", encoding="utf-8") as f:
                    json.dump(initial_state, f, indent=2)
                logging.info(f"Created initial state file for {self.agent_id}")
            except Exception as e:
                logging.error(f"Failed to create state file: {e}")

    def clone_for_agent(self, new_agent_id: str) -> 'AgentConfig':
        """Create a new config instance for a different agent.
        
        Args:
            new_agent_id: ID of the agent to create config for
            
        Returns:
            New AgentConfig instance for the specified agent
        """
        return AgentConfig(
            agent_id=new_agent_id,
            base_runtime=None,  # Will be auto-generated for new agent
            loop_delay_sec=self.loop_delay_sec,
            retry_delay_sec=self.retry_delay_sec,
            heartbeat_sec=self.heartbeat_sec,
            startup_delay_sec=self.startup_delay_sec,
            retrieve_retries=self.retrieve_retries,
            response_wait_sec=self.response_wait_sec,
            max_file_size_bytes=self.max_file_size_bytes,
            max_lines_per_edit=self.max_lines_per_edit,
            max_search_depth=self.max_search_depth,
            max_subdirs=self.max_subdirs,
            max_recovery_attempts=self.max_recovery_attempts,
            target_file_ops_ms=self.target_file_ops_ms,
            target_search_ms=self.target_search_ms,
            target_validation_ms=self.target_validation_ms
        )

def create_directories(config: AgentConfig):
    """Create necessary directories for agent operation"""
    # Create all required directories
    dirs_to_create = [
        config.base_runtime,
        config.inbox_dir,
        config.outbox_dir,
        config.processed_dir,
        config.state_dir,
        config.workspace_dir,
        config.devlog_path.parent,
        config.protocol_dir
    ]
    
    for directory in dirs_to_create:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Log the directory creation
    logging.info(f"Created directories for {config.agent_id}")
    
    # Create empty state file if it doesn't exist
    if not config.state_file.exists():
        import json
        from datetime import datetime, timezone
        
        initial_state = {
            "cycle_count": 0,
            "last_active": datetime.now(timezone.utc).isoformat(),
            "current_task": "initializing",
            "messages_processed": 0
        }
        
        try:
            with config.state_file.open("w", encoding="utf-8") as f:
                json.dump(initial_state, f, indent=2)
            logging.info(f"Created initial state file for {config.agent_id}")
        except Exception as e:
            logging.error(f"Failed to create state file: {e}")

def get_coords_file_path():
    """Get the path to the coordinates file"""
    return PROJECT_ROOT / "runtime/config/cursor_agent_coords.json"

def get_copy_coords_file_path():
    """Get the path to the copy coordinates file"""
    return PROJECT_ROOT / "runtime/config/cursor_agent_copy_coords.json"

def parse_args() -> Dict[str, Any]:
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Agent Bootstrap Runner")
    parser.add_argument("--agent", required=True, help="Agent ID (e.g. Agent-2)")
    parser.add_argument("--no-delay", action="store_true", help="Skip startup delay")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    return vars(parser.parse_args()) 