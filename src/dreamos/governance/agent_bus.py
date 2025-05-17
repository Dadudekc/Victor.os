# src/dreamos/governance/agent_bus.py
"""
Minimal event-bus adapter so ElectionManager & SystemMonitorAgent can run
without the full Dream.OS AgentBus.  Replace with real import when available.
"""

from __future__ import annotations
import asyncio, json, logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)

class AgentBus:
    """File-backed pub/sub for local testing."""
    _EVENT_DIR = Path("runtime/bus/events")

    def __init__(self) -> None:
        self._subs: Dict[str, List[Callable[[str, Dict[str, Any]], None]]] = {}

    async def publish(self, etype: str, payload: Dict[str, Any]) -> None:
        logger.info("Bus ▶ %s – %s", etype, payload)
        self._EVENT_DIR.mkdir(parents=True, exist_ok=True)
        fname = f"{etype.replace('.', '_')}_{int(datetime.utcnow().timestamp())}.json"
        with (self._EVENT_DIR / fname).open("w", encoding="utf-8") as f:
            json.dump({"event_type": etype,
                       "payload": payload,
                       "timestamp": datetime.utcnow().isoformat()}, f, indent=2)

        for cb in self._subs.get(etype, []):
            asyncio.create_task(cb(etype, payload))

    async def subscribe(self, etype: str, cb: Callable[[str, Dict[str, Any]], None]) -> None:
        self._subs.setdefault(etype, []).append(cb)
        logger.debug("Bus: %s subscribed to %s", cb.__qualname__, etype) 