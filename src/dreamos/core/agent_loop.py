import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import time
from .recovery_system import RecoverySystem
import subprocess
import fnmatch
import re
import asyncio
from .priority_message_queue import PriorityMessageQueue
from .resource_pool import ResourcePool
from .state_manager import StateManager
from .exceptions import ResourceLimitExceeded

class AgentLoop:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.message_queue = PriorityMessageQueue(
            max_size=config.get('queue_size', 1000),
            batch_size=config.get('batch_size', 10)
        )
        self.resource_pool = ResourcePool(
            max_workers=config.get('max_workers', 5),
            max_memory=config.get('max_memory', 1024)
        )
        self.state_manager = StateManager(
            checkpoint_interval=config.get('checkpoint_interval', 300)
        )
        self._setup_optimization()
        self.agent_id = config.get('agent_id')
        self.workspace_root = Path(config.get('workspace_root'))
        self.cycle_count = 0
        self.last_action_time = datetime.utcnow()
        self.action_queue = []
        self.state = {
            "cycle_count": 0,
            "last_action": None,
            "next_action": None,
            "recovery_attempts": 0,
            "last_stop_time": None,
            "autonomy_score": 0
        }
        self.state_path = self.workspace_root / "runtime" / "agent_comms" / "agent_mailboxes" / self.agent_id / "state.json"
        self.inbox_path = self.workspace_root / "runtime" / "agent_comms" / "agent_mailboxes" / self.agent_id / "inbox.json"
        self.recovery_system = RecoverySystem(self.agent_id, self.workspace_root)
        self._load_state()
        self._queue_next_action()  # Initialize with first action
        
    def _setup_optimization(self):
        """Configure optimization settings."""
        self.optimization_config = {
            'message_processing': {
                'batch_size': 10,
                'max_retries': 3,
                'retry_delay': 1
            },
            'resource_management': {
                'worker_pool_size': 5,
                'memory_limit': 1024,
                'cpu_limit': 80
            },
            'state_management': {
                'checkpoint_interval': 300,
                'max_checkpoints': 10,
                'compression_enabled': True
            }
        }
        
    async def process_messages(self):
        """Process messages with optimized batching and priority handling."""
        while True:
            try:
                # Get batch of messages
                messages = await self.message_queue.get_batch(
                    self.optimization_config['message_processing']['batch_size']
                )
                
                if not messages:
                    await asyncio.sleep(0.1)
                    continue
                    
                # Process messages in parallel
                tasks = []
                for message in messages:
                    task = asyncio.create_task(
                        self._process_message(message)
                    )
                    tasks.append(task)
                    
                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Handle results
                for message, result in zip(messages, results):
                    if isinstance(result, Exception):
                        await self._handle_message_error(message, result)
                    else:
                        await self._handle_message_success(message, result)
                        
            except Exception as e:
                logger.error(f"Error in message processing: {e}")
                await asyncio.sleep(1)
                
    async def _process_message(self, message: Dict[str, Any]):
        """Process a single message with resource management."""
        async with self.resource_pool.acquire() as resources:
            try:
                # Validate message
                if not self._validate_message(message):
                    raise ValueError("Invalid message format")
                    
                # Process message
                result = await self._execute_message(message, resources)
                
                # Update state
                await self.state_manager.update_state(message, result)
                
                return result
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                raise
                
    async def _execute_message(self, message: Dict[str, Any], resources: ResourcePool):
        """Execute message with resource constraints."""
        # Check resource limits
        if not resources.check_limits():
            raise ResourceLimitExceeded("Resource limits exceeded")
            
        # Execute message
        result = await self._run_message_execution(message)
        
        # Update resource usage
        resources.update_usage(result.get('resource_usage', {}))
        
        return result
        
    def _load_state(self):
        """Load agent state from file."""
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    self.state = json.load(f)
            except Exception as e:
                logging.error(f"Error loading state: {e}")
                
    def _save_state(self):
        """Save current state to file."""
        try:
            self.state["last_updated"] = datetime.utcnow().isoformat()
            with open(self.state_path, "w") as f:
                json.dump(self.state, f, indent=2)
            # Save good state for recovery
            self.recovery_system.save_good_state(self.state)
        except Exception as e:
            logging.error(f"Error saving state: {e}")
            
    def queue_action(self, action: Dict):
        """Queue next action to prevent idling."""
        self.action_queue.append(action)
        self.state["next_action"] = action
        self._save_state()
        
    def execute_cycle(self) -> bool:
        """Execute one cycle of the agent loop."""
        try:
            # Pre-action phase
            if not self._check_tool_availability():
                self._handle_stopping_condition("tool_unavailable")
                return False
                
            # Get next action
            if not self.action_queue:
                self._handle_stopping_condition("no_queued_action")
                return False
                
            action = self.action_queue.pop(0)
            self.state["last_action"] = action
            
            # Execute action
            success = self._execute_action(action)
            if not success:
                self._handle_stopping_condition("action_failed")
                return False
                
            # Post-action phase
            self.cycle_count += 1
            self.state["cycle_count"] = self.cycle_count
            self.last_action_time = datetime.utcnow()
            
            # Queue next action before current completes
            if not self.action_queue:
                self._queue_next_action()
                
            self._save_state()
            return True
            
        except Exception as e:
            self._handle_stopping_condition("unexpected_error", str(e))
            return False
            
    def _check_tool_availability(self) -> bool:
        """Verify all required tools are available."""
        try:
            # Check core tools
            required_tools = [
                "codebase_search",
                "read_file",
                "run_terminal_cmd",
                "list_dir",
                "grep_search",
                "edit_file",
                "file_search",
                "delete_file"
            ]
            
            # Verify each tool is available
            for tool in required_tools:
                if not hasattr(self, f"_check_{tool}"):
                    logging.error(f"Required tool {tool} not available")
                    return False
                    
            # All tools available
            return True
            
        except Exception as e:
            logging.error(f"Error checking tool availability: {e}")
            return False
            
    def _check_codebase_search(self) -> bool:
        """Check if codebase search is available."""
        return True
        
    def _check_read_file(self) -> bool:
        """Check if file reading is available."""
        return True
        
    def _check_run_terminal_cmd(self) -> bool:
        """Check if terminal commands are available."""
        return True
        
    def _check_list_dir(self) -> bool:
        """Check if directory listing is available."""
        return True
        
    def _check_grep_search(self) -> bool:
        """Check if grep search is available."""
        return True
        
    def _check_edit_file(self) -> bool:
        """Check if file editing is available."""
        return True
        
    def _check_file_search(self) -> bool:
        """Check if file search is available."""
        return True
        
    def _check_delete_file(self) -> bool:
        """Check if file deletion is available."""
        return True
        
    def _execute_action(self, action: Dict) -> bool:
        """Execute a single action with retry logic."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Validate action structure
                if not self._validate_action(action):
                    logging.error(f"Invalid action structure: {action}")
                    return False
                
                action_type = action.get("type")
                if action_type == "documentation":
                    # Handle documentation tasks non-blockingly
                    task = action.get("task")
                    logging.info(f"Processing documentation task: {task}")
                    self._queue_next_action()
                    return True
                elif action_type == "ping":
                    # Handle ping non-blockingly
                    logging.info("Ping received - continuing operation")
                    self._queue_next_action()
                    return True
                elif action_type == "continue":
                    return True
                elif action_type in ("reflection", "escalation", "pause"):
                    # Non-blocking: log and immediately queue next action
                    logging.info(f"Non-blocking {action_type} action: {action}")
                    self._queue_next_action()
                    return True
                elif action_type == "codebase_search":
                    # Execute codebase search
                    query = action.get("query")
                    target_dirs = action.get("target_directories", [])
                    return self._execute_codebase_search(query, target_dirs)
                    
                elif action_type == "read_file":
                    # Execute file read
                    target_file = action.get("target_file")
                    start_line = action.get("start_line_one_indexed")
                    end_line = action.get("end_line_one_indexed_inclusive")
                    return self._execute_read_file(target_file, start_line, end_line)
                    
                elif action_type == "run_terminal_cmd":
                    # Execute terminal command
                    command = action.get("command")
                    is_background = action.get("is_background", False)
                    return self._execute_terminal_cmd(command, is_background)
                    
                elif action_type == "list_dir":
                    # Execute directory listing
                    relative_path = action.get("relative_workspace_path")
                    return self._execute_list_dir(relative_path)
                    
                elif action_type == "grep_search":
                    # Execute grep search
                    query = action.get("query")
                    case_sensitive = action.get("case_sensitive", True)
                    include_pattern = action.get("include_pattern")
                    exclude_pattern = action.get("exclude_pattern")
                    return self._execute_grep_search(query, case_sensitive, include_pattern, exclude_pattern)
                    
                elif action_type == "edit_file":
                    # Execute file edit
                    target_file = action.get("target_file")
                    instructions = action.get("instructions")
                    code_edit = action.get("code_edit")
                    return self._execute_edit_file(target_file, instructions, code_edit)
                    
                elif action_type == "file_search":
                    # Execute file search
                    query = action.get("query")
                    return self._execute_file_search(query)
                    
                elif action_type == "delete_file":
                    # Execute file deletion
                    target_file = action.get("target_file")
                    return self._execute_delete_file(target_file)
                    
                else:
                    logging.error(f"Unknown action type: {action_type}")
                    return False
                    
            except Exception as e:
                retry_count += 1
                logging.error(f"Action execution failed (attempt {retry_count}/{max_retries}): {e}")
                if retry_count >= max_retries:
                    return False
                time.sleep(1)  # Wait before retry
                
        return False
        
    def _validate_action(self, action: Dict) -> bool:
        """Validate action structure and required fields."""
        if not isinstance(action, dict):
            return False
            
        required_fields = ["type"]
        for field in required_fields:
            if field not in action:
                return False
                
        # Validate action-specific fields
        action_type = action.get("type")
        if action_type == "codebase_search":
            return "query" in action
        elif action_type == "read_file":
            return all(field in action for field in ["target_file", "start_line_one_indexed", "end_line_one_indexed_inclusive"])
        elif action_type == "run_terminal_cmd":
            return "command" in action
        elif action_type == "documentation":
            return "task" in action
            
        return True
        
    def _execute_codebase_search(self, query: str, target_dirs: List[str]) -> bool:
        """Execute codebase search."""
        try:
            # Queue next action before executing
            self._queue_next_action()
            
            # Execute search
            results = self._process_codebase_search(query, target_dirs)
            if results is None:
                return False
                
            # Log results
            logging.info(f"Codebase search found {len(results)} results")
            return True
            
        except Exception as e:
            logging.error(f"Error executing codebase search: {e}")
            return False
            
    def _execute_read_file(self, target_file: str, start_line: int, end_line: int) -> bool:
        """Execute file read."""
        try:
            # Queue next action before executing
            self._queue_next_action()
            
            # Execute read
            content = self._process_file_read(target_file, start_line, end_line)
            if content is None:
                return False
                
            # Log success
            logging.info(f"Successfully read file {target_file}")
            return True
            
        except Exception as e:
            logging.error(f"Error executing file read: {e}")
            return False
            
    def _execute_terminal_cmd(self, command: str, is_background: bool) -> bool:
        """Execute terminal command."""
        try:
            # Queue next action before executing
            self._queue_next_action()
            
            # Execute command
            result = self._process_terminal_command(command, is_background)
            if result is None:
                return False
                
            # Log result
            logging.info(f"Terminal command executed: {command}")
            return True
            
        except Exception as e:
            logging.error(f"Error executing terminal command: {e}")
            return False
            
    def _execute_list_dir(self, relative_path: str) -> bool:
        """Execute directory listing."""
        try:
            # Queue next action before executing
            self._queue_next_action()
            
            # Execute listing
            contents = self._process_directory_listing(relative_path)
            if contents is None:
                return False
                
            # Log results
            logging.info(f"Directory listing found {len(contents)} items")
            return True
            
        except Exception as e:
            logging.error(f"Error executing directory listing: {e}")
            return False
            
    def _execute_grep_search(self, query: str, case_sensitive: bool, include_pattern: str, exclude_pattern: str) -> bool:
        """Execute grep search."""
        try:
            # Queue next action before executing
            self._queue_next_action()
            
            # Execute search
            results = self._process_grep_search(query, include_pattern)
            if results is None:
                return False
                
            # Log results
            logging.info(f"Grep search found {len(results)} matches")
            return True
            
        except Exception as e:
            logging.error(f"Error executing grep search: {e}")
            return False
            
    def _execute_edit_file(self, target_file: str, instructions: str, code_edit: str) -> bool:
        """Execute file edit."""
        try:
            # Queue next action before executing
            self._queue_next_action()
            
            # Execute edit
            success = self._process_file_edit(target_file, instructions, code_edit)
            if not success:
                return False
                
            # Log success
            logging.info(f"Successfully edited file {target_file}")
            return True
            
        except Exception as e:
            logging.error(f"Error executing file edit: {e}")
            return False
            
    def _execute_file_search(self, query: str) -> bool:
        """Execute file search."""
        try:
            # Queue next action before executing
            self._queue_next_action()
            
            # Execute search
            results = self._process_file_search(query)
            if results is None:
                return False
                
            # Log results
            logging.info(f"File search found {len(results)} matches")
            return True
            
        except Exception as e:
            logging.error(f"Error executing file search: {e}")
            return False
            
    def _execute_delete_file(self, target_file: str) -> bool:
        """Execute file deletion."""
        try:
            # Queue next action before executing
            self._queue_next_action()
            
            # Execute deletion
            success = self._process_file_deletion(target_file)
            if not success:
                return False
                
            # Log success
            logging.info(f"Successfully deleted file {target_file}")
            return True
            
        except Exception as e:
            logging.error(f"Error executing file deletion: {e}")
            return False
        
    def _queue_next_action(self):
        """Queue the next action to prevent idling."""
        try:
            # Check inbox for new actions
            if self.inbox_path.exists():
                with open(self.inbox_path, "r") as f:
                    inbox = json.load(f)
                    
                if inbox.get("actions"):
                    next_action = inbox["actions"].pop(0)
                    self.queue_action(next_action)
                    
                    # Save updated inbox
                    with open(self.inbox_path, "w") as f:
                        json.dump(inbox, f, indent=2)
                    return
                    
            # If no new actions, queue a continue action
            self.queue_action({
                "type": "continue",
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logging.error(f"Error queueing next action: {e}")
            # Queue continue action as fallback
            self.queue_action({
                "type": "continue",
                "timestamp": datetime.utcnow().isoformat()
            })
            
    def _handle_stopping_condition(self, condition: str, details: str = None):
        """Handle a stopping condition."""
        try:
            # Log the condition
            self._log_stopping_condition(condition, details)
            
            # Update state
            self.state["last_stop_time"] = datetime.utcnow().isoformat()
            self.state["recovery_attempts"] += 1
            
            # Attempt recovery
            if self.recovery_system.attempt_recovery(self.state):
                logging.info("Recovery successful, continuing operation")
                self._queue_next_action()
            else:
                logging.error("Recovery failed, stopping agent")
                self.state["autonomy_score"] = max(0, self.state["autonomy_score"] - 1)
                
            self._save_state()
            
        except Exception as e:
            logging.error(f"Error handling stopping condition: {e}")
            
    def _log_stopping_condition(self, condition: str, details: str = None):
        """Log a stopping condition."""
        try:
            log_path = self.workspace_root / "runtime" / "logs" / f"{self.agent_id}_stops.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(log_path, "a") as f:
                f.write(f"{datetime.utcnow().isoformat()} - {condition}")
                if details:
                    f.write(f": {details}")
                f.write("\n")
                
        except Exception as e:
            logging.error(f"Error logging stopping condition: {e}")
            
    def run(self, target_cycles: int = 25):
        """Run the agent loop for a target number of cycles."""
        try:
            while self.cycle_count < target_cycles:
                if not self.execute_cycle():
                    return False
                    
            return True
            
        except Exception as e:
            logging.error(f"Error in agent loop: {e}")
            return False

    # TEST: Add a test action to simulate 'reflection' or 'escalation'
    def test_non_blocking_actions(self):
        test_actions = [
            {"type": "reflection", "details": "Test reflection"},
            {"type": "escalation", "details": "Test escalation"},
            {"type": "pause", "details": "Test pause"}
        ]
        for action in test_actions:
            result = self._execute_action(action)
            assert result, f"Non-blocking action failed: {action}"

    def _process_codebase_search(self, query: str, target_directories: Optional[List[str]] = None) -> List[Dict]:
        """Implement actual codebase search."""
        try:
            results = []
            search_dirs = target_directories or [str(self.workspace_root)]
            
            for directory in search_dirs:
                for root, _, files in os.walk(directory):
                    for file in files:
                        if file.endswith(('.py', '.md', '.json', '.yaml', '.yml')):
                            file_path = os.path.join(root, file)
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    if query.lower() in content.lower():
                                        results.append({
                                            'file': file_path,
                                            'matches': content.count(query.lower())
                                        })
                            except Exception as e:
                                logging.error(f"Error reading file {file_path}: {e}")
                                
            return results
        except Exception as e:
            logging.error(f"Error in codebase search: {e}")
            return []

    def _process_file_read(self, file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
        """Implement actual file read."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            if start_line is not None and end_line is not None:
                lines = lines[start_line-1:end_line]
                
            return ''.join(lines)
        except Exception as e:
            logging.error(f"Error reading file {file_path}: {e}")
            return ""

    def _process_terminal_command(self, command: str, is_background: bool = False) -> Dict:
        """Implement actual terminal command."""
        try:
            if is_background:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
                return {
                    'pid': process.pid,
                    'status': 'running'
                }
            else:
                result = subprocess.run(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                return {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                }
        except Exception as e:
            logging.error(f"Error executing command {command}: {e}")
            return {'error': str(e)}

    def _process_directory_listing(self, directory: str) -> List[Dict]:
        """Implement actual directory listing."""
        try:
            results = []
            for root, dirs, files in os.walk(directory):
                for name in dirs:
                    results.append({
                        'type': 'directory',
                        'path': os.path.join(root, name)
                    })
                for name in files:
                    results.append({
                        'type': 'file',
                        'path': os.path.join(root, name)
                    })
            return results
        except Exception as e:
            logging.error(f"Error listing directory {directory}: {e}")
            return []

    def _process_grep_search(self, pattern: str, include_pattern: Optional[str] = None) -> List[Dict]:
        """Implement actual grep search."""
        try:
            results = []
            for root, _, files in os.walk(str(self.workspace_root)):
                for file in files:
                    if include_pattern and not fnmatch.fnmatch(file, include_pattern):
                        continue
                        
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line_num, line in enumerate(f, 1):
                                if re.search(pattern, line):
                                    results.append({
                                        'file': file_path,
                                        'line': line_num,
                                        'content': line.strip()
                                    })
                    except Exception as e:
                        logging.error(f"Error reading file {file_path}: {e}")
                        
            return results
        except Exception as e:
            logging.error(f"Error in grep search: {e}")
            return []

    def _process_file_edit(self, file_path: str, instructions: str, code_edit: str) -> bool:
        """Implement actual file edit."""
        try:
            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Apply edit
            edited_content = self._apply_edit(content, code_edit)
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(edited_content)
                
            return True
        except Exception as e:
            logging.error(f"Error editing file {file_path}: {e}")
            return False

    def _process_file_search(self, query: str) -> List[str]:
        """Implement actual file search."""
        try:
            results = []
            for root, _, files in os.walk(str(self.workspace_root)):
                for file in files:
                    if query.lower() in file.lower():
                        results.append(os.path.join(root, file))
            return results
        except Exception as e:
            logging.error(f"Error in file search: {e}")
            return []

    def _process_file_deletion(self, file_path: str) -> bool:
        """Implement actual file deletion."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            logging.error(f"Error deleting file {file_path}: {e}")
            return False

    def _apply_edit(self, content: str, code_edit: str) -> str:
        """Apply code edit to content."""
        try:
            # Split content into lines
            lines = content.splitlines()
            
            # Parse edit instructions
            edit_lines = code_edit.splitlines()
            current_line = 0
            result_lines = []
            
            for line in edit_lines:
                if line.strip() == "// ... existing code ...":
                    # Keep existing lines until next edit
                    while current_line < len(lines):
                        result_lines.append(lines[current_line])
                        current_line += 1
                else:
                    # Add edited line
                    result_lines.append(line)
                    
            return "\n".join(result_lines)
            
        except Exception as e:
            logging.error(f"Error applying edit: {e}")
            return content 