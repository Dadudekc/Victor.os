# src/dreamos/cli/bridge_diagnostic.py

import asyncio
import logging
from unittest.mock import MagicMock, patch

import click

# Attempt to import necessary components
try:
    from dreamos.automation.cursor_orchestrator import CursorOrchestrator  # noqa: F401
    from dreamos.automation.cursor_orchestrator import (
        get_cursor_orchestrator,
    )
    from dreamos.core.config import AppConfig
    from dreamos.core.errors import DreamOSError
except ImportError as e:
    click.echo(f"Error importing DreamOS components: {e}", err=True)
    click.echo("Please ensure DreamOS is installed correctly and dependencies are met.")
    exit(1)

# Setup basic logger for CLI
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bridge_diagnostic")


@click.command()
@click.option(
    "--config-path",
    default=None,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Path to the AppConfig YAML file (e.g., runtime/config/config.yaml).",
)
@click.option(
    "--no-ui",
    is_flag=True,
    default=False,
    help="Run in mock mode without actual UI automation calls (mocks pyautogui/pyperclip).",
)
@click.option(
    "--agent-id",
    default="diagnostic_agent",
    help="Dummy agent ID to use for the test injection.",
)
def run_diagnostic(config_path, no_ui, agent_id):
    """Runs a diagnostic 'ping' injection using CursorOrchestrator."""
    click.echo("Starting bridge diagnostic...")

    # --- Load Config ---
    try:
        # Use default path logic similar to manage_tasks.py if path not provided
        if config_path is None:
            # Assuming PROJECT_ROOT is findable or defined elsewhere
            # For simplicity, let's assume a common default
            from dreamos.utils.project_root import find_project_root

            PROJECT_ROOT = find_project_root()
            effective_config_path = PROJECT_ROOT / "runtime" / "config" / "config.yaml"
            if not effective_config_path.exists():
                click.echo(
                    f"Default config path not found: {effective_config_path}", err=True
                )
                raise FileNotFoundError("Default config not found.")
            click.echo(f"Using default config: {effective_config_path}")
        else:
            effective_config_path = config_path

        app_config = AppConfig.load(config_file=effective_config_path)
        click.echo("AppConfig loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load AppConfig: {e}", exc_info=True)
        click.echo(f"Error loading configuration: {e}", err=True)
        return

    # --- Mocking Setup (if --no-ui) ---
    mock_patches = []
    if no_ui:
        click.echo("Running in --no-ui mode. Mocking UI libraries.")
        # Define mocks
        mock_pyautogui = MagicMock()
        mock_pyperclip = MagicMock()
        mock_pygetwindow = MagicMock()
        mock_pygetwindow.getWindowsWithTitle.return_value = [
            MagicMock(activate=MagicMock())
        ]

        # Create patches - apply them *before* orchestrator initialization
        patch_pyautogui = patch(
            "dreamos.automation.cursor_orchestrator.pyautogui", mock_pyautogui
        )
        patch_pyperclip = patch(
            "dreamos.automation.cursor_orchestrator.pyperclip", mock_pyperclip
        )
        patch_pygetwindow = patch(
            "dreamos.automation.cursor_orchestrator.pygetwindow", mock_pygetwindow
        )
        patch_ui_available = patch(
            "dreamos.automation.cursor_orchestrator.UI_AUTOMATION_AVAILABLE", True
        )
        mock_patches = [
            patch_pyautogui,
            patch_pyperclip,
            patch_pygetwindow,
            patch_ui_available,
        ]

        for p in mock_patches:
            p.start()
            # Ensure mocks are accessible if needed later
            globals()["mock_pyautogui"] = mock_pyautogui
            globals()["mock_pyperclip"] = mock_pyperclip
            globals()["mock_pygetwindow"] = mock_pygetwindow
    else:
        click.echo("Running in live UI mode. Ensure Cursor is running and configured.")

    # --- Run Test ---
    try:
        click.echo(f"Attempting to inject 'ping' for agent '{agent_id}'...")
        # Run the async orchestrator logic
        asyncio.run(async_diagnostic_inject(app_config, agent_id))
        click.echo("Diagnostic injection call completed.")

        # If mocked, check calls
        if no_ui:
            click.echo("Checking mock calls...")
            mock_pyautogui.click.assert_called()
            # Add more specific call checks if needed, e.g., call counts, args
            if app_config.gui_automation.use_clipboard_paste:
                mock_pyperclip.copy.assert_called_with("ping")
                mock_pyautogui.hotkey.assert_called_with("ctrl", "v")
            else:
                mock_pyautogui.write.assert_called_with("ping")
            mock_pyautogui.press.assert_called_with("enter")
            click.echo("Mock calls verified (basic checks).")

    except DreamOSError as e:
        logger.error(f"Orchestrator error during diagnostic: {e}", exc_info=True)
        click.echo(f"Error during diagnostic: {e}", err=True)
    except Exception as e:
        logger.error(f"Unexpected error during diagnostic: {e}", exc_info=True)
        click.echo(f"Unexpected error: {e}", err=True)
    finally:
        # Stop patches if they were started
        for p in mock_patches:
            p.stop()
        click.echo("Diagnostic finished.")


async def async_diagnostic_inject(config: AppConfig, agent_id: str):
    """Async helper to get orchestrator and call inject."""
    orchestrator = await get_cursor_orchestrator(config=config)
    success = await orchestrator.inject_prompt(agent_id=agent_id, prompt="ping")
    if success:
        click.echo("Orchestrator reported SUCCESS for injection.")
    else:
        click.echo("Orchestrator reported FAILURE for injection.", err=True)


if __name__ == "__main__":
    run_diagnostic()
