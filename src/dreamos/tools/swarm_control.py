#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path
import logging
from datetime import datetime

# Add the src directory to the Python path
workspace_root = Path(__file__).parent.parent.parent
sys.path.append(str(workspace_root))

from dreamos.orchestration.swarm_controller import (
    load_config, launch_agent, terminate_agent, get_agent_status
)
from dreamos.orchestration.agent_manifest import AgentManifest

def setup_logging():
    log_dir = workspace_root / "runtime" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "swarm_control.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def send_agent_message(agent_id: str, message_type: str, content: str):
    """Send a message to an agent's inbox."""
    inbox_path = workspace_root / "runtime" / "agent_comms" / "agent_mailboxes" / agent_id / "inbox.json"
    
    if not inbox_path.exists():
        logging.error(f"Agent inbox not found: {inbox_path}")
        return False
    
    try:
        # Read existing messages
        with open(inbox_path, "r") as f:
            messages = json.load(f)
        
        # Add new message
        messages.append({
            "id": f"{message_type.upper()}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "type": message_type,
            "content": content,
            "processed": False,
            "priority": 100,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Write back
        with open(inbox_path, "w") as f:
            json.dump(messages, f, indent=2)
        
        logging.info(f"Sent {message_type} message to {agent_id}")
        return True
    except Exception as e:
        logging.error(f"Error sending message to {agent_id}: {e}")
        return False

def main():
    setup_logging()
    
    parser = argparse.ArgumentParser(description="DreamOS Swarm Control CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Agent control commands
    control_parser = subparsers.add_parser("control", help="Control agent lifecycle")
    control_parser.add_argument("action", choices=["start", "stop", "status"])
    control_parser.add_argument("agent_id", help="ID of the agent to control")
    
    # Onboarding commands
    onboard_parser = subparsers.add_parser("onboard", help="Trigger agent onboarding")
    onboard_parser.add_argument("agent_id", help="ID of the agent to onboard")
    onboard_parser.add_argument("--role", help="Optional role assignment")
    
    # Resume commands
    resume_parser = subparsers.add_parser("resume", help="Resume agent autonomy")
    resume_parser.add_argument("agent_id", help="ID of the agent to resume")
    
    # Manifest commands
    manifest_parser = subparsers.add_parser("manifest", help="Manage agent manifest")
    manifest_parser.add_argument("action", choices=["update", "show"])
    manifest_parser.add_argument("--agent-id", help="Optional agent ID to show status for")
    
    args = parser.parse_args()
    
    if args.command == "control":
        config = load_config()
        if not config:
            logging.error("Failed to load configuration")
            return 1
            
        if args.action == "start":
            agent_config = next((a for a in config.get("managed_agents", []) if a.get("agent_id") == args.agent_id), None)
            if agent_config:
                launch_agent(args.agent_id, agent_config)
            else:
                logging.error(f"Agent {args.agent_id} not found in configuration")
                
        elif args.action == "stop":
            terminate_agent(args.agent_id)
            
        elif args.action == "status":
            status = get_agent_status(args.agent_id)
            print(json.dumps(status, indent=2))
            
    elif args.command == "onboard":
        content = "Begin onboarding and initialize your personal devlog and task loop."
        if args.role:
            content += f" Assigned role: {args.role}"
        send_agent_message(args.agent_id, "onboarding", content)
        
    elif args.command == "resume":
        send_agent_message(args.agent_id, "resume", "Resume your UNIVERSAL_AGENT_LOOP immediately.")
        
    elif args.command == "manifest":
        manifest = AgentManifest(str(workspace_root))
        
        if args.action == "update":
            manifest.update_manifest()
            print("Manifest updated successfully")
            
        elif args.action == "show":
            if args.agent_id:
                status = manifest.get_agent_status(args.agent_id)
                if status:
                    print(json.dumps(status, indent=2))
                else:
                    print(f"No status found for agent {args.agent_id}")
            else:
                manifest_data = manifest.get_manifest()
                print(json.dumps(manifest_data, indent=2))
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 