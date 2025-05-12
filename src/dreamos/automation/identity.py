"""
Identity Management Module
Handles agent identity, purpose, and role configuration.
"""

import json
from pathlib import Path
from typing import Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class IdentityManager:
    def __init__(self):
        self.identities: Dict[str, Dict[str, str]] = {}
        self.config_path = Path("runtime/config/agent_identity.json")

    def initialize_identities(self, agent_awareness: Dict[str, Any]) -> bool:
        """Initialize agent identities from episode configuration."""
        try:
            # Extract agent prefixes and roles
            self.identities = {
                agent_id: {
                    "role": role,
                    "purpose": self._get_purpose_for_role(role)
                }
                for agent_id, role in agent_awareness['agent_prefixes'].items()
            }

            # Save identity configuration
            return self._save_identity_config()
        except Exception as e:
            logger.error(f"Error initializing identities: {str(e)}")
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

    def _save_identity_config(self) -> bool:
        """Save identity configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config_data = {
                "agents": self.identities,
                "last_updated": datetime.now().isoformat()
            }

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info("Saved agent identity configuration")
            return True
        except Exception as e:
            logger.error(f"Error saving identity config: {str(e)}")
            return False

    def get_agent_identity(self, agent_id: str) -> Dict[str, str]:
        """Get identity information for an agent."""
        return self.identities.get(agent_id, {
            "role": "Unknown",
            "purpose": "Undefined purpose"
        })

    def get_identity_prefix(self, agent_id: str) -> str:
        """Get identity prefix for an agent."""
        identity = self.get_agent_identity(agent_id)
        return f"{identity['role']} {agent_id}"

    def validate_identity(self, agent_id: str) -> bool:
        """Validate that an agent has a proper identity configuration."""
        return agent_id in self.identities

    def log_identity_confirmation(self, agent_id: str) -> bool:
        """Log agent identity confirmation at loop start."""
        try:
            identity = self.get_agent_identity(agent_id)
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "agent_id": agent_id,
                "role": identity['role'],
                "purpose": identity['purpose'],
                "event": "identity_confirmation"
            }

            log_path = Path("runtime/logs/identity")
            log_path.mkdir(parents=True, exist_ok=True)
            
            log_file = log_path / f"{agent_id}_identity.log"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + "\n")

            logger.info(f"Logged identity confirmation for {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error logging identity confirmation: {str(e)}")
            return False 