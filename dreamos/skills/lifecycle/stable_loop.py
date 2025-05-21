"""
Stable Autonomous Loop implementation for Dream.OS agents.

This module implements the Autonomous Loop Stability pattern described in
docs/knowledge/patterns/autonomous_loop_stability.md.
"""
import time
import logging
import threading
from typing import Dict, List, Any, Optional, Callable, Set

from .loop_guard import LoopGuard
from .circuit_breaker import CircuitBreaker
from .degraded_mode import DegradedOperationMode

logger = logging.getLogger(__name__)

class StableAutonomousLoop:
    """
    Implementation of the Autonomous Loop Stability pattern.
    
    This class provides a stable framework for implementing autonomous agent loops
    that are resistant to common failure modes such as drift, deadlocks, resource
    exhaustion, and infinite loops.
    
    Usage:
        loop = MyAgentLoop(agent_id="agent-3")
        loop.run()
    """
    
    def __init__(
        self,
        name: str = "autonomous_loop",
        max_cycles: Optional[int] = None,
        drift_detection: bool = True,
        drift_check_interval: int = 10,
        watchdog_timeout: int = 300,
        memory_limit_mb: Optional[int] = None
    ):
        """
        Initialize a stable autonomous loop.
        
        Args:
            name: Name of this loop (for logging)
            max_cycles: Maximum number of cycles to run (None for unlimited)
            drift_detection: Whether to enable drift detection
            drift_check_interval: How many cycles between drift checks
            watchdog_timeout: Timeout in seconds for watchdog timer
            memory_limit_mb: Memory limit in MB (None for no limit)
        """
        self.name = name
        self.max_cycles = max_cycles
        self.drift_detection = drift_detection
        self.drift_check_interval = drift_check_interval
        self.watchdog_timeout = watchdog_timeout
        self.memory_limit_mb = memory_limit_mb
        
        # State tracking
        self.cycle_count = 0
        self.state = {}  # Persistent state across cycles
        self.temp_state = {}  # Temporary state for current cycle
        self.circuit_breakers = {}
        self.resources = []
        
        # Performance tracking
        self.cycle_durations = []
        self.last_cycle_start = 0
        self.running = False
    
    def run(self):
        """
        Run the autonomous loop until completion or interruption.
        """
        self.running = True
        
        with LoopGuard(
            timeout=self.watchdog_timeout,
            memory_limit_mb=self.memory_limit_mb,
            on_timeout=self._handle_watchdog_timeout,
            on_resource_limit=self._handle_resource_limit
        ) as guard:
            while self._should_continue():
                try:
                    # Begin cycle
                    self.last_cycle_start = time.time()
                    self._begin_cycle()
                    
                    # Process core operations with circuit breakers
                    self._process_operations()
                    
                    # End cycle with persistence and validation
                    self._end_cycle()
                    
                    # Track cycle duration
                    duration = time.time() - self.last_cycle_start
                    self.cycle_durations.append(duration)
                    if len(self.cycle_durations) > 100:
                        self.cycle_durations = self.cycle_durations[-100:]
                    
                    # Report heartbeat
                    self._report_heartbeat("healthy")
                    
                    # Detect drift if enabled
                    if self.drift_detection and self.cycle_count % self.drift_check_interval == 0:
                        self._check_for_drift()
                        
                except Exception as e:
                    logger.error(f"Error in cycle {self.cycle_count}: {str(e)}", exc_info=True)
                    if not self._recover_from_error(e):
                        # Unrecoverable error - enter degraded mode
                        self._handle_unrecoverable_error(e)
                
                # Increment cycle count
                self.cycle_count += 1
                
                # Reset watchdog for next cycle
                guard.reset_watchdog()
        
        self.running = False
    
    def stop(self):
        """
        Request the loop to stop after the current cycle.
        """
        self.running = False
    
    def _should_continue(self) -> bool:
        """
        Check if the loop should continue running.
        
        Returns:
            True if the loop should continue, False otherwise
        """
        # Check if stop was requested
        if not self.running:
            return False
            
        # Check if max cycles reached
        if self.max_cycles is not None and self.cycle_count >= self.max_cycles:
            logger.info(f"Reached maximum cycle count ({self.max_cycles}), stopping")
            return False
            
        return True
    
    def _begin_cycle(self):
        """
        Begin a new cycle, initializing state and resources.
        """
        # Reset temporary state
        self.temp_state = {
            "cycle": self.cycle_count,
            "start_time": self.last_cycle_start,
            "actions": []
        }
        
        # Initialize resources for this cycle
        self._init_cycle_resources()
        
        logger.debug(f"Begin cycle {self.cycle_count}")
    
    def _end_cycle(self):
        """
        End the current cycle, persisting state and releasing resources.
        """
        # Persist state that should survive across cycles
        self._persist_state()
        
        # Release all resources acquired during cycle
        self._release_cycle_resources()
        
        # Validate cycle outcomes
        self._validate_cycle_outcomes()
        
        logger.debug(f"End cycle {self.cycle_count}, duration: {time.time() - self.last_cycle_start:.2f}s")
    
    def _process_operations(self):
        """
        Process the main operations of the cycle, with circuit breaker protection.
        
        This is a template method that should be overridden by subclasses.
        """
        pass
    
    def _init_cycle_resources(self):
        """
        Initialize resources needed for this cycle.
        
        This should be overridden by subclasses.
        """
        pass
    
    def _release_cycle_resources(self):
        """
        Release resources acquired during the cycle.
        
        This should be overridden by subclasses.
        """
        pass
    
    def _persist_state(self):
        """
        Persist state that should survive across cycles.
        
        This should be overridden by subclasses.
        """
        pass
    
    def _validate_cycle_outcomes(self):
        """
        Validate that this cycle produced expected outcomes.
        
        This should be overridden by subclasses.
        """
        # Default implementation checks if any actions were performed
        cycle_actions = self.temp_state.get("actions", [])
        if not cycle_actions:
            logger.warning(f"Cycle {self.cycle_count} completed with no actions")
    
    def _check_for_drift(self):
        """
        Check for behavioral drift by comparing current state to expected patterns.
        """
        # This is a template method that should be overridden by subclasses
        drift_detected = self._detect_behavioral_drift()
        if drift_detected:
            logger.warning(f"Detected drift: {drift_detected}")
            self._correct_drift(drift_detected)
    
    def _detect_behavioral_drift(self) -> Optional[Dict[str, Any]]:
        """
        Detect if the agent is drifting from expected behavior.
        
        This should be overridden by subclasses.
        
        Returns:
            Dict with drift details or None if no drift detected
        """
        return None
    
    def _correct_drift(self, drift: Dict[str, Any]):
        """
        Apply corrections based on detected drift.
        
        This should be overridden by subclasses.
        
        Args:
            drift: Dictionary with drift details
        """
        logger.info(f"No drift correction implemented for {self.name}")
    
    def _recover_from_error(self, error: Exception) -> bool:
        """
        Attempt to recover from an error.
        
        This should be overridden by subclasses.
        
        Args:
            error: The error to recover from
            
        Returns:
            True if recovery was successful, False otherwise
        """
        # Default implementation doesn't recover from any errors
        return False
    
    def _handle_unrecoverable_error(self, error: Exception):
        """
        Handle an unrecoverable error by entering degraded operation mode.
        
        Args:
            error: The unrecoverable error
        """
        logger.error(f"Unrecoverable error in {self.name}: {str(error)}")
        
        with DegradedOperationMode(
            reason=f"Unrecoverable error: {str(error)}",
            available_resources=self.resources
        ) as degraded:
            for action in degraded.get_alternative_actions():
                try:
                    success = action.execute(context={
                        "error": error,
                        "cycle": self.cycle_count,
                        "state": self.state
                    })
                    degraded.record_action_attempt(action, success)
                    if success:
                        logger.info(f"Successfully executed alternative action: {action.name}")
                except Exception as action_error:
                    logger.error(f"Error executing alternative action {action.name}: {str(action_error)}")
                    degraded.record_action_attempt(action, False)
    
    def _handle_watchdog_timeout(self):
        """
        Handle a watchdog timeout by interrupting the current operation.
        """
        logger.error(f"Watchdog timeout in cycle {self.cycle_count}")
        # In a real implementation, this would attempt to interrupt the current operation
        # and possibly enter degraded mode
    
    def _handle_resource_limit(self):
        """
        Handle a resource limit violation.
        """
        logger.error(f"Resource limit exceeded in cycle {self.cycle_count}")
        # In a real implementation, this would attempt to free resources
        # and possibly enter degraded mode
    
    def _report_heartbeat(self, status: str):
        """
        Report a heartbeat to the monitoring system.
        
        Args:
            status: Status to report (healthy, degraded, error)
        """
        # This is a placeholder - in a real implementation, this would
        # send a heartbeat to a monitoring system
        logger.debug(
            f"Heartbeat: {self.name}, cycle={self.cycle_count}, status={status}, "
            f"duration={time.time() - self.last_cycle_start:.2f}s"
        )
    
    def register_action(self, action_name: str):
        """
        Register that an action was performed in this cycle.
        
        Args:
            action_name: Name of the action that was performed
        """
        if "actions" not in self.temp_state:
            self.temp_state["actions"] = []
        self.temp_state["actions"].append({
            "name": action_name,
            "timestamp": time.time()
        })
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the persistent state.
        
        Args:
            key: State key to get
            default: Default value if key doesn't exist
            
        Returns:
            The state value or default
        """
        return self.state.get(key, default)
    
    def set_state(self, key: str, value: Any):
        """
        Set a value in the persistent state.
        
        Args:
            key: State key to set
            value: Value to set
        """
        self.state[key] = value 