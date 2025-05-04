# core/config.py
import logging
from pathlib import Path
from typing import Any, List, Optional

import yaml
from pydantic import (
    BaseModel,
    Field,
    FilePath,
    SecretStr,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

# Adjusted imports to reflect new location within core
# REMOVED: Unused AgentBus import
# from .coordination.agent_bus import AgentBus
# REMOVED: Obsolete config_utils references
from .errors import ConfigurationError as CoreConfigurationError

# Define project root relative to this file (now three levels up to repo root)
# NOTE (Captain-Agent-5): Calculating PROJECT_ROOT based on __file__ location can be fragile.  # noqa: E501
# Consider using a marker file search or environment variable for more robustness.
# However, the PathsConfig allows overriding this value during initialization.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "runtime" / "config" / "config.yaml"

logger = logging.getLogger(__name__)

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
    copy_attempts: int = 2  # Add copy attempts config (for TASK_AGENT8-CONFIG-CURSORORCH-COPYATTEMPTS-001)  # noqa: E501

    # Add validators if needed, e.g., for path existence (though FilePath handles basic check)  # noqa: E501


# EDIT END


# EDIT START: Add Agent Activation Config Models
class AgentActivationConfig(BaseModel):
    worker_id_pattern: str = Field(
        ...,
        description="Regex pattern to match worker names (e.g., 'Worker-.*' or 'Worker-(1|3)')",  # noqa: E501
    )
    agent_module: str = Field(
        ...,
        description="Full module path to the agent class (e.g., 'dreamos.agents.agent2_infra_surgeon')",  # noqa: E501
    )
    agent_class: str = Field(
        ...,
        description="Name of the agent class within the module (e.g., 'Agent2InfraSurgeon')",  # noqa: E501
    )
    agent_id_override: Optional[str] = Field(
        None,
        description="Optional specific agent_id to assign, otherwise derived or default used.",  # noqa: E501
    )


class SwarmConfig(BaseModel):
    max_concurrent_tasks: int = 5
    agent_startup_delay: float = 1.0


# EDIT END


# Add placeholder for Azure Blob config within an Integrations model
class AzureBlobConfig(BaseModel):
    connection_string: Optional[SecretStr] = None
    container_name: Optional[str] = None


class IntegrationsConfig(BaseModel):
    azure_blob: Optional[AzureBlobConfig] = None
    # Add other integrations here, e.g., github, slack


# EDIT START: Add Monitoring Config Model
class MonitoringConfig(BaseModel):
    stats_interval: int = Field(
        60, description="Interval in seconds for logging stats."
    )


# EDIT END


# --- ADD Health Check Config ---
class HealthCheckConfig(BaseModel):
    expected_agent_ids: List[str] = Field(
        default_factory=lambda: [f"Agent-{i}" for i in range(1, 9)]
    )  # Default Agent-1 to Agent-8
    cursor_coords_path: str = "runtime/config/cursor_coords.json"  # Default path
    enable_cursor_status_check: bool = True
    enable_cursor_window_check: bool = True


# {{ EDIT START: Define placeholder OrchestratorConfig - MOVED EARLIER }}
class OrchestratorConfig(BaseModel):
    # Add fields relevant to orchestration/swarm management as needed
    pass  # Empty for now to resolve NameError


# {{ EDIT END }}


# Main Application Configuration Model
class AppConfig(BaseSettings):
    """Main application configuration loaded from environment variables and/or config file."""  # noqa: E501

    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    dreamscape: DreamscapeConfig = Field(default_factory=DreamscapeConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    chatgpt_scraper: ChatGPTScraperConfig = Field(default_factory=ChatGPTScraperConfig)
    gui_automation: GuiAutomationConfig = Field(default_factory=GuiAutomationConfig)
    # Use the moved OrchestratorConfig
    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
    swarm: SwarmConfig = Field(default_factory=SwarmConfig)
    integrations: IntegrationsConfig = Field(default_factory=IntegrationsConfig)
    # memory_channel: MemoryChannelConfig = Field(default_factory=MemoryChannelConfig) # Placeholder added, needs proper model/use
    health_checks: HealthCheckConfig = Field(
        default_factory=HealthCheckConfig
    )  # ADD health_checks field
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

    # Configuration loading behavior
    model_config = SettingsConfigDict(
        env_prefix="DREAMOS_",  # Example prefix: DREAMOS_OPENAI_API_KEY
        env_nested_delimiter="__",  # Example: DREAMOS_CHATGPT_SCRAPER__EMAIL
        env_file=".env",  # Default .env file to check
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields found in config sources
        yaml_file=DEFAULT_CONFIG_PATH,  # Pass default path to custom source
    )

    # EDIT START: Implement settings_customise_sources
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        # file_secret_settings if/when needed
        # file_secret_settings: PydanticBaseSettingsSource, # REMOVE COMMENT, ADD ARGUMENT
        file_secret_settings: PydanticBaseSettingsSource,  # ADDED BY AGENT-1
        # Add yaml_settings source parameter (though we instantiate it below)
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Define the priority order for loading settings sources."""
        return (
            init_settings,  # 1. Values passed during initialization
            env_settings,  # 2. Environment variables
            dotenv_settings,  # 3. Values from .env file
            file_secret_settings,  # 4. Values from secret files (if used) # ENSURE THIS IS PRESENT
            YamlConfigSettingsSource(settings_cls),  # 5. Values from config.yaml
            # Add file_secret_settings here if needed
        )

    # EDIT END

    # Ensure paths are absolute after loading (Pydantic v2 uses model_post_init)
    @model_validator(mode="after")
    def resolve_paths(self) -> "AppConfig":
        """Ensures all configured paths are absolute after validation."""
        if self.paths:
            self.paths.runtime = self.paths.runtime.resolve()
            self.paths.logs = self.paths.logs.resolve()
            self.paths.agent_comms = self.paths.agent_comms.resolve()
            self.paths.central_task_boards = self.paths.central_task_boards.resolve()
            self.paths.task_schema = self.paths.task_schema.resolve()
            self.paths.project_root = self.paths.project_root.resolve()
        if self.gui_automation:
            self.gui_automation.input_coords_file_path = (
                self.gui_automation.input_coords_file_path.resolve()
            )
            self.gui_automation.copy_coords_file_path = (
                self.gui_automation.copy_coords_file_path.resolve()
            )
        # Resolve log file path if relative
        if self.logging and self.logging.log_file:
            log_path = Path(self.logging.log_file)
            if not log_path.is_absolute():
                # Assume relative to paths.logs directory
                self.logging.log_file = str(self.paths.logs / log_path)
            else:
                self.logging.log_file = str(log_path.resolve())

        return self


# Configuration Error Exception
class ConfigurationError(CoreConfigurationError):
    """Custom exception for configuration errors specific to this module."""

    pass


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
                f"ERROR: Failed to configure file logging to {config.logging.log_file}: {e}"  # noqa: E501
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
            f"Logging configured. Level: {config.logging.level}, Console: {config.logging.log_to_console}, File: {config.logging.log_file or 'Disabled'}"  # noqa: E501
        )
        _logging_configured = True
    else:
        logging.warning("No logging handlers configured.")


# EDIT START: Add YamlConfigSettingsSource
class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """
    A settings source class that loads variables from a YAML file.
    Handles potential file not found errors.
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        yaml_file: Optional[Path] = None,
        yaml_file_encoding: Optional[str] = None,
    ):
        super().__init__(settings_cls)
        # Attempt to get path/encoding from model_config, fallback to defaults/passed args  # noqa: E501
        yaml_file_from_config = settings_cls.model_config.get("yaml_file")
        self.yaml_file = yaml_file or yaml_file_from_config or DEFAULT_CONFIG_PATH

        yaml_encoding_from_config = settings_cls.model_config.get("yaml_file_encoding")
        self.yaml_file_encoding = (
            yaml_file_encoding or yaml_encoding_from_config or "utf-8"
        )
        self.config = self._load_config()

        logger.debug(f"YamlConfigSettingsSource initialized for file: {self.yaml_file}")

    def _load_config(self) -> dict[str, Any]:
        if not self.yaml_file.exists():
            # Use logger if available, otherwise print
            msg = (
                f"YAML config file not found at {self.yaml_file}, skipping YAML source."
            )
            try:
                logger.warning(msg)
            except NameError:
                print(f"Warning: {msg}")
            return {}
        try:
            with open(self.yaml_file, "r", encoding=self.yaml_file_encoding) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            msg = f"Error loading YAML config from {self.yaml_file}: {e}"
            try:
                logger.error(msg)
            except NameError:
                print(f"Error: {msg}")
            # Depending on strictness, could raise error or return empty
            return {}

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        # This method is not strictly needed if __call__ loads the whole file
        # and pydantic handles the field mapping.
        # Kept for potential future field-specific logic from YAML.
        # Returning None indicates the source doesn't provide this specific field directly.
        return None, field_name, False

    def prepare_field_value(
        self, field_name: str, field: Any, value: Any, value_is_complex: bool
    ) -> Any:
        # Can add specific value preparations if needed
        return value

    def __call__(self) -> dict[str, Any]:
        return self.config


# --- Loading Function ---

_config: Optional[AppConfig] = None


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """Loads the application configuration, ensuring it's a singleton."""
    global _config
    if _config is None:
        try:
            # Pass the specified path (or None to use defaults) to the model init
            # It will be picked up by the YamlConfigSettingsSource if relevant
            yaml_path = (
                config_path or DEFAULT_CONFIG_PATH
            )  # Ensure path is used if provided # noqa: E501
            # Override model_config directly for this instance if path is provided
            # This is a bit hacky, ideally YamlConfigSettingsSource would handle this more cleanly # noqa: E501
            if config_path:
                _config = AppConfig(_settings_config_dict={"yaml_file": config_path})
            else:
                _config = AppConfig()

            # Ensure logging is set up after config is loaded
            setup_logging(_config)
            logger.info(
                f"Configuration loaded successfully. Project Root: {_config.paths.project_root}"
            )  # noqa: E501
        except Exception as e:
            # Use logger if possible, otherwise print
            msg = f"Failed to load application configuration: {e}"
            try:
                logger.critical(msg, exc_info=True)
            except NameError:  # Logger might not be configured yet
                print(f"CRITICAL ERROR: {msg}")
            raise ConfigurationError(msg) from e
    return _config


def get_config() -> AppConfig:
    """Returns the loaded configuration instance, loading it if necessary."""
    if _config is None:
        return load_config()
    return _config


# # Example Usage (for testing if run directly) - REMOVED/COMMENTED
# # Kept commented for reference during development, but should be removed for production.  # noqa: E501
# if __name__ == "__main__":
#     import traceback # Add traceback import for direct run test
#     logging.basicConfig(level=logging.INFO) # Basic config for direct run
#     try:
#         print("Attempting to load configuration...")
#         # Set dummy env var for testing
#         os.environ['DREAMOS_OPENAI__API_KEY'] = 'test_key_from_env' # Corrected delimiter  # noqa: E501
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
#         logging.debug(f"Dreamscape Planner Model: {config.dreamscape.planner_agent.llm_model}")  # noqa: E501
#
#     except CoreConfigurationError as e:
#         logging.error(f"CONFIGURATION ERROR: {e}", exc_info=True)
#         print(f"CONFIGURATION ERROR: {e}")
#         traceback.print_exc() # Print full traceback on error
#     except Exception as e:
#         logging.error(f"An unexpected error occurred: {e}", exc_info=True)
#         print(f"UNEXPECTED ERROR: {e}")
#         traceback.print_exc()
