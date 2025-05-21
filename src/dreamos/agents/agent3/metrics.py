"""
Metrics collection and reporting for Agent-3.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List
from datetime import datetime

from dreamos.core.coordination.agent_bus import AgentBus, EventType

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and reports metrics for Agent-3."""
    
    def __init__(self, agent_bus: AgentBus, config: Dict[str, Any]):
        """Initialize metrics collector.
        
        Args:
            agent_bus: The agent bus for communication
            config: Metrics configuration
        """
        self.agent_bus = agent_bus
        self.config = config
        self.metrics: Dict[str, Any] = {
            "cycle_count": 0,
            "task_processing_time": [],
            "error_count": 0,
            "heartbeat_latency": []
        }
        self.start_time = time.time()
        self.is_running = False
        
    async def start(self):
        """Start metrics collection."""
        if self.is_running:
            return
            
        self.is_running = True
        asyncio.create_task(self._collect_metrics())
        logger.info("Metrics collector started")
        
    async def stop(self):
        """Stop metrics collection."""
        self.is_running = False
        logger.info("Metrics collector stopped")
        
    async def _collect_metrics(self):
        """Collect metrics at regular intervals."""
        while self.is_running:
            try:
                # Calculate metrics
                uptime = time.time() - self.start_time
                error_rate = self.metrics["error_count"] / max(1, self.metrics["cycle_count"])
                
                # Prepare metrics report
                report = {
                    "timestamp": datetime.now().isoformat(),
                    "uptime": uptime,
                    "cycle_count": self.metrics["cycle_count"],
                    "error_count": self.metrics["error_count"],
                    "error_rate": error_rate,
                    "avg_task_time": self._calculate_avg_task_time(),
                    "avg_heartbeat_latency": self._calculate_avg_heartbeat_latency()
                }
                
                # Publish metrics
                await self.agent_bus.publish("agent3.metrics", report)
                
                # Clear temporary metrics
                self.metrics["task_processing_time"] = []
                self.metrics["heartbeat_latency"] = []
                
                # Wait for next collection interval
                await asyncio.sleep(self.config["collection_interval"])
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                
    def record_cycle(self):
        """Record a completed cycle."""
        self.metrics["cycle_count"] += 1
        
    def record_error(self):
        """Record an error occurrence."""
        self.metrics["error_count"] += 1
        
    def record_task_time(self, processing_time: float):
        """Record task processing time.
        
        Args:
            processing_time: Time taken to process task in seconds
        """
        self.metrics["task_processing_time"].append(processing_time)
        
    def record_heartbeat_latency(self, latency: float):
        """Record heartbeat latency.
        
        Args:
            latency: Time taken to send heartbeat in seconds
        """
        self.metrics["heartbeat_latency"].append(latency)
        
    def _calculate_avg_task_time(self) -> float:
        """Calculate average task processing time."""
        times = self.metrics["task_processing_time"]
        return sum(times) / len(times) if times else 0.0
        
    def _calculate_avg_heartbeat_latency(self) -> float:
        """Calculate average heartbeat latency."""
        latencies = self.metrics["heartbeat_latency"]
        return sum(latencies) / len(latencies) if latencies else 0.0 