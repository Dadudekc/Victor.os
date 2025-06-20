#!/usr/bin/env python3
"""
Context Manager for Dream.OS

This utility helps manage context boundaries between planning phases
by handling git commits and devlog entries when context forks occur.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

# Constants
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEVLOG_DIR = PROJECT_ROOT / "runtime" / "devlogs"
AGENT_DEVLOG_DIR = DEVLOG_DIR / "agents"
DEFAULT_AGENT_ID = "THEA"  # Default agent if none specified


def ensure_directory_exists(path: Path) -> None:
    """Ensure the directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)


def get_current_datetime() -> str:
    """Get current datetime in ISO format."""
    return datetime.datetime.now().isoformat()


def run_git_command(git_args: List[str], working_dir: Optional[Path] = None) -> bool:
    """Run a git command and return whether it was successful."""
    command = ["git"] + git_args
    
    try:
        process = subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True, 
            cwd=working_dir or PROJECT_ROOT
        )
        print(f"Git command successful: {' '.join(command)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing Git command {' '.join(command)}: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return False


def create_git_commit(message: str) -> bool:
    """Create a git commit with the specified message."""
    # First add all changes
    if not run_git_command(["add", "."]):
        return False
    
    # Then commit with the message
    return run_git_command(["commit", "-m", message])


def get_or_create_devlog_file(agent_id: str) -> Path:
    """Get or create the devlog file for the specified agent."""
    ensure_directory_exists(AGENT_DEVLOG_DIR)
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    if agent_id.lower() == "thea":
        # THEA uses a system-level devlog
        devlog_file = DEVLOG_DIR / f"devlog_{today}.md"
    else:
        # Agent-specific devlog
        devlog_file = AGENT_DEVLOG_DIR / f"Agent-{agent_id}.md"
    
    # Create file if it doesn't exist
    if not devlog_file.exists():
        devlog_file.touch()
    
    return devlog_file


def add_context_fork_entry(
    agent_id: str,
    fork_source: str,
    fork_target: str, 
    planning_step: int,
    reason: str,
    tags: List[str] = None
) -> bool:
    """Add a context_fork entry to the agent's devlog."""
    devlog_file = get_or_create_devlog_file(agent_id)
    tags = tags or []
    tags.append("context_fork")
    
    # Format tags as hashtags
    formatted_tags = " ".join([f"#{tag}" for tag in tags])
    
    # Create the entry
    entry = f"""
**Context Fork - Agent-{agent_id} - Planning Step {planning_step}**

* **Timestamp:** {get_current_datetime()}
* **Status:** FORKED
* **Fork Source:** {fork_source}
* **Fork Target:** {fork_target}
* **Planning Step:** {planning_step}
* **Reason:** {reason}
* **Tags:** {formatted_tags}
"""
    
    # Append the entry to the devlog
    with open(devlog_file, "a") as f:
        f.write(entry)
    
    print(f"Added context fork entry to {devlog_file}")
    return True


def update_episode_metadata(episode_id: str, context_fork: Dict) -> bool:
    """Update episode metadata with context fork information."""
    episode_metadata_file = PROJECT_ROOT / "episodes" / f"episode_{episode_id}" / "metadata.yaml"
    
    if not episode_metadata_file.exists():
        print(f"Episode metadata file {episode_metadata_file} not found")
        return False
    
    try:
        import yaml
        
        # Read existing metadata
        with open(episode_metadata_file, "r") as f:
            metadata = yaml.safe_load(f) or {}
        
        # Add context fork information
        context_forks = metadata.get("context_forks", [])
        context_forks.append(context_fork)
        metadata["context_forks"] = context_forks
        
        # Write updated metadata
        with open(episode_metadata_file, "w") as f:
            yaml.dump(metadata, f, default_flow_style=False)
        
        print(f"Updated episode metadata at {episode_metadata_file}")
        return True
    except Exception as e:
        print(f"Error updating episode metadata: {e}")
        return False


def context_commit_macro(
    agent_id: str,
    planning_step: int,
    fork_source: str,
    fork_target: str,
    reason: str,
    episode_id: Optional[str] = None,
    commit: bool = True,
    tags: List[str] = None
) -> bool:
    """
    Main function to handle context forking.
    
    1. Creates a git commit to lock the current state
    2. Adds a context_fork entry to the devlog
    3. Updates episode metadata if episode_id is provided
    
    Args:
        agent_id: ID of the agent making the fork
        planning_step: The planning step number (1-4)
        fork_source: Description of the source context
        fork_target: Description of the target context
        reason: Reason for forking context
        episode_id: Optional episode ID to update metadata
        commit: Whether to create a git commit
        tags: Additional tags for the devlog entry
        
    Returns:
        Whether the operation was successful
    """
    success = True
    
    # Step 1: Create git commit if requested
    if commit:
        commit_message = f"Context Fork: {fork_source} → {fork_target} (Planning Step {planning_step})"
        if not create_git_commit(commit_message):
            print("Warning: Failed to create git commit")
            success = False
    
    # Step 2: Add devlog entry
    if not add_context_fork_entry(agent_id, fork_source, fork_target, planning_step, reason, tags):
        print("Warning: Failed to add context fork entry to devlog")
        success = False
    
    # Step 3: Update episode metadata if episode_id provided
    if episode_id:
        context_fork = {
            "timestamp": get_current_datetime(),
            "agent_id": agent_id,
            "planning_step": planning_step,
            "fork_source": fork_source,
            "fork_target": fork_target,
            "reason": reason,
        }
        if not update_episode_metadata(episode_id, context_fork):
            print("Warning: Failed to update episode metadata")
            success = False
    
    return success


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Dream.OS Context Manager")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Fork context command
    fork_parser = subparsers.add_parser("fork", help="Fork context")
    fork_parser.add_argument("--agent", "-a", default=DEFAULT_AGENT_ID, help="Agent ID (default: THEA)")
    fork_parser.add_argument("--planning-step", "-p", type=int, required=True, choices=[1, 2, 3, 4], 
                            help="Planning step (1-4)")
    fork_parser.add_argument("--source", "-s", required=True, help="Source context description")
    fork_parser.add_argument("--target", "-t", required=True, help="Target context description")
    fork_parser.add_argument("--reason", "-r", required=True, help="Reason for context fork")
    fork_parser.add_argument("--episode", "-e", help="Episode ID (optional)")
    fork_parser.add_argument("--no-commit", action="store_true", help="Don't create a git commit")
    fork_parser.add_argument("--tags", nargs="+", help="Additional tags for devlog entry")
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    if args.command == "fork":
        success = context_commit_macro(
            agent_id=args.agent,
            planning_step=args.planning_step,
            fork_source=args.source,
            fork_target=args.target,
            reason=args.reason,
            episode_id=args.episode,
            commit=not args.no_commit,
            tags=args.tags
        )
        sys.exit(0 if success else 1)
    else:
        print("No command specified. Use --help for usage information.")
        sys.exit(1)


if __name__ == "__main__":
    main() 