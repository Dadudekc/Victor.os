import asyncio
import logging
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Ensure src is in path to import dreamos modules
SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dreamos.core.coordination.message_patterns import (  # noqa: E402
    TaskMessage,
    TaskPriority,
    TaskStatus,
)

# Imports (adjust paths if necessary)
# Assuming TaskMemoryLayer is the concrete implementation for PersistentTaskMemoryAPI
from dreamos.memory.layers.task_memory_layer import TaskMemoryLayer  # noqa: E402

# --- Configuration ---
# Match the timeout configured in RecoveryCoordinatorAgent
TIMEOUT_SECONDS = 900  # Default: 15 minutes
AGENT_ID_TO_TEST = "AgentTest"  # Dummy agent ID for the task
TASK_TYPE_TO_TEST = "simulated_long_task"
# --- End Configuration ---


async def simulate_long_running_task():
    """
    Creates or updates a task in the task memory to appear as if it has been
    running for longer than the configured timeout.
    """
    logger = logging.getLogger("TimeoutSimulator")
    logger.info("Starting task timeout simulation...")

    try:
        # Initialize the task memory layer (uses default path: runtime/memory/task_memory.json)  # noqa: E501
        # NOTE: Ensure this path matches what RecoveryCoordinatorAgent uses
        task_memory = TaskMemoryLayer()

        # Create a dummy TaskMessage
        task_id = f"timeout_test_{uuid.uuid4().hex[:8]}"
        past_timestamp = datetime.now(timezone.utc) - timedelta(
            seconds=TIMEOUT_SECONDS + 120
        )  # Ensure it's well past the timeout

        dummy_task = TaskMessage(
            task_id=task_id,
            agent_id=AGENT_ID_TO_TEST,
            task_type=TASK_TYPE_TO_TEST,
            priority=TaskPriority.NORMAL,
            status=TaskStatus.RUNNING,  # Set status to RUNNING
            input_data={"simulated_param": "test_value"},
            result=None,
            error=None,
            created_at=past_timestamp
            - timedelta(seconds=10),  # Arbitrary creation time before update
            updated_at=past_timestamp,  # Set last update time to trigger timeout
            correlation_id=str(uuid.uuid4()),
            source_agent_id="TimeoutSimulatorScript",
            started_at=past_timestamp,  # Set started_at as well
        )

        logger.info(
            f"Creating/Updating task {task_id} with status RUNNING and timestamp {past_timestamp.isoformat()}"  # noqa: E501
        )

        # --- Add/Update the task in memory ---
        # This is the crucial part. We assume an `add_or_update_task` method exists.
        # If TaskMemoryLayer doesn't have this exact method, this needs adjustment.
        # Based on RecoveryCoordinatorAgent usage, this method should exist.
        if hasattr(task_memory, "add_or_update_task") and callable(
            task_memory.add_or_update_task
        ):
            success = await task_memory.add_or_update_task(dummy_task)
            if success:
                logger.info(
                    f"Successfully added/updated task {task_id} in task memory."
                )
                logger.info(
                    f"RecoveryCoordinatorAgent should detect this task as timed out on its next poll cycle (within {task_memory.poll_interval}s?)."  # noqa: E501
                )  # Need poll interval info
            else:
                logger.error(f"Failed to add/update task {task_id} in task memory.")
        else:
            # Fallback: Try modifying the internal data directly (less safe)
            logger.warning(
                "`add_or_update_task` method not found directly on TaskMemoryLayer. Attempting direct modification (may not persist correctly)."  # noqa: E501
            )
            with task_memory._lock:
                task_memory._memory_data[task_id] = (
                    dummy_task.to_dict()
                )  # Use dict representation
                task_memory._save_memory()  # Trigger save
            logger.info(
                f"Directly modified task memory for {task_id}. Persistence relies on _save_memory()."  # noqa: E501
            )
            logger.info(
                "RecoveryCoordinatorAgent should detect this task as timed out on its next poll cycle."  # noqa: E501
            )

    except ImportError as e:
        logger.error(
            f"Failed to import necessary modules. Check paths and environment: {e}"
        )
    except FileNotFoundError as e:
        logger.error(f"Task memory file not found or path incorrect: {e}")
    except AttributeError as e:
        logger.error(
            f"Potential issue with TaskMemoryLayer structure or missing method: {e}"
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(simulate_long_running_task())
