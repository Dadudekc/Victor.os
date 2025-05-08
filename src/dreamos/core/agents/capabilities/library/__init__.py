"""Library of predefined or standard agent capabilities.

This package collects implementations or definitions of common capabilities
that can be registered or used by agents.
"""

# This __init__.py can be used to expose specific capabilities or categories
# from the modules within this library package.
from .task_rewrite import (
    task_rewrite_capability,
    TASK_REWRITE_CAPABILITY_INFO,
    TASK_REWRITE_CAPABILITY_ID,
)

__all__ = [
    "task_rewrite_capability",
    "TASK_REWRITE_CAPABILITY_INFO",
    "TASK_REWRITE_CAPABILITY_ID",
] 