"""
Message Protocol

Defines the message protocol, validation, and type system for agent communication.
"""

from enum import Enum
from datetime import datetime
from typing import Dict, Optional, Any, List
import json
import logging
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('message_protocol')

class MessageType(Enum):
    """Message types for agent communication."""
    SYNC = "SYNC"           # Synchronization message
    RESUME = "RESUME"       # Resume operation message
    ALERT = "ALERT"         # Alert/notification message
    RETRY = "RETRY"         # Retry operation message
    TASK = "TASK"          # Task assignment message
    STATUS = "STATUS"      # Status update message
    HEALTH = "HEALTH"      # Health check message
    COORD = "COORD"        # Coordination message
    CELL = "CELL"          # Cell phone message
    RESPONSE = "RESPONSE"  # Agent response message
    # Cellphone/bootstrapper specific types
    BOOTSTRAP = "BOOTSTRAP"  # Bootstrap initialization
    SWARM_JOIN = "SWARM_JOIN"  # Agent joining swarm
    SWARM_LEAVE = "SWARM_LEAVE"  # Agent leaving swarm
    PROTOCOL = "PROTOCOL"  # Protocol instruction/update
    DREAM_OS = "DREAM_OS"  # Dream.OS specific operations
    FACILITATE = "FACILITATE"  # Facilitation commands
    # Additional protocol types
    PROTOCOL_ACK = "PROTOCOL_ACK"  # Protocol acknowledgment
    PROTOCOL_ERROR = "PROTOCOL_ERROR"  # Protocol error
    PROTOCOL_UPDATE = "PROTOCOL_UPDATE"  # Protocol update
    PROTOCOL_SYNC = "PROTOCOL_SYNC"  # Protocol synchronization
    PROTOCOL_CHECK = "PROTOCOL_CHECK"  # Protocol compliance check
    PROTOCOL_REPORT = "PROTOCOL_REPORT"  # Protocol compliance report
    PROTOCOL_ENFORCE = "PROTOCOL_ENFORCE"  # Protocol enforcement
    PROTOCOL_VIOLATION = "PROTOCOL_VIOLATION"  # Protocol violation
    PROTOCOL_REMEDIATE = "PROTOCOL_REMEDIATE"  # Protocol remediation
    PROTOCOL_AUDIT = "PROTOCOL_AUDIT"  # Protocol audit
    # Swarm coordination types
    SWARM_SYNC = "SWARM_SYNC"  # Swarm synchronization
    SWARM_CHECK = "SWARM_CHECK"  # Swarm health check
    SWARM_REPORT = "SWARM_REPORT"  # Swarm status report
    SWARM_UPDATE = "SWARM_UPDATE"  # Swarm configuration update
    SWARM_ALERT = "SWARM_ALERT"  # Swarm alert/notification
    SWARM_ENFORCE = "SWARM_ENFORCE"  # Swarm enforcement
    SWARM_VIOLATION = "SWARM_VIOLATION"  # Swarm violation
    SWARM_REMEDIATE = "SWARM_REMEDIATE"  # Swarm remediation
    SWARM_AUDIT = "SWARM_AUDIT"  # Swarm audit

class MessagePriority(Enum):
    """Message priority levels."""
    HIGH = "high"      # Critical messages
    MEDIUM = "medium"  # Normal messages
    LOW = "low"        # Background messages

@dataclass
class Message:
    """Base message structure."""
    id: str
    type: MessageType
    content: Dict[str, Any]
    priority: MessagePriority
    timestamp: str
    status: str = "pending"
    from_agent: Optional[str] = None
    to_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        # Convert string enums back to enum values
        data['type'] = MessageType(data['type'])
        data['priority'] = MessagePriority(data['priority'])
        return cls(**data)

class MessageValidator:
    """Validates message structure and content."""

    @staticmethod
    def validate_message(message: Dict[str, Any]) -> tuple[bool, str]:
        """Validate message structure and content."""
        try:
            # Check required fields
            required_fields = {
                'id', 'type', 'content', 'priority', 
                'timestamp', 'status'
            }
            missing_fields = required_fields - set(message.keys())
            if missing_fields:
                return False, f"Missing required fields: {missing_fields}"

            # Validate message type
            try:
                msg_type = MessageType(message['type'])
            except ValueError:
                return False, f"Invalid message type: {message['type']}"

            # Cellphone-specific validation
            if msg_type in [MessageType.BOOTSTRAP, MessageType.SWARM_JOIN, MessageType.SWARM_LEAVE]:
                if not message.get('from_agent'):
                    return False, f"{msg_type.value} messages require from_agent"
                if not message.get('content', {}).get('agent_id'):
                    return False, f"{msg_type.value} messages require agent_id in content"
                if msg_type == MessageType.SWARM_JOIN and not message.get('content', {}).get('swarm_id'):
                    return False, "SWARM_JOIN messages require swarm_id in content"

            # Protocol message validation
            if msg_type in [MessageType.PROTOCOL, MessageType.PROTOCOL_ACK, MessageType.PROTOCOL_ERROR,
                          MessageType.PROTOCOL_UPDATE, MessageType.PROTOCOL_SYNC, MessageType.PROTOCOL_CHECK,
                          MessageType.PROTOCOL_REPORT, MessageType.PROTOCOL_ENFORCE, MessageType.PROTOCOL_VIOLATION,
                          MessageType.PROTOCOL_REMEDIATE, MessageType.PROTOCOL_AUDIT]:
                if not message.get('content', {}).get('protocol'):
                    return False, f"{msg_type.value} messages require protocol in content"
                if msg_type == MessageType.PROTOCOL and not message.get('content', {}).get('instruction'):
                    return False, "PROTOCOL messages require instruction in content"
                if msg_type == MessageType.PROTOCOL_ERROR and not message.get('content', {}).get('error'):
                    return False, "PROTOCOL_ERROR messages require error in content"
                if msg_type == MessageType.PROTOCOL_REPORT and not message.get('content', {}).get('report'):
                    return False, "PROTOCOL_REPORT messages require report in content"
                if msg_type == MessageType.PROTOCOL_VIOLATION and not message.get('content', {}).get('violation'):
                    return False, "PROTOCOL_VIOLATION messages require violation in content"
                if msg_type == MessageType.PROTOCOL_REMEDIATE and not message.get('content', {}).get('remediation'):
                    return False, "PROTOCOL_REMEDIATE messages require remediation in content"
                if msg_type == MessageType.PROTOCOL_AUDIT and not message.get('content', {}).get('audit'):
                    return False, "PROTOCOL_AUDIT messages require audit in content"

            # Swarm message validation
            if msg_type in [MessageType.SWARM_SYNC, MessageType.SWARM_CHECK, MessageType.SWARM_REPORT,
                          MessageType.SWARM_UPDATE, MessageType.SWARM_ALERT, MessageType.SWARM_ENFORCE,
                          MessageType.SWARM_VIOLATION, MessageType.SWARM_REMEDIATE, MessageType.SWARM_AUDIT]:
                if not message.get('content', {}).get('swarm_id'):
                    return False, f"{msg_type.value} messages require swarm_id in content"
                if msg_type == MessageType.SWARM_ALERT and not message.get('content', {}).get('alert'):
                    return False, "SWARM_ALERT messages require alert in content"
                if msg_type == MessageType.SWARM_REPORT and not message.get('content', {}).get('report'):
                    return False, "SWARM_REPORT messages require report in content"
                if msg_type == MessageType.SWARM_VIOLATION and not message.get('content', {}).get('violation'):
                    return False, "SWARM_VIOLATION messages require violation in content"
                if msg_type == MessageType.SWARM_REMEDIATE and not message.get('content', {}).get('remediation'):
                    return False, "SWARM_REMEDIATE messages require remediation in content"
                if msg_type == MessageType.SWARM_AUDIT and not message.get('content', {}).get('audit'):
                    return False, "SWARM_AUDIT messages require audit in content"

            # Validate priority
            try:
                MessagePriority(message['priority'])
            except ValueError:
                return False, f"Invalid priority: {message['priority']}"

            # Validate timestamp format
            try:
                datetime.fromisoformat(message['timestamp'].replace('Z', '+00:00'))
            except ValueError:
                return False, f"Invalid timestamp format: {message['timestamp']}"

            # Validate content is dict
            if not isinstance(message['content'], dict):
                return False, "Content must be a dictionary"

            # Validate status
            valid_statuses = {'pending', 'delivered', 'read', 'failed'}
            if message['status'] not in valid_statuses:
                return False, f"Invalid status: {message['status']}"

            return True, "Valid message"

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    @staticmethod
    def format_bootstrap_message(
        agent_id: str,
        from_agent: str,
        swarm_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a bootstrap message for agent initialization."""
        return MessageValidator.format_message(
            msg_type=MessageType.BOOTSTRAP,
            content={
                "agent_id": agent_id,
                "swarm_id": swarm_id,
                "protocol_version": "1.0",
                "capabilities": ["dream_os", "swarm_coordination"],
                "bootstrap_time": datetime.now().isoformat()
            },
            priority=MessagePriority.HIGH,
            from_agent=from_agent,
            metadata=metadata
        )

    @staticmethod
    def format_swarm_join_message(
        agent_id: str,
        from_agent: str,
        swarm_id: str,
        capabilities: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a swarm join message."""
        return MessageValidator.format_message(
            msg_type=MessageType.SWARM_JOIN,
            content={
                "agent_id": agent_id,
                "swarm_id": swarm_id,
                "capabilities": capabilities,
                "join_time": datetime.now().isoformat()
            },
            priority=MessagePriority.HIGH,
            from_agent=from_agent,
            metadata=metadata
        )

    @staticmethod
    def format_protocol_message(
        protocol: str,
        instruction: str,
        from_agent: str,
        to_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a protocol instruction message."""
        return MessageValidator.format_message(
            msg_type=MessageType.PROTOCOL,
            content={
                "protocol": protocol,
                "instruction": instruction,
                "timestamp": datetime.now().isoformat()
            },
            priority=MessagePriority.HIGH,
            from_agent=from_agent,
            to_agent=to_agent,
            metadata=metadata
        )

    @staticmethod
    def format_facilitate_message(
        action: str,
        target_agent: str,
        from_agent: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a facilitation message."""
        return MessageValidator.format_message(
            msg_type=MessageType.FACILITATE,
            content={
                "action": action,
                "target_agent": target_agent,
                **content
            },
            priority=MessagePriority.HIGH,
            from_agent=from_agent,
            metadata=metadata
        )

    @staticmethod
    def format_dream_os_message(
        operation: str,
        from_agent: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a Dream.OS specific message."""
        return MessageValidator.format_message(
            msg_type=MessageType.DREAM_OS,
            content={
                "operation": operation,
                "timestamp": datetime.now().isoformat(),
                **content
            },
            priority=MessagePriority.HIGH,
            from_agent=from_agent,
            metadata=metadata
        )

    @staticmethod
    def format_protocol_ack_message(
        protocol: str,
        from_agent: str,
        to_agent: str,
        ack_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a protocol acknowledgment message."""
        return MessageValidator.format_message(
            msg_type=MessageType.PROTOCOL_ACK,
            content={
                "protocol": protocol,
                "ack_id": ack_id,
                "status": status,
                "timestamp": datetime.now().isoformat()
            },
            priority=MessagePriority.HIGH,
            from_agent=from_agent,
            to_agent=to_agent,
            metadata=metadata
        )

    @staticmethod
    def format_protocol_error_message(
        protocol: str,
        from_agent: str,
        error: str,
        details: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a protocol error message."""
        return MessageValidator.format_message(
            msg_type=MessageType.PROTOCOL_ERROR,
            content={
                "protocol": protocol,
                "error": error,
                "details": details,
                "timestamp": datetime.now().isoformat()
            },
            priority=MessagePriority.HIGH,
            from_agent=from_agent,
            metadata=metadata
        )

    @staticmethod
    def format_swarm_sync_message(
        swarm_id: str,
        from_agent: str,
        sync_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a swarm synchronization message."""
        return MessageValidator.format_message(
            msg_type=MessageType.SWARM_SYNC,
            content={
                "swarm_id": swarm_id,
                "sync_data": sync_data,
                "timestamp": datetime.now().isoformat()
            },
            priority=MessagePriority.HIGH,
            from_agent=from_agent,
            metadata=metadata
        )

    @staticmethod
    def format_swarm_alert_message(
        swarm_id: str,
        from_agent: str,
        alert: str,
        severity: str,
        details: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a swarm alert message."""
        return MessageValidator.format_message(
            msg_type=MessageType.SWARM_ALERT,
            content={
                "swarm_id": swarm_id,
                "alert": alert,
                "severity": severity,
                "details": details,
                "timestamp": datetime.now().isoformat()
            },
            priority=MessagePriority.HIGH,
            from_agent=from_agent,
            metadata=metadata
        )

    @staticmethod
    def format_protocol_violation_message(
        protocol: str,
        from_agent: str,
        violation: str,
        details: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a protocol violation message."""
        return MessageValidator.format_message(
            msg_type=MessageType.PROTOCOL_VIOLATION,
            content={
                "protocol": protocol,
                "violation": violation,
                "details": details,
                "timestamp": datetime.now().isoformat()
            },
            priority=MessagePriority.HIGH,
            from_agent=from_agent,
            metadata=metadata
        )

    @staticmethod
    def format_protocol_remediate_message(
        protocol: str,
        from_agent: str,
        remediation: str,
        details: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a protocol remediation message."""
        return MessageValidator.format_message(
            msg_type=MessageType.PROTOCOL_REMEDIATE,
            content={
                "protocol": protocol,
                "remediation": remediation,
                "details": details,
                "timestamp": datetime.now().isoformat()
            },
            priority=MessagePriority.HIGH,
            from_agent=from_agent,
            metadata=metadata
        )

    @staticmethod
    def format_protocol_audit_message(
        protocol: str,
        from_agent: str,
        audit: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a protocol audit message."""
        return MessageValidator.format_message(
            msg_type=MessageType.PROTOCOL_AUDIT,
            content={
                "protocol": protocol,
                "audit": audit,
                "timestamp": datetime.now().isoformat()
            },
            priority=MessagePriority.HIGH,
            from_agent=from_agent,
            metadata=metadata
        )

    @staticmethod
    def format_swarm_violation_message(
        swarm_id: str,
        from_agent: str,
        violation: str,
        details: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a swarm violation message."""
        return MessageValidator.format_message(
            msg_type=MessageType.SWARM_VIOLATION,
            content={
                "swarm_id": swarm_id,
                "violation": violation,
                "details": details,
                "timestamp": datetime.now().isoformat()
            },
            priority=MessagePriority.HIGH,
            from_agent=from_agent,
            metadata=metadata
        )

    @staticmethod
    def format_swarm_remediate_message(
        swarm_id: str,
        from_agent: str,
        remediation: str,
        details: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a swarm remediation message."""
        return MessageValidator.format_message(
            msg_type=MessageType.SWARM_REMEDIATE,
            content={
                "swarm_id": swarm_id,
                "remediation": remediation,
                "details": details,
                "timestamp": datetime.now().isoformat()
            },
            priority=MessagePriority.HIGH,
            from_agent=from_agent,
            metadata=metadata
        )

    @staticmethod
    def format_swarm_audit_message(
        swarm_id: str,
        from_agent: str,
        audit: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a swarm audit message."""
        return MessageValidator.format_message(
            msg_type=MessageType.SWARM_AUDIT,
            content={
                "swarm_id": swarm_id,
                "audit": audit,
                "timestamp": datetime.now().isoformat()
            },
            priority=MessagePriority.HIGH,
            from_agent=from_agent,
            metadata=metadata
        )

    @staticmethod
    def format_message(
        msg_type: MessageType,
        content: Dict[str, Any],
        priority: MessagePriority,
        from_agent: Optional[str] = None,
        to_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a new message with proper structure."""
        return Message(
            id=MessageValidator._generate_message_id(),
            type=msg_type,
            content=content,
            priority=priority,
            timestamp=datetime.now().isoformat(),
            from_agent=from_agent,
            to_agent=to_agent,
            metadata=metadata
        )

    @staticmethod
    def _generate_message_id() -> str:
        """Generate a unique message ID."""
        return f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

class MessageFormatter:
    """Formats messages for different outputs."""

    @staticmethod
    def to_json(message: Message) -> str:
        """Convert message to JSON string."""
        return json.dumps(message.to_dict(), indent=2)

    @staticmethod
    def from_json(json_str: str) -> Message:
        """Create message from JSON string."""
        data = json.loads(json_str)
        return Message.from_dict(data)

    @staticmethod
    def to_log(message: Message) -> str:
        """Format message for logging."""
        return (
            f"[{message.id}] {message.type.value} "
            f"({message.priority.value}) "
            f"from={message.from_agent or 'system'} "
            f"to={message.to_agent or 'all'}"
        )

def main():
    """Example usage of message protocol."""
    # Create a test message
    message = MessageValidator.format_message(
        msg_type=MessageType.ALERT,
        content={"text": "Test alert"},
        priority=MessagePriority.HIGH,
        from_agent="Agent-1",
        to_agent="Agent-2"
    )

    # Validate message
    is_valid, reason = MessageValidator.validate_message(message.to_dict())
    print(f"Message valid: {is_valid}")
    print(f"Reason: {reason}")

    # Format as JSON
    json_str = MessageFormatter.to_json(message)
    print(f"\nJSON format:\n{json_str}")

    # Format for logging
    log_str = MessageFormatter.to_log(message)
    print(f"\nLog format:\n{log_str}")

if __name__ == "__main__":
    main() 