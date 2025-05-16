"""
Agent 2: Infrastructure Surgeon

Responsible for executing infrastructure-related tasks, primarily by interacting
with a GUI (e.g., Cursor) via an event-driven mechanism. It publishes requests
(e.g., CURSOR_INJECT_REQUEST) and awaits corresponding success/failure responses.
Tasks are managed through a ProjectBoardManager.
"""

import asyncio
import logging
import traceback
import uuid
from typing import Any, Dict, Optional, Tuple

from dreamos.core.comms.mailbox_utils import (  # delete_message, # No longer called directly by Agent2, BaseAgent handles it; list_mailbox_messages, # No longer called directly by Agent2; read_message, # No longer called directly by Agent2
    get_agent_mailbox_path,
)

# Import AppConfig
from dreamos.core.config import AppConfig
from dreamos.core.coordination.agent_bus import AgentBus, BaseEvent, EventType

# REMOVED: from dreamos.core.eventing.publishers import publish_cursor_inject_event
# ADDED: Import payload needed for publishing
from dreamos.core.coordination.event_payloads import CursorInjectRequestPayload
from dreamos.core.coordination.message_patterns import (
    TaskMessage,
    TaskStatus,
)

from ..coordination.project_board_manager import (
    ProjectBoardManager,
)

# TaskStatus, # REMOVED - Imported from message_patterns
# --- Core DreamOS Imports ---
# Moved import later to potentially break cycle
from ..core.coordination.base_agent import BaseAgent

# Configure basic logging
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# ) # FIXME: Module-level basicConfig can interfere; configure logging at app entry point.
logger = logging.getLogger("Agent2InfraSurgeon")

AGENT_ID = "Agent-2"
DEFAULT_RESPONSE_TIMEOUT = 60.0  # Timeout in seconds for waiting for cursor response


# --- Agent Class Definition ---
# Moved import here
# from dreamos.core.coordination.base_agent import BaseAgent

from dreamos.core.coordination.utils import (
    with_error_handling,
    with_performance_tracking,
)
from dreamos.core.errors import TaskProcessingError


class Agent2InfraSurgeon(BaseAgent):
    """
    Agent responsible for executing infrastructure-related tasks via GUI automation (Cursor).
    Interacts primarily by publishing CURSOR_INJECT_REQUEST events and listening for
    CURSOR_RETRIEVE_SUCCESS/FAILURE responses.
    """  # noqa: E501

    def __init__(
        self,
        agent_id: str = AGENT_ID,
        config: Optional[AppConfig] = None,
        pbm: Optional[ProjectBoardManager] = None,
        agent_bus: Optional[AgentBus] = None,
    ):
        """Initialize the Agent 2 Infra Surgeon."""
        if not config:
            raise ValueError("AppConfig instance is required for Agent2InfraSurgeon")
        if not pbm:
            raise ValueError(
                "ProjectBoardManager instance is required for Agent2InfraSurgeon"
            )

        # FIXME: Ensure BaseAgent.__init__ correctly handles/expects 'pbm' or uses **kwargs.
        super().__init__(agent_id=agent_id, config=config, pbm=pbm, agent_bus=agent_bus)
        logger.info(f"Agent {self.agent_id} (Infra Surgeon) initializing...")

        # Dictionary to track pending requests: {correlation_id: (asyncio.Event, Optional[Dict])}  # noqa: E501
        # The Optional[Dict] will store the response data when received.
        self._pending_cursor_requests: Dict[
            str, Tuple[asyncio.Event, Optional[Dict]]
        ] = {}

        # Subscribe to response events if agent_bus is available
        if self.agent_bus:
            self.agent_bus.subscribe(
                EventType.CURSOR_RETRIEVE_SUCCESS, self._handle_cursor_response
            )
            self.agent_bus.subscribe(
                EventType.CURSOR_RETRIEVE_FAILURE,
                self._handle_cursor_response,  # Use the same handler for simplicity
            )
            logger.info(
                f"[{self.agent_id}] Subscribed to CURSOR_RETRIEVE_SUCCESS and CURSOR_RETRIEVE_FAILURE events."  # noqa: E501
            )
        else:
            logger.warning(
                f"[{self.agent_id}] AgentBus not provided. Cannot subscribe to cursor response events."  # noqa: E501
            )

        logger.info(f"Agent {self.agent_id} initialized.")

    async def _load_config(self):
        """Load agent-specific configuration if needed."""
        # Example: Load specific coordinates or settings for Agent 2 if required
        # await super()._load_config() # Call parent if it has loading logic
        logger.debug(f"[{self.agent_id}] Loading agent-specific configuration...")
        # Add specific config loading here if needed in the future
        logger.debug(f"[{self.agent_id}] Agent-specific configuration loaded.")

    async def _process_message(self, message: Dict[str, Any]):
        """Process incoming mailbox messages (directives, info, etc.)."""
        # Currently, Agent 2 primarily gets tasks via PBM, but can handle directives
        await super()._process_message(message)  # Leverage base class message handling

    async def _perform_task(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a task by publishing a CURSOR_INJECT_REQUEST and waiting for a response.
        """  # noqa: E501
        task_id = task_details.get("task_id", "UNKNOWN_TASK")
        prompt = task_details.get("prompt")  # Assuming task has a 'prompt' field
        if not prompt:
            prompt = task_details.get("description")
            if not prompt:
                logger.error(
                    f"[{self.agent_id}] Task {task_id} has no 'prompt' or 'description'. Cannot execute."  # noqa: E501
                )
                return {
                    "success": False,
                    "summary": "Missing prompt/description in task details.",
                }

        logger.info(f"[{self.agent_id}] Starting task {task_id}: '{prompt[:50]}...'")

        if not self.agent_bus:
            logger.error(
                f"[{self.agent_id}] AgentBus not available. Cannot execute task {task_id}."  # noqa: E501
            )
            return {
                "success": False,
                "summary": "AgentBus not available for event publishing.",
            }

        correlation_id = str(uuid.uuid4())
        response_event = asyncio.Event()  # Event to wait for the specific response
        self._pending_cursor_requests[correlation_id] = (
            response_event,
            None,
        )  # Store event, init response data=None
        response_data = None  # Variable to hold the received response

        try:
            logger.info(
                f"[{self.agent_id}] Publishing cursor inject request for CorrID: {correlation_id}..."  # noqa: E501
            )

            # --- MODIFIED: Replace helper with direct publish ---
            # Create the payload
            payload = CursorInjectRequestPayload(
                agent_id=self.agent_id,  # Target window is Agent-2's window
                prompt=prompt,
            )
            # Create the event
            inject_event = Event(
                type=EventType.CURSOR_INJECT_REQUEST,
                source_id=self.agent_id,
                data=payload.model_dump(),
                correlation_id=correlation_id,
            )
            # Publish the event
            await self.agent_bus.publish(inject_event)
            # Assume publish is successful if no exception
            success = True
            # --- END MODIFICATION ---

            if not success:
                logger.error(
                    f"[{self.agent_id}] Failed to publish cursor inject event (CorrID: {correlation_id}). Aborting task {task_id}."  # noqa: E501
                )
                # Clean up before returning
                del self._pending_cursor_requests[correlation_id]
                return {
                    "success": False,
                    "summary": "Failed to publish inject event to AgentBus.",
                }

            logger.info(
                f"[{self.agent_id}] Cursor inject request published (CorrID: {correlation_id}). Waiting for response (timeout: {DEFAULT_RESPONSE_TIMEOUT}s)..."  # noqa: E501
            )

            # Wait for the response event to be set by the handler
            try:
                await asyncio.wait_for(
                    response_event.wait(), timeout=DEFAULT_RESPONSE_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"[{self.agent_id}] Timeout waiting for cursor response for CorrID: {correlation_id} (Task: {task_id})."  # noqa: E501
                )
                return {
                    "success": False,
                    "summary": f"Timeout waiting for cursor response ({DEFAULT_RESPONSE_TIMEOUT}s).",  # noqa: E501
                }

            # Retrieve the response data stored by the handler
            _event, response_data = self._pending_cursor_requests.get(
                correlation_id, (None, None)
            )

            if response_data is None:
                # Should not happen if event was set, but safety check
                logger.error(
                    f"[{self.agent_id}] Response event triggered but no data found for CorrID: {correlation_id}."  # noqa: E501
                )
                return {
                    "success": False,
                    "summary": "Internal error: Response event set, but no data retrieved.",  # noqa: E501
                }

            # Process the received response data
            logger.info(
                f"[{self.agent_id}] Received response for CorrID: {correlation_id}."
            )
            # Assuming response_data contains keys like 'success', 'output', 'error'
            task_success = response_data.get("success", False)
            task_output = response_data.get("output", "")
            task_error = response_data.get("error")

            summary = f"Task {task_id} completed."
            if task_output:
                summary += f" Output: {str(task_output)[:100]}..."
            if task_error:
                summary += f" Error: {task_error}"

            return {
                "success": task_success,
                "summary": summary,
                "output": task_output,
            }  # Include full output if needed

        except Exception as e:
            logger.exception(
                f"[{self.agent_id}] Unexpected error during task {task_id} (CorrID: {correlation_id}): {e}"  # noqa: E501
            )
            return {"success": False, "summary": f"Unexpected error: {e}"}
        finally:
            # Ensure cleanup even if errors occur
            if correlation_id in self._pending_cursor_requests:
                del self._pending_cursor_requests[correlation_id]
                logger.debug(
                    f"[{self.agent_id}] Cleaned up pending request for CorrID: {correlation_id}."  # noqa: E501
                )

    async def _handle_cursor_response(self, event: BaseEvent):
        """
        Handles incoming CURSOR_RETRIEVE_SUCCESS and CURSOR_RETRIEVE_FAILURE events.
        Matches correlation ID and sets the corresponding asyncio Event.
        """
        correlation_id = event.data.get("correlation_id")
        logger.debug(
            f"[{self.agent_id}] Received event {event.event_type} with CorrID: {correlation_id}"  # noqa: E501
        )

        if correlation_id and correlation_id in self._pending_cursor_requests:
            response_event, _ = self._pending_cursor_requests[correlation_id]

            # Store the relevant data from the event
            response_data = {
                "success": event.event_type == EventType.CURSOR_RETRIEVE_SUCCESS,
                "output": event.data.get("output"),
                "error": event.data.get("error"),
                "correlation_id": correlation_id,  # Include for verification if needed
            }

            # Update the stored tuple with the response data
            self._pending_cursor_requests[correlation_id] = (
                response_event,
                response_data,
            )
            response_event.set()  # Signal that the response has been received
            logger.debug(
                f"[{self.agent_id}] Processed response for CorrID: {correlation_id}, event set."
            )
        else:
            logger.warning(
                f"[{self.agent_id}] Received cursor response for unknown/timed-out CorrID: {correlation_id}. Ignoring."
            )

    # --- Main Autonomous Loop ---
    async def run_autonomous_loop(self):
        """Main autonomous execution loop for Agent 2.

        Handles mailbox scanning by calling the BaseAgent's implementation,
        checking for and claiming suitable GUI tasks from the ProjectBoardManager,
        and processing them.
        """
        self.logger.info(f"[{self.agent_id}] Starting autonomous loop...")
        self._running = True

        # Determine this agent's specific inbox path once
        my_inbox_path = get_agent_mailbox_path(self.agent_id, self.config)

        while self._running:
            try:
                self.logger.debug(f"[{self.agent_id}] Starting new loop iteration.")

                # 1. Mailbox Scan (using BaseAgent's implementation)
                await self._scan_and_process_mailbox(
                    my_inbox_path
                )  # Call inherited method

                # 2. Working Tasks (Check if BaseAgent handles this)
                # BaseAgent._process_task_queue likely handles tasks added internally.
                # We need to check if we *have* an active task from a previous claim.
                # TODO: Implement more sophisticated active task checking if BaseAgent
                #       doesn't handle this state adequately for Agent 2's needs.
                has_active_task = False  # Placeholder
                if has_active_task:
                    self.logger.debug(
                        f"[{self.agent_id}] Currently processing an active task. Skipping queue check."  # noqa: E501
                    )
                    await asyncio.sleep(5)  # Wait before next check
                    continue

                # 3. Self-Assigned Tasks (Inbox - Placeholder)
                # Agent 2 primarily takes tasks from central queue for now.

                # 4. Central Task Queue Check (if idle)
                self.logger.debug(
                    f"[{self.agent_id}] Checking central ready queue for tasks..."
                )
                ready_tasks = await self.pbm.get_tasks_by_status(TaskStatus.READY)

                if not ready_tasks:
                    self.logger.info(
                        f"[{self.agent_id}] No tasks found in the ready queue. Checking blockers/idling."  # noqa: E501
                    )
                    # 5. Blocker Resolution (Placeholder)
                    await self._check_for_blockers()
                    await asyncio.sleep(
                        self.config.agent_settings.get("idle_sleep_interval", 30)
                    )  # Idle sleep
                    continue

                # Filter for suitable GUI tasks
                # TODO: Define a clearer tag/field in the task schema for GUI tasks
                #       instead of relying on task_type string or name matching.
                gui_tasks = [
                    t
                    for t in ready_tasks
                    if t.get("task_type") == "GUI_AUTOMATION"
                    or "GUI" in t.get("name", "").upper()
                ]

                if not gui_tasks:
                    self.logger.info(
                        f"[{self.agent_id}] No suitable GUI tasks found in the ready queue."  # noqa: E501
                    )
                    await asyncio.sleep(
                        self.config.agent_settings.get("idle_sleep_interval", 15)
                    )  # Shorter sleep if tasks exist but aren't suitable
                    continue

                # Attempt to claim the highest priority suitable task (simple approach)
                # TODO: Implement more sophisticated task selection (e.g., priority-based)
                #       if needed beyond taking the first suitable task.
                task_to_claim = gui_tasks[0]  # Simplest: take the first one
                task_id_to_claim = task_to_claim.get("task_id")

                if not task_id_to_claim:
                    self.logger.error(
                        f"[{self.agent_id}] Found suitable task missing a task_id: {task_to_claim.get('name')}. Skipping."  # noqa: E501
                    )
                    continue

                self.logger.info(
                    f"[{self.agent_id}] Attempting to claim task: {task_id_to_claim} ('{task_to_claim.get('name')}')"  # noqa: E501
                )
                try:
                    claimed_task_details = await self.pbm.claim_task(
                        task_id_to_claim, self.agent_id
                    )
                    if claimed_task_details:
                        self.logger.info(
                            f"[{self.agent_id}] Successfully claimed task {task_id_to_claim}."  # noqa: E501
                        )
                        # Add to internal processing queue or call processing method
                        # Option A: Use BaseAgent's queue (if appropriate)
                        # priority = self._get_priority_value(claimed_task_details.priority)  # noqa: E501
                        # await self._task_queue.put((priority, claimed_task_details))

                        # Option B: Call _process_single_task directly (potentially simpler)  # noqa: E501
                        # Requires converting dict -> TaskMessage if needed by _process_single_task  # noqa: E501
                        task_message = TaskMessage(
                            **claimed_task_details
                        )  # Assuming direct conversion works
                        await self._process_single_task(
                            task=task_message, correlation_id=None
                        )
                        # _process_single_task should handle status updates (COMPLETED/FAILED)  # noqa: E501
                    else:
                        # This case shouldn't happen if claim_task doesn't raise error, but safety check  # noqa: E501
                        self.logger.warning(
                            f"[{self.agent_id}] Claim successful for {task_id_to_claim} but no details returned?"  # noqa: E501
                        )
                except ProjectBoardError as e:
                    self.logger.warning(
                        f"[{self.agent_id}] Failed to claim task {task_id_to_claim}: {e}"  # noqa: E501
                    )
                    # Task was likely claimed by another agent, continue loop
                    await asyncio.sleep(1)  # Small delay before checking again
                    continue
                except Exception as e:
                    self.logger.exception(
                        f"[{self.agent_id}] Unexpected error during task claim for {task_id_to_claim}: {e}"  # noqa: E501
                    )
                    await asyncio.sleep(5)
                    continue

                # Short sleep after potentially processing a task or failing to claim
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                self.logger.info(f"[{self.agent_id}] Autonomous loop cancelled.")
                self._running = False
                break
            except Exception as e:
                self.logger.exception(
                    f"[{self.agent_id}] Unhandled error in autonomous loop: {e}"
                )
                # Avoid tight loop on persistent error
                await asyncio.sleep(60)

        self.logger.info(f"[{self.agent_id}] Autonomous loop finished.")

    async def _check_for_blockers(self):
        """Placeholder for agent-specific blocker checking logic.

        Agent 2 currently relies on other agents (e.g., Captains) for systemic
        board health and blocker management. This can be expanded if Agent 2
        needs to perform specific checks related to its GUI tasks or infra domain.
        """
        # TODO: Implement scanning task boards for blockers/corruption if needed for Agent 2 specifically.  # noqa: E501
        self.logger.debug(
            f"[{self.agent_id}] Checking for blockers (Agent 2 - Placeholder/No specific checks implemented)."  # noqa: E501
        )
        await asyncio.sleep(0.1)  # Prevent tight loop if called repeatedly

    # --- Overrides / Adaptations from BaseAgent ---
    # We need to ensure _process_single_task calls our _perform_task
    # OPTION 1: Override _process_single_task entirely (more control, more maintenance)
    # OPTION 2: Leverage existing _process_single_task but customize parts (less clear how)  # noqa: E501

    # Let's try overriding _process_single_task for clarity
    @with_error_handling(TaskProcessingError)  # noqa: F821
    @with_performance_tracking("process_single_task_agent2")  # noqa: F821
    async def _process_single_task(
        self, task: TaskMessage, correlation_id: Optional[str]
    ):
        """Processes a single claimed task by orchestrating GUI interaction via _perform_task.

        Overrides BaseAgent._process_single_task to integrate Agent 2's specific
        GUI-based task execution. Converts TaskMessage to dict for _perform_task.
        FIXME: The logic to finalize the task with ProjectBoardManager (e.g.,
               updating status to COMPLETED/FAILED and storing results) is missing
               at the end of this method. It should call something like
               `self.finalize_task_processing(task_id, status, result, completion_summary)`
               which would then interact with PBM.

        Args:
            task: The TaskMessage object representing the task to process.
            correlation_id: Optional correlation ID for tracing (currently unused here).
        """
        task_id = task.task_id
        self.logger.info(f"[{self.agent_id}] Starting processing for task: {task_id}")
        # await self.publish_task_started(task)

        result = None
        status = TaskStatus.FAILED  # Default to failure
        completion_summary = "Task processing failed internally."

        try:
            # Convert TaskMessage back to dict for existing _perform_task
            task_details = task.model_dump()  # Use Pydantic v2 method

            # Execute the core GUI logic via _perform_task
            perf_task_result = await self._perform_task(task_details)

            # Map result from _perform_task to BaseAgent expectations
            task_succeeded = perf_task_result.get("success", False)
            completion_summary = perf_task_result.get("summary", "No summary provided.")
            result = perf_task_result  # Pass the whole result dict

            if task_succeeded:
                status = TaskStatus.COMPLETED
                self.logger.info(
                    f"[{self.agent_id}] Task {task_id} completed successfully via GUI interaction."  # noqa: E501
                )
                # Validation for GUI tasks IS the success flag from orchestrator
                # We can skip flake8/py_compile validation steps here
                validation_passed = True
                validation_details = "GUI task success reported by orchestrator."
            else:
                status = TaskStatus.FAILED
                self.logger.error(
                    f"[{self.agent_id}] Task {task_id} failed during GUI interaction: {completion_summary}"  # noqa: E501
                )
                validation_passed = False  # Explicitly mark validation as failed
                validation_details = f"GUI task failed: {completion_summary}"

            # Update PBM (handle potential errors)
            # FIXME: ProjectBoardManager.update_task_status might only store a summary.
            #        Consider if a more comprehensive method (e.g., finalize_task that
            #        accepts the full 'result' dict) is needed in PBM to persist
            #        detailed output from _perform_task on the board itself.
            try:
                await self.pbm.update_task_status(
                    task_id, status, self.agent_id, completion_summary
                )
                self.logger.info(
                    f"[{self.agent_id}] Updated task {task_id} status to {status.value} in PBM."  # noqa: E501
                )
            except Exception as pbm_e:
                self.logger.error(
                    f"[{self.agent_id}] Failed to update PBM status for {task_id} to {status.value}: {pbm_e}",  # noqa: E501
                    exc_info=True,
                )
                # Task might be stuck in CLAIMED state

            # Publish events (even if PBM update failed, report what happened)
            if status == TaskStatus.COMPLETED:
                await self.publish_task_completed(task, result)
            else:
                # Use validation_details as the error message for failure reporting
                await self.publish_task_failed(
                    task, error=validation_details, is_final=True
                )
                if not validation_passed:
                    # Also publish specific validation failure event
                    await self.publish_validation_failed(task, validation_details)

        except Exception as e:
            self.logger.exception(
                f"[{self.agent_id}] Unhandled error processing task {task_id}: {e}"
            )
            completion_summary = (
                f"Unhandled exception during processing: {str(e)[:100]}..."
            )
            status = TaskStatus.FAILED
            try:
                # Attempt to mark as failed in PBM
                await self.pbm.update_task_status(
                    task_id, TaskStatus.FAILED, self.agent_id, completion_summary
                )
            except Exception as pbm_e:
                self.logger.error(
                    f"[{self.agent_id}] Also failed to update PBM status to FAILED for {task_id} after exception: {pbm_e}",  # noqa: E501
                    exc_info=True,
                )
            # Publish failure event
            await self.publish_task_failed(
                task, error=completion_summary, is_final=True
            )
            # Optionally publish agent error
            await self.publish_agent_error(
                f"Unhandled exception processing task {task_id}",
                details={
                    "exception": str(e),
                    "traceback": traceback.format_exc(),
                },  # noqa: F821
                task_id=task_id,
            )
        finally:
            # TODO: Clean up active task tracking if BaseAgent doesn't do it automatically  # noqa: E501
            self.logger.debug(f"[{self.agent_id}] Finished processing task {task_id}.")

    async def _configure(self, config: AppConfig):
        """Performs agent-specific configuration using the provided AppConfig.

        This method can be used to extract and set up specific configuration
        parameters relevant to Agent 2's operation, such as infrastructure details.
        Called during the agent's initialization lifecycle (if implemented in BaseAgent).

        Args:
            config: The application-wide AppConfig object.
        """
        # Example: Extract relevant config sections
        self.infra_config = config.get("infrastructure")
        if not self.infra_config:
            logger.warning("No infrastructure configuration found for Agent-2.")
        logger.info("Agent-2 Infrastructure Surgeon configured.")


# --- Remove old standalone script logic ---
# async def run_agent2_task(task_prompt: str): ...
# async def main(): ...
# if __name__ == "__main__": ...
