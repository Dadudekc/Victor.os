"""
Consensus module for agent bootstrap runner.
Handles voting and decision-making among agents.
"""

import asyncio
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ValidationError

from dreamos.core.coordination.agent_bus import AgentBus, EventType

logger = logging.getLogger(__name__)

class VoteData(BaseModel):
    """Vote data model."""
    vote_id: str
    agent_id: str
    choice: str
    confidence: float
    timestamp: str

class VoteSession(BaseModel):
    """Vote session model."""
    session_id: str
    topic: str
    choices: List[str]
    quorum: int
    timeout_seconds: int
    initiated_by: str
    initiated_at: str
    status: str = "active"

class ConsensusManager:
    """Manages consensus through voting among agents."""

    def __init__(self, agent_bus: AgentBus, config):
        """Initialize the consensus manager."""
        self.agent_bus = agent_bus
        self.config = config
        self.active_sessions: Dict[str, VoteSession] = {}
        self.votes: Dict[str, Dict[str, VoteData]] = {}
        self.tasks: Dict[str, asyncio.Task] = {}

    async def start(self):
        """Start listening for vote-related events."""
        try:
            await self.agent_bus.subscribe(EventType.VOTE_INITIATED.value, self._handle_vote_initiated)
            await self.agent_bus.subscribe(EventType.AGENT_VOTE.value, self._handle_vote)
            logger.info("ConsensusManager started successfully")
        except Exception as e:
            logger.error(f"Failed to start ConsensusManager: {e}")
            raise

    async def stop(self):
        """Stop all active vote sessions."""
        for session_id, task in self.tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self.active_sessions.clear()
        self.votes.clear()
        self.tasks.clear()

    async def initiate_vote(
        self,
        topic: str,
        choices: List[str],
        quorum: int,
        timeout_seconds: int,
        initiated_by: str
    ) -> str:
        """
        Initiate a new vote session.

        Args:
            topic: The topic being voted on
            choices: List of valid voting choices
            quorum: Number of votes needed for decision
            timeout_seconds: How long to wait for votes
            initiated_by: ID of the initiating agent

        Returns:
            str: The session ID
        """
        session_id = f"vote_{datetime.now(timezone.utc).timestamp()}"
        
        session = VoteSession(
            session_id=session_id,
            topic=topic,
            choices=choices,
            quorum=quorum,
            timeout_seconds=timeout_seconds,
            initiated_by=initiated_by,
            initiated_at=datetime.now(timezone.utc).isoformat()
        )
        
        self.active_sessions[session_id] = session
        self.votes[session_id] = {}
        
        # Start timeout task
        self.tasks[session_id] = asyncio.create_task(
            self._handle_vote_timeout(session_id, timeout_seconds)
        )
        
        # Announce vote session
        await self.agent_bus.publish(
            EventType.VOTE_INITIATED.value,
            {
                "session_id": session_id,
                "topic": topic,
                "choices": choices,
                "quorum": quorum,
                "timeout_seconds": timeout_seconds,
                "initiated_by": initiated_by
            }
        )
        
        return session_id

    async def cast_vote(
        self,
        session_id: str,
        agent_id: str,
        choice: str,
        confidence: float = 1.0
    ) -> bool:
        """
        Cast a vote in an active session.

        Args:
            session_id: The vote session ID
            agent_id: The voting agent's ID
            choice: The agent's choice
            confidence: The agent's confidence in their choice (0-1)

        Returns:
            bool: True if vote was accepted
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Vote session {session_id} not found")
            return False
            
        session = self.active_sessions[session_id]
        if session.status != "active":
            logger.warning(f"Vote session {session_id} is not active")
            return False
            
        if choice not in session.choices:
            logger.warning(f"Invalid choice '{choice}' for session {session_id}")
            return False
            
        vote = VoteData(
            vote_id=f"{session_id}_{agent_id}",
            agent_id=agent_id,
            choice=choice,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        self.votes[session_id][agent_id] = vote
        
        # Check if we have reached quorum
        if len(self.votes[session_id]) >= session.quorum:
            await self._finalize_vote_session(session_id)
            
        return True

    async def _handle_vote_initiated(self, topic: str, data: Dict[str, Any]):
        """Handle vote initiation events."""
        try:
            session = VoteSession(**data)
            if session.session_id in self.active_sessions:
                logger.warning(f"Duplicate vote session ID: {session.session_id}")
                return
                
            self.active_sessions[session.session_id] = session
            self.votes[session.session_id] = {}
            
            # Start timeout task
            self.tasks[session.session_id] = asyncio.create_task(
                self._handle_vote_timeout(session.session_id, session.timeout_seconds)
            )
            
        except ValidationError as e:
            logger.error(f"Invalid vote session data: {e}")
        except Exception as e:
            logger.error(f"Error handling vote initiation: {e}")

    async def _handle_vote(self, topic: str, data: Dict[str, Any]):
        """Handle incoming votes."""
        try:
            vote = VoteData(**data)
            session_id = vote.vote_id.split("_")[0]
            
            if session_id not in self.active_sessions:
                logger.warning(f"Vote for unknown session: {session_id}")
                return
                
            session = self.active_sessions[session_id]
            if session.status != "active":
                logger.warning(f"Vote for inactive session: {session_id}")
                return
                
            if vote.choice not in session.choices:
                logger.warning(f"Invalid choice in vote: {vote.choice}")
                return
                
            self.votes[session_id][vote.agent_id] = vote
            
            # Check if we have reached quorum
            if len(self.votes[session_id]) >= session.quorum:
                await self._finalize_vote_session(session_id)
                
        except ValidationError as e:
            logger.error(f"Invalid vote data: {e}")
        except Exception as e:
            logger.error(f"Error handling vote: {e}")

    async def _handle_vote_timeout(self, session_id: str, timeout_seconds: int):
        """Handle vote session timeout."""
        try:
            await asyncio.sleep(timeout_seconds)
            if session_id in self.active_sessions:
                await self._finalize_vote_session(session_id)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in vote timeout handler: {e}")

    async def _finalize_vote_session(self, session_id: str):
        """Finalize a vote session and publish results."""
        if session_id not in self.active_sessions:
            return
            
        session = self.active_sessions[session_id]
        if session.status != "active":
            return
            
        # Calculate results
        votes = self.votes[session_id]
        vote_counts = Counter(v.choice for v in votes.values())
        confidence_sums = {choice: 0.0 for choice in session.choices}
        for vote in votes.values():
            confidence_sums[vote.choice] += vote.confidence
            
        # Determine winner
        if vote_counts:
            winner = max(vote_counts.items(), key=lambda x: (x[1], confidence_sums[x[0]]))
            result = {
                "session_id": session_id,
                "winner": winner[0],
                "vote_counts": dict(vote_counts),
                "confidence_sums": confidence_sums,
                "total_votes": len(votes),
                "quorum_reached": len(votes) >= session.quorum
            }
        else:
            result = {
                "session_id": session_id,
                "winner": None,
                "vote_counts": {},
                "confidence_sums": confidence_sums,
                "total_votes": 0,
                "quorum_reached": False
            }
            
        # Update session status
        session.status = "completed"
        
        # Publish results
        await self.agent_bus.publish(
            EventType.VOTE_RESULTS.value,
            {
                "session_id": session_id,
                "topic": session.topic,
                "result": result,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Cleanup
        if session_id in self.tasks:
            task = self.tasks.pop(session_id)
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass 