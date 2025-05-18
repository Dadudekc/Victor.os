#!/usr/bin/env python3
"""
Dream.OS Context Management Utility

This tool helps manage context window boundaries for LLM-based workflows by:
1. Creating context boundary markers in devlogs
2. Committing state changes to mark clean boundaries
3. Tracking episode planning phases across sessions
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("context_manager")

# Constants
RUNTIME_DIR = Path("runtime")
DEVLOG_DIR = RUNTIME_DIR / "devlog" / "agents"
EPISODES_DIR = Path("episodes")
TASKS_DIR = RUNTIME_DIR / "tasks"
CONTEXT_BOUNDARIES_FILE = RUNTIME_DIR / "context_boundaries.json"

# Planning steps mapping
PLANNING_STEPS = {
    1: "Strategic Planning",
    2: "Feature Documentation",
    3: "Design",
    4: "Task Planning"
}

class ContextManager:
    """Manages context boundaries in LLM-based workflows"""
    
    def __init__(self, agent_id: Optional[str] = None, episode_id: Optional[str] = None):
        self.agent_id = agent_id
        self.episode_id = episode_id
        self.boundaries: Dict = self._load_boundaries()
        
    def _load_boundaries(self) -> Dict:
        """Load existing context boundaries"""
        if CONTEXT_BOUNDARIES_FILE.exists():
            try:
                with open(CONTEXT_BOUNDARIES_FILE, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Error parsing {CONTEXT_BOUNDARIES_FILE}, creating new")
                return {"boundaries": [], "current_phase": None}
        else:
            # Initialize with empty structure
            return {"boundaries": [], "current_phase": None}
    
    def _save_boundaries(self) -> None:
        """Save context boundaries to file"""
        # Ensure directory exists
        CONTEXT_BOUNDARIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(CONTEXT_BOUNDARIES_FILE, "w") as f:
            json.dump(self.boundaries, f, indent=2)
            
    def create_boundary(self, phase: str, reason: str) -> None:
        """Create a new context boundary"""
        timestamp = datetime.now().isoformat()
        
        # Create boundary entry
        boundary = {
            "timestamp": timestamp,
            "agent_id": self.agent_id,
            "episode_id": self.episode_id,
            "phase": phase,
            "reason": reason,
            "boundary_id": f"boundary-{len(self.boundaries['boundaries']) + 1}"
        }
        
        # Add to boundaries list
        self.boundaries["boundaries"].append(boundary)
        self.boundaries["current_phase"] = phase
        
        # Save updated boundaries
        self._save_boundaries()
        
        # Create devlog entry if agent_id is provided
        if self.agent_id:
            self._create_devlog_entry(boundary)
            
        logger.info(f"Created context boundary: {phase} - {reason}")
        
    def _create_devlog_entry(self, boundary: Dict) -> None:
        """Create a devlog entry for the boundary"""
        agent_devlog_dir = DEVLOG_DIR / self.agent_id.lower()
        agent_devlog_dir.mkdir(parents=True, exist_ok=True)
        
        # Create devlog filename with timestamp
        timestamp = datetime.fromisoformat(boundary["timestamp"]).strftime("%Y%m%d-%H%M%S")
        devlog_file = agent_devlog_dir / f"context_boundary_{timestamp}.md"
        
        # Write devlog content
        content = f"""# Context Boundary: {boundary['phase']}

## Metadata
- **Timestamp:** {boundary['timestamp']}
- **Agent:** {boundary['agent_id']}
- **Episode:** {boundary['episode_id']}
- **Boundary ID:** {boundary['boundary_id']}
- **Reason:** {boundary['reason']}

## Context Status
- **Planning Phase:** {boundary['phase']} 
- **Next Actions:** New chat window should be created after this boundary

This log marks a context boundary where a new chat window should be created to preserve
token context and maintain clean state separation between planning phases.
"""
        with open(devlog_file, "w") as f:
            f.write(content)
            
        logger.info(f"Created devlog entry at {devlog_file}")
    
    def get_current_phase(self) -> Optional[str]:
        """Get the current planning phase"""
        return self.boundaries.get("current_phase")
    
    def list_boundaries(self) -> List[Dict]:
        """List all context boundaries"""
        return self.boundaries.get("boundaries", [])
    
    def get_episode_planning_status(self, episode_id: str) -> Dict:
        """Get planning status for a specific episode"""
        episode_file = EPISODES_DIR / f"episode-{episode_id}.yaml"
        
        if not episode_file.exists():
            logger.error(f"Episode file not found: {episode_file}")
            return {"error": "Episode file not found"}
        
        try:
            with open(episode_file, "r") as f:
                episode_data = yaml.safe_load(f)
                
            return {
                "episode_id": episode_id,
                "planning_stage": episode_data.get("planning_stage", "unknown"),
                "tasks_by_planning_step": self._count_tasks_by_planning_step(episode_data)
            }
        except Exception as e:
            logger.error(f"Error reading episode file: {e}")
            return {"error": str(e)}
    
    def _count_tasks_by_planning_step(self, episode_data: Dict) -> Dict[str, int]:
        """Count tasks by planning step"""
        counts = {step_name: 0 for _, step_name in PLANNING_STEPS.items()}
        
        # Check if agent_assignments exists
        if "agent_assignments" not in episode_data:
            return counts
        
        # Count tasks by planning step
        for agent_id, task in episode_data["agent_assignments"].items():
            planning_step = task.get("planning_step")
            if planning_step and planning_step in PLANNING_STEPS:
                step_name = PLANNING_STEPS[planning_step]
                counts[step_name] = counts.get(step_name, 0) + 1
                
        return counts
    
    def suggest_next_boundary(self, episode_id: Optional[str] = None) -> Dict:
        """Suggest next context boundary based on planning status"""
        episode_id = episode_id or self.episode_id
        
        if not episode_id:
            return {"suggestion": "No episode specified, can't suggest boundary"}
        
        # Get planning status
        planning_status = self.get_episode_planning_status(episode_id)
        
        # Extract current planning stage
        planning_stage = planning_status.get("planning_stage", "unknown")
        
        # If planning is complete, suggest task execution boundary
        if planning_stage == "complete":
            return {
                "suggestion": "Planning is complete, suggest creating task execution boundary",
                "phase": "task_execution",
                "reason": "Transition from planning to execution phase"
            }
        
        # Check task counts by planning step
        task_counts = planning_status.get("tasks_by_planning_step", {})
        
        # Determine next phase based on task counts
        if task_counts.get("Strategic Planning", 0) > 0 and task_counts.get("Feature Documentation", 0) == 0:
            return {
                "suggestion": "Strategic Planning phase has tasks, suggest Feature Documentation boundary",
                "phase": "feature_documentation",
                "reason": "Transition from Strategic Planning to Feature Documentation" 
            }
        elif task_counts.get("Feature Documentation", 0) > 0 and task_counts.get("Design", 0) == 0:
            return {
                "suggestion": "Feature Documentation phase has tasks, suggest Design boundary",
                "phase": "design",
                "reason": "Transition from Feature Documentation to Design"
            }
        elif task_counts.get("Design", 0) > 0 and task_counts.get("Task Planning", 0) == 0:
            return {
                "suggestion": "Design phase has tasks, suggest Task Planning boundary",
                "phase": "task_planning",
                "reason": "Transition from Design to Task Planning"
            }
        
        return {
            "suggestion": "Cannot determine next boundary based on current planning status",
            "phase": "unknown",
            "reason": "Insufficient information to suggest boundary"
        }


def main():
    """Main entry point for context management utility"""
    parser = argparse.ArgumentParser(description="Dream.OS Context Management Utility")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # New boundary command
    new_parser = subparsers.add_parser("new-phase", help="Create a new context boundary")
    new_parser.add_argument("--agent", help="Agent ID (e.g., Agent-2)")
    new_parser.add_argument("--episode", help="Episode ID (e.g., 08)")
    new_parser.add_argument("--phase", help="Planning phase (strategic_planning, feature_documentation, design, task_planning)")
    new_parser.add_argument("--reason", help="Reason for creating boundary")
    
    # List boundaries command
    list_parser = subparsers.add_parser("list", help="List all context boundaries")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show current context status")
    status_parser.add_argument("--episode", help="Episode ID to check status for")
    
    # Suggest boundary command
    suggest_parser = subparsers.add_parser("suggest", help="Suggest next context boundary")
    suggest_parser.add_argument("--episode", help="Episode ID to suggest boundary for")
    
    args = parser.parse_args()
    
    # Create context manager
    manager = ContextManager(args.agent if hasattr(args, "agent") else None, 
                           args.episode if hasattr(args, "episode") else None)
    
    # Handle commands
    if args.command == "new-phase":
        if not args.phase or not args.reason:
            logger.error("Phase and reason are required for new-phase command")
            return 1
            
        manager.create_boundary(args.phase, args.reason)
        print(f"Created new context boundary: {args.phase}")
        
    elif args.command == "list":
        boundaries = manager.list_boundaries()
        if not boundaries:
            print("No context boundaries found")
        else:
            print(f"Found {len(boundaries)} context boundaries:")
            for i, boundary in enumerate(boundaries, 1):
                print(f"{i}. {boundary['timestamp']} - {boundary['phase']} - {boundary['reason']}")
                
    elif args.command == "status":
        if hasattr(args, "episode") and args.episode:
            status = manager.get_episode_planning_status(args.episode)
            print(f"Episode {args.episode} planning status:")
            for key, value in status.items():
                print(f"  {key}: {value}")
        else:
            current_phase = manager.get_current_phase()
            print(f"Current planning phase: {current_phase or 'Not set'}")
            
    elif args.command == "suggest":
        episode_id = args.episode if hasattr(args, "episode") and args.episode else None
        suggestion = manager.suggest_next_boundary(episode_id)
        print("Context boundary suggestion:")
        for key, value in suggestion.items():
            print(f"  {key}: {value}")
            
    else:
        parser.print_help()
        
    return 0


if __name__ == "__main__":
    sys.exit(main()) 