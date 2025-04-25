import os
import sys
import json
import logging
import threading
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# --- Path Setup --- 
# Add project root to sys.path to allow importing dreamforge modules
script_dir = os.path.dirname(__file__) # dreamforge/agents
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Up two levels
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# -----------------

try:
    from dreamforge.core.governance_memory_engine import log_event
    # from dreamforge.core.coordination.agent_bus import AgentBus # OLD IMPORT
    from core.coordination.agent_bus import AgentBus # CANONICAL IMPORT
    from core.coordination.dispatcher import Event, EventType
    from dreamforge.core.prompt_staging_service import PromptStagingService
    from dreamforge.core.feedback_engine import FeedbackEngine
    # Import other necessary agents or services as needed
except ImportError as e:
    print(f"Error importing core components in WorkflowAgent: {e}")
    # Decide how to handle critical import errors, maybe raise or log heavily
    log_event = None # Fallback or indicator
    AgentBus = None

# --- Agent Class --- 

class WorkflowAgent:
    """
    Orchestrates the execution of tasks defined in a plan. 
    Receives plan details from PlannerAgent, routes tasks to specialist agents,
    and manages workflow progress with integrated feedback loops.
    
    Core Responsibilities:
    - Task planning and dependency management
    - Agent assignment and load balancing
    - Status tracking and progress monitoring
    - Feedback collection and routing
    """
    def __init__(self, agent_bus: AgentBus):
        self.agent_id = "WorkflowAgent"
        self.current_workflow = None # Stores the plan/tasks being executed
        self.task_status = {} # Tracks status of individual tasks {task_id: status}
        self.agent_bus = agent_bus
        self.feedback_engine = FeedbackEngine()
        self.prompt_staging = PromptStagingService()
        self.agent_capabilities = {}  # Maps agent_id to list of capabilities
        self.agent_load = {}  # Tracks current task load per agent
        
        if not agent_bus and AgentBus:
            error_msg = f"[{self.agent_id}] AgentBus was not provided or failed to import."
            logging.error(error_msg)
            raise ValueError(error_msg)
            
        log_event("AGENT_INIT", self.agent_id, {"message": "WorkflowAgent initialized."})

    def plan_task(self, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Plans execution strategy for a task based on its requirements and current system state.
        
        Args:
            task_spec: Task specification including requirements, priority, and constraints
            
        Returns:
            Dict containing planned execution details including:
            - assigned_agent: Selected agent ID
            - estimated_duration: Expected completion time
            - resource_requirements: Required system resources
            - fallback_agents: List of backup agents if primary fails
        """
        log_event("TASK_PLANNING_START", self.agent_id, {"task_id": task_spec.get("task_id")})
        
        try:
            # Analyze task requirements
            required_capabilities = task_spec.get("required_capabilities", [])
            priority = task_spec.get("priority", "medium")
            
            # Find suitable agents
            capable_agents = self._find_capable_agents(required_capabilities)
            if not capable_agents:
                raise ValueError(f"No agents found with required capabilities: {required_capabilities}")
            
            # Select optimal agent based on current load and capabilities
            primary_agent = self._select_optimal_agent(capable_agents)
            fallback_agents = [agent for agent in capable_agents if agent != primary_agent][:2]
            
            # Estimate task duration based on historical data
            estimated_duration = self._estimate_task_duration(task_spec, primary_agent)
            
            planned_execution = {
                "task_id": task_spec["task_id"],
                "assigned_agent": primary_agent,
                "fallback_agents": fallback_agents,
                "estimated_duration": estimated_duration,
                "priority": priority,
                "resource_requirements": self._calculate_resource_requirements(task_spec)
            }
            
            log_event("TASK_PLANNING_SUCCESS", self.agent_id, {
                "task_id": task_spec["task_id"],
                "planned_execution": planned_execution
            })
            
            return planned_execution
            
        except Exception as e:
            log_event("TASK_PLANNING_ERROR", self.agent_id, {
                "task_id": task_spec.get("task_id"),
                "error": str(e)
            })
            raise

    def assign_agent(self, task_id: str, planned_execution: Dict[str, Any]) -> bool:
        """
        Assigns a task to an agent based on the planned execution strategy.
        
        Args:
            task_id: Unique identifier for the task
            planned_execution: Output from plan_task() containing assignment details
            
        Returns:
            bool: True if assignment was successful, False otherwise
        """
        log_event("AGENT_ASSIGNMENT_START", self.agent_id, {
            "task_id": task_id,
            "planned_execution": planned_execution
        })
        
        try:
            agent_id = planned_execution["assigned_agent"]
            
            # Prepare task message
            task_message = {
                "type": "EXECUTE_TASK",
                "task_id": task_id,
                "execution_plan": planned_execution,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Update agent load tracking
            self.agent_load[agent_id] = self.agent_load.get(agent_id, 0) + 1
            
            # Send task to agent via AgentBus
            if self.agent_bus.send_message(self.agent_id, agent_id, task_message):
                log_event("AGENT_ASSIGNMENT_SUCCESS", self.agent_id, {
                    "task_id": task_id,
                    "assigned_agent": agent_id
                })
                return True
                
            # If primary agent fails, try fallbacks
            for fallback_agent in planned_execution.get("fallback_agents", []):
                if self.agent_bus.send_message(self.agent_id, fallback_agent, task_message):
                    log_event("AGENT_ASSIGNMENT_FALLBACK_SUCCESS", self.agent_id, {
                        "task_id": task_id,
                        "original_agent": agent_id,
                        "fallback_agent": fallback_agent
                    })
                    self.agent_load[fallback_agent] = self.agent_load.get(fallback_agent, 0) + 1
                    self.agent_load[agent_id] = max(0, self.agent_load.get(agent_id, 1) - 1)
                    return True
                    
            raise RuntimeError(f"Failed to assign task {task_id} to any available agent")
            
        except Exception as e:
            log_event("AGENT_ASSIGNMENT_ERROR", self.agent_id, {
                "task_id": task_id,
                "error": str(e)
            })
            return False

    def check_status(self, task_id: str) -> Tuple[str, Dict[str, Any]]:
        """
        Checks the current status of a task and gathers execution metrics.
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            Tuple containing:
            - Current status string
            - Dict of execution metrics and details
        """
        if task_id not in self.task_status:
            log_event("STATUS_CHECK_ERROR", self.agent_id, {
                "task_id": task_id,
                "error": "Unknown task ID"
            })
            return "unknown", {}
            
        current_status = self.task_status[task_id]
        
        # Gather execution metrics
        metrics = {
            "status": current_status,
            "last_update": datetime.utcnow().isoformat(),
            "duration": self._calculate_task_duration(task_id),
            "assigned_agent": self._get_assigned_agent(task_id),
            "dependencies_met": self._check_dependencies_met(task_id),
            "error_count": self._get_error_count(task_id)
        }
        
        log_event("STATUS_CHECK", self.agent_id, {
            "task_id": task_id,
            "metrics": metrics
        })
        
        return current_status, metrics

    def route_feedback(self, task_id: str, feedback_data: Dict[str, Any]) -> bool:
        """
        Routes execution feedback to appropriate handlers and updates task state.
        
        Args:
            task_id: Task identifier
            feedback_data: Execution feedback including:
                - success: bool
                - output: Any task output
                - errors: List of error details
                - metrics: Performance metrics
                
        Returns:
            bool: True if feedback was successfully processed
        """
        log_event("FEEDBACK_ROUTING_START", self.agent_id, {
            "task_id": task_id,
            "feedback_type": feedback_data.get("type")
        })
        
        try:
            # Send to FeedbackEngine for processing
            self.feedback_engine.process_feedback(
                task_id=task_id,
                agent_id=self.agent_id,
                feedback_data=feedback_data
            )
            
            # Update task status based on feedback
            if feedback_data.get("success"):
                self.update_task_status(
                    task_id=task_id,
                    status="completed",
                    reporting_agent=feedback_data.get("agent_id"),
                    details=feedback_data
                )
            else:
                # Handle failure cases
                error_details = feedback_data.get("errors", [])
                if self._should_retry(task_id, error_details):
                    self._retry_task(task_id)
                else:
                    self.update_task_status(
                        task_id=task_id,
                        status="failed",
                        reporting_agent=feedback_data.get("agent_id"),
                        details={"errors": error_details}
                    )
            
            # Generate any necessary prompt updates
            if feedback_data.get("requires_prompt_update"):
                self.prompt_staging.update_prompt(
                    task_id=task_id,
                    feedback=feedback_data
                )
            
            log_event("FEEDBACK_ROUTING_SUCCESS", self.agent_id, {
                "task_id": task_id,
                "processed_feedback": feedback_data.get("type")
            })
            
            return True
            
        except Exception as e:
            log_event("FEEDBACK_ROUTING_ERROR", self.agent_id, {
                "task_id": task_id,
                "error": str(e)
            })
            return False

    def receive_message(self, sender_id: str, message: dict):
        """Handles incoming messages from the AgentBus."""
        message_type = message.get("type")
        log_event("MESSAGE_RECEIVED", self.agent_id, {"sender": sender_id, "type": message_type})

        if message_type == "EXECUTE_PLAN" and sender_id == "PlannerAgent": # Or wherever plans come from
            plan = message.get("plan")
            if plan:
                self.start_workflow(plan)
            else:
                log_event("AGENT_ERROR", self.agent_id, {"error": "Received EXECUTE_PLAN without a 'plan' payload.", "sender": sender_id})
        elif message_type == "TASK_UPDATE":
            # Handle status updates from other agents executing tasks
            task_id = message.get("task_id")
            status = message.get("status")
            details = message.get("details", {})
            if task_id and status:
                self.update_task_status(task_id, status, sender_id, details)
            else:
                log_event("AGENT_WARNING", self.agent_id, {"warning": "Received incomplete TASK_UPDATE.", "sender": sender_id, "payload": message})
        else:
            log_event("AGENT_INFO", self.agent_id, {"info": f"Received unhandled message type '{message_type}' from {sender_id}."})

    def start_workflow(self, plan: list):
        """Initiates the execution of a given plan (list of tasks)."""
        log_event("WORKFLOW_START", self.agent_id, {"task_count": len(plan)})
        self.current_workflow = plan
        self.task_status = {task.get("task_id"): "pending" for task in plan if task.get("task_id")}
        
        # Basic initial step: Send the first task(s) with no dependencies
        self._execute_next_tasks()

    def update_task_status(self, task_id: str, status: str, reporting_agent: str, details: dict):
        """Updates the status of a task and potentially triggers next steps."""
        if task_id not in self.task_status:
            log_event("AGENT_WARNING", self.agent_id, {"warning": f"Received status update for unknown task_id '{task_id}'.", "reporter": reporting_agent})
            return

        log_event("TASK_STATUS_UPDATE", self.agent_id, {"task_id": task_id, "old_status": self.task_status[task_id], "new_status": status, "reporter": reporting_agent, "details": details})
        self.task_status[task_id] = status

        if status in ["completed", "failed", "skipped"]:
            # Check if other tasks can now be started
            self._execute_next_tasks()

        # Check if workflow is complete
        self._check_workflow_completion()

    def _execute_next_tasks(self):
        """Identifies and dispatches tasks whose dependencies are met."""
        if not self.current_workflow:
            return # No active workflow

        all_completed_ids = {tid for tid, status in self.task_status.items() if status == "completed"}
        
        for task in self.current_workflow:
            task_id = task.get("task_id")
            current_status = self.task_status.get(task_id)

            if current_status == "pending":
                dependencies = set(task.get("dependencies", []))
                if dependencies.issubset(all_completed_ids):
                    # Dependencies met, dispatch this task
                    assigned_agent = task.get("assigned_to") # Needs mapping to actual agent ID
                    if assigned_agent: # Placeholder: Actual agent mapping needed
                        log_event("TASK_DISPATCH", self.agent_id, {"task_id": task_id, "target_agent": assigned_agent})
                        self.task_status[task_id] = "in_progress" 
                        # Placeholder: Define actual message format for task execution
                        message = {
                            "type": "EXECUTE_TASK",
                            "task_details": task
                        }
                        # !!! Need a mapping from assignee (e.g., 'Calendar') to Agent ID ('CalendarAgent') !!!
                        # Using task['assigned_to'] + "Agent" as a naive placeholder
                        target_agent_id = assigned_agent + "Agent" 
                        if not self.agent_bus.send_message(self.agent_id, target_agent_id, message):
                            log_event("AGENT_ERROR", self.agent_id, {"error": f"Failed to send task {task_id} to {target_agent_id}."})
                            self.task_status[task_id] = "failed" # Mark as failed if dispatch fails
                            self._check_workflow_completion() # Re-check completion status
                    else:
                        log_event("AGENT_ERROR", self.agent_id, {"error": f"Task {task_id} has no 'assigned_to' field.", "task": task})
                        self.task_status[task_id] = "failed"
                        self._check_workflow_completion()


    def _check_workflow_completion(self):
        """Checks if all tasks in the current workflow are completed or failed."""
        if not self.current_workflow:
            return False

        all_tasks_accounted_for = True
        for task_id, status in self.task_status.items():
            if status in ["pending", "in_progress"]:
                all_tasks_accounted_for = False
                break
        
        if all_tasks_accounted_for:
            final_status = "completed" if all(s == "completed" for s in self.task_status.values()) else "failed"
            log_event(f"WORKFLOW_{final_status.upper()}", self.agent_id, {"workflow_tasks": self.task_status})
            # Notify original requester? (e.g., PlannerAgent or Main)
            # Example: self.agent_bus.send_message(self.agent_id, "OriginatorAgent", {"type": "WORKFLOW_RESULT", "status": final_status, "results": self.task_status})
            self.current_workflow = None # Clear workflow
            self.task_status = {}
            return True
            
        return False

    # Helper methods
    def _find_capable_agents(self, required_capabilities: List[str]) -> List[str]:
        """Finds agents that have all required capabilities."""
        capable_agents = []
        for agent_id, capabilities in self.agent_capabilities.items():
            if all(cap in capabilities for cap in required_capabilities):
                capable_agents.append(agent_id)
        return capable_agents

    def _select_optimal_agent(self, capable_agents: List[str]) -> str:
        """Selects the agent with lowest current load from capable agents."""
        return min(capable_agents, key=lambda x: self.agent_load.get(x, 0))

    def _estimate_task_duration(self, task_spec: Dict[str, Any], agent_id: str) -> float:
        """Estimates task duration based on historical data and complexity."""
        # Placeholder for actual implementation
        return 60.0  # Default 60 second estimate

    def _calculate_resource_requirements(self, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates required system resources for task execution."""
        # Placeholder for actual implementation
        return {
            "memory": "256MB",
            "cpu_cores": 1,
            "disk_space": "100MB"
        }

    def _should_retry(self, task_id: str, error_details: List[Dict[str, Any]]) -> bool:
        """Determines if a failed task should be retried."""
        # Placeholder logic - implement actual retry policy
        return len(error_details) < 3

    def _retry_task(self, task_id: str):
        """Initiates task retry with updated execution plan."""
        # Implementation would go here
        pass

# Example usage (if run directly, for testing)
if __name__ == '__main__':
    # This basic test requires AgentBus to be importable and Governance/Logging
    if AgentBus and log_event:
        print("Running basic WorkflowAgent test...")
        bus = AgentBus() 
        workflow_agent = WorkflowAgent(bus)
        
        # Need mock agents to register and receive tasks
        class MockExecutorAgent:
            def __init__(self, id, bus):
                self.id = id
                self.bus = bus
            def receive_message(self, sender_id, message):
                if message.get("type") == "EXECUTE_TASK":
                    task = message["task_details"]
                    print(f"  [{self.id}] Received task: {task['task_id']}")
                    # Simulate completion
                    completion_msg = {
                        "type": "TASK_UPDATE", 
                        "task_id": task['task_id'], 
                        "status": "completed",
                        "details": {"result": "Mock execution success"}
                    }
                    self.bus.send_message(self.id, sender_id, completion_msg)

        # Register mock agents
        mock_planner = MockExecutorAgent("PlannerAgent", bus) # Treat planner as an executor for simplicity here
        mock_calendar = MockExecutorAgent("CalendarAgent", bus)
        bus.register_agent(workflow_agent.agent_id, workflow_agent)
        bus.register_agent(mock_planner.id, mock_planner)
        bus.register_agent(mock_calendar.id, mock_calendar)

        print("Registered Agents:", bus.list_agents())

        # Example Plan
        test_plan = [
            {"task_id": "P1", "description": "Plan step 1", "dependencies": [], "assigned_to": "Planner"},
            {"task_id": "C1", "description": "Calendar step 1", "dependencies": ["P1"], "assigned_to": "Calendar"},
            {"task_id": "P2", "description": "Plan step 2", "dependencies": ["P1"], "assigned_to": "Planner"},
        ]

        # Send plan to workflow agent (simulate PlannerAgent sending)
        start_message = {"type": "EXECUTE_PLAN", "plan": test_plan}
        bus.send_message("PlannerAgent", workflow_agent.agent_id, start_message)
        
        # In a real system, this would run asynchronously. Here, messages are processed immediately.
        print("Workflow test finished.")
    else:
        print("Skipping WorkflowAgent test due to import errors.") 

AGENT_NAME = "TaskOrchestratorAgent"
DEFAULT_TASK_LIST_PATH = "task_list.json"
TASK_EXECUTOR_AGENT_ID = "TaskExecutorAgent"

class TaskOrchestratorAgent:
    """Monitors task_list.json and dispatches TASK_QUEUED events for tasks ready to execute."""

    def __init__(self, agent_bus: AgentBus, task_list_path: str = DEFAULT_TASK_LIST_PATH, interval: int = 10):
        """
        Initializes the orchestrator agent.

        Args:
            agent_bus: The central AgentBus instance.
            task_list_path: Path to the task list file.
            interval: Time (in seconds) between orchestration cycles.
        """
        self.agent_name = AGENT_NAME
        self.bus = agent_bus
        self.task_list_path = task_list_path
        self.interval = interval
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.bus.register_agent(self.agent_name, capabilities=["task_orchestration", "workflow_initiation"])
        logger.info(f"{self.agent_name} initialized. Monitoring {self.task_list_path}")

    def _load_tasks(self) -> List[Dict[str, Any]]:
        """Safely loads the task list file."""
        with self._lock:
            try:
                if not os.path.exists(self.task_list_path):
                    logger.warning(f"Task list file {self.task_list_path} does not exist.")
                    # Create an empty file if it doesn't exist
                    try:
                        with open(self.task_list_path, 'w', encoding='utf-8') as f:
                            json.dump([], f)
                        logger.info(f"Created empty task list file: {self.task_list_path}")
                    except IOError as e_create:
                        logger.error(f"Failed to create task list file {self.task_list_path}: {e_create}")
                    return []

                with open(self.task_list_path, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
                    if not isinstance(tasks, list):
                        logger.error(f"Task list file {self.task_list_path} does not contain a valid JSON list. Resetting to empty list.")
                        # Overwrite corrupt file with empty list?
                        # Or handle more gracefully? For now, return empty.
                        # Consider backing up the corrupt file first.
                        return []
                    return tasks
            except json.JSONDecodeError as e_decode:
                logger.error(f"Failed to decode JSON from task list {self.task_list_path}: {e_decode}. Returning empty list.")
                # Consider backing up the corrupt file.
                return []
            except IOError as e_io:
                logger.error(f"IO error loading task list {self.task_list_path}: {e_io}")
                return []
            except Exception as e:
                logger.error(f"Unexpected error loading task list {self.task_list_path}: {e}", exc_info=True)
                return []

    def _save_tasks(self, tasks: List[Dict[str, Any]]) -> bool:
        """Writes updated task list back to file using atomic write pattern."""
        with self._lock:
            temp_path = self.task_list_path + ".tmp"
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(tasks, f, indent=2)
                # Atomic replace operation
                os.replace(temp_path, self.task_list_path)
                return True
            except IOError as e_io:
                logger.error(f"IO error saving task list to {self.task_list_path}: {e_io}")
            except Exception as e:
                logger.error(f"Unexpected error saving task list {self.task_list_path}: {e}", exc_info=True)
            finally:
                # Clean up temp file if it still exists after an error
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError as e_remove:
                        logger.error(f"Failed to remove temporary task list file {temp_path}: {e_remove}")
            return False

    def _check_dependencies(self, task: Dict[str, Any], completed_ids: set) -> bool:
        """Returns True if all task dependencies are met."""
        # Ensure depends_on is a list
        deps = task.get("depends_on", [])
        if not isinstance(deps, list):
            logger.warning(f"Task {task.get('task_id')} has invalid 'depends_on' field (not a list): {deps}. Treating as no dependencies.")
            return True
        return all(dep_id in completed_ids for dep_id in deps)

    def _dispatch_task(self, task: Dict[str, Any]) -> bool:
        """Dispatches a TASK_QUEUED event for the given task."""
        task_id = task.get("task_id")
        action = task.get("action")
        target_agent = task.get("target_agent", TASK_EXECUTOR_AGENT_ID) # Default to executor if not specified

        if not task_id:
            logger.warning("Skipping task dispatch: Task missing 'task_id'. Task data: {task}")
            return False
        if not action:
             logger.warning(f"Skipping task dispatch: Task {task_id} missing 'action'.")
             # Optionally mark as INVALID?
             return False
        # Removed target_agent check, defaulting is acceptable
        # if not target_agent:
        #      logger.warning(f"Skipping task dispatch: Task {task_id} missing 'target_agent'.")
        #      return False

        event_data = {
            "task_id": task_id,
            "action": action,
            "params": task.get("params", {}),
            "target_agent": target_agent,
            "priority": task.get("priority", 0),
            # Add any other necessary fields from the task spec
        }

        event = Event(
            type=EventType.TASK_QUEUED,
            source_id=self.agent_name,
            target_id=TASK_EXECUTOR_AGENT_ID, # Always target the executor for queuing
            data=event_data,
            priority=event_data["priority"]
        )

        try:
            self.bus.dispatch(event)
            logger.info(f"Dispatched {EventType.TASK_QUEUED.name} for task {task_id} (Action: {action}) to {TASK_EXECUTOR_AGENT_ID}")
            return True
        except Exception as e:
            logger.error(f"Failed to dispatch {EventType.TASK_QUEUED.name} event for task {task_id}: {e}", exc_info=True)
            return False

    def run_cycle(self):
        """Scans the task list and dispatches ready tasks."""
        logger.debug(f"{self.agent_name} starting run cycle...")
        tasks = self._load_tasks()
        if not tasks:
            logger.debug("Task list is empty or failed to load.")
            return

        # Determine completed task IDs for dependency checking
        # Consider DISPATCHED as potentially met for simpler logic, or require COMPLETED strictly?
        # Let's require COMPLETED for dependency check.
        completed_ids = {t["task_id"] for t in tasks if isinstance(t, dict) and t.get("status") == "COMPLETED"}
        dispatched_count = 0
        tasks_changed = False

        for task in tasks:
            # Basic validation
            if not isinstance(task, dict) or "task_id" not in task:
                logger.warning(f"Skipping invalid task entry: {task}")
                continue

            task_id = task["task_id"]
            status = task.get("status")

            if status == "PENDING":
                if not self._check_dependencies(task, completed_ids):
                    logger.debug(f"Task {task_id} waiting on dependencies.")
                    continue

                # Attempt to dispatch
                success = self._dispatch_task(task)
                if success:
                    # IMPORTANT: Update status locally immediately after dispatch
                    # to prevent re-dispatching in the same/next cycle.
                    # The final status (COMPLETED/FAILED) will come from TaskStatusUpdater later.
                    task["status"] = "DISPATCHED" # Mark as dispatched in our local list
                    task["last_dispatched_at"] = datetime.now().isoformat() # Optional tracking
                    dispatched_count += 1
                    tasks_changed = True
                    # Add the newly dispatched task to completed_ids if DISPATCHED counts for deps
                    # completed_ids.add(task_id) # Uncomment if DISPATCHED meets dependency needs
                else:
                    # Optional: Mark as DISPATCH_FAILED?
                    # task["status"] = "DISPATCH_FAILED"
                    # tasks_changed = True
                     logger.error(f"Failed to dispatch PENDING task {task_id}, leaving as PENDING for next cycle.")

        # Save the task list *only* if statuses were changed (to DISPATCHED)
        if tasks_changed:
            logger.info(f"Dispatched {dispatched_count} task(s) in this cycle. Saving updated task list.")
            save_success = self._save_tasks(tasks)
            if not save_success:
                 logger.error("Critical: Failed to save task list after updating statuses to DISPATCHED.")
        else:
             logger.debug("No tasks dispatched in this cycle.")

        logger.debug(f"{self.agent_name} run cycle finished.")

    def start(self):
        """Starts the periodic orchestration loop."""
        if self._thread and self._thread.is_alive():
            logger.warning(f"{self.agent_name} already running.")
            return
        logger.info(f"Starting {self.agent_name} with cycle interval {self.interval}s...")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name=f"{self.agent_name}Loop", daemon=True)
        self._thread.start()

    def stop(self):
        """Stops the orchestration loop."""
        if not self._thread or not self._thread.is_alive():
            logger.info(f"{self.agent_name} is not running.")
            return
        logger.info(f"Stopping {self.agent_name}...")
        self._stop_event.set()
        try:
            self._thread.join(timeout=self.interval + 1) # Wait slightly longer than interval
            if self._thread.is_alive():
                logger.warning(f"{self.agent_name} thread did not stop gracefully.")
        except Exception as e:
             logger.error(f"Error joining {self.agent_name} thread: {e}")
        self._thread = None
        logger.info(f"{self.agent_name} stopped.")

    def _run_loop(self):
        """Internal loop that runs the orchestration cycle at regular intervals."""
        logger.info(f"{self.agent_name} run loop started.")
        while not self._stop_event.is_set():
            start_time = time.monotonic()
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"Critical error in {self.agent_name} run_cycle: {e}", exc_info=True)
            
            # Calculate sleep time, ensuring it's not negative if cycle took too long
            elapsed_time = time.monotonic() - start_time
            sleep_time = max(0, self.interval - elapsed_time)
            if self._stop_event.wait(timeout=sleep_time):
                break # Stop event was set during sleep
        logger.info(f"{self.agent_name} run loop stopped.") 