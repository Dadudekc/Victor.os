"""
CLI tool for Dream.OS agent communication.
"""

import argparse
from pathlib import Path
import sys
from typing import Optional

from dreamos.coordination.agent_coordinates import AgentRegistry, AgentCoordinates
from dreamos.coordination.messaging import Message, MessageHandler, MessagePriority, MessageMode

def parse_args():
    parser = argparse.ArgumentParser(description="Dream.OS Agent Communication Tool")
    parser.add_argument("agent_id", help="Target agent ID")
    parser.add_argument("--message", "-m", help="Message content")
    parser.add_argument("--priority", "-p", type=int, default=1,
                       help="Message priority (0=LOW, 1=NORMAL, 2=HIGH, 3=URGENT)")
    parser.add_argument("--mode", "-M", choices=["async", "sync"], default="async",
                       help="Message mode (async/sync)")
    parser.add_argument("--from-agent", "-f", help="Source agent ID")
    parser.add_argument("--to-agent", "-t", help="Target agent ID")
    parser.add_argument("--list", "-l", action="store_true", help="List messages")
    parser.add_argument("--read", "-r", help="Mark message as read")
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Initialize coordination system
    base_path = Path("src/dreamos/coordination")
    registry = AgentRegistry(base_path)
    handler = MessageHandler(base_path)
    
    # Handle message listing
    if args.list:
        messages = handler.get_messages(args.agent_id)
        for msg in messages:
            print(f"[{msg.timestamp}] {msg.from_agent} -> {msg.to_agent}: {msg.content}")
        return
    
    # Handle message marking as read
    if args.read:
        if handler.mark_read(args.agent_id, args.read):
            print(f"Message {args.read} marked as read")
        else:
            print(f"Failed to mark message {args.read} as read")
        return
    
    # Handle message sending
    if not args.message:
        print("Error: Message content required")
        sys.exit(1)
    
    if not args.from_agent:
        print("Error: Source agent ID required")
        sys.exit(1)
    
    if not args.to_agent:
        print("Error: Target agent ID required")
        sys.exit(1)
    
    # Create and send message
    try:
        priority = MessagePriority(args.priority)
        mode = MessageMode(args.mode)
        
        message = Message.create(
            from_agent=args.from_agent,
            to_agent=args.to_agent,
            content=args.message,
            priority=priority,
            mode=mode
        )
        
        if handler.send_message(message):
            print(f"Message sent: {message.id}")
        else:
            print("Failed to send message")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 