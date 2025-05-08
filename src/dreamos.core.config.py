import logging
import os
from pathlib import Path
from typing import Any, List, Optional

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

# --- Early definitions or simple imports (no circular risk) ---
logger = logging.getLogger(__name__)  # Define logger early


def find_project_root_marker(marker: str = ".git") -> Path:
    current_path = Path(__file__).resolve()
    while current_path != current_path.parent:
        if (current_path / marker).exists():
            return current_path
        current_path = current_path.parent
    return Path.cwd()


PROJECT_ROOT = find_project_root_marker()
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "runtime" / "config" / "config.yaml"

print("DEBUG: dreamos.core.config.py - Top of file executing", flush=True)
print(
    f"DEBUG: dreamos.core.config.py - PROJECT_ROOT determined: {PROJECT_ROOT}",
    flush=True,
)
print(
    f"DEBUG: dreamos.core.config.py - DEFAULT_CONFIG_PATH: {DEFAULT_CONFIG_PATH}",
    flush=True,
)


# --- Pydantic Models for Config Structure (ensure these don't import AppConfig or cause cycles) ---
class LoggingConfig(BaseModel):
    level: str = Field("INFO")
    log_file: Optional[str] = None
    log_to_console: bool = True
    # ... (resolve_log_dir method if any) ...


class PathsConfig(BaseModel):
    project_root: Path = Field(default_factory=lambda: PROJECT_ROOT)
    runtime: Path = Field(default_factory=lambda: PROJECT_ROOT / "runtime")
    logs: Path = Field(default_factory=lambda: PROJECT_ROOT / "runtime" / "logs")
    # ... (other path fields) ...


class OpenAIConfig(BaseModel):
    api_key: Optional[SecretStr] = Field(None, alias="openai_api_key")


class ChatGPTScraperConfig(BaseModel):
    email: Optional[SecretStr] = Field(None, alias="chatgpt_email")
    password: Optional[SecretStr] = Field(None, alias="chatgpt_password")
    totp_secret: Optional[SecretStr] = Field(None, alias="chatgpt_totp_secret")


# Define other simple config component models here if they are used by AppConfig fields
# For instance, if PyAutoGUIBridgeConfig, OrchestratorConfig etc. are defined in *this file* or imported
# from modules that don't create cycles, they can be defined/imported here.


# --- YamlConfigSettingsSource (if it remains in this file and is self-contained) ---
class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    # ... (implementation as before) ...
    def __init__(
        self,
        settings_cls: type[BaseSettings],
        yaml_file: Optional[Path] = None,
        yaml_file_encoding: Optional[str] = None,
    ):
        super().__init__(settings_cls)
        self.default_config_file_path = yaml_file or DEFAULT_CONFIG_PATH
        self.yaml_file_encoding = yaml_file_encoding or "utf-8"
        self.config_data = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        config_path_str = os.getenv(
            "DREAMOS_CONFIG_PATH", str(self.default_config_file_path)
        )
        config_path = Path(config_path_str)
        if config_path.exists():
            try:
                with open(config_path, "r", encoding=self.yaml_file_encoding) as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Error loading YAML config from {config_path}: {e}")
        return {}

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        field_value = self.config_data.get(field_name)
        return field_value, field_name, False

    def prepare_field_value(
        self, field_name: str, field: Any, value: Any, value_is_complex: bool
    ) -> Any:
        return value

    def __call__(self) -> dict[str, Any]:
        return self.config_data


# --- AppConfig Definition ---
class AppConfig(BaseSettings):
    """Main application configuration loaded from environment variables and/or config file."""

    # Use string literals for types that will be imported *after* this class definition
    logging: "LoggingConfig" = Field(default_factory=LoggingConfig)
    paths: "PathsConfig" = Field(default_factory=PathsConfig)
    dreamscape: Optional["DreamscapeConfig"] = None
    openai: "OpenAIConfig" = Field(default_factory=OpenAIConfig)
    chatgpt_scraper: "ChatGPTScraperConfig" = Field(
        default_factory=ChatGPTScraperConfig
    )
    gui_automation: Optional["GuiAutomationConfig"] = None
    pyautogui_bridge: Optional["PyAutoGUIBridgeConfig"] = None  # Example
    orchestrator: Optional["OrchestratorConfig"] = None  # Example
    swarm: Optional["SwarmConfig"] = None  # Example
    integrations: Optional["IntegrationsConfig"] = None  # Example
    health_checks: Optional["HealthCheckConfig"] = None  # Example
    monitoring: Optional["MonitoringConfig"] = None  # Example
    memory_maintenance: Optional["MemoryMaintenanceConfig"] = None  # Example
    agent_points_system: Optional["AgentPointsSystemConfig"] = None  # Example

    project_root_internal: Path = Field(
        exclude=True, default_factory=lambda: PROJECT_ROOT
    )

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
        validate_assignment=True,
        # Removed str_strip_whitespace if it was causing warnings from user output and not critical
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            dotenv_settings,
            env_settings,
            YamlConfigSettingsSource(settings_cls=settings_cls),
            file_secret_settings,
        )

    def setup_logging(self):
        log_level = self.logging.level.upper()
        log_file = (
            self.paths.logs / self.logging.log_file if self.logging.log_file else None
        )
        handlers: List[logging.Handler] = []
        if self.logging.log_to_console:
            handlers.append(logging.StreamHandler(sys.stdout))
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=handlers,
            force=True,
        )
        logger.info(
            f"Logging configured. Level: {log_level}, Console: {self.logging.log_to_console}, File: {log_file}"
        )

    def _ensure_dirs_exist(self):
        # Example: Create logs directory if it doesn't exist
        self.paths.logs.mkdir(parents=True, exist_ok=True)
        # Add other necessary directory creations here

    @classmethod
    def load(cls, config_file: Optional[str] = None) -> "AppConfig":
        # Ensure DREAMOS_CONFIG_PATH is set for YamlConfigSettingsSource if config_file is provided
        effective_config_path = Path(config_file or DEFAULT_CONFIG_PATH)
        if not effective_config_path.is_absolute():
            effective_config_path = PROJECT_ROOT / effective_config_path

        os.environ["DREAMOS_CONFIG_PATH"] = str(effective_config_path)
        logger.info(f"Loading AppConfig from: {os.environ['DREAMOS_CONFIG_PATH']}")

        instance = cls()
        instance.project_root_internal = PROJECT_ROOT  # Set internal project root

        # Ensure paths are resolved after loading config, especially if they depend on project_root_internal
        # or other loaded values. For now, assuming direct factory usage of PROJECT_ROOT is sufficient.
        # If PathsConfig needs to be re-initialized or its fields re-resolved:
        # instance.paths = PathsConfig(project_root=instance.project_root_internal, ...)

        instance._ensure_dirs_exist()
        instance.setup_logging()
        return instance


# --- Late imports (should be AT MODULE LEVEL, AFTER AppConfig class definition) ---
from dreamos.automation.config import GuiAutomationConfig
from dreamscape.config import DreamscapeConfig

# Import other custom config model classes if they were string-hinted in AppConfig
# Example:
# from .pyautogui_bridge_config import PyAutoGUIBridgeConfig
# from .orchestrator_config import OrchestratorConfig, SwarmConfig, IntegrationsConfig # If grouped
# from .health_check_config import HealthCheckConfig
# from .monitoring_config import MonitoringConfig
# from .memory_maintenance_config import MemoryMaintenanceConfig # If defined elsewhere
# from .agent_points_system_config import AgentPointsSystemConfig # If defined elsewhere

# Global config instance (optional)
# _app_config = AppConfig.load()
# print(f"DEBUG: AppConfig loaded. OpenAI API Key set: {bool(_app_config.openai.api_key)}")
