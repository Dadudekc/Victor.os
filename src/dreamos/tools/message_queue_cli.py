"""
Message Queue CLI

Command-line interface for managing the message queue.
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Optional
from .message_queue import MessageQueueManager
from .message_protocol import (
    Message, MessageType, MessagePriority,
    MessageValidator, MessageFormatter
)
import click
import uuid

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Message Queue CLI")
    
    # Main commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List messages
    list_parser = subparsers.add_parser("list", help="List messages in queue")
    list_parser.add_argument(
        "--priority",
        choices=[p.value for p in MessagePriority],
        help="Filter by priority"
    )
    list_parser.add_argument(
        "--type",
        choices=[t.value for t in MessageType],
        help="Filter by message type"
    )
    list_parser.add_argument(
        "--from-agent",
        help="Filter by sender"
    )
    list_parser.add_argument(
        "--to-agent",
        help="Filter by recipient"
    )
    
    # Send message
    send_parser = subparsers.add_parser("send", help="Send a message")
    send_parser.add_argument(
        "--type",
        choices=[t.value for t in MessageType],
        required=True,
        help="Message type"
    )
    send_parser.add_argument(
        "--content",
        required=True,
        help="Message content (JSON string)"
    )
    send_parser.add_argument(
        "--priority",
        choices=[p.value for p in MessagePriority],
        default=MessagePriority.MEDIUM.value,
        help="Message priority"
    )
    send_parser.add_argument(
        "--from-agent",
        help="Sender agent ID"
    )
    send_parser.add_argument(
        "--to-agent",
        help="Recipient agent ID"
    )
    
    # Clear queue
    clear_parser = subparsers.add_parser("clear", help="Clear message queue")
    clear_parser.add_argument(
        "--priority",
        choices=[p.value for p in MessagePriority],
        help="Clear specific priority queue"
    )
    
    # Get status
    subparsers.add_parser("status", help="Get queue status")
    
    # Archive commands
    archive_parser = subparsers.add_parser("archive", help="Archive operations")
    archive_parser.add_argument(
        "--list",
        action="store_true",
        help="List archived messages"
    )
    archive_parser.add_argument(
        "--since",
        help="Filter by start date (ISO format)"
    )
    archive_parser.add_argument(
        "--until",
        help="Filter by end date (ISO format)"
    )
    archive_parser.add_argument(
        "--type",
        choices=[t.value for t in MessageType],
        help="Filter by message type"
    )
    archive_parser.add_argument(
        "--from-agent",
        help="Filter by sender"
    )
    archive_parser.add_argument(
        "--to-agent",
        help="Filter by recipient"
    )

    # Cellphone commands
    cellphone_parser = subparsers.add_parser("cellphone", help="Cellphone operations")
    cellphone_subparsers = cellphone_parser.add_subparsers(dest="cellphone_command", help="Cellphone command")
    
    # Bootstrap agent
    bootstrap_parser = cellphone_subparsers.add_parser("bootstrap", help="Bootstrap an agent")
    bootstrap_parser.add_argument(
        "--agent-id",
        required=True,
        help="Agent ID to bootstrap"
    )
    bootstrap_parser.add_argument(
        "--swarm-id",
        help="Swarm ID to join"
    )
    bootstrap_parser.add_argument(
        "--capabilities",
        nargs="+",
        default=["dream_os", "swarm_coordination"],
        help="Agent capabilities"
    )
    
    # Join swarm
    join_parser = cellphone_subparsers.add_parser("join", help="Join a swarm")
    join_parser.add_argument(
        "--agent-id",
        required=True,
        help="Agent ID"
    )
    join_parser.add_argument(
        "--swarm-id",
        required=True,
        help="Swarm ID to join"
    )
    join_parser.add_argument(
        "--capabilities",
        nargs="+",
        help="Agent capabilities"
    )
    
    # Leave swarm
    leave_parser = cellphone_subparsers.add_parser("leave", help="Leave a swarm")
    leave_parser.add_argument(
        "--agent-id",
        required=True,
        help="Agent ID"
    )
    leave_parser.add_argument(
        "--swarm-id",
        required=True,
        help="Swarm ID to leave"
    )
    
    # Send protocol
    protocol_parser = cellphone_subparsers.add_parser("protocol", help="Send protocol instruction")
    protocol_parser.add_argument(
        "--protocol",
        required=True,
        help="Protocol name"
    )
    protocol_parser.add_argument(
        "--instruction",
        required=True,
        help="Protocol instruction"
    )
    protocol_parser.add_argument(
        "--to-agent",
        help="Target agent ID"
    )
    
    # Get swarm status
    swarm_parser = cellphone_subparsers.add_parser("swarm", help="Get swarm status")
    swarm_parser.add_argument(
        "--swarm-id",
        help="Specific swarm ID"
    )
    
    return parser.parse_args()

def list_messages(
    manager: MessageQueueManager,
    priority: Optional[str] = None,
    msg_type: Optional[str] = None,
    from_agent: Optional[str] = None,
    to_agent: Optional[str] = None
):
    """List messages in queue with optional filters."""
    try:
        # Get messages from each priority queue
        messages = []
        for p in MessagePriority:
            if priority and p.value != priority:
                continue
            queue_messages = manager.queue[p.value]
            messages.extend(queue_messages)
            
        # Apply filters
        if msg_type:
            messages = [msg for msg in messages if msg.type.value == msg_type]
        if from_agent:
            messages = [msg for msg in messages if msg.from_agent == from_agent]
        if to_agent:
            messages = [msg for msg in messages if msg.to_agent == to_agent]
            
        # Print messages
        if messages:
            print(f"\nFound {len(messages)} messages:")
            for msg in messages:
                print(f"\n{MessageFormatter.to_json(msg)}")
        else:
            print("No messages found")
            
    except Exception as e:
        print(f"Error listing messages: {e}", file=sys.stderr)
        sys.exit(1)

def send_message(
    manager: MessageQueueManager,
    msg_type: str,
    content: str,
    priority: str,
    from_agent: Optional[str] = None,
    to_agent: Optional[str] = None
):
    """Send a message to the queue."""
    try:
        # Parse content JSON
        content_dict = json.loads(content)
        
        # Create message
        message = MessageValidator.format_message(
            msg_type=MessageType(msg_type),
            content=content_dict,
            priority=MessagePriority(priority),
            from_agent=from_agent,
            to_agent=to_agent
        )
        
        # Add to queue
        if manager.add_message(message):
            print(f"Message sent successfully: {MessageFormatter.to_log(message)}")
        else:
            print("Failed to send message", file=sys.stderr)
            sys.exit(1)
            
    except json.JSONDecodeError:
        print("Invalid JSON content", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error sending message: {e}", file=sys.stderr)
        sys.exit(1)

def clear_queue(manager: MessageQueueManager, priority: Optional[str] = None):
    """Clear message queue."""
    try:
        if priority:
            manager.clear_queue(MessagePriority(priority))
            print(f"Cleared {priority} queue")
        else:
            manager.clear_queue()
            print("Cleared all queues")
    except Exception as e:
        print(f"Error clearing queue: {e}", file=sys.stderr)
        sys.exit(1)

def get_status(manager: MessageQueueManager):
    """Get queue status."""
    try:
        status = manager.get_queue_status()
        print("\nQueue Status:")
        print(json.dumps(status, indent=2))
    except Exception as e:
        print(f"Error getting status: {e}", file=sys.stderr)
        sys.exit(1)

def list_archived(
    manager: MessageQueueManager,
    since: Optional[str] = None,
    until: Optional[str] = None,
    msg_type: Optional[str] = None,
    from_agent: Optional[str] = None,
    to_agent: Optional[str] = None
):
    """List archived messages."""
    try:
        # Get archived messages
        messages = manager.get_archived_messages(
            since=since,
            until=until,
            message_type=MessageType(msg_type) if msg_type else None,
            from_agent=from_agent,
            to_agent=to_agent
        )
        
        # Print messages
        if messages:
            print(f"\nFound {len(messages)} archived messages:")
            for msg in messages:
                print(f"\n{MessageFormatter.to_json(msg)}")
        else:
            print("No archived messages found")
            
    except Exception as e:
        print(f"Error listing archived messages: {e}", file=sys.stderr)
        sys.exit(1)

def handle_cellphone_command(manager: MessageQueueManager, args):
    """Handle cellphone-specific commands."""
    if args.cellphone_command == "bootstrap":
        message = MessageValidator.format_bootstrap_message(
            agent_id=args.agent_id,
            from_agent="cellphone",
            swarm_id=args.swarm_id,
            metadata={"capabilities": args.capabilities}
        )
        if manager.add_message(message):
            print(f"Agent {args.agent_id} bootstrapped successfully")
        else:
            print("Failed to bootstrap agent", file=sys.stderr)
            sys.exit(1)
            
    elif args.cellphone_command == "join":
        message = MessageValidator.format_swarm_join_message(
            agent_id=args.agent_id,
            from_agent=args.agent_id,
            swarm_id=args.swarm_id,
            capabilities=args.capabilities
        )
        if manager.add_message(message):
            print(f"Agent {args.agent_id} joined swarm {args.swarm_id}")
        else:
            print("Failed to join swarm", file=sys.stderr)
            sys.exit(1)
            
    elif args.cellphone_command == "leave":
        message = MessageValidator.format_message(
            msg_type=MessageType.SWARM_LEAVE,
            content={
                "agent_id": args.agent_id,
                "swarm_id": args.swarm_id,
                "leave_time": datetime.now().isoformat()
            },
            priority=MessagePriority.HIGH,
            from_agent=args.agent_id
        )
        if manager.add_message(message):
            print(f"Agent {args.agent_id} left swarm {args.swarm_id}")
        else:
            print("Failed to leave swarm", file=sys.stderr)
            sys.exit(1)
            
    elif args.cellphone_command == "protocol":
        message = MessageValidator.format_protocol_message(
            protocol=args.protocol,
            instruction=args.instruction,
            from_agent="cellphone",
            to_agent=args.to_agent
        )
        if manager.add_message(message):
            print(f"Protocol instruction sent: {args.protocol} - {args.instruction}")
        else:
            print("Failed to send protocol instruction", file=sys.stderr)
            sys.exit(1)
            
    elif args.cellphone_command == "swarm":
        status = manager.get_swarm_status(args.swarm_id)
        print("\nSwarm Status:")
        print(json.dumps(status, indent=2))
        
    else:
        print("Invalid cellphone command", file=sys.stderr)
        sys.exit(1)

def main():
    """Main entry point."""
    args = parse_args()
    
    # Initialize queue manager
    manager = MessageQueueManager()
    
    # Execute command
    if args.command == "list":
        list_messages(
            manager,
            priority=args.priority,
            msg_type=args.type,
            from_agent=args.from_agent,
            to_agent=args.to_agent
        )
    elif args.command == "send":
        send_message(
            manager,
            msg_type=args.type,
            content=args.content,
            priority=args.priority,
            from_agent=args.from_agent,
            to_agent=args.to_agent
        )
    elif args.command == "clear":
        clear_queue(manager, args.priority)
    elif args.command == "status":
        get_status(manager)
    elif args.command == "archive":
        if args.list:
            list_archived(
                manager,
                since=args.since,
                until=args.until,
                msg_type=args.type,
                from_agent=args.from_agent,
                to_agent=args.to_agent
            )
    elif args.command == "cellphone":
        handle_cellphone_command(manager, args)
    else:
        print("No command specified", file=sys.stderr)
        sys.exit(1)

@click.command()
@click.option('--protocol', required=True, help='Protocol name')
@click.option('--instruction', required=True, help='Protocol instruction')
@click.option('--to-agent', help='Target agent ID')
@click.option('--priority', type=click.Choice(['HIGH', 'MEDIUM', 'LOW']), default='MEDIUM')
@click.option('--metadata', help='Additional metadata as JSON')
def protocol(protocol: str, instruction: str, to_agent: Optional[str], priority: str, metadata: Optional[str]):
    """Send a protocol instruction."""
    try:
        queue = MessageQueueManager()
        message = MessageValidator.format_protocol_message(
            protocol=protocol,
            instruction=instruction,
            to_agent=to_agent,
            priority=MessagePriority[priority],
            metadata=json.loads(metadata) if metadata else None
        )
        if queue.add_message(message):
            click.echo(f"Protocol instruction sent: {protocol}")
        else:
            click.echo("Failed to send protocol instruction")
    except Exception as e:
        click.echo(f"Error: {e}")

@click.command()
@click.option('--protocol', required=True, help='Protocol name')
@click.option('--status', required=True, help='Protocol status')
@click.option('--from-agent', required=True, help='Agent ID')
@click.option('--to-agent', help='Target agent ID')
@click.option('--ack-id', help='Acknowledgment ID')
@click.option('--metadata', help='Additional metadata as JSON')
def protocol_ack(protocol: str, status: str, from_agent: str, to_agent: Optional[str], 
                ack_id: Optional[str], metadata: Optional[str]):
    """Send a protocol acknowledgment."""
    try:
        queue = MessageQueueManager()
        message = MessageValidator.format_protocol_ack_message(
            protocol=protocol,
            from_agent=from_agent,
            to_agent=to_agent,
            ack_id=ack_id or str(uuid.uuid4()),
            status=status,
            metadata=json.loads(metadata) if metadata else None
        )
        if queue.add_message(message):
            click.echo(f"Protocol acknowledgment sent: {protocol}")
        else:
            click.echo("Failed to send protocol acknowledgment")
    except Exception as e:
        click.echo(f"Error: {e}")

@click.command()
@click.option('--swarm-id', required=True, help='Swarm ID')
@click.option('--sync-data', required=True, help='Sync data as JSON')
@click.option('--from-agent', required=True, help='Agent ID')
@click.option('--metadata', help='Additional metadata as JSON')
def swarm_sync(swarm_id: str, sync_data: str, from_agent: str, metadata: Optional[str]):
    """Send a swarm synchronization message."""
    try:
        queue = MessageQueueManager()
        message = MessageValidator.format_swarm_sync_message(
            swarm_id=swarm_id,
            from_agent=from_agent,
            sync_data=json.loads(sync_data),
            metadata=json.loads(metadata) if metadata else None
        )
        if queue.add_message(message):
            click.echo(f"Swarm sync sent: {swarm_id}")
        else:
            click.echo("Failed to send swarm sync")
    except Exception as e:
        click.echo(f"Error: {e}")

@click.command()
@click.option('--swarm-id', required=True, help='Swarm ID')
@click.option('--alert', required=True, help='Alert message')
@click.option('--severity', required=True, type=click.Choice(['INFO', 'WARNING', 'ERROR', 'CRITICAL']))
@click.option('--details', required=True, help='Alert details as JSON')
@click.option('--from-agent', required=True, help='Agent ID')
@click.option('--metadata', help='Additional metadata as JSON')
def swarm_alert(swarm_id: str, alert: str, severity: str, details: str, from_agent: str, metadata: Optional[str]):
    """Send a swarm alert message."""
    try:
        queue = MessageQueueManager()
        message = MessageValidator.format_swarm_alert_message(
            swarm_id=swarm_id,
            from_agent=from_agent,
            alert=alert,
            severity=severity,
            details=json.loads(details),
            metadata=json.loads(metadata) if metadata else None
        )
        if queue.add_message(message):
            click.echo(f"Swarm alert sent: {swarm_id}")
        else:
            click.echo("Failed to send swarm alert")
    except Exception as e:
        click.echo(f"Error: {e}")

@click.command()
@click.option('--protocol', help='Specific protocol to check')
def protocol_status(protocol: Optional[str]):
    """Get protocol status."""
    try:
        queue = MessageQueueManager()
        status = queue.get_protocol_status(protocol)
        click.echo(json.dumps(status, indent=2))
    except Exception as e:
        click.echo(f"Error: {e}")

@click.command()
@click.option('--protocol', required=True, help='Protocol name')
@click.option('--violation', required=True, help='Violation description')
@click.option('--details', required=True, help='Violation details as JSON')
@click.option('--from-agent', required=True, help='Agent ID')
@click.option('--metadata', help='Additional metadata as JSON')
def protocol_violation(protocol: str, violation: str, details: str, from_agent: str, metadata: Optional[str]):
    """Report a protocol violation."""
    try:
        queue = MessageQueueManager()
        message = MessageValidator.format_protocol_violation_message(
            protocol=protocol,
            from_agent=from_agent,
            violation=violation,
            details=json.loads(details),
            metadata=json.loads(metadata) if metadata else None
        )
        if queue.add_message(message):
            click.echo(f"Protocol violation reported: {protocol}")
        else:
            click.echo("Failed to report protocol violation")
    except Exception as e:
        click.echo(f"Error: {e}")

@click.command()
@click.option('--protocol', required=True, help='Protocol name')
@click.option('--remediation', required=True, help='Remediation description')
@click.option('--details', required=True, help='Remediation details as JSON')
@click.option('--from-agent', required=True, help='Agent ID')
@click.option('--metadata', help='Additional metadata as JSON')
def protocol_remediate(protocol: str, remediation: str, details: str, from_agent: str, metadata: Optional[str]):
    """Report a protocol remediation."""
    try:
        queue = MessageQueueManager()
        message = MessageValidator.format_protocol_remediate_message(
            protocol=protocol,
            from_agent=from_agent,
            remediation=remediation,
            details=json.loads(details),
            metadata=json.loads(metadata) if metadata else None
        )
        if queue.add_message(message):
            click.echo(f"Protocol remediation reported: {protocol}")
        else:
            click.echo("Failed to report protocol remediation")
    except Exception as e:
        click.echo(f"Error: {e}")

@click.command()
@click.option('--protocol', required=True, help='Protocol name')
@click.option('--audit', required=True, help='Audit data as JSON')
@click.option('--from-agent', required=True, help='Agent ID')
@click.option('--metadata', help='Additional metadata as JSON')
def protocol_audit(protocol: str, audit: str, from_agent: str, metadata: Optional[str]):
    """Report a protocol audit."""
    try:
        queue = MessageQueueManager()
        message = MessageValidator.format_protocol_audit_message(
            protocol=protocol,
            from_agent=from_agent,
            audit=json.loads(audit),
            metadata=json.loads(metadata) if metadata else None
        )
        if queue.add_message(message):
            click.echo(f"Protocol audit reported: {protocol}")
        else:
            click.echo("Failed to report protocol audit")
    except Exception as e:
        click.echo(f"Error: {e}")

@click.command()
@click.option('--swarm-id', required=True, help='Swarm ID')
@click.option('--violation', required=True, help='Violation description')
@click.option('--details', required=True, help='Violation details as JSON')
@click.option('--from-agent', required=True, help='Agent ID')
@click.option('--metadata', help='Additional metadata as JSON')
def swarm_violation(swarm_id: str, violation: str, details: str, from_agent: str, metadata: Optional[str]):
    """Report a swarm violation."""
    try:
        queue = MessageQueueManager()
        message = MessageValidator.format_swarm_violation_message(
            swarm_id=swarm_id,
            from_agent=from_agent,
            violation=violation,
            details=json.loads(details),
            metadata=json.loads(metadata) if metadata else None
        )
        if queue.add_message(message):
            click.echo(f"Swarm violation reported: {swarm_id}")
        else:
            click.echo("Failed to report swarm violation")
    except Exception as e:
        click.echo(f"Error: {e}")

@click.command()
@click.option('--swarm-id', required=True, help='Swarm ID')
@click.option('--remediation', required=True, help='Remediation description')
@click.option('--details', required=True, help='Remediation details as JSON')
@click.option('--from-agent', required=True, help='Agent ID')
@click.option('--metadata', help='Additional metadata as JSON')
def swarm_remediate(swarm_id: str, remediation: str, details: str, from_agent: str, metadata: Optional[str]):
    """Report a swarm remediation."""
    try:
        queue = MessageQueueManager()
        message = MessageValidator.format_swarm_remediate_message(
            swarm_id=swarm_id,
            from_agent=from_agent,
            remediation=remediation,
            details=json.loads(details),
            metadata=json.loads(metadata) if metadata else None
        )
        if queue.add_message(message):
            click.echo(f"Swarm remediation reported: {swarm_id}")
        else:
            click.echo("Failed to report swarm remediation")
    except Exception as e:
        click.echo(f"Error: {e}")

@click.command()
@click.option('--swarm-id', required=True, help='Swarm ID')
@click.option('--audit', required=True, help='Audit data as JSON')
@click.option('--from-agent', required=True, help='Agent ID')
@click.option('--metadata', help='Additional metadata as JSON')
def swarm_audit(swarm_id: str, audit: str, from_agent: str, metadata: Optional[str]):
    """Report a swarm audit."""
    try:
        queue = MessageQueueManager()
        message = MessageValidator.format_swarm_audit_message(
            swarm_id=swarm_id,
            from_agent=from_agent,
            audit=json.loads(audit),
            metadata=json.loads(metadata) if metadata else None
        )
        if queue.add_message(message):
            click.echo(f"Swarm audit reported: {swarm_id}")
        else:
            click.echo("Failed to report swarm audit")
    except Exception as e:
        click.echo(f"Error: {e}")

@click.command()
@click.option('--protocol', help='Specific protocol to check')
@click.option('--swarm-id', help='Specific swarm to check')
def violations(protocol: Optional[str], swarm_id: Optional[str]):
    """Get protocol or swarm violations."""
    try:
        queue = MessageQueueManager()
        violations = queue.get_violations(protocol, swarm_id)
        click.echo(json.dumps(violations, indent=2))
    except Exception as e:
        click.echo(f"Error: {e}")

@click.command()
@click.option('--protocol', help='Specific protocol to check')
@click.option('--swarm-id', help='Specific swarm to check')
def remediations(protocol: Optional[str], swarm_id: Optional[str]):
    """Get protocol or swarm remediations."""
    try:
        queue = MessageQueueManager()
        remediations = queue.get_remediations(protocol, swarm_id)
        click.echo(json.dumps(remediations, indent=2))
    except Exception as e:
        click.echo(f"Error: {e}")

@click.command()
@click.option('--protocol', help='Specific protocol to check')
@click.option('--swarm-id', help='Specific swarm to check')
def audits(protocol: Optional[str], swarm_id: Optional[str]):
    """Get protocol or swarm audits."""
    try:
        queue = MessageQueueManager()
        audits = queue.get_audits(protocol, swarm_id)
        click.echo(json.dumps(audits, indent=2))
    except Exception as e:
        click.echo(f"Error: {e}")

if __name__ == "__main__":
    main() 