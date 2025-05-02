# core/config.py
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

import yaml
from pydantic import BaseModel, Field, FilePath, SecretStr, ValidationError, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Adjusted imports to reflect new location within core
# REMOVED: Unused AgentBus import
# from .coordination.agent_bus import AgentBus
# REMOVED: Obsolete config_utils references
from .errors import ConfigurationError as CoreConfigurationError

# Define project root relative to this file (now three levels up to repo root)
# NOTE (Captain-Agent-5): Calculating PROJECT_ROOT based on __file__ location can be fragile.
# Consider using a marker file search or environment variable for more robustness.
# However, the PathsConfig allows overriding this value during initialization.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "runtime" / "config" / "config.yaml"

# --- Pydantic Models for Config Structure ---


class LoggingConfig(BaseModel):
    level: str = Field("INFO", description="Logging level (e.g., DEBUG, INFO, WARNING)")
    log_file: Optional[str] = Field(
        None, description="Path to log file relative to runtime/logs, if enabled."
    )
    log_to_console: bool = Field(True, description="Whether to log to console.")


class PathsConfig(BaseModel):
    runtime: Path = Field(
        PROJECT_ROOT / "runtime", description="Path to the runtime directory"
    )
    logs: Path = Field(
        PROJECT_ROOT / "runtime" / "logs", description="Path to the logs directory"
    )
    agent_comms: Path = Field(
        PROJECT_ROOT / "runtime" / "agent_comms",
        description="Base directory for agent communications (mailboxes, boards)",
    )
    central_task_boards: Path = Field(
        PROJECT_ROOT / "runtime" / "agent_comms" / "central_task_boards",
        description="Directory for central task board JSON files",
    )
    task_schema: Path = Field(
        PROJECT_ROOT
        / "src"
        / "dreamos"
        / "coordination"
        / "tasks"
        / "task-schema.json",
        description="Path to the task definition JSON schema",
    )
    project_root: Path = Field(
        PROJECT_ROOT, description="Resolved project root directory"
    )


class DreamscapePlannerAgentConfig(BaseModel):
    agent_id: str = Field(
        "dreamscape_planner_001", description="Agent ID for the planner"
    )
    llm_model: str = Field("gpt-3.5-turbo", description="LLM model to use for planning")
    max_tokens: int = Field(500, description="Max tokens for planning LLM response")


class DreamscapeWriterAgentConfig(BaseModel):
    agent_id: str = Field(
        "dreamscape_writer_001", description="Agent ID for the writer"
    )
    llm_model: str = Field(
        "gpt-4-turbo-preview",
        description="LLM model to use for writing (potentially different)",
    )  # Example: different model
    max_tokens: int = Field(
        2000, description="Max tokens for writing LLM response"
    )  # Example: more tokens


class DreamscapeConfig(BaseModel):
    # NOTE (Captain-Agent-5): This config section appears specific to a
    # 'Dreamscape' planner/writer application. Review if this is still actively
    # used or belongs in the core configuration vs. an application-specific layer.
    planner_agent: DreamscapePlannerAgentConfig = Field(
        default_factory=DreamscapePlannerAgentConfig
    )
    writer_agent: DreamscapeWriterAgentConfig = Field(
        default_factory=DreamscapeWriterAgentConfig
    )


class OpenAIConfig(BaseModel):
    api_key: Optional[SecretStr] = Field(
        None, alias="openai_api_key", description="OpenAI API Key"
    )
    # Add other OpenAI settings like organization, base_url if needed


# ADDED: Config model for ChatGPT Scraper Credentials
class ChatGPTScraperConfig(BaseModel):
    email: Optional[SecretStr] = Field(
        None, alias="chatgpt_email", description="ChatGPT Login Email/Username"
    )
    password: Optional[SecretStr] = Field(
        None, alias="chatgpt_password", description="ChatGPT Login Password"
    )
    totp_secret: Optional[SecretStr] = Field(
        None,
        alias="chatgpt_totp_secret",
        description="ChatGPT 2FA TOTP Secret (Base32)",
    )


# EDIT START: Add GUI Automation Config Model
class GuiAutomationConfig(BaseModel):
    target_window_title: str = "Cursor"  # Default to common IDE name
    input_coords_file_path: FilePath = Path(
        PROJECT_ROOT / "runtime/config/cursor_agent_coords.json"
    )
    copy_coords_file_path: FilePath = Path(
        PROJECT_ROOT / "runtime/config/cursor_agent_copy_coords.json"
    )
    recalibration_retries: int = 1
    min_pause_seconds: float = 0.10
    max_pause_seconds: float = 0.25
    random_offset_pixels: int = 3
    type_interval_seconds: float = 0.01  # Add typing interval
    retry_attempts: int = 3  # Add retry attempts
    retry_delay_seconds: float = 0.5  # Add retry delay
    copy_attempts: int = (
        2  # Add copy attempts config (for TASK_AGENT8-CONFIG-CURSORORCH-COPYATTEMPTS-001)
    )

    # Add validators if needed, e.g., for path existence (though FilePath handles basic check)


# EDIT END


# Main Application Configuration Model
class AppConfig(BaseSettings):
    """Main application configuration loaded from environment variables and/or config file."""

    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    dreamscape: DreamscapeConfig = Field(default_factory=DreamscapeConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    chatgpt_scraper: ChatGPTScraperConfig = Field(default_factory=ChatGPTScraperConfig)
    gui_automation: GuiAutomationConfig = Field(default_factory=GuiAutomationConfig)

    # Add other top-level config sections as needed (e.g., agent_bus, database)

    # Configuration loading behavior
    model_config = SettingsConfigDict(
        env_prefix="DREAMOS_",  # Example prefix: DREAMOS_OPENAI_API_KEY
        env_nested_delimiter="__",  # Example: DREAMOS_CHATGPT_SCRAPER__EMAIL
        env_file=".env",  # Optionally load from .env file
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields found in config sources
    )

    # Custom initialization to load from YAML file as well
    # NOTE: _config_file argument is handled by pydantic-settings if file path loading is desired
    # Or implement custom __init__ / model_post_init if complex loading logic required

    @classmethod
    def load(cls, config_file: Optional[Path] = None) -> "AppConfig":
        """Loads configuration, prioritizing env vars over config file."""
        # pydantic-settings handles .env loading automatically.
        # For YAML, we might need custom logic if not using its built-in features fully.
        # This is a basic example, assumes pydantic-settings handles most things.
        try:
            # Instantiate using pydantic-settings (handles env vars, .env)
            instance = cls()

            # If a specific YAML file is provided, or default exists, load and merge
            yaml_config_data = {}
            load_path = config_file if config_file else DEFAULT_CONFIG_PATH
            if load_path.exists():
                try:
                    with open(load_path, "r") as f:
                        yaml_config_data = yaml.safe_load(f) or {}
                    # Simplified YAML merge logic (Env vars take priority)
                    temp_instance = cls.model_validate(yaml_config_data)
                    final_data = temp_instance.model_dump()
                    final_data.update(instance.model_dump(exclude_unset=True))
                    instance = cls.model_validate(final_data)
                except Exception as e:
                    logging.warning(
                        f"Could not load or parse YAML config at {load_path}: {e}"
                    )

            # Ensure paths are absolute after loading and potential merging
            instance.paths.runtime = instance.paths.runtime.resolve()
            instance.paths.logs = instance.paths.logs.resolve()
            instance.paths.agent_comms = instance.paths.agent_comms.resolve()
            instance.paths.central_task_boards = (
                instance.paths.central_task_boards.resolve()
            )
            instance.paths.task_schema = instance.paths.task_schema.resolve()
            instance.paths.project_root = instance.paths.project_root.resolve()
            if instance.gui_automation:
                instance.gui_automation.input_coords_file_path = (
                    instance.gui_automation.input_coords_file_path.resolve()
                )
                instance.gui_automation.copy_coords_file_path = (
                    instance.gui_automation.copy_coords_file_path.resolve()
                )

            return instance

        except ValidationError as e:
            raise CoreConfigurationError(f"Configuration validation failed: {e}") from e
        except Exception as e:
            raise CoreConfigurationError(f"Failed to load configuration: {e}") from e


# --- Logging Setup Function ---
# (Assuming setup_logging function exists elsewhere or needs to be defined/moved here)
_logging_configured = False


def setup_logging(config: AppConfig):
    """Configures logging based on AppConfig settings."""
    global _logging_configured
    if _logging_configured:
        # Prevent reconfiguring logging multiple times
        return

    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    # Get root logger
    root_logger = logging.getLogger()

    # Remove existing handlers added by this function to avoid duplication
    # Be careful if other parts of the system add handlers to root
    current_handlers = root_logger.handlers[:]
    for handler in current_handlers:
        if (
            isinstance(handler, (logging.StreamHandler, logging.FileHandler))
            and handler.formatter == formatter
        ):
            root_logger.removeHandler(handler)

    handlers = []

    # Console Handler
    if config.logging.log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    # File Handler
    if config.logging.log_file:
        try:
            log_dir = config.paths.logs
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / config.logging.log_file
            # Use RotatingFileHandler for larger logs potentially
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
            print(
                f"Logging configured. Logging to file: {log_path}"
            )  # Temp print for verification
        except Exception as e:
            # Log error to console if file logging fails
            print(
                f"ERROR: Failed to configure file logging to {config.logging.log_file}: {e}"
            )
            logging.error(
                f"Failed to configure file logging to {config.logging.log_file}: {e}",
                exc_info=True,
            )

    # Configure Root Logger only if handlers were successfully created
    if handlers:
        root_logger.setLevel(log_level)
        for handler in handlers:
            root_logger.addHandler(handler)

        # Adjust levels for noisy libraries if needed
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)

        logging.info(
            f"Logging configured. Level: {config.logging.level}, Console: {config.logging.log_to_console}, File: {config.logging.log_file or 'Disabled'}"
        )
        _logging_configured = True
    else:
        logging.warning("No logging handlers configured.")


# # Example Usage (for testing if run directly) - REMOVED/COMMENTED
# # Kept commented for reference during development, but should be removed for production.
# if __name__ == "__main__":
#     import traceback # Add traceback import for direct run test
#     logging.basicConfig(level=logging.INFO) # Basic config for direct run
#     try:
#         print("Attempting to load configuration...")
#         # Set dummy env var for testing
#         os.environ['DREAMOS_OPENAI__API_KEY'] = 'test_key_from_env' # Corrected delimiter
#         os.environ['DREAMOS_LOGGING__LEVEL'] = 'DEBUG' # Test env var override
#
#         # Load default config first (relies on BaseSettings defaults)
#         config = AppConfig.load()
#
#         # Setup logging based on loaded config
#         print(f"Initial loaded Log Level (from defaults/env): {config.logging.level}")
#         setup_logging(config)
#
#         # Print some loaded values
#         logging.info("Configuration loaded successfully.")
#         logging.debug(f"Project Root: {PROJECT_ROOT}")
#         logging.debug(f"Runtime Path: {config.paths.runtime}")
#         logging.debug(f"Log Path: {config.paths.logs}")
#         logging.info(f"Logging Level: {config.logging.level}")
#         logging.info(f"OpenAI API Key Set: {bool(config.openai.api_key)}")
#         # Be careful logging secrets, even SecretStr representation
#         # logging.debug(f"OpenAI Key: {config.openai.api_key}")
#         logging.info(f"ChatGPT Email Set: {bool(config.chatgpt_scraper.email)}")
#         logging.info(f"ChatGPT Password Set: {bool(config.chatgpt_scraper.password)}")
#
#         # Test accessing a nested value
#         logging.debug(f"Dreamscape Planner Model: {config.dreamscape.planner_agent.llm_model}")
#
#     except CoreConfigurationError as e:
#         logging.error(f"CONFIGURATION ERROR: {e}", exc_info=True)
#         print(f"CONFIGURATION ERROR: {e}")
#         traceback.print_exc() # Print full traceback on error
#     except Exception as e:
#         logging.error(f"An unexpected error occurred: {e}", exc_info=True)
#         print(f"UNEXPECTED ERROR: {e}")
#         traceback.print_exc()
