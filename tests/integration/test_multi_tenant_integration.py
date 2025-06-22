"""
Integration tests for multi-tenant architecture
Phase 4: Enterprise Deployment - Testing multi-tenant integration
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from src.dreamos.core.enterprise.multi_tenant_manager import (
    MultiTenantManager, TenantTier, TenantStatus, BillingCycle
)
from src.dreamos.core.coordination.agent_bus import AgentBus
from src.dreamos.core.coordination.tenant_aware_coordinator import TenantAwareCoordinator
from src.dreamos.agents.base_agent import BaseAgent

class TestMultiTenantIntegration:
    """Test multi-tenant architecture integration"""
    
    @pytest_asyncio.fixture
    async def setup_multi_tenant_system(self):
        """Setup multi-tenant system for testing"""
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        
        # Create tenant directory
        tenant_dir = temp_path / "tenants"
        tenant_dir.mkdir(exist_ok=True)
        
        # Initialize multi-tenant manager
        config = {
            "max_tenants": 10,
            "default_tier": TenantTier.STARTER,
            "isolation_enabled": True,
            "usage_tracking_interval": 60,
            "billing_cycle": BillingCycle.MONTHLY,
            "auto_suspension": False,
            "monitoring_enabled": True,
            "compliance_mode": False,
            "audit_logging": True,
        }
        
        multi_tenant_manager = MultiTenantManager(config)
        agent_bus = AgentBus()
        coordinator = TenantAwareCoordinator(multi_tenant_manager, agent_bus)
        
        # Start agent bus
        await agent_bus.start()
        
        yield {
            "multi_tenant_manager": multi_tenant_manager,
            "agent_bus": agent_bus,
            "coordinator": coordinator,
            "temp_dir": temp_dir,
            "temp_path": temp_path
        }
        
        # Cleanup
        await agent_bus.stop()
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_tenant_creation_and_agent_registration(self, setup_multi_tenant_system):
        """Test creating a tenant and registering agents"""
        system = setup_multi_tenant_system
        multi_tenant_manager = system["multi_tenant_manager"]
        coordinator = system["coordinator"]
        
        # Create a tenant
        tenant_id = await multi_tenant_manager.create_tenant(
            name="Test Company",
            domain="test.company.com",
            tier=TenantTier.PROFESSIONAL,
            admin_email="admin@test.company.com"
        )
        
        assert tenant_id is not None
        
        # Activate the tenant
        success = await multi_tenant_manager.activate_tenant(tenant_id)
        assert success is True
        
        # Create a test agent
        agent_config = {
            "agent_id": "test_agent_1",
            "mailbox_path": str(system["temp_path"] / "mailbox"),
            "episode_path": str(system["temp_path"] / "episodes")
        }
        
        agent = BaseAgent(agent_config)
        
        # Register agent for tenant
        success = await coordinator.register_agent_for_tenant(tenant_id, agent)
        assert success is True
        
        # Verify agent is registered
        tenant_agents = await coordinator.get_tenant_agents(tenant_id)
        assert len(tenant_agents) == 1
        assert tenant_agents[0].agent_id == "test_agent_1"
        
        # Verify agent tenant mapping
        agent_tenant = await coordinator.get_agent_tenant("test_agent_1")
        assert agent_tenant == tenant_id
        
        # Verify agent context
        context = await coordinator.get_agent_context("test_agent_1")
        assert context is not None
        assert context.tenant_id == tenant_id
        assert context.agent_id == "test_agent_1"
    
    @pytest.mark.asyncio
    async def test_tenant_limits_enforcement(self, setup_multi_tenant_system):
        """Test that tenant limits are properly enforced"""
        system = setup_multi_tenant_system
        multi_tenant_manager = system["multi_tenant_manager"]
        coordinator = system["coordinator"]
        
        # Create a tenant with limited agents
        tenant_id = await multi_tenant_manager.create_tenant(
            name="Limited Company",
            domain="limited.company.com",
            tier=TenantTier.STARTER,  # Starter tier has limited agents
            admin_email="admin@limited.company.com"
        )
        
        await multi_tenant_manager.activate_tenant(tenant_id)
        
        # Get tenant info to see limits
        tenant_info = await multi_tenant_manager.get_tenant_info(tenant_id)
        max_agents = tenant_info.config.max_agents
        
        # Try to register more agents than allowed
        for i in range(max_agents + 2):
            agent_config = {
                "agent_id": f"test_agent_{i}",
                "mailbox_path": str(system["temp_path"] / f"mailbox_{i}"),
                "episode_path": str(system["temp_path"] / f"episodes_{i}")
            }
            
            agent = BaseAgent(agent_config)
            success = await coordinator.register_agent_for_tenant(tenant_id, agent)
            
            if i < max_agents:
                assert success is True, f"Agent {i} should be registered"
            else:
                assert success is False, f"Agent {i} should be rejected due to limits"
        
        # Verify only max_agents are registered
        tenant_agents = await coordinator.get_tenant_agents(tenant_id)
        assert len(tenant_agents) == max_agents
    
    @pytest.mark.asyncio
    async def test_tenant_isolation(self, setup_multi_tenant_system):
        """Test that tenants are properly isolated"""
        system = setup_multi_tenant_system
        multi_tenant_manager = system["multi_tenant_manager"]
        coordinator = system["coordinator"]
        
        # Create two tenants
        tenant_1_id = await multi_tenant_manager.create_tenant(
            name="Company A",
            domain="company-a.com",
            tier=TenantTier.PROFESSIONAL
        )
        
        tenant_2_id = await multi_tenant_manager.create_tenant(
            name="Company B", 
            domain="company-b.com",
            tier=TenantTier.ENTERPRISE
        )
        
        await multi_tenant_manager.activate_tenant(tenant_1_id)
        await multi_tenant_manager.activate_tenant(tenant_2_id)
        
        # Register agents for each tenant
        agent_1 = BaseAgent({
            "agent_id": "agent_company_a",
            "mailbox_path": str(system["temp_path"] / "mailbox_a"),
            "episode_path": str(system["temp_path"] / "episodes_a")
        })
        
        agent_2 = BaseAgent({
            "agent_id": "agent_company_b",
            "mailbox_path": str(system["temp_path"] / "mailbox_b"),
            "episode_path": str(system["temp_path"] / "episodes_b")
        })
        
        await coordinator.register_agent_for_tenant(tenant_1_id, agent_1)
        await coordinator.register_agent_for_tenant(tenant_2_id, agent_2)
        
        # Verify agents are isolated
        tenant_1_agents = await coordinator.get_tenant_agents(tenant_1_id)
        tenant_2_agents = await coordinator.get_tenant_agents(tenant_2_id)
        
        assert len(tenant_1_agents) == 1
        assert len(tenant_2_agents) == 1
        assert tenant_1_agents[0].agent_id == "agent_company_a"
        assert tenant_2_agents[0].agent_id == "agent_company_b"
        
        # Verify agent contexts are isolated
        context_1 = await coordinator.get_agent_context("agent_company_a")
        context_2 = await coordinator.get_agent_context("agent_company_b")
        
        assert context_1.tenant_id == tenant_1_id
        assert context_2.tenant_id == tenant_2_id
        assert context_1.tenant_id != context_2.tenant_id
    
    @pytest.mark.asyncio
    async def test_tenant_coordination_status(self, setup_multi_tenant_system):
        """Test tenant coordination status reporting"""
        system = setup_multi_tenant_system
        multi_tenant_manager = system["multi_tenant_manager"]
        coordinator = system["coordinator"]
        
        # Create and activate tenant
        tenant_id = await multi_tenant_manager.create_tenant(
            name="Status Test Company",
            domain="status-test.company.com",
            tier=TenantTier.PROFESSIONAL
        )
        
        await multi_tenant_manager.activate_tenant(tenant_id)
        
        # Register agents
        for i in range(3):
            agent = BaseAgent({
                "agent_id": f"status_agent_{i}",
                "mailbox_path": str(system["temp_path"] / f"mailbox_{i}"),
                "episode_path": str(system["temp_path"] / f"episodes_{i}")
            })
            await coordinator.register_agent_for_tenant(tenant_id, agent)
        
        # Get coordination status
        status = await coordinator.get_tenant_coordination_status(tenant_id)
        
        assert status["tenant_id"] == tenant_id
        assert status["tenant_name"] == "Status Test Company"
        assert status["tenant_status"] == "active"
        assert status["tenant_tier"] == "professional"
        assert status["active_agents"] == 3
        assert len(status["agents"]) == 3
        
        # Verify agent details in status
        agent_ids = [agent["agent_id"] for agent in status["agents"]]
        assert "status_agent_0" in agent_ids
        assert "status_agent_1" in agent_ids
        assert "status_agent_2" in agent_ids
    
    @pytest.mark.asyncio
    async def test_system_coordination_status(self, setup_multi_tenant_system):
        """Test overall system coordination status"""
        system = setup_multi_tenant_system
        multi_tenant_manager = system["multi_tenant_manager"]
        coordinator = system["coordinator"]
        
        # Create multiple tenants
        tenant_ids = []
        for i in range(3):
            tenant_id = await multi_tenant_manager.create_tenant(
                name=f"Company {i}",
                domain=f"company{i}.com",
                tier=TenantTier.STARTER
            )
            await multi_tenant_manager.activate_tenant(tenant_id)
            tenant_ids.append(tenant_id)
            
            # Add agents to each tenant
            for j in range(2):
                agent = BaseAgent({
                    "agent_id": f"agent_{i}_{j}",
                    "mailbox_path": str(system["temp_path"] / f"mailbox_{i}_{j}"),
                    "episode_path": str(system["temp_path"] / f"episodes_{i}_{j}")
                })
                await coordinator.register_agent_for_tenant(tenant_id, agent)
        
        # Get system status
        system_status = await coordinator.get_system_coordination_status()
        
        assert system_status["total_tenants"] == 3
        assert system_status["active_tenants"] == 3
        assert system_status["total_agents"] == 6  # 3 tenants * 2 agents each
        
        # Verify tenant agent counts
        tenant_agents = system_status["tenant_agents"]
        for tenant_id in tenant_ids:
            assert tenant_agents[tenant_id] == 2
    
    @pytest.mark.asyncio
    async def test_agent_unregistration(self, setup_multi_tenant_system):
        """Test unregistering agents from tenants"""
        system = setup_multi_tenant_system
        multi_tenant_manager = system["multi_tenant_manager"]
        coordinator = system["coordinator"]
        
        # Create tenant and register agent
        tenant_id = await multi_tenant_manager.create_tenant(
            name="Unregister Test",
            domain="unregister.test.com",
            tier=TenantTier.STARTER
        )
        
        await multi_tenant_manager.activate_tenant(tenant_id)
        
        agent = BaseAgent({
            "agent_id": "unregister_agent",
            "mailbox_path": str(system["temp_path"] / "mailbox"),
            "episode_path": str(system["temp_path"] / "episodes")
        })
        
        await coordinator.register_agent_for_tenant(tenant_id, agent)
        
        # Verify agent is registered
        tenant_agents = await coordinator.get_tenant_agents(tenant_id)
        assert len(tenant_agents) == 1
        
        # Unregister agent
        success = await coordinator.unregister_agent_from_tenant(tenant_id, "unregister_agent")
        assert success is True
        
        # Verify agent is unregistered
        tenant_agents = await coordinator.get_tenant_agents(tenant_id)
        assert len(tenant_agents) == 0
        
        # Verify agent tenant mapping is removed
        agent_tenant = await coordinator.get_agent_tenant("unregister_agent")
        assert agent_tenant is None
        
        # Verify context is removed
        context = await coordinator.get_agent_context("unregister_agent")
        assert context is None 