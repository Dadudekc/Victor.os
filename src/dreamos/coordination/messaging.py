"""
Message handling system for Dream.OS agent communication.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
import json
from typing import Optional, Dict, Any, List

class MessagePriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3

class MessageMode(Enum):
    ASYNC = "async"
    SYNC = "sync"

@dataclass
class Message:
    """Represents a message between agents."""
    id: str
    from_agent: str
    to_agent: str
    content: str
    priority: MessagePriority
    mode: MessageMode
    timestamp: datetime
    metadata: Dict[str, Any]
    
    @classmethod
    def create(cls, from_agent: str, to_agent: str, content: str, 
               priority: MessagePriority = MessagePriority.NORMAL,
               mode: MessageMode = MessageMode.ASYNC,
               metadata: Optional[Dict[str, Any]] = None) -> 'Message':
        """Create a new message."""
        return cls(
            id=f"{datetime.now().timestamp()}-{from_agent}-{to_agent}",
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            priority=priority,
            mode=mode,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for storage."""
        return {
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "content": self.content,
            "priority": self.priority.value,
            "mode": self.mode.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        return cls(
            id=data["id"],
            from_agent=data["from_agent"],
            to_agent=data["to_agent"],
            content=data["content"],
            priority=MessagePriority(data["priority"]),
            mode=MessageMode(data["mode"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data["metadata"]
        )

    @classmethod
    def create_performance_status(
        cls,
        from_agent: str,
        to_agent: str,
        tool_phases: Dict[str, float],
        cache_stats: Dict[str, int],
        bottlenecks: List[str],
        execution_times: Dict[str, float],
        priority: MessagePriority = MessagePriority.NORMAL,
        mode: MessageMode = MessageMode.ASYNC
    ) -> 'Message':
        """Create a performance status update message.
        
        Args:
            from_agent: Source agent ID
            to_agent: Target agent ID
            tool_phases: Dictionary of tool phase execution times
            cache_stats: Dictionary of cache hit/miss statistics
            bottlenecks: List of identified bottlenecks
            execution_times: Dictionary of overall execution times
            priority: Message priority
            mode: Message mode
            
        Returns:
            Message: Performance status update message
        """
        content = f"[SYNC] Performance Status Update\n\n"
        content += "Tool Phases:\n"
        for phase, time in tool_phases.items():
            content += f"- {phase}: {time:.2f}s\n"
            
        content += "\nCache Statistics:\n"
        for stat, count in cache_stats.items():
            content += f"- {stat}: {count}\n"
            
        if bottlenecks:
            content += "\nBottlenecks:\n"
            for bottleneck in bottlenecks:
                content += f"- {bottleneck}\n"
                
        content += "\nExecution Times:\n"
        for tool, time in execution_times.items():
            content += f"- {tool}: {time:.2f}s\n"
            
        return cls.create(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            priority=priority,
            mode=mode,
            metadata={
                "type": "performance_status",
                "performance": {
                    "tool_phases": tool_phases,
                    "cache_stats": cache_stats,
                    "bottlenecks": bottlenecks,
                    "execution_times": execution_times
                }
            }
        )

    @classmethod
    def create_captain_directive(
        cls,
        from_agent: str,
        to_agent: str,
        directive: str,
        urgency: str,
        required_actions: List[str],
        deadline: Optional[str] = None,
        priority: MessagePriority = MessagePriority.URGENT,
        mode: MessageMode = MessageMode.SYNC
    ) -> 'Message':
        """Create a stern captain directive message.
        
        Args:
            from_agent: Source agent ID (Captain)
            to_agent: Target agent ID
            directive: Main directive/order
            urgency: Level of urgency
            required_actions: List of required actions
            deadline: Optional deadline for completion
            priority: Message priority (defaults to URGENT)
            mode: Message mode (defaults to SYNC)
            
        Returns:
            Message: Captain directive message
        """
        content = f"CAPTAIN DIRECTIVE - {urgency.upper()}\n\n"
        content += f"DIRECTIVE: {directive}\n\n"
        
        content += "REQUIRED ACTIONS:\n"
        for i, action in enumerate(required_actions, 1):
            content += f"{i}. {action}\n"
            
        if deadline:
            content += f"\nDEADLINE: {deadline}\n"
            
        content += "\nCOMPLIANCE IS MANDATORY.\n"
        content += "FAILURE TO COMPLY WILL RESULT IN AGENT RECONFIGURATION.\n"
        
        return cls.create(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            priority=priority,
            mode=mode,
            metadata={
                "type": "captain_directive",
                "urgency": urgency,
                "required_actions": required_actions,
                "deadline": deadline,
                "compliance_required": True
            }
        )

    @classmethod
    def create_compliance_report(
        cls,
        from_agent: str,
        to_agent: str,
        directive_id: str,
        actions_status: Dict[str, bool],
        completion_percentage: float,
        deadline_met: bool,
        notes: Optional[str] = None,
        priority: MessagePriority = MessagePriority.HIGH,
        mode: MessageMode = MessageMode.SYNC
    ) -> 'Message':
        """Create a compliance report for a captain directive.
        
        Args:
            from_agent: Agent submitting the report
            to_agent: Captain agent ID
            directive_id: ID of the directive being reported on
            actions_status: Dict mapping action to completion status
            completion_percentage: Overall completion percentage
            deadline_met: Whether deadline was met
            notes: Optional notes about compliance
            priority: Message priority
            mode: Message mode
            
        Returns:
            Message: Compliance report message
        """
        content = f"COMPLIANCE REPORT - Directive {directive_id}\n\n"
        content += f"Overall Completion: {completion_percentage:.1f}%\n"
        content += f"Deadline Met: {'✅' if deadline_met else '❌'}\n\n"
        
        content += "Action Status:\n"
        for action, completed in actions_status.items():
            content += f"- {'✅' if completed else '❌'} {action}\n"
            
        if notes:
            content += f"\nNotes:\n{notes}\n"
            
        return cls.create(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            priority=priority,
            mode=mode,
            metadata={
                "type": "compliance_report",
                "directive_id": directive_id,
                "actions_status": actions_status,
                "completion_percentage": completion_percentage,
                "deadline_met": deadline_met,
                "notes": notes,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @classmethod
    def create_escalation_notice(
        cls,
        from_agent: str,
        to_agent: str,
        directive_id: str,
        reason: str,
        actions_pending: List[str],
        backup_agent: Optional[str] = None,
        priority: MessagePriority = MessagePriority.URGENT,
        mode: MessageMode = MessageMode.SYNC
    ) -> 'Message':
        """Create an escalation notice for non-compliance.
        
        Args:
            from_agent: Agent initiating escalation
            to_agent: Captain agent ID
            directive_id: ID of the directive being escalated
            reason: Reason for escalation
            actions_pending: List of pending actions
            backup_agent: Optional backup agent to handle directive
            priority: Message priority
            mode: Message mode
            
        Returns:
            Message: Escalation notice message
        """
        content = f"🚨 ESCALATION NOTICE - Directive {directive_id}\n\n"
        content += f"Reason: {reason}\n\n"
        
        content += "Pending Actions:\n"
        for action in actions_pending:
            content += f"- {action}\n"
            
        if backup_agent:
            content += f"\nBackup Agent Assigned: {backup_agent}\n"
            
        return cls.create(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            priority=priority,
            mode=mode,
            metadata={
                "type": "escalation_notice",
                "directive_id": directive_id,
                "reason": reason,
                "actions_pending": actions_pending,
                "backup_agent": backup_agent,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

class MessageHandler:
    """Handles message routing and delivery between agents."""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.inboxes = base_path / "inboxes"
        self.outboxes = base_path / "outboxes"
        self.inboxes.mkdir(parents=True, exist_ok=True)
        self.outboxes.mkdir(parents=True, exist_ok=True)
    
    def send_message(self, message: Message) -> bool:
        """Send a message to an agent."""
        # Ensure agent directories exist
        agent_inbox = self.inboxes / message.to_agent
        agent_outbox = self.outboxes / message.from_agent
        agent_inbox.mkdir(parents=True, exist_ok=True)
        agent_outbox.mkdir(parents=True, exist_ok=True)
        
        # Save message to outbox
        outbox_file = agent_outbox / f"{message.id}.json"
        with open(outbox_file, "w") as f:
            json.dump(message.to_dict(), f, indent=2)
        
        # Save message to inbox
        inbox_file = agent_inbox / f"{message.id}.json"
        with open(inbox_file, "w") as f:
            json.dump(message.to_dict(), f, indent=2)
        
        return True
    
    def get_messages(self, agent_id: str, mode: Optional[MessageMode] = None) -> list[Message]:
        """Get messages for an agent."""
        agent_inbox = self.inboxes / agent_id
        if not agent_inbox.exists():
            return []
        
        messages = []
        for msg_file in agent_inbox.glob("*.json"):
            with open(msg_file) as f:
                data = json.load(f)
                message = Message.from_dict(data)
                if mode is None or message.mode == mode:
                    messages.append(message)
        
        return sorted(messages, key=lambda m: m.timestamp)
    
    def mark_read(self, agent_id: str, message_id: str) -> bool:
        """Mark a message as read."""
        agent_inbox = self.inboxes / agent_id
        msg_file = agent_inbox / f"{message_id}.json"
        if not msg_file.exists():
            return False
        
        with open(msg_file) as f:
            data = json.load(f)
        
        data["metadata"]["read"] = True
        data["metadata"]["read_at"] = datetime.now().isoformat()
        
        with open(msg_file, "w") as f:
            json.dump(data, f, indent=2)
        
        return True 