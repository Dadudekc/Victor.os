# src/dreamos/core/coordination/event_types.py
# -*- coding: utf-8 -*-
"""Defines the canonical EventType enum for the DreamOS AgentBus.

Consolidated here to resolve inconsistencies and potential file corruption
in agent_bus.py.
"""

from enum import Enum


class EventType(Enum):
    """Enumeration of standardized event types for AgentBus communication.

    Uses hierarchical dot notation for topic structure:
    e.g., scope.domain.resource.action[.status]
    """

    # === System Events ===
    # Docstring: Events related to the overall DreamOS system state and agent lifecycle management.
    SYSTEM_ERROR = "dreamos.system.error"
    SYSTEM_AGENT_REGISTERED = "dreamos.system.agent.registered"
    SYSTEM_AGENT_UNREGISTERED = "dreamos.system.agent.unregistered"
    SYSTEM_AGENT_STATUS_CHANGE = "dreamos.system.agent.status_change"
    SYSTEM_SHUTDOWN_REQUEST = "dreamos.system.shutdown.request"
    SYSTEM_SHUTDOWN_READY = "dreamos.system.shutdown.ready"  # Agent reports ready
    SYSTEM_SHUTDOWN_COMPLETE = "dreamos.system.shutdown.complete"  # Bus signals done

    # === Agent Status Events (Published by Agents) ===
    # Docstring: Events broadcast by individual agents about their internal state or lifecycle.
    AGENT_STARTED = "dreamos.agent.lifecycle.started"
    AGENT_STOPPED = "dreamos.agent.lifecycle.stopped"
    AGENT_STATUS_UPDATE = (
        "dreamos.agent.status.updated"  # General status like IDLE, WORKING
    )
    AGENT_HEARTBEAT = "dreamos.agent.status.heartbeat"
    AGENT_ERROR = "dreamos.agent.error"
    AGENT_BLOCKED = "dreamos.agent.status.blocked"
    AGENT_UNBLOCKED = "dreamos.agent.status.unblocked"
    AGENT_CONTRACT_STATUS = "dreamos.agent.contract.status"  # Response to query
    AGENT_PROMPT_REQUEST = "dreamos.agent.prompt.request"  # Agent asking for prompt
    AGENT_PROMPT_RESPONSE = (
        "dreamos.agent.prompt.response"  # Agent providing LLM response
    )
    AGENT_OUTPUT = "dreamos.agent.output.generated"  # Generic agent output

    # === Task Lifecycle Events ===
    # Docstring: Events tracking the progression of tasks through the system.
    TASK_RECEIVED = "dreamos.task.lifecycle.received"  # Received by agent/system
    TASK_COMMAND = "dreamos.task.command"  # Specific command/task for an agent (often agent-specific topic)
    TASK_ASSIGNED = "dreamos.task.lifecycle.assigned"
    TASK_ACCEPTED = "dreamos.task.lifecycle.accepted"
    TASK_REJECTED = "dreamos.task.lifecycle.rejected"
    TASK_STARTED = "dreamos.task.lifecycle.started"
    TASK_PROGRESS = "dreamos.task.status.progress"
    TASK_COMPLETED = "dreamos.task.lifecycle.completed"
    TASK_FAILED = "dreamos.task.lifecycle.failed"
    TASK_VALIDATION_FAILED = "dreamos.task.validation.failed"
    TASK_STATUS_UPDATE = "dreamos.task.status.update"  # Generic status update

    # === Tool Events ===
    # Docstring: Events related to the invocation and results of tools used by agents.
    TOOL_CALL = "dreamos.tool.execution.call"
    TOOL_RESULT = "dreamos.tool.execution.result"

    # === Memory Events ===
    # Docstring: Events concerning agent interactions with memory systems.
    MEMORY_UPDATE = "dreamos.memory.operation.update"
    MEMORY_READ = "dreamos.memory.operation.read"
    MEMORY_DELETE = "dreamos.memory.operation.delete"
    MEMORY_QUERY = "dreamos.memory.operation.query"

    # === Coordination & Governance Events ===
    # Docstring: Events facilitating multi-agent coordination, supervision, and decision-making.
    COORDINATION_DIRECTIVE = "dreamos.coordination.directive"
    COORDINATION_PROPOSAL = "dreamos.coordination.proposal"
    SUPERVISOR_ALERT = "dreamos.coordination.supervisor.alert"
    SUPERVISOR_APPROVAL_REQUESTED = "dreamos.coordination.supervisor.approval.request"
    SUPERVISOR_APPROVAL_RESPONSE = "dreamos.coordination.supervisor.approval.response"
    VOTE_INITIATED = "dreamos.coordination.vote.initiated"
    VOTE_CAST = "dreamos.coordination.vote.cast"
    VOTE_RESULT = "dreamos.coordination.vote.result"

    # === Integration Specific Events ===
    # Docstring: Events related to interactions with external systems or specific integrations.
    # Cursor
    CURSOR_INJECT_REQUEST = "dreamos.integration.cursor.inject.request"
    CURSOR_RETRIEVE_REQUEST = "dreamos.integration.cursor.retrieve.request"
    CURSOR_OPERATION_RESULT = "dreamos.integration.cursor.operation.result"
    # ChatGPT Scraper (Consider standardizing)
    CHATGPT_RESPONSE_SCRAPED = "dreamos.integration.chatgpt.scraped.response"
    # Discord
    DISCORD_MESSAGE_RECEIVED = "dreamos.integration.discord.message.received"
    DISCORD_MESSAGE_SEND = "dreamos.integration.discord.message.send"

    # === Capability Registry Events (Added by Agent4) ===
    # Docstring: Events related to the Agent Capability Registry.
    SYSTEM_CAPABILITY_REGISTERED = "dreamos.system.capability.registered"
    SYSTEM_CAPABILITY_UNREGISTERED = "dreamos.system.capability.unregistered"

    # === Command Supervisor Events ===
    # Docstring: Events related to the secure command execution framework.
    COMMAND_EXECUTION_REQUEST = "dreamos.command.execution.request"
    COMMAND_APPROVAL_REQUEST = "dreamos.command.approval.request"
    COMMAND_APPROVAL_RESPONSE = "dreamos.command.approval.response"
    COMMAND_EXECUTION_RESULT = "dreamos.command.execution.result"

    def __str__(self):
        return self.value


__all__ = ["EventType"]
