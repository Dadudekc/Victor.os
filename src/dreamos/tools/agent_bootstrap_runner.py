#!/usr/bin/env python3
"""
Dream.OS Universal Agent Bootstrap Runner – Refactored

• Cleaner structure & typing
• Centralised constants
• Robust logging (no duplicate handlers)
• Async-friendly shutdown
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import json

from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.utils.gui.injector import CursorInjector
from dreamos.utils.gui.retriever import ResponseRetriever
from .validation import validate_all_files

################################################################################
# CONFIG
################################################################################

RUNTIME_DIR          = Path("runtime")
PROMPT_DIR_DEFAULT   = RUNTIME_DIR / "prompts"
MAILBOX_ROOT         = RUNTIME_DIR / "agent_comms" / "agent_mailboxes"
DEVLOG_DIR           = RUNTIME_DIR / "devlog" / "agents"
CONTEXT_BOUNDARIES_FILE = RUNTIME_DIR / "context_boundaries.json"

HEARTBEAT_SEC        = int(os.getenv("AGENT_HEARTBEAT_SEC", 30))
LOOP_DELAY_SEC       = int(os.getenv("AGENT_LOOP_DELAY_SEC", 5))
RESPONSE_WAIT_SEC    = int(os.getenv("AGENT_RESPONSE_WAIT_SEC", 15))
RETRIEVE_RETRIES     = int(os.getenv("AGENT_RETRIEVE_RETRIES", 3))
RETRY_DELAY_SEC      = int(os.getenv("AGENT_RETRY_DELAY_SEC", 2))
STARTUP_DELAY_SEC    = int(os.getenv("AGENT_STARTUP_DELAY_SEC", 30))

# Planning steps mapping
PLANNING_STEPS = {
    1: "Strategic Planning",
    2: "Feature Documentation",
    3: "Design",
    4: "Task Planning"
}

################################################################################
# LOGGING
################################################################################

logging.basicConfig(
    level=os.getenv("AGENT_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
ROOT_LOG = logging.getLogger("bootstrap")


def init_agent_logger(agent_id: str) -> logging.Logger:
    """Return a logger unique to this agent with its own FileHandler."""
    logger = logging.getLogger(f"Agent.{agent_id}")
    if any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        return logger  # already initialised

    DEVLOG_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(DEVLOG_DIR / f"{agent_id.lower()}.log")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    logger.setLevel(os.getenv(f"AGENT_LOG_LEVEL_{agent_id.upper()}", "INFO"))
    return logger


################################################################################
# DATA CLASSES
################################################################################

# Define AGENT_STATE_FILE path globally for the new function
AGENT_STATE_FILE = Path("runtime/state/agent_last_activity.json")

def update_agent_activity(agent_id: str, logger_instance: logging.Logger):
    """Update the agent's last activity timestamp in a central JSON file."""
    try:
        AGENT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if AGENT_STATE_FILE.exists():
            try:
                with open(AGENT_STATE_FILE, "r") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                logger_instance.warning(f"Could not decode {AGENT_STATE_FILE}, initializing new state.")
                data = {}
        else:
            data = {}
        
        data[agent_id] = datetime.now(timezone.utc).isoformat()
        
        with open(AGENT_STATE_FILE, "w") as f:
            json.dump(data, f, indent=2)
        logger_instance.debug(f"Updated last activity for {agent_id} in {AGENT_STATE_FILE}")
    except Exception as e:
        logger_instance.error(f"Failed to update agent activity for {agent_id}: {e}")


@dataclass
class AgentConfig:
    """Configuration for agent bootstrap runner"""
    agent_id: str
    prompt_dirs: List[Path] = None
    heartbeat_sec: int = HEARTBEAT_SEC
    loop_delay_sec: int = LOOP_DELAY_SEC
    response_wait_sec: int = RESPONSE_WAIT_SEC
    retrieve_retries: int = RETRIEVE_RETRIES
    retry_delay_sec: int = RETRY_DELAY_SEC
    startup_delay_sec: int = STARTUP_DELAY_SEC
    mailbox_dir: Path = MAILBOX_ROOT
    no_delay: bool = False
    once: bool = False
    
    def __post_init__(self):
        # Ensure agent_id is valid
        if not self._validate_agent_id(self.agent_id):
            raise ValueError(f"Invalid agent ID: {self.agent_id}")
        
        # Set default prompt dirs if not provided
        if self.prompt_dirs is None:
            self.prompt_dirs = [PROMPT_DIR_DEFAULT]
            
        # Ensure all prompt dirs exist
        for prompt_dir in self.prompt_dirs:
            prompt_dir.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def _validate_agent_id(agent_id: str) -> bool:
        """Validate agent ID"""
        try:
            if not agent_id.startswith("Agent-"):
                return False
            agent_num = int(agent_id.split("-")[1])
            return 1 <= agent_num <= 8
        except (ValueError, IndexError):
            return False


################################################################################
# BOOTSTRAP RUNNER IMPLEMENTATION
################################################################################

class AgentStateManager:
    """Manages agent state during bootstrap process"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = config.agent_id
        self.logger = logging.getLogger(f"bootstrap.{self.agent_id}")
        self.agent_bus = AgentBus(self.agent_id)
        self.state: Dict = self._load_initial_state()
        
    def _load_initial_state(self) -> Dict:
        """Load initial agent state"""
        return {
            "agent_id": self.agent_id,
            "last_prompt": None,
            "last_response": None,
            "last_heartbeat": None,
            "startup_time": datetime.now(timezone.utc).isoformat(),
            "cycle_count": 0,
            "planning_phase": None,  # Track current planning phase
            "context_boundary": None,  # Track last context boundary
        }
        
    def update_state(self, **kwargs) -> None:
        """Update agent state with provided values"""
        self.state.update(**kwargs)
        
    def get_state(self) -> Dict:
        """Get current agent state"""
        return self.state.copy()
    
    def increment_cycle_count(self) -> int:
        """Increment and return cycle count"""
        self.state["cycle_count"] += 1
        return self.state["cycle_count"]

    def check_context_boundaries(self) -> Optional[Dict]:
        """Check for context boundaries and update state if found"""
        try:
            if not CONTEXT_BOUNDARIES_FILE.exists():
                return None
                
            with open(CONTEXT_BOUNDARIES_FILE, "r") as f:
                boundaries = json.load(f)
                
            if not boundaries.get("boundaries"):
                return None
                
            # Find the most recent boundary
            boundaries_list = boundaries.get("boundaries", [])
            if not boundaries_list:
                return None
                
            # Sort by timestamp
            sorted_boundaries = sorted(
                boundaries_list, 
                key=lambda x: x.get("timestamp", ""), 
                reverse=True
            )
            
            latest_boundary = sorted_boundaries[0]
            current_boundary = self.state.get("context_boundary")
            
            # Check if this is a new boundary
            if (current_boundary is None or 
                latest_boundary.get("boundary_id") != current_boundary.get("boundary_id")):
                self.update_state(
                    context_boundary=latest_boundary,
                    planning_phase=latest_boundary.get("phase")
                )
                return latest_boundary
                
            return None
                
        except Exception as e:
            self.logger.error(f"Error checking context boundaries: {e}")
            return None


class TaskManager:
    """Manages tasks for the agent"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = config.agent_id
        self.logger = logging.getLogger(f"bootstrap.{self.agent_id}.tasks")
        
    def get_current_tasks(self) -> List[Dict]:
        """Get current tasks for the agent"""
        # Implementation would retrieve tasks from task board
        return []
        
    def get_tasks_by_planning_step(self, planning_step: int) -> List[Dict]:
        """Get tasks filtered by planning step"""
        tasks = self.get_current_tasks()
        return [t for t in tasks if t.get("planning_step") == planning_step]


class PromptManager:
    """Manages prompts for the agent"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = config.agent_id
        self.prompt_dirs = config.prompt_dirs
        self.logger = logging.getLogger(f"bootstrap.{self.agent_id}.prompts")
        
    def get_available_prompts(self) -> List[str]:
        """Get list of available prompt files"""
        prompts = []
        for prompt_dir in self.prompt_dirs:
            prompts.extend([
                p.stem for p in prompt_dir.glob("*.prompt.md") 
                if p.is_file()
            ])
        return sorted(prompts)
    
    def load_prompt(self, prompt_name: str) -> Optional[str]:
        """Load prompt content by name"""
        # Check each prompt directory for the file
        for prompt_dir in self.prompt_dirs:
            prompt_path = prompt_dir / f"{prompt_name}.prompt.md"
            if prompt_path.exists():
                try:
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception as e:
                    self.logger.error(f"Error reading prompt {prompt_path}: {e}")
                    return None
        
        self.logger.error(f"Prompt not found: {prompt_name}")
        return None
        
    def get_prompt_by_planning_step(self, planning_step: int) -> Optional[str]:
        """Get prompt appropriate for the current planning step"""
        step_name = PLANNING_STEPS.get(planning_step)
        if not step_name:
            return None
            
        # Try to find a matching prompt
        step_prompt_name = f"{self.agent_id.lower()}_{step_name.lower().replace(' ', '_')}"
        prompt_content = self.load_prompt(step_prompt_name)
        
        # If not found, try a generic planning step prompt
        if not prompt_content:
            generic_prompt_name = f"planning_step_{planning_step}"
            prompt_content = self.load_prompt(generic_prompt_name)
            
        return prompt_content


class DevlogManager:
    """Manages devlog entries for the agent"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = config.agent_id
        self.devlog_dir = DEVLOG_DIR / self.agent_id.lower()
        self.devlog_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(f"bootstrap.{self.agent_id}.devlog")
        
    def log_boundary_transition(self, boundary: Dict) -> None:
        """Log a context boundary transition to the devlog"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        devlog_file = self.devlog_dir / f"boundary_transition_{timestamp}.md"
        
        content = f"""# Context Boundary Transition

## Metadata
- **Timestamp:** {datetime.now().isoformat()}
- **Agent:** {self.agent_id}
- **Boundary ID:** {boundary.get('boundary_id')}
- **Planning Phase:** {boundary.get('phase')}

## Context Status
- **Reason:** {boundary.get('reason')}
- **Action Required:** Create new chat window after this transition

This log marks a context boundary transition where a new chat window should be created
to preserve token context and maintain clean state separation between planning phases.
"""
        
        try:
            with open(devlog_file, "w") as f:
                f.write(content)
                
            self.logger.info(f"Logged boundary transition to {devlog_file}")
        except Exception as e:
            self.logger.error(f"Error logging boundary transition: {e}")


class AgentBootstrapRunner:
    """Main bootstrap runner class"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = config.agent_id
        self.logger = logging.getLogger(f"bootstrap.{self.agent_id}")
        
        # Initialize components
        self.state_manager = AgentStateManager(config)
        self.task_manager = TaskManager(config)
        self.prompt_manager = PromptManager(config)
        self.devlog_manager = DevlogManager(config)
        
        # Initialize GUI interaction components
        self.cursor_injector = CursorInjector(agent_id=self.agent_id)
        self.response_retriever = ResponseRetriever(agent_id=self.agent_id)
        
        # Track run state
        self.running = False
        self.shutdown_requested = False
        
    async def run(self) -> None:
        """Run the agent bootstrap process"""
        self.running = True
        self.logger.info(f"Starting {self.agent_id} bootstrap runner")
        
        try:
            # Initial startup delay unless disabled
            if not self.config.no_delay:
                self.logger.info(f"Initial startup delay: {self.config.startup_delay_sec}s")
                await asyncio.sleep(self.config.startup_delay_sec)
            
            # Main agent loop
            planning_only = os.getenv("PLANNING_ONLY_MODE", "false").lower() == "true"

            while self.running and not self.shutdown_requested:
                # Check for context boundaries
                boundary = self.state_manager.check_context_boundaries()
                if boundary:
                    self.logger.info(f"Context boundary detected: {boundary.get('phase')}")
                    self.devlog_manager.log_boundary_transition(boundary)
                
                # Increment cycle count
                cycle = self.state_manager.increment_cycle_count()
                self.logger.info(f"Starting cycle {cycle}")
                
                # Execute core agent logic unless planning_only_mode is active
                if planning_only:
                    self.logger.info("Planning Only Mode enabled - skipping core logic")
                    success = True
                else:
                    success = self._execute_core_agent_logic()
                
                # Break after one cycle if configured for once mode
                if self.config.once:
                    self.logger.info("Once mode enabled, exiting after first cycle")
                    break
                
                # Sleep before next cycle
                await asyncio.sleep(self.config.loop_delay_sec)
                
            self.logger.info(f"Agent {self.agent_id} bootstrap runner completed")
            
        except asyncio.CancelledError:
            self.logger.info("Bootstrap runner cancelled")
            self.shutdown_requested = True
        except Exception as e:
            self.logger.error(f"Error in bootstrap runner: {e}", exc_info=True)
        finally:
            self.running = False
            
    def shutdown(self) -> None:
        """Request graceful shutdown of runner"""
        self.logger.info("Shutdown requested")
        self.shutdown_requested = True

    def _execute_core_agent_logic(self):
        """Execute core agent logic for continuous operation."""
        try:
            # Initialize agent state
            self.state = {
                "cycle_count": 0,
                "last_action": None,
                "next_action": None,
                "recovery_attempts": 0,
                "last_stop_time": None,
                "autonomy_score": 0
            }
            
            # Start agent loop
            agent_loop = AgentLoop(self.agent_id, str(self.workspace_root))
            
            # Run for target cycles
            success = agent_loop.run(target_cycles=25)
            
            if success:
                logging.info(f"Agent {self.agent_id} completed {agent_loop.cycle_count} cycles successfully")
                return True
            else:
                logging.error(f"Agent {self.agent_id} failed to complete target cycles")
                return False
                
        except Exception as e:
            logging.error(f"Error in core agent logic: {e}")
            return False


################################################################################
# ENTRY POINT
################################################################################

async def main_async() -> int:
    """Async entry point for bootstrap runner"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Agent Bootstrap Runner")
    parser.add_argument("--agent", required=True, help="Agent ID (e.g. Agent-2)")
    parser.add_argument("--no-delay", action="store_true", help="Skip startup delay")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--planning-step", type=int, choices=[1, 2, 3, 4],
                       help="Specify planning step for this run (1=Strategic, 2=Feature, 3=Design, 4=Task)")
    args = parser.parse_args()
    
    # Create agent configuration
    config = AgentConfig(
        agent_id=args.agent,
        no_delay=args.no_delay,
        once=args.once,
    )
    
    # Create and run bootstrap runner
    runner = AgentBootstrapRunner(config)
    await runner.run()
    
    return 0


if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        ROOT_LOG.info("Terminated by user.")
