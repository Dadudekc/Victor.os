"""Agent reporting utilities for standardized output formatting."""

from typing import Optional

def format_agent_report(
    agent_id: str,
    task: str,
    status: str,
    action: str,
    agent_name: Optional[str] = None
) -> str:
    """Format a standardized agent report string.
    
    Args:
        agent_id: The unique identifier of the agent.
        task: Description of the task being performed.
        status: Current status of the task.
        action: Action being taken or completed.
        agent_name: Optional display name for the agent.
        
    Returns:
        str: A formatted report string in the format:
             [AgentName] Task: <task> | Status: <status> | Action: <action>
    """
    agent_display = agent_name or agent_id
    return f"[{agent_display}] Task: {task} | Status: {status} | Action: {action}" 