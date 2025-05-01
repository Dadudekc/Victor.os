import json
import logging
import os

logger = logging.getLogger(__name__)


class TaskStatus:
    PENDING = "PENDING"
    INVALID = "INVALID"
    DISPATCHED = "DISPATCHED"
    DISPATCH_FAILED = "DISPATCH_FAILED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


AGENT_NAME = "TaskExecutorAgent"


class TaskExecutorAgent:
    def __init__(self, agent_bus, task_status_updater, task_list_path, task_list_lock):
        self.agent_name = AGENT_NAME
        self.bus = agent_bus
        self.status_updater = task_status_updater
        self.task_list_path = task_list_path
        self.task_list_lock = task_list_lock

        # Register agent and response handler
        self.bus.register_agent(
            AGENT_NAME, capabilities=["task_execution", "task_dispatch"]
        )
        self.bus.register_handler(AGENT_NAME, self.handle_response)

        # Ensure the task list file exists
        if not os.path.exists(self.task_list_path):
            with open(self.task_list_path, "w") as f:
                f.write("[]")

    def _load_tasks(self):
        tasks = []  # Default empty list
        try:
            with self.task_list_lock:
                with open(self.task_list_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    tasks = json.loads(content) if content.strip() else []
        except Exception as e:
            logger.warning(f"{self.agent_name} failed to load tasks: {e}")
        return tasks

    def _check_dependencies(self, task, tasks_map):
        depends = task.get("depends_on", [])
        task_id = task.get("task_id")
        for dep in depends:
            if dep not in tasks_map:
                logger.warning(
                    f"Task '{task_id}' has unmet dependency: Task '{dep}' not found"
                )
                return False
            if tasks_map[dep].get("status") != TaskStatus.COMPLETED:
                return False
        return True

    def handle_response(self, message):
        task_id = getattr(message, "task_id", None)
        if not task_id:
            logger.warning(f"{self.agent_name} received response without a task_id")
            return

        status = getattr(message, "status", None)
        if status == "SUCCESS":
            normalized = TaskStatus.COMPLETED
        elif status == "FAILED":
            normalized = TaskStatus.FAILED
        elif status == "EXECUTION_ERROR":
            normalized = TaskStatus.ERROR
        else:
            logger.warning(
                f"{self.agent_name} received response with unhandled status '{status}'"
            )
            return

        payload = getattr(message, "payload", {}) or {}
        result_summary = None
        error_details = None

        if normalized == TaskStatus.COMPLETED:
            result_summary = payload.get("summary")
        elif normalized == TaskStatus.FAILED:
            error_details = payload.get("error_details")
        elif normalized == TaskStatus.ERROR:
            error_details = payload.get("error")

        self.status_updater.update_task_status(
            task_id=task_id,
            status=normalized,
            result_summary=result_summary,
            error_details=error_details,
            originating_agent=getattr(message, "sender", None),
        )

    def run_cycle(self):
        tasks = self._load_tasks()
        tasks_map = {t.get("task_id"): t for t in tasks if t.get("task_id")}

        for task in tasks:
            task_id = task.get("task_id")
            status = task.get("status")
            if status == TaskStatus.COMPLETED:
                continue
            if status != TaskStatus.PENDING:
                continue
            if not self._check_dependencies(task, tasks_map):
                continue

            action = task.get("action")
            if not action:
                continue

            recipient = "CursorControlAgent"
            payload = {"action": action, "params": task.get("params", {})}

            self.bus.send_message(
                sender=AGENT_NAME,
                recipient=recipient,
                message_type=action,
                payload=payload,
                task_id=task_id,
            )

            self.status_updater.update_task_status(
                task_id=task_id, status=TaskStatus.DISPATCHED
            )
            break
