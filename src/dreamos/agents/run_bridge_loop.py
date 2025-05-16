"""
Bridge Loop Runner

This module connects THEA to agent inboxes and the feedback pipeline.
It handles message injection, response processing, and feedback cycles.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

from dreamos.agents.utils.response_retriever import ResponseRetriever
from dreamos.agents.utils.autonomy_engine import AutonomyEngine
from dreamos.agents.task_schema import TaskSchema
from dreamos.agents.message_schema import MessageSchema

class BridgeLoop:
    """Bridge loop connecting THEA to agent inboxes and feedback pipeline."""
    
    def __init__(self, workspace_root: str, agent_bus: Any, pbm: Any):
        """Initialize bridge loop with workspace and dependencies."""
        self.workspace_root = Path(workspace_root)
        self.agent_bus = agent_bus
        self.pbm = pbm
        self.config = self.load_config()
        self.response_retriever = ResponseRetriever(workspace_root)
        self.autonomy_engine = AutonomyEngine(workspace_root)
        self.task_schema = TaskSchema()
        self.message_schema = MessageSchema()
        self.logger = self._setup_logger()
        self.active_agents = self.config.get('active_agents', [])
        self.check_interval = self.config.get('loop', {}).get('check_interval', 1)
        self.error_backoff = self.config.get('loop', {}).get('error_backoff', 5)
        self.max_retries = self.config.get('loop', {}).get('max_retries', 3)
        self.message_types = self.config.get('messages', {}).get('types', [])
        self.thea_enabled = self.config.get('thea', {}).get('enabled', True)
        self.critical_errors = self.config.get('error_handling', {}).get('critical_errors', [])
        
    def _setup_logger(self) -> logging.Logger:
        """Set up logging with config settings."""
        log_config = self.config.get('logging', {})
        logger = logging.getLogger('bridge_loop')
        logger.setLevel(log_config.get('level', 'INFO'))
        
        # Create handlers
        file_handler = logging.FileHandler(log_config.get('file', 'runtime/logs/bridge_loop.log'))
        console_handler = logging.StreamHandler()
        
        # Create formatters and add it to handlers
        log_format = logging.Formatter(log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        file_handler.setFormatter(log_format)
        console_handler.setFormatter(log_format)
        
        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger

    def load_config(self) -> Dict:
        """Load configuration from YAML file."""
        config_path = self.workspace_root / "src/dreamos/config/bridge_loop_config.yaml"
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return {}

    def inject_to_agent(self, agent_id: str, message: Dict) -> bool:
        """Inject message into agent's inbox with metadata."""
        try:
            # Add metadata
            message['metadata'] = {
                'timestamp': time.time(),
                'source': 'THEA',
                'type': message.get('type', 'unknown')
            }
            
            # Validate message
            if not self.message_schema.validate_message(message):
                self.logger.error(f"Invalid message format for agent {agent_id}")
                return False
                
            # Write to agent's inbox as a list
            inbox_path = self.response_retriever.get_inbox_path(agent_id)
            if not inbox_path:
                self.logger.error(f"No inbox found for agent {agent_id}")
                return False
            
            # Read existing messages (if any)
            messages = []
            if inbox_path.exists():
                try:
                    with open(inbox_path, 'r') as f:
                        existing = json.load(f)
                        if isinstance(existing, list):
                            messages = existing
                        elif isinstance(existing, dict):
                            messages = [existing]
                except Exception as e:
                    self.logger.warning(f"Could not read existing inbox for agent {agent_id}: {e}")
            messages.append(message)
            with open(inbox_path, 'w') as f:
                json.dump(messages, f, indent=2)
            self.logger.info(f"Injected message to agent {agent_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to inject message to agent {agent_id}: {e}")
            return False

    def process_agent_response(self, agent_id: str, response: Dict) -> bool:
        """Process agent response and handle feedback."""
        try:
            # Validate response
            if not self.message_schema.validate_message(response):
                self.logger.error(f"Invalid response format from agent {agent_id}")
                return False
                
            # Handle based on response type
            response_type = response.get('type')
            
            if response_type == 'task_completion':
                # Update task status
                task_id = response.get('task_id')
                if task_id:
                    self.task_schema.update_task_status(
                        task_id,
                        'completed',
                        response.get('completion_notes', '')
                    )
                    
            elif response_type == 'error':
                # Log error and check if critical
                error_type = response.get('error_type')
                if error_type in self.critical_errors:
                    self.logger.critical(f"Critical error from agent {agent_id}: {error_type}")
                    # Trigger recovery if configured
                    if self.thea_enabled:
                        self._trigger_recovery(agent_id, error_type)
                else:
                    self.logger.error(f"Error from agent {agent_id}: {error_type}")
                    
            elif response_type == 'status_update':
                # Log status update
                self.logger.info(f"Status update from agent {agent_id}: {response.get('status')}")
                
            elif response_type == 'autonomy_decision':
                # Log autonomy decision
                self.autonomy_engine.log_autonomy_decision(
                    agent_id,
                    response.get('decision'),
                    response.get('reasoning')
                )
                
            # Clear processed message
            self.response_retriever.clear_inbox(agent_id)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process response from agent {agent_id}: {e}")
            return False

    def _trigger_recovery(self, agent_id: str, error_type: str) -> None:
        """Trigger recovery process for critical errors."""
        try:
            recovery_message = {
                'type': 'recovery_trigger',
                'agent_id': agent_id,
                'error_type': error_type,
                'timestamp': time.time()
            }
            
            # Send to THEA if enabled
            if self.thea_enabled:
                self.agent_bus.send_message('THEA', recovery_message)
                
            # Log recovery trigger
            self.logger.info(f"Triggered recovery for agent {agent_id} due to {error_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to trigger recovery for agent {agent_id}: {e}")

    def run_test_cycle(self) -> None:
        """Run a test cycle to validate the bridge loop."""
        self.logger.info("Starting bridge loop test cycle")
        
        # Test message for each active agent
        test_message = {
            'type': 'task_assignment',
            'task_id': 'TEST-001',
            'description': 'Bridge loop test task',
            'priority': 'high',
            'metadata': {
                'test_cycle': True,
                'timestamp': time.time()
            }
        }
        
        for agent_id in self.active_agents:
            # Inject test message
            if self.inject_to_agent(agent_id, test_message):
                self.logger.info(f"Injected test message to agent {agent_id}")
                
                # Wait for response
                time.sleep(self.check_interval)
                
                # Check for response
                response = self.response_retriever.get_unread_messages(agent_id)
                if response:
                    self.logger.info(f"Received test response from agent {agent_id}")
                    self.process_agent_response(agent_id, response[0])
                else:
                    self.logger.warning(f"No test response from agent {agent_id}")
                    
        self.logger.info("Completed bridge loop test cycle")

    def run(self) -> None:
        """Run the bridge loop continuously."""
        self.logger.info("Starting bridge loop")
        
        while True:
            try:
                # Check for messages from THEA
                if self.thea_enabled and self.agent_bus is not None:
                    thea_messages = self.agent_bus.get_messages('THEA')
                    for message in thea_messages:
                        target_agent = message.get('target_agent')
                        if target_agent in self.active_agents:
                            self.inject_to_agent(target_agent, message)
                elif self.thea_enabled:
                    self.logger.warning("THEA integration enabled but agent_bus is None")
                            
                # Check agent responses
                for agent_id in self.active_agents:
                    responses = self.response_retriever.get_unread_messages(agent_id)
                    for response in responses:
                        self.process_agent_response(agent_id, response)
                        
                # Sleep between checks
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Bridge loop error: {e}")
                time.sleep(self.error_backoff)

def main():
    """Main entry point for bridge loop."""
    workspace_root = "D:/Dream.os"
    agent_bus = None  # Initialize with actual agent bus
    pbm = None  # Initialize with actual PBM
    
    bridge_loop = BridgeLoop(workspace_root, agent_bus, pbm)
    
    # Run test cycle first
    bridge_loop.run_test_cycle()
    
    # Start main loop
    bridge_loop.run()

if __name__ == "__main__":
    main() 