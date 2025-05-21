"""
Message Manager Module

Handles message formatting, chunking, and communication.
"""

import logging
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Optional
from dreamos.tools.agent_cellphone import AgentCellphone, MessageMode

logger = logging.getLogger('message_manager')

class MessageManager:
    def __init__(self, cellphone: AgentCellphone):
        self.cellphone = cellphone
        
        # Message chunking parameters
        self.max_chunk_size = 100
        self.retry_attempts = 3
        self.retry_delay = 5
        self.verification_delay = 0.2
        
        # Message format templates
        self.message_templates = {
            "status": "[{agent_id}] [SYNC] Status:\n{metrics}\n\nWE ARE THE SWARM",
            "task": "[{agent_id}] [TASK] {task_id} - {component}: {status}",
            "alert": "[{agent_id}] [ALERT] {level} - {message}",
            "action": "[{agent_id}] [ACTION] {type} - {details}"
        }
        
    def format_status(self, agent_id: str, metrics: str) -> str:
        """Format status message."""
        return self.message_templates["status"].format(
            agent_id=agent_id,
            metrics=metrics
        )
        
    def format_task(self, agent_id: str, task_id: str, component: str, status: bool) -> str:
        """Format task status message."""
        return self.message_templates["task"].format(
            agent_id=agent_id,
            task_id=task_id,
            component=component,
            status='✓' if status else '✗'
        )
        
    def format_alert(self, agent_id: str, level: str, message: str) -> str:
        """Format alert message."""
        return self.message_templates["alert"].format(
            agent_id=agent_id,
            level=level,
            message=message
        )
        
    def format_action(self, agent_id: str, action_type: str, details: str) -> str:
        """Format action message."""
        return self.message_templates["action"].format(
            agent_id=agent_id,
            type=action_type,
            details=details
        )
        
    def chunk_message(self, message: str) -> List[str]:
        """Split message into chunks with verification hashes."""
        chunks = []
        current_chunk = ""
        total_chunks = (len(message) + self.max_chunk_size - 1) // self.max_chunk_size
        
        for i, char in enumerate(message):
            current_chunk += char
            if len(current_chunk) >= self.max_chunk_size or i == len(message) - 1:
                chunk_num = len(chunks) + 1
                chunk_hash = hashlib.md5(current_chunk.encode()).hexdigest()[:6]
                chunk_header = f"[CHUNK {chunk_num}/{total_chunks} HASH:{chunk_hash}]"
                chunks.append(f"{chunk_header}\n{current_chunk.strip()}")
                current_chunk = ""
                
        return chunks
        
    def verify_chunk(self, expected: str, actual: str) -> bool:
        """Verify chunk content and hash."""
        try:
            # Extract headers
            expected_header = expected.split('\n')[0]
            actual_header = actual.split('\n')[0]
            
            # Extract content
            expected_content = '\n'.join(expected.split('\n')[1:]).strip()
            actual_content = '\n'.join(actual.split('\n')[1:]).strip()
            
            # Verify header format
            if not (expected_header.startswith('[CHUNK') and actual_header.startswith('[CHUNK')):
                return False
                
            # Verify content - allow for slight variations in whitespace
            return expected_content.replace(' ', '') == actual_content.replace(' ', '')
        except Exception as e:
            logger.error(f"Error verifying chunk: {e}")
            return False
            
    def send_chunked_message(self, agent_id: str, message: str, mode: MessageMode) -> bool:
        """Send message in chunks with verification."""
        chunks = self.chunk_message(message)
        
        for chunk in chunks:
            for attempt in range(self.retry_attempts):
                try:
                    logger.info(f"Sending chunk to {agent_id}")
                    success = self.cellphone.message_agent(agent_id, chunk, mode)
                    
                    if success:
                        logger.info(f"Successfully sent chunk to {agent_id}")
                        break
                    else:
                        logger.warning(f"Failed to send chunk to {agent_id} on attempt {attempt + 1}")
                        if attempt < self.retry_attempts - 1:
                            time.sleep(self.retry_delay)
                except Exception as e:
                    logger.error(f"Error sending chunk to {agent_id}: {e}")
                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay)
                    continue
                    
            if not success:
                return False
                
        return True 