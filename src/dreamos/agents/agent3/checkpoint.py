"""
Checkpoint verification tool for Agent-3.
Validates agent operation against protocol requirements.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from dreamos.core.coordination.agent_bus import AgentBus, EventType

logger = logging.getLogger(__name__)

class CheckpointVerifier:
    """Verifies Agent-3's operation against protocol checkpoints."""
    
    def __init__(self, agent_bus: AgentBus, config: Dict[str, Any]):
        """Initialize checkpoint verifier.
        
        Args:
            agent_bus: The agent bus for communication
            config: Verification configuration
        """
        self.agent_bus = agent_bus
        self.config = config
        self.checkpoints: Dict[str, Dict[str, Any]] = {
            "continuous_operation": {
                "required": True,
                "status": False,
                "last_verified": None,
                "verification_interval": 300  # 5 minutes
            },
            "cycle_completion": {
                "required": True,
                "status": False,
                "min_cycles": 25,
                "last_verified": None,
                "verification_interval": 60  # 1 minute
            },
            "error_rate": {
                "required": True,
                "status": False,
                "max_rate": 0.1,  # 10%
                "last_verified": None,
                "verification_interval": 300  # 5 minutes
            },
            "heartbeat_health": {
                "required": True,
                "status": False,
                "max_latency": 1.0,  # seconds
                "last_verified": None,
                "verification_interval": 60  # 1 minute
            },
            "task_completion": {
                "required": True,
                "status": False,
                "last_verified": None,
                "verification_interval": 300  # 5 minutes
            }
        }
        self.metrics_history: Dict[str, List[Any]] = {
            "cycles": [],
            "errors": [],
            "heartbeats": [],
            "tasks": []
        }
        self.is_running = False
        
    async def start(self):
        """Start checkpoint verification."""
        if self.is_running:
            return
            
        self.is_running = True
        await self.agent_bus.subscribe(EventType.AGENT_HEARTBEAT.value, self._handle_heartbeat)
        await self.agent_bus.subscribe(EventType.AGENT_ERROR.value, self._handle_error)
        await self.agent_bus.subscribe(EventType.TASK_COMPLETED.value, self._handle_task_completed)
        
        # Start verification loop
        asyncio.create_task(self._verification_loop())
        logger.info("Checkpoint verifier started")
        
    async def stop(self):
        """Stop checkpoint verification."""
        self.is_running = False
        logger.info("Checkpoint verifier stopped")
        
    async def _verification_loop(self):
        """Main verification loop."""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Verify each checkpoint
                for checkpoint_id, checkpoint in self.checkpoints.items():
                    if self._should_verify_checkpoint(checkpoint, current_time):
                        await self._verify_checkpoint(checkpoint_id, checkpoint)
                        checkpoint["last_verified"] = current_time
                
                # Clean up old metrics
                self._cleanup_old_metrics()
                
                # Sleep until next verification cycle
                await asyncio.sleep(self.config.get("verification_interval", 60))
                
            except Exception as e:
                logger.error(f"Error in verification loop: {e}")
                
    def _should_verify_checkpoint(self, checkpoint: Dict[str, Any], current_time: datetime) -> bool:
        """Check if a checkpoint should be verified.
        
        Args:
            checkpoint: Checkpoint configuration
            current_time: Current time
            
        Returns:
            bool: True if checkpoint should be verified
        """
        if not checkpoint["last_verified"]:
            return True
            
        time_since_last = (current_time - checkpoint["last_verified"]).total_seconds()
        return time_since_last >= checkpoint["verification_interval"]
        
    async def _verify_checkpoint(self, checkpoint_id: str, checkpoint: Dict[str, Any]):
        """Verify a specific checkpoint.
        
        Args:
            checkpoint_id: ID of the checkpoint
            checkpoint: Checkpoint configuration
        """
        try:
            if checkpoint_id == "continuous_operation":
                await self._verify_continuous_operation(checkpoint)
            elif checkpoint_id == "cycle_completion":
                await self._verify_cycle_completion(checkpoint)
            elif checkpoint_id == "error_rate":
                await self._verify_error_rate(checkpoint)
            elif checkpoint_id == "heartbeat_health":
                await self._verify_heartbeat_health(checkpoint)
            elif checkpoint_id == "task_completion":
                await self._verify_task_completion(checkpoint)
                
            # Report checkpoint status
            await self._report_checkpoint_status(checkpoint_id, checkpoint)
            
        except Exception as e:
            logger.error(f"Error verifying checkpoint {checkpoint_id}: {e}")
            checkpoint["status"] = False
            
    async def _verify_continuous_operation(self, checkpoint: Dict[str, Any]):
        """Verify continuous operation."""
        # Check if agent has been running without interruption
        if not self.metrics_history["heartbeats"]:
            checkpoint["status"] = False
            return
            
        last_heartbeat = self.metrics_history["heartbeats"][-1]
        time_since_heartbeat = (datetime.now() - last_heartbeat["timestamp"]).total_seconds()
        
        checkpoint["status"] = time_since_heartbeat <= self.config.get("max_heartbeat_interval", 10)
        
    async def _verify_cycle_completion(self, checkpoint: Dict[str, Any]):
        """Verify cycle completion."""
        if not self.metrics_history["cycles"]:
            checkpoint["status"] = False
            return
            
        recent_cycles = [
            cycle for cycle in self.metrics_history["cycles"]
            if (datetime.now() - cycle["timestamp"]).total_seconds() <= 300  # Last 5 minutes
        ]
        
        checkpoint["status"] = len(recent_cycles) >= checkpoint["min_cycles"]
        
    async def _verify_error_rate(self, checkpoint: Dict[str, Any]):
        """Verify error rate."""
        if not self.metrics_history["errors"]:
            checkpoint["status"] = True
            return
            
        recent_errors = [
            error for error in self.metrics_history["errors"]
            if (datetime.now() - error["timestamp"]).total_seconds() <= 300  # Last 5 minutes
        ]
        
        error_rate = len(recent_errors) / max(1, len(self.metrics_history["cycles"]))
        checkpoint["status"] = error_rate <= checkpoint["max_rate"]
        
    async def _verify_heartbeat_health(self, checkpoint: Dict[str, Any]):
        """Verify heartbeat health."""
        if not self.metrics_history["heartbeats"]:
            checkpoint["status"] = False
            return
            
        recent_heartbeats = [
            hb for hb in self.metrics_history["heartbeats"]
            if (datetime.now() - hb["timestamp"]).total_seconds() <= 60  # Last minute
        ]
        
        if not recent_heartbeats:
            checkpoint["status"] = False
            return
            
        avg_latency = sum(hb["latency"] for hb in recent_heartbeats) / len(recent_heartbeats)
        checkpoint["status"] = avg_latency <= checkpoint["max_latency"]
        
    async def _verify_task_completion(self, checkpoint: Dict[str, Any]):
        """Verify task completion."""
        if not self.metrics_history["tasks"]:
            checkpoint["status"] = True
            return
            
        recent_tasks = [
            task for task in self.metrics_history["tasks"]
            if (datetime.now() - task["timestamp"]).total_seconds() <= 300  # Last 5 minutes
        ]
        
        checkpoint["status"] = all(task["status"] == "completed" for task in recent_tasks)
        
    async def _report_checkpoint_status(self, checkpoint_id: str, checkpoint: Dict[str, Any]):
        """Report checkpoint status.
        
        Args:
            checkpoint_id: ID of the checkpoint
            checkpoint: Checkpoint configuration
        """
        await self.agent_bus.publish("agent3.checkpoint", {
            "checkpoint_id": checkpoint_id,
            "status": checkpoint["status"],
            "timestamp": datetime.now().isoformat(),
            "details": {
                "required": checkpoint["required"],
                "last_verified": checkpoint["last_verified"].isoformat() if checkpoint["last_verified"] else None
            }
        })
        
    def _cleanup_old_metrics(self):
        """Clean up old metrics data."""
        retention_period = self.config.get("metrics_retention_period", 3600)  # 1 hour
        cutoff_time = datetime.now() - timedelta(seconds=retention_period)
        
        for metric_type in self.metrics_history:
            self.metrics_history[metric_type] = [
                metric for metric in self.metrics_history[metric_type]
                if metric["timestamp"] > cutoff_time
            ]
            
    async def _handle_heartbeat(self, event_type: str, data: Dict[str, Any]):
        """Handle heartbeat events."""
        self.metrics_history["heartbeats"].append({
            "timestamp": datetime.fromisoformat(data["timestamp"]),
            "latency": data.get("latency", 0.0)
        })
        
    async def _handle_error(self, event_type: str, data: Dict[str, Any]):
        """Handle error events."""
        self.metrics_history["errors"].append({
            "timestamp": datetime.fromisoformat(data["timestamp"]),
            "error": data["error"]
        })
        
    async def _handle_task_completed(self, event_type: str, data: Dict[str, Any]):
        """Handle task completion events."""
        self.metrics_history["tasks"].append({
            "timestamp": datetime.fromisoformat(data["timestamp"]),
            "task_id": data["task_id"],
            "status": "completed"
        }) 