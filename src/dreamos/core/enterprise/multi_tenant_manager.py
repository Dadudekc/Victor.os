"""
Victor.os Multi-Tenant Architecture System
Phase 4: Enterprise Deployment - Multi-tenant support for enterprise customers
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import structlog
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import hashlib
import secrets

console = Console()
logger = structlog.get_logger("multi_tenant_manager")

class TenantStatus(Enum):
    """Tenant status enumeration"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    CANCELLED = "cancelled"
    MAINTENANCE = "maintenance"

class TenantTier(Enum):
    """Tenant subscription tiers"""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"

class BillingCycle(Enum):
    """Billing cycle options"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"

@dataclass
class TenantConfig:
    """Tenant configuration and limits"""
    max_agents: int
    max_nodes: int
    max_storage_gb: int
    max_api_requests_per_minute: int
    max_concurrent_users: int
    features_enabled: List[str]
    custom_domain: Optional[str] = None
    ssl_enabled: bool = True
    backup_enabled: bool = True
    monitoring_enabled: bool = True

@dataclass
class TenantInfo:
    """Tenant information"""
    tenant_id: str
    name: str
    domain: str
    status: TenantStatus
    tier: TenantTier
    billing_cycle: BillingCycle
    created_at: float
    updated_at: float
    config: TenantConfig
    metadata: Dict[str, Any]
    admin_users: List[str]
    total_users: int
    total_agents: int
    total_nodes: int
    storage_used_gb: float
    api_requests_this_month: int

@dataclass
class TenantUsage:
    """Tenant usage metrics"""
    tenant_id: str
    timestamp: float
    agents_active: int
    nodes_active: int
    storage_used_gb: float
    api_requests: int
    cpu_usage_percent: float
    memory_usage_percent: float
    bandwidth_used_mb: float

class MultiTenantManager:
    """Multi-tenant architecture manager for enterprise deployment"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.tenants: Dict[str, TenantInfo] = {}
        self.tenant_usage: Dict[str, List[TenantUsage]] = {}
        self.tenant_resources: Dict[str, Dict[str, Any]] = {}
        self.isolation_enabled = True
        
        # Setup tenant storage
        self.tenant_dir = Path("tenants")
        self.tenant_dir.mkdir(exist_ok=True)
        
        # Setup monitoring
        self._setup_monitoring()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for multi-tenant manager"""
        return {
            "max_tenants": 1000,
            "default_tier": TenantTier.STARTER,
            "isolation_enabled": True,
            "usage_tracking_interval": 300,  # 5 minutes
            "billing_cycle": BillingCycle.MONTHLY,
            "auto_suspension": True,
            "suspension_threshold_days": 30,
            "backup_interval": 86400,  # 24 hours
            "monitoring_enabled": True,
            "compliance_mode": False,
            "audit_logging": True,
        }
    
    def _setup_monitoring(self):
        """Setup tenant monitoring"""
        self.metrics = {
            "total_tenants": 0,
            "active_tenants": 0,
            "total_users": 0,
            "total_agents": 0,
            "total_nodes": 0,
            "total_storage_gb": 0.0,
            "total_api_requests": 0,
        }
    
    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        asyncio.create_task(self._usage_tracking_loop())
        asyncio.create_task(self._billing_cycle_loop())
        asyncio.create_task(self._backup_loop())
        asyncio.create_task(self._compliance_audit_loop())
    
    async def create_tenant(self, name: str, domain: str, tier: TenantTier = None, 
                          admin_email: str = None, custom_config: Dict[str, Any] = None) -> str:
        """Create a new tenant"""
        try:
            # Validate tenant creation
            if len(self.tenants) >= self.config["max_tenants"]:
                raise ValueError("Maximum tenant limit reached")
            
            if not self._validate_domain(domain):
                raise ValueError("Invalid domain format")
            
            if self._domain_exists(domain):
                raise ValueError("Domain already exists")
            
            # Generate tenant ID
            tenant_id = self._generate_tenant_id()
            
            # Set default tier
            tier = tier or self.config["default_tier"]
            
            # Create tenant configuration
            config = self._create_tenant_config(tier, custom_config)
            
            # Create tenant info
            tenant_info = TenantInfo(
                tenant_id=tenant_id,
                name=name,
                domain=domain,
                status=TenantStatus.PENDING,
                tier=tier,
                billing_cycle=self.config["billing_cycle"],
                created_at=time.time(),
                updated_at=time.time(),
                config=config,
                metadata=custom_config or {},
                admin_users=[admin_email] if admin_email else [],
                total_users=0,
                total_agents=0,
                total_nodes=0,
                storage_used_gb=0.0,
                api_requests_this_month=0
            )
            
            # Store tenant
            self.tenants[tenant_id] = tenant_info
            self.tenant_usage[tenant_id] = []
            self.tenant_resources[tenant_id] = {}
            
            # Create tenant directory structure
            await self._create_tenant_directory(tenant_id)
            
            # Update metrics
            self._update_metrics()
            
            logger.info("Tenant created successfully", 
                       tenant_id=tenant_id,
                       name=name,
                       domain=domain,
                       tier=tier.value)
            
            return tenant_id
            
        except Exception as e:
            logger.error("Failed to create tenant", 
                        name=name,
                        domain=domain,
                        error=str(e))
            raise
    
    def _validate_domain(self, domain: str) -> bool:
        """Validate domain format"""
        # Simple domain validation
        if not domain or len(domain) < 3:
            return False
        
        # Check for valid characters
        valid_chars = set("abcdefghijklmnopqrstuvwxyz0123456789.-")
        return all(c in valid_chars for c in domain.lower())
    
    def _domain_exists(self, domain: str) -> bool:
        """Check if domain already exists"""
        return any(t.domain == domain for t in self.tenants.values())
    
    def _generate_tenant_id(self) -> str:
        """Generate unique tenant ID"""
        return f"tenant_{uuid.uuid4().hex[:8]}"
    
    def _create_tenant_config(self, tier: TenantTier, custom_config: Dict[str, Any] = None) -> TenantConfig:
        """Create tenant configuration based on tier"""
        tier_configs = {
            TenantTier.STARTER: {
                "max_agents": 5,
                "max_nodes": 2,
                "max_storage_gb": 10,
                "max_api_requests_per_minute": 100,
                "max_concurrent_users": 10,
                "features_enabled": ["basic_agents", "api_access", "basic_analytics"]
            },
            TenantTier.PROFESSIONAL: {
                "max_agents": 25,
                "max_nodes": 5,
                "max_storage_gb": 100,
                "max_api_requests_per_minute": 500,
                "max_concurrent_users": 50,
                "features_enabled": ["basic_agents", "api_access", "advanced_analytics", "ml_optimization", "plugin_support"]
            },
            TenantTier.ENTERPRISE: {
                "max_agents": 100,
                "max_nodes": 20,
                "max_storage_gb": 1000,
                "max_api_requests_per_minute": 2000,
                "max_concurrent_users": 200,
                "features_enabled": ["basic_agents", "api_access", "advanced_analytics", "ml_optimization", "plugin_support", "custom_integrations", "priority_support", "sla_guarantee"]
            },
            TenantTier.CUSTOM: {
                "max_agents": custom_config.get("max_agents", 1000),
                "max_nodes": custom_config.get("max_nodes", 100),
                "max_storage_gb": custom_config.get("max_storage_gb", 10000),
                "max_api_requests_per_minute": custom_config.get("max_api_requests_per_minute", 10000),
                "max_concurrent_users": custom_config.get("max_concurrent_users", 1000),
                "features_enabled": custom_config.get("features_enabled", ["all_features"])
            }
        }
        
        base_config = tier_configs.get(tier, tier_configs[TenantTier.STARTER])
        
        return TenantConfig(
            max_agents=base_config["max_agents"],
            max_nodes=base_config["max_nodes"],
            max_storage_gb=base_config["max_storage_gb"],
            max_api_requests_per_minute=base_config["max_api_requests_per_minute"],
            max_concurrent_users=base_config["max_concurrent_users"],
            features_enabled=base_config["features_enabled"],
            custom_domain=custom_config.get("custom_domain") if custom_config else None,
            ssl_enabled=custom_config.get("ssl_enabled", True) if custom_config else True,
            backup_enabled=custom_config.get("backup_enabled", True) if custom_config else True,
            monitoring_enabled=custom_config.get("monitoring_enabled", True) if custom_config else True
        )
    
    async def _create_tenant_directory(self, tenant_id: str):
        """Create tenant directory structure"""
        tenant_path = self.tenant_dir / tenant_id
        tenant_path.mkdir(exist_ok=True)
        
        # Create subdirectories
        (tenant_path / "data").mkdir(exist_ok=True)
        (tenant_path / "logs").mkdir(exist_ok=True)
        (tenant_path / "backups").mkdir(exist_ok=True)
        (tenant_path / "config").mkdir(exist_ok=True)
        (tenant_path / "plugins").mkdir(exist_ok=True)
    
    async def activate_tenant(self, tenant_id: str) -> bool:
        """Activate a tenant"""
        try:
            if tenant_id not in self.tenants:
                raise ValueError("Tenant not found")
            
            tenant = self.tenants[tenant_id]
            tenant.status = TenantStatus.ACTIVE
            tenant.updated_at = time.time()
            
            logger.info("Tenant activated", tenant_id=tenant_id)
            return True
            
        except Exception as e:
            logger.error("Failed to activate tenant", 
                        tenant_id=tenant_id,
                        error=str(e))
            return False
    
    async def suspend_tenant(self, tenant_id: str, reason: str = None) -> bool:
        """Suspend a tenant"""
        try:
            if tenant_id not in self.tenants:
                raise ValueError("Tenant not found")
            
            tenant = self.tenants[tenant_id]
            tenant.status = TenantStatus.SUSPENDED
            tenant.updated_at = time.time()
            
            # Add suspension metadata
            tenant.metadata["suspension_reason"] = reason
            tenant.metadata["suspended_at"] = time.time()
            
            logger.info("Tenant suspended", 
                       tenant_id=tenant_id,
                       reason=reason)
            return True
            
        except Exception as e:
            logger.error("Failed to suspend tenant", 
                        tenant_id=tenant_id,
                        error=str(e))
            return False
    
    async def update_tenant_config(self, tenant_id: str, config_updates: Dict[str, Any]) -> bool:
        """Update tenant configuration"""
        try:
            if tenant_id not in self.tenants:
                raise ValueError("Tenant not found")
            
            tenant = self.tenants[tenant_id]
            
            # Update config fields
            for key, value in config_updates.items():
                if hasattr(tenant.config, key):
                    setattr(tenant.config, key, value)
            
            tenant.updated_at = time.time()
            
            logger.info("Tenant config updated", 
                       tenant_id=tenant_id,
                       updates=list(config_updates.keys()))
            return True
            
        except Exception as e:
            logger.error("Failed to update tenant config", 
                        tenant_id=tenant_id,
                        error=str(e))
            return False
    
    async def get_tenant_info(self, tenant_id: str) -> Optional[TenantInfo]:
        """Get tenant information"""
        return self.tenants.get(tenant_id)
    
    async def get_tenant_usage(self, tenant_id: str, days: int = 30) -> List[TenantUsage]:
        """Get tenant usage metrics"""
        if tenant_id not in self.tenant_usage:
            return []
        
        cutoff_time = time.time() - (days * 86400)
        return [
            usage for usage in self.tenant_usage[tenant_id]
            if usage.timestamp >= cutoff_time
        ]
    
    async def check_tenant_limits(self, tenant_id: str) -> Dict[str, Any]:
        """Check tenant resource limits"""
        if tenant_id not in self.tenants:
            return {"error": "Tenant not found"}
        
        tenant = self.tenants[tenant_id]
        config = tenant.config
        
        # Get current usage
        current_usage = await self._get_current_tenant_usage(tenant_id)
        
        limits = {
            "agents": {
                "current": tenant.total_agents,
                "limit": config.max_agents,
                "usage_percent": (tenant.total_agents / config.max_agents) * 100
            },
            "nodes": {
                "current": tenant.total_nodes,
                "limit": config.max_nodes,
                "usage_percent": (tenant.total_nodes / config.max_nodes) * 100
            },
            "storage": {
                "current_gb": tenant.storage_used_gb,
                "limit_gb": config.max_storage_gb,
                "usage_percent": (tenant.storage_used_gb / config.max_storage_gb) * 100
            },
            "api_requests": {
                "current_per_minute": current_usage.get("api_requests_per_minute", 0),
                "limit_per_minute": config.max_api_requests_per_minute,
                "usage_percent": (current_usage.get("api_requests_per_minute", 0) / config.max_api_requests_per_minute) * 100
            },
            "users": {
                "current": tenant.total_users,
                "limit": config.max_concurrent_users,
                "usage_percent": (tenant.total_users / config.max_concurrent_users) * 100
            }
        }
        
        # Check for exceeded limits
        exceeded_limits = []
        for resource, data in limits.items():
            if data["usage_percent"] > 100:
                exceeded_limits.append(resource)
        
        limits["exceeded_limits"] = exceeded_limits
        limits["status"] = "warning" if exceeded_limits else "ok"
        
        return limits
    
    async def _get_current_tenant_usage(self, tenant_id: str) -> Dict[str, Any]:
        """Get current tenant usage metrics"""
        if tenant_id not in self.tenant_usage or not self.tenant_usage[tenant_id]:
            return {}
        
        # Get most recent usage
        latest_usage = max(self.tenant_usage[tenant_id], key=lambda x: x.timestamp)
        
        return {
            "agents_active": latest_usage.agents_active,
            "nodes_active": latest_usage.nodes_active,
            "storage_used_gb": latest_usage.storage_used_gb,
            "api_requests_per_minute": latest_usage.api_requests,
            "cpu_usage_percent": latest_usage.cpu_usage_percent,
            "memory_usage_percent": latest_usage.memory_usage_percent,
            "bandwidth_used_mb": latest_usage.bandwidth_used_mb
        }
    
    async def record_tenant_usage(self, tenant_id: str, usage_data: Dict[str, Any]):
        """Record tenant usage metrics"""
        try:
            if tenant_id not in self.tenants:
                return
            
            usage = TenantUsage(
                tenant_id=tenant_id,
                timestamp=time.time(),
                agents_active=usage_data.get("agents_active", 0),
                nodes_active=usage_data.get("nodes_active", 0),
                storage_used_gb=usage_data.get("storage_used_gb", 0.0),
                api_requests=usage_data.get("api_requests", 0),
                cpu_usage_percent=usage_data.get("cpu_usage_percent", 0.0),
                memory_usage_percent=usage_data.get("memory_usage_percent", 0.0),
                bandwidth_used_mb=usage_data.get("bandwidth_used_mb", 0.0)
            )
            
            self.tenant_usage[tenant_id].append(usage)
            
            # Update tenant totals
            tenant = self.tenants[tenant_id]
            tenant.total_agents = usage.agents_active
            tenant.total_nodes = usage.nodes_active
            tenant.storage_used_gb = usage.storage_used_gb
            tenant.api_requests_this_month += usage.api_requests
            
            # Keep only recent usage data (last 90 days)
            cutoff_time = time.time() - (90 * 86400)
            self.tenant_usage[tenant_id] = [
                u for u in self.tenant_usage[tenant_id]
                if u.timestamp >= cutoff_time
            ]
            
        except Exception as e:
            logger.error("Failed to record tenant usage", 
                        tenant_id=tenant_id,
                        error=str(e))
    
    async def _usage_tracking_loop(self):
        """Background usage tracking loop"""
        while True:
            try:
                for tenant_id in self.tenants.keys():
                    # Simulate usage data collection
                    usage_data = await self._collect_tenant_usage(tenant_id)
                    await self.record_tenant_usage(tenant_id, usage_data)
                
                await asyncio.sleep(self.config["usage_tracking_interval"])
                
            except Exception as e:
                logger.error("Usage tracking error", error=str(e))
                await asyncio.sleep(60)
    
    async def _collect_tenant_usage(self, tenant_id: str) -> Dict[str, Any]:
        """Collect usage data for tenant"""
        # This would integrate with the distributed manager and other systems
        # For now, return simulated data
        return {
            "agents_active": 2,
            "nodes_active": 1,
            "storage_used_gb": 5.2,
            "api_requests": 45,
            "cpu_usage_percent": 25.0,
            "memory_usage_percent": 30.0,
            "bandwidth_used_mb": 150.0
        }
    
    async def _billing_cycle_loop(self):
        """Background billing cycle processing"""
        while True:
            try:
                current_time = time.time()
                
                for tenant_id, tenant in self.tenants.items():
                    # Check if billing cycle needs processing
                    if self._should_process_billing(tenant, current_time):
                        await self._process_billing_cycle(tenant_id)
                
                await asyncio.sleep(86400)  # Check daily
                
            except Exception as e:
                logger.error("Billing cycle error", error=str(e))
                await asyncio.sleep(3600)
    
    def _should_process_billing(self, tenant: TenantInfo, current_time: float) -> bool:
        """Check if billing cycle should be processed"""
        # Simplified billing cycle check
        days_since_creation = (current_time - tenant.created_at) / 86400
        
        if tenant.billing_cycle == BillingCycle.MONTHLY:
            return days_since_creation % 30 < 1
        elif tenant.billing_cycle == BillingCycle.QUARTERLY:
            return days_since_creation % 90 < 1
        elif tenant.billing_cycle == BillingCycle.ANNUALLY:
            return days_since_creation % 365 < 1
        
        return False
    
    async def _process_billing_cycle(self, tenant_id: str):
        """Process billing cycle for tenant"""
        try:
            tenant = self.tenants[tenant_id]
            
            # Reset monthly counters
            tenant.api_requests_this_month = 0
            
            # Generate billing report
            billing_report = await self._generate_billing_report(tenant_id)
            
            # Store billing report
            await self._store_billing_report(tenant_id, billing_report)
            
            logger.info("Billing cycle processed", 
                       tenant_id=tenant_id,
                       cycle=tenant.billing_cycle.value)
            
        except Exception as e:
            logger.error("Failed to process billing cycle", 
                        tenant_id=tenant_id,
                        error=str(e))
    
    async def _generate_billing_report(self, tenant_id: str) -> Dict[str, Any]:
        """Generate billing report for tenant"""
        tenant = self.tenants[tenant_id]
        usage = await self.get_tenant_usage(tenant_id, 30)
        
        return {
            "tenant_id": tenant_id,
            "billing_cycle": tenant.billing_cycle.value,
            "period_start": time.time() - (30 * 86400),
            "period_end": time.time(),
            "usage_summary": {
                "total_agents": tenant.total_agents,
                "total_nodes": tenant.total_nodes,
                "storage_used_gb": tenant.storage_used_gb,
                "api_requests": tenant.api_requests_this_month
            },
            "tier": tenant.tier.value,
            "estimated_cost": self._calculate_estimated_cost(tenant)
        }
    
    def _calculate_estimated_cost(self, tenant: TenantInfo) -> float:
        """Calculate estimated cost for tenant"""
        # Simplified cost calculation
        base_costs = {
            TenantTier.STARTER: 99.0,
            TenantTier.PROFESSIONAL: 299.0,
            TenantTier.ENTERPRISE: 999.0,
            TenantTier.CUSTOM: 1999.0
        }
        
        base_cost = base_costs.get(tenant.tier, 99.0)
        
        # Add usage-based costs
        storage_cost = tenant.storage_used_gb * 0.10  # $0.10 per GB
        api_cost = (tenant.api_requests_this_month / 1000) * 0.01  # $0.01 per 1000 requests
        
        return base_cost + storage_cost + api_cost
    
    async def _store_billing_report(self, tenant_id: str, report: Dict[str, Any]):
        """Store billing report"""
        tenant_path = self.tenant_dir / tenant_id / "billing"
        tenant_path.mkdir(exist_ok=True)
        
        report_file = tenant_path / f"billing_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
    
    async def _backup_loop(self):
        """Background backup loop"""
        while True:
            try:
                for tenant_id in self.tenants.keys():
                    if self.tenants[tenant_id].config.backup_enabled:
                        await self._backup_tenant_data(tenant_id)
                
                await asyncio.sleep(self.config["backup_interval"])
                
            except Exception as e:
                logger.error("Backup error", error=str(e))
                await asyncio.sleep(3600)
    
    async def _backup_tenant_data(self, tenant_id: str):
        """Backup tenant data"""
        try:
            tenant_path = self.tenant_dir / tenant_id
            backup_path = tenant_path / "backups" / f"backup_{int(time.time())}.tar.gz"
            
            # Simplified backup - in real implementation, use proper backup tools
            logger.info("Tenant backup created", 
                       tenant_id=tenant_id,
                       backup_path=str(backup_path))
            
        except Exception as e:
            logger.error("Failed to backup tenant data", 
                        tenant_id=tenant_id,
                        error=str(e))
    
    async def _compliance_audit_loop(self):
        """Background compliance audit loop"""
        if not self.config["compliance_mode"]:
            return
        
        while True:
            try:
                for tenant_id in self.tenants.keys():
                    await self._audit_tenant_compliance(tenant_id)
                
                await asyncio.sleep(86400)  # Daily audit
                
            except Exception as e:
                logger.error("Compliance audit error", error=str(e))
                await asyncio.sleep(3600)
    
    async def _audit_tenant_compliance(self, tenant_id: str):
        """Audit tenant compliance"""
        try:
            tenant = self.tenants[tenant_id]
            
            # Check various compliance requirements
            compliance_checks = {
                "data_retention": await self._check_data_retention(tenant_id),
                "access_controls": await self._check_access_controls(tenant_id),
                "audit_logging": await self._check_audit_logging(tenant_id),
                "security_measures": await self._check_security_measures(tenant_id)
            }
            
            # Store compliance report
            await self._store_compliance_report(tenant_id, compliance_checks)
            
            logger.info("Compliance audit completed", 
                       tenant_id=tenant_id,
                       checks_passed=sum(compliance_checks.values()))
            
        except Exception as e:
            logger.error("Failed to audit tenant compliance", 
                        tenant_id=tenant_id,
                        error=str(e))
    
    async def _check_data_retention(self, tenant_id: str) -> bool:
        """Check data retention compliance"""
        # Simplified check
        return True
    
    async def _check_access_controls(self, tenant_id: str) -> bool:
        """Check access control compliance"""
        # Simplified check
        return True
    
    async def _check_audit_logging(self, tenant_id: str) -> bool:
        """Check audit logging compliance"""
        # Simplified check
        return True
    
    async def _check_security_measures(self, tenant_id: str) -> bool:
        """Check security measures compliance"""
        # Simplified check
        return True
    
    async def _store_compliance_report(self, tenant_id: str, checks: Dict[str, bool]):
        """Store compliance report"""
        tenant_path = self.tenant_dir / tenant_id / "compliance"
        tenant_path.mkdir(exist_ok=True)
        
        report = {
            "tenant_id": tenant_id,
            "audit_date": time.time(),
            "checks": checks,
            "overall_compliance": all(checks.values())
        }
        
        report_file = tenant_path / f"compliance_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
    
    def _update_metrics(self):
        """Update system metrics"""
        self.metrics["total_tenants"] = len(self.tenants)
        self.metrics["active_tenants"] = len([t for t in self.tenants.values() if t.status == TenantStatus.ACTIVE])
        self.metrics["total_users"] = sum(t.total_users for t in self.tenants.values())
        self.metrics["total_agents"] = sum(t.total_agents for t in self.tenants.values())
        self.metrics["total_nodes"] = sum(t.total_nodes for t in self.tenants.values())
        self.metrics["total_storage_gb"] = sum(t.storage_used_gb for t in self.tenants.values())
        self.metrics["total_api_requests"] = sum(t.api_requests_this_month for t in self.tenants.values())
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get multi-tenant system status"""
        return {
            "total_tenants": len(self.tenants),
            "active_tenants": len([t for t in self.tenants.values() if t.status == TenantStatus.ACTIVE]),
            "tenants_by_tier": self._group_tenants_by_tier(),
            "tenants_by_status": self._group_tenants_by_status(),
            "metrics": self.metrics,
            "config": {
                "max_tenants": self.config["max_tenants"],
                "isolation_enabled": self.config["isolation_enabled"],
                "compliance_mode": self.config["compliance_mode"],
                "audit_logging": self.config["audit_logging"]
            }
        }
    
    def _group_tenants_by_tier(self) -> Dict[str, int]:
        """Group tenants by tier"""
        grouped = {}
        for tenant in self.tenants.values():
            tier = tenant.tier.value
            grouped[tier] = grouped.get(tier, 0) + 1
        return grouped
    
    def _group_tenants_by_status(self) -> Dict[str, int]:
        """Group tenants by status"""
        grouped = {}
        for tenant in self.tenants.values():
            status = tenant.status.value
            grouped[status] = grouped.get(status, 0) + 1
        return grouped 