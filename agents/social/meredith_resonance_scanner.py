import logging
import time
from threading import Thread, Lock, Event as ThreadingEvent
from queue import Queue, Empty
from typing import Optional, Dict, Any

# Canonical imports
from core.coordination.agent_bus import AgentBus
from core.coordination.dispatcher import Event, EventType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AGENT_NAME_DEFAULT = "MeredithResonanceScanner"

class MeredithResonanceScanner:
    """
    Agent responsible for scanning social media platforms for mentions
    related to 'Meredith' and analyzing their resonance or sentiment.
    (Refactored to use Event protocol)
    """
    def __init__(self, agent_name: str = AGENT_NAME_DEFAULT, bus: AgentBus = None, config: dict = None):
        """
        Initializes the MeredithResonanceScanner agent.

        Args:
            agent_name (str): The unique name of this agent.
            bus (AgentBus): The agent bus instance for communication.
            config (dict, optional): Configuration parameters for the agent. Defaults to None.
        """
        if bus is None:
            raise ValueError("AgentBus instance is required.")

        self.agent_name = agent_name
        self.bus = bus
        self.config = config or {}
        self.is_running = False
        self.thread = None
        self.stop_event = ThreadingEvent()
        self.lock = Lock()

        # Example capabilities - adjust as needed
        self.capabilities = ["social_media_scan", "sentiment_analysis", "meredith_topic"]

        # Register with the AgentBus
        try:
            self.bus.register_agent(self.agent_name, capabilities=self.capabilities)
            logger.info(f"{self.agent_name} registered with capabilities: {self.capabilities}")
        except Exception as e:
             logger.error(f"Failed to register agent {self.agent_name}: {e}")
             raise

        # Register a handler specifically for SCAN_MEREDITH_RESONANCE events
        try:
            self.bus.register_handler(EventType.SCAN_MEREDITH_RESONANCE, self.handle_event)
            logger.info(f"Registered handler for EventType: {EventType.SCAN_MEREDITH_RESONANCE.name}")
        except Exception as e:
            logger.error(f"Failed to register handler for {EventType.SCAN_MEREDITH_RESONANCE.name}: {e}")

    def start(self):
        """Starts the agent's background activity if any."""
        with self.lock:
            if not self.is_running:
                self.is_running = True
                self.stop_event.clear()
                logger.info(f"{self.agent_name} started.")

    def stop(self):
        """Stops the agent's background activity."""
        with self.lock:
            if self.is_running:
                self.is_running = False
                self.stop_event.set()
                logger.info(f"{self.agent_name} stopped.")

    def handle_event(self, event: Event):
        """Handles incoming events from the AgentBus."""
        logger.info(f"{self.agent_name} received event: {event.type.name} (ID: {event.id}) from {event.source_id}")

        if event.type == EventType.SCAN_MEREDITH_RESONANCE:
            self._perform_scan(event)
        else:
            logger.warning(f"Received unexpected event type {event.type.name}. Ignoring.")

    # --- Core Logic Methods ---
    def _perform_scan(self, trigger_event: Event):
        """Placeholder for the core scanning logic. Triggered by an event."""
        parameters = trigger_event.data
        query = parameters.get("query", "Meredith")
        logger.info(f"{self.agent_name} performing resonance scan for query: '{query}' (triggered by Event ID: {trigger_event.id}) with params: {parameters}")
        
        simulated_mentions = [
            {"platform": "Twitter", "text": f"Excited about the new {query} project!", "user": "user123", "timestamp": time.time() - 3600},
            {"platform": "Reddit", "text": f"Anyone have details on {query}?", "user": "redditorABC", "timestamp": time.time() - 7200},
            {"platform": "Twitter", "text": f"Not sure about the {query} initiative yet...", "user": "criticXYZ", "timestamp": time.time() - 1800},
        ]
        logger.info(f"Simulated finding {len(simulated_mentions)} mentions.")
        
        simulated_resonance_score = 0.65
        simulated_sentiment = "mostly_positive"
        logger.info(f"Simulated resonance score: {simulated_resonance_score}, Sentiment: {simulated_sentiment}")
        
        result_data = {
            "status": "scan_completed",
            "query": query,
            "mention_count": len(simulated_mentions),
            "resonance_score": simulated_resonance_score,
            "sentiment": simulated_sentiment,
            "results": simulated_mentions,
            "timestamp": time.time(),
            "correlation_id": trigger_event.id
        }

        result_event = Event(
            type=EventType.MEREDITH_RESONANCE_RESULT,
            source_id=self.agent_name,
            target_id=trigger_event.source_id,
            data=result_data
        )

        try:
            self.bus.dispatch(result_event)
            logger.info(f"Dispatched {EventType.MEREDITH_RESONANCE_RESULT.name} event (CorrID: {trigger_event.id}) to {trigger_event.source_id}.")
        except Exception as e:
            logger.error(f"Failed to dispatch scan result event: {e}")