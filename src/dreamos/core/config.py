"""
Core configuration management for the DreamOS application.

This module defines the Pydantic models for various configuration sections,
manages loading settings from YAML files and environment variables, and provides
centralized access to application configuration.
"""

# core/config.py
# EDIT START: Add print at the very beginning of the file
print("DEBUG: dreamos.core.config.py - Top of file executing", flush=True)
# EDIT END
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

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

# Define logger at module level
logger = logging.getLogger(__name__)

# Setup basic logging config if not already configured elsewhere (e.g., at entry point)
# logging.basicConfig(level=logging.INFO)


# --- Function to find project root robustly ---
def find_project_root_marker(marker: str = ".git") -> Path:
    """Find the project root by searching upwards for a marker file/directory."""
    current_dir = Path(__file__).resolve().parent
    while current_dir != current_dir.parent:
        if (current_dir / marker).exists():
            return current_dir
        current_dir = current_dir.parent
    raise FileNotFoundError(
        f"Project root marker '{marker}' not found starting from {__file__}"
    )


# --- Determine Project Root --- #
try:
    PROJECT_ROOT = find_project_root_marker()
    # EDIT START: Add print after PROJECT_ROOT determination
    print(
        f"DEBUG: dreamos.core.config.py - PROJECT_ROOT determined: {PROJECT_ROOT}",
        flush=True,
    )
    # EDIT END
except FileNotFoundError as e:
    logger.error(
        f"Failed to find project root automatically: {e}. Falling back to relative path."
    )
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    # EDIT START: Add print after fallback PROJECT_ROOT determination
    print(
        f"DEBUG: dreamos.core.config.py - PROJECT_ROOT fallback: {PROJECT_ROOT}",
        flush=True,
    )
    # EDIT END

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "runtime" / "config" / "config.yaml"
# EDIT START: Add print after DEFAULT_CONFIG_PATH determination
print(
    f"DEBUG: dreamos.core.config.py - DEFAULT_CONFIG_PATH: {DEFAULT_CONFIG_PATH}",
    flush=True,
)
# EDIT END

# --- Pydantic Models for Config Structure ---

# Import moved config models
from dreamos.automation.config import GuiAutomationConfig
from dreamscape.config import DreamscapeConfig


class LoggingConfig(BaseModel):
    level: str = Field("INFO", description="Logging level (e.g., DEBUG, INFO, WARNING)")
    log_file: Optional[str] = Field(
        None, description="Path to log file relative to runtime/logs, if enabled."
    )
    log_to_console: bool = Field(True, description="Whether to log to console.")

    def resolve_log_dir(self, project_root: Path) -> Path:
        """Resolves the log directory path, creating it if necessary."""
        # Use the passed project_root argument directly
        root = project_root

        # Safely access log_dir attribute
        custom_log_dir_value = getattr(self, "log_dir", None)

        if custom_log_dir_value:
            log_path = Path(custom_log_dir_value)
            if log_path.is_absolute():
                resolved_path = log_path
            else:
                resolved_path = (root / custom_log_dir_value).resolve()
            # Ensures creation happens before returning (commented out, handled by _ensure_dirs_exist)
            # resolved_path.mkdir(parents=True, exist_ok=True)
            return resolved_path
        else:
            # Default log directory
            default_path = (root / "runtime" / "logs").resolve()
            # default_path.mkdir(parents=True, exist_ok=True) # (commented out, handled by _ensure_dirs_exist)
            return default_path


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
    # Paths identified during configuration management refactoring (TASK-REFACTOR-CONFIG-PATHS-001)
    # Define path for cursor state file (used in dreamos.services.utils.cursor)
    cursor_state_path: Optional[Path] = Field(
        None, description="Path to the cursor state JSON file."
    )
    # Define path for task memory layer file (used in dreamos.memory.layers.task_memory_layer)
    task_memory_path: Optional[Path] = Field(
        None, description="Path to the task memory JSON file."
    )
    # Define path for failed prompt archive (used in dreamos.services.failed_prompt_archive)
    failed_prompt_archive_path: Optional[Path] = Field(
        None, description="Path to the failed prompt archive JSON file."
    )
    # Define path for persistent memory (used in legacy dreamos.chat_engine.feedback_engine)
    persistent_memory_path: Optional[Path] = Field(
        None,
        description="Path to the persistent memory JSON file (legacy FeedbackEngine).",
    )
    # Define path for feedback log (used in legacy dreamos.chat_engine.feedback_engine)
    feedback_log_path: Optional[Path] = Field(
        None, description="Path to the feedback log JSON file (legacy FeedbackEngine)."
    )
    # Define path for context memory (used in legacy dreamos.chat_engine.feedback_engine)
    context_memory_path: Optional[Path] = Field(
        None,
        description="Path to the context memory JSON file (legacy FeedbackEngine).",
    )
    # Define path for GUI validation output (used in tools/validation/validate_gui_coords.py)
    gui_validation_output_path: Optional[Path] = Field(
        None, description="Path for GUI coordinate validation results JSON."
    )
    # Define path for scanner cache (used in dreamos.tools.analysis.project_scanner)
    scanner_cache_path: Optional[Path] = Field(
        None, description="Path to the project scanner dependency cache JSON file."
    )
    # Define path for analysis output (used in dreamos.tools.analysis.project_scanner)
    analysis_output_path: Optional[Path] = Field(
        None, description="Path for the main project analysis JSON report."
    )
    # Define path for ChatGPT context output (used in dreamos.tools.analysis.project_scanner)
    chatgpt_context_output_path: Optional[Path] = Field(
        None, description="Path for the ChatGPT context JSON export."
    )
    # Define path for completed tasks (used in dreamos.reporting.scoring_analyzer)
    completed_tasks_path: Optional[Path] = Field(
        None, description="Path to the completed tasks JSON file for reporting."
    )

    # NOTE: GUI coords input path is handled under GuiAutomationConfig below


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

    # --- EDIT START: Add thea_copy nested model ---
    class TheaCopyConfig(BaseModel):
        anchor_image_path: str = "assets/thea_reply_anchor.png"
        click_offset_x: int = 50
        click_offset_y: int = 50
        confidence: float = 0.9
        retries: int = 2
        delay_between_actions: float = 0.1

    thea_copy: TheaCopyConfig = Field(default_factory=TheaCopyConfig)
    # --- EDIT END ---

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
    active_agents_config_path: Optional[str] = Field(
        None, description="Path to JSON file listing active agents and their configs"
    )
    # Define configuration for active agents, loaded from external JSON
    active_agents: List[AgentActivationConfig] = Field(
        default_factory=list,
        description="List of agent activation configurations, typically loaded from file.",
    )


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


# EDIT START: Add PyAutoGUIBridgeConfig Model (as proposed in API doc)
class PyAutoGUIBridgeConfig(BaseModel):
    default_confidence: float = Field(
        0.9, description="Default confidence for image matching."
    )
    default_timeout_seconds: float = Field(
        10.0, description="Default timeout for finding elements."
    )
    default_retry_attempts: int = Field(
        3, description="Default retry attempts for failing PyAutoGUI actions."
    )
    default_retry_delay_seconds: float = Field(
        0.5, description="Default delay between retries."
    )
    type_interval_seconds: float = Field(
        0.01, description="Default interval between keystrokes for typing."
    )
    image_assets_path: str = Field(
        "runtime/assets/bridge_gui_snippets/",
        description="Path to image assets for the bridge, relative to project root.",
    )
    clipboard_wait_timeout: float = Field(
        5.0,
        description="Timeout in seconds to wait for clipboard content to update after a copy action.",
    )
    pause_before_action: float = Field(
        0.1,
        description="Default pause in seconds before performing a GUI action like click.",
    )
    # Add other specific settings as needed


# EDIT END


# --- Moved YAML Source Class Definition ---
# Define YamlConfigSettingsSource BEFORE AppConfig uses it in settings_customise_sources
class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """
    A Pydantic settings source that loads configuration from a YAML file.

    This class is used in conjunction with `AppConfig.settings_customise_sources`
    to enable loading application settings from a specified YAML configuration file.
    It handles finding the YAML file (with priority to environment variables)
    and parsing its content.
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        yaml_file: Optional[
            Path
        ] = None,  # This is the default path from settings_customise_sources
        yaml_file_encoding: Optional[str] = None,
    ):
        super().__init__(settings_cls)
        # Store the default YAML file path and encoding provided at instantiation
        self.default_config_file_path: Optional[Path] = yaml_file
        self.default_config_file_encoding: Optional[str] = yaml_file_encoding
        # logger.debug(f"YamlConfigSettingsSource initialized with default_yaml_file: {self.default_config_file_path}")

    def _load_config(self) -> dict[str, Any]:
        # Determine the config file to load.
        # Priority:
        # 1. DREAMOS_CONFIG_PATH environment variable (set by AppConfig.load for specific files).
        # 2. self.default_config_file_path (provided during __init__, typically DEFAULT_CONFIG_PATH).

        env_config_path_str = os.environ.get("DREAMOS_CONFIG_PATH")

        load_path: Optional[Path] = None
        # Use the instance's default encoding if set, otherwise fallback to utf-8
        encoding_to_use: str = self.default_config_file_encoding or "utf-8"

        if env_config_path_str:
            load_path = Path(env_config_path_str)
            # logger.debug(f"YamlConfigSettingsSource: Using DREAMOS_CONFIG_PATH env var: {load_path}")
        elif self.default_config_file_path:
            load_path = self.default_config_file_path
            # logger.debug(f"YamlConfigSettingsSource: Using default_config_file_path: {load_path}")
        else:
            # This case should ideally not be reached if DEFAULT_CONFIG_PATH is always valid
            # and AppConfig.load ensures a path when calling the AppConfig constructor.
            logger.warning(
                "YamlConfigSettingsSource: No YAML file path specified (no env var, no default path from init). Returning empty dict."
            )
            return {}

        # Ensure load_path is a Path object if it was derived from string (already handled by Path() above)
        # if not isinstance(load_path, Path): # This check is redundant now
        #     load_path = Path(load_path)

        if not load_path.exists():
            logger.warning(
                f"YamlConfigSettingsSource: Config file '{load_path}' not found."
            )
            raise ConfigurationError(f"Config file not found: {load_path}")

        try:
            with open(load_path, "r", encoding=encoding_to_use) as f:
                config_data = yaml.safe_load(f)

            if config_data is None:  # Handle empty YAML file case
                logger.warning(
                    f"Config file '{load_path}' is empty. Returning empty dict."
                )
                return {}

            if not isinstance(config_data, dict):
                logger.error(
                    f"Config file '{load_path}' content is not a valid dictionary."
                )
                raise ConfigurationError(
                    f"Config file is not a valid dictionary: {load_path}"
                )

            logger.info(f"Loaded configuration from YAML file: {load_path}")
            return config_data
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file '{load_path}': {e}", exc_info=True)
            raise ConfigurationError(
                f"Failed to load config due to YAML parsing error in {load_path}: {e}"
            ) from e
        except ConfigurationError:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error loading YAML file '{load_path}': {e}", exc_info=True
            )
            raise ConfigurationError(
                f"Unexpected error loading config file {load_path}: {e}"
            ) from e

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        # This method is not strictly needed if __call__ loads the whole file
        # and pydantic handles the field mapping.
        # Kept for potential future field-specific logic from YAML.
        # Returning None indicates the source doesn't provide this specific field directly.
        config = self._load_config()
        field_value = config.get(field_name)
        return field_value, field_name, False  # Assume value isn't complex here

    def prepare_field_value(
        self, field_name: str, field: Any, value: Any, value_is_complex: bool
    ) -> Any:
        # Can add specific value preparations if needed
        return value

    def __call__(self) -> dict[str, Any]:
        """Load and return the entire config dictionary from the YAML file."""
        return self._load_config()


# --- End Moved YAML Source Class Definition ---


# --- Memory Maintenance Policies (Moved for TEST-002) ---
# Base model for common policy fields
class BasePolicyConfig(BaseModel):
    enabled: bool = Field(True, description="Whether this policy is active.")
    file_pattern: Optional[str] = Field(
        None,
        description="Glob pattern to match specific files (e.g., '*.log', 'chat_history*'). None matches all.",
    )
    compress_after_processing: bool = Field(
        False,
        description="Compress the output file (e.g., with zlib) after processing.",
    )
    delete_original_after_processing: bool = Field(
        False, description="Delete the original file after successful processing."
    )


class CompactionPolicyConfig(BasePolicyConfig):
    compaction_strategy: str = Field(
        "default",
        description="Strategy for compaction (e.g., 'default', 'json_collate').",
    )
    max_file_size_kb: Optional[int] = Field(
        None, description="Trigger compaction if file size exceeds this limit."
    )
    max_entry_count: Optional[int] = Field(
        None, description="Trigger compaction if entry count exceeds this limit."
    )
    min_age_hours: Optional[float] = Field(
        None, description="Only compact files older than this many hours."
    )


# RENAME SummarizationPolicyConfig to SummarizationConfig
class SummarizationConfig(BasePolicyConfig):  # Renamed from SummarizationPolicyConfig
    trigger_threshold_entries: int = Field(
        200, description="Minimum entries before summarization is triggered."
    )
    summarize_n_oldest: int = Field(
        50, description="Number of oldest entries to summarize in one go."
    )
    min_chunk_size: int = Field(
        10,
        description="Minimum number of entries required to form a chunk for summarization.",
    )
    summarization_model_name: Optional[str] = Field(
        None,
        description="Specific AI model to use for summarization (overrides default).",
    )
    target_summary_length_tokens: Optional[int] = Field(
        None, description="Target length for the summary."
    )
    summarization_prompt_template: Optional[str] = Field(
        None, description="Custom prompt template name for summarization."
    )
    # REMOVED: type field as it might not belong here if SummarizationConfig is the intended name
    # type: str = Field("default", description="Policy type identifier, mainly for config clarity.") # Added based on test usage
    summarization_chunk_size: int = Field(
        50, description="Alias/duplicate for summarize_n_oldest for compatibility?"
    )  # Added based on test usage


# Config for agent-specific overrides - Update reference
class AgentMemoryPolicyOverride(BaseModel):
    compaction_policies: List[CompactionPolicyConfig] = Field(default_factory=list)
    summarization_policies: List[SummarizationConfig] = Field(
        default_factory=list
    )  # Updated reference


# Main config block for memory maintenance service - Update reference
class MemoryMaintenanceConfig(BaseModel):
    enabled: bool = Field(True, description="Enable the memory maintenance service.")
    schedule_interval_minutes: int = Field(
        60, description="How often the maintenance job runs."
    )
    snapshot_base_path_override: Optional[str] = Field(
        None, description="Override the base path for agent memory snapshots."
    )
    default_compaction_policies: List[CompactionPolicyConfig] = Field(
        default_factory=list
    )
    default_summarization_policies: List[SummarizationConfig] = Field(
        default_factory=list
    )  # Updated reference
    agent_policy_overrides: Dict[str, AgentMemoryPolicyOverride] = Field(
        default_factory=dict
    )


# --- End Memory Maintenance Policies ---


# --- EDIT START: Add AgentPointsSystemConfig ---
class AgentPointsSystemConfig(BaseModel):
    """Configuration for the agent points system."""

    point_values: Dict[str, int] = Field(
        default_factory=dict,
        description="Specific point values for various event keys.",
    )
    # --- Add new fields for captaincy check ---
    captaincy_check_interval_minutes: int = Field(
        15, description="How often (in minutes) to check for captaincy changes."
    )
    captain_status_file: str = Field(
        "runtime/governance/current_captain.txt",
        description="Path relative to project root to store the current captain's ID.",
    )
    # --- End new fields ---

    class Config:
        anystr_strip_whitespace = True
        extra = "ignore"


# --- EDIT END ---


# --- AppConfig Definition ---
class AppConfig(BaseSettings):
    """Main application configuration loaded from environment variables and/or config file."""  # noqa: E501

    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    dreamscape: DreamscapeConfig = Field(default_factory=DreamscapeConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    chatgpt_scraper: ChatGPTScraperConfig = Field(default_factory=ChatGPTScraperConfig)
    gui_automation: Optional[GuiAutomationConfig] = None
    pyautogui_bridge: PyAutoGUIBridgeConfig = Field(
        default_factory=PyAutoGUIBridgeConfig
    )
    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
    swarm: SwarmConfig = Field(default_factory=SwarmConfig)
    integrations: IntegrationsConfig = Field(default_factory=IntegrationsConfig)
    health_checks: HealthCheckConfig = Field(
        default_factory=HealthCheckConfig
    )  # ADD health_checks field
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    memory_maintenance: MemoryMaintenanceConfig = Field(
        default_factory=MemoryMaintenanceConfig
    )  # This reference is now correct

    # --- EDIT START: Add agent_points_system field ---
    agent_points_system: Optional[AgentPointsSystemConfig] = Field(
        None, description="Configuration for the Agent Points System"
    )
    # --- EDIT END ---

    project_root_internal: Path = Field(exclude=True, default_factory=Path.cwd)

    # Configuration loading behavior
    model_config = SettingsConfigDict(
        env_prefix="DREAMOS_",  # Prefix for environment variables
        env_nested_delimiter="__",
        validate_assignment=True,
        extra="ignore",  # Allow extra fields in config files initially, then validate
        # Removed yaml_file from here as it's handled by settings_customise_sources
        # yaml_file=DEFAULT_CONFIG_PATH, # Default YAML file to load
        # yaml_file_encoding='utf-8',
    )

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
        """Customizes the sources for loading settings, adding YAML file support."""
        # logger.debug(f"AppConfig.settings_customise_sources called for {settings_cls}")
        # logger.debug(f"AppConfig.model_config: {settings_cls.model_config}")

        # Get yaml_file from model_config (potentially set via _settings_config_dict in __init__)
        # or from an explicit field in model_config if defined there.
        yaml_file_from_model_config_str = settings_cls.model_config.get("yaml_file")
        # logger.debug(f"Yaml file from model_config.get('yaml_file'): {yaml_file_from_model_config_str}")

        path_for_yaml_source: Optional[Path] = None
        if yaml_file_from_model_config_str:
            path_for_yaml_source = Path(yaml_file_from_model_config_str)
            # logger.debug(f"Using yaml_file from model_config: {path_for_yaml_source}")
        elif (
            DEFAULT_CONFIG_PATH
        ):  # Fallback to module-level default if nothing in model_config
            path_for_yaml_source = Path(DEFAULT_CONFIG_PATH)
            # logger.debug(f"Using module-level DEFAULT_CONFIG_PATH: {path_for_yaml_source}")
        else:
            # logger.debug("No yaml_file in model_config and no DEFAULT_CONFIG_PATH.")
            pass  # path_for_yaml_source remains None

        # Default encoding
        yaml_encoding = settings_cls.model_config.get("yaml_file_encoding", "utf-8")

        # logger.debug(f"Final path for YamlConfigSettingsSource: {path_for_yaml_source}, encoding: {yaml_encoding}")

        return (
            init_settings,  # Values provided to __init__ directly (highest priority after custom sources)
            env_settings,  # Environment variables
            dotenv_settings,  # .env file
            YamlConfigSettingsSource(  # Our custom YAML source
                settings_cls,
                yaml_file=path_for_yaml_source,
                yaml_file_encoding=yaml_encoding,
            ),
            file_secret_settings,  # Secrets files (lowest priority among file/env based)
        )

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

    @model_validator(mode="before")
    @classmethod
    def _determine_project_root(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Update reference from _project_root to project_root_internal
            if "config_file_path" in data:
                config_file = Path(data["config_file_path"]).resolve()
                if "runtime/config" in str(config_file.parent):
                    # Set the internal field name
                    data["project_root_internal"] = config_file.parent.parent.parent
                else:
                    data["project_root_internal"] = config_file.parent  # Fallback
            else:
                data["project_root_internal"] = Path.cwd()
            # Update log message if desired
            logger.info(
                f"Determined project root (internal): {data['project_root_internal']}"
            )
        return data

    @model_validator(mode="after")
    def _inject_project_root(self) -> "AppConfig":
        """Injects the determined project root into nested models."""
        # Update references from _project_root to project_root_internal
        if hasattr(
            self.paths, "_project_root"
        ):  # Check if nested model expects old name (should be updated too ideally)
            # Ideally, nested models also wouldn't expect leading underscore
            # Assuming PathsConfig might still need project_root internally:
            self.paths.project_root = (
                self.project_root_internal
            )  # Inject into the public field
        else:
            # If PathsConfig has been updated to use project_root_internal or similar:
            # self.paths.project_root_internal = self.project_root_internal
            # For now, inject into the public field defined in PathsConfig
            self.paths.project_root = self.project_root_internal

        if hasattr(
            self.logging, "_project_root"
        ):  # Check if LoggingConfig expects old name
            # self.logging._project_root = self.project_root_internal # Original pattern, but _project_root isn't defined on LoggingConfig
            # LoggingConfig needs project_root passed to its resolve_log_dir method
            # This injection logic might be redundant if resolve_log_dir uses the main config's root correctly.
            # Keep for now, but review nested models.
            pass  # No direct field injection needed here based on current LoggingConfig structure

        # Inject into other nested configs as needed
        self._ensure_dirs_exist()  # Call ensure_dirs after root is set
        return self

    @classmethod
    def load(cls, config_file: Optional[str] = None) -> "AppConfig":
        """Loads configuration from a YAML file."""
        config_path = None
        if config_file:
            config_path = Path(config_file)
            if not config_path.is_absolute():
                # Assume relative to CWD if not absolute? Or project root?
                # Let's assume CWD for now, but project root might be better
                config_path = Path.cwd() / config_file

            if not config_path.exists():
                raise CoreConfigurationError(f"Config file not found: {config_path}")
        else:
            # Add logic to search for default config files if needed
            logger.warning("No config file specified, using default values.")
            # Returning default model might be okay if defaults are sufficient
            # return cls() # This would use defaults
            raise CoreConfigurationError("Config file path must be provided.")

        try:
            import yaml  # Import here to avoid making it a hard dependency if not used

            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)
            if not isinstance(config_data, dict):
                raise CoreConfigurationError("Config file is not a valid dictionary.")

            # Pass path to validator
            config_data["config_file_path"] = str(config_path)

            # Potential issue: If validation fails, AppConfig might not be fully initialized
            # Consider if ensure_dirs should happen *after* full validation or be more resilient
            instance = cls(**config_data)
            # self._ensure_dirs_exist() # Moved to validator
            return instance
        except ImportError:
            raise CoreConfigurationError("PyYAML is required to load config files.")
        except Exception as e:
            raise CoreConfigurationError(
                f"Failed to load config from {config_path}: {e}"
            ) from e

    def _ensure_dirs_exist(self):
        """Ensure necessary directories exist based on config."""
        try:
            # Update reference from _project_root to project_root_internal
            log_dir = self.logging.resolve_log_dir(self.project_root_internal)
            log_dir.mkdir(parents=True, exist_ok=True)
            # Ensure other key directories exist
            # Assuming self.paths.resolve_relative_path exists and works correctly
            # runtime_path = self.paths.resolve_relative_path("runtime") # Use helper
            # Assuming resolve_relative_path isn't defined, use direct path construction
            runtime_path = self.project_root_internal / self.paths.runtime
            runtime_path.mkdir(parents=True, exist_ok=True)
            # Update path construction if resolve_relative_path exists or logic differs
            (runtime_path / "tasks").mkdir(parents=True, exist_ok=True)
            # ... add others as needed (agent_state, mailboxes etc.)
        except Exception as e:
            logger.error(f"Error ensuring directories exist: {e}", exc_info=True)


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
            log_dir = config.logging.resolve_log_dir(config.project_root_internal)
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
