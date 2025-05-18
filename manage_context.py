#!/usr/bin/env python3
"""
Dream.OS Context Management CLI

A command-line interface for managing context boundaries in LLM-based workflows.
This is a wrapper around the core context management functionality in src/dreamos/tools/manage_context.py.
"""

import argparse
import os
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from dreamos.tools.manage_context import ContextManager

def main():
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(
        description="Dream.OS Context Management Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new context boundary for transitioning from strategic planning to feature documentation
  python manage_context.py new-phase --agent Agent-1 --episode 08 --phase feature_documentation --reason "Completed strategic planning phase"
  
  # List all context boundaries
  python manage_context.py list
  
  # Check status of a specific episode
  python manage_context.py status --episode 08
  
  # Get suggestion for next context boundary
  python manage_context.py suggest --episode 08
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # New boundary command
    new_parser = subparsers.add_parser("new-phase", help="Create a new context boundary")
    new_parser.add_argument("--agent", required=True, help="Agent ID (e.g., Agent-2)")
    new_parser.add_argument("--episode", required=True, help="Episode ID (e.g., 08)")
    new_parser.add_argument("--phase", required=True, 
                           choices=["strategic_planning", "feature_documentation", "design", "task_planning", "task_execution"],
                           help="Planning phase")
    new_parser.add_argument("--reason", required=True, help="Reason for creating boundary")
    
    # List boundaries command
    subparsers.add_parser("list", help="List all context boundaries")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show current context status")
    status_parser.add_argument("--episode", required=True, help="Episode ID to check status for")
    
    # Suggest boundary command
    suggest_parser = subparsers.add_parser("suggest", help="Suggest next context boundary")
    suggest_parser.add_argument("--episode", required=True, help="Episode ID to suggest boundary for")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle commands
    if args.command is None:
        parser.print_help()
        return 0
    
    # Create context manager
    manager = ContextManager(
        agent_id=args.agent if hasattr(args, "agent") else None,
        episode_id=args.episode if hasattr(args, "episode") else None
    )
    
    if args.command == "new-phase":
        manager.create_boundary(args.phase, args.reason)
        print(f"Created new context boundary: {args.phase}")
        if args.phase == "task_execution":
            print("\nIMPORTANT: You should now create a new chat window (Ctrl+N) to start task execution with a clean context.")
        else:
            print(f"\nIMPORTANT: You should now create a new chat window (Ctrl+N) to start the {args.phase.replace('_', ' ')} phase with a clean context.")
        
    elif args.command == "list":
        boundaries = manager.list_boundaries()
        if not boundaries:
            print("No context boundaries found")
        else:
            print(f"Found {len(boundaries)} context boundaries:")
            for i, boundary in enumerate(boundaries, 1):
                print(f"{i}. {boundary['timestamp']} - {boundary['phase']} - {boundary['reason']}")
                
    elif args.command == "status":
        status = manager.get_episode_planning_status(args.episode)
        print(f"\nEpisode {args.episode} planning status:")
        print(f"Planning stage: {status.get('planning_stage', 'unknown')}")
        
        print("\nTasks by planning step:")
        for step, count in status.get("tasks_by_planning_step", {}).items():
            print(f"  {step}: {count} tasks")
            
    elif args.command == "suggest":
        suggestion = manager.suggest_next_boundary(args.episode)
        print("\nContext boundary suggestion:")
        print(f"  Suggestion: {suggestion['suggestion']}")
        print(f"  Phase: {suggestion['phase']}")
        print(f"  Reason: {suggestion['reason']}")
        
        if suggestion["phase"] != "unknown":
            print("\nTo create this boundary, run:")
            print(f"  python manage_context.py new-phase --agent <agent-id> --episode {args.episode} --phase {suggestion['phase']} --reason \"{suggestion['reason']}\"")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 