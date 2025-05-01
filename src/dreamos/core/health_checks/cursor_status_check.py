# src/dreamos/core/health_checks/cursor_status_check.py
import asyncio
import logging
from typing import Any, Dict, List, Literal, Optional

# Assuming CursorOrchestrator is accessible via a getter or singleton pattern
# Adjust import path as needed based on final location
try:
    from dreamos.automation.cursor_orchestrator import (
        AgentStatus,
        CursorOrchestrator,
        CursorOrchestratorError,
    )

    # Potentially use an async getter if provided by the module
    # from dreamos.automation.cursor_orchestrator import get_cursor_orchestrator
    CURSOR_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    CursorOrchestrator = None
    AgentStatus = None
    CursorOrchestratorError = None
    CURSOR_ORCHESTRATOR_AVAILABLE = False
    logging.error(
        "CursorOrchestrator not found. Cannot perform cursor agent status check."
    )

logger = logging.getLogger(__name__)

# {{ EDIT START: Define constants for return structure }}
CheckStatus = Literal["PASS", "WARN", "FAIL", "ERROR"]
CHECK_NAME = "cursor_agent_status"
# {{ EDIT END }}

# TODO: Make EXPECTED_AGENT_IDS configurable or dynamically retrieved from orchestrator/registry.
EXPECTED_AGENT_IDS = [f"agent_{i:03d}" for i in range(1, 9)]  # agent_001 to agent_008

HEALTHY_STATUSES = ["IDLE", "INJECTING", "AWAITING_RESPONSE", "COPYING"]
UNHEALTHY_STATUSES = ["ERROR", "UNRESPONSIVE", "UNKNOWN"]


async def check_cursor_agent_statuses() -> Dict[str, Any]:
    """Checks the operational status of agents managed by CursorOrchestrator."""
    logger.info(f"Running {CHECK_NAME} check...")
    details: Dict[str, Any] = {"per_agent": {}}
    overall_status: CheckStatus = "PASS"  # Start optimistic

    if not CURSOR_ORCHESTRATOR_AVAILABLE:
        logger.error(
            f"{CHECK_NAME}: Cannot perform check: CursorOrchestrator module not available."
        )
        details["error"] = "CursorOrchestrator unavailable"
        for agent_id in EXPECTED_AGENT_IDS:
            details["per_agent"][agent_id] = {
                "healthy": False,
                "status": "N/A",
                "reason": details["error"],
            }
        return {"check_name": CHECK_NAME, "status": "ERROR", "details": details}

    try:
        # TODO: Replace direct instantiation with getter or dependency injection for CursorOrchestrator.
        orchestrator = CursorOrchestrator()
    except Exception as e:
        logger.error(
            f"{CHECK_NAME}: Failed to get CursorOrchestrator instance: {e}",
            exc_info=True,
        )
        details["error"] = "Failed to get orchestrator instance"
        for agent_id in EXPECTED_AGENT_IDS:
            details["per_agent"][agent_id] = {
                "healthy": False,
                "status": "N/A",
                "reason": details["error"],
            }
        return {"check_name": CHECK_NAME, "status": "ERROR", "details": details}

    status_tasks = []
    for agent_id in EXPECTED_AGENT_IDS:
        status_tasks.append(orchestrator.get_agent_status(agent_id))

    try:
        statuses = await asyncio.gather(*status_tasks)
    except Exception as e:
        logger.error(
            f"{CHECK_NAME}: Error gathering agent statuses: {e}", exc_info=True
        )
        details["error"] = f"Error during status query: {e}"
        for agent_id in EXPECTED_AGENT_IDS:
            details["per_agent"][agent_id] = {
                "healthy": False,
                "status": "N/A",
                "reason": details["error"],
            }
        return {"check_name": CHECK_NAME, "status": "ERROR", "details": details}

    any_unhealthy = False
    for agent_id, status in zip(EXPECTED_AGENT_IDS, statuses):
        agent_result = {"healthy": False, "status": status, "reason": ""}
        if status in HEALTHY_STATUSES:
            agent_result["healthy"] = True
            agent_result["reason"] = f"Agent status '{status}' is considered healthy."
            logger.debug(f"{CHECK_NAME} PASSED for {agent_id}: {status}")
        elif status in UNHEALTHY_STATUSES:
            agent_result["reason"] = f"Agent status '{status}' is unhealthy."
            logger.warning(f"{CHECK_NAME} FAILED for {agent_id}: {status}")
            any_unhealthy = True
        else:  # Handles UNKNOWN or other unexpected statuses
            agent_result["reason"] = f"Unknown or unexpected status: {status}"
            logger.error(
                f"{CHECK_NAME} FAILED for {agent_id}: Unexpected status '{status}'"
            )
            any_unhealthy = True

        details["per_agent"][agent_id] = agent_result

    if any_unhealthy:
        if overall_status != "ERROR":  # Don't override ERROR status
            overall_status = "FAIL"  # Any unhealthy agent fails the check

    logger.info(f"{CHECK_NAME} check complete. Overall status: {overall_status}")
    return {"check_name": CHECK_NAME, "status": overall_status, "details": details}


# Example usage (can be run standalone if orchestrator is setup)
async def _run_check():
    print("Running Cursor Agent Status Check...")
    # Requires orchestrator to be running/initializable
    if not CURSOR_ORCHESTRATOR_AVAILABLE:
        print("CursorOrchestrator not available. Cannot run check.")
        return

    check_results = await check_cursor_agent_statuses()
    print("\n--- Check Results ---")
    import pprint

    pprint.pprint(check_results)
    print("-------------------")


if __name__ == "__main__":
    # Note: Running this standalone requires CursorOrchestrator
    # to be properly configured and potentially running if it uses external resources.
    try:
        asyncio.run(_run_check())
    except RuntimeError as e:
        print(f"Error running async check (might need running event loop): {e}")
    except CursorOrchestratorError as e:
        print(f"CursorOrchestrator setup error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
