"""
Agent Identity Management for Dream.OS

This module handles agent identity verification and ethos compliance during initialization
and runtime. It ensures that all agents maintain alignment with Dream.OS principles.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

from .ethos_validator import EthosValidator

logger = logging.getLogger(__name__)

class AgentIdentity:
    """Manages agent identity and ethos compliance."""
    
    def __init__(self, agent_id: str, identity_path: Optional[str] = None):
        """Initialize agent identity manager.
        
        Args:
            agent_id: Unique identifier for the agent
            identity_path: Path to identity configuration. If None, uses default location.
        """
        self.agent_id = agent_id
        self.identity_path = identity_path or str(
            Path(__file__).parent.parent.parent / "config" / "agents" / f"{agent_id}.json"
        )
        self.ethos_validator = EthosValidator()
        self.identity = self._load_identity()
        self.devlog_path = Path(__file__).parent.parent.parent / "runtime" / "logs" / "empathy"
        self.devlog_path.mkdir(parents=True, exist_ok=True)
        
    def _load_identity(self) -> Dict:
        """Load and validate agent identity configuration."""
        try:
            with open(self.identity_path, 'r') as f:
                identity = json.load(f)
            self._validate_identity_structure(identity)
            return identity
        except Exception as e:
            logger.error(f"Failed to load agent identity: {e}")
            raise
            
    def _validate_identity_structure(self, identity: Dict) -> None:
        """Validate the structure of the identity configuration."""
        required_sections = [
            "version", "created_at", "agent_type", "capabilities",
            "ethos_alignment", "personality_traits"
        ]
        for section in required_sections:
            if section not in identity:
                raise ValueError(f"Missing required section: {section}")
                
    def validate_ethos_compliance(self) -> Tuple[bool, Dict]:
        """Validate agent's current state against ethos principles.
        
        Returns:
            Tuple[bool, Dict]: (is_compliant, validation_results)
        """
        # Check current state alignment
        alignment = self.ethos_validator.check_ethos_alignment(self.identity)
        
        # Log validation results
        self._log_validation_results(alignment)
        
        # Determine compliance
        is_compliant = all(score >= 0.7 for score in alignment["metrics"].values())
        
        return is_compliant, alignment
        
    def _log_validation_results(self, alignment: Dict) -> None:
        """Log validation results to devlog."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.devlog_path / f"ethos_validation_{self.agent_id}_{timestamp}.json"
        
        with open(log_file, 'w') as f:
            json.dump({
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat(),
                "alignment": alignment
            }, f, indent=2)
            
    def handle_violation(self, violation: Dict) -> None:
        """Handle ethos violation.
        
        Args:
            violation: Dictionary containing violation details
        """
        # Log violation
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.devlog_path / f"violation_{self.agent_id}_{timestamp}.json"
        
        with open(log_file, 'w') as f:
            json.dump({
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat(),
                "violation": violation
            }, f, indent=2)
            
        # Escalate if needed
        if violation.get("severity", "low") in ["high", "critical"]:
            self._escalate_to_thea(violation)
            
    def _escalate_to_thea(self, violation: Dict) -> None:
        """Escalate violation to THEA for review."""
        # TODO: Implement THEA escalation
        logger.warning(f"Escalating violation to THEA: {violation}")
        
    def update_identity(self, updates: Dict) -> None:
        """Update agent identity with new information.
        
        Args:
            updates: Dictionary containing identity updates
        """
        # Validate updates against ethos
        if not self.ethos_validator.validate_action({
            "type": "identity_update",
            "context": self.identity,
            "updates": updates
        }):
            raise ValueError("Updates violate ethos principles")
            
        # Apply updates
        self.identity.update(updates)
        self.identity["last_updated"] = datetime.now().isoformat()
        
        # Save updated identity
        with open(self.identity_path, 'w') as f:
            json.dump(self.identity, f, indent=2)
            
    def get_identity_summary(self) -> Dict:
        """Get a summary of the agent's identity and ethos alignment.
        
        Returns:
            Dict containing identity summary
        """
        return {
            "agent_id": self.agent_id,
            "agent_type": self.identity["agent_type"],
            "capabilities": self.identity["capabilities"],
            "ethos_alignment": self.identity["ethos_alignment"],
            "personality_traits": self.identity["personality_traits"],
            "last_updated": self.identity["last_updated"]
        }
        
    def enforce_identity(self, action: Dict) -> bool:
        """Enforce identity constraints on an action.
        
        Args:
            action: Dictionary containing action details
            
        Returns:
            bool: True if action is allowed, False otherwise
        """
        # Check against capabilities
        if not self._check_capabilities(action):
            return False
            
        # Check against personality traits
        if not self._check_personality_traits(action):
            return False
            
        # Check against ethos alignment
        if not self._check_ethos_alignment(action):
            return False
            
        return True
        
    def _check_capabilities(self, action: Dict) -> bool:
        """Check if action is within agent's capabilities."""
        required_capabilities = action.get("required_capabilities", [])
        return all(
            capability in self.identity["capabilities"]
            for capability in required_capabilities
        )
        
    def _check_personality_traits(self, action: Dict) -> bool:
        """Check if action aligns with agent's personality traits."""
        # TODO: Implement personality trait validation
        return True
        
    def _check_ethos_alignment(self, action: Dict) -> bool:
        """Check if action aligns with agent's ethos alignment."""
        return self.ethos_validator.validate_action(action) 