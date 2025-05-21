from enum import Enum

class MessageType(Enum):
    # ... existing message types ...
    PROTOCOL_VIOLATION = "protocol_violation"
    PROTOCOL_REMEDIATE = "protocol_remediate"
    PROTOCOL_AUDIT = "protocol_audit"
    SWARM_VIOLATION = "swarm_violation"
    SWARM_REMEDIATE = "swarm_remediate"
    SWARM_AUDIT = "swarm_audit"

# ... existing code ... 