"""
Agent-3: Autonomous Loop Engineer
Responsible for maintaining continuous operation and implementing autonomous protocols.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import time

from dreamos.core.coordination.agent_bus import AgentBus, EventType, BaseEvent
from .recovery import RecoveryHandler
from .metrics import MetricsCollector
from .checkpoint import CheckpointVerifier

logger = logging.getLogger(__name__)

class Agent3:
    """Agent-3: Autonomous Loop Engineer implementation."""
    
    def __init__(self, agent_bus: AgentBus, config: Dict[str, Any]):
        """Initialize Agent-3.
        
        Args:
            agent_bus: The agent bus for communication
            config: Agent configuration
        """
        self.agent_bus = agent_bus
        self.config = config
        self.agent_id = "agent3"
        self.cycle_count = 0
        self.last_heartbeat = datetime.now()
        self.is_running = False
        self.current_task: Optional[Dict[str, Any]] = None
        self.recovery_handler = RecoveryHandler(agent_bus, config.get("recovery", {}))
        self.metrics_collector = MetricsCollector(agent_bus, config.get("metrics", {}))
        self.checkpoint_verifier = CheckpointVerifier(agent_bus, config.get("checkpoint", {}))
        self.min_cycles_before_pause = 25
        self.continuous_mode = True
        self.consecutive_checkpoint_failures = 0
        
    async def start(self):
        """Start Agent-3's autonomous operation."""
        if self.is_running:
            return
            
        self.is_running = True
        await self.agent_bus.publish(EventType.AGENT_STARTED.value, {
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Start metrics collection
        await self.metrics_collector.start()
        
        # Start checkpoint verification
        await self.checkpoint_verifier.start()
        
        # Subscribe to relevant events
        await self.agent_bus.subscribe(EventType.TASK_CREATED.value, self._handle_task_created)
        await self.agent_bus.subscribe(EventType.TASK_UPDATED.value, self._handle_task_updated)
        await self.agent_bus.subscribe(EventType.AGENT_ERROR.value, self._handle_agent_error)
        await self.agent_bus.subscribe("agent3.checkpoint", self._handle_checkpoint_status)
        
        # Start autonomous operation loop
        asyncio.create_task(self._autonomous_loop())
        logger.info("Agent-3 started in continuous mode")
        
    async def stop(self):
        """Stop Agent-3's operation."""
        if not self.is_running:
            return
            
        self.is_running = False
        await self.metrics_collector.stop()
        await self.checkpoint_verifier.stop()
        await self.agent_bus.publish(EventType.AGENT_STOPPED.value, {
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat(),
            "total_cycles": self.cycle_count
        })
        logger.info("Agent-3 stopped")
        
    async def _autonomous_loop(self):
        """Main autonomous operation loop."""
        while self.is_running:
            try:
                start_time = time.time()
                
                # Send heartbeat
                await self._send_heartbeat()
                
                # Process current task if any
                if self.current_task:
                    await self._process_task()
                    
                # Increment cycle count
                self.cycle_count += 1
                self.metrics_collector.record_cycle()
                
                # Record metrics
                processing_time = time.time() - start_time
                self.metrics_collector.record_task_time(processing_time)
                
                # Check if we should pause (only if not in continuous mode)
                if not self.continuous_mode and self.cycle_count >= self.min_cycles_before_pause:
                    logger.info(f"Completed {self.cycle_count} cycles, pausing as per protocol")
                    await asyncio.sleep(self.config.get("pause_duration", 60))
                    self.cycle_count = 0
                
                # Sleep to maintain cycle rate
                await asyncio.sleep(self.config.get("cycle_interval", 1))
                
            except Exception as e:
                logger.error(f"Error in autonomous loop: {e}")
                self.metrics_collector.record_error()
                await self._handle_error(e)
                
    async def _send_heartbeat(self):
        """Send heartbeat to indicate agent is alive."""
        start_time = time.time()
        self.last_heartbeat = datetime.now()
        await self.agent_bus.publish(EventType.AGENT_HEARTBEAT.value, {
            "agent_id": self.agent_id,
            "timestamp": self.last_heartbeat.isoformat(),
            "cycle_count": self.cycle_count,
            "continuous_mode": self.continuous_mode
        })
        latency = time.time() - start_time
        self.metrics_collector.record_heartbeat_latency(latency)
        
    async def _handle_task_created(self, event_type: str, data: Dict[str, Any]):
        """Handle new task creation."""
        if not self.current_task:
            self.current_task = data
            logger.info(f"Agent-3 received new task: {data}")
            
    async def _handle_task_updated(self, event_type: str, data: Dict[str, Any]):
        """Handle task updates."""
        if self.current_task and data.get("task_id") == self.current_task.get("task_id"):
            self.current_task.update(data)
            logger.info(f"Agent-3 received task update: {data}")
            
    async def _handle_agent_error(self, event_type: str, data: Dict[str, Any]):
        """Handle errors from other agents."""
        if data.get("fatal", False):
            logger.warning(f"Received fatal error from another agent: {data}")
            # Implement emergency procedures if needed
            
    async def _handle_checkpoint_status(self, event_type: str, data: Dict[str, Any]):
        """Handle checkpoint verification status."""
        checkpoint_id = data["checkpoint_id"]
        status = data["status"]
        
        if not status:
            self.consecutive_checkpoint_failures += 1
            logger.warning(f"Checkpoint {checkpoint_id} failed verification")
            
            # Check if we've exceeded the maximum consecutive failures
            max_failures = self.config.get("emergency", {}).get("max_consecutive_checkpoint_failures", 3)
            if self.consecutive_checkpoint_failures >= max_failures:
                logger.error(f"Exceeded maximum consecutive checkpoint failures ({max_failures})")
                await self._handle_checkpoint_emergency()
        else:
            self.consecutive_checkpoint_failures = 0
            logger.debug(f"Checkpoint {checkpoint_id} passed verification")
            
    async def _handle_checkpoint_emergency(self):
        """Handle checkpoint verification emergency."""
        emergency_config = self.config.get("emergency", {})
        
        if emergency_config.get("auto_shutdown", False):
            logger.error("Initiating emergency shutdown due to checkpoint failures")
            await self.stop()
        else:
            logger.warning("Checkpoint failures detected but auto-shutdown disabled")
            # Implement other emergency procedures if needed
            
    async def _process_task(self):
        """Process the current task."""
        if not self.current_task:
            return
            
        try:
            # Implement task processing logic here
            # This is where Agent-3's specific responsibilities would be handled
            
            # For now, just log the processing
            logger.info(f"Agent-3 processing task: {self.current_task}")
            
            # Mark task as completed
            await self.agent_bus.publish(EventType.TASK_COMPLETED.value, {
                "task_id": self.current_task.get("task_id"),
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            })
            self.current_task = None
            
        except Exception as e:
            logger.error(f"Error processing task: {e}")
            self.metrics_collector.record_error()
            await self._handle_error(e)
            
    async def _handle_error(self, error: Exception):
        """Handle errors during operation."""
        context = {
            "agent_id": self.agent_id,
            "cycle_count": self.cycle_count,
            "timestamp": datetime.now().isoformat()
        }
        
        # Attempt recovery
        success = await self.recovery_handler.handle_error(error, context)
        
        if not success:
            await self.agent_bus.publish(EventType.AGENT_ERROR.value, {
                "agent_id": self.agent_id,
                "error": str(error),
                "fatal": True,
                "timestamp": datetime.now().isoformat()
            }) 