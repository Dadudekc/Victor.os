import asyncio
import json
from typing import Dict, Set

from websockets.exceptions import ConnectionClosed
from websockets.server import WebSocketServerProtocol

from ..agents.dna_analyzer import DNAAnalyzer
from ..memory import AgentMemory
from ..utils.logging import get_logger

logger = get_logger(__name__)


class DNAWebSocketService:
    """WebSocket service for real-time DNA analysis updates."""

    def __init__(self, memory: AgentMemory):
        self.memory = memory
        self.dna_analyzer = DNAAnalyzer(memory)
        self.connections: Set[WebSocketServerProtocol] = set()
        self.agent_subscriptions: Dict[str, Set[WebSocketServerProtocol]] = {}
        self.analysis_interval = 300  # 5 minutes

    async def start(self):
        """Starts the DNA analysis background task."""
        while True:
            try:
                # Analyze all active agents
                active_agents = await self.memory.get_active_agents()
                for agent_id in active_agents:
                    try:
                        # Analyze agent DNA
                        dna_profile = await self.dna_analyzer.analyze_agent_dna(
                            agent_id
                        )

                        # Broadcast update to subscribed clients
                        await self._broadcast_dna_update(agent_id, dna_profile)

                    except Exception as e:
                        logger.error(f"Error analyzing agent {agent_id}: {str(e)}")

                # Wait for next analysis interval
                await asyncio.sleep(self.analysis_interval)

            except Exception as e:
                logger.error(f"Error in DNA analysis loop: {str(e)}")
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def handle_connection(self, websocket: WebSocketServerProtocol):
        """Handles a new WebSocket connection."""
        try:
            self.connections.add(websocket)

            async for message in websocket:
                try:
                    data = json.loads(message)

                    if data["type"] == "subscribe":
                        await self._handle_subscription(websocket, data["agent_id"])
                    elif data["type"] == "unsubscribe":
                        await self._handle_unsubscription(websocket, data["agent_id"])
                    elif data["type"] == "request_analysis":
                        await self._handle_analysis_request(websocket, data["agent_id"])

                except json.JSONDecodeError:
                    logger.error("Invalid JSON message received")
                except KeyError as e:
                    logger.error(f"Missing required field: {str(e)}")
                except Exception as e:
                    logger.error(f"Error handling message: {str(e)}")

        except ConnectionClosed:
            pass
        finally:
            await self._cleanup_connection(websocket)

    async def _handle_subscription(
        self, websocket: WebSocketServerProtocol, agent_id: str
    ):
        """Handles subscription to an agent's DNA updates."""
        if agent_id not in self.agent_subscriptions:
            self.agent_subscriptions[agent_id] = set()

        self.agent_subscriptions[agent_id].add(websocket)

        # Send current DNA profile
        try:
            dna_profile = await self.memory.get_agent_dna(agent_id)
            if dna_profile:
                await websocket.send(
                    json.dumps(
                        {
                            "type": "agent_dna_update",
                            "agentId": agent_id,
                            "dna": dna_profile,
                        }
                    )
                )
        except Exception as e:
            logger.error(f"Error sending initial DNA profile: {str(e)}")

    async def _handle_unsubscription(
        self, websocket: WebSocketServerProtocol, agent_id: str
    ):
        """Handles unsubscription from an agent's DNA updates."""
        if agent_id in self.agent_subscriptions:
            self.agent_subscriptions[agent_id].discard(websocket)
            if not self.agent_subscriptions[agent_id]:
                del self.agent_subscriptions[agent_id]

    async def _handle_analysis_request(
        self, websocket: WebSocketServerProtocol, agent_id: str
    ):
        """Handles a request for immediate DNA analysis."""
        try:
            dna_profile = await self.dna_analyzer.analyze_agent_dna(agent_id)
            await websocket.send(
                json.dumps(
                    {
                        "type": "agent_dna_update",
                        "agentId": agent_id,
                        "dna": dna_profile,
                    }
                )
            )
        except Exception as e:
            logger.error(f"Error handling analysis request: {str(e)}")
            await websocket.send(
                json.dumps({"type": "error", "message": "Failed to analyze agent DNA"})
            )

    async def _broadcast_dna_update(self, agent_id: str, dna_profile: Dict):
        """Broadcasts DNA update to all subscribed clients."""
        if agent_id not in self.agent_subscriptions:
            return

        message = json.dumps(
            {"type": "agent_dna_update", "agentId": agent_id, "dna": dna_profile}
        )

        for websocket in self.agent_subscriptions[agent_id]:
            try:
                await websocket.send(message)
            except ConnectionClosed:
                await self._cleanup_connection(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting DNA update: {str(e)}")

    async def _cleanup_connection(self, websocket: WebSocketServerProtocol):
        """Cleans up a closed WebSocket connection."""
        self.connections.discard(websocket)

        # Remove from all subscriptions
        for agent_id in list(self.agent_subscriptions.keys()):
            self.agent_subscriptions[agent_id].discard(websocket)
            if not self.agent_subscriptions[agent_id]:
                del self.agent_subscriptions[agent_id]
