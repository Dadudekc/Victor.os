#!/usr/bin/env python3
"""
Agent Response Handler

This script handles incoming messages for agents and generates appropriate responses.
It's designed to be run by each agent to process their mailbox.
"""

import json
import logging
import time
from pathlib import Path
import argparse
from typing import Optional, Dict
from agent_cellphone import MessageMode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('agent_response_handler')

class AgentResponseHandler:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.mailbox_dir = Path("runtime/agent_comms/agent_mailboxes")
        self.agent_mailbox = self.mailbox_dir / agent_id
        self.agent_mailbox.mkdir(parents=True, exist_ok=True)
        
    def _get_unread_messages(self) -> list:
        """Get all unread messages from mailbox."""
        if not self.agent_mailbox.exists():
            return []
            
        unread_messages = []
        for message_file in self.agent_mailbox.glob("message_*.json"):
            try:
                with open(message_file, 'r') as f:
                    message_data = json.load(f)
                    if message_data.get("status") == "unread":
                        unread_messages.append((message_file, message_data))
            except Exception as e:
                logger.error(f"Failed to read message file {message_file}: {e}")
                
        return unread_messages
        
    def _mark_message_read(self, message_file: Path):
        """Mark a message as read."""
        try:
            with open(message_file, 'r') as f:
                message_data = json.load(f)
                
            message_data["status"] = "read"
            
            with open(message_file, 'w') as f:
                json.dump(message_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to mark message as read: {e}")
            
    def _write_response(self, message_data: dict, response: str):
        """Write response to mailbox."""
        response_file = self.agent_mailbox / f"response_{int(time.time())}.json"
        response_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": message_data["mode"],
            "in_response_to": message_data["message"],
            "response": response
        }
        
        with open(response_file, 'w') as f:
            json.dump(response_data, f, indent=2)
            
    def _generate_response(self, message_data: dict) -> str:
        """Generate appropriate response based on message mode and content."""
        mode = message_data["mode"]
        message = message_data["message"]
        
        if mode == MessageMode.WAKE.value:
            return f"Agent {self.agent_id} is now active and ready for coordination."
            
        elif mode == MessageMode.PING.value:
            return f"Agent {self.agent_id} is operational and monitoring system status."
            
        elif mode == MessageMode.SYNC.value:
            return f"Agent {self.agent_id} is synchronized with system state."
            
        elif mode == MessageMode.DEBUG.value:
            return f"Agent {self.agent_id} is in debug mode. Current status: operational."
            
        elif mode == MessageMode.RESUME.value:
            return f"Agent {self.agent_id} has resumed normal operation."
            
        return f"Agent {self.agent_id} received message: {message}"
        
    def process_messages(self):
        """Process all unread messages in mailbox."""
        unread_messages = self._get_unread_messages()
        
        for message_file, message_data in unread_messages:
            try:
                # Generate response
                response = self._generate_response(message_data)
                
                # Write response
                self._write_response(message_data, response)
                
                # Mark message as read
                self._mark_message_read(message_file)
                
                logger.info(f"Processed message: {message_data['message']}")
                
            except Exception as e:
                logger.error(f"Failed to process message: {e}")

def main():
    parser = argparse.ArgumentParser(description='Dream.OS Agent Response Handler')
    parser.add_argument('agent_id', help='Agent ID to handle responses for')
    
    args = parser.parse_args()
    
    handler = AgentResponseHandler(args.agent_id)
    handler.process_messages()

if __name__ == "__main__":
    main() 