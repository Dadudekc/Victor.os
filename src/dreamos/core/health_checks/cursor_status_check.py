# src/dreamos/core/health_checks/cursor_status_check.py
import asyncio
import logging
from typing import Any, Dict, Literal, Optional

# Import AppConfig
from ..config import AppConfig

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

# TODO: Make EXPECTED_AGENT_IDS configurable or dynamically retrieved from orchestrator/registry.  # noqa: E501
# REMOVED hardcoded EXPECTED_AGENT_IDS

HEALTHY_STATUSES = ["IDLE", "INJECTING", "AWAITING_RESPONSE", "COPYING"]
UNHEALTHY_STATUSES = ["ERROR", "UNRESPONSIVE", "UNKNOWN"]


class CursorStatusCheck:
    """Encapsulates the logic for the cursor agent status check."""

    def __init__(
        self, config: AppConfig, cursor_orchestrator: Optional[CursorOrchestrator]
    ):
        self.config = config
        self.expected_agent_ids = config.health_checks.expected_agent_ids
        self.orchestrator = cursor_orchestrator
        if not self.orchestrator:
            logger.warning(
                "CursorOrchestrator instance not provided to CursorStatusCheck."
            )
        logger.info(
            f"{CHECK_NAME} initialized. Expected Agents: {len(self.expected_agent_ids)}"
        )

    async def run_check(self) -> Dict[str, Any]:
        """Checks the operational status of agents managed by CursorOrchestrator."""
        logger.info(f"Running {CHECK_NAME} check...")
        details: Dict[str, Any] = {"per_agent": {}}
        overall_status: CheckStatus = "PASS"  # Start optimistic

        if not CURSOR_ORCHESTRATOR_AVAILABLE or not self.orchestrator:
            error_reason = (
                "CursorOrchestrator module unavailable"
                if not CURSOR_ORCHESTRATOR_AVAILABLE
                else "CursorOrchestrator instance not provided"
            )
            logger.error(f"{CHECK_NAME}: Cannot perform check: {error_reason}.")
            details["error"] = error_reason
            for agent_id in self.expected_agent_ids:
                details["per_agent"][agent_id] = {
                    "healthy": False,
                    "status": "N/A",
                    "reason": details["error"],
                }
            return {"check_name": CHECK_NAME, "status": "ERROR", "details": details}

        # REMOVED direct instantiation

        status_tasks = []
        for agent_id in self.expected_agent_ids:
            # Use the injected orchestrator instance
            status_tasks.append(self.orchestrator.get_agent_status(agent_id))

        try:
            statuses = await asyncio.gather(*status_tasks)
        except Exception as e:
            logger.error(
                f"{CHECK_NAME}: Error gathering agent statuses: {e}", exc_info=True
            )
            details["error"] = f"Error during status query: {e}"
            for agent_id in self.expected_agent_ids:
                details["per_agent"][agent_id] = {
                    "healthy": False,
                    "status": "N/A",
                    "reason": details["error"],
                }
            return {"check_name": CHECK_NAME, "status": "ERROR", "details": details}

        any_unhealthy = False
        for agent_id, status in zip(self.expected_agent_ids, statuses):
            agent_result = {"healthy": False, "status": status, "reason": ""}
            if status in HEALTHY_STATUSES:
                agent_result["healthy"] = True
                agent_result["reason"] = (
                    f"Agent status '{status}' is considered healthy."
                )
                logger.debug(f"{CHECK_NAME} PASSED for {agent_id}: {status}")
            elif status in UNHEALTHY_STATUSES:
                agent_result["reason"] = f"Agent status '{status}' is unhealthy."
                logger.warning(f"{CHECK_NAME} FAILED for {agent_id}: {status}")
                any_unhealthy = True
            else:
                agent_result["reason"] = f"Unknown or unexpected status: {status}"
                logger.error(
                    f"{CHECK_NAME} FAILED for {agent_id}: Unexpected status '{status}'"
                )
                any_unhealthy = True

            details["per_agent"][agent_id] = agent_result

        if any_unhealthy:
            if overall_status != "ERROR":
                overall_status = "FAIL"

        logger.info(f"{CHECK_NAME} check complete. Overall status: {overall_status}")
        return {"check_name": CHECK_NAME, "status": overall_status, "details": details}


# Keep original function signature as a wrapper?
async def check_cursor_agent_statuses(
    config: AppConfig,  # Requires config
    cursor_orchestrator: Optional[CursorOrchestrator],  # Requires orchestrator instance
) -> Dict[str, Any]:
    """Runs the cursor agent status check using config and orchestrator instance."""
    checker = CursorStatusCheck(config, cursor_orchestrator)
    return await checker.run_check()


# Example usage (can be run standalone if orchestrator is setup)
async def _run_check():
    print("Running Cursor Agent Status Check...")
    # Requires orchestrator to be running/initializable
    if not CURSOR_ORCHESTRATOR_AVAILABLE:
        print("CursorOrchestrator not available. Cannot run check.")
        return

    # Load config
    try:
        app_config = AppConfig.load()
    except Exception as e:
        print(f"Failed to load AppConfig: {e}. Cannot run check.")
        return

    # Instantiate orchestrator (replace with actual DI/getter if available)
    try:
        orchestrator_instance = (
            CursorOrchestrator()
        )  # Still direct instantiation for standalone test
    except Exception as e:
        print(f"Failed to instantiate CursorOrchestrator: {e}")
        return

    check_results = await check_cursor_agent_statuses(app_config, orchestrator_instance)
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
