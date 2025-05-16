"""
Core runner for agent bootstrap process.

Implements the standardized messaging system and directory structure as documented in
docs/agent_system/agent_directory_structure.md
"""

import asyncio
import logging
from typing import List

from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.utils.gui.injector import CursorInjector
from dreamos.utils.gui.retriever import ResponseRetriever

from .config import AgentConfig
from .messaging import MessageFormat, create_seed_inbox, process_message, send_message
from .validation import validate_all_files

log = logging.getLogger(__name__)


class AgentBootstrapRunner:
    """Core runner for agent bootstrap process."""

    def __init__(self, config: AgentConfig):
        """
        Initialize the runner.

        Args:
            config: Agent configuration
        """
        self.config = config
        self.agent_bus = AgentBus()
        self.injector = CursorInjector()
        self.retriever = ResponseRetriever()

        # Set up logging
        self.setup_logging()

        # Ensure directory structure exists
        self.ensure_directories()

    def setup_logging(self):
        """Configure agent-specific logging."""
        log_file = self.config.devlog_path
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        log.addHandler(file_handler)

    def ensure_directories(self):
        """Ensure all required directories exist."""
        for dir_path in [
            self.config.inbox_dir,
            self.config.outbox_dir,
            self.config.processed_dir,
            self.config.state_dir,
            self.config.workspace_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    async def process_inbox(self) -> List[MessageFormat]:
        """
        Process all messages in the inbox.

        Returns:
            List[MessageFormat]: List of processed messages
        """
        processed_messages = []

        # Process all .json files in inbox
        for message_path in self.config.inbox_dir.glob("*.json"):
            try:
                # Read and parse message
                with message_path.open("r", encoding="utf-8") as f:
                    message_data = json.loads(f)
                message = MessageFormat.from_dict(message_data)

                # Verify message is for this agent
                if message.recipient_agent_id != self.config.agent_id:
                    log.warning(
                        f"Found message for {message.recipient_agent_id} in {self.config.agent_id}'s inbox"
                    )
                    continue

                # Process message
                if process_message(self.config, message_path):
                    processed_messages.append(message)
                    log.info(f"Processed message {message.message_id}")
                else:
                    log.error(f"Failed to process message {message.message_id}")

            except Exception as e:
                log.error(f"Error processing message {message_path}: {e}")

        return processed_messages

    async def send_response(
        self, original_message: MessageFormat, response_body: str
    ) -> bool:
        """
        Send a response message.

        Args:
            original_message: Message being responded to
            response_body: Response content

        Returns:
            bool: True if response was sent successfully
        """
        return send_message(
            sender_config=self.config,
            recipient_id=original_message.sender_agent_id,
            subject=f"Re: {original_message.subject}",
            message_type="RESPONSE",
            body=response_body,
            metadata={"in_reply_to": original_message.message_id},
        )

    async def run(self):
        """Run the agent bootstrap process."""
        try:
            # Validate files and directories
            validation = validate_all_files(log, self.config)
            if not validation.passed:
                log.error(f"Validation failed: {validation.error}")
                return

            # Create seed inbox if needed
            create_seed_inbox(log, self.config)

            # Main loop
            while True:
                try:
                    # Process inbox messages
                    messages = await self.process_inbox()

                    # Handle each message
                    for message in messages:
                        # TODO: Implement message handling logic
                        pass

                    # Wait before next check
                    await asyncio.sleep(self.config.loop_delay_sec)

                except Exception as e:
                    log.error(f"Error in main loop: {e}")
                    await asyncio.sleep(self.config.retry_delay_sec)

        except Exception as e:
            log.error(f"Fatal error in runner: {e}")
            raise


async def agent_loop(config: AgentConfig):
    """
    Main entry point for agent bootstrap process.

    Args:
        config: Agent configuration
    """
    runner = AgentBootstrapRunner(config)
    await runner.run()
