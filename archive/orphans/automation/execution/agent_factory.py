"""Factory for creating and initializing agent instances based on configuration."""

import importlib
import logging
from typing import Dict

# Core dependencies needed by agents
from dreamos.core.agents.base_agent import BaseAgent
from dreamos.core.config import AgentActivationConfig, AppConfig
from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.core.coordination.project_board_manager import ProjectBoardManager
from dreamos.core.db.sqlite_adapter import SQLiteAdapter

logger = logging.getLogger(__name__)


class AgentFactoryError(Exception):
    """Custom exception for agent factory errors."""

    pass


class AgentFactory:
    """Handles the dynamic loading and instantiation of agents."""

    def __init__(
        self,
        config: AppConfig,
        agent_bus: AgentBus,
        pbm: ProjectBoardManager,
        adapter: SQLiteAdapter,
    ):
        """Initialize the factory with dependencies required by agents."""
        self.config = config
        self.agent_bus = agent_bus
        self.pbm = pbm
        self.adapter = adapter
        logger.info("AgentFactory initialized.")

    def create_active_agents(self) -> Dict[str, BaseAgent]:
        """Loads and instantiates agents defined in AppConfig.swarm.active_agents."""
        created_agents: Dict[str, BaseAgent] = {}
        if not hasattr(self.config, "swarm") or not hasattr(
            self.config.swarm, "active_agents"
        ):
            logger.warning(
                "AppConfig has no swarm.active_agents configured. No agents loaded by factory."
            )
            return created_agents

        active_agent_configs: list[AgentActivationConfig] = (
            self.config.swarm.active_agents
        )

        if not active_agent_configs:
            logger.warning(
                "AppConfig.swarm.active_agents list is empty. No agents loaded by factory."
            )
            return created_agents

        logger.info(
            f"Attempting to load {len(active_agent_configs)} configured active agents..."
        )

        for agent_config in active_agent_configs:
            agent_id = None
            try:
                logger.debug(
                    f"Processing agent config: Module={agent_config.agent_module}, Class={agent_config.agent_class}, Pattern={agent_config.worker_id_pattern}, Override={agent_config.agent_id_override}"
                )

                # Determine Agent ID (Simplified: uses override or class name for now)
                # A more robust approach might map worker patterns to specific instance IDs.
                # For simplicity here, we assume one instance per activation config for now.
                # If an override is given, use it.
                if agent_config.agent_id_override:
                    agent_id = agent_config.agent_id_override
                else:
                    # Fallback to class name or derive from module if no override
                    # Using class name might lead to conflicts if multiple instances of the same class are needed without overrides.
                    agent_id = agent_config.agent_class  # Simple fallback
                    logger.warning(
                        f"No agent_id_override for {agent_config.agent_class}, using class name '{agent_id}' as ID. Ensure uniqueness if multiple instances are intended."
                    )

                if agent_id in created_agents:
                    logger.error(
                        f"Duplicate agent ID detected: '{agent_id}'. Skipping configuration for {agent_config.agent_module}.{agent_config.agent_class}. Check agent_id_override in config."
                    )
                    continue

                # Dynamically import the module
                try:
                    module_path = agent_config.agent_module
                    agent_module = importlib.import_module(module_path)
                    logger.debug(f"Successfully imported module: {module_path}")
                except ImportError as e:
                    raise AgentFactoryError(
                        f"Failed to import agent module '{module_path}': {e}"
                    ) from e

                # Get the class from the module
                try:
                    AgentClass = getattr(agent_module, agent_config.agent_class)
                    logger.debug(
                        f"Successfully found class '{agent_config.agent_class}' in module {module_path}"
                    )
                except AttributeError as e:
                    raise AgentFactoryError(
                        f"Class '{agent_config.agent_class}' not found in module '{module_path}': {e}"
                    ) from e

                # Ensure it's a subclass of BaseAgent (optional but good practice)
                if not issubclass(AgentClass, BaseAgent):
                    raise AgentFactoryError(
                        f"Class '{AgentClass.__name__}' is not a subclass of BaseAgent."
                    )

                # Instantiate the agent, passing required dependencies
                # Note: Assumes agent constructors primarily need these core dependencies.
                # Specific agents might need additional config subsections passed.
                logger.info(
                    f"Instantiating agent: ID='{agent_id}', Class='{AgentClass.__name__}'"
                )
                agent_instance = AgentClass(
                    agent_id=agent_id,
                    config=self.config,  # Pass the full config
                    agent_bus=self.agent_bus,  # Pass the bus instance
                    pbm=self.pbm,  # Pass the ProjectBoardManager instance
                    # adapter=self.adapter,  # BaseAgent doesn't directly take adapter, PBM uses it.
                    # Add if specific agents need it directly.
                )

                created_agents[agent_id] = agent_instance
                logger.info(f"Successfully created and registered agent: {agent_id}")

            except AgentFactoryError as afe:
                logger.error(
                    f"Failed to create agent from config {agent_config}: {afe}"
                )
                # Optionally continue to try loading other agents
            except Exception as e:
                logger.error(
                    f"Unexpected error creating agent (ID: {agent_id or 'unknown'}) from config {agent_config}: {e}",
                    exc_info=True,
                )
                # Optionally continue

        logger.info(
            f"AgentFactory finished loading. Created {len(created_agents)} agents."
        )
        return created_agents
