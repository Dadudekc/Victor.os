"""
Tenant-Aware Coordinator for Multi-Tenant Agent System
Phase 4: Enterprise Deployment - Integrates multi-tenant architecture with agent coordination
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
import json
import time
from dataclasses import dataclass

from .agent_bus import AgentBus, EventType
from ..enterprise.multi_tenant_manager import MultiTenantManager, TenantInfo, TenantStatus
from ...agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

@dataclass
class TenantAgentContext:
    """Context for agents operating within a tenant"""
    tenant_id: str
    agent_id: str
    tenant_info: TenantInfo
    agent_config: Dict[str, Any]
    resource_limits: Dict[str, Any]
    isolation_path: Path

class TenantAwareCoordinator:
    """Coordinates agents within multi-tenant architecture"""
    
    def __init__(self, multi_tenant_manager: MultiTenantManager, agent_bus: AgentBus):
        self.multi_tenant_manager = multi_tenant_manager
        self.agent_bus = agent_bus
        self.tenant_agents: Dict[str, Dict[str, BaseAgent]] = {}  # tenant_id -> {agent_id -> agent}
        self.agent_tenants: Dict[str, str] = {}  # agent_id -> tenant_id
        self.tenant_contexts: Dict[str, TenantAgentContext] = {}  # agent_id -> context
        
        # Subscribe to agent events
        self._setup_event_subscriptions()
        
    def _setup_event_subscriptions(self):
        """Setup event subscriptions for tenant-aware coordination"""
        asyncio.create_task(self.agent_bus.subscribe(EventType.AGENT_STARTED, self._handle_agent_started))
        asyncio.create_task(self.agent_bus.subscribe(EventType.AGENT_STOPPED, self._handle_agent_stopped))
        asyncio.create_task(self.agent_bus.subscribe(EventType.AGENT_ERROR, self._handle_agent_error))
        asyncio.create_task(self.agent_bus.subscribe(EventType.TASK_CREATED, self._handle_task_created))
        asyncio.create_task(self.agent_bus.subscribe(EventType.TASK_COMPLETED, self._handle_task_completed))
    
    async def register_agent_for_tenant(self, tenant_id: str, agent: BaseAgent, 
                                      agent_config: Dict[str, Any] = None) -> bool:
        """Register an agent for a specific tenant"""
        try:
            # Validate tenant exists and is active
            tenant_info = await self.multi_tenant_manager.get_tenant_info(tenant_id)
            if not tenant_info:
                logger.error(f"Tenant {tenant_id} not found")
                return False
                
            if tenant_info.status != TenantStatus.ACTIVE:
                logger.error(f"Tenant {tenant_id} is not active (status: {tenant_info.status})")
                return False
            
            # Check tenant limits
            limits = await self.multi_tenant_manager.check_tenant_limits(tenant_id)
            max_agents = tenant_info.config.max_agents
            current_agents = len(self.tenant_agents.get(tenant_id, {}))
            if current_agents >= max_agents:
                logger.error(f"Tenant {tenant_id} has reached agent limit ({current_agents}/{max_agents})")
                return False
            if limits.get("agents_at_limit", False):
                logger.error(f"Tenant {tenant_id} has reached agent limit (limits dict)")
                return False
            
            # Create tenant context
            context = TenantAgentContext(
                tenant_id=tenant_id,
                agent_id=agent.agent_id,
                tenant_info=tenant_info,
                agent_config=agent_config or {},
                resource_limits=limits,
                isolation_path=Path(f"tenants/{tenant_id}/agents/{agent.agent_id}")
            )
            
            # Store agent in tenant context
            if tenant_id not in self.tenant_agents:
                self.tenant_agents[tenant_id] = {}
            
            self.tenant_agents[tenant_id][agent.agent_id] = agent
            self.agent_tenants[agent.agent_id] = tenant_id
            self.tenant_contexts[agent.agent_id] = context
            
            # Create isolation directory
            context.isolation_path.mkdir(parents=True, exist_ok=True)
            
            # Update agent configuration for tenant context
            await self._configure_agent_for_tenant(agent, context)
            
            logger.info(f"Agent {agent.agent_id} registered for tenant {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering agent {agent.agent_id} for tenant {tenant_id}: {e}")
            return False
    
    async def _configure_agent_for_tenant(self, agent: BaseAgent, context: TenantAgentContext):
        """Configure agent for tenant-specific operation"""
        # Update agent configuration with tenant context
        tenant_config = context.tenant_info.config
        
        # Set tenant-specific paths
        agent.mailbox_path = str(context.isolation_path / "mailbox")
        agent.episode_path = str(context.isolation_path / "episodes")
        
        # Apply tenant resource limits
        agent.max_concurrent_tasks = tenant_config.max_agents
        agent.max_storage_gb = tenant_config.max_storage_gb
        agent.max_api_requests_per_minute = tenant_config.max_api_requests_per_minute
        
        # Set tenant metadata
        agent.tenant_id = context.tenant_id
        agent.tenant_tier = context.tenant_info.tier.value
        
        # Create tenant-specific directories
        Path(agent.mailbox_path).mkdir(parents=True, exist_ok=True)
        Path(agent.episode_path).mkdir(parents=True, exist_ok=True)
    
    async def unregister_agent_from_tenant(self, tenant_id: str, agent_id: str) -> bool:
        """Unregister an agent from a tenant"""
        try:
            if tenant_id in self.tenant_agents and agent_id in self.tenant_agents[tenant_id]:
                agent = self.tenant_agents[tenant_id][agent_id]
                
                # Clean up agent resources
                await self._cleanup_agent_resources(agent_id)
                
                # Remove from tracking
                del self.tenant_agents[tenant_id][agent_id]
                if agent_id in self.agent_tenants:
                    del self.agent_tenants[agent_id]
                if agent_id in self.tenant_contexts:
                    del self.tenant_contexts[agent_id]
                
                logger.info(f"Agent {agent_id} unregistered from tenant {tenant_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error unregistering agent {agent_id} from tenant {tenant_id}: {e}")
            return False
    
    async def _cleanup_agent_resources(self, agent_id: str):
        """Clean up resources for an agent"""
        if agent_id in self.tenant_contexts:
            context = self.tenant_contexts[agent_id]
            # Clean up temporary files, etc.
            pass
    
    async def get_tenant_agents(self, tenant_id: str) -> List[BaseAgent]:
        """Get all agents for a specific tenant"""
        return list(self.tenant_agents.get(tenant_id, {}).values())
    
    async def get_agent_tenant(self, agent_id: str) -> Optional[str]:
        """Get the tenant ID for a specific agent"""
        return self.agent_tenants.get(agent_id)
    
    async def get_agent_context(self, agent_id: str) -> Optional[TenantAgentContext]:
        """Get the tenant context for a specific agent"""
        return self.tenant_contexts.get(agent_id)
    
    async def check_agent_tenant_limits(self, agent_id: str) -> Dict[str, Any]:
        """Check if an agent is within its tenant limits"""
        tenant_id = await self.get_agent_tenant(agent_id)
        if not tenant_id:
            return {"error": "Agent not associated with any tenant"}
        
        return await self.multi_tenant_manager.check_tenant_limits(tenant_id)
    
    async def record_agent_usage(self, agent_id: str, usage_data: Dict[str, Any]):
        """Record usage data for an agent's tenant"""
        tenant_id = await self.get_agent_tenant(agent_id)
        if tenant_id:
            await self.multi_tenant_manager.record_tenant_usage(tenant_id, usage_data)
    
    # Event handlers for tenant-aware coordination
    async def _handle_agent_started(self, event_type: str, data: Dict[str, Any]):
        """Handle agent started event"""
        agent_id = data.get("agent_id")
        if agent_id and agent_id in self.agent_tenants:
            tenant_id = self.agent_tenants[agent_id]
            await self.record_agent_usage(agent_id, {
                "event": "agent_started",
                "timestamp": time.time(),
                "agents_active": 1
            })
    
    async def _handle_agent_stopped(self, event_type: str, data: Dict[str, Any]):
        """Handle agent stopped event"""
        agent_id = data.get("agent_id")
        if agent_id and agent_id in self.agent_tenants:
            tenant_id = self.agent_tenants[agent_id]
            await self.record_agent_usage(agent_id, {
                "event": "agent_stopped",
                "timestamp": time.time(),
                "agents_active": -1
            })
    
    async def _handle_agent_error(self, event_type: str, data: Dict[str, Any]):
        """Handle agent error event"""
        agent_id = data.get("agent_id")
        if agent_id and agent_id in self.agent_tenants:
            tenant_id = self.agent_tenants[agent_id]
            await self.record_agent_usage(agent_id, {
                "event": "agent_error",
                "timestamp": time.time(),
                "error_count": 1
            })
    
    async def _handle_task_created(self, event_type: str, data: Dict[str, Any]):
        """Handle task created event"""
        agent_id = data.get("agent_id")
        if agent_id and agent_id in self.agent_tenants:
            tenant_id = self.agent_tenants[agent_id]
            await self.record_agent_usage(agent_id, {
                "event": "task_created",
                "timestamp": time.time(),
                "tasks_created": 1
            })
    
    async def _handle_task_completed(self, event_type: str, data: Dict[str, Any]):
        """Handle task completed event"""
        agent_id = data.get("agent_id")
        if agent_id and agent_id in self.agent_tenants:
            tenant_id = self.agent_tenants[agent_id]
            await self.record_agent_usage(agent_id, {
                "event": "task_completed",
                "timestamp": time.time(),
                "tasks_completed": 1
            })
    
    async def get_tenant_coordination_status(self, tenant_id: str) -> Dict[str, Any]:
        """Get coordination status for a specific tenant"""
        tenant_info = await self.multi_tenant_manager.get_tenant_info(tenant_id)
        if not tenant_info:
            return {"error": "Tenant not found"}
        
        agents = await self.get_tenant_agents(tenant_id)
        limits = await self.multi_tenant_manager.check_tenant_limits(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant_info.name,
            "tenant_status": tenant_info.status.value,
            "tenant_tier": tenant_info.tier.value,
            "active_agents": len(agents),
            "max_agents": tenant_info.config.max_agents,
            "resource_limits": limits,
            "agents": [
                {
                    "agent_id": agent.agent_id,
                    "status": agent.status,
                    "current_task": agent.current_task
                }
                for agent in agents
            ]
        }
    
    async def get_system_coordination_status(self) -> Dict[str, Any]:
        """Get overall system coordination status"""
        system_status = await self.multi_tenant_manager.get_system_status()
        
        return {
            "total_tenants": system_status["total_tenants"],
            "active_tenants": system_status["active_tenants"],
            "total_agents": len(self.agent_tenants),
            "tenant_agents": {
                tenant_id: len(agents) 
                for tenant_id, agents in self.tenant_agents.items()
            },
            "system_metrics": system_status
        } 