"""
Agent 002 - Data Processing Agent
Responsible for data collection, validation, and processing tasks.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging
import json
import uuid
import re

from ..core.coordination.base_agent import BaseAgent
from ..core.agent_identity import AgentIdentity
from ..core.empathy_scoring import EmpathyScorer
from ..utils.common_utils import get_logger


@dataclass
class DataTask:
    """Represents a data processing task."""
    
    task_id: str
    data_type: str
    source: str
    destination: str
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    processing_steps: List[str] = field(default_factory=list)
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataValidator:
    """Validates data according to specified rules."""
    
    def __init__(self):
        self.validation_patterns = {
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "phone": r"^\+?1?\d{9,15}$",
            "url": r"^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$",
            "date": r"^\d{4}-\d{2}-\d{2}$",
            "timestamp": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?$"
        }
    
    def validate_field(self, value: Any, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single field according to rules."""
        result = {"valid": True, "errors": []}
        
        # Check required field
        if rule.get("required", False) and (value is None or value == ""):
            result["valid"] = False
            result["errors"].append("Field is required")
            return result
        
        if value is None or value == "":
            return result  # Skip validation for empty optional fields
        
        # Check data type
        expected_type = rule.get("type")
        if expected_type:
            if expected_type == "string" and not isinstance(value, str):
                result["valid"] = False
                result["errors"].append(f"Expected string, got {type(value).__name__}")
            elif expected_type == "number" and not isinstance(value, (int, float)):
                result["valid"] = False
                result["errors"].append(f"Expected number, got {type(value).__name__}")
            elif expected_type == "boolean" and not isinstance(value, bool):
                result["valid"] = False
                result["errors"].append(f"Expected boolean, got {type(value).__name__}")
        
        # Check pattern
        pattern = rule.get("pattern")
        if pattern and isinstance(value, str):
            if pattern in self.validation_patterns:
                pattern = self.validation_patterns[pattern]
            
            if not re.match(pattern, value):
                result["valid"] = False
                result["errors"].append(f"Value does not match pattern: {pattern}")
        
        # Check min/max length
        if isinstance(value, str):
            min_length = rule.get("min_length")
            max_length = rule.get("max_length")
            
            if min_length and len(value) < min_length:
                result["valid"] = False
                result["errors"].append(f"Minimum length is {min_length}")
            
            if max_length and len(value) > max_length:
                result["valid"] = False
                result["errors"].append(f"Maximum length is {max_length}")
        
        # Check min/max value
        if isinstance(value, (int, float)):
            min_value = rule.get("min_value")
            max_value = rule.get("max_value")
            
            if min_value is not None and value < min_value:
                result["valid"] = False
                result["errors"].append(f"Minimum value is {min_value}")
            
            if max_value is not None and value > max_value:
                result["valid"] = False
                result["errors"].append(f"Maximum value is {max_value}")
        
        return result
    
    def validate_data(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against a schema."""
        result = {"valid": True, "errors": {}, "summary": {"total_fields": 0, "valid_fields": 0, "invalid_fields": 0}}
        
        for field_name, field_rules in schema.items():
            result["summary"]["total_fields"] += 1
            field_value = data.get(field_name)
            
            field_result = self.validate_field(field_value, field_rules)
            
            if field_result["valid"]:
                result["summary"]["valid_fields"] += 1
            else:
                result["summary"]["invalid_fields"] += 1
                result["errors"][field_name] = field_result["errors"]
                result["valid"] = False
        
        return result


class DataProcessor:
    """Processes data according to specified steps."""
    
    def __init__(self):
        self.processors = {
            "clean_whitespace": self._clean_whitespace,
            "normalize_case": self._normalize_case,
            "remove_duplicates": self._remove_duplicates,
            "sort_data": self._sort_data,
            "filter_data": self._filter_data,
            "transform_format": self._transform_format,
            "aggregate_data": self._aggregate_data
        }
    
    async def process_data(self, data: Any, steps: List[Dict[str, Any]]) -> Any:
        """Process data through a series of steps."""
        result = data
        
        for step in steps:
            step_name = step.get("name")
            step_params = step.get("parameters", {})
            
            if step_name in self.processors:
                try:
                    result = await self.processors[step_name](result, step_params)
                except Exception as e:
                    raise Exception(f"Error in step '{step_name}': {e}")
            else:
                raise Exception(f"Unknown processing step: {step_name}")
        
        return result
    
    async def _clean_whitespace(self, data: Any, params: Dict[str, Any]) -> Any:
        """Clean whitespace from string data."""
        if isinstance(data, str):
            return data.strip()
        elif isinstance(data, list):
            return [item.strip() if isinstance(item, str) else item for item in data]
        elif isinstance(data, dict):
            return {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}
        return data
    
    async def _normalize_case(self, data: Any, params: Dict[str, Any]) -> Any:
        """Normalize case of string data."""
        case_type = params.get("case", "lower")
        
        if isinstance(data, str):
            if case_type == "lower":
                return data.lower()
            elif case_type == "upper":
                return data.upper()
            elif case_type == "title":
                return data.title()
        elif isinstance(data, list):
            return [self._normalize_case(item, params) for item in data]
        elif isinstance(data, dict):
            return {k: self._normalize_case(v, params) for k, v in data.items()}
        
        return data
    
    async def _remove_duplicates(self, data: Any, params: Dict[str, Any]) -> Any:
        """Remove duplicate items from data."""
        if isinstance(data, list):
            return list(dict.fromkeys(data))  # Preserves order
        return data
    
    async def _sort_data(self, data: Any, params: Dict[str, Any]) -> Any:
        """Sort data."""
        if isinstance(data, list):
            reverse = params.get("reverse", False)
            key = params.get("key")
            
            if key and isinstance(data[0], dict):
                return sorted(data, key=lambda x: x.get(key), reverse=reverse)
            else:
                return sorted(data, reverse=reverse)
        return data
    
    async def _filter_data(self, data: Any, params: Dict[str, Any]) -> Any:
        """Filter data based on conditions."""
        if isinstance(data, list):
            condition = params.get("condition")
            if condition:
                return [item for item in data if self._evaluate_condition(item, condition)]
        return data
    
    async def _transform_format(self, data: Any, params: Dict[str, Any]) -> Any:
        """Transform data format."""
        target_format = params.get("format")
        
        if target_format == "json" and not isinstance(data, str):
            return json.dumps(data)
        elif target_format == "dict" and isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data
        
        return data
    
    async def _aggregate_data(self, data: Any, params: Dict[str, Any]) -> Any:
        """Aggregate data."""
        if isinstance(data, list) and data:
            operation = params.get("operation", "sum")
            
            if operation == "sum":
                return sum(data)
            elif operation == "average":
                return sum(data) / len(data)
            elif operation == "count":
                return len(data)
            elif operation == "min":
                return min(data)
            elif operation == "max":
                return max(data)
        
        return data
    
    def _evaluate_condition(self, item: Any, condition: Dict[str, Any]) -> bool:
        """Evaluate a condition on an item."""
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")
        
        if field and isinstance(item, dict):
            item_value = item.get(field)
        else:
            item_value = item
        
        if operator == "equals":
            return item_value == value
        elif operator == "not_equals":
            return item_value != value
        elif operator == "greater_than":
            return item_value > value
        elif operator == "less_than":
            return item_value < value
        elif operator == "contains":
            return value in str(item_value)
        elif operator == "starts_with":
            return str(item_value).startswith(str(value))
        elif operator == "ends_with":
            return str(item_value).endswith(str(value))
        
        return True


class Agent002(BaseAgent):
    """
    Agent 002 - Data Processing Agent
    
    Responsibilities:
    - Data collection from various sources
    - Data validation and cleaning
    - Data transformation and processing
    - Data quality assurance
    - Data export and delivery
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            identity=AgentIdentity(
                agent_id="agent_002",
                name="Data Processing Agent",
                role="Data Processor",
                capabilities=["data_collection", "data_validation", "data_processing", "data_export"],
                personality_traits=["meticulous", "analytical", "efficient"]
            ),
            config=config or {}
        )
        
        self.logger = get_logger("Agent002")
        self.tasks: Dict[str, DataTask] = {}
        self.validator = DataValidator()
        self.processor = DataProcessor()
        self.empathy_scorer = EmpathyScorer()
        
        # Data processing statistics
        self.stats = {
            "tasks_processed": 0,
            "data_validated": 0,
            "errors_encountered": 0,
            "processing_time_avg": 0.0
        }
    
    async def create_data_task(self, data_type: str, source: str, destination: str,
                             validation_rules: Optional[Dict[str, Any]] = None,
                             processing_steps: Optional[List[Dict[str, Any]]] = None) -> str:
        """Create a new data processing task."""
        task_id = str(uuid.uuid4())
        
        task = DataTask(
            task_id=task_id,
            data_type=data_type,
            source=source,
            destination=destination,
            validation_rules=validation_rules or {},
            processing_steps=processing_steps or []
        )
        
        self.tasks[task_id] = task
        self.logger.info(f"Created data task {task_id}: {data_type} from {source}")
        
        return task_id
    
    async def collect_data(self, source: str, data_type: str) -> Any:
        """Collect data from a source."""
        self.logger.info(f"Collecting {data_type} data from {source}")
        
        # Simulate data collection
        await asyncio.sleep(1)
        
        # Return sample data based on type
        sample_data = {
            "user_data": [
                {"id": 1, "name": "John Doe", "email": "john@example.com", "age": 30},
                {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "age": 25},
                {"id": 3, "name": "Bob Johnson", "email": "bob@example.com", "age": 35}
            ],
            "transaction_data": [
                {"id": "T001", "amount": 100.50, "currency": "USD", "timestamp": "2024-01-01T10:00:00Z"},
                {"id": "T002", "amount": 250.75, "currency": "USD", "timestamp": "2024-01-01T11:00:00Z"},
                {"id": "T003", "amount": 75.25, "currency": "USD", "timestamp": "2024-01-01T12:00:00Z"}
            ],
            "log_data": [
                {"level": "INFO", "message": "System started", "timestamp": "2024-01-01T09:00:00Z"},
                {"level": "WARNING", "message": "High memory usage", "timestamp": "2024-01-01T09:30:00Z"},
                {"level": "ERROR", "message": "Connection failed", "timestamp": "2024-01-01T10:00:00Z"}
            ]
        }
        
        return sample_data.get(data_type, [])
    
    async def validate_data(self, data: Any, validation_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data according to rules."""
        self.logger.info("Validating data")
        
        if isinstance(data, list) and data:
            # Validate each item in the list
            validation_results = []
            for i, item in enumerate(data):
                result = self.validator.validate_data(item, validation_rules)
                result["index"] = i
                validation_results.append(result)
            
            # Aggregate results
            total_items = len(data)
            valid_items = sum(1 for r in validation_results if r["valid"])
            invalid_items = total_items - valid_items
            
            return {
                "valid": invalid_items == 0,
                "total_items": total_items,
                "valid_items": valid_items,
                "invalid_items": invalid_items,
                "validation_rate": valid_items / total_items if total_items > 0 else 0,
                "item_results": validation_results
            }
        else:
            # Validate single item
            return self.validator.validate_data(data, validation_rules)
    
    async def process_data(self, data: Any, processing_steps: List[Dict[str, Any]]) -> Any:
        """Process data through specified steps."""
        self.logger.info(f"Processing data through {len(processing_steps)} steps")
        
        start_time = datetime.utcnow()
        result = await self.processor.process_data(data, processing_steps)
        end_time = datetime.utcnow()
        
        processing_time = (end_time - start_time).total_seconds()
        self.stats["processing_time_avg"] = (
            (self.stats["processing_time_avg"] * self.stats["tasks_processed"] + processing_time) /
            (self.stats["tasks_processed"] + 1)
        )
        
        return result
    
    async def export_data(self, data: Any, destination: str, format: str = "json") -> bool:
        """Export processed data to destination."""
        self.logger.info(f"Exporting data to {destination} in {format} format")
        
        # Simulate export
        await asyncio.sleep(0.5)
        
        # In a real implementation, this would write to file, database, API, etc.
        return True
    
    async def execute_data_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a complete data processing task."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.tasks[task_id]
        task.status = "processing"
        
        try:
            # Step 1: Collect data
            self.logger.info(f"Starting task {task_id}: Collecting data from {task.source}")
            data = await self.collect_data(task.source, task.data_type)
            
            # Step 2: Validate data
            if task.validation_rules:
                self.logger.info(f"Validating data for task {task_id}")
                validation_result = await self.validate_data(data, task.validation_rules)
                
                if not validation_result["valid"]:
                    task.status = "failed"
                    task.result = {"error": "Data validation failed", "details": validation_result}
                    self.stats["errors_encountered"] += 1
                    return task.result
            
            # Step 3: Process data
            if task.processing_steps:
                self.logger.info(f"Processing data for task {task_id}")
                data = await self.process_data(data, task.processing_steps)
            
            # Step 4: Export data
            self.logger.info(f"Exporting data for task {task_id}")
            export_success = await self.export_data(data, task.destination)
            
            if not export_success:
                task.status = "failed"
                task.result = {"error": "Data export failed"}
                self.stats["errors_encountered"] += 1
                return task.result
            
            # Task completed successfully
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            task.result = {
                "status": "success",
                "data_size": len(data) if isinstance(data, list) else 1,
                "processing_time": (task.completed_at - task.created_at).total_seconds()
            }
            
            self.stats["tasks_processed"] += 1
            self.logger.info(f"Task {task_id} completed successfully")
            
            return task.result
            
        except Exception as e:
            task.status = "failed"
            task.result = {"error": str(e)}
            self.stats["errors_encountered"] += 1
            self.logger.error(f"Task {task_id} failed: {e}")
            return task.result
    
    async def get_processing_statistics(self) -> Dict[str, Any]:
        """Get data processing statistics."""
        return {
            "agent_id": self.identity.agent_id,
            "agent_name": self.identity.name,
            "stats": self.stats,
            "active_tasks": sum(1 for task in self.tasks.values() if task.status == "processing"),
            "completed_tasks": sum(1 for task in self.tasks.values() if task.status == "completed"),
            "failed_tasks": sum(1 for task in self.tasks.values() if task.status == "failed"),
            "total_tasks": len(self.tasks),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def run(self):
        """Main run loop for the data processing agent."""
        self.logger.info("Starting Agent 002 - Data Processing Agent")
        
        while self.is_running:
            try:
                # Process pending tasks
                pending_tasks = [task for task in self.tasks.values() if task.status == "pending"]
                
                for task in pending_tasks:
                    await self.execute_data_task(task.task_id)
                
                # Generate statistics periodically
                if self._should_generate_stats():
                    stats = await self.get_processing_statistics()
                    self.logger.info(f"Processing statistics: {stats['stats']}")
                
                # Sleep before next iteration
                await asyncio.sleep(3)
                
            except Exception as e:
                self.logger.error(f"Error in data processing loop: {e}")
                await asyncio.sleep(5)
    
    def _should_generate_stats(self) -> bool:
        """Determine if it's time to generate statistics."""
        current_time = datetime.utcnow()
        if not hasattr(self, '_last_stats_time'):
            self._last_stats_time = current_time
            return True
        
        time_diff = (current_time - self._last_stats_time).total_seconds()
        if time_diff >= 60:  # Generate stats every minute
            self._last_stats_time = current_time
            return True
        
        return False 