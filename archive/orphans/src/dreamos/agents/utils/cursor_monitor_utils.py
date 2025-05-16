"""Utilities for monitoring cursor agent states through GUI images."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

import imagehash
import mss
import mss.tools
from PIL import Image

from dreamos.core.coordination.agent_bus import AgentBus

from ...utils.common_utils import get_utc_iso_timestamp

logger = logging.getLogger(__name__)


class CursorStateMonitor:
    """Monitors cursor agent states through GUI images."""

    def __init__(
        self,
        bus: AgentBus,
        gui_images_dir: Path,
        coords_file: Path,
        check_interval: float = 1.0,
        hash_threshold: int = 5,
        image_size: Tuple[int, int] = (50, 50),  # Default size for state images
    ):
        """Initialize the cursor state monitor.

        Args:
            bus: AgentBus instance for publishing state changes
            gui_images_dir: Directory containing cursor GUI images
            coords_file: Path to JSON file containing agent coordinates
            check_interval: How often to check image states (seconds)
            hash_threshold: Threshold for image similarity comparison
            image_size: Size of the region to capture for state detection
        """
        self.bus = bus
        self.gui_images_dir = gui_images_dir
        self.coords_file = coords_file
        self.check_interval = check_interval
        self.hash_threshold = hash_threshold
        self.image_size = image_size

        # Load reference images
        self.complete_img = Image.open(gui_images_dir / "complete.png")
        self.generating_img = Image.open(gui_images_dir / "generating.png")

        # Calculate reference hashes
        self.complete_hash = imagehash.average_hash(self.complete_img)
        self.generating_hash = imagehash.average_hash(self.generating_img)

        # Load agent coordinates
        self.agent_coords = self._load_agent_coords()

        # Track agent states
        self.agent_states: Dict[str, bool] = {}  # agent_id -> is_complete
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.stuck_timers: Dict[str, float] = {}  # agent_id -> start_time

        # Initialize screen capture
        self.sct = mss.mss()

    def _load_agent_coords(self) -> Dict[str, Dict[str, Dict[str, int]]]:
        """Load agent coordinates from JSON file.

        Returns:
            Dict mapping agent IDs to their coordinate dictionaries
            containing input_box and copy_button positions
        """
        try:
            if self.coords_file.exists():
                with open(self.coords_file) as f:
                    return json.load(f)
            logger.warning(f"Coordinates file not found: {self.coords_file}")
            return {}
        except Exception as e:
            logger.error(f"Failed to load agent coordinates: {e}", exc_info=True)
            return {}

    def _get_agent_region(self, agent_id: str) -> Optional[Tuple[int, int, int, int]]:
        """Get screen region for an agent's state detection.

        Args:
            agent_id: ID of the agent

        Returns:
            Tuple of (left, top, width, height) if found, None otherwise
        """
        coords = self.agent_coords.get(agent_id)
        if not coords:
            logger.warning(f"No coordinates found for agent {agent_id}")
            return None

        # Use copy_button coordinates as reference point for state detection
        copy_btn = coords.get("copy_button", {})
        if not copy_btn:
            logger.warning(f"No copy_button coordinates for agent {agent_id}")
            return None

        x = copy_btn["x"]
        y = copy_btn["y"]
        width, height = self.image_size

        return (x, y, width, height)

    def _capture_cursor_image(
        self, coords: Dict[str, Dict[str, int]]
    ) -> Optional[Image.Image]:
        """Capture the cursor image at specified coordinates.

        Args:
            coords: Dictionary containing input_box and copy_button coordinates

        Returns:
            PIL Image object if successful, None otherwise
        """
        try:
            # Use copy_button coordinates for state detection
            copy_btn = coords.get("copy_button", {})
            if not copy_btn:
                logger.warning("No copy_button coordinates provided")
                return None

            region = {
                "left": copy_btn["x"],
                "top": copy_btn["y"],
                "width": self.image_size[0],
                "height": self.image_size[1],
            }

            # Capture the region
            screenshot = self.sct.grab(region)

            # Convert to PIL Image
            return Image.frombytes("RGB", screenshot.size, screenshot.rgb)

        except Exception as e:
            logger.error(f"Failed to capture cursor image: {e}", exc_info=True)
            return None

    async def _monitor_agent_state(
        self, agent_id: str, coords: Dict[str, Dict[str, int]]
    ) -> None:
        """Monitor an agent's cursor state by comparing GUI images.

        Args:
            agent_id: ID of the agent to monitor
            coords: Dictionary containing input_box and copy_button coordinates
        """
        try:
            while True:
                # Capture current state
                current_img = self._capture_cursor_image(coords)
                if current_img:
                    current_hash = imagehash.average_hash(current_img)

                    # Compare with reference states
                    complete_diff = current_hash - self.complete_hash
                    generating_diff = current_hash - self.generating_hash

                    # Determine if state changed
                    is_complete = complete_diff < self.hash_threshold
                    is_generating = generating_diff < self.hash_threshold

                    # Check for stuck state
                    if is_generating:
                        if agent_id not in self.stuck_timers:
                            self.stuck_timers[agent_id] = (
                                asyncio.get_event_loop().time()
                            )
                        elif (
                            asyncio.get_event_loop().time()
                            - self.stuck_timers[agent_id]
                            > 60
                        ):
                            await self._handle_stuck_agent(agent_id)
                    else:
                        self.stuck_timers.pop(agent_id, None)

                    # Handle state change
                    if is_complete != self.agent_states.get(agent_id, False):
                        self.agent_states[agent_id] = is_complete
                        await self._publish_state_change(agent_id, is_complete)

                await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            logger.info(f"Cursor monitoring cancelled for agent {agent_id}")
        except Exception as e:
            logger.error(
                f"Error monitoring cursor agent {agent_id}: {e}", exc_info=True
            )
        finally:
            self.stuck_timers.pop(agent_id, None)

    async def _handle_stuck_agent(self, agent_id: str) -> None:
        """Handle a stuck agent by publishing an alert.

        Args:
            agent_id: ID of the stuck agent
        """
        stuck_topic = f"system.cursor.{agent_id}.stuck"
        stuck_payload = {
            "sender_id": "cursor_monitor",
            "correlation_id": None,
            "timestamp_utc": get_utc_iso_timestamp(),
            "data": {
                "agent_id": agent_id,
                "message": "Agent appears stalled (generating for > 60s)",
            },
        }

        try:
            await self.bus.publish(stuck_topic, stuck_payload)
            logger.warning(f"Published stuck alert for agent {agent_id}")
        except Exception as e:
            logger.error(
                f"Failed to publish stuck alert for agent {agent_id}: {e}",
                exc_info=True,
            )

    async def stop(self) -> None:
        """Stop the monitor and clean up resources."""
        # Cancel all monitoring tasks
        for agent_id in list(self.monitoring_tasks.keys()):
            await self.stop_monitoring(agent_id)

        # Close screen capture
        self.sct.close()

        logger.info("Cursor state monitor stopped")

    async def start_monitoring(
        self, agent_id: str, coords: Dict[str, Dict[str, int]]
    ) -> None:
        """Start monitoring a cursor agent's state.

        Args:
            agent_id: ID of the agent to monitor
            coords: Dictionary containing input_box and copy_button coordinates
        """
        if agent_id in self.monitoring_tasks:
            logger.warning(f"Already monitoring agent {agent_id}")
            return

        self.agent_states[agent_id] = False
        self.monitoring_tasks[agent_id] = asyncio.create_task(
            self._monitor_agent_state(agent_id, coords),
            name=f"cursor_monitor_{agent_id}",
        )
        logger.info(f"Started monitoring cursor agent {agent_id}")

    async def stop_monitoring(self, agent_id: str) -> None:
        """Stop monitoring a cursor agent's state.

        Args:
            agent_id: ID of the agent to stop monitoring
        """
        if agent_id in self.monitoring_tasks:
            self.monitoring_tasks[agent_id].cancel()
            try:
                await self.monitoring_tasks[agent_id]
            except asyncio.CancelledError:
                pass
            del self.monitoring_tasks[agent_id]
            del self.agent_states[agent_id]
            logger.info(f"Stopped monitoring cursor agent {agent_id}")

    async def _publish_state_change(self, agent_id: str, is_complete: bool) -> None:
        """Publish cursor state change to the bus.

        Args:
            agent_id: ID of the agent whose state changed
            is_complete: Whether the agent is now complete
        """
        state_topic = f"system.cursor.{agent_id}.state"
        state_payload = {
            "sender_id": "cursor_monitor",
            "correlation_id": None,
            "timestamp_utc": get_utc_iso_timestamp(),
            "data": {"agent_id": agent_id, "is_complete": is_complete},
        }

        try:
            await self.bus.publish(state_topic, state_payload)
            logger.debug(
                f"Published cursor state change for {agent_id}: "
                f"{'complete' if is_complete else 'generating'}"
            )
        except Exception as e:
            logger.error(
                f"Failed to publish cursor state change for {agent_id}: {e}",
                exc_info=True,
            )

    def is_agent_complete(self, agent_id: str) -> bool:
        """Check if an agent is in complete state.

        Args:
            agent_id: ID of the agent to check

        Returns:
            bool: True if agent is complete, False otherwise
        """
        return self.agent_states.get(agent_id, False)

    def get_complete_agents(self) -> Set[str]:
        """Get set of all agents in complete state.

        Returns:
            Set[str]: Set of agent IDs that are complete
        """
        return {aid for aid, state in self.agent_states.items() if state}
