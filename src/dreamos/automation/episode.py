"""
DreamOS Episode Manager
Handles episode lifecycle, validation, and documentation.
"""

import json
import os
import yaml
from datetime import datetime
from typing import Dict, List, Optional

from .promotion import PromotionSystem
from .reflection import ReflectionEngine
from .empathy import EmpathyLogger

class EpisodeManager:
    def __init__(self, state_dir: str = "runtime/state", docs_dir: str = "docs"):
        self.state_dir = state_dir
        self.docs_dir = docs_dir
        self.promotion_system = PromotionSystem(state_dir)
        self.reflection_engine = ReflectionEngine(state_dir, docs_dir)
        self.empathy_logger = EmpathyLogger(state_dir)

    def validate_episode(self, episode_file: str) -> bool:
        """Validate an episode configuration."""
        if not os.path.exists(episode_file):
            return False

        try:
            with open(episode_file, 'r') as f:
                episode_data = yaml.safe_load(f)
            
            # Basic validation
            required_fields = ['episode', 'theme', 'milestones', 'tasks']
            return all(field in episode_data for field in required_fields)
        except Exception:
            return False

    def initialize_episode(self, episode_file: str) -> bool:
        """Initialize a new episode."""
        if not self.validate_episode(episode_file):
            return False

        # Load episode data
        with open(episode_file, 'r') as f:
            episode_data = yaml.safe_load(f)

        # Initialize systems
        self.promotion_system._load_state()
        self.reflection_engine._load_config()
        self.empathy_logger._load_state()

        return True

    def get_episode_status(self) -> Dict:
        """Get the current episode status."""
        return {
            "promotion_system": self.promotion_system.get_system_metrics(),
            "reflection_engine": self.reflection_engine.get_config(),
            "empathy_logger": self.empathy_logger.get_system_metrics()
        } 