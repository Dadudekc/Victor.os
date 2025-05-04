# src/dreamos/agents/library/agent_lore_writer.py
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from dreamos.core.agents.base_agent import BaseAgent
from dreamos.core.agents.capabilities.library.narrative_generate import (
    NARRATIVE_GENERATE_CAPABILITY_ID,
    NARRATIVE_GENERATE_CAPABILITY_INFO,
    NarrativeGenerateInput,
    narrative_generate_episode_capability,
)
from dreamos.core.agents.capabilities.schema import AgentCapability
from dreamos.core.config import AppConfig
from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.core.db.sqlite_adapter import SQLiteAdapter
from dreamos.core.llm.client import get_llm_client
from dreamos.core.narrative.lore_parser import ContextWindow, gather_narrative_context
from dreamos.core.tasks.nexus.capability_registry import CapabilityRegistry

logger = logging.getLogger(__name__)

AGENT_ID = "LoreWriter-001"


class AgentLoreWriter(BaseAgent):
    """An agent dedicated to observing project events and generating narrative lore or devlogs."""

    def __init__(
        self,
        agent_id: str = AGENT_ID,
        config: Optional[AppConfig] = None,
        agent_bus: Optional[AgentBus] = None,
        db_adapter: Optional[SQLiteAdapter] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
        **kwargs,
    ):
        super().__init__(agent_id, config, agent_bus, **kwargs)
        self.db_adapter = db_adapter
        self.registry = capability_registry
        try:
            self.llm_client = get_llm_client()
        except Exception as e:
            logger.error(
                f"[{self.agent_id}] Failed to initialize LLM client: {e}", exc_info=True
            )
            self.llm_client = None

        if not self.db_adapter:
            logger.error(
                f"[{self.agent_id}] DB Adapter not provided during initialization!"
            )
        if not self.registry:
            logger.error(
                f"[{self.agent_id}] Capability Registry not provided during initialization!"
            )

        logger.info(f"Agent {self.agent_id} initialized.")

    async def setup(self):
        """Perform async setup, like subscribing to bus events and registering capabilities."""
        await super().setup()
        if self.registry:
            try:
                capability = AgentCapability(
                    agent_id=self.agent_id,
                    capability_id=NARRATIVE_GENERATE_CAPABILITY_ID,
                    capability_name=NARRATIVE_GENERATE_CAPABILITY_INFO.get(
                        "capability_name", "Narrative Episode Generator"
                    ),
                    description=NARRATIVE_GENERATE_CAPABILITY_INFO.get(
                        "description", "Generates narrative episodes."
                    ),
                    parameters_schema=NARRATIVE_GENERATE_CAPABILITY_INFO.get(
                        "parameters", {}
                    ),
                    handler_info={
                        "type": "internal_method",
                        "method_name": "execute_narrative_generation",
                    },
                    tags=["narrative", "llm", "reporting", "lore", "dreamscape"],
                )
                if self.registry.register_capability(capability):
                    logger.info(
                        f"[{self.agent_id}] Successfully registered capability: {capability.capability_id}"
                    )
                else:
                    logger.error(
                        f"[{self.agent_id}] Failed to register capability: {capability.capability_id}"
                    )
            except Exception as e:
                logger.error(
                    f"[{self.agent_id}] Error registering capability {NARRATIVE_GENERATE_CAPABILITY_ID}: {e}",
                    exc_info=True,
                )
        else:
            logger.error(
                f"[{self.agent_id}] Capability registry not available, cannot register capabilities."
            )

        if self.agent_bus:
            try:
                await self.agent_bus.subscribe(
                    self.handle_event, event_type="TASK_COMPLETED"
                )
                logger.info(f"[{self.agent_id}] Subscribed to TASK_COMPLETED events.")
            except Exception as e:
                logger.error(
                    f"[{self.agent_id}] Failed to subscribe to AgentBus events: {e}",
                    exc_info=True,
                )
        else:
            logger.warning(
                f"[{self.agent_id}] AgentBus not available, cannot subscribe to events."
            )

        logger.info(f"Agent {self.agent_id} setup complete.")

    async def loop(self):
        """Main agent loop. Primarily event-driven via handle_event."""
        while not self.should_stop:
            logger.debug(
                f"Agent {self.agent_id} loop iteration (waiting for events/stop signal)."
            )
            await asyncio.sleep(60)

    async def handle_event(self, event_type: str, event_data: Dict[str, Any]):
        """Handle events received from the AgentBus."""
        logger.info(f"Agent {self.agent_id} received event: {event_type}")
        if event_type == "TASK_COMPLETED":
            task_id = event_data.get("task_id")
            if task_id:
                await self.generate_lore_for_task(task_id)
            else:
                logger.warning(
                    f"[{self.agent_id}] Received TASK_COMPLETED event without task_id."
                )
        # Add handling for other relevant events (e.g., COMMIT_DETECTED)

    async def generate_lore_for_task(self, task_id: str):
        """Generate a lore snippet or devlog entry for a completed task."""
        logger.info(f"[{self.agent_id}] Generating lore for completed task: {task_id}")

        if not self.db_adapter:
            logger.error(
                f"[{self.agent_id}] DB adapter not available, cannot fetch task details for {task_id}."
            )
            return
        if not self.llm_client:
            logger.error(
                f"[{self.agent_id}] LLM client not available, cannot generate lore for {task_id}."
            )
            return
        if not self.config:
            logger.error(
                f"[{self.agent_id}] Config not available, cannot determine paths for {task_id}."
            )
            return

        try:
            task_details = self.db_adapter.get_task(task_id)
            if not task_details:
                logger.warning(
                    f"[{self.agent_id}] Could not retrieve details for task {task_id}."
                )
                return

            context_window = ContextWindow(task_ids=[task_id])
            repo_path = Path(self.config.paths.project_root)
            log_dir = Path(self.config.paths.logs)
            report_dir = Path(self.config.reporting.captain_log_dir)
            lore_repo_dir = Path(self.config.narrative.lore_repository_dir)

            context_data = gather_narrative_context(
                context_window=context_window,
                adapter=self.db_adapter,
                repo_path=repo_path,
                log_dir=log_dir,
                report_dir=report_dir,
                lore_dir=lore_repo_dir,
            )

            context_summary = f"Task Details: {task_details.get('description')}\nResult: {task_details.get('result_summary')}"
            if context_data.get("commits"):
                context_summary += (
                    f"\nRelated Commits:\n{context_data['commits'][:500]}..."
                )

            prompt = (
                f"Generate a short narrative devlog entry or lore snippet about the completion of task {task_id} (Agent: {task_details.get('agent_id')}).\n"
                f"Context:\n{context_summary}\n\n"
                f"Focus on the significance, challenges, or interesting outcomes. Keep it concise (1-3 paragraphs)."
            )

            generated_text = self.llm_client.generate(prompt, max_tokens=300)
            logger.info(
                f"[{self.agent_id}] Generated lore snippet for task {task_id}: {generated_text[:100]}..."
            )

            devlog_dir = lore_repo_dir / "devlogs"
            devlog_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            lore_filename = f"devlog_{timestamp}_task_{task_id}.md"
            lore_filepath = devlog_dir / lore_filename
            lore_filepath.write_text(generated_text, encoding="utf-8")
            logger.info(f"[{self.agent_id}] Saved lore snippet to: {lore_filepath}")

        except Exception as e:
            logger.error(
                f"[{self.agent_id}] Error generating/saving lore for task {task_id}: {e}",
                exc_info=True,
            )

    async def generate_periodic_summary(self):
        """Generate a summary based on recent activity (e.g., last N tasks/commits)."""
        logger.info(f"[{self.agent_id}] Generating periodic lore summary...")
        pass

    async def execute_narrative_generation(
        self, input_data: NarrativeGenerateInput
    ) -> Dict:
        """Executes the narrative generation based on input data."""
        logger.info(
            f"[{self.agent_id}] Received request to execute narrative generation: {input_data.get('trigger_event_summary')}"
        )
        if not self.db_adapter or not self.config:
            logger.error(
                "Cannot execute narrative generation: DB adapter or config missing."
            )
            return {"episode_file_path": None, "error": "Agent dependencies missing."}

        result = narrative_generate_episode_capability(
            input_data=input_data, adapter=self.db_adapter, config=self.config
        )
        return result

    async def teardown(self):
        """Clean up resources before shutdown."""
        await super().teardown()
        logger.info(f"Agent {self.agent_id} tearing down.")


# Example of how this agent might be instantiated (in SwarmController or similar)
# lore_writer = AgentLoreWriter(
#     config=app_config,
#     agent_bus=agent_bus_instance,
#     db_adapter=db_adapter_instance
# )
