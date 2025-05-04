# src/dreamos/agents/library/agent_devlog.py
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set

from dreamos.core.agents.base_agent import BaseAgent
from dreamos.core.config import AppConfig
from dreamos.core.coordination.agent_bus import AgentBus, BaseEvent
from dreamos.core.coordination.event_types import EventType
from filelock import FileLock, Timeout

logger = logging.getLogger(__name__)

AGENT_ID = "DevlogAgent-001"


class AgentDevlog(BaseAgent):
    """An agent that listens to the AgentBus and automatically logs significant events to a daily devlog file."""

    def __init__(
        self,
        agent_id: str = AGENT_ID,
        config: Optional[AppConfig] = None,
        agent_bus: Optional[AgentBus] = None,
        **kwargs,
    ):
        super().__init__(agent_id, config, agent_bus, **kwargs)

        self.log_directory: Optional[Path] = None
        self.target_event_types: Set[EventType] = set()
        self.log_format_template: str = ""
        self.is_enabled: bool = False

        if self.config and hasattr(self.config, "devlog"):
            devlog_config = self.config.devlog
            self.is_enabled = getattr(devlog_config, "enabled", False)
            if self.is_enabled:
                try:
                    self.log_directory = Path(
                        getattr(devlog_config, "log_directory", "runtime/devlogs")
                    )
                    # Ensure relative paths are resolved based on project root
                    if not self.log_directory.is_absolute():
                        self.log_directory = (
                            self.config.paths.project_root / self.log_directory
                        )

                    event_names = getattr(devlog_config, "target_event_types", [])
                    for name in event_names:
                        try:
                            self.target_event_types.add(EventType[name])
                        except KeyError:
                            logger.warning(
                                f"[{self.agent_id}] Invalid event type '{name}' in devlog config."
                            )

                    # TODO: Load template from file or use config string
                    self.log_format_template = getattr(
                        devlog_config,
                        "log_format_template",
                        self._get_default_template(),
                    )

                    logger.info(
                        f"[{self.agent_id}] Initialized. Logging to: {self.log_directory}. Tracking events: {[et.name for et in self.target_event_types]}"
                    )
                except Exception as e:
                    logger.error(
                        f"[{self.agent_id}] Failed to process devlog config: {e}",
                        exc_info=True,
                    )
                    self.is_enabled = False  # Disable if config fails
        else:
            logger.warning(
                f"[{self.agent_id}] Devlog configuration missing or agent disabled."
            )
            self.is_enabled = False

    def _get_default_template(self) -> str:
        return (
            "\n---\n"
            "**Timestamp:** {{TIMESTAMP_UTC}}\n"
            "**Event:** {{EVENT_TYPE}}\n"
            "**Source:** {{SOURCE_ID}}\n"
            "**Details:**\n"
            "> {{DETAILS_SUMMARY}}\n"
            # Add more fields/structure as needed
        )

    async def setup(self):
        """Subscribe to target events on the AgentBus."""
        await super().setup()
        if not self.is_enabled:
            logger.info(f"[{self.agent_id}] Devlog agent is disabled, skipping setup.")
            return

        if not self.agent_bus:
            logger.error(
                f"[{self.agent_id}] AgentBus not available, cannot subscribe for devlog events."
            )
            return

        if not self.target_event_types:
            logger.warning(
                f"[{self.agent_id}] No target event types configured, devlog agent will not log anything."
            )
            return

        subscribed_count = 0
        for event_type in self.target_event_types:
            try:
                await self.agent_bus.subscribe(
                    self.handle_event, event_type=event_type.name
                )
                subscribed_count += 1
            except Exception as e:
                logger.error(
                    f"[{self.agent_id}] Failed to subscribe to event type {event_type.name}: {e}"
                )
        logger.info(
            f"[{self.agent_id}] Subscribed to {subscribed_count} event types for devlogging."
        )

    async def loop(self):
        """Main loop - primarily waits for events."""
        if not self.is_enabled:
            return  # Agent is disabled

        while not self.should_stop:
            logger.debug(f"[{self.agent_id}] Idling, waiting for events...")
            await asyncio.sleep(300)  # Check stop signal every 5 mins

    async def handle_event(self, event: BaseEvent):
        """Handle events received from the AgentBus."""
        if not self.is_enabled or event.event_type not in self.target_event_types:
            return

        logger.debug(
            f"[{self.agent_id}] Received target event: {event.event_type.name}"
        )
        try:
            log_entry = self._format_log_entry(event)
            if log_entry:
                await self._write_log_entry(log_entry)
        except Exception as e:
            logger.error(
                f"[{self.agent_id}] Failed to process event {event.event_type.name}: {e}",
                exc_info=True,
            )

    def _format_log_entry(self, event: BaseEvent) -> Optional[str]:
        """Formats the event data into a Markdown log entry string using the template."""
        # Basic placeholder implementation - needs templating engine (e.g., Jinja2) or simple replace
        timestamp = (
            event.timestamp.isoformat()
            if event.timestamp
            else datetime.now(timezone.utc).isoformat()
        )
        event_type_name = event.event_type.name
        source_id = event.source_id
        details_summary = json.dumps(event.data)  # Simple JSON dump for now

        # TODO: Implement better data extraction based on event type
        # Example for TASK_COMPLETED:
        if event.event_type == EventType.TASK_COMPLETED and isinstance(
            event.data, dict
        ):
            task_id = event.data.get("task_id", "N/A")
            agent_id = event.data.get("agent_id", "N/A")
            result = event.data.get("result", "N/A")
            details_summary = f"Task '{task_id}' completed by Agent '{agent_id}'. Result: {str(result)[:200]}..."

        # Simple string replacement (replace with Jinja2 later if complex)
        entry = self.log_format_template
        entry = entry.replace("{{TIMESTAMP_UTC}}", timestamp)
        entry = entry.replace("{{EVENT_TYPE}}", event_type_name)
        entry = entry.replace("{{SOURCE_ID}}", source_id)
        entry = entry.replace("{{DETAILS_SUMMARY}}", details_summary)

        return entry

    async def _write_log_entry(self, entry: str):
        """Appends the formatted log entry to the appropriate daily log file."""
        if not self.log_directory:
            logger.error(
                f"[{self.agent_id}] Log directory not configured, cannot write entry."
            )
            return

        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            log_filename = f"devlog_{today}.md"
            log_filepath = self.log_directory / log_filename
            lock_filepath = self.log_directory / f"{log_filename}.lock"

            # Ensure directory exists
            self.log_directory.mkdir(parents=True, exist_ok=True)

            # Use file lock for safe appending
            lock = FileLock(lock_filepath, timeout=5)
            async with asyncio.to_thread(lock.acquire):
                try:
                    with open(log_filepath, "a", encoding="utf-8") as f:
                        f.write(entry + "\n")
                    logger.debug(f"[{self.agent_id}] Appended entry to {log_filepath}")
                finally:
                    lock.release()

        except Timeout:
            logger.error(
                f"[{self.agent_id}] Failed to acquire lock for {lock_filepath} to write devlog entry."
            )
        except Exception as e:
            logger.error(
                f"[{self.agent_id}] Failed to write devlog entry: {e}", exc_info=True
            )

    async def teardown(self):
        """Clean up resources."""
        await super().teardown()
        logger.info(f"Agent {self.agent_id} tearing down.")
