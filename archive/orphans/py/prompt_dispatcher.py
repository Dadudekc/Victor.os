# src/dreamos/automation/prompt_dispatcher.py
import asyncio  # Added asyncio
import logging
import random
import uuid  # Added uuid
from typing import Any, Dict, List, Optional, Union

# Imports for AgentBus and TaskMessage (adjust paths as needed)
try:
    from dreamos.coordination.agent_bus import AgentBus
    from dreamos.core.coordination.message_patterns import (
        TaskMessage,
        TaskPriority,
        create_task_message,
    )

    AGENT_BUS_AVAILABLE = True
except ImportError as e:
    logging.error(
        f"Failed to import AgentBus or TaskMessage: {e}. Dispatcher cannot use AgentBus."  # noqa: E501
    )
    AgentBus = None
    TaskMessage = None
    TaskPriority = None
    create_task_message = None
    AGENT_BUS_AVAILABLE = False

# Attempt to import the scraper
try:
    from dreamos.services.utils.chatgpt_scraper import ChatGPTScraper

    CHATGPT_SCRAPER_AVAILABLE = True
except ImportError:
    logging.error("ChatGPTScraper not found. Dispatcher cannot scrape.")
    ChatGPTScraper = None
    CHATGPT_SCRAPER_AVAILABLE = False

logger = logging.getLogger(__name__)

# --- Configuration ---
AGENT_IDS = [f"agent_{i:02d}" for i in range(1, 9)]  # Keep for routing logic
DISPATCH_INTERVAL_SECONDS = 5
DEFAULT_PRIORITY = TaskPriority.NORMAL if TaskPriority else "NORMAL"  # Fallback
HIGH_PRIORITY_KEYWORDS = {
    "high priority",
    "important",
    "needs attention",
    "review",
    "priority",
}
CRITICAL_PRIORITY_KEYWORDS = {
    "critical",
    "urgent",
    "asap",
    "immediately",
    "blocker",
    "now",
    "emergency",
}
LOW_PRIORITY_KEYWORDS = {
    "low priority",
    "cleanup",
    "later",
    "background",
    "chore",
    "refactor",
    "someday",
}

# --- Dispatcher Functions ---


def scrape_new_prompts(
    scraper_instance: Optional[ChatGPTScraper],
) -> List[Dict[str, Any]]:
    """Calls the ChatGPTScraper to fetch new messages/prompts. Returns list of dicts {prompt: str, metadata: dict}."""  # noqa: E501
    if not scraper_instance:
        logger.warning("Scraper instance not available.")
        return []
    try:
        # Assuming fetch_new_messages returns list of strings
        new_messages = scraper_instance.fetch_new_messages()
        if new_messages:
            logger.info(f"Scraped {len(new_messages)} new message(s).")
            return [
                {"prompt": msg, "metadata": {}}
                for msg in new_messages
                if isinstance(msg, str)
            ]
        return []
    except AttributeError:
        logger.error(
            "Scraper instance missing expected method like 'fetch_new_messages'."
        )
        return []
    except Exception as e:
        logger.error(f"Error scraping ChatGPT: {e}", exc_info=True)
        return []


def determine_prompt_priority(prompt_data: Dict[str, Any]) -> Union[TaskPriority, str]:
    """Determines task priority based on metadata or prompt text keywords."""
    metadata = prompt_data.get("metadata", {})
    prompt_text = prompt_data.get("prompt", "").lower()

    # 1. Check metadata first
    meta_priority_str = str(metadata.get("priority", "")).upper()
    if TaskPriority and meta_priority_str in TaskPriority.__members__:
        logger.debug(f"Priority '{meta_priority_str}' determined from metadata.")
        return TaskPriority[meta_priority_str]

    # 2. Check keywords in prompt text
    # TODO: Add more sophisticated priority detection (keywords, metadata fields) -> Refined below  # noqa: E501
    if any(keyword in prompt_text for keyword in CRITICAL_PRIORITY_KEYWORDS):
        logger.debug("Priority CRITICAL determined from keywords.")
        return TaskPriority.CRITICAL if TaskPriority else "CRITICAL"
    if any(keyword in prompt_text for keyword in HIGH_PRIORITY_KEYWORDS):
        logger.debug("Priority HIGH determined from keywords.")
        return TaskPriority.HIGH if TaskPriority else "HIGH"
    if any(keyword in prompt_text for keyword in LOW_PRIORITY_KEYWORDS):
        logger.debug("Priority LOW determined from keywords.")
        return TaskPriority.LOW if TaskPriority else "LOW"

    # 3. Default
    logger.debug(f"Using default priority: {DEFAULT_PRIORITY}")
    return DEFAULT_PRIORITY


def route_prompt_to_agent(prompt_data: Dict[str, Any]) -> Optional[str]:
    """Determines the target agent ID based on simple routing rules."""
    prompt_text = prompt_data.get("prompt", "").lower()
    if not AGENT_IDS:
        logger.error("No AGENT_IDS defined for routing.")
        return None
    for agent_id in AGENT_IDS:
        if agent_id.replace("_", "") in prompt_text or agent_id in prompt_text:
            logger.debug(f"Routing prompt to {agent_id} based on keyword match.")
            return agent_id
    chosen_agent = random.choice(AGENT_IDS)
    logger.debug(f"Routing prompt to {chosen_agent} via random fallback.")
    return chosen_agent


async def publish_prompt_task(
    agent_bus: AgentBus,
    agent_id: str,
    prompt_data: Dict[str, Any],
    priority: Union[TaskPriority, str],
):
    """Creates a TaskMessage and publishes it to the target agent via AgentBus."""
    if not TaskMessage or not create_task_message:
        logger.error("TaskMessage components not available.")
        return
    try:
        task_id = f"prompt_task_{uuid.uuid4().hex[:8]}"
        # Define the task payload
        task_payload = {
            "task_id": task_id,
            "task_type": "process_scraped_prompt",  # Define a specific task type
            "priority": (
                priority.name
                if TaskPriority and isinstance(priority, TaskPriority)
                else priority
            ),  # Send name or string
            "input_data": {
                "prompt_text": prompt_data.get("prompt", ""),
                "source_metadata": prompt_data.get("metadata", {}),
            },
        }
        task_message = create_task_message(target_agent_id=agent_id, **task_payload)

        command_topic = f"dreamos.agent.{agent_id}.task.command"
        # Publish command to the target agent's specific command topic
        await agent_bus.publish(command_topic, task_message.to_dict())
        priority_name = (
            priority.name
            if TaskPriority and isinstance(priority, TaskPriority)
            else priority
        )
        logger.info(
            f"Published prompt task {task_id} (Priority: {priority_name}) to agent '{agent_id}' on topic '{command_topic}'"  # noqa: E501
        )

    except Exception as e:
        logger.error(
            f"Failed to publish prompt task for {agent_id}: {e}", exc_info=True
        )


async def run_dispatcher_loop(interval: int = DISPATCH_INTERVAL_SECONDS):
    """Continuously scrapes and dispatches prompts via AgentBus."""
    if not CHATGPT_SCRAPER_AVAILABLE:
        logger.critical(
            "ChatGPTScraper dependency not met. Dispatcher loop cannot start."
        )
        return
    if not AGENT_BUS_AVAILABLE:
        logger.critical(
            "AgentBus components not available. Dispatcher loop cannot start."
        )
        return

    # Initialize scraper
    try:
        scraper = ChatGPTScraper()  # Add args if needed
        logger.info("ChatGPT Scraper initialized.")
    except Exception as e:
        logger.critical(
            f"Failed to initialize ChatGPTScraper: {e}. Loop cannot start.",
            exc_info=True,
        )
        return

    # Get AgentBus instance (assuming singleton or provided externally)
    # For direct run, instantiate it here. In real system, it might be passed in.
    try:
        agent_bus = AgentBus()  # Assumes singleton or simple init
        logger.info("AgentBus instance obtained.")
    except Exception as e:
        logger.critical(
            f"Failed to get AgentBus instance: {e}. Loop cannot start.", exc_info=True
        )
        return

    logger.info(
        f"Starting Prompt Dispatcher loop (interval: {interval}s)... Press Ctrl+C to stop."  # noqa: E501
    )
    while True:
        try:
            new_prompts_data = scrape_new_prompts(scraper)
            if new_prompts_data:
                logger.info(
                    f"Dispatching {len(new_prompts_data)} scraped prompts via AgentBus..."  # noqa: E501
                )
                for prompt_data in new_prompts_data:
                    target_agent = route_prompt_to_agent(prompt_data)
                    if target_agent:
                        priority = determine_prompt_priority(prompt_data)
                        # Publish task asynchronously
                        asyncio.create_task(
                            publish_prompt_task(
                                agent_bus, target_agent, prompt_data, priority
                            )
                        )
                    else:
                        logger.warning(
                            f"Could not route prompt, discarding: {prompt_data.get('prompt', '')[:100]}..."  # noqa: E501
                        )
            else:
                logger.debug("No new prompts to dispatch this cycle.")

            await asyncio.sleep(interval)  # Use asyncio.sleep

        except KeyboardInterrupt:
            logger.info("Dispatcher loop stopped by user.")
            break
        except Exception as e:
            logger.error(
                f"Error in dispatcher loop: {e}. Pausing before retry...", exc_info=True
            )
            await asyncio.sleep(interval * 2)  # Use asyncio.sleep


async def main():  # Make main async
    log_format = "%(asctime)s - %(levelname)-8s - %(name)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format)
    await run_dispatcher_loop()


if __name__ == "__main__":
    asyncio.run(main())  # Run the async main
