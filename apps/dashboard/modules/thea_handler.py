import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

class THEAHandler:
    def __init__(self, inbox_base: Path):
        self.inbox_base = inbox_base
        
    async def handle_escalation(self, agent_id: str, task_id: str, escalation: Dict[str, Any]) -> None:
        """Handle THEA's response to an escalation"""
        try:
            # For now, just acknowledge the escalation
            response = {
                "type": "thea_response",
                "task_id": task_id,
                "status": "in_progress",
                "response": "Escalation received. Will process shortly.",
                "next_steps": ["Review task details", "Determine best course of action"],
                "timestamp": time.time()
            }
            await self._process_thea_response(agent_id, task_id, response)
        except Exception as e:
            print(f"Error handling THEA escalation: {e}")
                
    async def _process_thea_response(self, agent_id: str, task_id: str, response: Dict[str, Any]) -> None:
        """Process and store THEA's response"""
        try:
            inbox_path = self.inbox_base / agent_id / "inbox.json"
            if inbox_path.exists():
                messages = json.loads(inbox_path.read_text())
                if isinstance(messages, list):
                    messages.append({
                        "type": "thea_response",
                        "task_id": task_id,
                        "content": response,
                        "timestamp": time.time()
                    })
                    inbox_path.write_text(json.dumps(messages, indent=2))
                    
                    # Update task status if provided
                    if response.get("status"):
                        from .task_manager import update_task_status
                        update_task_status(agent_id, task_id, response["status"])
        except Exception as e:
            print(f"Error processing THEA response: {e}") 