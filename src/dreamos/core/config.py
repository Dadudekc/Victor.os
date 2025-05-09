"""
Core configuration management for the DreamOS application.

This module defines the Pydantic models for various configuration sections,
manages loading settings from YAML files and environment variables, and provides
centralized access to application configuration.
"""

# core/config.py
# EDIT START: Add print at the very beginning of the file
print("DEBUG_CONFIG: Top of dreamos.core.config.py")
# EDIT END
import logging
print("DEBUG_CONFIG: Imported logging")
import os
print("DEBUG_CONFIG: Imported os")
import threading
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

import yaml
from pydantic import (
    BaseModel,
    Field,
    SecretStr,
)
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

print("DEBUG_CONFIG: Before importing .errors", flush=True)
# Adjusted imports to reflect new location within core
# REMOVED: Unused AgentBus import
# from .coordination.agent_bus import AgentBus
# REMOVED: Obsolete config_utils references
# {{ EDIT START }}
from . import errors as appconfig_errors
# {{ EDIT END }}

# EDIT: Add DreamscapeConfig import here
from dreamscape.config import DreamscapeConfig

# Guarded import for GuiAutomationConfig
if TYPE_CHECKING:
    from dreamos.automation.config import GuiAutomationConfig

# Define logger at module level
logger = logging.getLogger(__name__)

# Setup basic logging config if not already configured elsewhere (e.g., at entry point)
# logging.basicConfig(level=logging.INFO)

# ADDED: Global config variable and lock with forward reference for AppConfig
_config: Optional["AppConfig"] = None
_config_lock = threading.Lock()
_logging_configured = False  # Flag to prevent duplicate logging setup


# --- Function to find project root robustly ---
print("DEBUG_CONFIG: Before find_project_root_marker definition")
def find_project_root_marker(marker: str = ".git") -> Path:
    """Finds the project root by searching upwards for a marker file/directory."""
    current_path = Path(__file__).resolve()
    # logger.debug(f"Starting root search from: {current_path}")
    while current_path != current_path.parent:
        # logger.debug(f"Checking for marker in: {current_path}")
        if (current_path / marker).exists():
            # logger.debug(f"Found project root marker '{marker}' at: {current_path}")
            return current_path
        current_path = current_path.parent
    # Fallback or error if marker not found
    logger.warning(
        f"Project root marker '{marker}' not found starting from {Path(__file__).resolve()}. Falling back to CWD."
    )
    return Path.cwd()  # Or raise FileNotFoundError("Project root marker not found.")
print("DEBUG_CONFIG: After find_project_root_marker definition")


# --- Determine Project Root --- #
print("DEBUG_CONFIG: Before PROJECT_ROOT determination")
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
print("DEBUG_CONFIG: After PROJECT_ROOT determination, before DEFAULT_CONFIG_PATH")
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "runtime" / "config" / "config.yaml"
print(f"DEBUG_CONFIG: DEFAULT_CONFIG_PATH set to {DEFAULT_CONFIG_PATH}")
# EDIT START: Add print after DEFAULT_CONFIG_PATH determination
print(
    f"DEBUG: dreamos.core.config.py - DEFAULT_CONFIG_PATH: {DEFAULT_CONFIG_PATH}",
    flush=True,
)
# EDIT END

# --- Pydantic Models for Config Structure ---

# Import moved config models
# REMOVED: from dreamscape.config import DreamscapeConfig # Moved later


print("DEBUG_CONFIG: Before LoggingConfig definition")
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
print("DEBUG_CONFIG: After LoggingConfig definition, before PathsConfig")


class PathsConfig(BaseModel):
    runtime: Path = Field(
        PROJECT_ROOT / "runtime", description="Path to the runtime directory"
    )
    logs: Path = Field(
        PROJECT_ROOT / "runtime" / "logs", description="Path to the logs directory"
    )
    performance_log_path: Optional[Path] = Field(
        default=None, # Or set a default like PROJECT_ROOT / "runtime" / "logs" / "performance.jsonl"
        description="Path for the PerformanceLogger output file relative to project root."
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
    # EDIT START: Add new paths for scraper with defaults
    chrome_profiles_base_dir: Path = Field(
        PROJECT_ROOT / "runtime" / "chrome_profiles",
        description="Base directory for Chrome user profiles."
    )
    cookies_base_dir: Path = Field(
        PROJECT_ROOT / "runtime" / "cookies",
        description="Base directory for storing cookies."
    )
    scraper_content_logs_base_dir: Path = Field(
        PROJECT_ROOT / "runtime" / "scraper_logs" / "chat_mate",
        description="Base directory for scraper content logs for ChatMate."
    )
    webdrivers_cache_base_dir: Path = Field(
        PROJECT_ROOT / "runtime" / "webdrivers_cache",
        description="Base directory for caching webdrivers."
    )
    # EDIT END
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

print("DEBUG_CONFIG: After PathsConfig definition, before OpenAIConfig")


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
# class GuiAutomationConfig(BaseModel): # Starting from here, commented out / to be deleted
#     target_window_title: str = "Cursor"  # Default to common IDE name
#     input_coords_file_path: FilePath = Path(
#         PROJECT_ROOT / "runtime/config/cursor_agent_coords.json"
#     )
#     copy_coords_file_path: FilePath = Path(
#         PROJECT_ROOT / "runtime/config/cursor_agent_copy_coords.json"
#     )
#     recalibration_retries: int = 1
#     min_pause_seconds: float = 0.10
#     max_pause_seconds: float = 0.25
#     random_offset_pixels: int = 3
#     type_interval_seconds: float = 0.01  # Add typing interval
#     retry_attempts: int = 3  # Add retry attempts
#     retry_delay_seconds: float = 0.5  # Add retry delay
#     copy_attempts: int = 2  # Add copy attempts config (for TASK_AGENT8-CONFIG-CURSORORCH-COPYATTEMPTS-001)  # noqa: E501
#
#     # --- EDIT START: Add thea_copy nested model ---
#     class TheaCopyConfig(BaseModel):
#         anchor_image_path: str = "assets/thea_reply_anchor.png"
#         click_offset_x: int = 50
#         click_offset_y: int = 50
#         confidence: float = 0.9
#         retries: int = 2
#         delay_between_actions: float = 0.1
#
#     thea_copy: TheaCopyConfig = Field(default_factory=TheaCopyConfig)
#     # --- EDIT END ---


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
            raise appconfig_errors.exceptions.ConfigurationError(f"Config file not found: {load_path}")

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
                raise appconfig_errors.exceptions.ConfigurationError(
                    f"Config file is not a valid dictionary: {load_path}"
                )

            logger.info(f"Loaded configuration from YAML file: {load_path}")
            return config_data
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file '{load_path}': {e}", exc_info=True)
            raise appconfig_errors.exceptions.ConfigurationError(
                f"Failed to load config due to YAML parsing error in {load_path}: {e}"
            ) from e
        except appconfig_errors.exceptions.ConfigurationError:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error loading YAML file '{load_path}': {e}", exc_info=True
            )
            raise appconfig_errors.exceptions.ConfigurationError(
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
print("DEBUG_CONFIG: After YamlConfigSettingsSource, before load_config function")


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


# EDIT: Define Enums directly in this file
class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class OperatingMode(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    PRODUCTION = "PRODUCTION"
    TESTING = "TESTING"


# --- AppConfig Definition ---
print("DEBUG_CONFIG: Before AppConfig class definition")
class AppConfig(BaseSettings):
    """Main application configuration loaded from environment variables and/or config file."""
    print("DEBUG_CONFIG: Inside AppConfig class body", flush=True)

    # MOVED all custom type imports here
    # Imports are now handled outside class or at bottom of file

    # {{ EDIT START: Problematic 'from . import errors' line removed from this spot }}
    # The line "from . import errors # Import the errors package" was previously here.
    # It has been removed to resolve a Pydantic UserError.
    # The 'errors' module is imported at the top level as 'appconfig_errors'.
    # {{ EDIT END }}
    # REMOVED: Unused AgentBus import
    # from .coordination.agent_bus import AgentBus
    # REMOVED: Obsolete config_utils references
    # MOVED: from . import errors as appconfig_errors # Commented out here

    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    # EDIT START: Add cursor_executable_path to AppConfig
    cursor_executable_path: Optional[str] = Field(
        r"C:\\Program Files\\Cursor\\Cursor.exe",
        description="Path to the Cursor executable."
    )
    # EDIT END
    # Restore dreamscape field
    dreamscape: 'DreamscapeConfig' = Field(default_factory=lambda: DreamscapeConfig())
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    chatgpt_scraper: ChatGPTScraperConfig = Field(default_factory=ChatGPTScraperConfig)
    # Restore gui_automation field
    gui_automation: Optional['GuiAutomationConfig'] = None # MODIFIED: Forward ref hint
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
        env_file=".env",  # Default .env file
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from config sources
        # Added: customize sources to include YAML first, then env vars, then .env
        # The order determines precedence (last one wins for overlapping keys)
        # Removed: settings_show_yaml_error (not a direct SettingsConfigDict key)
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Determine the config file path (from env var or default)
        # Ensure PROJECT_ROOT is available at this point
        config_file_env = os.getenv(f"{cls.model_config['env_prefix']}CONFIG_PATH")

        # Use the resolved DEFAULT_CONFIG_PATH which is based on PROJECT_ROOT
        config_file_path_to_load = (
            Path(config_file_env) if config_file_env else DEFAULT_CONFIG_PATH
        )

        return (
            init_settings,
            YamlConfigSettingsSource(
                settings_cls=settings_cls,
                yaml_file=config_file_path_to_load, # Use the determined path
                yaml_file_encoding="utf-8",
            ),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    @classmethod
    def load(cls, config_file: Optional[str] = None) -> "AppConfig":
        global _config
        global _logging_configured # Access the global flag

        with _config_lock:
            # If a specific config_file is provided, set it as an environment variable
            # so that settings_customise_sources can pick it up.
            # This allows overriding the default config path for this specific load() call.
            original_env_config_path = os.getenv(f"{cls.model_config['env_prefix']}CONFIG_PATH")
            if config_file:
                os.environ[f"{cls.model_config['env_prefix']}CONFIG_PATH"] = str(Path(config_file).resolve())
            elif original_env_config_path: # If env var was already set, respect it
                os.environ[f"{cls.model_config['env_prefix']}CONFIG_PATH"] = str(Path(original_env_config_path).resolve())
            else: # Otherwise, ensure it's set to the default for this load operation
                os.environ[f"{cls.model_config['env_prefix']}CONFIG_PATH"] = str(DEFAULT_CONFIG_PATH.resolve())


            try:
                logger.info(f"Loading AppConfig from: {os.getenv(f'{cls.model_config['env_prefix']}CONFIG_PATH')}")
                instance = cls() # This will trigger Pydantic's loading logic
                instance.project_root_internal = PROJECT_ROOT # Set the resolved project root

                # Perform path resolutions after loading
                instance.paths.runtime = (
                    instance.project_root_internal / instance.paths.runtime
                ).resolve()
                instance.paths.logs = (
                    instance.project_root_internal / instance.paths.logs
                ).resolve()

                # EDIT START: Resolve all other optional paths if they are set
                for field_name, field_type in instance.paths.model_fields.items():
                    if field_name in ["runtime", "logs", "project_root", "task_schema"]: # Already handled or absolute
                        continue
                    path_value = getattr(instance.paths, field_name)
                    if path_value and isinstance(path_value, (str, Path)): # Check if it's a path type
                        original_path_str = str(path_value) # For logging
                        if isinstance(path_value, str): # If loaded as string from YAML
                            path_value = Path(path_value)

                        if not path_value.is_absolute():
                            resolved_path = (instance.project_root_internal / path_value).resolve()
                            setattr(instance.paths, field_name, resolved_path)
                            logger.debug(f"Resolved relative path for {field_name} (originally '{original_path_str}'): {resolved_path}")
                        # If it's already a Path object and absolute (like our new defaults), no change needed by this if block.
                # EDIT END


                _config = instance

                # Initialize logging only once after config is loaded
                # and only if it hasn't been configured yet by an external entry point.
                # The `_logging_configured` flag prevents re-configuration if an
                # entry point (like a CLI tool) has already set up logging.
                if not _logging_configured:
                    setup_logging(instance)
                    _logging_configured = True # Mark as configured
                else:
                    logger.debug("Logging already configured by entry point. Skipping AppConfig's setup_logging.")


                return instance
            except Exception as e:
                # Log the error with traceback for detailed debugging
                logger.critical(f"Failed to load config from {os.getenv(f'{cls.model_config['env_prefix']}CONFIG_PATH')}: {e}", exc_info=True)
                raise appconfig_errors.ConfigurationError(
                    f"Failed to load application configuration from {os.getenv(f'{cls.model_config['env_prefix']}CONFIG_PATH')}: {e}"
                ) from e
            finally:
                # Restore original environment variable if it was changed
                if original_env_config_path:
                    os.environ[f"{cls.model_config['env_prefix']}CONFIG_PATH"] = original_env_config_path
                elif config_file: # If we set it and there wasn't one before
                    del os.environ[f"{cls.model_config['env_prefix']}CONFIG_PATH"]


def setup_logging(config: AppConfig):
    global _logging_configured
    if _logging_configured: # Check again to be absolutely sure
        logger.debug("setup_logging called but logging already configured. Skipping.")
        return

    # Ensure the log directory exists
    log_dir = config.logging.resolve_log_dir(config.paths.project_root) # Pass project_root
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        # Fallback to a very basic console logger if dir creation fails
        logging.basicConfig(level=logging.WARNING)
        logger.error(f"Failed to create log directory {log_dir}: {e}. Using basic console logging.")
        _logging_configured = True # Mark as configured to avoid retry loops
        return


    log_level_str = config.logging.level.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    handlers: List[logging.Handler] = []
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    if config.logging.log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    if config.logging.log_file:
        # Use the resolved log_dir from LoggingConfig
        file_handler = logging.FileHandler(log_dir / config.logging.log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure the root logger
    # Get the root logger
    root_logger = logging.getLogger()
    # Set its level. This is important because handlers won't process messages below this level.
    root_logger.setLevel(log_level)
    # Remove any existing handlers to avoid duplication if setup_logging is called multiple times
    # (though _logging_configured should prevent this)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    # Add the new handlers
    for handler in handlers:
        root_logger.addHandler(handler)

    logger.info(
        f"Logging configured. Level: {log_level_str}. Console: {config.logging.log_to_console}. File: {config.logging.log_file or 'Disabled'}"
    )
    _logging_configured = True # Set flag after successful configuration


def load_config(config_file: Optional[str | Path] = None) -> AppConfig:
    """Loads application configuration using the AppConfig.load method."""
    global _config
    if _config is None or config_file: # Reload if a specific file is given
        _config = AppConfig.load(config_file=str(config_file) if config_file else None)
    if _config is None: # Should not happen if load was successful
        raise appconfig_errors.ConfigurationError("Configuration could not be loaded.")
    return _config


def get_config() -> AppConfig:
    """Returns the global AppConfig instance, loading it if necessary."""
    global _config
    if _config is None:
        logger.debug("Global config not yet loaded. Loading default AppConfig now.")
        _config = AppConfig.load() # Loads default or from DREAMOS_CONFIG_PATH
    if _config is None: # Should not happen
        raise appconfig_errors.ConfigurationError("Configuration could not be retrieved or loaded.")
    return _config


# EDIT START: Remove late import of GuiAutomationConfig
# from dreamos.automation.config import GuiAutomationConfig # MOVED AND GUARDED
# EDIT END

# At the very end of the file, after all model definitions and functions
AppConfig.model_rebuild()
print("DEBUG_CONFIG: End of dreamos.core.config.py, AppConfig.model_rebuild() called.")

# Ensure logging is set up if this module is imported and no entry point has done so.
# This is a fallback. Ideally, the main application entry point calls load_config() or get_config().
# if not _logging_configured:
#     try:
#         fallback_config = get_config() # Try to get/load config
#         # setup_logging(fallback_config) # setup_logging is now called within load/get
#     except Exception as e:
#         # If config loading fails here, use a very basic logger.
#         logging.basicConfig(level=logging.WARNING)
#         logger.error(f"Fallback logging setup failed due to config error: {e}. Using basic console logging.")
#         _logging_configured = True # Prevent further attempts
