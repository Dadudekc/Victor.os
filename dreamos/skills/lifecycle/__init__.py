"""
Dream.OS Agent Lifecycle Utilities

This module provides utilities for managing agent lifecycle and autonomous loop stability.
"""

from .loop_guard import LoopGuard
from .circuit_breaker import CircuitBreaker
from .degraded_mode import DegradedOperationMode, AlternativeActions
from .stable_loop import StableAutonomousLoop

__all__ = [
    'LoopGuard',
    'CircuitBreaker',
    'DegradedOperationMode',
    'AlternativeActions',
    'StableAutonomousLoop',
] 