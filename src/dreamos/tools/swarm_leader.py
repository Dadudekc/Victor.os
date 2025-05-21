import time
import logging
import threading
import json
import re
import shutil
from pathlib import Path
from datetime import datetime, timezone
from agent_cellphone import AgentCellphone, MessageMode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('swarm_leader')

class SwarmLeader:
    def __init__(self):
        self.cellphone = AgentCellphone()
        self.running = False
        self.resume_interval = 600  # 10 minutes
        self.leader_id = "Agent-8"  # Our ID as the swarm leader
        self.protocol_dir = Path("docs/agents/protocols")
        self.coordination_file = Path("runtime/agent_comms/coordination/swarm_status.json")
        self.coordination_file.parent.mkdir(parents=True, exist_ok=True)
        self.agent_status = {}
        self.load_coordination_state()
        
    def load_coordination_state(self):
        """Load the current coordination state from file."""
        try:
            if self.coordination_file.exists():
                with open(self.coordination_file, 'r') as f:
                    self.agent_status = json.load(f)
            else:
                self.agent_status = {
                    "last_update": datetime.now(timezone.utc).isoformat(),
                    "agents": {},
                    "protocol_versions": {},
                    "active_tasks": {},
                    "system_health": {}
                }
                self.save_coordination_state()
        except Exception as e:
            logger.error(f"Error loading coordination state: {e}")
            
    def save_coordination_state(self):
        """Save the current coordination state to file."""
        try:
            self.agent_status["last_update"] = datetime.now(timezone.utc).isoformat()
            with open(self.coordination_file, 'w') as f:
                json.dump(self.agent_status, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving coordination state: {e}")
            
    def start_leadership_loop(self):
        """Start the leadership loop in a background thread."""
        self.running = True
        self.leadership_thread = threading.Thread(target=self._leadership_loop)
        self.leadership_thread.daemon = True
        self.leadership_thread.start()
        logger.info("Started swarm leadership loop")
        
    def stop_leadership_loop(self):
        """Stop the leadership loop."""
        self.running = False
        if hasattr(self, 'leadership_thread'):
            self.leadership_thread.join()
        logger.info("Stopped swarm leadership loop")
        
    def _leadership_loop(self):
        """Main leadership loop that coordinates swarm activities."""
        while self.running:
            try:
                # Update protocol versions
                self._update_protocol_versions()
                
                # Check agent statuses
                self._check_agent_statuses()
                
                # Send leadership message
                self._send_leadership_message()
                
                # Process feedback
                self._process_agent_feedback()
                
                # Update coordination state
                self.save_coordination_state()
                
                # Wait for next interval
                time.sleep(self.resume_interval)
                
            except Exception as e:
                logger.error(f"Error in leadership loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
                
    def _update_protocol_versions(self):
        """Update protocol versions from documentation."""
        try:
            for protocol_file in self.protocol_dir.glob("*.md"):
                with open(protocol_file, 'r') as f:
                    content = f.read()
                    # Extract version from header
                    version_match = re.search(r"Version:\s*(\d+\.\d+\.\d+)", content)
                    if version_match:
                        self.agent_status["protocol_versions"][protocol_file.stem] = version_match.group(1)
        except Exception as e:
            logger.error(f"Error updating protocol versions: {e}")
            
    def _check_agent_statuses(self):
        """Check and update status of all agents."""
        try:
            for agent_id in self.agent_status["agents"]:
                # Send status check message
                status_message = {
                    "type": "status_check",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "protocol_versions": self.agent_status["protocol_versions"]
                }
                
                ok = self.cellphone.message_agent(
                    agent_id,
                    json.dumps(status_message),
                    MessageMode.STATUS
                )
                
                if not ok:
                    logger.warning(f"Failed to check status for {agent_id}")
                    
        except Exception as e:
            logger.error(f"Error checking agent statuses: {e}")
            
    def _send_leadership_message(self):
        """Send leadership message to maintain swarm coordination."""
        try:
            leadership_message = {
                "type": "leadership",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "protocol_versions": self.agent_status["protocol_versions"],
                "active_tasks": self.agent_status["active_tasks"],
                "system_health": self.agent_status["system_health"]
            }
            
            ok = self.cellphone.message_agent(
                self.leader_id,
                json.dumps(leadership_message),
                MessageMode.WAKE
            )
            
            if ok:
                logger.info("Successfully sent leadership message")
            else:
                logger.warning("Failed to send leadership message")
                
        except Exception as e:
            logger.error(f"Error sending leadership message: {e}")
            
    def _process_agent_feedback(self):
        """Process feedback from agents."""
        try:
            feedback_dir = Path("runtime/agent_comms/feedback")
            if feedback_dir.exists():
                for feedback_file in feedback_dir.glob("*.json"):
                    with open(feedback_file, 'r') as f:
                        feedback = json.load(f)
                        
                    # Process feedback based on type
                    if feedback["type"] == "status_update":
                        self._handle_status_update(feedback)
                    elif feedback["type"] == "task_update":
                        self._handle_task_update(feedback)
                    elif feedback["type"] == "protocol_feedback":
                        self._handle_protocol_feedback(feedback)
                        
                    # Archive processed feedback
                    archive_dir = feedback_dir / "archive"
                    archive_dir.mkdir(exist_ok=True)
                    shutil.move(feedback_file, archive_dir / feedback_file.name)
                    
        except Exception as e:
            logger.error(f"Error processing agent feedback: {e}")
            
    def _handle_status_update(self, feedback: dict):
        """Handle agent status update feedback."""
        try:
            agent_id = feedback["agent_id"]
            self.agent_status["agents"][agent_id] = {
                "last_update": feedback["timestamp"],
                "status": feedback["status"],
                "protocol_compliance": feedback.get("protocol_compliance", {}),
                "health": feedback.get("health", {})
            }
        except Exception as e:
            logger.error(f"Error handling status update: {e}")
            
    def _handle_task_update(self, feedback: dict):
        """Handle task update feedback."""
        try:
            task_id = feedback["task_id"]
            self.agent_status["active_tasks"][task_id] = {
                "last_update": feedback["timestamp"],
                "status": feedback["status"],
                "agent_id": feedback["agent_id"],
                "progress": feedback.get("progress", 0),
                "details": feedback.get("details", {})
            }
        except Exception as e:
            logger.error(f"Error handling task update: {e}")
            
    def _handle_protocol_feedback(self, feedback: dict):
        """Handle protocol feedback."""
        try:
            protocol = feedback["protocol"]
            if protocol not in self.agent_status["protocol_versions"]:
                self.agent_status["protocol_versions"][protocol] = feedback["version"]
                
            # Update protocol compliance metrics
            if "compliance_metrics" in feedback:
                self.agent_status["agents"][feedback["agent_id"]]["protocol_compliance"][protocol] = feedback["compliance_metrics"]
        except Exception as e:
            logger.error(f"Error handling protocol feedback: {e}")

def main():
    leader = SwarmLeader()
    
    # Start leadership loop
    leader.start_leadership_loop()
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal (Ctrl+C)")
        logger.info("Initiating graceful shutdown...")
        
        # Stop the leadership loop
        leader.stop_leadership_loop()
        
        # Wait for any pending operations to complete
        logger.info("Waiting for pending operations to complete...")
        time.sleep(2)
        
        logger.info("Shutdown complete. You can now check the logs.")
        logger.info("Log file location: runtime/logs/swarm_leader.log")
        logger.info("To restart, run: python swarm_leader.py")

if __name__ == "__main__":
    # Configure logging to file
    log_dir = Path("runtime/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(
        log_dir / "swarm_leader.log",
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(file_handler)
    
    # Set up signal handlers for graceful shutdown
    import signal
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        raise KeyboardInterrupt()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    main() 
    