from typing import Dict, Any, Optional
from dreamos.models import Message, MessageType, MessagePriority

class MessageValidator:
    @staticmethod
    def format_protocol_violation_message(
        protocol: str,
        from_agent: str,
        violation: str,
        details: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a protocol violation message."""
        return Message(
            type=MessageType.PROTOCOL_VIOLATION,
            from_agent=from_agent,
            content={
                'protocol': protocol,
                'violation': violation,
                'details': details
            },
            metadata=metadata or {},
            priority=MessagePriority.HIGH
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
        return Message(
            type=MessageType.PROTOCOL_REMEDIATE,
            from_agent=from_agent,
            content={
                'protocol': protocol,
                'remediation': remediation,
                'details': details
            },
            metadata=metadata or {},
            priority=MessagePriority.HIGH
        )

    @staticmethod
    def format_protocol_audit_message(
        protocol: str,
        from_agent: str,
        audit: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a protocol audit message."""
        return Message(
            type=MessageType.PROTOCOL_AUDIT,
            from_agent=from_agent,
            content={
                'protocol': protocol,
                'audit': audit
            },
            metadata=metadata or {},
            priority=MessagePriority.MEDIUM
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
        return Message(
            type=MessageType.SWARM_VIOLATION,
            from_agent=from_agent,
            content={
                'swarm_id': swarm_id,
                'violation': violation,
                'details': details
            },
            metadata=metadata or {},
            priority=MessagePriority.HIGH
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
        return Message(
            type=MessageType.SWARM_REMEDIATE,
            from_agent=from_agent,
            content={
                'swarm_id': swarm_id,
                'remediation': remediation,
                'details': details
            },
            metadata=metadata or {},
            priority=MessagePriority.HIGH
        )

    @staticmethod
    def format_swarm_audit_message(
        swarm_id: str,
        from_agent: str,
        audit: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Format a swarm audit message."""
        return Message(
            type=MessageType.SWARM_AUDIT,
            from_agent=from_agent,
            content={
                'swarm_id': swarm_id,
                'audit': audit
            },
            metadata=metadata or {},
            priority=MessagePriority.MEDIUM
        ) 