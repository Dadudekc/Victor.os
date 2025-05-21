"""
Bridge Module 2: Telemetry
-------------------------
Provides comprehensive metrics collection, event tracking, and performance monitoring capabilities.
Implements Module 3 patterns for error handling and logging.
"""

import os
import time
import uuid
import json
import datetime
import statistics
from typing import Dict, Any, List, Tuple, Union, Optional
from collections import defaultdict

# Import Module 3 components
from bridge.modules.module3 import BridgeLogger, ErrorHandler

class BridgeTelemetry:
    """
    Main class for the Bridge Telemetry module.
    Provides metrics collection, event tracking, and performance monitoring capabilities.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Bridge Telemetry with the given configuration.
        
        Args:
            config: Configuration dictionary containing settings for telemetry
        """
        # Initialize configuration
        self.config = config
        
        # Initialize logger from Module 3
        self.logger = BridgeLogger(config.get('logger_config', {}))
        
        # Initialize error handler from Module 3
        self.error_handler = ErrorHandler(self.logger)
        
        # Initialize storage backend
        self.storage = self._initialize_storage()
        
        # Initialize metric aggregators
        self.aggregators = self._initialize_aggregators()
        
        # Initialize retention policy manager
        self.retention_manager = self._initialize_retention_manager()
        
        # Initialize real-time monitors
        self.monitors = self._initialize_monitors()
        
        # Statistics tracking
        self.stats = {
            "events_recorded": 0,
            "metrics_recorded": 0,
            "start_time": time.time()
        }
        
        # Log initialization
        self.logger.log({
            "source": "Bridge_Telemetry",
            "status": "INFO",
            "message": "Bridge Telemetry initialized successfully",
            "payload": {"config": {k: v for k, v in config.items() if k != "logger_config"}}
        })
    
    def _initialize_storage(self) -> Any:
        """
        Initialize the telemetry storage backend.
        
        Returns:
            Storage backend
        """
        storage_type = self.config.get('storage_type', 'memory')
        
        if storage_type == 'file':
            return FileStorage(self.config.get('storage_config', {}))
        else:
            return MemoryStorage(self.config.get('storage_config', {}))
    
    def _initialize_aggregators(self) -> Dict[str, Any]:
        """
        Initialize metric aggregators.
        
        Returns:
            Dictionary of aggregator functions by type
        """
        return {
            "mean": lambda values: statistics.mean(values) if values else 0,
            "sum": lambda values: sum(values) if values else 0,
            "min": lambda values: min(values) if values else 0,
            "max": lambda values: max(values) if values else 0,
            "count": lambda values: len(values)
        }
    
    def _initialize_retention_manager(self) -> Any:
        """
        Initialize retention policy manager.
        
        Returns:
            Retention policy manager
        """
        retention_config = self.config.get('retention_policy', {
            'events': {'duration_days': 7},
            'metrics': {'duration_days': 30}
        })
        
        return RetentionManager(retention_config, self.storage, self.logger)
    
    def _initialize_monitors(self) -> Dict[str, Any]:
        """
        Initialize real-time monitors.
        
        Returns:
            Dictionary of monitors by type
        """
        return {
            "system_health": SystemHealthMonitor(self.config.get('monitor_config', {}), self.logger),
            "performance": PerformanceMonitor(self.config.get('monitor_config', {}), self.logger),
            "error_rate": ErrorRateMonitor(self.config.get('monitor_config', {}), self.logger)
        }
    
    def _validate_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an event against schema.
        
        Args:
            event_data: The event data to validate
            
        Returns:
            Validation result dictionary
        """
        # Check required fields
        required_fields = ['event_type', 'source']
        missing_fields = [field for field in required_fields if field not in event_data]
        
        if missing_fields:
            return {
                "is_valid": False,
                "error_message": f"Missing required fields: {', '.join(missing_fields)}",
                "errors": {"missing_fields": missing_fields}
            }
            
        # Check event type
        if not isinstance(event_data.get('event_type'), str):
            return {
                "is_valid": False,
                "error_message": "Event type must be a string",
                "errors": {"invalid_type": "event_type"}
            }
            
        # Check source
        if not isinstance(event_data.get('source'), str):
            return {
                "is_valid": False,
                "error_message": "Source must be a string",
                "errors": {"invalid_type": "source"}
            }
            
        # Check data if present
        if 'data' in event_data and not isinstance(event_data.get('data'), dict):
            return {
                "is_valid": False,
                "error_message": "Data must be a dictionary",
                "errors": {"invalid_type": "data"}
            }
            
        return {
            "is_valid": True,
            "error_message": None,
            "errors": None
        }
    
    def record_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record a telemetry event.
        
        Args:
            event_data: Dictionary containing event information
            
        Returns:
            Dictionary containing the result of the operation
        """
        try:
            # Generate event ID if not provided
            if "event_id" not in event_data:
                event_data["event_id"] = str(uuid.uuid4())
                
            # Add timestamp if not provided
            if "timestamp" not in event_data:
                event_data["timestamp"] = datetime.datetime.utcnow().isoformat()
                
            # Validate event data
            validation_result = self._validate_event(event_data)
            if not validation_result["is_valid"]:
                return self.error_handler.create_error_response(
                    "INVALID_EVENT",
                    validation_result["error_message"],
                    {"validation_errors": validation_result["errors"]}
                )
                
            # Check for infinite loops or recursion
            if self.logger.detect_infinite_loop(event_data):
                return self.error_handler.create_error_response(
                    "LOOP_DETECTED",
                    "Event appears to be in an infinite loop"
                )
                
            # Store the event
            storage_result = self.storage.store_event(event_data)
            if not storage_result["success"]:
                return self.error_handler.create_error_response(
                    "STORAGE_FAILURE",
                    storage_result["error_message"]
                )
                
            # Update monitors for real-time analysis
            for monitor in self.monitors.values():
                monitor.process_event(event_data)
                
            # Update statistics
            self.stats["events_recorded"] += 1
            
            # Log event recording
            self.logger.log({
                "source": "Bridge_Telemetry",
                "status": "INFO",
                "message": f"Recorded event: {event_data.get('event_type')}",
                "payload": {"event_id": event_data["event_id"]}
            })
            
            # Return success
            return {
                "status": "success",
                "event_id": event_data["event_id"],
                "timestamp": event_data["timestamp"]
            }
            
        except Exception as e:
            # Handle unexpected errors
            return self.error_handler.handle_exception(e, context={"event_data": event_data})
            
    def record_metric(self, metric_name: str, metric_value: Union[int, float, str], 
                      context: Dict[str, Any] = None, timestamp: str = None) -> Dict[str, Any]:
        """
        Record a metric value for later analysis.
        
        Args:
            metric_name: Name of the metric to record
            metric_value: Value of the metric
            context: Additional contextual information
            timestamp: Optional timestamp (defaults to current time)
            
        Returns:
            Dictionary containing the result of the operation
        """
        try:
            # Validate metric name
            if not metric_name or not isinstance(metric_name, str):
                return self.error_handler.create_error_response(
                    "INVALID_METRIC_NAME",
                    "Metric name must be a non-empty string"
                )
                
            # Ensure metric value is numeric if not string
            if not isinstance(metric_value, (int, float, str)):
                return self.error_handler.create_error_response(
                    "INVALID_METRIC_VALUE",
                    "Metric value must be a number or string"
                )
                
            # Create metric event
            event_data = {
                "event_type": "METRIC",
                "source": "metrics_collector",
                "event_id": str(uuid.uuid4()),
                "timestamp": timestamp or datetime.datetime.utcnow().isoformat(),
                "data": {
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                    "context": context or {}
                }
            }
            
            # Store the metric
            storage_result = self.storage.store_metric(event_data)
            if not storage_result["success"]:
                return self.error_handler.create_error_response(
                    "STORAGE_FAILURE",
                    storage_result["error_message"]
                )
                
            # Update aggregators
            for aggregator in self.aggregators.values():
                if callable(getattr(aggregator, "process_metric", None)):
                    aggregator.process_metric(metric_name, metric_value, context, event_data["timestamp"])
                
            # Update statistics
            self.stats["metrics_recorded"] += 1
            
            # Log metric recording
            self.logger.log({
                "source": "Bridge_Telemetry",
                "status": "INFO",
                "message": f"Recorded metric: {metric_name}",
                "payload": {
                    "event_id": event_data["event_id"],
                    "metric_value": metric_value
                }
            })
            
            # Return success
            return {
                "status": "success",
                "event_id": event_data["event_id"],
                "timestamp": event_data["timestamp"]
            }
            
        except Exception as e:
            # Handle unexpected errors
            return self.error_handler.handle_exception(
                e, 
                context={
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                    "context": context
                }
            )
            
    def get_metrics(self, metric_names: List[str] = None, 
                   time_range: Tuple[str, str] = None, 
                   aggregation: str = "MEAN") -> Dict[str, Any]:
        """
        Retrieve aggregated metrics for the specified time range.
        
        Args:
            metric_names: List of metric names to retrieve (None for all)
            time_range: Tuple of (start_time, end_time) to retrieve metrics for
            aggregation: Aggregation method (MEAN, SUM, MIN, MAX, COUNT)
            
        Returns:
            Dictionary of metric names to aggregated values
        """
        try:
            # Validate parameters
            if aggregation not in ["MEAN", "SUM", "MIN", "MAX", "COUNT"]:
                return self.error_handler.create_error_response(
                    "INVALID_AGGREGATION",
                    f"Unsupported aggregation method: {aggregation}"
                )
                
            # Retrieve metrics from storage
            metrics_result = self.storage.retrieve_metrics(metric_names, time_range)
            if not metrics_result["success"]:
                return self.error_handler.create_error_response(
                    "RETRIEVAL_FAILURE",
                    metrics_result["error_message"]
                )
                
            # Aggregate metrics
            aggregator = self.aggregators.get(aggregation.lower(), self.aggregators["mean"])
            aggregated_metrics = {}
            
            for metric_name, metric_data in metrics_result["metrics"].items():
                aggregated_value = aggregator(metric_data["values"])
                aggregated_metrics[metric_name] = {
                    "value": aggregated_value,
                    "aggregation": aggregation,
                    "sample_count": len(metric_data["values"]),
                    "time_range": {
                        "start": metric_data["time_range"][0],
                        "end": metric_data["time_range"][1]
                    }
                }
                
            # Return aggregated metrics
            return {
                "status": "success",
                "metrics": aggregated_metrics
            }
            
        except Exception as e:
            # Handle unexpected errors
            return self.error_handler.handle_exception(
                e, 
                context={
                    "metric_names": metric_names,
                    "time_range": time_range,
                    "aggregation": aggregation
                }
            )
    
    def health_check(self) -> Dict[str, Any]:
        """
        Return health status of the Telemetry module.
        
        Returns:
            Dictionary containing health status information
        """
        uptime_seconds = int(time.time() - self.stats["start_time"])
        
        # Get retention info
        retention_info = self.retention_manager.get_retention_info()
        
        # Get storage usage
        storage_usage = self.storage.get_storage_info()
        
        return {
            "status": "healthy",
            "version": self.config.get("version", "0.8.0"),
            "uptime_seconds": uptime_seconds,
            "stats": {
                "events_recorded": self.stats["events_recorded"],
                "metrics_recorded": self.stats["metrics_recorded"],
                "data_retention_days": retention_info.get("metrics", {}).get("duration_days", 7),
                "storage_usage_percentage": storage_usage.get("usage_percentage", 0)
            }
        }


# Supporting classes for Telemetry

class MemoryStorage:
    """In-memory storage for telemetry events and metrics."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize memory storage."""
        self.events = []
        self.metrics = defaultdict(list)
        self.max_events = config.get('max_events', 10000)
        self.max_metrics_per_name = config.get('max_metrics_per_name', 1000)
    
    def store_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store an event in memory."""
        # Check if we need to truncate the events list
        if len(self.events) >= self.max_events:
            # Remove oldest events
            self.events = self.events[len(self.events) // 2:]
        
        # Add the event
        self.events.append(event_data)
        
        return {"success": True}
    
    def store_metric(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a metric in memory."""
        metric_name = event_data["data"]["metric_name"]
        metric_value = event_data["data"]["metric_value"]
        timestamp = event_data["timestamp"]
        
        # Check if we need to truncate the metrics list
        if len(self.metrics[metric_name]) >= self.max_metrics_per_name:
            # Remove oldest metrics
            self.metrics[metric_name] = self.metrics[metric_name][len(self.metrics[metric_name]) // 2:]
        
        # Add the metric
        self.metrics[metric_name].append({
            "value": metric_value, 
            "timestamp": timestamp,
            "event_id": event_data["event_id"]
        })
        
        return {"success": True}
    
    def retrieve_metrics(self, metric_names: List[str] = None, 
                       time_range: Tuple[str, str] = None) -> Dict[str, Any]:
        """Retrieve metrics from memory."""
        result_metrics = {}
        
        # Use all metrics if None specified
        if metric_names is None:
            metric_names = list(self.metrics.keys())
        
        # Set default time range if not provided
        if time_range is None:
            # Default to all time
            time_range = ("1970-01-01T00:00:00Z", datetime.datetime.utcnow().isoformat())
        
        # Process each requested metric
        for metric_name in metric_names:
            if metric_name in self.metrics:
                # Filter by time range
                filtered_metrics = []
                for metric in self.metrics[metric_name]:
                    if time_range[0] <= metric["timestamp"] <= time_range[1]:
                        filtered_metrics.append(metric)
                
                # Extract values for aggregation
                values = [m["value"] for m in filtered_metrics]
                
                # Only include metrics with values
                if values:
                    result_metrics[metric_name] = {
                        "values": values,
                        "time_range": time_range
                    }
        
        return {"success": True, "metrics": result_metrics}
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage usage information."""
        return {
            "usage_percentage": (len(self.events) / self.max_events) * 100,
            "event_count": len(self.events),
            "metric_names": len(self.metrics),
            "total_metrics": sum(len(metrics) for metrics in self.metrics.values())
        }


class FileStorage:
    """File-based storage for telemetry events and metrics."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize file storage."""
        self.events_file = config.get('events_file', 'runtime/data/telemetry/events.jsonl')
        self.metrics_file = config.get('metrics_file', 'runtime/data/telemetry/metrics.jsonl')
        self.metrics_index = {}
        
        # Create directories if they don't exist
        events_dir = os.path.dirname(self.events_file)
        metrics_dir = os.path.dirname(self.metrics_file)
        
        if events_dir and not os.path.exists(events_dir):
            os.makedirs(events_dir, exist_ok=True)
        
        if metrics_dir and not os.path.exists(metrics_dir):
            os.makedirs(metrics_dir, exist_ok=True)
        
        # Initialize metrics index
        self._load_metrics_index()
    
    def _load_metrics_index(self) -> None:
        """Load metrics index from file."""
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            metric = json.loads(line)
                            metric_name = metric["data"]["metric_name"]
                            
                            if metric_name not in self.metrics_index:
                                self.metrics_index[metric_name] = []
                                
                            self.metrics_index[metric_name].append({
                                "value": metric["data"]["metric_value"],
                                "timestamp": metric["timestamp"],
                                "event_id": metric["event_id"],
                                "line": line
                            })
                        except json.JSONDecodeError:
                            # Skip invalid lines
                            continue
        except Exception:
            # Start with empty index if file can't be read
            self.metrics_index = {}
    
    def store_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store an event in a file."""
        try:
            with open(self.events_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_data) + '\n')
            
            return {"success": True}
        except Exception as e:
            return {"success": False, "error_message": str(e)}
    
    def store_metric(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a metric in a file."""
        try:
            # Write to metrics file
            with open(self.metrics_file, 'a', encoding='utf-8') as f:
                line = json.dumps(event_data) + '\n'
                f.write(line)
            
            # Update index
            metric_name = event_data["data"]["metric_name"]
            
            if metric_name not in self.metrics_index:
                self.metrics_index[metric_name] = []
                
            self.metrics_index[metric_name].append({
                "value": event_data["data"]["metric_value"],
                "timestamp": event_data["timestamp"],
                "event_id": event_data["event_id"],
                "line": line
            })
            
            return {"success": True}
        except Exception as e:
            return {"success": False, "error_message": str(e)}
    
    def retrieve_metrics(self, metric_names: List[str] = None, 
                       time_range: Tuple[str, str] = None) -> Dict[str, Any]:
        """Retrieve metrics from file storage."""
        result_metrics = {}
        
        try:
            # Use all metrics if None specified
            if metric_names is None:
                metric_names = list(self.metrics_index.keys())
            
            # Set default time range if not provided
            if time_range is None:
                # Default to all time
                time_range = ("1970-01-01T00:00:00Z", datetime.datetime.utcnow().isoformat())
            
            # Process each requested metric
            for metric_name in metric_names:
                if metric_name in self.metrics_index:
                    # Filter by time range
                    filtered_metrics = []
                    for metric in self.metrics_index[metric_name]:
                        if time_range[0] <= metric["timestamp"] <= time_range[1]:
                            filtered_metrics.append(metric)
                    
                    # Extract values for aggregation
                    values = [m["value"] for m in filtered_metrics]
                    
                    # Only include metrics with values
                    if values:
                        result_metrics[metric_name] = {
                            "values": values,
                            "time_range": time_range
                        }
            
            return {"success": True, "metrics": result_metrics}
        except Exception as e:
            return {"success": False, "error_message": str(e)}
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage usage information."""
        try:
            events_size = os.path.getsize(self.events_file) if os.path.exists(self.events_file) else 0
            metrics_size = os.path.getsize(self.metrics_file) if os.path.exists(self.metrics_file) else 0
            
            # Arbitrary "full" size for percentage calculation
            max_size = 100 * 1024 * 1024  # 100MB
            
            return {
                "usage_percentage": ((events_size + metrics_size) / max_size) * 100,
                "events_size_bytes": events_size,
                "metrics_size_bytes": metrics_size,
                "metric_names": len(self.metrics_index),
                "total_metrics": sum(len(metrics) for metrics in self.metrics_index.values())
            }
        except Exception:
            return {
                "usage_percentage": 0,
                "events_size_bytes": 0,
                "metrics_size_bytes": 0,
                "metric_names": 0,
                "total_metrics": 0
            }


class RetentionManager:
    """Manages data retention policies for telemetry data."""
    
    def __init__(self, config: Dict[str, Any], storage: Any, logger: BridgeLogger):
        """Initialize retention manager."""
        self.config = config
        self.storage = storage
        self.logger = logger
        self.last_cleanup = 0
        self.cleanup_interval = config.get('cleanup_interval_hours', 24) * 3600  # Convert to seconds
    
    def get_retention_info(self) -> Dict[str, Any]:
        """Get retention policy information."""
        return self.config
    
    def check_retention(self) -> None:
        """Check if retention policies need to be applied."""
        now = time.time()
        
        # Only run cleanup at specified intervals
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        self.last_cleanup = now
        
        # Apply retention policies
        self._apply_retention_policies()
    
    def _apply_retention_policies(self) -> None:
        """Apply retention policies to telemetry data."""
        # In a real implementation, this would delete old data
        self.logger.log({
            "source": "Bridge_Telemetry",
            "status": "INFO",
            "message": "Applying retention policies",
            "payload": {"retention_policies": self.config}
        })


class SystemHealthMonitor:
    """Monitors system health based on telemetry data."""
    
    def __init__(self, config: Dict[str, Any], logger: BridgeLogger):
        """Initialize system health monitor."""
        self.config = config
        self.logger = logger
        self.health_metrics = {}
    
    def process_event(self, event_data: Dict[str, Any]) -> None:
        """Process an event for system health monitoring."""
        # Extract health-related metrics from event
        if event_data.get('event_type') == 'SYSTEM_HEALTH':
            # Process system health event
            pass


class PerformanceMonitor:
    """Monitors performance metrics based on telemetry data."""
    
    def __init__(self, config: Dict[str, Any], logger: BridgeLogger):
        """Initialize performance monitor."""
        self.config = config
        self.logger = logger
        self.performance_metrics = {}
    
    def process_event(self, event_data: Dict[str, Any]) -> None:
        """Process an event for performance monitoring."""
        # Extract performance-related metrics from event
        if event_data.get('event_type') == 'PERFORMANCE':
            # Process performance event
            pass


class ErrorRateMonitor:
    """Monitors error rates based on telemetry data."""
    
    def __init__(self, config: Dict[str, Any], logger: BridgeLogger):
        """Initialize error rate monitor."""
        self.config = config
        self.logger = logger
        self.error_counts = defaultdict(int)
        self.total_events = 0
    
    def process_event(self, event_data: Dict[str, Any]) -> None:
        """Process an event for error rate monitoring."""
        # Count total events
        self.total_events += 1
        
        # Extract error-related metrics from event
        if event_data.get('status') == 'ERROR':
            error_code = event_data.get('errorDetails', {}).get('errorCode', 'UNKNOWN_ERROR')
            self.error_counts[error_code] += 1
            
            # Check error threshold
            error_threshold = self.config.get('error_threshold_percentage', 5)
            error_rate = (sum(self.error_counts.values()) / self.total_events) * 100
            
            if error_rate > error_threshold:
                self.logger.log({
                    "source": "Bridge_Telemetry",
                    "status": "WARNING",
                    "message": f"Error rate exceeded threshold: {error_rate:.2f}% > {error_threshold}%",
                    "payload": {
                        "error_counts": dict(self.error_counts),
                        "total_events": self.total_events
                    }
                }, log_level="WARNING")


# Module-level functions for easier usage

def record_event(event_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Record a telemetry event.
    
    Args:
        event_data: The event to record
        config: Optional configuration for the telemetry
        
    Returns:
        Event recording result
    """
    # Use singleton pattern for default configuration
    global _default_telemetry
    
    if config is not None:
        # Create a new telemetry instance with the provided config
        telemetry = BridgeTelemetry(config)
        return telemetry.record_event(event_data)
    else:
        # Use or create the default telemetry
        if '_default_telemetry' not in globals():
            _default_telemetry = BridgeTelemetry({
                'logger_config': {
                    'log_path': 'runtime/logs/bridge_telemetry.jsonl',
                    'enable_console': True
                }
            })
        
        return _default_telemetry.record_event(event_data)

def record_metric(metric_name: str, metric_value: Union[int, float, str], 
                 context: Dict[str, Any] = None, timestamp: str = None, 
                 config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Record a metric value.
    
    Args:
        metric_name: Name of the metric to record
        metric_value: Value of the metric
        context: Additional contextual information
        timestamp: Optional timestamp
        config: Optional configuration for the telemetry
        
    Returns:
        Metric recording result
    """
    global _default_telemetry
    
    if config is not None:
        # Create a new telemetry instance with the provided config
        telemetry = BridgeTelemetry(config)
        return telemetry.record_metric(metric_name, metric_value, context, timestamp)
    else:
        # Use or create the default telemetry
        if '_default_telemetry' not in globals():
            _default_telemetry = BridgeTelemetry({
                'logger_config': {
                    'log_path': 'runtime/logs/bridge_telemetry.jsonl',
                    'enable_console': True
                }
            })
        
        return _default_telemetry.record_metric(metric_name, metric_value, context, timestamp)

def get_metrics(metric_names: List[str] = None, time_range: Tuple[str, str] = None, 
               aggregation: str = "MEAN", config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get aggregated metrics.
    
    Args:
        metric_names: List of metric names to retrieve
        time_range: Tuple of (start_time, end_time)
        aggregation: Aggregation method
        config: Optional configuration for the telemetry
        
    Returns:
        Aggregated metrics
    """
    global _default_telemetry
    
    if config is not None:
        # Create a new telemetry instance with the provided config
        telemetry = BridgeTelemetry(config)
        return telemetry.get_metrics(metric_names, time_range, aggregation)
    else:
        # Use or create the default telemetry
        if '_default_telemetry' not in globals():
            _default_telemetry = BridgeTelemetry({
                'logger_config': {
                    'log_path': 'runtime/logs/bridge_telemetry.jsonl',
                    'enable_console': True
                }
            })
        
        return _default_telemetry.get_metrics(metric_names, time_range, aggregation)

def health_check(config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get health status of the telemetry.
    
    Args:
        config: Optional configuration for the telemetry
        
    Returns:
        Health status information
    """
    global _default_telemetry
    
    if config is not None:
        # Create a new telemetry instance with the provided config
        telemetry = BridgeTelemetry(config)
        return telemetry.health_check()
    else:
        # Use or create the default telemetry
        if '_default_telemetry' not in globals():
            _default_telemetry = BridgeTelemetry({
                'logger_config': {
                    'log_path': 'runtime/logs/bridge_telemetry.jsonl',
                    'enable_console': True
                }
            })
        
        return _default_telemetry.health_check() 