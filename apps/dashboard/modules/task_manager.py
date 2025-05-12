import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio
import time

def load_inbox(agent_id: str, inbox_base: Path) -> List[Dict[str, Any]]:
    """Load agent's inbox messages"""
    inbox_path = inbox_base / agent_id / "inbox.json"
    if inbox_path.exists():
        try:
            messages = json.loads(inbox_path.read_text())
            if isinstance(messages, list):
                return messages
        except json.JSONDecodeError:
            print(f"Error loading inbox for {agent_id}")
    return []

def load_status(agent_id: str, inbox_base: Path) -> Dict[str, Any]:
    """Load agent's status information"""
    status_path = inbox_base / agent_id / "status.json"
    if status_path.exists():
        try:
            return json.loads(status_path.read_text())
        except json.JSONDecodeError:
            print(f"Error loading status for {agent_id}")
    return {}

def load_devlog(agent_id: str, inbox_base: Path) -> str:
    """Load agent's devlog content"""
    devlog_path = inbox_base / agent_id / "devlog.json"
    if devlog_path.exists():
        try:
            return devlog_path.read_text()
        except Exception as e:
            print(f"Error loading devlog for {agent_id}: {e}")
    return ""

def update_task_status(agent_id: str, task_id: str, status: str, inbox_base: Path) -> None:
    """Update task status in agent's inbox"""
    inbox_path = inbox_base / agent_id / "inbox.json"
    if inbox_path.exists():
        try:
            messages = json.loads(inbox_path.read_text())
            if isinstance(messages, list):
                for msg in messages:
                    if msg.get("id") == task_id:
                        msg["status"] = status
                inbox_path.write_text(json.dumps(messages, indent=2))
        except json.JSONDecodeError:
            print(f"Error updating task status for {agent_id}")

def requeue_task(agent_id: str, task_id: str, target_agent: str, inbox_base: Path) -> None:
    """Requeue a task to another agent"""
    source_inbox = inbox_base / agent_id / "inbox.json"
    target_inbox = inbox_base / target_agent / "inbox.json"
    
    if source_inbox.exists() and target_inbox.exists():
        try:
            # Load source inbox
            messages = json.loads(source_inbox.read_text())
            if isinstance(messages, list):
                # Find and remove task
                task = next((msg for msg in messages if msg.get("id") == task_id), None)
                if task:
                    messages = [msg for msg in messages if msg.get("id") != task_id]
                    source_inbox.write_text(json.dumps(messages, indent=2))
                    
                    # Add to target inbox
                    target_messages = json.loads(target_inbox.read_text())
                    if isinstance(target_messages, list):
                        task["source_agent"] = agent_id
                        target_messages.append(task)
                        target_inbox.write_text(json.dumps(target_messages, indent=2))
        except json.JSONDecodeError:
            print(f"Error requeuing task from {agent_id} to {target_agent}")

def escalate_to_thea(agent_id: str, task_id: str, inbox_base: Path, thea_handler) -> None:
    """Escalate a task to THEA"""
    thea_inbox = inbox_base / "THEA" / "inbox.json"
    if thea_inbox.exists():
        try:
            # Load source task
            messages = load_inbox(agent_id, inbox_base)
            task = next((msg for msg in messages if msg.get("id") == task_id), None)
            if task:
                # Create escalation message with context
                escalation = {
                    "type": "escalation",
                    "source_agent": agent_id,
                    "source_task": task_id,
                    "content": task.get("content", "No content"),
                    "timestamp": time.time(),
                    "priority": "high",
                    "context": {
                        "original_task": task,
                        "agent_status": load_status(agent_id, inbox_base),
                        "agent_inbox": messages
                    }
                }
                
                # Add to THEA's inbox
                thea_messages = json.loads(thea_inbox.read_text())
                if isinstance(thea_messages, list):
                    thea_messages.append(escalation)
                    thea_inbox.write_text(json.dumps(thea_messages, indent=2))
                    
                    # Start async THEA response handler
                    asyncio.create_task(thea_handler.handle_escalation(agent_id, task_id, escalation))
        except Exception as e:
            print(f"Error escalating task: {e}") 