"""
Message Queue Manager

Handles message queuing and processing for agent communication.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from .message_protocol import (
    Message, MessageType, MessagePriority,
    MessageValidator, MessageFormatter
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('message_queue')

class MessageQueueManager:
    def __init__(self):
        self.queue_file = Path("runtime/agent_comms/coordination/message_queue.json")
        self.archive_file = Path("runtime/agent_comms/coordination/message_archive.json")
        self.swarm_file = Path("runtime/agent_comms/coordination/swarm_status.json")
        self.protocol_file = Path("runtime/agent_comms/coordination/protocol_status.json")
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        self.queue: Dict[str, List[Message]] = {
            MessagePriority.HIGH.value: [],    # Critical messages
            MessagePriority.MEDIUM.value: [],  # Normal messages
            MessagePriority.LOW.value: []      # Background messages
        }
        self.swarm_status: Dict[str, Dict[str, Any]] = {}
        self.protocol_status: Dict[str, Dict[str, Any]] = {}
        self.protocol_violations: Dict[str, List[Dict[str, Any]]] = {}
        self.swarm_violations: Dict[str, List[Dict[str, Any]]] = {}
        self.protocol_remediations: Dict[str, List[Dict[str, Any]]] = {}
        self.swarm_remediations: Dict[str, List[Dict[str, Any]]] = {}
        self.protocol_audits: Dict[str, List[Dict[str, Any]]] = {}
        self.swarm_audits: Dict[str, List[Dict[str, Any]]] = {}
        self.load_queue()
        self.load_swarm_status()
        self.load_protocol_status()
        self.load_violations()
        self.load_remediations()
        self.load_audits()
        
    def load_queue(self):
        """Load message queue from file."""
        try:
            if self.queue_file.exists():
                with open(self.queue_file, 'r') as f:
                    data = json.load(f)
                    # Convert dict messages back to Message objects
                    self.queue = {
                        priority: [Message.from_dict(msg) for msg in messages]
                        for priority, messages in data.items()
                    }
            else:
                self.save_queue()
        except Exception as e:
            logger.error(f"Error loading queue: {e}")
            # Initialize empty queues on error
            self.queue = {
                MessagePriority.HIGH.value: [],
                MessagePriority.MEDIUM.value: [],
                MessagePriority.LOW.value: []
            }
            
    def save_queue(self):
        """Save message queue to file."""
        try:
            # Convert Message objects to dicts
            data = {
                priority: [msg.to_dict() for msg in messages]
                for priority, messages in self.queue.items()
            }
            with open(self.queue_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving queue: {e}")
            
    def load_swarm_status(self):
        """Load swarm status from file."""
        try:
            if self.swarm_file.exists():
                with open(self.swarm_file, 'r') as f:
                    self.swarm_status = json.load(f)
            else:
                self.save_swarm_status()
        except Exception as e:
            logger.error(f"Error loading swarm status: {e}")
            self.swarm_status = {}

    def save_swarm_status(self):
        """Save swarm status to file."""
        try:
            with open(self.swarm_file, 'w') as f:
                json.dump(self.swarm_status, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving swarm status: {e}")

    def load_protocol_status(self):
        """Load protocol status from file."""
        try:
            if self.protocol_file.exists():
                with open(self.protocol_file, 'r') as f:
                    self.protocol_status = json.load(f)
            else:
                self.save_protocol_status()
        except Exception as e:
            logger.error(f"Error loading protocol status: {e}")
            self.protocol_status = {}

    def save_protocol_status(self):
        """Save protocol status to file."""
        try:
            with open(self.protocol_file, 'w') as f:
                json.dump(self.protocol_status, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving protocol status: {e}")

    def load_violations(self):
        """Load protocol and swarm violations from file."""
        try:
            violations_file = Path("runtime/agent_comms/coordination/violations.json")
            if violations_file.exists():
                with open(violations_file, 'r') as f:
                    data = json.load(f)
                    self.protocol_violations = data.get('protocol', {})
                    self.swarm_violations = data.get('swarm', {})
            else:
                self.save_violations()
        except Exception as e:
            logger.error(f"Error loading violations: {e}")
            self.protocol_violations = {}
            self.swarm_violations = {}

    def save_violations(self):
        """Save protocol and swarm violations to file."""
        try:
            violations_file = Path("runtime/agent_comms/coordination/violations.json")
            data = {
                'protocol': self.protocol_violations,
                'swarm': self.swarm_violations
            }
            with open(violations_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving violations: {e}")

    def load_remediations(self):
        """Load protocol and swarm remediations from file."""
        try:
            remediations_file = Path("runtime/agent_comms/coordination/remediations.json")
            if remediations_file.exists():
                with open(remediations_file, 'r') as f:
                    data = json.load(f)
                    self.protocol_remediations = data.get('protocol', {})
                    self.swarm_remediations = data.get('swarm', {})
            else:
                self.save_remediations()
        except Exception as e:
            logger.error(f"Error loading remediations: {e}")
            self.protocol_remediations = {}
            self.swarm_remediations = {}

    def save_remediations(self):
        """Save protocol and swarm remediations to file."""
        try:
            remediations_file = Path("runtime/agent_comms/coordination/remediations.json")
            data = {
                'protocol': self.protocol_remediations,
                'swarm': self.swarm_remediations
            }
            with open(remediations_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving remediations: {e}")

    def load_audits(self):
        """Load protocol and swarm audits from file."""
        try:
            audits_file = Path("runtime/agent_comms/coordination/audits.json")
            if audits_file.exists():
                with open(audits_file, 'r') as f:
                    data = json.load(f)
                    self.protocol_audits = data.get('protocol', {})
                    self.swarm_audits = data.get('swarm', {})
            else:
                self.save_audits()
        except Exception as e:
            logger.error(f"Error loading audits: {e}")
            self.protocol_audits = {}
            self.swarm_audits = {}

    def save_audits(self):
        """Save protocol and swarm audits to file."""
        try:
            audits_file = Path("runtime/agent_comms/coordination/audits.json")
            data = {
                'protocol': self.protocol_audits,
                'swarm': self.swarm_audits
            }
            with open(audits_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving audits: {e}")

    def handle_bootstrap(self, message: Message) -> bool:
        """Handle bootstrap message."""
        try:
            agent_id = message.content['agent_id']
            swarm_id = message.content.get('swarm_id')
            
            # Initialize agent in swarm
            if swarm_id:
                if swarm_id not in self.swarm_status:
                    self.swarm_status[swarm_id] = {
                        "agents": {},
                        "created_at": datetime.now().isoformat()
                    }
                
                self.swarm_status[swarm_id]["agents"][agent_id] = {
                    "status": "bootstrapping",
                    "capabilities": message.content.get('capabilities', []),
                    "joined_at": datetime.now().isoformat(),
                    "last_seen": datetime.now().isoformat()
                }
                
                self.save_swarm_status()
                logger.info(f"Agent {agent_id} bootstrapped in swarm {swarm_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error handling bootstrap: {e}")
            return False

    def handle_swarm_join(self, message: Message) -> bool:
        """Handle swarm join message."""
        try:
            agent_id = message.content['agent_id']
            swarm_id = message.content['swarm_id']
            
            if swarm_id in self.swarm_status:
                self.swarm_status[swarm_id]["agents"][agent_id] = {
                    "status": "active",
                    "capabilities": message.content.get('capabilities', []),
                    "joined_at": datetime.now().isoformat(),
                    "last_seen": datetime.now().isoformat()
                }
                
                self.save_swarm_status()
                logger.info(f"Agent {agent_id} joined swarm {swarm_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error handling swarm join: {e}")
            return False

    def handle_swarm_leave(self, message: Message) -> bool:
        """Handle swarm leave message."""
        try:
            agent_id = message.content['agent_id']
            swarm_id = message.content.get('swarm_id')
            
            if swarm_id and swarm_id in self.swarm_status:
                if agent_id in self.swarm_status[swarm_id]["agents"]:
                    self.swarm_status[swarm_id]["agents"][agent_id]["status"] = "inactive"
                    self.swarm_status[swarm_id]["agents"][agent_id]["left_at"] = datetime.now().isoformat()
                    self.save_swarm_status()
                    logger.info(f"Agent {agent_id} left swarm {swarm_id}")
                    return True
            return False
            
        except Exception as e:
            logger.error(f"Error handling swarm leave: {e}")
            return False

    def get_swarm_status(self, swarm_id: Optional[str] = None) -> Dict:
        """Get swarm status."""
        try:
            if swarm_id:
                return self.swarm_status.get(swarm_id, {})
            return self.swarm_status
        except Exception as e:
            logger.error(f"Error getting swarm status: {e}")
            return {}

    def handle_protocol_message(self, message: Message) -> bool:
        """Handle protocol-related messages."""
        try:
            protocol = message.content['protocol']
            
            if message.type == MessageType.PROTOCOL:
                # Initialize protocol status if not exists
                if protocol not in self.protocol_status:
                    self.protocol_status[protocol] = {
                        "status": "active",
                        "last_updated": datetime.now().isoformat(),
                        "agents": {}
                    }
                
                # Update protocol status
                self.protocol_status[protocol]["last_updated"] = datetime.now().isoformat()
                if message.to_agent:
                    self.protocol_status[protocol]["agents"][message.to_agent] = {
                        "status": "pending",
                        "last_instruction": message.content.get('instruction'),
                        "timestamp": datetime.now().isoformat()
                    }
                
                self.save_protocol_status()
                logger.info(f"Protocol instruction sent: {protocol}")
                return True
                
            elif message.type == MessageType.PROTOCOL_ACK:
                if protocol in self.protocol_status and message.from_agent:
                    self.protocol_status[protocol]["agents"][message.from_agent] = {
                        "status": message.content.get('status', 'unknown'),
                        "last_ack": message.content.get('ack_id'),
                        "timestamp": datetime.now().isoformat()
                    }
                    self.save_protocol_status()
                    logger.info(f"Protocol acknowledgment received from {message.from_agent}")
                    return True
                    
            elif message.type == MessageType.PROTOCOL_ERROR:
                if protocol in self.protocol_status and message.from_agent:
                    self.protocol_status[protocol]["agents"][message.from_agent] = {
                        "status": "error",
                        "error": message.content.get('error'),
                        "timestamp": datetime.now().isoformat()
                    }
                    self.save_protocol_status()
                    logger.error(f"Protocol error from {message.from_agent}: {message.content.get('error')}")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error handling protocol message: {e}")
            return False

    def handle_swarm_message(self, message: Message) -> bool:
        """Handle swarm-related messages."""
        try:
            swarm_id = message.content['swarm_id']
            
            if message.type == MessageType.SWARM_SYNC:
                if swarm_id in self.swarm_status:
                    # Update swarm sync data
                    self.swarm_status[swarm_id]["last_sync"] = datetime.now().isoformat()
                    self.swarm_status[swarm_id]["sync_data"] = message.content.get('sync_data', {})
                    self.save_swarm_status()
                    logger.info(f"Swarm {swarm_id} synchronized")
                    return True
                    
            elif message.type == MessageType.SWARM_ALERT:
                if swarm_id in self.swarm_status:
                    # Record swarm alert
                    if "alerts" not in self.swarm_status[swarm_id]:
                        self.swarm_status[swarm_id]["alerts"] = []
                    
                    self.swarm_status[swarm_id]["alerts"].append({
                        "alert": message.content.get('alert'),
                        "severity": message.content.get('severity'),
                        "details": message.content.get('details'),
                        "timestamp": datetime.now().isoformat()
                    })
                    self.save_swarm_status()
                    logger.warning(f"Swarm alert for {swarm_id}: {message.content.get('alert')}")
                    return True
                    
            elif message.type == MessageType.SWARM_CHECK:
                if swarm_id in self.swarm_status:
                    # Update swarm health check
                    self.swarm_status[swarm_id]["last_health_check"] = datetime.now().isoformat()
                    self.save_swarm_status()
                    logger.info(f"Swarm {swarm_id} health check completed")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error handling swarm message: {e}")
            return False

    def handle_protocol_violation(self, message: Message) -> bool:
        """Handle protocol violation message."""
        try:
            protocol = message.content['protocol']
            violation = message.content['violation']
            details = message.content['details']
            
            # Initialize protocol violations if not exists
            if protocol not in self.protocol_violations:
                self.protocol_violations[protocol] = []
            
            # Record violation
            self.protocol_violations[protocol].append({
                "violation": violation,
                "details": details,
                "from_agent": message.from_agent,
                "timestamp": datetime.now().isoformat()
            })
            
            self.save_violations()
            logger.warning(f"Protocol violation recorded for {protocol}: {violation}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling protocol violation: {e}")
            return False

    def handle_protocol_remediation(self, message: Message) -> bool:
        """Handle protocol remediation message."""
        try:
            protocol = message.content['protocol']
            remediation = message.content['remediation']
            details = message.content['details']
            
            # Initialize protocol remediations if not exists
            if protocol not in self.protocol_remediations:
                self.protocol_remediations[protocol] = []
            
            # Record remediation
            self.protocol_remediations[protocol].append({
                "remediation": remediation,
                "details": details,
                "from_agent": message.from_agent,
                "timestamp": datetime.now().isoformat()
            })
            
            self.save_remediations()
            logger.info(f"Protocol remediation recorded for {protocol}: {remediation}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling protocol remediation: {e}")
            return False

    def handle_protocol_audit(self, message: Message) -> bool:
        """Handle protocol audit message."""
        try:
            protocol = message.content['protocol']
            audit = message.content['audit']
            
            # Initialize protocol audits if not exists
            if protocol not in self.protocol_audits:
                self.protocol_audits[protocol] = []
            
            # Record audit
            self.protocol_audits[protocol].append({
                "audit": audit,
                "from_agent": message.from_agent,
                "timestamp": datetime.now().isoformat()
            })
            
            self.save_audits()
            logger.info(f"Protocol audit recorded for {protocol}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling protocol audit: {e}")
            return False

    def handle_swarm_violation(self, message: Message) -> bool:
        """Handle swarm violation message."""
        try:
            swarm_id = message.content['swarm_id']
            violation = message.content['violation']
            details = message.content['details']
            
            # Initialize swarm violations if not exists
            if swarm_id not in self.swarm_violations:
                self.swarm_violations[swarm_id] = []
            
            # Record violation
            self.swarm_violations[swarm_id].append({
                "violation": violation,
                "details": details,
                "from_agent": message.from_agent,
                "timestamp": datetime.now().isoformat()
            })
            
            self.save_violations()
            logger.warning(f"Swarm violation recorded for {swarm_id}: {violation}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling swarm violation: {e}")
            return False

    def handle_swarm_remediation(self, message: Message) -> bool:
        """Handle swarm remediation message."""
        try:
            swarm_id = message.content['swarm_id']
            remediation = message.content['remediation']
            details = message.content['details']
            
            # Initialize swarm remediations if not exists
            if swarm_id not in self.swarm_remediations:
                self.swarm_remediations[swarm_id] = []
            
            # Record remediation
            self.swarm_remediations[swarm_id].append({
                "remediation": remediation,
                "details": details,
                "from_agent": message.from_agent,
                "timestamp": datetime.now().isoformat()
            })
            
            self.save_remediations()
            logger.info(f"Swarm remediation recorded for {swarm_id}: {remediation}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling swarm remediation: {e}")
            return False

    def handle_swarm_audit(self, message: Message) -> bool:
        """Handle swarm audit message."""
        try:
            swarm_id = message.content['swarm_id']
            audit = message.content['audit']
            
            # Initialize swarm audits if not exists
            if swarm_id not in self.swarm_audits:
                self.swarm_audits[swarm_id] = []
            
            # Record audit
            self.swarm_audits[swarm_id].append({
                "audit": audit,
                "from_agent": message.from_agent,
                "timestamp": datetime.now().isoformat()
            })
            
            self.save_audits()
            logger.info(f"Swarm audit recorded for {swarm_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling swarm audit: {e}")
            return False

    def add_message(self, message: Message) -> bool:
        """Add message to queue."""
        try:
            # Validate message
            is_valid, reason = MessageValidator.validate_message(message.to_dict())
            if not is_valid:
                logger.warning(f"Invalid message skipped: {reason}")
                return False
                
            # Handle special message types
            if message.type == MessageType.BOOTSTRAP:
                if not self.handle_bootstrap(message):
                    return False
            elif message.type == MessageType.SWARM_JOIN:
                if not self.handle_swarm_join(message):
                    return False
            elif message.type == MessageType.SWARM_LEAVE:
                if not self.handle_swarm_leave(message):
                    return False
            elif message.type in [MessageType.PROTOCOL, MessageType.PROTOCOL_ACK, MessageType.PROTOCOL_ERROR]:
                if not self.handle_protocol_message(message):
                    return False
            elif message.type in [MessageType.SWARM_SYNC, MessageType.SWARM_ALERT, MessageType.SWARM_CHECK]:
                if not self.handle_swarm_message(message):
                    return False
            elif message.type == MessageType.PROTOCOL_VIOLATION:
                if not self.handle_protocol_violation(message):
                    return False
            elif message.type == MessageType.PROTOCOL_REMEDIATE:
                if not self.handle_protocol_remediation(message):
                    return False
            elif message.type == MessageType.PROTOCOL_AUDIT:
                if not self.handle_protocol_audit(message):
                    return False
            elif message.type == MessageType.SWARM_VIOLATION:
                if not self.handle_swarm_violation(message):
                    return False
            elif message.type == MessageType.SWARM_REMEDIATE:
                if not self.handle_swarm_remediation(message):
                    return False
            elif message.type == MessageType.SWARM_AUDIT:
                if not self.handle_swarm_audit(message):
                    return False
                
            # Add to appropriate queue
            self.queue[message.priority.value].append(message)
            self.save_queue()
            logger.info(f"Added message to {message.priority.value} queue: {MessageFormatter.to_log(message)}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return False
            
    def get_next_message(self, priority: MessagePriority) -> Optional[Message]:
        """Get next message from queue."""
        try:
            if self.queue[priority.value]:
                message = self.queue[priority.value].pop(0)
                self.save_queue()
                logger.info(f"Retrieved message from {priority.value} queue: {MessageFormatter.to_log(message)}")
                return message
            return None
        except Exception as e:
            logger.error(f"Error getting message: {e}")
            return None
            
    def clear_queue(self, priority: Optional[MessagePriority] = None):
        """Clear message queue."""
        try:
            if priority:
                self.queue[priority.value] = []
            else:
                for p in self.queue:
                    self.queue[p] = []
            self.save_queue()
            logger.info(f"Cleared {'all' if not priority else priority.value} queues")
            return True
        except Exception as e:
            logger.error(f"Error clearing queue: {e}")
            return False
            
    def get_queue_status(self) -> Dict:
        """Get current queue status."""
        try:
            return {
                "queue_size": sum(len(q) for q in self.queue.values()),
                "processing": False,
                "pending_messages": {
                    priority: len(messages)
                    for priority, messages in self.queue.items()
                },
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {"error": str(e)}
            
    def archive_message(self, message: Message):
        """Archive a delivered message."""
        try:
            # Load existing archive
            archive = []
            if self.archive_file.exists():
                with open(self.archive_file, 'r') as f:
                    archive = json.load(f)
                    
            # Add message to archive
            archive.append(message.to_dict())
            
            # Save archive
            with open(self.archive_file, 'w') as f:
                json.dump(archive, f, indent=2)
                
            logger.info(f"Archived message: {MessageFormatter.to_log(message)}")
            
        except Exception as e:
            logger.error(f"Error archiving message: {e}")
            
    def get_archived_messages(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        from_agent: Optional[str] = None,
        to_agent: Optional[str] = None
    ) -> List[Message]:
        """Get archived messages with optional filters."""
        try:
            if not self.archive_file.exists():
                return []
                
            with open(self.archive_file, 'r') as f:
                archive = json.load(f)
                
            # Convert to Message objects
            messages = [Message.from_dict(msg) for msg in archive]
            
            # Apply filters
            if since:
                messages = [msg for msg in messages if msg.timestamp >= since]
            if until:
                messages = [msg for msg in messages if msg.timestamp <= until]
            if message_type:
                messages = [msg for msg in messages if msg.type == message_type]
            if from_agent:
                messages = [msg for msg in messages if msg.from_agent == from_agent]
            if to_agent:
                messages = [msg for msg in messages if msg.to_agent == to_agent]
                
            return messages
            
        except Exception as e:
            logger.error(f"Error getting archived messages: {e}")
            return []

    def get_protocol_status(self, protocol: Optional[str] = None) -> Dict:
        """Get protocol status."""
        try:
            if protocol:
                return self.protocol_status.get(protocol, {})
            return self.protocol_status
        except Exception as e:
            logger.error(f"Error getting protocol status: {e}")
            return {}

    def get_violations(self, protocol: Optional[str] = None, swarm_id: Optional[str] = None) -> Dict:
        """Get protocol or swarm violations."""
        try:
            if protocol:
                return self.protocol_violations.get(protocol, [])
            elif swarm_id:
                return self.swarm_violations.get(swarm_id, [])
            return {
                'protocol': self.protocol_violations,
                'swarm': self.swarm_violations
            }
        except Exception as e:
            logger.error(f"Error getting violations: {e}")
            return {}

    def get_remediations(self, protocol: Optional[str] = None, swarm_id: Optional[str] = None) -> Dict:
        """Get protocol or swarm remediations."""
        try:
            if protocol:
                return self.protocol_remediations.get(protocol, [])
            elif swarm_id:
                return self.swarm_remediations.get(swarm_id, [])
            return {
                'protocol': self.protocol_remediations,
                'swarm': self.swarm_remediations
            }
        except Exception as e:
            logger.error(f"Error getting remediations: {e}")
            return {}

    def get_audits(self, protocol: Optional[str] = None, swarm_id: Optional[str] = None) -> Dict:
        """Get protocol or swarm audits."""
        try:
            if protocol:
                return self.protocol_audits.get(protocol, [])
            elif swarm_id:
                return self.swarm_audits.get(swarm_id, [])
            return {
                'protocol': self.protocol_audits,
                'swarm': self.swarm_audits
            }
        except Exception as e:
            logger.error(f"Error getting audits: {e}")
            return {}

def main():
    """Example usage of MessageQueueManager."""
    manager = MessageQueueManager()
    
    # Create test messages
    alert_msg = MessageValidator.format_message(
        msg_type=MessageType.ALERT,
        content={"text": "Test alert"},
        priority=MessagePriority.HIGH,
        from_agent="Agent-1",
        to_agent="Agent-2"
    )
    
    status_msg = MessageValidator.format_message(
        msg_type=MessageType.STATUS,
        content={"status": "running"},
        priority=MessagePriority.MEDIUM,
        from_agent="Agent-3",
        to_agent="Agent-4"
    )
    
    # Add messages to queue
    manager.add_message(alert_msg)
    manager.add_message(status_msg)
    
    # Get queue status
    status = manager.get_queue_status()
    print(f"\nQueue Status:\n{json.dumps(status, indent=2)}")
    
    # Get next high priority message
    message = manager.get_next_message(MessagePriority.HIGH)
    if message:
        print(f"\nRetrieved message:\n{MessageFormatter.to_json(message)}")
        
    # Archive message
    if message:
        manager.archive_message(message)
        
    # Get archived messages
    archived = manager.get_archived_messages()
    print(f"\nArchived messages: {len(archived)}")

if __name__ == "__main__":
    main() 