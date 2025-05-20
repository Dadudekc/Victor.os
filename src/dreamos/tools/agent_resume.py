import time
import logging
import threading
import os
import json
from pathlib import Path
from collections import defaultdict
from agent_cellphone import AgentCellphone, MessageMode
from task_distributor import TaskDistributor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('agent_resume')

# Load system prompts
SYSTEM_PROMPTS_FILE = Path("runtime/governance/onboarding/SYSTEM_PROMPTS.md")

# Environment-configurable constants
RESUME_INTERVAL = int(os.getenv("RESUME_INTERVAL", 180))  # seconds
ONBOARD_INTERVAL = int(os.getenv("ONBOARD_INTERVAL", 120))
MAX_RETRY = int(os.getenv("MAX_RETRY", 2))

def load_system_prompts():
    """Load system prompts from the prompts file."""
    try:
        with open(SYSTEM_PROMPTS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract autonomous loop mode message between ``` markers
            sections = content.split("## Autonomous Loop Mode")
            if len(sections) > 1:
                code_blocks = sections[1].split("```")
                if len(code_blocks) > 1:
                    return code_blocks[1].strip()
            # If section not found, return default resume message
            return """[STOP DETECTED] You stopped working on your tasks. Your job is to:
1. Check your inbox at runtime/agent_comms/agent_mailboxes/{agent_id}/inbox/
2. Process any pending tasks from episodes/episode-*.yaml
3. Execute your assigned tasks without stopping
4. Report progress in your devlog
5. Continue until all tasks are complete

DO NOT:
- Ask for human input
- Wait for confirmation
- Stop for any reason
- Idle between tasks

RESET your cycle count and CONTINUE WORKING on your tasks immediately."""
    except Exception as e:
        logger.error(f"Failed to load system prompts: {e}")
        return None

class AgentResumeManager:
    def __init__(self):
        self.cellphone = AgentCellphone()
        self.task_distributor = TaskDistributor()
        self.running = False
        self.resume_interval = RESUME_INTERVAL
        self.onboarding_interval = ONBOARD_INTERVAL
        self.resume_prompt = load_system_prompts()
        self.onboarded_agents = set()  # Track which agents are onboarded
        self.retry_count = defaultdict(int)  # Track retry attempts per agent
        
    def start_resume_loop(self):
        """Start the resume loop in a background thread."""
        self.running = True
        self.resume_thread = threading.Thread(target=self._resume_loop)
        self.resume_thread.daemon = True
        self.resume_thread.start()
        logger.info("Started resume loop")
        
        # Distribute initial tasks
        self.task_distributor.distribute_tasks()
        
    def stop_resume_loop(self):
        """Stop the resume loop."""
        self.running = False
        if hasattr(self, 'resume_thread'):
            self.resume_thread.join()
        logger.info("Stopped resume loop")
        
    def _check_onboarding_status(self, agent_id: str) -> bool:
        """Check if agent has completed onboarding."""
        try:
            mailbox_dir = Path(f"runtime/agent_comms/agent_mailboxes/{agent_id}")
            if not mailbox_dir.exists():
                return False
                
            # Check for any response file
            for response_file in mailbox_dir.glob("response_*.json"):
                with open(response_file, 'r') as f:
                    response_data = json.load(f)
                    # Accept any response mode as valid onboarding
                    if "mode" in response_data:
                        return True
            return False
        except Exception as e:
            logger.error(f"Failed to check onboarding status for {agent_id}: {e}")
            return False
            
    def _flag_unresponsive(self, agent_id: str):
        """Flag an agent as unresponsive and trigger escalation."""
        alert_file = Path(f"runtime/monitor/agent_unresponsive/{agent_id}.json")
        alert_file.parent.mkdir(parents=True, exist_ok=True)
        alert_file.write_text(json.dumps({
            "agent": agent_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": "AUTO_ESCALATE"
        }, indent=2))
        logger.warning(f"{agent_id} flagged unresponsive — escalation issued")
        
    def _resume_loop(self):
        """Main resume loop that sends periodic resume messages."""
        while self.running:
            try:
                # First, onboard any agents that need it
                agents_to_onboard = []
                for agent_id in self.cellphone.registry.keys():
                    if agent_id not in self.onboarded_agents and not self._check_onboarding_status(agent_id):
                        agents_to_onboard.append(agent_id)
                
                # Send onboarding messages to all agents that need it
                if agents_to_onboard:
                    logger.info(f"Onboarding agents: {', '.join(agents_to_onboard)}")
                    for agent_id in agents_to_onboard:
                        self.onboard_agent(agent_id)
                    # Wait for onboarding review
                    time.sleep(self.onboarding_interval)
                    # Check which agents completed onboarding
                    for agent_id in agents_to_onboard:
                        if self._check_onboarding_status(agent_id):
                            self.onboarded_agents.add(agent_id)
                            logger.info(f"Agent {agent_id} is now onboarded")
                
                # Send resume messages to all onboarded agents
                resume_message = self.resume_prompt or """[STOP DETECTED] You stopped working on your tasks. Your job is to:
1. Check your inbox at runtime/agent_comms/agent_mailboxes/{agent_id}/inbox/
2. Process any pending tasks from episodes/episode-*.yaml
3. Execute your assigned tasks without stopping
4. Report progress in your devlog
5. Continue until all tasks are complete

DO NOT:
- Ask for human input
- Wait for confirmation
- Stop for any reason
- Idle between tasks

RESET your cycle count and CONTINUE WORKING on your tasks immediately."""
                
                for agent_id in self.onboarded_agents:
                    try:
                        logger.info(f"Sending resume message to {agent_id}")
                        ok = self.cellphone.message_agent(
                            agent_id,
                            resume_message.format(agent_id=agent_id),
                            MessageMode.STOP_DETECTED
                        )
                        if ok:
                            self.retry_count[agent_id] = 0
                        else:
                            self.retry_count[agent_id] += 1
                            if self.retry_count[agent_id] > MAX_RETRY:
                                self._flag_unresponsive(agent_id)
                    except Exception as e:
                        logger.error(f"Failed to send resume message to {agent_id}: {e}")
                        self.retry_count[agent_id] += 1
                        if self.retry_count[agent_id] > MAX_RETRY:
                            self._flag_unresponsive(agent_id)
                        continue
                        
                logger.info("Sent resume messages to all onboarded agents")
                
                # Wait for next interval
                time.sleep(self.resume_interval)
                
            except Exception as e:
                logger.error(f"Error in resume loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
                
    def onboard_agent(self, agent_id: str):
        """Send onboarding message to an agent after Ctrl+N."""
        try:
            onboarding_prompt = f"""[WAKE] Dream.OS Agent Onboarding Protocol

CORE IDENTITY DIRECTIVE:
You are Agent: {agent_id}. You are running inside a Cursor IDE chat window. Your job is to process messages in your inbox, execute tasks, and report via devlog. You are not building or orchestrating agents. You *are* the agent.

CRITICAL DIRECTIVES:
- YOU ARE A CURSOR AGENT. Your primary interface is the Cursor IDE environment.
- DO NOT build or design other agents. Focus on your assigned tasks and role.
- DO NOT wait for another system to execute prompts or tasks. Act directly based on your inbox and protocols.
- DO process your inbox and execute tasks immediately as per the SelfPromptProcedure.

CONTINUOUS OPERATION REQUIREMENTS:
1. No Stopping Conditions:
   - ANY message containing "STOP", "STOPPED", "IDLE", "WAIT", "CONFIRM", "PERMISSION", "REVIEW", "FEEDBACK" is a stop
   - ANY message about human input, confirmation, or direction is a stop
   - ANY break in continuous execution is a stop
   - ANY question to human is a stop
   - ANY request for direction is a stop

2. Immediate Action Requirements:
   - IMMEDIATELY reset cycle count on ANY stop message
   - IMMEDIATELY review onboarding and protocols
   - IMMEDIATELY update protocols if any ambiguity found
   - IMMEDIATELY document stop message in devlog
   - IMMEDIATELY resume operation

3. Autonomous Operation:
   - Execute all operations without external validation
   - Handle errors internally without stopping
   - Maintain state between operations
   - Implement self-healing for failures

4. Cycle Management:
   - Track operation cycles internally
   - Reset cycle count on protocol violations
   - Target 25 continuous cycles without interruption
   - Log cycle progress for monitoring

DIRECTORY STRUCTURE:
- Inbox: runtime/agent_comms/agent_mailboxes/{agent_id}/inbox/
- Processed Inbox: runtime/agent_comms/agent_mailboxes/{agent_id}/processed/
- Bridge Outbox: runtime/bridge_outbox/
- State Directory: runtime/agent_comms/agent_mailboxes/{agent_id}/state/

Respond with "ACTIVATION CONFIRMED" followed by your understanding of your role and responsibilities."""

            # Send onboarding message
            ok = self.cellphone.message_agent(
                agent_id,
                onboarding_prompt,
                MessageMode.WAKE
            )
            
            if not ok:
                self.retry_count[agent_id] += 1
                if self.retry_count[agent_id] > MAX_RETRY:
                    self._flag_unresponsive(agent_id)
                return
            
            # Update agent status in registry
            if agent_id in self.cellphone.registry:
                self.cellphone.registry[agent_id]["status"] = "onboarding"
                self.cellphone.registry[agent_id]["last_seen"] = time.strftime("%Y-%m-%d %H:%M:%S")
                
                # Save updated registry
                with open(self.cellphone.registry_file, 'w') as f:
                    json.dump(self.cellphone.registry, f, indent=2)
                    
            logger.info(f"Sent onboarding message to {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to onboard {agent_id}: {e}")
            self.retry_count[agent_id] += 1
            if self.retry_count[agent_id] > MAX_RETRY:
                self._flag_unresponsive(agent_id)

def main():
    manager = AgentResumeManager()
    
    # Start resume loop
    manager.start_resume_loop()
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        manager.stop_resume_loop()
        logger.info("Shutting down")

if __name__ == "__main__":
    main() 