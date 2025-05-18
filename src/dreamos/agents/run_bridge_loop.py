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
import asyncio
from dreamos.core.coordination.agent_bus import AgentBus

from dreamos.agents.utils.response_retriever import ResponseRetriever
from dreamos.agents.utils.autonomy_engine import AutonomyEngine
from dreamos.agents.task_schema import TaskSchema
from dreamos.agents.message_schema import MessageSchema

class BridgeLoop:
    """Bridge loop connecting THEA to agent inboxes and feedback pipeline."""
    
    def __init__(self, workspace_root: str, agent_bus: AgentBus, pbm: Any):
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
            # Ensure logger is available or print if not
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(f"Failed to load config: {e}")
            else:
                print(f"ERROR: Failed to load config: {e}") # Fallback if logger not init
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

    async def process_agent_response(self, agent_id: str, response: Dict) -> bool:
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
                        # asyncio.create_task to call async from sync if necessary,
                        # but _trigger_recovery will be async.
                        # This part needs careful handling if process_agent_response remains sync.
                        # For now, assuming it's called from an async context or BridgeLoop.run manages this.
                        # If process_agent_response is called from the main async loop, it's fine.
                        await self._trigger_recovery(agent_id, error_type)
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

    async def _trigger_recovery(self, agent_id: str, error_type: str) -> None:
        """Trigger recovery process for critical errors."""
        try:
            recovery_message = {
                'type': 'recovery_trigger',
                'agent_id': agent_id,
                'error_type': error_type,
                'timestamp': time.time()
            }
            
            # Send to THEA if enabled
            if self.thea_enabled and self.agent_bus:
                await self.agent_bus.publish(
                    event_type="recovery_trigger", 
                    data={
                        'source_id': f'BridgeLoop_Agent_{agent_id}',
                        'payload': recovery_message 
                    }
                )
                
            # Log recovery trigger
            self.logger.info(f"Triggered recovery for agent {agent_id} due to {error_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to trigger recovery for agent {agent_id}: {e}")

    async def run_test_cycle(self) -> None:
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
                    await self.process_agent_response(agent_id, response[0])
                else:
                    self.logger.warning(f"No test response from agent {agent_id}")
                    
        self.logger.info("Completed bridge loop test cycle")

    async def _handle_thea_message(self, event_type: str, data: Dict[str, Any]):
        """Callback to handle messages received from THEA via AgentBus."""
        self.logger.info(f"Received event '{event_type}' from THEA (source: {data.get('source_id', 'Unknown')})")
        
        # Assuming 'data' contains the actual message payload from THEA,
        # and this payload includes 'target_agent' and the message content itself.
        # Example: data = {'source_id': 'THEA_System', 'payload': {'target_agent': 'Agent-1', 'type': 'task_assignment', ...}}
        
        message_payload = data.get('payload')
        if not isinstance(message_payload, dict):
            self.logger.error(f"Invalid message payload structure from THEA for event '{event_type}': {message_payload}")
            return

        target_agent_id = message_payload.get('target_agent')
        
        if not target_agent_id:
            self.logger.error(f"No 'target_agent' specified in payload from THEA for event '{event_type}': {message_payload}")
            return

        if target_agent_id in self.active_agents:
            self.logger.info(f"Injecting message type '{message_payload.get('type', 'unknown')}' to agent {target_agent_id} from THEA event '{event_type}'")
            # Ensure the message payload is what inject_to_agent expects
            # inject_to_agent adds its own metadata if source is 'THEA', but this comes via AgentBus
            # We might need to adjust what 'message' is passed to inject_to_agent
            
            # Reconstruct message for injection, ensuring it matches what inject_to_agent expects
            # inject_to_agent expects the core message content.
            # The 'type' in the payload is the message type for the agent.
            agent_message_content = {k: v for k, v in message_payload.items() if k != 'target_agent'}
            
            # Add source information if not already present or to override
            agent_message_content['metadata'] = agent_message_content.get('metadata', {})
            agent_message_content['metadata']['source'] = f"THEA_via_AgentBus_Event_{event_type}"
            agent_message_content['metadata']['original_event_source_id'] = data.get('source_id')

            self.inject_to_agent(target_agent_id, agent_message_content)
        else:
            self.logger.warning(f"Target agent {target_agent_id} from THEA event '{event_type}' not in active_agents list. Ignoring.")

    async def start(self):
        """Start the AgentBus and subscribe to THEA messages."""
        if self.agent_bus:
            await self.agent_bus.start()
            self.logger.info("AgentBus started by BridgeLoop.")

            if self.thea_enabled:
                thea_config_types = self.config.get('thea', {}).get('message_types', [])
                # Bridge subscribes to messages FROM THEA. It publishes 'recovery_trigger'.
                event_types_from_thea = [et for et in thea_config_types if et != 'recovery_trigger']
                
                if not event_types_from_thea:
                    self.logger.warning("THEA is enabled, but no message types configured for BridgeLoop to subscribe to (excluding 'recovery_trigger').")
                else:
                    for event_type in event_types_from_thea:
                        await self.agent_bus.subscribe(event_type, self._handle_thea_message)
                        self.logger.info(f"BridgeLoop subscribed to THEA event type: '{event_type}'")
            else:
                self.logger.info("THEA integration is disabled. BridgeLoop will not subscribe to THEA events.")
        else:
            self.logger.error("AgentBus not provided to BridgeLoop. Cannot start or subscribe to THEA events.")

    async def run(self) -> None:
        """Run the bridge loop continuously."""
        self.logger.info("Starting bridge loop (async run)")
        
        # THEA message polling is removed, handled by AgentBus subscription & _handle_thea_message callback
        
        while True:
            try:
                # Check agent responses
                for agent_id in self.active_agents:
                    # Assuming get_unread_messages is synchronous I/O.
                    # If it were async, it would need 'await'.
                    responses = self.response_retriever.get_unread_messages(agent_id)
                    for response in responses:
                        await self.process_agent_response(agent_id, response)
                        
                # Sleep between checks
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Bridge loop error: {e}")
                await asyncio.sleep(self.error_backoff)

async def amain():
    """Async main function to run the BridgeLoop."""
    # Determine workspace_root - assuming script is run from a context where this is clear
    # For now, let's assume the workspace root is the parent of 'src'
    workspace_root = Path(__file__).resolve().parents[2] # DANGER: This assumes a fixed structure. Better to pass as arg.
    
    # Initialize AgentBus
    agent_bus = AgentBus()
    
    # Initialize Policy & Belief Manager (PBM) - placeholder
    pbm = None # Replace with actual PBM initialization if available/needed
    
    bridge_loop = BridgeLoop(str(workspace_root), agent_bus, pbm)
    
    # Start AgentBus and subscriptions
    await bridge_loop.start()
    
    # Run the main loop
    try:
        await bridge_loop.run()
    except KeyboardInterrupt:
        bridge_loop.logger.info("BridgeLoop received KeyboardInterrupt. Shutting down.")
    finally:
        if agent_bus:
            bridge_loop.logger.info("Stopping AgentBus...")
            await agent_bus.stop()
            bridge_loop.logger.info("AgentBus stopped.")
        bridge_loop.logger.info("BridgeLoop shut down complete.")

def main():
    """Synchronous entry point, runs the async main function."""
    # Setup basic logging in case config load fails before BridgeLoop logger is up
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__) # For main function itself
    
    # Determine workspace_root more robustly or accept as CLI arg
    # Defaulting for now, but this should be improved.
    # Example: If run from workspace root as `python src/dreamos/agents/run_bridge_loop.py`
    # then Path.cwd() could be workspace_root.
    # If script is in /d:/Dream.os/src/dreamos/agents/run_bridge_loop.py
    # Workspace root /d:/Dream.os
    # script is /d:/Dream.os/src/dreamos/agents/run_bridge_loop.py
    # So, Path(__file__).resolve().parents[3] should be /d:/Dream.os/
    
    # Simple workspace root detection (can be replaced by arg parsing)
    script_path = Path(__file__).resolve() # /d%3A/Dream.os/src/dreamos/agents/run_bridge_loop.py
    workspace_root = script_path.parents[3] # Should be /d%3A/Dream.os if structure is /d%3A/Dream.os/src/dreamos/agents/
    
    # Confirm if this is the correct path structure. 
    # If the script is in `src/dreamos/agents/run_bridge_loop.py`
    # parents[0] is run_bridge_loop.py
    # parents[1] is agents
    # parents[2] is dreamos
    # parents[3] is src
    # parents[4] is Dream.os (workspace root) - this depends on where the script is located relative to root.
    # Let's assume the script is directly in the workspace for now or use a fixed relative path from script.
    # The previous main had # workspace_root = Path(args.workspace).resolve()
    # For now, using a relative path from script, assuming script is at src/dreamos/agents/run_bridge_loop.py
    # and workspace is two levels up from 'src'.
    # This is what the user_info implies as workspace root
    # /d%3A/Dream.os
    # script is /d%3A/Dream.os/src/dreamos/agents/run_bridge_loop.py
    # So, Path(__file__).resolve().parents[3] should be /d%3A/Dream.os/
    
    # Trying to make workspace_root discovery more robust.
    # If the script is at <workspace>/src/dreamos/agents/run_bridge_loop.py
    # Then workspace is Path(__file__).resolve().parents[3]
    current_file_path = Path(__file__).resolve() # e.g. /d:/Dream.os/src/dreamos/agents/run_bridge_loop.py
    
    # Attempt to find 'src' directory going upwards. Workspace is its parent.
    # This is still fragile. Best would be an env var or CLI arg.
    # For now, assuming script is in src/dreamos/agents/
    # workspace_root = current_file_path.parent.parent.parent 
    # This would make workspace_root = src
    
    # Let's stick to previous main's logic structure if it existed, or pass it.
    # The provided context didn't show the original main.
    # A common pattern: workspace_root = Path.cwd() if script is run from workspace root.
    # Or using an environment variable.
    
    # FALLBACK: Use a hardcoded relative path for dev, assuming script is in src/dreamos/agents
    # and workspace root is two levels above `src`
    # This is what the user_info implies as workspace root
    # /d%3A/Dream.os
    # script is /d%3A/Dream.os/src/dreamos/agents/run_bridge_loop.py
    # So, Path(__file__).resolve().parents[3] should be /d%3A/Dream.os/
    
    try:
        # This calculation of workspace_root is based on the user_info path.
        # /d%3A/Dream.os/src/dreamos/agents/run_bridge_loop.py
        # parents[0] = agents
        # parents[1] = dreamos
        # parents[2] = src
        # parents[3] = Dream.os
        workspace_root_path = Path(__file__).resolve().parents[3]
    except IndexError:
        logger.error("Could not determine workspace root. Please run from within the project structure or provide WORKSPACE_ROOT.")
        return

    logger.info(f"Deduced workspace root: {workspace_root_path}")

    # Initialize AgentBus
    agent_bus_instance = AgentBus()
    
    # Initialize Policy & Belief Manager (PBM) - placeholder
    pbm_instance = None 
    
    bridge_loop_instance = BridgeLoop(str(workspace_root_path), agent_bus_instance, pbm_instance)
    
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(bridge_loop_instance.start())
        loop.run_until_complete(bridge_loop_instance.run())
    except KeyboardInterrupt:
        logger.info("BridgeLoop (main) received KeyboardInterrupt. Shutting down.")
    finally:
        if agent_bus_instance:
            logger.info("Stopping AgentBus (main)...")
            loop.run_until_complete(agent_bus_instance.stop())
            logger.info("AgentBus stopped (main).")
        logger.info("BridgeLoop shut down complete (main).")
        loop.close()

if __name__ == "__main__":
    main() 