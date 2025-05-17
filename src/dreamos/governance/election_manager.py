"""
Coordinates autonomous Captain elections.

Public API:
    ElectionManager(bus, consensus).start_services()
"""

from __future__ import annotations
import asyncio, logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from .agent_bus import AgentBus
from .event_types import EventType
from .consensus_manager_stub import ConsensusManager

logger = logging.getLogger(__name__)

# Tunables (seconds)
CANDIDACY_PERIOD_S = 60 * 60      # 1 hr  (adjust for prod)
VOTING_PERIOD_S    = 60 * 60
QUORUM_FACTOR      = 0.5          # 50 % eligible voters
MIN_CANDIDATES     = 1

class ElectionManager:
    def __init__(self,
                 bus: AgentBus,
                 consensus: ConsensusManager,
                 agent_id: str = "ElectionManager") -> None:
        self.bus, self.consensus, self.agent_id = bus, consensus, agent_id
        self._state: Optional[Dict[str, Any]] = None
        self._candidates: Dict[str, Dict[str, Any]] = {}
        self._timer_task: Optional[asyncio.Task] = None

    # ─────────────────────────── bootstrap
    async def start_services(self) -> None:
        sub = self.bus.subscribe
        await sub(EventType.ELECTION_START,       self._on_start)
        await sub(EventType.DECLARE_CANDIDACY,    self._on_candidacy)
        await sub(EventType.CONSENSUS_VOTE_COMPLETED, self._on_vote_complete)
        logger.info("%s online.", self.agent_id)

    # ─────────────────────────── handlers
    async def _on_start(self, etype: str, data: Dict[str, Any]) -> None:
        if self._state:
            logger.warning("Election in progress; ignoring new start.")
            return

        self._state = {
            "cycle": data["cycle_count"],
            "eligible_candidates": data["eligible_candidates"],
            "eligible_voters": data["eligible_voters"],
            "status": "candidacy_open",
            "start_ts": datetime.utcnow().isoformat()
        }
        self._candidates.clear()
        logger.info("Election cycle %s started. Candidacy open %ds.",
                    self._state["cycle"], CANDIDACY_PERIOD_S)
        self._timer_task = asyncio.create_task(self._end_candidacy())

    async def _on_candidacy(self, etype: str, data: Dict[str, Any]) -> None:
        if not self._state or self._state["status"] != "candidacy_open":
            return
        aid = data.get("agent_id")
        if aid not in self._state["eligible_candidates"]:
            logger.warning("%s not eligible; candidacy ignored.", aid)
            return
        self._candidates[aid] = {
            "platform": data.get("platform_statement", ""),
            "declared_at": datetime.utcnow().isoformat()
        }
        logger.info("%s entered race (%d so far).", aid, len(self._candidates))

    async def _on_vote_complete(self, etype: str, data: Dict[str, Any]) -> None:
        if not self._state or data["session_id"] != self._state.get("session_id"):
            return
        winner = data.get("winning_choice") if data.get("quorum_met") else None
        status  = "success" if winner else "failed"
        await self._publish_result(winner, status)

    # ─────────────────────────── phases
    async def _end_candidacy(self) -> None:
        await asyncio.sleep(CANDIDACY_PERIOD_S)
        if not self._state:   # aborted
            return
        if len(self._candidates) < MIN_CANDIDATES:
            await self._publish_result(None, "insufficient_candidates")
            return

        self._state["status"] = "voting_open"
        voters  = self._state["eligible_voters"]
        quorum  = max(1, int(len(voters) * QUORUM_FACTOR))
        choices = list(self._candidates.keys())
        sid = await self.consensus.initiate_vote(
            topic=f"CaptainElection_{self._state['cycle']}",
            choices=choices,
            quorum=quorum,
            timeout_s=VOTING_PERIOD_S,
            initiated_by=self.agent_id,
            eligible_voters=voters
        )
        self._state["session_id"] = sid
        logger.info("Voting session %s open %ds.", sid, VOTING_PERIOD_S)

    # ─────────────────────────── utils
    async def _publish_result(self, winner: Optional[str], status: str) -> None:
        await self.bus.publish(EventType.ELECTION_RESULT, {
            "cycle_count": self._state["cycle"],
            "status": status,
            "winner": winner,
            "candidates": self._candidates,
            "timestamp": datetime.utcnow().isoformat()
        })
        logger.info("Election cycle %s finished. Status=%s Winner=%s",
                    self._state["cycle"], status, winner)
        self._cleanup()

    def _cleanup(self) -> None:
        if self._timer_task:
            self._timer_task.cancel()
        self._state, self._candidates = None, {}
