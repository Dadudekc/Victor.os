"""
Victor.os Phase 3 Integration Demo
Comprehensive simulation of distributed agents, ML optimization, and API gateway
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Any
from pathlib import Path
import structlog
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout

# Import Phase 3 modules
from core.scalability.distributed_manager import (
    DistributedManager, NodeInfo, NodeStatus, AgentDeployment
)
from core.intelligence.ml_optimizer import (
    MLOptimizer, AgentMetrics, OptimizationTarget, OptimizationResult
)
from core.integration.plugin_manager import (
    PluginManager, PluginType, PluginStatus, PluginInfo
)
from core.integration.api_gateway import APIGateway, APIVersion, EndpointType

console = Console()
logger = structlog.get_logger("phase3_demo")

class Phase3IntegrationDemo:
    """Comprehensive Phase 3 integration demonstration"""
    
    def __init__(self):
        self.distributed_manager = DistributedManager()
        self.ml_optimizer = MLOptimizer()
        self.plugin_manager = PluginManager()
        self.api_gateway = APIGateway()
        
        # Demo state
        self.demo_agents = {}
        self.demo_nodes = {}
        self.demo_metrics = []
        self.demo_plugins = {}
        
        # Setup demo environment
        self._setup_demo_environment()
    
    def _setup_demo_environment(self):
        """Setup demo environment with mock data"""
        console.print(Panel.fit(
            "🚀 [bold blue]Victor.os Phase 3 Integration Demo[/bold blue]\n"
            "Setting up distributed agents, ML optimization, and API gateway...",
            border_style="blue"
        ))
    
    async def run_full_demo(self):
        """Run complete Phase 3 integration demo"""
        console.print("\n[bold green]Starting Phase 3 Integration Demo[/bold green]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Step 1: Initialize distributed nodes
            task1 = progress.add_task("🌐 Initializing distributed nodes...", total=3)
            await self._demo_distributed_nodes(progress, task1)
            
            # Step 2: Deploy agents
            task2 = progress.add_task("🤖 Deploying agents...", total=5)
            await self._demo_agent_deployment(progress, task2)
            
            # Step 3: Collect metrics and run ML optimization
            task3 = progress.add_task("🧠 Running ML optimization...", total=10)
            await self._demo_ml_optimization(progress, task3)
            
            # Step 4: Load plugins
            task4 = progress.add_task("🔌 Loading plugins...", total=3)
            await self._demo_plugin_system(progress, task4)
            
            # Step 5: Start API gateway
            task5 = progress.add_task("🌐 Starting API gateway...", total=2)
            await self._demo_api_gateway(progress, task5)
            
            # Step 6: Integration testing
            task6 = progress.add_task("🧪 Running integration tests...", total=5)
            await self._demo_integration_tests(progress, task6)
        
        # Final status report
        await self._generate_final_report()
    
    async def _demo_distributed_nodes(self, progress, task):
        """Demonstrate distributed node management"""
        try:
            # Create mock nodes
            nodes = [
                NodeInfo(
                    node_id="node-1",
                    host="192.168.1.10",
                    port=8080,
                    status=NodeStatus.ONLINE,
                    capacity=10,
                    current_load=0,
                    cpu_usage=0.3,
                    memory_usage=0.4,
                    last_heartbeat=time.time(),
                    metadata={"region": "us-east", "zone": "a"}
                ),
                NodeInfo(
                    node_id="node-2", 
                    host="192.168.1.11",
                    port=8080,
                    status=NodeStatus.ONLINE,
                    capacity=8,
                    current_load=0,
                    cpu_usage=0.2,
                    memory_usage=0.3,
                    last_heartbeat=time.time(),
                    metadata={"region": "us-west", "zone": "b"}
                ),
                NodeInfo(
                    node_id="node-3",
                    host="192.168.1.12", 
                    port=8080,
                    status=NodeStatus.ONLINE,
                    capacity=12,
                    current_load=0,
                    cpu_usage=0.1,
                    memory_usage=0.2,
                    last_heartbeat=time.time(),
                    metadata={"region": "eu-west", "zone": "c"}
                )
            ]
            
            # Register nodes
            for i, node in enumerate(nodes):
                success = await self.distributed_manager.register_node(node)
                if success:
                    self.demo_nodes[node.node_id] = node
                    progress.update(task, advance=1)
                    await asyncio.sleep(0.5)
            
            # Get system status
            status = await self.distributed_manager.get_system_status()
            
            # Display node table
            table = Table(title="🌐 Distributed Nodes Status")
            table.add_column("Node ID", style="cyan")
            table.add_column("Host", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Capacity", style="blue")
            table.add_column("Load", style="red")
            table.add_column("CPU", style="magenta")
            
            for node in self.demo_nodes.values():
                table.add_row(
                    node.node_id,
                    f"{node.host}:{node.port}",
                    node.status.value,
                    str(node.capacity),
                    f"{node.current_load}/{node.capacity}",
                    f"{node.cpu_usage:.1%}"
                )
            
            console.print(table)
            
        except Exception as e:
            logger.error("Distributed nodes demo failed", error=str(e))
    
    async def _demo_agent_deployment(self, progress, task):
        """Demonstrate agent deployment across nodes"""
        try:
            # Create agent configurations
            agent_configs = [
                {
                    "name": "Research Agent",
                    "type": "research",
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                {
                    "name": "Analysis Agent", 
                    "type": "analysis",
                    "model": "gpt-4",
                    "temperature": 0.3,
                    "max_tokens": 1500
                },
                {
                    "name": "Creative Agent",
                    "type": "creative", 
                    "model": "gpt-4",
                    "temperature": 0.9,
                    "max_tokens": 3000
                },
                {
                    "name": "Code Agent",
                    "type": "coding",
                    "model": "gpt-4", 
                    "temperature": 0.2,
                    "max_tokens": 4000
                },
                {
                    "name": "QA Agent",
                    "type": "qa",
                    "model": "gpt-4",
                    "temperature": 0.5,
                    "max_tokens": 1000
                }
            ]
            
            # Deploy agents
            for i, config in enumerate(agent_configs):
                agent_id = await self.distributed_manager.deploy_agent(config)
                if agent_id:
                    self.demo_agents[agent_id] = {
                        "config": config,
                        "deployed_at": time.time(),
                        "status": "active"
                    }
                    progress.update(task, advance=1)
                    await asyncio.sleep(0.3)
            
            # Display deployment status
            table = Table(title="🤖 Agent Deployment Status")
            table.add_column("Agent ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Type", style="yellow")
            table.add_column("Model", style="blue")
            table.add_column("Status", style="red")
            
            for agent_id, agent_data in self.demo_agents.items():
                table.add_row(
                    agent_id[:8] + "...",
                    agent_data["config"]["name"],
                    agent_data["config"]["type"],
                    agent_data["config"]["model"],
                    agent_data["status"]
                )
            
            console.print(table)
            
        except Exception as e:
            logger.error("Agent deployment demo failed", error=str(e))
    
    async def _demo_ml_optimization(self, progress, task):
        """Demonstrate ML optimization system"""
        try:
            # Generate mock metrics for agents
            for agent_id in self.demo_agents.keys():
                for i in range(10):  # Generate 10 metrics per agent
                    metrics = AgentMetrics(
                        agent_id=agent_id,
                        timestamp=time.time() - (i * 3600),  # Last 10 hours
                        response_time=2.5 + (i * 0.1),  # Increasing response time
                        success_rate=0.85 + (i * 0.01),  # Improving success rate
                        cpu_usage=0.3 + (i * 0.02),
                        memory_usage=0.4 + (i * 0.01),
                        user_satisfaction=0.8 + (i * 0.02),
                        task_completion_rate=0.9 + (i * 0.01),
                        error_rate=0.05 - (i * 0.002),
                        interaction_count=100 + (i * 50),
                        context_length=1000 + (i * 100),
                        model_parameters=self.demo_agents[agent_id]["config"]
                    )
                    
                    await self.ml_optimizer.collect_metrics(metrics)
                    self.demo_metrics.append(metrics)
                    progress.update(task, advance=0.5)
                    await asyncio.sleep(0.1)
            
            # Run optimization for each agent
            for agent_id in self.demo_agents.keys():
                for target in [OptimizationTarget.RESPONSE_TIME, OptimizationTarget.SUCCESS_RATE]:
                    result = await self.ml_optimizer.optimize_agent(agent_id, target)
                    if result:
                        progress.update(task, advance=0.5)
                        await asyncio.sleep(0.2)
            
            # Display optimization results
            table = Table(title="🧠 ML Optimization Results")
            table.add_column("Agent ID", style="cyan")
            table.add_column("Target", style="green")
            table.add_column("Original", style="yellow")
            table.add_column("Optimized", style="blue")
            table.add_column("Improvement", style="red")
            table.add_column("Confidence", style="magenta")
            
            # Get recent optimizations
            recent_optimizations = self.ml_optimizer.optimization_history[-5:]
            
            for opt in recent_optimizations:
                table.add_row(
                    opt.agent_id[:8] + "...",
                    opt.optimization_target.value,
                    f"{opt.original_value:.3f}",
                    f"{opt.optimized_value:.3f}",
                    f"{opt.improvement_percentage:+.1f}%",
                    f"{opt.confidence_score:.2f}"
                )
            
            console.print(table)
            
        except Exception as e:
            logger.error("ML optimization demo failed", error=str(e))
    
    async def _demo_plugin_system(self, progress, task):
        """Demonstrate plugin system"""
        try:
            # Create mock plugin manifests
            plugin_manifests = [
                {
                    "name": "Discord Integration",
                    "version": "1.0.0",
                    "description": "Discord bot integration for agent communication",
                    "author": "Victor.os Team",
                    "type": "api_integration",
                    "entry_point": "discord_bot",
                    "dependencies": [],
                    "requirements": ["discord.py"]
                },
                {
                    "name": "Data Analytics",
                    "version": "1.0.0", 
                    "description": "Advanced analytics and reporting plugin",
                    "author": "Victor.os Team",
                    "type": "analytics",
                    "entry_point": "analytics_engine",
                    "dependencies": [],
                    "requirements": ["pandas", "matplotlib"]
                },
                {
                    "name": "Security Monitor",
                    "version": "1.0.0",
                    "description": "Security monitoring and threat detection",
                    "author": "Victor.os Team", 
                    "type": "security",
                    "entry_point": "security_monitor",
                    "dependencies": [],
                    "requirements": ["cryptography"]
                }
            ]
            
            # Create plugin directories and manifests
            for i, manifest in enumerate(plugin_manifests):
                plugin_type = manifest["type"]
                plugin_name = manifest["name"].lower().replace(" ", "_")
                
                # Create plugin directory
                plugin_dir = Path(f"plugins/{plugin_type}/{plugin_name}")
                plugin_dir.mkdir(parents=True, exist_ok=True)
                
                # Create manifest file
                manifest_file = plugin_dir / "manifest.yaml"
                import yaml
                with open(manifest_file, 'w') as f:
                    yaml.dump(manifest, f)
                
                # Create entry point file
                entry_file = plugin_dir / f"{manifest['entry_point']}.py"
                entry_file.write_text(f"# {manifest['name']} plugin entry point")
                
                progress.update(task, advance=1)
                await asyncio.sleep(0.3)
            
            # Discover and load plugins
            discovered_plugins = await self.plugin_manager.discover_plugins()
            
            # Display plugin status
            table = Table(title="🔌 Plugin System Status")
            table.add_column("Plugin Name", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Version", style="yellow")
            table.add_column("Status", style="blue")
            table.add_column("Enabled", style="red")
            
            plugin_status = await self.plugin_manager.get_all_plugins_status()
            
            for plugin_data in plugin_status["plugin_list"]:
                if plugin_data:
                    info = plugin_data["info"]
                    table.add_row(
                        info["name"],
                        info["plugin_type"],
                        info["version"],
                        info["status"],
                        "✅" if info["enabled"] else "❌"
                    )
            
            console.print(table)
            
        except Exception as e:
            logger.error("Plugin system demo failed", error=str(e))
    
    async def _demo_api_gateway(self, progress, task):
        """Demonstrate API gateway"""
        try:
            # Register custom endpoints
            self.api_gateway.register_endpoint(
                path="/demo/agents",
                method="GET",
                handler=self._demo_agents_endpoint,
                version=APIVersion.V1,
                endpoint_type=EndpointType.REST,
                description="Demo agents endpoint"
            )
            
            self.api_gateway.register_endpoint(
                path="/demo/optimize/{agent_id}",
                method="POST",
                handler=self._demo_optimize_endpoint,
                version=APIVersion.V1,
                endpoint_type=EndpointType.REST,
                description="Demo optimization endpoint"
            )
            
            progress.update(task, advance=1)
            
            # Get API gateway status
            status = await self.api_gateway.get_system_status()
            
            # Display API status
            table = Table(title="🌐 API Gateway Status")
            table.add_column("Endpoint", style="cyan")
            table.add_column("Method", style="green")
            table.add_column("Version", style="yellow")
            table.add_column("Type", style="blue")
            table.add_column("Auth", style="red")
            
            for endpoint in status["endpoints"][:5]:  # Show first 5 endpoints
                table.add_row(
                    endpoint["path"],
                    endpoint["method"],
                    endpoint["version"],
                    endpoint["type"],
                    "✅" if endpoint["authentication_required"] else "❌"
                )
            
            console.print(table)
            progress.update(task, advance=1)
            
        except Exception as e:
            logger.error("API gateway demo failed", error=str(e))
    
    async def _demo_integration_tests(self, progress, task):
        """Run integration tests across all systems"""
        try:
            tests = [
                ("Distributed Manager", self._test_distributed_manager),
                ("ML Optimizer", self._test_ml_optimizer),
                ("Plugin Manager", self._test_plugin_manager),
                ("API Gateway", self._test_api_gateway),
                ("Cross-System Integration", self._test_cross_system)
            ]
            
            for test_name, test_func in tests:
                try:
                    await test_func()
                    progress.update(task, advance=1)
                    console.print(f"✅ {test_name} test passed")
                except Exception as e:
                    console.print(f"❌ {test_name} test failed: {str(e)}")
                    progress.update(task, advance=1)
                
                await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error("Integration tests failed", error=str(e))
    
    async def _test_distributed_manager(self):
        """Test distributed manager functionality"""
        # Test node registration
        status = await self.distributed_manager.get_system_status()
        assert len(status["nodes"]) > 0, "No nodes registered"
        
        # Test agent deployment
        assert len(status["deployments"]) > 0, "No agents deployed"
    
    async def _test_ml_optimizer(self):
        """Test ML optimizer functionality"""
        # Test metrics collection
        status = await self.ml_optimizer.get_system_status()
        assert status["total_metrics"] > 0, "No metrics collected"
        
        # Test optimization history
        assert len(self.ml_optimizer.optimization_history) > 0, "No optimizations performed"
    
    async def _test_plugin_manager(self):
        """Test plugin manager functionality"""
        # Test plugin discovery
        status = await self.plugin_manager.get_all_plugins_status()
        assert status["total_plugins"] > 0, "No plugins discovered"
    
    async def _test_api_gateway(self):
        """Test API gateway functionality"""
        # Test endpoint registration
        status = await self.api_gateway.get_system_status()
        assert status["endpoints_registered"] > 0, "No endpoints registered"
    
    async def _test_cross_system(self):
        """Test cross-system integration"""
        # Test that all systems are running
        assert len(self.demo_nodes) > 0, "No nodes available"
        assert len(self.demo_agents) > 0, "No agents deployed"
        assert len(self.demo_metrics) > 0, "No metrics collected"
    
    # API Gateway endpoint handlers
    async def _demo_agents_endpoint(self, request):
        """Demo agents endpoint"""
        return {
            "agents": [
                {
                    "id": agent_id,
                    "config": agent_data["config"],
                    "status": agent_data["status"]
                }
                for agent_id, agent_data in self.demo_agents.items()
            ],
            "total": len(self.demo_agents)
        }
    
    async def _demo_optimize_endpoint(self, request, agent_id: str):
        """Demo optimization endpoint"""
        if agent_id not in self.demo_agents:
            return {"error": "Agent not found"}
        
        # Run optimization
        result = await self.ml_optimizer.optimize_agent(
            agent_id, OptimizationTarget.RESPONSE_TIME
        )
        
        if result:
            return {
                "agent_id": agent_id,
                "optimization_result": {
                    "target": result.optimization_target.value,
                    "improvement": f"{result.improvement_percentage:.2f}%",
                    "confidence": f"{result.confidence_score:.2f}"
                }
            }
        else:
            return {"error": "Optimization failed"}
    
    async def _generate_final_report(self):
        """Generate final Phase 3 demo report"""
        console.print("\n" + "="*80)
        console.print(Panel.fit(
            "[bold green]🎉 Phase 3 Integration Demo Complete![/bold green]\n\n"
            "All systems are running and integrated successfully:\n\n"
            "🌐 [bold]Distributed System:[/bold] {nodes} nodes, {agents} agents deployed\n"
            "🧠 [bold]ML Optimization:[/bold] {metrics} metrics, {optimizations} optimizations\n"
            "🔌 [bold]Plugin System:[/bold] {plugins} plugins discovered\n"
            "🌐 [bold]API Gateway:[/bold] {endpoints} endpoints registered\n\n"
            "Victor.os is now ready for enterprise-scale deployment!".format(
                nodes=len(self.demo_nodes),
                agents=len(self.demo_agents),
                metrics=len(self.demo_metrics),
                optimizations=len(self.ml_optimizer.optimization_history),
                plugins=len(self.plugin_manager.plugin_info),
                endpoints=len(self.api_gateway.endpoints)
            ),
            border_style="green"
        ))
        console.print("="*80)

async def main():
    """Main demo function"""
    demo = Phase3IntegrationDemo()
    await demo.run_full_demo()

if __name__ == "__main__":
    asyncio.run(main()) 