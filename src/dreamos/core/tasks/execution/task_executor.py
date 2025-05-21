"""
Enhanced Task Executor with product output support.

This module provides a robust task execution system with:
- Product output validation and packaging
- Quality metrics tracking
- User feedback collection
- Enhanced error reporting
"""

import os
import json
import logging
import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import jsonschema

from dreamos.utils.resilient_io import read_file, write_file
from dreamos.feedback import FeedbackEngineV2
from dreamos.core.tasks.task_nexus import TaskNexus
from dreamos.core.tasks.schemas.product_output_schema import (
    ProductOutput, ProductOutputMetadata, CodeOutput, DocumentationOutput, DataOutput,
    PRODUCT_OUTPUT_SCHEMA
)

logger = logging.getLogger(__name__)

class TaskExecutionError(Exception):
    """Base exception for task execution errors."""
    pass

class ProductOutputError(TaskExecutionError):
    """Exception for product output validation errors."""
    pass

class TaskExecutor:
    """Enhanced task executor with product output support."""
    
    def __init__(self, task_nexus: TaskNexus, feedback_engine: Optional[FeedbackEngineV2] = None):
        """Initialize the task executor.
        
        Args:
            task_nexus: Task nexus for task management
            feedback_engine: Optional feedback engine for quality tracking
        """
        self.task_nexus = task_nexus
        self.feedback_engine = feedback_engine or FeedbackEngineV2()
        self.execution_history = {}  # Track execution attempts
        self.quality_metrics = {}  # Track quality metrics
        
        # Initialize product output directory
        self.product_output_dir = Path("runtime/product_outputs")
        self.product_output_dir.mkdir(parents=True, exist_ok=True)
        
    async def execute_task(self, task_id: str, agent_id: str) -> bool:
        """Execute a task with proper tracking and error handling."""
        task = self.task_nexus.get_task_by_id(task_id)
        if not task:
            logger.error(f"Task {task_id} not found for execution")
            return False
            
        # Record execution attempt
        if task_id not in self.execution_history:
            self.execution_history[task_id] = []
        
        self.execution_history[task_id].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "attempt_number": len(self.execution_history[task_id]) + 1
        })
        
        try:
            # Update task status to IN_PROGRESS
            self.task_nexus.update_task_status(task_id, "in_progress")
            
            # Execute task logic
            result = await self._execute_task_logic(task)
            
            # Update task status based on result
            if result.get("success", False):
                self.task_nexus.update_task_status(task_id, "completed", result=result)
                return True
            else:
                self._handle_task_failure(task_id, agent_id, result.get("error", "Unknown error"))
                return False
                
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            self._handle_task_failure(task_id, agent_id, str(e))
            return False
    
    def _validate_product_output(self, task_id: str, output: Dict[str, Any]) -> None:
        """Validate a product output against the schema.
        
        Args:
            task_id: ID of the task that generated the output
            output: The product output to validate
            
        Raises:
            ProductOutputError: If validation fails
        """
        try:
            # Validate against JSON schema
            jsonschema.validate(instance=output, schema=PRODUCT_OUTPUT_SCHEMA)
            
            # Additional validation specific to output type
            output_type = output.get("output_type")
            if output_type == "code":
                self._validate_code_output(output)
            elif output_type == "documentation":
                self._validate_documentation_output(output)
            elif output_type == "data":
                self._validate_data_output(output)
            elif output_type == "test_results":
                self._validate_test_results(output)
            else:
                raise ProductOutputError(f"Unknown output type: {output_type}")
                
            # Update validation status
            output["validation_status"] = "valid"
            output["validation_errors"] = []
            
        except jsonschema.exceptions.ValidationError as e:
            output["validation_status"] = "invalid"
            output["validation_errors"] = [str(e)]
            raise ProductOutputError(f"Schema validation failed: {str(e)}")
        except Exception as e:
            output["validation_status"] = "invalid"
            output["validation_errors"] = [str(e)]
            raise ProductOutputError(f"Validation failed: {str(e)}")
    
    def _validate_code_output(self, output: Dict[str, Any]) -> None:
        """Validate a code output.
        
        Args:
            output: The code output to validate
            
        Raises:
            ProductOutputError: If validation fails
        """
        content = output.get("content", {})
        if not content.get("content"):
            raise ProductOutputError("Code output missing content")
        if not content.get("language"):
            raise ProductOutputError("Code output missing language")
    
    def _validate_documentation_output(self, output: Dict[str, Any]) -> None:
        """Validate a documentation output.
        
        Args:
            output: The documentation output to validate
            
        Raises:
            ProductOutputError: If validation fails
        """
        content = output.get("content", {})
        if not content.get("content"):
            raise ProductOutputError("Documentation output missing content")
        if not content.get("format"):
            raise ProductOutputError("Documentation output missing format")
    
    def _validate_data_output(self, output: Dict[str, Any]) -> None:
        """Validate a data output.
        
        Args:
            output: The data output to validate
            
        Raises:
            ProductOutputError: If validation fails
        """
        content = output.get("content", {})
        if not content.get("content"):
            raise ProductOutputError("Data output missing content")
        if not content.get("format"):
            raise ProductOutputError("Data output missing format")
    
    def _validate_test_results(self, output: Dict[str, Any]) -> None:
        """Validate test results output.
        
        Args:
            output: The test results output to validate
            
        Raises:
            ProductOutputError: If validation fails
        """
        content = output.get("content", {})
        if not content.get("content"):
            raise ProductOutputError("Test results output missing content")
        if not isinstance(content.get("content", {}).get("passed"), bool):
            raise ProductOutputError("Test results output missing or invalid passed status")
        if not isinstance(content.get("content", {}).get("test_count"), int):
            raise ProductOutputError("Test results output missing or invalid test count")
        if not isinstance(content.get("content", {}).get("passed_count"), int):
            raise ProductOutputError("Test results output missing or invalid passed count")
    
    def _package_product_output(self, task_id: str, output: Dict[str, Any]) -> None:
        """Package a validated product output.
        
        Args:
            task_id: ID of the task that generated the output
            output: The validated product output to package
        """
        # Create output directory if it doesn't exist
        output_dir = self.product_output_dir / task_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        output_id = output.get("output_id", str(uuid.uuid4()))
        output_type = output.get("output_type")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{output_id}_{output_type}_{timestamp}.json"
        
        # Write output to file
        output_path = output_dir / filename
        write_file(output_path, json.dumps(output, indent=2))
        
        # Create metadata file
        metadata_path = output_dir / f"{output_id}_metadata.json"
        metadata = {
            "output_id": output_id,
            "task_id": task_id,
            "output_type": output_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "file_path": str(output_path),
            "validation_status": output.get("validation_status"),
            "validation_errors": output.get("validation_errors", []),
            "content_type": output.get("content", {}).get("type"),
            "content_format": output.get("content", {}).get("format"),
            "metadata": output.get("content", {}).get("metadata", {})
        }
        write_file(metadata_path, json.dumps(metadata, indent=2))
        
        # Log packaging
        logger.info(f"Packaged product output for task {task_id}: {filename}")
    
    def _track_quality_metrics(self, task_id: str, result: Dict[str, Any]) -> None:
        """Track quality metrics for a task execution.
        
        Args:
            task_id: ID of the task
            result: The task execution result
        """
        if task_id not in self.quality_metrics:
            self.quality_metrics[task_id] = []
            
        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_time": result.get("execution_time", 0),
            "success": result.get("success", False),
            "quality_score": result.get("quality_score", 0.0),
            "error_count": len(result.get("errors", [])),
            "warning_count": len(result.get("warnings", [])),
            "product_output": {
                "type": result.get("product_output", {}).get("output_type"),
                "validation_status": result.get("product_output", {}).get("validation_status"),
                "validation_errors": len(result.get("product_output", {}).get("validation_errors", []))
            } if "product_output" in result else None
        }
        
        self.quality_metrics[task_id].append(metrics)
        
        # Update feedback engine
        if self.feedback_engine:
            self.feedback_engine.ingest_feedback({
                "type": "quality_metrics",
                "task_id": task_id,
                "metrics": metrics,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        # Log metrics
        logger.info(f"Task {task_id} quality metrics: {metrics}")
    
    def _collect_user_feedback(self, task_id: str, feedback: Dict[str, Any]) -> None:
        """Collect user feedback for a task execution.
        
        Args:
            task_id: ID of the task
            feedback: The user feedback to collect
        """
        if self.feedback_engine:
            feedback_data = {
                "type": "user_feedback",
                "task_id": task_id,
                "feedback": feedback,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metrics": {
                    "satisfaction_score": feedback.get("satisfaction_score", 0.0),
                    "usefulness_score": feedback.get("usefulness_score", 0.0),
                    "quality_score": feedback.get("quality_score", 0.0)
                }
            }
            
            self.feedback_engine.ingest_feedback(feedback_data)
            
            # Log feedback
            logger.info(f"Collected user feedback for task {task_id}: {feedback_data}")
            
            # Update quality metrics with feedback
            if task_id in self.quality_metrics:
                self.quality_metrics[task_id][-1]["user_feedback"] = feedback_data
    
    def _handle_task_failure(self, task_id: str, agent_id: str, error_msg: str) -> None:
        """Handle task execution failure.
        
        Args:
            task_id: ID of the failed task
            agent_id: ID of the agent that failed
            error_msg: Error message describing the failure
        """
        # Update task status
        self.task_nexus.update_task_status(task_id, "failed", result={"error": error_msg})
        
        # Record failure in execution history
        if task_id in self.execution_history:
            self.execution_history[task_id][-1]["error"] = error_msg
            self.execution_history[task_id][-1]["status"] = "failed"
        
        # Track failure metrics
        if task_id not in self.quality_metrics:
            self.quality_metrics[task_id] = []
            
        self.quality_metrics[task_id].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": False,
            "error": error_msg,
            "agent_id": agent_id
        })
        
        # Update feedback engine
        if self.feedback_engine:
            self.feedback_engine.ingest_feedback({
                "type": "task_failure",
                "task_id": task_id,
                "agent_id": agent_id,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        # Log failure
        logger.error(f"Task {task_id} failed: {error_msg}")
    
    async def _execute_task_logic(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the core task logic.
        
        Args:
            task: Task to execute
            
        Returns:
            Task execution result
        """
        task_type = task.get("type", "unknown")
        task_payload = task.get("payload", {})
        
        try:
            if task_type == "code_generation":
                result = await self._execute_code_generation(task_payload)
            elif task_type == "documentation":
                result = await self._execute_documentation(task_payload)
            elif task_type == "data_processing":
                result = await self._execute_data_processing(task_payload)
            elif task_type == "testing":
                result = await self._execute_testing(task_payload)
            else:
                raise TaskExecutionError(f"Unknown task type: {task_type}")
                
            # Validate and package the output
            if "product_output" in result:
                self._validate_product_output(task["task_id"], result["product_output"])
                self._package_product_output(task["task_id"], result["product_output"])
                
            # Track quality metrics
            self._track_quality_metrics(task["task_id"], result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing task logic: {e}")
            raise TaskExecutionError(f"Task execution failed: {str(e)}")
            
    async def _execute_code_generation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute code generation task.
        
        Args:
            payload: Task payload containing generation parameters
            
        Returns:
            Task execution result
        """
        # Implement code generation logic
        # For now, return a placeholder result
        return {
            "success": True,
            "execution_time": 1.0,
            "quality_score": 0.95,
            "product_output": {
                "output_id": str(uuid.uuid4()),
                "output_type": "code",
                "content": {
                    "type": "code",
                    "content": "# Generated code",
                    "language": payload.get("language", "python"),
                    "metadata": {
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "version": "1.0.0",
                        "quality_score": 0.95
                    }
                }
            }
        }
        
    async def _execute_documentation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute documentation task.
        
        Args:
            payload: Task payload containing documentation parameters
            
        Returns:
            Task execution result
        """
        # Implement documentation generation logic
        # For now, return a placeholder result
        return {
            "success": True,
            "execution_time": 1.0,
            "quality_score": 0.95,
            "product_output": {
                "output_id": str(uuid.uuid4()),
                "output_type": "documentation",
                "content": {
                    "type": "documentation",
                    "content": "# Documentation",
                    "format": payload.get("format", "markdown"),
                    "metadata": {
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "version": "1.0.0",
                        "quality_score": 0.95
                    }
                }
            }
        }
        
    async def _execute_data_processing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data processing task.
        
        Args:
            payload: Task payload containing data processing parameters
            
        Returns:
            Task execution result
        """
        # Implement data processing logic
        # For now, return a placeholder result
        return {
            "success": True,
            "execution_time": 1.0,
            "quality_score": 0.95,
            "product_output": {
                "output_id": str(uuid.uuid4()),
                "output_type": "data",
                "content": {
                    "type": "data",
                    "content": {},
                    "format": payload.get("format", "json"),
                    "metadata": {
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "version": "1.0.0",
                        "quality_score": 0.95
                    }
                }
            }
        }
        
    async def _execute_testing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute testing task.
        
        Args:
            payload: Task payload containing testing parameters
            
        Returns:
            Task execution result
        """
        # Implement testing logic
        # For now, return a placeholder result
        return {
            "success": True,
            "execution_time": 1.0,
            "quality_score": 0.95,
            "product_output": {
                "output_id": str(uuid.uuid4()),
                "output_type": "test_results",
                "content": {
                    "type": "test_results",
                    "content": {
                        "passed": True,
                        "test_count": 1,
                        "passed_count": 1
                    },
                    "format": "json",
                    "metadata": {
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "version": "1.0.0",
                        "quality_score": 0.95
                    }
                }
            }
        } 