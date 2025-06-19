import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MetricsLogger:
    """Centralized metrics logging for Dream.OS swarm operations."""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.metrics_file = workspace_root / "runtime" / "episode-metrics.json"
        self.status_file = workspace_root / "runtime" / "agent_status.json"
        self._ensure_metrics_files()
    
    def _ensure_metrics_files(self):
        """Ensure metrics files exist with proper structure."""
        if not self.metrics_file.exists():
            self._initialize_metrics_file()
        if not self.status_file.exists():
            self._initialize_status_file()
    
    def _initialize_metrics_file(self):
        """Initialize episode metrics file with default structure."""
        default_metrics = {
            "version": "1.0",
            "last_updated": datetime.utcnow().isoformat(),
            "metrics": {
                "task_execution": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "average_latency_ms": 0,
                    "recent_executions": []
                },
                "task_handoff": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "average_handoff_time_ms": 0,
                    "recent_handoffs": []
                },
                "help_requests": {
                    "total": 0,
                    "resolved": 0,
                    "pending": 0,
                    "average_resolution_time_ms": 0,
                    "recent_requests": []
                },
                "recovery_actions": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "recent_recoveries": []
                },
                "injection_stats": {
                    "total_attempts": 0,
                    "successful": 0,
                    "failed": 0,
                    "average_latency_ms": 0,
                    "retry_count": 0,
                    "image_match_failures": 0,
                    "recent_injections": [],
                    "per_agent": {}
                },
                "drift_metrics": {
                    "total_drift_events": 0,
                    "total_recovery_attempts": 0,
                    "total_recovery_success": 0,
                    "average_recovery_time_sec": 0,
                    "recent_drift_events": [],
                    "per_agent": {}
                }
            },
            "agent_metrics": {},
            "system_health": {
                "last_check": datetime.utcnow().isoformat(),
                "active_agents": 0,
                "total_messages_processed": 0,
                "recovery_triggered": False,
                "drift_threshold_exceeded": False
            }
        }
        self._write_metrics(default_metrics)
    
    def _initialize_status_file(self):
        """Initialize agent status file with default structure."""
        default_status = {
            "version": "1.0",
            "last_updated": datetime.utcnow().isoformat(),
            "agents": {},
            "system": {
                "total_agents": 0,
                "active_agents": 0,
                "last_health_check": datetime.utcnow().isoformat(),
                "recovery_triggered": False,
                "drift_threshold": 300,
                "drift_exceeded": False
            }
        }
        self._write_status(default_status)
    
    def _read_metrics(self) -> Dict[str, Any]:
        """Read current metrics from file."""
        try:
            with open(self.metrics_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading metrics file: {e}")
            return {}
    
    def _read_status(self) -> Dict[str, Any]:
        """Read current agent status from file."""
        try:
            with open(self.status_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading status file: {e}")
            return {}
    
    def _write_metrics(self, metrics: Dict[str, Any]):
        """Write metrics to file."""
        try:
            metrics["last_updated"] = datetime.utcnow().isoformat()
            with open(self.metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing metrics file: {e}")
    
    def _write_status(self, status: Dict[str, Any]):
        """Write agent status to file."""
        try:
            status["last_updated"] = datetime.utcnow().isoformat()
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing status file: {e}")
    
    def log_task_execution_metrics(self, agent_id: str, task_id: str, 
                                 start_time: float, end_time: float,
                                 success: bool, error: Optional[str] = None,
                                 response_size: Optional[int] = None,
                                 token_count: Optional[int] = None):
        """Log metrics for task execution."""
        metrics = self._read_metrics()
        execution_time = (end_time - start_time) * 1000  # Convert to ms
        
        # Update task execution metrics
        metrics["metrics"]["task_execution"]["total"] += 1
        if success:
            metrics["metrics"]["task_execution"]["successful"] += 1
        else:
            metrics["metrics"]["task_execution"]["failed"] += 1
        
        # Update average latency
        current_avg = metrics["metrics"]["task_execution"]["average_latency_ms"]
        total = metrics["metrics"]["task_execution"]["total"]
        metrics["metrics"]["task_execution"]["average_latency_ms"] = (
            (current_avg * (total - 1) + execution_time) / total
        )
        
        # Add to recent executions
        recent = metrics["metrics"]["task_execution"]["recent_executions"]
        recent.append({
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": agent_id,
            "task_id": task_id,
            "execution_time_ms": execution_time,
            "success": success,
            "error": error,
            "response_size": response_size,
            "token_count": token_count
        })
        metrics["metrics"]["task_execution"]["recent_executions"] = recent[-10:]  # Keep last 10
        
        # Update agent metrics
        if agent_id not in metrics["agent_metrics"]:
            metrics["agent_metrics"][agent_id] = {
                "last_active": datetime.utcnow().isoformat(),
                "cycle_count": 0,
                "error_count": 0,
                "recovery_count": 0,
                "message_processing": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0
                }
            }
        
        agent_metrics = metrics["agent_metrics"][agent_id]
        agent_metrics["last_active"] = datetime.utcnow().isoformat()
        if not success:
            agent_metrics["error_count"] += 1
        
        self._write_metrics(metrics)
    
    def log_agent_cycle_update(self, agent_id: str, errors_this_cycle: int = 0):
        """Log metrics for agent cycle completion."""
        status = self._read_status()
        metrics = self._read_metrics()
        
        # Update agent status
        if agent_id not in status["agents"]:
            status["agents"][agent_id] = {
                "status": "active",
                "last_active": datetime.utcnow().isoformat(),
                "cycle_count": 0,
                "current_task": None,
                "error_count": 0,
                "recovery_count": 0,
                "message_queue": {
                    "total": 0,
                    "processed": 0,
                    "failed": 0
                }
            }
        
        agent_status = status["agents"][agent_id]
        agent_status["last_active"] = datetime.utcnow().isoformat()
        agent_status["cycle_count"] += 1
        agent_status["error_count"] += errors_this_cycle
        
        # Update metrics
        if agent_id not in metrics["agent_metrics"]:
            metrics["agent_metrics"][agent_id] = {
                "last_active": datetime.utcnow().isoformat(),
                "cycle_count": 0,
                "error_count": 0,
                "recovery_count": 0,
                "message_processing": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0
                }
            }
        
        agent_metrics = metrics["agent_metrics"][agent_id]
        agent_metrics["last_active"] = datetime.utcnow().isoformat()
        agent_metrics["cycle_count"] += 1
        agent_metrics["error_count"] += errors_this_cycle
        
        # Update system health
        metrics["system_health"]["last_check"] = datetime.utcnow().isoformat()
        metrics["system_health"]["active_agents"] = len([
            a for a in status["agents"].values() 
            if a["status"] == "active"
        ])
        
        self._write_status(status)
        self._write_metrics(metrics)
    
    def log_help_response_metrics(self, requestor_id: str, responder_id: str,
                                request_time: float, response_time: float,
                                success: bool, error: Optional[str] = None):
        """Log metrics for help request/response cycle."""
        metrics = self._read_metrics()
        resolution_time = (response_time - request_time) * 1000  # Convert to ms
        
        # Update help request metrics
        metrics["metrics"]["help_requests"]["total"] += 1
        if success:
            metrics["metrics"]["help_requests"]["resolved"] += 1
        else:
            metrics["metrics"]["help_requests"]["pending"] += 1
        
        # Update average resolution time
        current_avg = metrics["metrics"]["help_requests"]["average_resolution_time_ms"]
        total = metrics["metrics"]["help_requests"]["total"]
        metrics["metrics"]["help_requests"]["average_resolution_time_ms"] = (
            (current_avg * (total - 1) + resolution_time) / total
        )
        
        # Add to recent requests
        recent = metrics["metrics"]["help_requests"]["recent_requests"]
        recent.append({
            "timestamp": datetime.utcnow().isoformat(),
            "requestor_id": requestor_id,
            "responder_id": responder_id,
            "resolution_time_ms": resolution_time,
            "success": success,
            "error": error
        })
        metrics["metrics"]["help_requests"]["recent_requests"] = recent[-10:]  # Keep last 10
        
        self._write_metrics(metrics)
    
    def log_injection_metrics(self, agent_id: str, 
                            start_time: float,
                            end_time: float,
                            success: bool,
                            retry_count: int = 0,
                            image_match_failed: bool = False,
                            error: Optional[str] = None):
        """Log metrics for PyAutoGUI injection attempts.
        
        Args:
            agent_id: ID of the agent performing the injection
            start_time: Timestamp when injection started
            end_time: Timestamp when injection completed
            success: Whether injection was successful
            retry_count: Number of retry attempts
            image_match_failed: Whether image matching failed
            error: Error message if injection failed
        """
        metrics = self._read_metrics()
        injection_time = (end_time - start_time) * 1000  # Convert to ms
        
        # Update injection stats
        stats = metrics["metrics"]["injection_stats"]
        stats["total_attempts"] += 1
        if success:
            stats["successful"] += 1
        else:
            stats["failed"] += 1
        stats["retry_count"] += retry_count
        if image_match_failed:
            stats["image_match_failures"] += 1
        
        # Update average latency
        current_avg = stats["average_latency_ms"]
        total = stats["total_attempts"]
        stats["average_latency_ms"] = (
            (current_avg * (total - 1) + injection_time) / total
        )
        
        # Add to recent injections
        recent = stats["recent_injections"]
        recent.append({
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": agent_id,
            "injection_time_ms": injection_time,
            "success": success,
            "retry_count": retry_count,
            "image_match_failed": image_match_failed,
            "error": error
        })
        stats["recent_injections"] = recent[-10:]  # Keep last 10
        
        # Update per-agent stats
        if agent_id not in stats["per_agent"]:
            stats["per_agent"][agent_id] = {
                "total_attempts": 0,
                "successful": 0,
                "failed": 0,
                "retry_count": 0,
                "image_match_failures": 0,
                "average_latency_ms": 0
            }
        
        agent_stats = stats["per_agent"][agent_id]
        agent_stats["total_attempts"] += 1
        if success:
            agent_stats["successful"] += 1
        else:
            agent_stats["failed"] += 1
        agent_stats["retry_count"] += retry_count
        if image_match_failed:
            agent_stats["image_match_failures"] += 1
        
        # Update agent average latency
        current_agent_avg = agent_stats["average_latency_ms"]
        agent_total = agent_stats["total_attempts"]
        agent_stats["average_latency_ms"] = (
            (current_agent_avg * (agent_total - 1) + injection_time) / agent_total
        )
        
        self._write_metrics(metrics)
    
    def log_drift_event(self, agent_id: str, 
                       drift_start_time: float,
                       drift_end_time: Optional[float] = None,
                       recovery_attempted: bool = False,
                       recovery_successful: bool = False,
                       recovery_error: Optional[str] = None):
        """Log metrics for agent drift events and recovery attempts.
        
        Args:
            agent_id: ID of the agent that drifted
            drift_start_time: Timestamp when drift was detected
            drift_end_time: Timestamp when drift ended (if recovered)
            recovery_attempted: Whether recovery was attempted
            recovery_successful: Whether recovery was successful
            recovery_error: Error message if recovery failed
        """
        metrics = self._read_metrics()
        drift_metrics = metrics["metrics"]["drift_metrics"]
        
        # Calculate drift duration if recovered
        drift_duration = None
        if drift_end_time:
            drift_duration = drift_end_time - drift_start_time
        
        # Update global drift metrics
        drift_metrics["total_drift_events"] += 1
        if recovery_attempted:
            drift_metrics["total_recovery_attempts"] += 1
        if recovery_successful:
            drift_metrics["total_recovery_success"] += 1
            if drift_duration:
                # Update average recovery time
                current_avg = drift_metrics["average_recovery_time_sec"]
                total = drift_metrics["total_recovery_success"]
                drift_metrics["average_recovery_time_sec"] = (
                    (current_avg * (total - 1) + drift_duration) / total
                )
        
        # Add to recent drift events
        recent = drift_metrics["recent_drift_events"]
        recent.append({
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": agent_id,
            "drift_start": datetime.fromtimestamp(drift_start_time).isoformat(),
            "drift_end": datetime.fromtimestamp(drift_end_time).isoformat() if drift_end_time else None,
            "drift_duration_sec": drift_duration,
            "recovery_attempted": recovery_attempted,
            "recovery_successful": recovery_successful,
            "recovery_error": recovery_error
        })
        drift_metrics["recent_drift_events"] = recent[-10:]  # Keep last 10
        
        # Update per-agent drift metrics
        if agent_id not in drift_metrics["per_agent"]:
            drift_metrics["per_agent"][agent_id] = {
                "drift_events": 0,
                "avg_drift_duration_sec": 0,
                "recovery_attempts": 0,
                "recovery_success": 0,
                "last_drift_time": None,
                "total_drift_duration_sec": 0
            }
        
        agent_drift = drift_metrics["per_agent"][agent_id]
        agent_drift["drift_events"] += 1
        if recovery_attempted:
            agent_drift["recovery_attempts"] += 1
        if recovery_successful:
            agent_drift["recovery_success"] += 1
            if drift_duration:
                agent_drift["total_drift_duration_sec"] += drift_duration
                # Update average drift duration
                agent_drift["avg_drift_duration_sec"] = (
                    agent_drift["total_drift_duration_sec"] / agent_drift["recovery_success"]
                )
        
        agent_drift["last_drift_time"] = datetime.fromtimestamp(drift_start_time).isoformat()
        
        # Update system health
        metrics["system_health"]["recovery_triggered"] = recovery_attempted
        metrics["system_health"]["drift_threshold_exceeded"] = True
        
        self._write_metrics(metrics)
        
        # Update agent status
        status = self._read_status()
        if agent_id in status["agents"]:
            agent_status = status["agents"][agent_id]
            agent_status["status"] = "recovering" if recovery_attempted else "drifting"
            agent_status["last_active"] = datetime.utcnow().isoformat()
            self._write_status(status) 