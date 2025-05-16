from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid
import logging

class AgentMessage(BaseModel):
    """Schema for messages exchanged between agents."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: str = Field(..., description="Type of message (task, status, blocker, command, response)")
    sender_id: str = Field(..., description="ID of the sending agent")
    recipient_id: str = Field(..., description="ID of the receiving agent")
    content: Dict[str, Any] = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    in_response_to: Optional[str] = Field(None, description="ID of the message this is responding to")
    requires_ack: bool = Field(default=False, description="Whether this message requires acknowledgment")
    priority: str = Field(default="NORMAL", description="Message priority (HIGH, NORMAL, LOW)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

def create_message(
    message_type: str,
    sender_id: str,
    recipient_id: str,
    content: Dict[str, Any],
    in_response_to: Optional[str] = None,
    requires_ack: bool = False,
    priority: str = "NORMAL"
) -> AgentMessage:
    """Helper function to create a new message."""
    return AgentMessage(
        message_type=message_type,
        sender_id=sender_id,
        recipient_id=recipient_id,
        content=content,
        in_response_to=in_response_to,
        requires_ack=requires_ack,
        priority=priority
    )

# Message type constants
MESSAGE_TYPES = {
    "TASK": "task",
    "STATUS": "status",
    "BLOCKER": "blocker",
    "COMMAND": "command",
    "RESPONSE": "response"
}

# Priority levels
PRIORITY_LEVELS = {
    "HIGH": "HIGH",
    "NORMAL": "NORMAL",
    "LOW": "LOW"
}

# Common message content templates
def create_task_message(
    task_id: str,
    action: str,
    details: Dict[str, Any],
    sender_id: str,
    recipient_id: str,
    requires_ack: bool = True
) -> AgentMessage:
    """Create a task-related message."""
    return create_message(
        message_type=MESSAGE_TYPES["TASK"],
        sender_id=sender_id,
        recipient_id=recipient_id,
        content={
            "task_id": task_id,
            "action": action,
            "details": details
        },
        requires_ack=requires_ack,
        priority=PRIORITY_LEVELS["HIGH"]
    )

def create_status_message(
    status: str,
    details: Dict[str, Any],
    sender_id: str,
    recipient_id: str,
    requires_ack: bool = False
) -> AgentMessage:
    """Create a status update message."""
    return create_message(
        message_type=MESSAGE_TYPES["STATUS"],
        sender_id=sender_id,
        recipient_id=recipient_id,
        content={
            "status": status,
            "details": details
        },
        requires_ack=requires_ack,
        priority=PRIORITY_LEVELS["NORMAL"]
    )

def create_blocker_message(
    blocker_type: str,
    description: str,
    details: Dict[str, Any],
    sender_id: str,
    recipient_id: str,
    requires_ack: bool = True
) -> AgentMessage:
    """Create a blocker notification message."""
    return create_message(
        message_type=MESSAGE_TYPES["BLOCKER"],
        sender_id=sender_id,
        recipient_id=recipient_id,
        content={
            "blocker_type": blocker_type,
            "description": description,
            "details": details
        },
        requires_ack=requires_ack,
        priority=PRIORITY_LEVELS["HIGH"]
    )

def create_command_message(
    command: str,
    parameters: Dict[str, Any],
    sender_id: str,
    recipient_id: str,
    requires_ack: bool = True
) -> AgentMessage:
    """Create a command message."""
    return create_message(
        message_type=MESSAGE_TYPES["COMMAND"],
        sender_id=sender_id,
        recipient_id=recipient_id,
        content={
            "command": command,
            "parameters": parameters
        },
        requires_ack=requires_ack,
        priority=PRIORITY_LEVELS["HIGH"]
    )

def create_response_message(
    status: str,
    details: Dict[str, Any],
    sender_id: str,
    recipient_id: str,
    in_response_to: str,
    requires_ack: bool = False
) -> AgentMessage:
    """Create a response message."""
    return create_message(
        message_type=MESSAGE_TYPES["RESPONSE"],
        sender_id=sender_id,
        recipient_id=recipient_id,
        content={
            "status": status,
            "details": details
        },
        in_response_to=in_response_to,
        requires_ack=requires_ack,
        priority=PRIORITY_LEVELS["NORMAL"]
    )

class MessageSchema:
    """Message schema for validation."""
    
    def __init__(self):
        """Initialize message schema."""
        self.logger = logging.getLogger(__name__)
        self.required_fields = {
            'type': str,
            'metadata': dict
        }
        self.valid_types = [
            'task_assignment',
            'task_completion',
            'error',
            'status_update',
            'autonomy_decision',
            'recovery_trigger'
        ]
        self.required_metadata = {
            'timestamp': (int, float),
            'source': str
        }
        
    def validate_message(self, message: Dict) -> bool:
        """Validate message against schema.
        
        Args:
            message: Message dictionary to validate
            
        Returns:
            bool: True if message is valid
        """
        try:
            # Check required fields
            for field, field_type in self.required_fields.items():
                if field not in message:
                    self.logger.error(f"Missing required field: {field}")
                    return False
                if not isinstance(message[field], field_type):
                    self.logger.error(f"Invalid type for field {field}: expected {field_type}")
                    return False
                    
            # Validate message type
            if message['type'] not in self.valid_types:
                self.logger.error(f"Invalid message type: {message['type']}")
                return False
                
            # Validate metadata
            metadata = message.get('metadata', {})
            for field, field_type in self.required_metadata.items():
                if field not in metadata:
                    self.logger.error(f"Missing required metadata field: {field}")
                    return False
                if not isinstance(metadata[field], field_type):
                    self.logger.error(f"Invalid type for metadata field {field}: expected {field_type}")
                    return False
                    
            # Type-specific validation
            if message['type'] == 'task_assignment':
                if 'task_id' not in message:
                    self.logger.error("Missing task_id in task assignment")
                    return False
                    
            elif message['type'] == 'task_completion':
                if 'task_id' not in message:
                    self.logger.error("Missing task_id in task completion")
                    return False
                    
            elif message['type'] == 'error':
                if 'error_type' not in message:
                    self.logger.error("Missing error_type in error message")
                    return False
                    
            elif message['type'] == 'status_update':
                if 'status' not in message:
                    self.logger.error("Missing status in status update")
                    return False
                    
            elif message['type'] == 'autonomy_decision':
                if 'decision' not in message:
                    self.logger.error("Missing decision in autonomy decision")
                    return False
                    
            elif message['type'] == 'recovery_trigger':
                if 'error_type' not in message:
                    self.logger.error("Missing error_type in recovery trigger")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating message: {e}")
            return False 