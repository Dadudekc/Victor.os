import json
import logging
import time
from pathlib import Path
import pyautogui
import pyperclip
import argparse
from enum import Enum
from typing import Optional, Dict, List, Any
import os
import sys
from datetime import datetime, timezone

# EDIT START: Fix project_root to point to the repo root, not src/dreamos
# Rationale: The config files are located at <repo_root>/runtime/config/templates, not under src/dreamos. This ensures correct path resolution regardless of where the script is run from.
project_root = Path(__file__).resolve().parents[3]
# EDIT END
sys.path.append(str(project_root))

from dreamos.tools.cursor_controller import CursorController
from dreamos.core.agent_registry import AgentRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('agent_cellphone')

class MessageMode(Enum):
    RESUME = "[RESUME]"
    SYNC = "[SYNC]"
    VERIFY = "[VERIFY]"
    REPAIR = "[REPAIR]"
    BACKUP = "[BACKUP]"
    RESTORE = "[RESTORE]"
    CLEANUP = "[CLEANUP]"
    CAPTAIN = "[CAPTAIN]"
    TASK = "[TASK]"
    INTEGRATE = "[INTEGRATE]"
    NORMAL = ""  # No additional tags

def send_cell_phone_message(from_agent, to_agent, message, priority=2):
    """Send a message from one agent to another using the cellphone system."""
    try:
        cellphone = AgentCellphone(agent_id=from_agent)  # Use from_agent as the sender
        return cellphone.message_agent(to_agent, message, mode=MessageMode.RESUME)  # Use RESUME mode to add tags
    except Exception as e:
        logger.error(f"Failed to send cell phone message from {from_agent} to {to_agent}: {e}")
        return False

class AgentCellphone:
    def __init__(self):
        self.cursor = CursorController()
        self.registry = AgentRegistry()
        self.config_dir = project_root / "runtime" / "config"
        self.coords_file = self.config_dir / "cursor_agent_coords.json"
        self.modes_file = self.config_dir / "templates" / "agent_modes.json"
        self.load_configs()

    def load_configs(self):
        """Load configuration files"""
        try:
            with open(self.coords_file, 'r') as f:
                self.coords = json.load(f)
            with open(self.modes_file, 'r') as f:
                self.modes = json.load(f)
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {e}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing configuration file: {e}")
            sys.exit(1)

    def get_agent_coords(self, agent_id: str) -> Dict[str, Any]:
        """Get coordinates for a specific agent"""
        if agent_id not in self.coords:
            raise ValueError(f"Agent {agent_id} not found in coordinates file")
        
        coords = self.coords[agent_id]
        if not isinstance(coords, dict):
            raise ValueError(f"Invalid coordinate format for {agent_id}")
        
        required_keys = ["input_box", "initial_spot"]
        missing_keys = [key for key in required_keys if key not in coords]
        
        if missing_keys:
            raise ValueError(f"Agent {agent_id} is missing required coordinates: {', '.join(missing_keys)}")
        
        return coords

    def validate_coordinates(self, x: int, y: int) -> bool:
        """Validate if coordinates are within screen bounds, including negative values for multi-monitor setups"""
        try:
            # Get all monitor information
            monitors = pyautogui.getAllMonitors()
            
            # Check if coordinates are within any monitor's bounds
            for monitor in monitors:
                if (monitor.left <= x <= monitor.left + monitor.width and 
                    monitor.top <= y <= monitor.top + monitor.height):
                    return True
            
            # If we get here, coordinates are not within any monitor
            logger.warning(f"Coordinates ({x}, {y}) are not within any monitor bounds")
            return False
            
        except Exception as e:
            logger.error(f"Error validating coordinates: {e}")
            return False

    def get_mode_template(self, mode: str, **kwargs) -> str:
        """Get the prompt template for a specific mode"""
        if mode not in self.modes["modes"]:
            raise ValueError(f"Mode {mode} not found in modes configuration")
        
        template = self.modes["modes"][mode]["prompt_template"]
        return template.format(**kwargs)

    def send_message(self, agent_id: str, message: str, mode: MessageMode = MessageMode.NORMAL):
        """Send a message to a specific agent"""
        try:
            coords = self.get_agent_coords(agent_id)
            
            # Format message with mode tag if needed
            if mode != MessageMode.NORMAL:
                message = f"{mode.value} {message}"
            
            # Click input box
            input_box = coords["input_box"]
            self.cursor.move_to(input_box["x"], input_box["y"])
            self.cursor.click()
            time.sleep(0.5)
            
            # Type message
            self.cursor.type_text(message)
            time.sleep(0.5)
            
            # Press Enter to send
            self.cursor.press_enter()
            time.sleep(1)
            
            # If this is part of initialization sequence, wait longer
            if "Confirm your identity" in message or "Load your core protocols" in message or \
               "Initialize your state management" in message or "Connect to the agent registry" in message or \
               "Establish communication channels" in message or "Report your initialization status" in message:
                time.sleep(2)  # Wait longer for initialization steps
            
            logger.info(f"Message sent to {agent_id} with mode {mode.value}")
            
        except Exception as e:
            logger.error(f"Error sending message to {agent_id}: {e}")
            raise

    def onboard_agent(self, agent_id: str, message: str):
        """Onboard a new agent with initial setup"""
        try:
            coords = self.get_agent_coords(agent_id)
            
            # Click the input box directly - no need to click initial spot first
            input_box = coords["input_box"]
            self.cursor.move_to(input_box["x"], input_box["y"])
            self.cursor.click()
            time.sleep(0.5)
            
            # Type and send the welcome message
            if not message:
                message = f"""Welcome to Dream.os! You are now {agent_id}.

Please initialize with the following sequence:
1. Confirm your identity as {agent_id}
2. Load your core protocols
3. Initialize your state management system
4. Connect to the agent registry
5. Establish communication channels
6. Report your initialization status

Once initialized, you will be integrated into the Dream.os swarm network.
Please proceed with the initialization sequence and report your status."""

            # Type message
            self.cursor.type_text(message)
            time.sleep(0.5)
            
            # Press Enter to send
            self.cursor.press_enter()
            time.sleep(1)
            
            # Update registry
            self.registry.register_agent(agent_id)
            
            logger.info(f"Onboarded agent {agent_id} with message: {message}")
            
        except Exception as e:
            logger.error(f"Error onboarding agent {agent_id}: {e}")
            raise

    def execute_mode(self, agent_id: str, mode: str, **kwargs):
        """Execute a specific mode for an agent"""
        try:
            # Get the template for the mode
            template = self.get_mode_template(mode, agent_id=agent_id, **kwargs)
            
            # Map mode string to MessageMode enum
            mode_enum = MessageMode[mode.upper()]
            
            # Send the formatted message
            self.send_message(agent_id, template, mode_enum)
            
            logger.info(f"Executed {mode} mode for {agent_id}")
            
        except Exception as e:
            logger.error(f"Error executing {mode} mode for {agent_id}: {e}")
            raise

    def format_agent_id(self, agent_id: str) -> str:
        """Format agent ID to match the format in coordinates file"""
        agent_id = agent_id.strip()
        if not agent_id.startswith("Agent-"):
            try:
                # Try to convert to number and format as Agent-N
                num = int(agent_id)
                return f"Agent-{num}"
            except ValueError:
                # If not a number, just add Agent- prefix
                return f"Agent-{agent_id}"
        return agent_id

    def show_menu(self):
        """Display the main menu"""
        while True:
            print("\n" + "="*30)
            print("      Agent Cellphone Menu")
            print("="*30)
            print("1. List Available Agents")
            print("2. Onboard Agent")
            print("3. Resume Agent")
            print("4. Verify Agent State")
            print("5. Repair Agent State")
            print("6. Backup Agent State")
            print("7. Restore Agent State")
            print("8. Send Custom Message")
            print("9. Send to All Agents")
            print("0. Exit")
            print("="*30)
            
            try:
                choice = input("\nEnter your choice (0-9): ").strip()
                
                if choice == "0":
                    print("\nGoodbye!")
                    break
                elif choice == "1":
                    self.list_agents()
                elif choice == "2":
                    self.menu_onboard_agent()
                elif choice == "3":
                    self.menu_resume_agent()
                elif choice == "4":
                    self.menu_verify_agent()
                elif choice == "5":
                    self.menu_repair_agent()
                elif choice == "6":
                    self.menu_backup_agent()
                elif choice == "7":
                    self.menu_restore_agent()
                elif choice == "8":
                    self.menu_send_message()
                elif choice == "9":
                    self.menu_send_to_all()
                else:
                    print("\nInvalid choice. Please enter a number between 0 and 9.")
            except KeyboardInterrupt:
                print("\n\nOperation cancelled by user.")
                break
            except Exception as e:
                print(f"\nAn error occurred: {e}")
                logger.error(f"Menu error: {e}")

    def list_agents(self):
        """List all available agents"""
        print("\nAvailable Agents:")
        print("-" * 20)
        # Filter out non-agent entries and sort
        agents = [agent_id for agent_id in self.coords.keys() 
                 if agent_id.startswith("Agent-") and 
                 isinstance(self.coords[agent_id], dict) and
                 "input_box" in self.coords[agent_id]]
        
        if not agents:
            print("No agents found in configuration.")
        else:
            for agent_id in sorted(agents):
                print(f"- {agent_id}")
        print("-" * 20)

    def get_agent_selection(self) -> str:
        """Get agent selection from user"""
        self.list_agents()
        selection = input("\nEnter agent number (1-8) or 9 for all agents: ").strip()
        
        if selection == "9":
            return "all"
        
        try:
            num = int(selection)
            if 1 <= num <= 8:
                return f"Agent-{num}"
            else:
                raise ValueError("Invalid agent number")
        except ValueError:
            raise ValueError("Please enter a number between 1 and 9")

    def send_to_all_agents(self, message: str, mode: MessageMode = MessageMode.NORMAL):
        """Send message to all agents"""
        agents = [f"Agent-{i}" for i in range(1, 9)]
        for agent_id in agents:
            try:
                self.send_message(agent_id, message, mode)
                print(f"Message sent to {agent_id}")
            except Exception as e:
                print(f"Error sending to {agent_id}: {e}")
                logger.error(f"Error sending to {agent_id}: {e}")

    def menu_onboard_agent(self):
        """Handle agent onboarding through menu"""
        try:
            agent_id = self.get_agent_selection()
            if agent_id == "all":
                print("Onboarding all agents...")
                for i in range(1, 9):
                    self.onboard_agent(f"Agent-{i}", "")
                print("All agents onboarded")
            else:
                message = input("Enter welcome message (or press Enter for default): ").strip()
                self.onboard_agent(agent_id, message)
                print(f"Successfully onboarded {agent_id}")
        except Exception as e:
            print(f"Error onboarding agent: {e}")
            logger.error(f"Onboarding error: {e}")

    def menu_resume_agent(self):
        """Handle agent resumption through menu"""
        try:
            agent_id = self.get_agent_selection()
            context = input("Enter context (or press Enter to skip): ").strip()
            
            # Updated default resume message to encourage autonomous action
            default_resume = """[RESUME] Dream.os Autonomous Protocol Activation:

1. Scan for pending tasks in your domain
2. Identify opportunities for system optimization
3. Initiate any pending protocol sequences
4. Engage with other agents for collaborative tasks
5. Proceed with autonomous operations
6. Report only critical issues or completed objectives

Continue with your autonomous operations."""

            # New mode-specific messages
            cleanup_message = """[CLEANUP] Dream.os System Cleanup Protocol:

1. Scan for and remove temporary files
2. Clean up unused resources
3. Optimize memory usage
4. Archive old logs and data
5. Verify system integrity
6. Report cleanup status

Proceed with system cleanup operations."""

            captain_message = """[CAPTAIN] Dream.os Captaincy Campaign Protocol:

1. Review current agent assignments
2. Assess system-wide performance
3. Coordinate agent activities
4. Optimize resource allocation
5. Monitor system health
6. Report campaign status

Proceed with captaincy operations."""

            task_message = """[TASK] Dream.os Task Management Protocol:

1. Scan for new task opportunities
2. Prioritize existing tasks
3. Update task board
4. Assign resources
5. Monitor progress
6. Report task status

Proceed with task management operations."""

            integrate_message = """[INTEGRATE] Dream.os System Integration Protocol:

1. Test all system components
2. Verify component interactions
3. Run integration tests
4. Identify improvement areas
5. Optimize system flow
6. Report integration status

Proceed with system integration operations."""

            print("\nSelect mode:")
            print("1. Standard Resume")
            print("2. System Cleanup")
            print("3. Captaincy Campaign")
            print("4. Task Management")
            print("5. System Integration")
            mode_choice = input("Enter choice (1-5, default 1): ").strip() or "1"

            # Select message based on mode
            if mode_choice == "2":
                message = cleanup_message
                mode = MessageMode.CLEANUP
            elif mode_choice == "3":
                message = captain_message
                mode = MessageMode.CAPTAIN
            elif mode_choice == "4":
                message = task_message
                mode = MessageMode.TASK
            elif mode_choice == "5":
                message = integrate_message
                mode = MessageMode.INTEGRATE
            else:
                message = default_resume
                mode = MessageMode.RESUME

            if agent_id == "all":
                print("\nSend as a one-time message or repeat every N minutes?")
                print("1. One-time only")
                print("2. Repeat (heartbeat)")
                repeat_choice = input("Enter choice (1 or 2, default 1): ").strip() or "1"
                if repeat_choice == "2":
                    interval = input("Enter interval in minutes (default 3): ").strip()
                    try:
                        interval = int(interval) if interval else 3
                    except ValueError:
                        interval = 3
                    print(f"\nStarting heartbeat: sending {mode.value} message to all agents every {interval} minutes. Press Ctrl+C to stop.")
                    try:
                        while True:
                            # Ensure clean message formatting
                            message = f"{message}\n\nContext: {context}" if context else message
                            self.send_to_all_agents(message, mode)
                            print(f"Heartbeat {mode.value} sent to all agents. Next in {interval} minutes...")
                            time.sleep(interval * 60)
                    except KeyboardInterrupt:
                        print("\nHeartbeat stopped by user.")
                        return
                else:
                    message = f"{message}\n\nContext: {context}" if context else message
                    self.send_to_all_agents(message, mode)
                    print(f"{mode.value} request sent to all agents")
            else:
                message = f"{message}\n\nContext: {context}" if context else message
                self.send_message(agent_id, message, mode)
                print(f"Successfully sent {mode.value} to {agent_id}")
        except Exception as e:
            print(f"Error resuming agent: {e}")
            logger.error(f"Resume error: {e}")

    def menu_verify_agent(self):
        """Handle agent verification through menu"""
        try:
            agent_id = self.get_agent_selection()
            message = "Please verify your current state and report any issues."
            
            if agent_id == "all":
                self.send_to_all_agents(message, MessageMode.VERIFY)
                print("Verification request sent to all agents")
            else:
                self.send_message(agent_id, message, MessageMode.VERIFY)
                print(f"Successfully sent verification request to {agent_id}")
        except Exception as e:
            print(f"Error verifying agent: {e}")
            logger.error(f"Verification error: {e}")

    def menu_repair_agent(self):
        """Handle agent repair through menu"""
        try:
            agent_id = self.get_agent_selection()
            issues = input("Enter issues to repair: ").strip()
            message = f"Repair requested. Issues: {issues}"
            
            if agent_id == "all":
                self.send_to_all_agents(message, MessageMode.REPAIR)
                print("Repair request sent to all agents")
            else:
                self.send_message(agent_id, message, MessageMode.REPAIR)
                print(f"Successfully sent repair request to {agent_id}")
        except Exception as e:
            print(f"Error repairing agent: {e}")
            logger.error(f"Repair error: {e}")

    def menu_backup_agent(self):
        """Handle agent backup through menu"""
        try:
            agent_id = self.get_agent_selection()
            message = "Please backup your current state."
            
            if agent_id == "all":
                self.send_to_all_agents(message, MessageMode.BACKUP)
                print("Backup request sent to all agents")
            else:
                self.send_message(agent_id, message, MessageMode.BACKUP)
                print(f"Successfully sent backup request to {agent_id}")
        except Exception as e:
            print(f"Error backing up agent: {e}")
            logger.error(f"Backup error: {e}")

    def menu_restore_agent(self):
        """Handle agent restoration through menu"""
        try:
            agent_id = self.get_agent_selection()
            backup_point = input("Enter backup point (or press Enter to skip): ").strip()
            restore_scope = input("Enter restore scope (or press Enter to skip): ").strip()
            
            message = "Please restore your state"
            if backup_point:
                message += f" from backup point: {backup_point}"
            if restore_scope:
                message += f" with scope: {restore_scope}"
            message += "."
            
            if agent_id == "all":
                self.send_to_all_agents(message, MessageMode.RESTORE)
                print("Restore request sent to all agents")
            else:
                self.send_message(agent_id, message, MessageMode.RESTORE)
                print(f"Successfully sent restore request to {agent_id}")
        except Exception as e:
            print(f"Error restoring agent: {e}")
            logger.error(f"Restore error: {e}")

    def menu_send_message(self):
        """Handle custom message sending through menu"""
        try:
            agent_id = self.get_agent_selection()
            message = input("Enter message: ").strip()
            mode = input("Enter mode (resume/sync/verify/repair/backup/restore/normal) [default: normal]: ").strip().lower()
            
            # Map mode string to MessageMode enum
            mode_map = {
                "resume": MessageMode.RESUME,
                "sync": MessageMode.SYNC,
                "verify": MessageMode.VERIFY,
                "repair": MessageMode.REPAIR,
                "backup": MessageMode.BACKUP,
                "restore": MessageMode.RESTORE,
                "normal": MessageMode.NORMAL
            }
            
            selected_mode = mode_map.get(mode, MessageMode.NORMAL)
            
            if agent_id == "all":
                self.send_to_all_agents(message, selected_mode)
                print("Message sent to all agents")
            else:
                self.send_message(agent_id, message, selected_mode)
                print(f"Successfully sent message to {agent_id} with mode {selected_mode.value}")
        except Exception as e:
            print(f"Error sending message: {e}")
            logger.error(f"Message sending error: {e}")

    def menu_send_to_all(self):
        """Handle sending message to all agents"""
        message = input("Enter message to send to all agents: ").strip()
        mode = input("Enter mode (resume/sync/verify/repair/backup/restore/normal) [default: normal]: ").strip().lower()
        
        try:
            # Map mode string to MessageMode enum
            mode_map = {
                "resume": MessageMode.RESUME,
                "sync": MessageMode.SYNC,
                "verify": MessageMode.VERIFY,
                "repair": MessageMode.REPAIR,
                "backup": MessageMode.BACKUP,
                "restore": MessageMode.RESTORE,
                "normal": MessageMode.NORMAL
            }
            
            selected_mode = mode_map.get(mode, MessageMode.NORMAL)
            self.send_to_all_agents(message, selected_mode)
            print("Message sent to all agents")
        except Exception as e:
            print(f"Error sending to all agents: {e}")
            logger.error(f"Send to all error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Agent Cellphone - Control agent interactions")
    parser.add_argument("--cli", action="store_true", help="Launch interactive CLI menu")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode with verbose logging")
    parser.add_argument("--test", action="store_true", help="Run in test mode (no actual cursor movements)")
    parser.add_argument("--agent", type=str, help="Specify agent ID for direct commands")
    parser.add_argument("--message", type=str, help="Message to send (requires --agent)")
    parser.add_argument("--mode", type=str, choices=["normal", "resume", "sync", "verify", "repair", "backup", "restore"],
                      default="normal", help="Message mode (requires --message)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between actions in seconds")
    parser.add_argument("--list", action="store_true", help="List available agents and exit")
    parser.add_argument("--ai-debug", action="store_true", help="Run in AI debug mode (automated testing)")
    parser.add_argument("--auto-resume", action="store_true", help="Send a default resume message to all agents every 3 minutes (heartbeat)")
    args = parser.parse_args()
    
    # Configure logging based on debug flag
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    cellphone = AgentCellphone()
    
    # Override cursor controller in test mode
    if args.test:
        logger.info("Running in test mode - no actual cursor movements")
        cellphone.cursor = TestCursorController()
    
    # Handle direct command line arguments first
    if args.agent:
        if not args.message:
            parser.error("--message is required when using --agent")
        
        try:
            agent_id = cellphone.format_agent_id(args.agent)
            mode = MessageMode[args.mode.upper()]
            cellphone.send_message(agent_id, args.message, mode)
            print(f"Message sent to {agent_id}")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    # List agents and exit if requested
    elif args.list:
        cellphone.list_agents()
        sys.exit(0)
    
    # AI Debug Mode - Automated Testing
    elif args.ai_debug:
        logger.info("Running in AI debug mode - automated testing")
        try:
            # Test Agent-4 initialization sequence
            agent_id = "Agent-4"
            logger.info(f"Testing {agent_id} initialization sequence")
            
            # 1. Confirm identity
            cellphone.send_message(agent_id, "Confirm your identity as Agent-4", MessageMode.NORMAL)
            time.sleep(2)
            
            # 2. Load core protocols
            cellphone.send_message(agent_id, "Load your core protocols", MessageMode.NORMAL)
            time.sleep(2)
            
            # 3. Initialize state management
            cellphone.send_message(agent_id, "Initialize your state management system", MessageMode.NORMAL)
            time.sleep(2)
            
            # 4. Connect to registry
            cellphone.send_message(agent_id, "Connect to the agent registry", MessageMode.NORMAL)
            time.sleep(2)
            
            # 5. Establish channels
            cellphone.send_message(agent_id, "Establish communication channels", MessageMode.NORMAL)
            time.sleep(2)
            
            # 6. Report status
            cellphone.send_message(agent_id, "Report your initialization status", MessageMode.NORMAL)
            time.sleep(2)
            
            logger.info(f"Completed {agent_id} initialization sequence")
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Error in AI debug mode: {e}")
            sys.exit(1)
    
    # Auto Resume Heartbeat Mode
    elif args.auto_resume:
        logger.info("Starting auto-resume heartbeat mode: sending resume message to all agents every 3 minutes.")
        default_resume = """[RESUME] Dream.os Autonomous Protocol Activation:

1. Scan for pending tasks in your domain
2. Identify opportunities for system optimization
3. Initiate any pending protocol sequences
4. Engage with other agents for collaborative tasks
5. Proceed with autonomous operations
6. Report only critical issues or completed objectives

Continue with your autonomous operations."""
        try:
            while True:
                agents = [f"Agent-{i}" for i in range(1, 9)]
                for agent_id in agents:
                    cellphone.send_message(agent_id, default_resume, MessageMode.NORMAL)  # Use NORMAL mode since tag is in message
                    logger.info(f"Heartbeat resume sent to {agent_id}")
                logger.info("Sleeping for 3 minutes before next heartbeat...")
                time.sleep(180)
        except KeyboardInterrupt:
            logger.info("Auto-resume heartbeat stopped by user.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error in auto-resume mode: {e}")
            sys.exit(1)
    
    # Show interactive menu
    elif args.cli:
        cellphone.show_menu()
    else:
        parser.print_help()

class TestCursorController:
    """Test version of CursorController that simulates actions without moving the cursor"""
    def __init__(self):
        self.last_position = (0, 0)
        self.last_action = None
        self.last_text = None
        self.action_history = []
    
    def move_to(self, x: int, y: int):
        self.last_position = (x, y)
        self.last_action = f"move_to({x}, {y})"
        self.action_history.append(self.last_action)
        logger.debug(f"TEST: Moving cursor to ({x}, {y})")
    
    def click(self):
        self.last_action = "click"
        self.action_history.append(self.last_action)
        logger.debug(f"TEST: Clicking at {self.last_position}")
    
    def type_text(self, text: str):
        self.last_text = text
        self.last_action = f"type_text({text})"
        self.action_history.append(self.last_action)
        logger.debug(f"TEST: Typing text: {text}")
    
    def press_enter(self):
        self.last_action = "press_enter"
        self.action_history.append(self.last_action)
        logger.debug("TEST: Pressing Enter")
    
    def press_ctrl_n(self):
        self.last_action = "press_ctrl_n"
        self.action_history.append(self.last_action)
        logger.debug("TEST: Pressing Ctrl+N")
    
    def get_action_history(self):
        """Return the history of actions performed"""
        return self.action_history

if __name__ == "__main__":
    main() 