"""
Configuration for Agent-3.
"""

from typing import Dict, Any

DEFAULT_CONFIG: Dict[str, Any] = {
    "agent_id": "agent3",
    "cycle_interval": 1.0,  # seconds between cycles
    "pause_duration": 60,   # seconds to pause after min_cycles
    "continuous_mode": True,
    "min_cycles_before_pause": 25,
    
    "recovery": {
        "max_retries": 3,
        "retry_delay": 1.0,
        "backoff_factor": 2.0
    },
    
    "metrics": {
        "collection_interval": 60,  # seconds between metric reports
        "retention_period": 3600,   # seconds to keep metrics
        "enabled_metrics": [
            "cycle_count",
            "task_processing_time",
            "error_count",
            "heartbeat_latency"
        ]
    },
    
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file": "agent3.log"
    },
    
    "emergency": {
        "max_consecutive_errors": 5,
        "error_threshold_period": 300,  # 5 minutes
        "auto_shutdown": False,
        "max_consecutive_checkpoint_failures": 3,
        "checkpoint_failure_threshold": 0.7,  # 70% of checkpoints must pass
        "emergency_procedures": {
            "auto_shutdown": False,
            "notify_admin": True,
            "enter_degraded_mode": True,
            "retry_interval": 60  # seconds between retry attempts
        }
    },
    
    "checkpoint": {
        "verification_interval": 60,  # seconds between verification cycles
        "metrics_retention_period": 3600,  # seconds to keep metrics history
        "max_heartbeat_interval": 10,  # seconds
        "checkpoints": {
            "continuous_operation": {
                "required": True,
                "verification_interval": 300  # 5 minutes
            },
            "cycle_completion": {
                "required": True,
                "min_cycles": 25,
                "verification_interval": 60  # 1 minute
            },
            "error_rate": {
                "required": True,
                "max_rate": 0.1,  # 10%
                "verification_interval": 300  # 5 minutes
            },
            "heartbeat_health": {
                "required": True,
                "max_latency": 1.0,  # seconds
                "verification_interval": 60  # 1 minute
            },
            "task_completion": {
                "required": True,
                "verification_interval": 300  # 5 minutes
            }
        }
    }
}

def get_config() -> Dict[str, Any]:
    """Get Agent-3 configuration.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    # In a real implementation, this would load from a file or environment
    return DEFAULT_CONFIG.copy()

# Agent identification
AGENT_ID = "agent3"
AGENT_NAME = "Autonomous Loop Engineer"
AGENT_VERSION = "1.0.0"

# Operation settings
CYCLE_INTERVAL = 1.0  # seconds
MAX_CYCLES_BEFORE_PAUSE = 25
HEARTBEAT_INTERVAL = 5.0  # seconds

# Task processing settings
MAX_TASK_RETRIES = 3
TASK_TIMEOUT = 300  # seconds

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Event subscriptions
EVENT_SUBSCRIPTIONS = [
    "task.created",
    "task.updated",
    "task.completed",
    "task.failed",
    "agent.error",
    "system.cursor",
    "system.cursor.stuck"
]

# Performance metrics
METRICS_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "collection_interval": 60,  # seconds
    "metrics": [
        "cycle_count",
        "task_processing_time",
        "error_rate",
        "heartbeat_latency"
    ]
}

# Recovery settings
RECOVERY_CONFIG: Dict[str, Any] = {
    "max_retries": 3,
    "retry_delay": 5,  # seconds
    "backoff_factor": 2
}

# Safety limits
SAFETY_LIMITS: Dict[str, Any] = {
    "max_concurrent_tasks": 1,
    "max_memory_usage": 512,  # MB
    "max_cpu_usage": 80,  # percentage
    "max_error_rate": 0.1  # 10% error rate threshold
} 