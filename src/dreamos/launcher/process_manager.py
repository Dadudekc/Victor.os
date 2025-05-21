"""
Dream.OS Process Management Module

Provides process spawning, monitoring, resource management, and checkpoint integration
for Dream.OS components launched through the centralized launcher.

Features:
- Cross-platform process management
- Resource usage monitoring and limits
- Checkpoint protocol integration
- Graceful recovery from process failures
- Logging and diagnostics
"""

import os
import sys
import time
import signal
import logging
import subprocess
import threading
import psutil
import json
import shlex
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from datetime import datetime

# Constants
ROOT_DIR = Path(os.getcwd()).resolve()
RUNTIME_DIR = ROOT_DIR / "runtime"
PROCESS_DIR = RUNTIME_DIR / "processes"
CHECKPOINT_DIR = RUNTIME_DIR / "checkpoints"
LOG_DIR = RUNTIME_DIR / "logs" / "processes"

# Ensure directories exist
for dir_path in [PROCESS_DIR, CHECKPOINT_DIR, LOG_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dreamos.launcher.process_manager")


class ProcessManager:
    """
    Manager for spawning, monitoring, and controlling Dream.OS component processes.
    """
    
    def __init__(self):
        """Initialize the process manager."""
        self._processes = {}  # Map of process_id -> process data
        self._lock = threading.RLock()
        self._monitors = {}  # Map of process_id -> monitor thread
        self._recovery_handlers = {}  # Map of component_type -> recovery handler
        self._load_running_processes()
        
        # Register default recovery handlers
        self.register_recovery_handler("agent", self._default_agent_recovery)
        self.register_recovery_handler("service", self._default_service_recovery)
        self.register_recovery_handler("tool", self._default_tool_recovery)
        self.register_recovery_handler("utility", self._default_utility_recovery)
        
    def _load_running_processes(self):
        """Load information about already running processes."""
        try:
            process_files = list(PROCESS_DIR.glob("*.json"))
            for file_path in process_files:
                try:
                    with open(file_path, 'r') as f:
                        process_data = json.load(f)
                    
                    process_id = process_data.get("process_id")
                    if not process_id:
                        continue
                        
                    pid = process_data.get("pid")
                    if not pid:
                        continue
                        
                    # Check if process is still running
                    try:
                        process = psutil.Process(pid)
                        if process.is_running():
                            self._processes[process_id] = process_data
                            # Start monitoring thread for existing process
                            self._start_monitor(process_id)
                            logger.info(f"Loaded running process: {process_id} (PID: {pid})")
                        else:
                            # Process not running, mark as crashed
                            process_data["status"] = "crashed"
                            process_data["end_time"] = datetime.now().isoformat()
                            self._save_process_data(process_id, process_data)
                            logger.warning(f"Process {process_id} (PID: {pid}) not running, marked as crashed")
                    except psutil.NoSuchProcess:
                        # Process not running, mark as crashed
                        process_data["status"] = "crashed"
                        process_data["end_time"] = datetime.now().isoformat()
                        self._save_process_data(process_id, process_data)
                        logger.warning(f"Process {process_id} (PID: {pid}) not found, marked as crashed")
                except Exception as e:
                    logger.error(f"Error loading process data from {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading running processes: {e}")
            
    def _save_process_data(self, process_id: str, process_data: Dict[str, Any]) -> bool:
        """
        Save process data to disk.
        
        Args:
            process_id: ID of the process
            process_data: Process data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = PROCESS_DIR / f"{process_id}.json"
            with open(file_path, 'w') as f:
                json.dump(process_data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving process data for {process_id}: {e}")
            return False
            
    def _generate_process_id(self, component_id: str) -> str:
        """
        Generate a unique process ID for a component.
        
        Args:
            component_id: ID of the component
            
        Returns:
            Unique process ID
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{component_id}_{timestamp}"
        
    def _monitor_process(self, process_id: str):
        """
        Monitor a running process and handle termination.
        
        Args:
            process_id: ID of the process to monitor
        """
        try:
            with self._lock:
                if process_id not in self._processes:
                    logger.warning(f"Process {process_id} not found for monitoring")
                    return
                    
                process_data = self._processes[process_id]
                pid = process_data.get("pid")
                
                if not pid:
                    logger.warning(f"No PID found for process {process_id}")
                    return
                    
            try:
                process = psutil.Process(pid)
                
                # Monitor loop
                while True:
                    try:
                        # Check if process is still running
                        if not process.is_running():
                            break
                            
                        # Collect resource usage
                        try:
                            cpu_percent = process.cpu_percent(interval=1.0)
                            memory_info = process.memory_info()
                            memory_mb = memory_info.rss / (1024 * 1024)
                            
                            # Update process data with resource usage
                            with self._lock:
                                if process_id in self._processes:
                                    self._processes[process_id]["resource_usage"] = {
                                        "cpu_percent": cpu_percent,
                                        "memory_mb": memory_mb,
                                        "timestamp": datetime.now().isoformat()
                                    }
                                    
                            # Check resource limits
                            self._check_resource_limits(process_id, cpu_percent, memory_mb)
                            
                            # Save checkpoint if needed
                            self._check_checkpoint_needs(process_id)
                        except Exception as e:
                            logger.error(f"Error collecting resource usage for {process_id}: {e}")
                            
                        # Sleep for monitoring interval
                        time.sleep(5)
                    except Exception as e:
                        logger.error(f"Error in monitoring loop for {process_id}: {e}")
                        time.sleep(5)
                        
                # Process has terminated
                with self._lock:
                    if process_id in self._processes:
                        # Update process data
                        self._processes[process_id]["status"] = "terminated"
                        self._processes[process_id]["end_time"] = datetime.now().isoformat()
                        
                        # Handle recovery if needed
                        self._handle_process_termination(process_id)
                        
                        # Save updated process data
                        self._save_process_data(process_id, self._processes[process_id])
                        
                        logger.info(f"Process {process_id} (PID: {pid}) has terminated")
            except psutil.NoSuchProcess:
                with self._lock:
                    if process_id in self._processes:
                        # Update process data
                        self._processes[process_id]["status"] = "crashed"
                        self._processes[process_id]["end_time"] = datetime.now().isoformat()
                        
                        # Handle recovery if needed
                        self._handle_process_termination(process_id)
                        
                        # Save updated process data
                        self._save_process_data(process_id, self._processes[process_id])
                        
                        logger.warning(f"Process {process_id} (PID: {pid}) has crashed")
        except Exception as e:
            logger.error(f"Error monitoring process {process_id}: {e}")
        finally:
            # Clean up
            with self._lock:
                if process_id in self._monitors:
                    del self._monitors[process_id]
                    
    def _start_monitor(self, process_id: str):
        """
        Start a monitoring thread for a process.
        
        Args:
            process_id: ID of the process to monitor
        """
        if process_id in self._monitors:
            return
            
        monitor_thread = threading.Thread(
            target=self._monitor_process,
            args=(process_id,),
            daemon=True
        )
        self._monitors[process_id] = monitor_thread
        monitor_thread.start()
        
    def _check_resource_limits(self, process_id: str, cpu_percent: float, memory_mb: float):
        """
        Check if a process has exceeded its resource limits.
        
        Args:
            process_id: ID of the process
            cpu_percent: CPU usage percentage
            memory_mb: Memory usage in MB
        """
        with self._lock:
            if process_id not in self._processes:
                return
                
            process_data = self._processes[process_id]
            limits = process_data.get("resource_limits", {})
            
            # Check CPU limit
            cpu_limit = limits.get("cpu_percent")
            if cpu_limit and cpu_percent > cpu_limit:
                logger.warning(f"Process {process_id} exceeded CPU limit: {cpu_percent}% > {cpu_limit}%")
                
                # Log resource warning
                if "warnings" not in process_data:
                    process_data["warnings"] = []
                    
                process_data["warnings"].append({
                    "type": "cpu_limit_exceeded",
                    "timestamp": datetime.now().isoformat(),
                    "value": cpu_percent,
                    "limit": cpu_limit
                })
                
                # Update process data
                self._save_process_data(process_id, process_data)
                
            # Check memory limit
            memory_limit = limits.get("memory_mb")
            if memory_limit and memory_mb > memory_limit:
                logger.warning(f"Process {process_id} exceeded memory limit: {memory_mb}MB > {memory_limit}MB")
                
                # Log resource warning
                if "warnings" not in process_data:
                    process_data["warnings"] = []
                    
                process_data["warnings"].append({
                    "type": "memory_limit_exceeded",
                    "timestamp": datetime.now().isoformat(),
                    "value": memory_mb,
                    "limit": memory_limit
                })
                
                # Update process data
                self._save_process_data(process_id, process_data)
                
    def _check_checkpoint_needs(self, process_id: str):
        """
        Check if a process needs to create a checkpoint.
        
        Args:
            process_id: ID of the process
        """
        with self._lock:
            if process_id not in self._processes:
                return
                
            process_data = self._processes[process_id]
            
            # Skip if checkpointing is disabled
            if not process_data.get("checkpoint_enabled", False):
                return
                
            # Check if it's time for a checkpoint
            last_checkpoint = process_data.get("last_checkpoint")
            checkpoint_interval = process_data.get("checkpoint_interval", 3600)  # Default: 1 hour
            
            if last_checkpoint:
                last_time = datetime.fromisoformat(last_checkpoint)
                now = datetime.now()
                
                # If interval has passed, trigger checkpoint
                if (now - last_time).total_seconds() >= checkpoint_interval:
                    self._trigger_checkpoint(process_id)
            else:
                # No checkpoint yet, trigger first one
                self._trigger_checkpoint(process_id)
                
    def _trigger_checkpoint(self, process_id: str):
        """
        Trigger a checkpoint for a process.
        
        Args:
            process_id: ID of the process
        """
        with self._lock:
            if process_id not in self._processes:
                return
                
            process_data = self._processes[process_id]
            
            # Create checkpoint metadata
            checkpoint_id = f"{process_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            checkpoint_path = CHECKPOINT_DIR / f"{checkpoint_id}.json"
            
            # Update process data
            process_data["last_checkpoint"] = datetime.now().isoformat()
            process_data["current_checkpoint"] = checkpoint_id
            
            # Save process data
            self._save_process_data(process_id, process_data)
            
            # Notify process of checkpoint (to be implemented based on checkpoint protocol)
            logger.info(f"Triggered checkpoint for process {process_id}: {checkpoint_id}")
            
    def _handle_process_termination(self, process_id: str):
        """
        Handle process termination, including recovery if needed.
        
        Args:
            process_id: ID of the process
        """
        with self._lock:
            if process_id not in self._processes:
                return
                
            process_data = self._processes[process_id]
            component_type = process_data.get("component_type")
            restart_policy = process_data.get("restart_policy", "NEVER")
            
            # Handle according to restart policy
            if restart_policy == "ALWAYS" or (restart_policy == "ON_FAILURE" and process_data.get("status") == "crashed"):
                logger.info(f"Restarting process {process_id} according to policy: {restart_policy}")
                
                # Call appropriate recovery handler
                if component_type in self._recovery_handlers:
                    self._recovery_handlers[component_type](process_id, process_data)
                else:
                    # Use default recovery
                    self._default_recovery(process_id, process_data)
            else:
                logger.info(f"Not restarting process {process_id} (policy: {restart_policy}, status: {process_data.get('status')})")
                
    def _default_recovery(self, process_id: str, process_data: Dict[str, Any]):
        """
        Default recovery handler for processes.
        
        Args:
            process_id: ID of the process
            process_data: Process data
        """
        try:
            # Get component information
            component_id = process_data.get("component_id")
            entry_point = process_data.get("entry_point")
            args = process_data.get("args", [])
            
            if not component_id or not entry_point:
                logger.error(f"Cannot recover process {process_id}: missing component_id or entry_point")
                return
                
            # Create new process ID
            new_process_id = self._generate_process_id(component_id)
            
            # Start process
            success, new_process_data = self.start_process(
                component_id=component_id,
                component_type=process_data.get("component_type", "unknown"),
                entry_point=entry_point,
                args=args,
                env=process_data.get("env", {}),
                cwd=process_data.get("cwd"),
                resource_limits=process_data.get("resource_limits", {}),
                restart_policy=process_data.get("restart_policy", "NEVER"),
                checkpoint_enabled=process_data.get("checkpoint_enabled", False),
                checkpoint_interval=process_data.get("checkpoint_interval", 3600),
                process_id=new_process_id,
                recovered_from=process_id
            )
            
            if success:
                logger.info(f"Successfully recovered process {process_id} as {new_process_id}")
            else:
                logger.error(f"Failed to recover process {process_id}")
        except Exception as e:
            logger.error(f"Error in default recovery for process {process_id}: {e}")
            
    def _default_agent_recovery(self, process_id: str, process_data: Dict[str, Any]):
        """
        Recovery handler for agent processes.
        
        Args:
            process_id: ID of the process
            process_data: Process data
        """
        # Agent-specific recovery logic
        self._default_recovery(process_id, process_data)
        
    def _default_service_recovery(self, process_id: str, process_data: Dict[str, Any]):
        """
        Recovery handler for service processes.
        
        Args:
            process_id: ID of the process
            process_data: Process data
        """
        # Service-specific recovery logic
        self._default_recovery(process_id, process_data)
        
    def _default_tool_recovery(self, process_id: str, process_data: Dict[str, Any]):
        """
        Recovery handler for tool processes.
        
        Args:
            process_id: ID of the process
            process_data: Process data
        """
        # Tools typically don't need recovery
        logger.info(f"Not recovering tool process {process_id}")
        
    def _default_utility_recovery(self, process_id: str, process_data: Dict[str, Any]):
        """
        Recovery handler for utility processes.
        
        Args:
            process_id: ID of the process
            process_data: Process data
        """
        # Utilities typically don't need recovery
        logger.info(f"Not recovering utility process {process_id}")
        
    def register_recovery_handler(self, component_type: str, handler: Callable[[str, Dict[str, Any]], None]):
        """
        Register a recovery handler for a component type.
        
        Args:
            component_type: Type of component
            handler: Recovery handler function
        """
        self._recovery_handlers[component_type] = handler
        
    def get_process_info(self, process_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a running process.
        
        Args:
            process_id: ID of the process
            
        Returns:
            Process data or None if not found
        """
        with self._lock:
            process_data = self._processes.get(process_id)
            if process_data:
                return dict(process_data)  # Return a copy
            return None
            
    def get_all_processes(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all managed processes.
        
        Returns:
            Dictionary of process_id -> process data
        """
        with self._lock:
            return {k: dict(v) for k, v in self._processes.items()}
            
    def get_component_processes(self, component_id: str) -> List[Dict[str, Any]]:
        """
        Get all processes for a specific component.
        
        Args:
            component_id: ID of the component
            
        Returns:
            List of process data dictionaries
        """
        with self._lock:
            return [
                dict(proc) for proc in self._processes.values()
                if proc.get("component_id") == component_id
            ]
            
    def start_process(self, 
                     component_id: str,
                     component_type: str,
                     entry_point: str,
                     args: List[str] = None,
                     env: Dict[str, str] = None,
                     cwd: str = None,
                     resource_limits: Dict[str, Any] = None,
                     restart_policy: str = "NEVER",
                     checkpoint_enabled: bool = False,
                     checkpoint_interval: int = 3600,
                     process_id: str = None,
                     recovered_from: str = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Start a new process for a component.
        
        Args:
            component_id: ID of the component
            component_type: Type of component (agent, service, tool, utility)
            entry_point: Path to the entry point script
            args: Command-line arguments
            env: Environment variables
            cwd: Working directory
            resource_limits: Resource limits
            restart_policy: Restart policy (NEVER, ON_FAILURE, ALWAYS)
            checkpoint_enabled: Whether to enable checkpointing
            checkpoint_interval: Checkpoint interval in seconds
            process_id: Process ID (generated if not provided)
            recovered_from: ID of the process this is recovering from
            
        Returns:
            Tuple of (success, process_data)
        """
        try:
            # Generate process ID if not provided
            if not process_id:
                process_id = self._generate_process_id(component_id)
                
            # Resolve entry point path
            entry_path = Path(entry_point)
            if not entry_path.is_absolute():
                entry_path = ROOT_DIR / entry_path
                
            # Check if entry point exists
            if not entry_path.exists():
                logger.error(f"Entry point does not exist: {entry_path}")
                return False, None
                
            # Determine working directory
            if cwd:
                working_dir = Path(cwd)
                if not working_dir.is_absolute():
                    working_dir = ROOT_DIR / working_dir
            else:
                working_dir = entry_path.parent
                
            # Set up environment
            process_env = os.environ.copy()
            if env:
                process_env.update(env)
                
            # Set up command
            cmd = [sys.executable, str(entry_path)]
            if args:
                if isinstance(args, list):
                    cmd.extend(args)
                elif isinstance(args, str):
                    cmd.extend(shlex.split(args))
                    
            # Create process data
            process_data = {
                "process_id": process_id,
                "component_id": component_id,
                "component_type": component_type,
                "entry_point": str(entry_path),
                "args": args,
                "cwd": str(working_dir),
                "env": {k: v for k, v in env.items()} if env else {},
                "status": "starting",
                "start_time": datetime.now().isoformat(),
                "resource_limits": resource_limits or {},
                "restart_policy": restart_policy,
                "checkpoint_enabled": checkpoint_enabled,
                "checkpoint_interval": checkpoint_interval,
                "log_file": str(LOG_DIR / f"{process_id}.log"),
            }
            
            if recovered_from:
                process_data["recovered_from"] = recovered_from
                
            # Create log directory if needed
            log_path = Path(process_data["log_file"])
            log_path.parent.mkdir(parents=True, exist_ok=True)
                
            # Start process
            logger.info(f"Starting process {process_id} for component {component_id}")
            logger.info(f"Command: {' '.join(cmd)}")
            
            with open(process_data["log_file"], 'w') as log_file:
                process = subprocess.Popen(
                    cmd,
                    cwd=str(working_dir),
                    env=process_env,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                
            # Update process data
            process_data["pid"] = process.pid
            process_data["status"] = "running"
            
            # Save process data
            with self._lock:
                self._processes[process_id] = process_data
                self._save_process_data(process_id, process_data)
                
            # Start monitoring thread
            self._start_monitor(process_id)
            
            logger.info(f"Started process {process_id} for component {component_id} with PID {process.pid}")
            return True, process_data
        except Exception as e:
            logger.error(f"Error starting process for component {component_id}: {e}")
            return False, None
            
    def stop_process(self, process_id: str, force: bool = False, timeout: int = 30) -> bool:
        """
        Stop a running process.
        
        Args:
            process_id: ID of the process to stop
            force: Whether to force kill the process
            timeout: Timeout in seconds to wait for graceful shutdown
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            if process_id not in self._processes:
                logger.warning(f"Process {process_id} not found")
                return False
                
            process_data = self._processes[process_id]
            pid = process_data.get("pid")
            
            if not pid:
                logger.warning(f"No PID found for process {process_id}")
                return False
                
            logger.info(f"Stopping process {process_id} (PID: {pid})")
            
            try:
                process = psutil.Process(pid)
                
                if force:
                    # Force kill
                    process.kill()
                    logger.info(f"Force killed process {process_id} (PID: {pid})")
                else:
                    # Graceful shutdown
                    process.terminate()
                    
                    # Wait for process to terminate
                    try:
                        process.wait(timeout=timeout)
                        logger.info(f"Gracefully stopped process {process_id} (PID: {pid})")
                    except psutil.TimeoutExpired:
                        # Force kill if timeout
                        process.kill()
                        logger.warning(f"Process {process_id} (PID: {pid}) did not terminate gracefully, force killed")
                        
                # Update process data
                process_data["status"] = "terminated"
                process_data["end_time"] = datetime.now().isoformat()
                self._save_process_data(process_id, process_data)
                
                return True
            except psutil.NoSuchProcess:
                # Process already terminated
                process_data["status"] = "terminated"
                process_data["end_time"] = datetime.now().isoformat()
                self._save_process_data(process_id, process_data)
                
                logger.warning(f"Process {process_id} (PID: {pid}) already terminated")
                return True
            except Exception as e:
                logger.error(f"Error stopping process {process_id}: {e}")
                return False
                
    def restart_process(self, process_id: str) -> Tuple[bool, Optional[str]]:
        """
        Restart a process.
        
        Args:
            process_id: ID of the process to restart
            
        Returns:
            Tuple of (success, new_process_id)
        """
        with self._lock:
            if process_id not in self._processes:
                logger.warning(f"Process {process_id} not found")
                return False, None
                
            process_data = dict(self._processes[process_id])
            
            # Stop the current process
            self.stop_process(process_id)
            
            # Create new process ID
            component_id = process_data.get("component_id")
            new_process_id = self._generate_process_id(component_id)
            
            # Start new process
            success, new_process_data = self.start_process(
                component_id=component_id,
                component_type=process_data.get("component_type", "unknown"),
                entry_point=process_data.get("entry_point"),
                args=process_data.get("args", []),
                env=process_data.get("env", {}),
                cwd=process_data.get("cwd"),
                resource_limits=process_data.get("resource_limits", {}),
                restart_policy=process_data.get("restart_policy", "NEVER"),
                checkpoint_enabled=process_data.get("checkpoint_enabled", False),
                checkpoint_interval=process_data.get("checkpoint_interval", 3600),
                process_id=new_process_id,
                recovered_from=process_id
            )
            
            if success:
                logger.info(f"Successfully restarted process {process_id} as {new_process_id}")
                return True, new_process_id
            else:
                logger.error(f"Failed to restart process {process_id}")
                return False, None
                
    def send_signal(self, process_id: str, signal_name: str) -> bool:
        """
        Send a signal to a process.
        
        Args:
            process_id: ID of the process
            signal_name: Name of the signal to send
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            if process_id not in self._processes:
                logger.warning(f"Process {process_id} not found")
                return False
                
            process_data = self._processes[process_id]
            pid = process_data.get("pid")
            
            if not pid:
                logger.warning(f"No PID found for process {process_id}")
                return False
                
            try:
                process = psutil.Process(pid)
                
                # Get signal by name
                sig = getattr(signal, signal_name, None)
                if sig is None:
                    logger.error(f"Invalid signal name: {signal_name}")
                    return False
                    
                # Send signal
                process.send_signal(sig)
                logger.info(f"Sent signal {signal_name} to process {process_id} (PID: {pid})")
                return True
            except psutil.NoSuchProcess:
                logger.warning(f"Process {process_id} (PID: {pid}) not found")
                return False
            except Exception as e:
                logger.error(f"Error sending signal to process {process_id}: {e}")
                return False
                
    def get_process_logs(self, process_id: str, max_lines: int = 100) -> Optional[List[str]]:
        """
        Get logs for a process.
        
        Args:
            process_id: ID of the process
            max_lines: Maximum number of lines to return
            
        Returns:
            List of log lines or None if not found
        """
        with self._lock:
            if process_id not in self._processes:
                logger.warning(f"Process {process_id} not found")
                return None
                
            process_data = self._processes[process_id]
            log_file = process_data.get("log_file")
            
            if not log_file:
                logger.warning(f"No log file found for process {process_id}")
                return None
                
            try:
                with open(log_file, 'r') as f:
                    # Get last N lines
                    lines = f.readlines()
                    return lines[-max_lines:] if len(lines) > max_lines else lines
            except Exception as e:
                logger.error(f"Error reading logs for process {process_id}: {e}")
                return None
                
    def cleanup_old_processes(self, max_age_days: int = 7) -> int:
        """
        Clean up data for old terminated processes.
        
        Args:
            max_age_days: Maximum age in days for process data
            
        Returns:
            Number of processes cleaned up
        """
        cleaned_up = 0
        try:
            process_files = list(PROCESS_DIR.glob("*.json"))
            cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
            
            for file_path in process_files:
                try:
                    # Check file modification time
                    if file_path.stat().st_mtime < cutoff_time:
                        # Read file to check process status
                        with open(file_path, 'r') as f:
                            process_data = json.load(f)
                            
                        status = process_data.get("status")
                        if status in ["terminated", "crashed"]:
                            # Safe to remove
                            file_path.unlink()
                            
                            # Also remove log file if exists
                            log_file = process_data.get("log_file")
                            if log_file:
                                log_path = Path(log_file)
                                if log_path.exists():
                                    log_path.unlink()
                                    
                            cleaned_up += 1
                except Exception as e:
                    logger.error(f"Error cleaning up process file {file_path}: {e}")
            
            logger.info(f"Cleaned up {cleaned_up} old process files")
            return cleaned_up
        except Exception as e:
            logger.error(f"Error cleaning up old processes: {e}")
            return 0


# Singleton instance
_process_manager = None

def get_process_manager() -> ProcessManager:
    """
    Get the singleton instance of the process manager.
    
    Returns:
        ProcessManager instance
    """
    global _process_manager
    if _process_manager is None:
        _process_manager = ProcessManager()
    return _process_manager 