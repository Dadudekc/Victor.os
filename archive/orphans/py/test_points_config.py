#!/usr/bin/env python3
"""Test script for validating AgentPointsSystem configuration loading."""

import logging
import sys
from pathlib import Path

# Add project root to sys.path to allow for dreamos imports
# This assumes the script is run from the project root or PYTHONPATH is set
PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)  # Assumes scripts/test_points_config.py
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
if (
    str(PROJECT_ROOT) not in sys.path
):  # Ensure project root itself is also there for potential top-level imports if any
    sys.path.insert(0, str(PROJECT_ROOT))


# Configure basic logging for the test
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    logger.info(f"Current sys.path: {sys.path}")
    logger.info("Attempting to import AppConfig from dreamos.core.config")
    from dreamos.core.config import DEFAULT_CONFIG_PATH, AppConfig

    logger.info(
        f"Successfully imported AppConfig. Default config path: {DEFAULT_CONFIG_PATH}"
    )

    logger.info(
        "Attempting to import AgentPointsManager from dreamos.governance.agent_points_manager"
    )
    from dreamos.governance.agent_points_manager import (
        DEFAULT_POINT_VALUES,
        AgentPointsManager,
    )

    logger.info("Successfully imported AgentPointsManager.")

except ImportError:
    logger.error(
        "Failed to import necessary modules. Please ensure PYTHONPATH is set correctly or run from project root.",
        exc_info=True,
    )
    logger.error(
        "Make sure the script is in a 'scripts' subdirectory of your project, and 'src' is at the same level as 'scripts'."
    )
    sys.exit(1)


def main():
    logger.info("Starting Agent Points System configuration test...")

    # Determine the config file path to use for the test
    # This uses the DEFAULT_CONFIG_PATH from the config module itself
    config_file_to_test = DEFAULT_CONFIG_PATH
    logger.info(f"Using config file for test: {config_file_to_test}")

    if not config_file_to_test.exists():
        logger.error(f"Test configuration file not found: {config_file_to_test}")
        logger.error(
            "Please ensure 'runtime/config/config.yaml' exists and contains the 'agent_points_system' section."
        )
        sys.exit(1)

    try:
        logger.info(f"Loading AppConfig from: {config_file_to_test}...")
        # The AppConfig.load method in the provided snippet seems to expect a string path.
        # And it seems to be more of a factory for the singleton, let's try instantiating directly for test with a specific file path.
        # The AppConfig class itself uses settings_customise_sources which should pick up the YAML.
        # We might need to adjust how AppConfig is instantiated if its `load` method isn't suitable for specific test files.
        # For now, we assume AppConfig() will try to load DEFAULT_CONFIG_PATH via its settings sources.
        # Or, if a modified AppConfig.load(cls, config_file_path_str) is used, that would be better.

        # Re-checking AppConfig.load - it takes `config_file: Optional[str] = None`
        # but the provided user snippet called it as `AppConfig.load(config_file="path/to/runtime/config/config.yaml")`
        # The provided `config.py` has a `load_config` function that might be the intended entry point for getting the singleton.
        # Let's use AppConfig() directly which should trigger its loading mechanism including YAML source for DEFAULT_CONFIG_PATH.

        # Simplest approach: instantiate AppConfig, it should load default yaml path
        app_config = AppConfig()
        logger.info("AppConfig loaded successfully.")

        # Check if agent_points_system was loaded
        if app_config.agent_points_system:
            logger.info(
                f"AppConfig.agent_points_system successfully loaded: {app_config.agent_points_system.model_dump()}"
            )
        else:
            logger.warning("AppConfig.agent_points_system is None. Check config.yaml.")
            # Continue to AgentPointsManager to see if it uses defaults correctly

        logger.info("Initializing AgentPointsManager...")
        points_manager = AgentPointsManager(config=app_config)
        logger.info("AgentPointsManager initialized.")
        logger.info(f"Points values in manager: {points_manager.point_values}")

        # Test point retrieval for keys expected in config
        logger.info("--- Testing Point Retrieval ---")
        test_keys = [
            "task_completion",
            "task_failure",
            "unblock_major",
            "task_completion_chore",
            "non_existent_key",  # Test default handling
        ]

        for key in test_keys:
            points = points_manager.get_points_for_reason(key)
            expected_points = "(from config or default)"
            if key in DEFAULT_POINT_VALUES and (
                not app_config.agent_points_system
                or key not in app_config.agent_points_system.point_values
            ):
                expected_points = f"(expected default: {DEFAULT_POINT_VALUES[key]})"
            elif (
                app_config.agent_points_system
                and key in app_config.agent_points_system.point_values
            ):
                expected_points = f"(expected from config: {app_config.agent_points_system.point_values[key]})"
            elif key == "non_existent_key":
                expected_points = "(expected default: 0)"

            logger.info(f"Points for '{key}': {points} {expected_points}")

        logger.info("--- Test Summary ---")
        configured_task_completion = points_manager.get_points_for_reason(
            "task_completion"
        )
        default_if_missing = DEFAULT_POINT_VALUES.get("task_completion")

        if (
            app_config.agent_points_system
            and "task_completion" in app_config.agent_points_system.point_values
        ):
            if (
                configured_task_completion
                == app_config.agent_points_system.point_values["task_completion"]
            ):
                logger.info("SUCCESS: 'task_completion' points match config.yaml.")
            else:
                logger.error(
                    "FAILURE: 'task_completion' points DO NOT match config.yaml."
                )
        elif configured_task_completion == default_if_missing:
            logger.info(
                "SUCCESS: 'task_completion' points match internal default (config.yaml entry missing or section missing)."
            )
        else:
            logger.error(
                f"FAILURE: Unexpected value for 'task_completion': {configured_task_completion}. Default: {default_if_missing}"
            )

        non_existent_points = points_manager.get_points_for_reason("non_existent_key")
        if non_existent_points == 0:
            logger.info(
                "SUCCESS: Retrieval for 'non_existent_key' correctly defaulted to 0."
            )
        else:
            logger.error(
                f"FAILURE: Retrieval for 'non_existent_key' was {non_existent_points}, expected 0."
            )

        logger.info("Configuration test script finished.")

    except Exception as e:
        logger.error(f"An error occurred during the test: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
