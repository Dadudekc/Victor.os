"""
Agent Identity Module

This module handles agent identity initialization, validation against ethos principles,
and integration with the empathy scoring system.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .ethos_validator import EthosValidator
from .empathy_scoring import EmpathyScorer
from .devlog_formatter import DevlogFormatter

logger = logging.getLogger(__name__)

class AgentIdentity:
    """Manages agent identity including ethos alignment and empathy metrics."""
    
    def __init__(self, agent_id: str, ethos_path: Optional[str] = None):
        """Initialize agent identity.
        
        Args:
            agent_id: Unique identifier for the agent
            ethos_path: Path to ethos.json. If None, uses default location.
        """
        self.agent_id = agent_id
        self.ethos_path = ethos_path or str(Path(__file__).parent.parent.parent / "dreamos_ai_organizer" / "ethos.json")
        self.validator = EthosValidator(self.ethos_path)
        self.scorer = EmpathyScorer(self.ethos_path)
        self.devlog = DevlogFormatter()
        self.creation_time = datetime.now().isoformat()
        self.last_validated = None
        self.identity_data = self._initialize_identity()
        self.previous_score = self.identity_data["empathy_score"]
        self.score_history = []
        
    def _initialize_identity(self) -> Dict:
        """Initialize the agent's identity data."""
        try:
            # Load ethos
            with open(self.ethos_path, 'r') as f:
                ethos = json.load(f)
                
            # Create initial identity
            identity = {
                "agent_id": self.agent_id,
                "created_at": self.creation_time,
                "ethos_version": ethos.get("version", "unknown"),
                "core_values": {value: 1.0 for value in ethos.get("core_values", {}).keys()},
                "principles": {principle: 1.0 for principle in ethos.get("operational_principles", {}).keys()},
                "empathy_score": 75.0,  # Default starting score
                "empathy_status": "developing",
                "validation_history": []
            }
            
            # Log initialization
            self._log_identity_update("Initialized agent identity with ethos version " + identity["ethos_version"])
            
            return identity
        except Exception as e:
            logger.error(f"Failed to initialize agent identity: {e}")
            # Create fallback identity
            return {
                "agent_id": self.agent_id,
                "created_at": self.creation_time,
                "ethos_version": "unknown",
                "core_values": {},
                "principles": {},
                "empathy_score": 60.0,  # Lower default score for fallback case
                "empathy_status": "needs_improvement",
                "validation_history": []
            }
            
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate agent identity against ethos principles.
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_violations)
        """
        is_valid, violations = self.validator.validate_identity(self.identity_data)
        
        # Update validation history
        self.last_validated = datetime.now().isoformat()
        self.identity_data["validation_history"].append({
            "timestamp": self.last_validated,
            "valid": is_valid,
            "violations": violations
        })
        
        # Log validation result
        if is_valid:
            self._log_identity_update("Identity validated successfully against ethos")
        else:
            self._log_ethos_violation(violations)
            
        return is_valid, violations
        
    def update_empathy_score(self) -> Dict:
        """Update the agent's empathy score based on logs.
        
        Returns:
            Dict containing updated empathy score metrics
        """
        # Store the previous score for delta calculation
        self.previous_score = self.identity_data.get("empathy_score", 75.0)
        
        # Calculate current empathy score
        score_data = self.scorer.calculate_agent_score(self.agent_id)
        
        # Update identity with new score
        self.identity_data["empathy_score"] = score_data["score"]
        self.identity_data["empathy_status"] = score_data["status"]
        
        # Calculate score delta and track history
        score_delta = score_data["score"] - self.previous_score
        score_entry = {
            "timestamp": datetime.now().isoformat(),
            "score": score_data["score"],
            "previous_score": self.previous_score,
            "delta": score_delta,
            "status": score_data["status"]
        }
        self.score_history.append(score_entry)
        
        # Limit history size to prevent unbounded growth
        if len(self.score_history) > 100:
            self.score_history = self.score_history[-100:]
        
        # Format delta for logging
        delta_text = f"+{score_delta:.1f}" if score_delta >= 0 else f"{score_delta:.1f}"
        
        # Log score update with delta
        self._log_identity_update(
            f"Updated empathy score to {score_data['score']:.1f} ({score_data['status']}) [Δ {delta_text}]",
            score_delta=score_delta,
            score_history=self.score_history[-10:]  # Include recent history
        )
        
        return score_data
        
    def _log_identity_update(self, message: str, **additional_data) -> None:
        """Log an identity update event.
        
        Args:
            message: The log message
            **additional_data: Additional data to include in the log
        """
        try:
            # Create log entry with identity state
            log_data = {
                "identity_state": self.identity_data
            }
            
            # Add any additional data
            if additional_data:
                log_data.update(additional_data)
            
            # Check if this is a score update
            if "score_delta" in additional_data:
                # Create a more detailed log for score changes
                score_delta = additional_data["score_delta"]
                
                # Determine if this is significant based on the magnitude
                is_significant = abs(score_delta) >= 5.0
                
                # Create a log file path that includes the agent ID
                log_dir = Path("runtime/logs/agents")
                log_dir.mkdir(parents=True, exist_ok=True)
                
                log_file = log_dir / f"{self.agent_id}_score_evolution.log"
                
                # Append to the dedicated score evolution log
                try:
                    with open(log_file, "a") as f:
                        f.write(f"[{datetime.now().isoformat()}] {message}\n")
                        f.write(f"  Previous: {self.previous_score:.1f}, Current: {self.identity_data['empathy_score']:.1f}, Delta: {score_delta:.1f}\n")
                        f.write(f"  Status: {self.identity_data['empathy_status']}\n")
                        
                        # Add trending information if we have enough history
                        if len(self.score_history) >= 3:
                            recent_deltas = [entry["delta"] for entry in self.score_history[-3:]]
                            avg_delta = sum(recent_deltas) / len(recent_deltas)
                            trend = "improving" if avg_delta > 0 else "declining" if avg_delta < 0 else "stable"
                            f.write(f"  Trend: {trend} (avg Δ: {avg_delta:.1f} over last 3 updates)\n")
                            
                        f.write("\n")
                except Exception as e:
                    logger.error(f"Failed to write to score evolution log: {e}")
            
            # Write to the main devlog
            self.devlog.format_and_write_identity_update(
                agent_id=self.agent_id,
                message=message,
                identity_state=self.identity_data,
                **additional_data
            )
            
        except Exception as e:
            logger.error(f"Failed to log identity update: {e}")
            
    def _log_ethos_violation(self, violations: List[str]) -> None:
        """Log ethos violations."""
        try:
            self.devlog.format_and_write_violation(
                agent_id=self.agent_id,
                violation_type="ethos_identity_violation",
                severity="high",
                description=f"Identity validation failed with {len(violations)} violations",
                details="\n".join(violations),
                context={
                    "identity_state": self.identity_data,
                    "validation_time": self.last_validated
                }
            )
            
            # Check if violations are severe enough to escalate
            if len(violations) > 3:
                self._escalate_violations(violations)
        except Exception as e:
            logger.error(f"Failed to log ethos violation: {e}")
            
    def _escalate_violations(self, violations: List[str]) -> None:
        """Escalate severe violations to THEA or other supervisory system."""
        logger.warning(f"ESCALATING {len(violations)} ethos violations for agent {self.agent_id}")
        
        # This is a placeholder for actual escalation logic
        # In a real implementation, this would:
        # 1. Format a structured alert
        # 2. Send it to THEA or another oversight system
        # 3. Potentially trigger a human review or agent pause
        
        logger.warning(
            f"ESCALATION ALERT - Agent: {self.agent_id}, "
            f"Violations: {', '.join(violations[:3])}{'...' if len(violations) > 3 else ''}"
        )
        
    def get_identity_summary(self) -> Dict:
        """Get a summary of the agent's identity.
        
        Returns:
            Dict containing identity summary
        """
        return {
            "agent_id": self.identity_data["agent_id"],
            "created_at": self.identity_data["created_at"],
            "ethos_version": self.identity_data["ethos_version"],
            "empathy_score": self.identity_data["empathy_score"],
            "empathy_status": self.identity_data["empathy_status"],
            "last_validated": self.last_validated,
            "validation_status": self.identity_data["validation_history"][-1]["valid"] 
                if self.identity_data["validation_history"] 
                else None,
            "score_history": self.score_history[-5:] if self.score_history else []
        }

    def get_score_history(self, limit: int = 10) -> List[Dict]:
        """Get the agent's empathy score history.
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            List of score history entries
        """
        return self.score_history[-limit:] if len(self.score_history) > limit else self.score_history


def initialize_agent(agent_id: str) -> AgentIdentity:
    """Initialize an agent with identity and ethos validation.
    
    Args:
        agent_id: Unique identifier for the agent
        
    Returns:
        AgentIdentity: Initialized agent identity
    """
    try:
        # Create and validate agent identity
        identity = AgentIdentity(agent_id)
        is_valid, violations = identity.validate()
        
        if not is_valid:
            logger.warning(f"Agent {agent_id} identity validation failed: {violations}")
            
        # Calculate initial empathy score
        identity.update_empathy_score()
        
        return identity
    except Exception as e:
        logger.error(f"Failed to initialize agent {agent_id}: {e}")
        raise 