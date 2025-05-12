"""
DreamOS Automation Module
Handles episode management, agent coordination, and system automation.
"""

from .episode import EpisodeManager
from .orchestrator import Orchestrator
from .reflection import ReflectionEngine
from .promotion import PromotionSystem
from .validation_utils import ValidationStatus, ValidationResult, ImprovementValidator

__all__ = [
    'EpisodeManager',
    'Orchestrator',
    'ReflectionEngine',
    'PromotionSystem',
    'ValidationStatus',
    'ValidationResult',
    'ImprovementValidator'
] 