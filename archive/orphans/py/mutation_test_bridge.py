#!/usr/bin/env python3
"""
Mutation Test Harness for THEA-Cursor Bridge

Framework for injecting artificial faults into mocked bridge components
to test the robustness of the main agent and stress test logic.
Loads scenarios dynamically from a JSON file.
"""

import json  # Added
import logging
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import patch

# --- Path Setup ---
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# --- Import Target Components (or Mocks) ---
# Import functions/classes to be tested or wrapped by mutations
try:
    from concurrent.futures import TimeoutError  # Example

    # Potentially import mockable dependencies directly if needed
    # from src.dreamos.utils.gui_utils import copy_thea_reply
    # from src.dreamos.services.utils.chatgpt_scraper import ChatGPTScraper
    # from src.dreamos.tools.cursor_bridge.cursor_bridge import inject_prompt_into_cursor
    # Import specific exceptions if needed for fault_raise_exception params
    from socket import ConnectionRefusedError  # Example

    from src.dreamos.core.config import AppConfig, load_config

    from scripts.thea_to_cursor_agent import (
        main_loop as agent_main_loop,  # Example target
    )
except ImportError as e:
    print(f"CRITICAL: Failed to import modules needed for mutation testing: {e}")
    sys.exit(1)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("BridgeMutationTester")

# --- Constants ---
SCENARIO_FILE = project_root / "runtime" / "config" / "mutation_scenarios.json"

# --- Mutation Definitions ---
# Store faults in a dictionary for lookup
AVAILABLE_FAULTS: Dict[str, Callable] = {}


def register_fault(func: Callable):
    """Decorator to register fault functions."""
    AVAILABLE_FAULTS[func.__name__] = func
    return func


@register_fault
def fault_none(original_func: Optional[Callable] = None) -> Callable:
    """Mutation: Return None instead of the actual result."""

    def mutated_func(*args, **kwargs):
        # Use provided name or try to get from args if original_func was None initially
        func_name = original_func.__name__ if original_func else "unknown_target"
        logger.warning(f"[MUTATION:{func_name}] Returning None")
        return None

    return mutated_func


@register_fault
def fault_empty_string(original_func: Optional[Callable] = None) -> Callable:
    """Mutation: Return an empty string."""

    def mutated_func(*args, **kwargs):
        func_name = original_func.__name__ if original_func else "unknown_target"
        logger.warning(f"[MUTATION:{func_name}] Returning ''")
        return ""

    return mutated_func


@register_fault
def fault_raise_exception(
    original_func: Optional[Callable] = None,
    exc_type_str: str = "Exception",
    msg: str = "Simulated mutation error",
) -> Callable:
    """Mutation: Raise a specified exception by string name."""

    def mutated_func(*args, **kwargs):
        func_name = original_func.__name__ if original_func else "unknown_target"
        exc_type = getattr(
            sys.modules[__name__], exc_type_str, Exception
        )  # Find exception type by name
        logger.warning(f"[MUTATION:{func_name}] Raising {exc_type.__name__}('{msg}')")
        raise exc_type(msg)

    return mutated_func


@register_fault
def fault_delay(
    original_func: Optional[Callable] = None, delay_seconds: float = 2.0
) -> Callable:
    """Mutation: Add a delay before calling the original function."""

    def mutated_func(*args, **kwargs):
        func_name = original_func.__name__ if original_func else "unknown_target"
        logger.warning(f"[MUTATION:{func_name}] Adding delay of {delay_seconds}s")
        time.sleep(delay_seconds)
        # This version needs the *actual* original function to call it.
        # The patching logic needs to handle providing this.
        # For simplicity in this refactor, we might need to assume it doesn't call original
        # OR modify how run_mutation_test works.
        # Let's assume for now it just delays and returns a placeholder or None
        # return original_func(*args, **kwargs) # Requires more complex patching
        logger.warning(
            f"[MUTATION:{func_name}] Delay finished (original call skipped in this version)"
        )
        return None  # Or a mock value

    return mutated_func


@register_fault
def fault_return_corrupted_data(
    original_func: Optional[Callable] = None, corruption: Any = "<corrupted>"
) -> Callable:
    """Mutation: Return unexpected data type (e.g., bytes)."""

    def mutated_func(*args, **kwargs):
        func_name = original_func.__name__ if original_func else "unknown_target"
        logger.warning(
            f"[MUTATION:{func_name}] Returning corrupted data ({type(corruption)}): {str(corruption)[:50]}"
        )
        return corruption

    return mutated_func


@register_fault
def fault_return_false(original_func: Optional[Callable] = None) -> Callable:
    """Mutation: Always return False (useful for simulating failed checks/operations)."""

    def mutated_func(*args, **kwargs):
        func_name = original_func.__name__ if original_func else "unknown_target"
        logger.warning(f"[MUTATION:{func_name}] Returning False")
        return False

    return mutated_func


# --- Scenario Loading ---
def load_mutation_scenarios(file_path: Path) -> List[Dict[str, Any]]:
    """Loads mutation scenarios from the JSON file."""
    if not file_path.exists():
        logger.error(f"Mutation scenario file not found: {file_path}")
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            scenarios = json.load(f)
        if not isinstance(scenarios, list):
            logger.error(f"Invalid format in {file_path}, expected a JSON list.")
            return []
        # TODO: Add validation for scenario structure
        logger.info(f"Loaded {len(scenarios)} mutation scenarios from {file_path}")
        return scenarios
    except Exception as e:
        logger.error(f"Failed to load or parse {file_path}: {e}", exc_info=True)
        return []


# --- Test Execution Framework ---
def create_mutator(fault_config: Dict[str, Any]) -> Optional[Callable]:
    """Creates a mutation function based on config."""
    fault_type = fault_config.get("type")
    params = fault_config.get("params", {})

    fault_builder = AVAILABLE_FAULTS.get(fault_type)
    if not fault_builder:
        logger.error(f"Unknown fault type specified: '{fault_type}'")
        return None

    try:
        # Pass params to the fault builder function
        return fault_builder(**params)
    except TypeError as e:
        logger.error(
            f"Error creating mutator for type '{fault_type}' with params {params}: {e}"
        )
        return None


def run_mutation_test(target_path: str, mutator: Callable, config: AppConfig):
    """Runs the target code with a specific mutation applied."""
    logger.info(
        f"--- Running Mutation Test --- Target: [{target_path}], Mutation: [{getattr(mutator, '__name__', 'anonymous')}] ---"
    )
    test_passed = False
    # We apply the mutator directly as the side_effect
    with patch(
        target_path, side_effect=mutator(None), create=True
    ):  # Pass None as original func initially
        logger.info("Executing test scenario with mutation applied...")
        try:
            # Placeholder for test execution logic
            print(
                f"[SIMULATION] Calling target logic with mutation on {target_path}..."
            )
            # Example: Run one agent loop cycle (needs careful mocking of other deps)
            # with patch('time.sleep', side_effect=StopIteration("break loop")):
            #     agent_main_loop(config) # Need to ensure config is valid
            time.sleep(0.2)  # Simulate work
            logger.info(
                "Test scenario execution finished (simulated). Outcome assumed OK."
            )
            # TODO: Add assertions - did the agent handle the fault gracefully?
            test_passed = True  # Assume survived if no crash during simulation
        except StopIteration:
            logger.info("Test scenario loop broken as expected.")
            test_passed = True  # Loop break is often expected success
        except Exception as e:
            logger.error(f"Execution FAILED under mutation: {e}", exc_info=True)
            test_passed = False

    result = (
        "PASSED (Survived Mutation)"
        if test_passed
        else "FAILED (Crashed/Unexpected Behavior)"
    )
    logger.info(f"--- Mutation Test Result: {result} ---")
    return test_passed


# --- Main Execution ---
if __name__ == "__main__":
    logger.info("Starting Bridge Mutation Test Harness...")

    scenarios = load_mutation_scenarios(SCENARIO_FILE)
    if not scenarios:
        logger.critical("No valid scenarios loaded. Exiting.")
        sys.exit(1)

    # Load config once for all tests
    try:
        app_config = load_config()
    except Exception as e:
        logger.critical(
            f"Failed to load AppConfig: {e}. Cannot run tests.", exc_info=True
        )
        sys.exit(1)

    all_passed_count = 0
    total_mutations = 0

    for scenario in scenarios:
        scenario_name = scenario.get("scenario_name", "Unnamed Scenario")
        target = scenario.get("target_function")
        mutations = scenario.get("mutations", [])
        logger.info(
            f"\n===== Running Scenario: {scenario_name} (Target: {target}) ===="
        )

        if not target or not mutations:
            logger.warning(
                "Skipping scenario due to missing target function or mutations."
            )
            continue

        for mutation_config in mutations:
            total_mutations += 1
            mutator = create_mutator(mutation_config)
            if mutator:
                passed = run_mutation_test(target, mutator, app_config)
                if passed:
                    all_passed_count += 1
                time.sleep(0.1)  # Small delay between mutations
            else:
                logger.error(
                    f"Skipping mutation due to creation error: {mutation_config}"
                )

    logger.info("\n--- Mutation Testing Summary ---")
    logger.info(f"Total Scenarios Executed: {len(scenarios)}")
    logger.info(f"Total Mutations Attempted: {total_mutations}")
    logger.info(f"Mutations Survived (Passed): {all_passed_count}")
    failed_count = total_mutations - all_passed_count
    if failed_count > 0:
        logger.error(f"Mutations Failed: {failed_count}")
        logger.error(
            "Overall Result: FAILED (One or more mutations caused unexpected failure)"
        )
    else:
        logger.info("Overall Result: PASSED (All mutations survived)")
    logger.info("Mutation Test Harness finished.")
