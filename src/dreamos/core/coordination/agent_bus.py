# --- Simple Pub/Sub Implementation ---

import asyncio
import logging
import time
import uuid
from collections import defaultdict, deque
from typing import (
    Any,
    Callable,
    Coroutine,
    DefaultDict,
    Deque,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

from pydantic import ValidationError

from ..events.base_event import BaseDreamEvent
from .event_types import EventType

# Corrected relative imports (assuming events and errors are siblings under core)
# REMOVED Obsolete Edit/TODO comments


class BusError(Exception):
    """Base exception for AgentBus errors."""


class TopicNotFoundError(BusError):
    """Raised when a topic is not found."""


class SubscriberCallbackError(BusError):
    """Raised when a subscriber callback fails."""


class MessageValidationError(BusError):
    """Raised when message validation fails."""


# DELETE START: Remove duplicate/obsolete AgentBus skeleton
# class AgentBus:
#     """
#     An asynchronous event bus for inter-agent and system communication.
#
#     Handles event subscription, publishing, and basic error handling.
#     Uses asyncio for non-blocking operations.
#
#     Core Concepts:
#         - Topics: Hierarchical strings (e.g., "agent.status.online", "task.lifecycle.created").
#         - Events: Pydantic models inheriting from BaseEvent, containing data.
#         - Subscribers: Coroutine functions that handle specific event types on topics.
#         - Wildcards: Supports single-level (#) and multi-level (*) wildcards in topic subscriptions.
#     """
#
#     # ... existing code ...
# DELETE END

# --- Simple Pub/Sub Implementation ---
