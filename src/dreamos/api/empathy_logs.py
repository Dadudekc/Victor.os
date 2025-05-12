"""
Empathy Logs API

Provides endpoints for accessing and filtering empathy logs.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import re

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()

class LogEntry(BaseModel):
    """Model for log entries."""
    timestamp: str
    type: str
    severity: Optional[str]
    content: str
    agent_id: Optional[str]

def parse_log_content(content: str) -> Dict[str, Any]:
    """
    Parse log content and extract relevant information.
    
    Args:
        content: Raw log content
        
    Returns:
        Dictionary containing parsed log data
    """
    # Determine log type
    if "# Violation Detected" in content or "VIOLATION" in content.splitlines()[0]:
        log_type = "violation"
    elif "# Compliance Check" in content or "COMPLIANCE" in content.splitlines()[0]:
        log_type = "compliance"
    else:
        log_type = "compliance"  # Default to compliance if not clear
    
    # Extract metadata
    metadata = {
        "timestamp": None,
        "agent_id": None,
        "type": log_type,
        "severity": "info",
        "metrics": {
            "loop_duration": 0.0,
            "reflection_gap": 0.0,
            "task_complexity": 0.0,
            "compliance_score": 0.0
        }
    }
    
    # Extract timestamp
    timestamp_match = re.search(r"\[(.*?)\]", content)
    if timestamp_match:
        metadata["timestamp"] = timestamp_match.group(1)
    
    # Extract agent ID
    agent_match = re.search(r'(?:Agent|\*\*Agent\*\*):\s*([\w\-]+)', content)
    if agent_match:
        metadata["agent_id"] = agent_match.group(1)
    
    # Extract severity
    severity_match = re.search(r"Severity: (\w+)", content)
    if severity_match:
        metadata["severity"] = severity_match.group(1).lower()
    
    # Extract metrics
    metrics = {
        "loop_duration": float(re.search(r"(?:\*\*Loop Duration\*\*|Loop Duration): ([\d.]+)", content).group(1)) if re.search(r"(?:\*\*Loop Duration\*\*|Loop Duration): ([\d.]+)", content) else 0.0,
        "reflection_gap": float(re.search(r"(?:\*\*Reflection Gap\*\*|Reflection Gap): ([\d.]+)", content).group(1)) if re.search(r"(?:\*\*Reflection Gap\*\*|Reflection Gap): ([\d.]+)", content) else 0.0,
        "task_complexity": float(re.search(r"(?:\*\*Task Complexity\*\*|Task Complexity): ([\d.]+)", content).group(1)) if re.search(r"(?:\*\*Task Complexity\*\*|Task Complexity): ([\d.]+)", content) else 0.0,
        "compliance_score": float(re.search(r"(?:\*\*Compliance Score\*\*|Compliance Score): ([\d.]+)", content).group(1)) if re.search(r"(?:\*\*Compliance Score\*\*|Compliance Score): ([\d.]+)", content) else 0.0
    }
    metadata["metrics"] = metrics
    
    # Set top-level keys for backward compatibility
    metadata["loop_duration"] = metrics["loop_duration"]
    metadata["reflection_gap"] = metrics["reflection_gap"]
    metadata["task_complexity"] = metrics["task_complexity"]
    
    return metadata

def get_log_entries(
    log_dir: Path,
    log_type: Optional[str] = None,
    severity: Optional[str] = None,
    agent_id: Optional[str] = None,
    days: int = 7
) -> List[LogEntry]:
    """Get log entries with optional filtering."""
    entries = []
    cutoff = datetime.now() - timedelta(days=days)
    
    # Get all log files
    log_files = []
    if log_type:
        log_files.extend(log_dir.glob(f"{log_type}_*.md"))
    else:
        log_files.extend(log_dir.glob("*.md"))
        
    for log_file in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True):
        # Check file age
        if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
            continue
            
        # Read and parse log file
        with open(log_file) as f:
            content = f.read()
            log_data = parse_log_content(content)
            
            # Apply filters
            if severity and log_data['severity'] != severity:
                continue
            if agent_id and log_data['agent_id'] != agent_id:
                continue
                
            entries.append(LogEntry(
                timestamp=log_data['timestamp'],
                type=log_data['type'],
                severity=log_data['severity'],
                content=content,
                agent_id=log_data['agent_id']
            ))
            
    return entries

@router.get("/api/empathy/logs")
async def get_logs(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    log_type: Optional[str] = Query(None, description="Filter by log type"),
    start_date: Optional[str] = Query(None, description="Filter by start date"),
    end_date: Optional[str] = Query(None, description="Filter by end date")
) -> List[Dict]:
    """
    Get logs with optional filtering.
    
    Args:
        agent_id: Filter by agent ID
        log_type: Filter by log type (compliance/violation)
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)
        
    Returns:
        List of log entries
    """
    log_dir = Path("runtime/logs/empathy")
    if not log_dir.exists():
        return []
    
    logs = []
    for log_file in log_dir.glob("*.md"):
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            log_data = parse_log_content(content)
            
            # Apply filters
            if agent_id and log_data["agent_id"] != agent_id:
                continue
            if log_type and log_data["type"] != log_type:
                continue
            if start_date and log_data["timestamp"] < start_date:
                continue
            if end_date and log_data["timestamp"] > end_date:
                continue
            
            logs.append(log_data)
    
    return sorted(logs, key=lambda x: x["timestamp"] if x["timestamp"] else "", reverse=True)

@router.get("/api/empathy/agents")
async def get_agents() -> List[str]:
    """Get list of agents with log entries."""
    try:
        log_dir = Path("runtime/logs/empathy")
        if not log_dir.exists():
            raise HTTPException(status_code=404, detail="Log directory not found")
            
        agents = set()
        for log_file in log_dir.glob("*.md"):
            with open(log_file) as f:
                content = f.read()
                log_data = parse_log_content(content)
                if log_data['agent_id']:
                    agents.add(log_data['agent_id'])
                    
        return sorted(list(agents))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def export_logs(
    agent_id: Optional[str] = None,
    log_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "markdown"
) -> Dict:
    """
    Export logs in the specified format.
    
    Args:
        agent_id: Filter by agent ID
        log_type: Filter by log type (compliance/violation)
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)
        format: Export format (markdown/json)
        
    Returns:
        Dictionary containing export data
    """
    logs = await get_logs(agent_id, log_type, start_date, end_date)
    
    if format == "markdown":
        content = "# Empathy Intelligence Logs\n\n"
        for log in logs:
            content += f"## {log['timestamp']} - {log['type'].upper()}\n"
            content += f"Agent: {log['agent_id']}\n"
            content += f"Severity: {log['severity']}\n\n"
            content += "### Metrics\n"
            for metric, value in log['metrics'].items():
                content += f"- {metric}: {value}\n"
            content += "\n"
        return {"content": content, "format": "markdown"}
    else:
        return {"content": json.dumps(logs, indent=2), "format": "json"} 