"""
Dream.OS Ethos Package

This package implements the core ethos validation and enforcement system,
ensuring all agents operate within the defined ethical and operational boundaries.
"""

from .identity import AgentIdentity, create_agent
from .validator import EthosValidator
from .logger import EmpathyLogger
from .compliance import (
    ValueCompliance,
    PrincipleCompliance,
    SafeguardCompliance
)

__all__ = [
    'AgentIdentity',
    'create_agent',
    'EthosValidator',
    'EmpathyLogger',
    'ValueCompliance',
    'PrincipleCompliance',
    'SafeguardCompliance'
] 