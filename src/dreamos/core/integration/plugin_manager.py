"""
Victor.os Plugin Architecture System
Phase 3: Integration Ecosystem - Plugin architecture and third-party integrations
"""

import asyncio
import json
import time
import importlib
import inspect
from typing import Dict, List, Optional, Any, Type, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import structlog
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import yaml

console = Console()
logger = structlog.get_logger("plugin_manager")

class PluginType(Enum):
    """Plugin types for different integration categories"""
    API_INTEGRATION = "api_integration"
    AUTOMATION_TOOL = "automation_tool"
    DATA_PROCESSOR = "data_processor"
    UI_EXTENSION = "ui_extension"
    ANALYTICS = "analytics"
    SECURITY = "security"
    CUSTOM_AGENT = "custom_agent"

class PluginStatus(Enum):
    """Plugin status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    LOADING = "loading"
    DISABLED = "disabled"

@dataclass
class PluginInfo:
    """Plugin information and metadata"""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    entry_point: str
    config_schema: Dict[str, Any]
    dependencies: List[str]
    requirements: List[str]
    status: PluginStatus
    enabled: bool
    load_time: float
    error_message: Optional[str] = None

@dataclass
class PluginConfig:
    """Plugin configuration"""
    plugin_id: str
    config_data: Dict[str, Any]
    enabled: bool
    auto_start: bool
    priority: int

class PluginManager:
    """Plugin management system for Victor.os"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.plugins: Dict[str, Any] = {}
        self.plugin_info: Dict[str, PluginInfo] = {}
        self.plugin_configs: Dict[str, PluginConfig] = {}
        self.plugin_hooks: Dict[str, List[Callable]] = {}
        
        # Setup plugin directories
        self.plugin_dir = Path("plugins")
        self.plugin_dir.mkdir(exist_ok=True)
        
        # Plugin registry
        self.plugin_registry: Dict[str, Type] = {}
        
        # Initialize plugin system
        self._setup_plugin_system()
        
        # Start background monitoring
        self._start_background_monitoring()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for plugin manager"""
        return {
            "auto_discover_plugins": True,
            "plugin_scan_interval": 300,  # 5 minutes
            "max_plugins": 50,
            "plugin_timeout": 30,  # seconds
            "enable_hot_reload": True,
            "plugin_validation": True,
            "sandbox_plugins": True,
            "plugin_logging": True,
            "default_plugin_config": {
                "enabled": True,
                "auto_start": False,
                "priority": 5,
            }
        }
    
    def _setup_plugin_system(self):
        """Setup plugin system infrastructure"""
        # Create plugin directories
        for plugin_type in PluginType:
            type_dir = self.plugin_dir / plugin_type.value
            type_dir.mkdir(exist_ok=True)
        
        # Create plugin registry file
        self.registry_file = self.plugin_dir / "registry.json"
        self._load_plugin_registry()
        
        # Setup plugin hooks
        self._setup_plugin_hooks()
    
    def _setup_plugin_hooks(self):
        """Setup plugin hook system"""
        self.plugin_hooks = {
            "pre_agent_start": [],
            "post_agent_start": [],
            "pre_task_execution": [],
            "post_task_execution": [],
            "pre_data_processing": [],
            "post_data_processing": [],
            "system_startup": [],
            "system_shutdown": [],
            "error_handling": [],
            "metrics_collection": [],
        }
    
    def _load_plugin_registry(self):
        """Load plugin registry from disk"""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, 'r') as f:
                    registry_data = json.load(f)
                    self.plugin_registry = registry_data
            else:
                self.plugin_registry = {}
        except Exception as e:
            logger.error("Failed to load plugin registry", error=str(e))
            self.plugin_registry = {}
    
    def _save_plugin_registry(self):
        """Save plugin registry to disk"""
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(self.plugin_registry, f, indent=2)
        except Exception as e:
            logger.error("Failed to save plugin registry", error=str(e))
    
    async def discover_plugins(self) -> List[str]:
        """Discover available plugins in plugin directory"""
        discovered_plugins = []
        
        try:
            for plugin_type_dir in self.plugin_dir.iterdir():
                if plugin_type_dir.is_dir() and plugin_type_dir.name in [pt.value for pt in PluginType]:
                    for plugin_dir in plugin_type_dir.iterdir():
                        if plugin_dir.is_dir():
                            plugin_id = f"{plugin_type_dir.name}.{plugin_dir.name}"
                            
                            # Check for plugin manifest
                            manifest_file = plugin_dir / "manifest.yaml"
                            if manifest_file.exists():
                                try:
                                    with open(manifest_file, 'r') as f:
                                        manifest = yaml.safe_load(f)
                                    
                                    # Validate manifest
                                    if self._validate_plugin_manifest(manifest):
                                        discovered_plugins.append(plugin_id)
                                        await self._register_plugin(plugin_id, manifest, plugin_dir)
                                    
                                except Exception as e:
                                    logger.error("Failed to load plugin manifest", 
                                                plugin_id=plugin_id,
                                                error=str(e))
            
            logger.info("Plugin discovery completed", 
                       discovered_count=len(discovered_plugins))
            
        except Exception as e:
            logger.error("Plugin discovery failed", error=str(e))
        
        return discovered_plugins
    
    def _validate_plugin_manifest(self, manifest: Dict[str, Any]) -> bool:
        """Validate plugin manifest"""
        required_fields = ["name", "version", "description", "author", "entry_point"]
        
        for field in required_fields:
            if field not in manifest:
                return False
        
        # Validate version format
        if not self._is_valid_version(manifest["version"]):
            return False
        
        return True
    
    def _is_valid_version(self, version: str) -> bool:
        """Check if version string is valid"""
        try:
            parts = version.split('.')
            if len(parts) != 3:
                return False
            
            for part in parts:
                int(part)
            
            return True
        except ValueError:
            return False
    
    async def _register_plugin(self, plugin_id: str, manifest: Dict[str, Any], plugin_dir: Path):
        """Register plugin in the system"""
        try:
            plugin_info = PluginInfo(
                name=manifest["name"],
                version=manifest["version"],
                description=manifest["description"],
                author=manifest["author"],
                plugin_type=PluginType(manifest.get("type", "api_integration")),
                entry_point=manifest["entry_point"],
                config_schema=manifest.get("config_schema", {}),
                dependencies=manifest.get("dependencies", []),
                requirements=manifest.get("requirements", []),
                status=PluginStatus.INACTIVE,
                enabled=False,
                load_time=0.0
            )
            
            self.plugin_info[plugin_id] = plugin_info
            
            # Create default config
            default_config = self.config["default_plugin_config"].copy()
            plugin_config = PluginConfig(
                plugin_id=plugin_id,
                config_data=manifest.get("default_config", {}),
                enabled=default_config["enabled"],
                auto_start=default_config["auto_start"],
                priority=default_config["priority"]
            )
            
            self.plugin_configs[plugin_id] = plugin_config
            
            logger.info("Plugin registered", 
                       plugin_id=plugin_id,
                       name=plugin_info.name,
                       version=plugin_info.version)
            
        except Exception as e:
            logger.error("Failed to register plugin", 
                        plugin_id=plugin_id,
                        error=str(e))
    
    async def load_plugin(self, plugin_id: str) -> bool:
        """Load a specific plugin"""
        try:
            if plugin_id not in self.plugin_info:
                logger.error("Plugin not found", plugin_id=plugin_id)
                return False
            
            plugin_info = self.plugin_info[plugin_id]
            plugin_config = self.plugin_configs[plugin_id]
            
            # Update status
            plugin_info.status = PluginStatus.LOADING
            
            # Check dependencies
            if not await self._check_plugin_dependencies(plugin_id):
                plugin_info.status = PluginStatus.ERROR
                plugin_info.error_message = "Dependency check failed"
                return False
            
            # Load plugin module
            start_time = time.time()
            plugin_module = await self._load_plugin_module(plugin_id, plugin_info)
            
            if not plugin_module:
                plugin_info.status = PluginStatus.ERROR
                plugin_info.error_message = "Module loading failed"
                return False
            
            # Initialize plugin
            plugin_instance = await self._initialize_plugin(plugin_id, plugin_module, plugin_config)
            
            if not plugin_instance:
                plugin_info.status = PluginStatus.ERROR
                plugin_info.error_message = "Plugin initialization failed"
                return False
            
            # Store plugin instance
            self.plugins[plugin_id] = plugin_instance
            
            # Update status
            plugin_info.status = PluginStatus.ACTIVE
            plugin_info.enabled = plugin_config.enabled
            plugin_info.load_time = time.time() - start_time
            
            # Register plugin hooks
            await self._register_plugin_hooks(plugin_id, plugin_instance)
            
            logger.info("Plugin loaded successfully", 
                       plugin_id=plugin_id,
                       load_time=f"{plugin_info.load_time:.2f}s")
            
            return True
            
        except Exception as e:
            logger.error("Failed to load plugin", 
                        plugin_id=plugin_id,
                        error=str(e))
            
            if plugin_id in self.plugin_info:
                self.plugin_info[plugin_id].status = PluginStatus.ERROR
                self.plugin_info[plugin_id].error_message = str(e)
            
            return False
    
    async def _check_plugin_dependencies(self, plugin_id: str) -> bool:
        """Check if plugin dependencies are satisfied"""
        plugin_info = self.plugin_info[plugin_id]
        
        for dependency in plugin_info.dependencies:
            if dependency not in self.plugins:
                logger.warning("Plugin dependency not loaded", 
                              plugin_id=plugin_id,
                              dependency=dependency)
                return False
        
        return True
    
    async def _load_plugin_module(self, plugin_id: str, plugin_info: PluginInfo) -> Optional[Any]:
        """Load plugin module"""
        try:
            # Construct module path
            plugin_type = plugin_info.plugin_type.value
            plugin_name = plugin_id.split('.')[-1]
            module_path = f"plugins.{plugin_type}.{plugin_name}.{plugin_info.entry_point}"
            
            # Import module
            module = importlib.import_module(module_path)
            
            return module
            
        except Exception as e:
            logger.error("Failed to load plugin module", 
                        plugin_id=plugin_id,
                        error=str(e))
            return None
    
    async def _initialize_plugin(self, plugin_id: str, module: Any, config: PluginConfig) -> Optional[Any]:
        """Initialize plugin instance"""
        try:
            # Look for plugin class
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and hasattr(obj, 'initialize'):
                    plugin_class = obj
                    break
            
            if not plugin_class:
                logger.error("No plugin class found", plugin_id=plugin_id)
                return None
            
            # Create plugin instance
            plugin_instance = plugin_class()
            
            # Initialize plugin
            if hasattr(plugin_instance, 'initialize'):
                await plugin_instance.initialize(config.config_data)
            
            return plugin_instance
            
        except Exception as e:
            logger.error("Failed to initialize plugin", 
                        plugin_id=plugin_id,
                        error=str(e))
            return None
    
    async def _register_plugin_hooks(self, plugin_id: str, plugin_instance: Any):
        """Register plugin hooks"""
        try:
            for hook_name in self.plugin_hooks.keys():
                if hasattr(plugin_instance, hook_name):
                    hook_method = getattr(plugin_instance, hook_name)
                    if callable(hook_method):
                        self.plugin_hooks[hook_name].append(hook_method)
                        logger.debug("Plugin hook registered", 
                                   plugin_id=plugin_id,
                                   hook=hook_name)
            
        except Exception as e:
            logger.error("Failed to register plugin hooks", 
                        plugin_id=plugin_id,
                        error=str(e))
    
    async def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a specific plugin"""
        try:
            if plugin_id not in self.plugins:
                logger.warning("Plugin not loaded", plugin_id=plugin_id)
                return False
            
            plugin_instance = self.plugins[plugin_id]
            
            # Cleanup plugin
            if hasattr(plugin_instance, 'cleanup'):
                await plugin_instance.cleanup()
            
            # Remove from plugins
            del self.plugins[plugin_id]
            
            # Update status
            if plugin_id in self.plugin_info:
                self.plugin_info[plugin_id].status = PluginStatus.INACTIVE
                self.plugin_info[plugin_id].enabled = False
            
            # Remove hooks
            await self._remove_plugin_hooks(plugin_id)
            
            logger.info("Plugin unloaded", plugin_id=plugin_id)
            return True
            
        except Exception as e:
            logger.error("Failed to unload plugin", 
                        plugin_id=plugin_id,
                        error=str(e))
            return False
    
    async def _remove_plugin_hooks(self, plugin_id: str):
        """Remove plugin hooks"""
        # This is a simplified implementation
        # In a real system, you'd track which hooks belong to which plugin
        pass
    
    async def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a plugin"""
        try:
            if plugin_id not in self.plugin_configs:
                logger.error("Plugin config not found", plugin_id=plugin_id)
                return False
            
            plugin_config = self.plugin_configs[plugin_id]
            plugin_config.enabled = True
            
            # Load plugin if not already loaded
            if plugin_id not in self.plugins:
                success = await self.load_plugin(plugin_id)
                if not success:
                    plugin_config.enabled = False
                    return False
            
            # Update plugin info
            if plugin_id in self.plugin_info:
                self.plugin_info[plugin_id].enabled = True
            
            logger.info("Plugin enabled", plugin_id=plugin_id)
            return True
            
        except Exception as e:
            logger.error("Failed to enable plugin", 
                        plugin_id=plugin_id,
                        error=str(e))
            return False
    
    async def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin"""
        try:
            if plugin_id not in self.plugin_configs:
                logger.error("Plugin config not found", plugin_id=plugin_id)
                return False
            
            plugin_config = self.plugin_configs[plugin_id]
            plugin_config.enabled = False
            
            # Update plugin info
            if plugin_id in self.plugin_info:
                self.plugin_info[plugin_id].enabled = False
            
            logger.info("Plugin disabled", plugin_id=plugin_id)
            return True
            
        except Exception as e:
            logger.error("Failed to disable plugin", 
                        plugin_id=plugin_id,
                        error=str(e))
            return False
    
    async def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Execute plugin hooks"""
        results = []
        
        if hook_name not in self.plugin_hooks:
            logger.warning("Hook not found", hook_name=hook_name)
            return results
        
        for hook in self.plugin_hooks[hook_name]:
            try:
                if asyncio.iscoroutinefunction(hook):
                    result = await hook(*args, **kwargs)
                else:
                    result = hook(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error("Hook execution failed", 
                            hook_name=hook_name,
                            error=str(e))
        
        return results
    
    async def get_plugin_status(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed plugin status"""
        if plugin_id not in self.plugin_info:
            return None
        
        plugin_info = self.plugin_info[plugin_id]
        plugin_config = self.plugin_configs.get(plugin_id)
        
        return {
            "plugin_id": plugin_id,
            "info": asdict(plugin_info),
            "config": asdict(plugin_config) if plugin_config else None,
            "loaded": plugin_id in self.plugins,
            "hooks_registered": len([h for h in self.plugin_hooks.values() if h])
        }
    
    async def get_all_plugins_status(self) -> Dict[str, Any]:
        """Get status of all plugins"""
        return {
            "total_plugins": len(self.plugin_info),
            "loaded_plugins": len(self.plugins),
            "enabled_plugins": len([p for p in self.plugin_info.values() if p.enabled]),
            "plugins_by_type": self._group_plugins_by_type(),
            "plugins_by_status": self._group_plugins_by_status(),
            "plugin_list": [
                await self.get_plugin_status(plugin_id)
                for plugin_id in self.plugin_info.keys()
            ]
        }
    
    def _group_plugins_by_type(self) -> Dict[str, int]:
        """Group plugins by type"""
        grouped = {}
        for plugin_info in self.plugin_info.values():
            plugin_type = plugin_info.plugin_type.value
            grouped[plugin_type] = grouped.get(plugin_type, 0) + 1
        return grouped
    
    def _group_plugins_by_status(self) -> Dict[str, int]:
        """Group plugins by status"""
        grouped = {}
        for plugin_info in self.plugin_info.values():
            status = plugin_info.status.value
            grouped[status] = grouped.get(status, 0) + 1
        return grouped
    
    async def _start_background_monitoring(self):
        """Start background plugin monitoring"""
        if self.config["auto_discover_plugins"]:
            asyncio.create_task(self._plugin_monitoring_loop())
    
    async def _plugin_monitoring_loop(self):
        """Background plugin monitoring loop"""
        while True:
            try:
                await self.discover_plugins()
                await asyncio.sleep(self.config["plugin_scan_interval"])
            except Exception as e:
                logger.error("Plugin monitoring error", error=str(e))
                await asyncio.sleep(60)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get plugin manager system status"""
        return {
            "total_plugins": len(self.plugin_info),
            "loaded_plugins": len(self.plugins),
            "enabled_plugins": len([p for p in self.plugin_info.values() if p.enabled]),
            "plugin_types": [pt.value for pt in PluginType],
            "hooks_available": list(self.plugin_hooks.keys()),
            "auto_discovery": self.config["auto_discover_plugins"],
            "hot_reload": self.config["enable_hot_reload"],
            "plugin_timeout": self.config["plugin_timeout"],
        } 