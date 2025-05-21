"""
Dream.OS Checkpoint Validation

This module provides utilities for validating agent checkpoint implementations
against the Checkpoint Protocol defined in docs/vision/CHECKPOINT_PROTOCOL.md.
"""

from .verification_tool import CheckpointVerifier, ValidationResult, IntervalResult, RestorationResult

__all__ = [
    'CheckpointVerifier',
    'ValidationResult',
    'IntervalResult',
    'RestorationResult'
] 