"""
Agent Identity and Awareness Module
Handles agent identity, purpose, and role configuration.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AgentIdentity:
    def __init__(self, agent_id: str, role: str, purpose: str):
        self.agent_id = agent_id
        self.role = role
        self.purpose = purpose
        self.last_confirmation = None
        self.awareness_level = 0.0  # 0.0 to 1.0 scale

    def to_dict(self) -> Dict[str, Any]:
        """Convert identity to dictionary format."""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "purpose": self.purpose,
            "last_confirmation": self.last_confirmation,
            "awareness_level": self.awareness_level
        }

class AgentAwareness:
    def __init__(self):
        self.identities: Dict[str, AgentIdentity] = {}
        self.config_path = Path("runtime/config/agent_identity.json")
        self.log_path = Path("runtime/logs/awareness")

    def initialize_from_config(self, config_data: Dict[str, Any]) -> bool:
        """Initialize agent identities from configuration."""
        try:
            # Extract agent prefixes and roles
            for agent_id, role in config_data['agent_prefixes'].items():
                purpose = self._get_purpose_for_role(role)
                self.identities[agent_id] = AgentIdentity(agent_id, role, purpose)

            # Save initial configuration
            return self._save_config()
        except Exception as e:
            logger.error(f"Error initializing agent awareness: {str(e)}")
            return False

    def _get_purpose_for_role(self, role: str) -> str:
        """Get purpose statement for a given role."""
        purposes = {
            "⚙️ Engineer": "System engineering and optimization",
            "🛡️ Escalation Watch": "Safety and oversight",
            "📦 Task Router": "Task distribution and coordination",
            "🔬 Validator": "Quality assurance and validation",
            "🎯 Captain": "Strategic direction and leadership",
            "🧠 Reflection": "System reflection and improvement",
            "📡 Bridge Ops": "Communication and integration",
            "🕊️ Lorekeeper": "Documentation and knowledge management"
        }
        return purposes.get(role, "Undefined purpose")

    def _save_config(self) -> bool:
        """Save agent identity configuration."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config_data = {
                "agents": {
                    agent_id: identity.to_dict()
                    for agent_id, identity in self.identities.items()
                },
                "last_updated": datetime.now().isoformat()
            }

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info("Saved agent identity configuration")
            return True
        except Exception as e:
            logger.error(f"Error saving identity config: {str(e)}")
            return False

    def confirm_identity(self, agent_id: str) -> bool:
        """Confirm agent identity and log awareness."""
        try:
            if agent_id not in self.identities:
                logger.error(f"Unknown agent ID: {agent_id}")
                return False

            identity = self.identities[agent_id]
            identity.last_confirmation = datetime.now().isoformat()
            identity.awareness_level = min(1.0, identity.awareness_level + 0.1)

            # Log awareness confirmation
            self._log_awareness(identity)

            # Update configuration
            return self._save_config()
        except Exception as e:
            logger.error(f"Error confirming identity: {str(e)}")
            return False

    def _log_awareness(self, identity: AgentIdentity) -> None:
        """Log agent awareness confirmation."""
        try:
            self.log_path.mkdir(parents=True, exist_ok=True)
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "agent_id": identity.agent_id,
                "role": identity.role,
                "purpose": identity.purpose,
                "awareness_level": identity.awareness_level,
                "event": "identity_confirmation"
            }

            log_file = self.log_path / f"{identity.agent_id}_awareness.log"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + "\n")

            logger.info(f"Logged awareness confirmation for {identity.agent_id}")
        except Exception as e:
            logger.error(f"Error logging awareness: {str(e)}")

    def get_identity(self, agent_id: str) -> Optional[AgentIdentity]:
        """Get identity information for an agent."""
        return self.identities.get(agent_id)

    def get_identity_prefix(self, agent_id: str) -> str:
        """Get identity prefix for an agent."""
        identity = self.get_identity(agent_id)
        if not identity:
            return f"Unknown {agent_id}"
        return f"{identity.role} {agent_id}"

    def validate_identity(self, agent_id: str) -> bool:
        """Validate that an agent has a proper identity configuration."""
        return agent_id in self.identities

    def get_awareness_level(self, agent_id: str) -> float:
        """Get current awareness level for an agent."""
        identity = self.get_identity(agent_id)
        return identity.awareness_level if identity else 0.0 