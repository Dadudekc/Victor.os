import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ValidationStatus(Enum):
    PASS = "pass"
    WARNING = "warning"
    ERROR = "error"

class ValidationResult:
    def __init__(self, status: ValidationStatus, message: str, details: Optional[Dict[str, Any]] = None):
        self.status = status
        self.message = message
        self.details = details or {}

class StateValidator:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.config_path = workspace_root / "src/dreamos/config/autonomous_loop_config.yaml"
        self.load_config()

    def load_config(self) -> None:
        """Load validation configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading validation config: {e}")
            self.config = {}

    async def validate_current_state(self) -> ValidationResult:
        """Validate the current state of the autonomous loop."""
        try:
            # 1. Check file permissions
            permission_result = self._check_permissions()
            if permission_result.status != ValidationStatus.PASS:
                return permission_result

            # 2. Validate schema
            schema_result = self._validate_schema()
            if schema_result.status != ValidationStatus.PASS:
                return schema_result

            # 3. Check dependencies
            dependency_result = self._check_dependencies()
            if dependency_result.status != ValidationStatus.PASS:
                return dependency_result

            return ValidationResult(
                ValidationStatus.PASS,
                "All validation checks passed"
            )

        except Exception as e:
            logger.error(f"Error during state validation: {e}")
            return ValidationResult(
                ValidationStatus.ERROR,
                f"Validation failed: {str(e)}"
            )

    def _check_permissions(self) -> ValidationResult:
        """Check file permissions for required paths."""
        required_paths = [
            self.workspace_root / "runtime/agent_mailboxes",
            self.workspace_root / "runtime/tasks/working_tasks.json",
            self.workspace_root / "episodes/episode-launch-final-lock.yaml"
        ]

        for path in required_paths:
            if not path.exists():
                return ValidationResult(
                    ValidationStatus.ERROR,
                    f"Required path does not exist: {path}"
                )
            if not os.access(path, os.R_OK):
                return ValidationResult(
                    ValidationStatus.ERROR,
                    f"No read permission for: {path}"
                )
            if not os.access(path, os.W_OK):
                return ValidationResult(
                    ValidationStatus.ERROR,
                    f"No write permission for: {path}"
                )

        return ValidationResult(
            ValidationStatus.PASS,
            "All permission checks passed"
        )

    def _validate_schema(self) -> ValidationResult:
        """Validate schema of working tasks and episode files."""
        try:
            # Validate working tasks
            working_tasks_path = self.workspace_root / "runtime/tasks/working_tasks.json"
            with open(working_tasks_path, 'r') as f:
                tasks = json.load(f)
                if not isinstance(tasks, list):
                    return ValidationResult(
                        ValidationStatus.ERROR,
                        "working_tasks.json must contain a list"
                    )

            # Validate episode file
            episode_path = self.workspace_root / "episodes/episode-launch-final-lock.yaml"
            with open(episode_path, 'r') as f:
                episode = yaml.safe_load(f)
                if not isinstance(episode, dict) or 'tasks' not in episode:
                    return ValidationResult(
                        ValidationStatus.ERROR,
                        "episode file must contain a 'tasks' key"
                    )

            return ValidationResult(
                ValidationStatus.PASS,
                "Schema validation passed"
            )

        except Exception as e:
            return ValidationResult(
                ValidationStatus.ERROR,
                f"Schema validation failed: {str(e)}"
            )

    def _check_dependencies(self) -> ValidationResult:
        """Check for required dependencies and their versions."""
        try:
            # Add your dependency checks here
            # For example, check if required Python packages are installed
            # or if required system services are running

            return ValidationResult(
                ValidationStatus.PASS,
                "Dependency checks passed"
            )

        except Exception as e:
            return ValidationResult(
                ValidationStatus.ERROR,
                f"Dependency check failed: {str(e)}"
            )

    def validate_task(self, task: Dict[str, Any]) -> ValidationResult:
        """Validate a single task's structure and data."""
        required_fields = ['id', 'description', 'priority', 'status']
        missing_fields = [field for field in required_fields if field not in task]

        if missing_fields:
            return ValidationResult(
                ValidationStatus.ERROR,
                f"Task missing required fields: {', '.join(missing_fields)}"
            )

        if task['status'] not in ['PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED']:
            return ValidationResult(
                ValidationStatus.ERROR,
                f"Invalid task status: {task['status']}"
            )

        if task['priority'] not in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            return ValidationResult(
                ValidationStatus.ERROR,
                f"Invalid task priority: {task['priority']}"
            )

        return ValidationResult(
            ValidationStatus.PASS,
            "Task validation passed"
        )

    def validate_message(self, message: Dict[str, Any]) -> ValidationResult:
        """Validate a message's structure and data."""
        required_fields = ['id', 'type', 'content', 'timestamp']
        missing_fields = [field for field in required_fields if field not in message]

        if missing_fields:
            return ValidationResult(
                ValidationStatus.ERROR,
                f"Message missing required fields: {', '.join(missing_fields)}"
            )

        return ValidationResult(
            ValidationStatus.PASS,
            "Message validation passed"
        ) 