"""
Victor.os Distributed Agent Management System
Phase 3: Scalability - Distributed deployment and load balancing
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import aiohttp
import structlog
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
logger = structlog.get_logger("distributed_manager")

class NodeStatus(Enum):
    """Node status enumeration"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"

class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    IP_HASH = "ip_hash"
    LEAST_RESPONSE_TIME = "least_response_time"

@dataclass
class NodeInfo:
    """Node information for distributed deployment"""
    node_id: str
    host: str
    port: int
    status: NodeStatus
    capacity: int  # Max agents
    current_load: int  # Current agents
    cpu_usage: float
    memory_usage: float
    last_heartbeat: float
    metadata: Dict[str, Any]

@dataclass
class AgentDeployment:
    """Agent deployment information"""
    agent_id: str
    node_id: str
    deployment_time: float
    status: str
    resource_usage: Dict[str, float]
    health_score: float

class DistributedManager:
    """Distributed agent deployment and management system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.nodes: Dict[str, NodeInfo] = {}
        self.agent_deployments: Dict[str, AgentDeployment] = {}
        self.load_balancer = LoadBalancer(self.config.get("load_balancing_strategy", LoadBalancingStrategy.ROUND_ROBIN))
        self.health_monitor = HealthMonitor()
        self.scaling_manager = ScalingManager(self.config)
        
        # Setup monitoring
        self._setup_monitoring()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for distributed manager"""
        return {
            "load_balancing_strategy": LoadBalancingStrategy.LEAST_CONNECTIONS,
            "health_check_interval": 30,  # seconds
            "node_timeout": 60,  # seconds
            "auto_scaling": True,
            "max_nodes": 10,
            "min_nodes": 1,
            "scaling_threshold": 0.8,  # 80% capacity triggers scaling
            "deployment_timeout": 300,  # seconds
            "failover_enabled": True,
            "data_replication": True,
        }
    
    def _setup_monitoring(self):
        """Setup monitoring and logging"""
        self.metrics = {
            "total_nodes": 0,
            "active_nodes": 0,
            "total_agents": 0,
            "deployment_success_rate": 0.0,
            "average_response_time": 0.0,
            "system_uptime": 0.0,
        }
    
    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._metrics_collection_loop())
        asyncio.create_task(self._auto_scaling_loop())
    
    async def register_node(self, node_info: NodeInfo) -> bool:
        """Register a new node in the distributed system"""
        try:
            # Validate node information
            if not self._validate_node_info(node_info):
                logger.error("Invalid node information", node_id=node_info.node_id)
                return False
            
            # Check if node already exists
            if node_info.node_id in self.nodes:
                logger.warning("Node already registered", node_id=node_info.node_id)
                return False
            
            # Add node to system
            self.nodes[node_info.node_id] = node_info
            self.metrics["total_nodes"] = len(self.nodes)
            self.metrics["active_nodes"] = len([n for n in self.nodes.values() if n.status == NodeStatus.ONLINE])
            
            logger.info("Node registered successfully", 
                       node_id=node_info.node_id, 
                       host=node_info.host, 
                       port=node_info.port)
            
            # Update load balancer
            self.load_balancer.add_node(node_info)
            
            return True
            
        except Exception as e:
            logger.error("Failed to register node", 
                        node_id=node_info.node_id, 
                        error=str(e))
            return False
    
    def _validate_node_info(self, node_info: NodeInfo) -> bool:
        """Validate node information"""
        required_fields = ["node_id", "host", "port", "capacity"]
        for field in required_fields:
            if not hasattr(node_info, field) or getattr(node_info, field) is None:
                return False
        
        # Validate capacity
        if node_info.capacity <= 0:
            return False
        
        # Validate port range
        if not (1024 <= node_info.port <= 65535):
            return False
        
        return True
    
    async def deploy_agent(self, agent_config: Dict[str, Any]) -> Optional[str]:
        """Deploy an agent to the best available node"""
        try:
            # Select best node using load balancer
            selected_node = self.load_balancer.select_node(self.nodes)
            
            if not selected_node:
                logger.error("No available nodes for agent deployment")
                return None
            
            # Create agent deployment
            agent_id = str(uuid.uuid4())
            deployment = AgentDeployment(
                agent_id=agent_id,
                node_id=selected_node.node_id,
                deployment_time=time.time(),
                status="deploying",
                resource_usage={},
                health_score=1.0
            )
            
            # Deploy agent to node
            success = await self._deploy_to_node(selected_node, agent_config, agent_id)
            
            if success:
                # Update node load
                selected_node.current_load += 1
                
                # Store deployment information
                self.agent_deployments[agent_id] = deployment
                self.metrics["total_agents"] = len(self.agent_deployments)
                
                logger.info("Agent deployed successfully", 
                           agent_id=agent_id, 
                           node_id=selected_node.node_id)
                
                return agent_id
            else:
                logger.error("Failed to deploy agent", 
                           agent_id=agent_id, 
                           node_id=selected_node.node_id)
                return None
                
        except Exception as e:
            logger.error("Agent deployment failed", error=str(e))
            return None
    
    async def _deploy_to_node(self, node: NodeInfo, agent_config: Dict[str, Any], agent_id: str) -> bool:
        """Deploy agent to specific node"""
        try:
            # Simulate deployment to node
            # In real implementation, this would make HTTP request to node
            deployment_url = f"http://{node.host}:{node.port}/deploy"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(deployment_url, json={
                    "agent_id": agent_id,
                    "config": agent_config
                }) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.error("Node deployment failed", 
                                   node_id=node.node_id, 
                                   status=response.status)
                        return False
                        
        except Exception as e:
            logger.error("Deployment request failed", 
                        node_id=node.node_id, 
                        error=str(e))
            return False
    
    async def remove_agent(self, agent_id: str) -> bool:
        """Remove agent from distributed system"""
        try:
            if agent_id not in self.agent_deployments:
                logger.warning("Agent not found", agent_id=agent_id)
                return False
            
            deployment = self.agent_deployments[agent_id]
            node = self.nodes.get(deployment.node_id)
            
            if node:
                # Remove agent from node
                success = await self._remove_from_node(node, agent_id)
                
                if success:
                    # Update node load
                    node.current_load = max(0, node.current_load - 1)
                    
                    # Remove deployment record
                    del self.agent_deployments[agent_id]
                    self.metrics["total_agents"] = len(self.agent_deployments)
                    
                    logger.info("Agent removed successfully", agent_id=agent_id)
                    return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to remove agent", 
                        agent_id=agent_id, 
                        error=str(e))
            return False
    
    async def _remove_from_node(self, node: NodeInfo, agent_id: str) -> bool:
        """Remove agent from specific node"""
        try:
            # Simulate removal from node
            removal_url = f"http://{node.host}:{node.port}/remove/{agent_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.delete(removal_url) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error("Node removal failed", 
                        node_id=node.node_id, 
                        error=str(e))
            return False
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "nodes": {
                node_id: asdict(node) for node_id, node in self.nodes.items()
            },
            "deployments": {
                agent_id: asdict(deployment) for agent_id, deployment in self.agent_deployments.items()
            },
            "metrics": self.metrics,
            "load_balancer": self.load_balancer.get_status(),
            "health": self.health_monitor.get_health_summary(),
            "scaling": self.scaling_manager.get_scaling_status(),
        }
    
    async def _health_check_loop(self):
        """Background health check loop"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.config["health_check_interval"])
            except Exception as e:
                logger.error("Health check loop error", error=str(e))
                await asyncio.sleep(10)
    
    async def _perform_health_checks(self):
        """Perform health checks on all nodes"""
        current_time = time.time()
        
        for node_id, node in self.nodes.items():
            try:
                # Check if node is responsive
                is_healthy = await self._check_node_health(node)
                
                if not is_healthy:
                    # Mark node as degraded or offline
                    if current_time - node.last_heartbeat > self.config["node_timeout"]:
                        node.status = NodeStatus.OFFLINE
                        logger.warning("Node marked as offline", node_id=node_id)
                    else:
                        node.status = NodeStatus.DEGRADED
                        logger.warning("Node marked as degraded", node_id=node_id)
                else:
                    node.status = NodeStatus.ONLINE
                    node.last_heartbeat = current_time
                
                # Update metrics
                self.metrics["active_nodes"] = len([n for n in self.nodes.values() if n.status == NodeStatus.ONLINE])
                
            except Exception as e:
                logger.error("Health check failed", node_id=node_id, error=str(e))
    
    async def _check_node_health(self, node: NodeInfo) -> bool:
        """Check health of specific node"""
        try:
            health_url = f"http://{node.host}:{node.port}/health"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=5) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        # Update node metrics
                        node.cpu_usage = health_data.get("cpu_usage", 0.0)
                        node.memory_usage = health_data.get("memory_usage", 0.0)
                        return True
                    else:
                        return False
                        
        except Exception as e:
            logger.debug("Node health check failed", 
                        node_id=node.node_id, 
                        error=str(e))
            return False
    
    async def _metrics_collection_loop(self):
        """Background metrics collection loop"""
        while True:
            try:
                await self._collect_metrics()
                await asyncio.sleep(60)  # Collect metrics every minute
            except Exception as e:
                logger.error("Metrics collection error", error=str(e))
                await asyncio.sleep(10)
    
    async def _collect_metrics(self):
        """Collect system metrics"""
        # Calculate deployment success rate
        total_deployments = len(self.agent_deployments)
        successful_deployments = len([d for d in self.agent_deployments.values() if d.status == "active"])
        
        if total_deployments > 0:
            self.metrics["deployment_success_rate"] = successful_deployments / total_deployments
        
        # Calculate average response time (simplified)
        response_times = []
        for node in self.nodes.values():
            if node.status == NodeStatus.ONLINE:
                response_times.append(0.1)  # Simplified
        
        if response_times:
            self.metrics["average_response_time"] = sum(response_times) / len(response_times)
    
    async def _auto_scaling_loop(self):
        """Background auto-scaling loop"""
        if not self.config["auto_scaling"]:
            return
        
        while True:
            try:
                await self.scaling_manager.evaluate_scaling_needs(self.nodes, self.agent_deployments)
                await asyncio.sleep(300)  # Check scaling every 5 minutes
            except Exception as e:
                logger.error("Auto-scaling error", error=str(e))
                await asyncio.sleep(60)

class LoadBalancer:
    """Load balancer for distributed agent deployment"""
    
    def __init__(self, strategy: LoadBalancingStrategy):
        self.strategy = strategy
        self.current_index = 0
        self.node_weights = {}
    
    def add_node(self, node: NodeInfo):
        """Add node to load balancer"""
        self.node_weights[node.node_id] = 1.0  # Default weight
    
    def select_node(self, nodes: Dict[str, NodeInfo]) -> Optional[NodeInfo]:
        """Select best node based on load balancing strategy"""
        available_nodes = [n for n in nodes.values() if n.status == NodeStatus.ONLINE]
        
        if not available_nodes:
            return None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(available_nodes)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(available_nodes)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_select(available_nodes)
        elif self.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            return self._least_response_time_select(available_nodes)
        else:
            return self._round_robin_select(available_nodes)
    
    def _round_robin_select(self, nodes: List[NodeInfo]) -> NodeInfo:
        """Round-robin node selection"""
        if not nodes:
            return None
        
        selected = nodes[self.current_index % len(nodes)]
        self.current_index += 1
        return selected
    
    def _least_connections_select(self, nodes: List[NodeInfo]) -> NodeInfo:
        """Least connections node selection"""
        return min(nodes, key=lambda n: n.current_load)
    
    def _weighted_round_robin_select(self, nodes: List[NodeInfo]) -> NodeInfo:
        """Weighted round-robin node selection"""
        # Simplified implementation
        return self._round_robin_select(nodes)
    
    def _least_response_time_select(self, nodes: List[NodeInfo]) -> NodeInfo:
        """Least response time node selection"""
        # Simplified implementation - use CPU usage as proxy
        return min(nodes, key=lambda n: n.cpu_usage)
    
    def get_status(self) -> Dict[str, Any]:
        """Get load balancer status"""
        return {
            "strategy": self.strategy.value,
            "current_index": self.current_index,
            "node_weights": self.node_weights,
        }

class HealthMonitor:
    """Health monitoring system"""
    
    def __init__(self):
        self.health_history = []
        self.alert_thresholds = {
            "cpu_usage": 0.9,
            "memory_usage": 0.9,
            "node_failure_rate": 0.2,
        }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health monitoring summary"""
        return {
            "overall_health": "good",
            "alerts": [],
            "history": self.health_history[-10:],  # Last 10 entries
        }

class ScalingManager:
    """Auto-scaling manager"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.scaling_history = []
    
    async def evaluate_scaling_needs(self, nodes: Dict[str, NodeInfo], deployments: Dict[str, AgentDeployment]):
        """Evaluate if scaling is needed"""
        # Simplified scaling logic
        total_capacity = sum(n.capacity for n in nodes.values() if n.status == NodeStatus.ONLINE)
        total_load = len(deployments)
        
        if total_capacity > 0:
            utilization = total_load / total_capacity
            
            if utilization > self.config["scaling_threshold"]:
                logger.info("Scaling threshold exceeded", 
                           utilization=utilization, 
                           threshold=self.config["scaling_threshold"])
                # In real implementation, this would trigger node addition
    
    def get_scaling_status(self) -> Dict[str, Any]:
        """Get scaling manager status"""
        return {
            "auto_scaling_enabled": self.config["auto_scaling"],
            "scaling_threshold": self.config["scaling_threshold"],
            "history": self.scaling_history[-5:],  # Last 5 scaling events
        } 