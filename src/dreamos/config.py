# config.py
from typing import Tuple
from pathlib import Path
import yaml
import logging
import os
from pydantic import BaseModel, Field, FilePath, validator, ValidationError
from typing import Optional, Literal, List

# Define project root relative to this file (two levels up to repo root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# --- Pydantic Models for Config Structure ---

class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_dir: Path = Field(default=PROJECT_ROOT / "logs")
    log_file: Optional[str] = None  # e.g., "dream_os.log"

    @validator('log_dir')
    def resolve_log_dir(cls, v):
        path = Path(v)
        if not path.is_absolute():
            return (PROJECT_ROOT / path).resolve()
        return v

class PathsConfig(BaseModel):
    memory: Path = Field(default=PROJECT_ROOT / "data" / "memory")
    temp: Path = Field(default=PROJECT_ROOT / "data" / "temp")

    @validator('memory', 'temp', pre=True, always=True)
    def resolve_relative_path(cls, v):
        path = Path(v)
        if not path.is_absolute():
            return (PROJECT_ROOT / path).resolve()
        return v

class TaskDetailsConfig(BaseModel):
    description: str
    target_files: List[FilePath] = []
    output_path: Optional[Path] = None

    @validator('target_files', pre=True, each_item=True)
    def resolve_target_files(cls, v):
        path = Path(v)
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        return path

    @validator('output_path', pre=True)
    def resolve_output_path(cls, v):
        if v is None:
            return None
        path = Path(v)
        if not path.is_absolute():
            return (PROJECT_ROOT / path).resolve()
        return v

# --- Main Configuration Model ---

class AppConfig(BaseModel):
    mode: Literal["gui", "task"] = "gui"
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    task_details: Optional[TaskDetailsConfig] = None

    @classmethod
    def load(cls, config_path: str | Path = "config/config.yaml") -> 'AppConfig':
        """Loads configuration from a YAML file and validates it."""
        config_path = Path(config_path)
        if not config_path.is_absolute():
            config_path = (PROJECT_ROOT / config_path).resolve()

        if not config_path.exists():
            logging.warning(f"Configuration file not found at {config_path}. Using default settings.")
            default_config = cls()
            cls._ensure_dirs_exist(default_config)
            return default_config

        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            if config_data is None:
                logging.warning(f"Configuration file {config_path} is empty. Using default settings.")
                config = cls()
            else:
                model_fields = cls.model_fields.keys()
                filtered = {k: v for k, v in config_data.items() if k in model_fields}
                config = cls(**filtered)

            cls._ensure_dirs_exist(config)
            logging.info(f"Configuration loaded successfully from '{config_path}'.")
            return config
        except ValidationError as e:
            logging.error(f"Configuration validation failed: {e}")
            logging.warning("Falling back to default configuration due to validation errors.")
            default_config = cls()
            cls._ensure_dirs_exist(default_config)
            return default_config
        except Exception as e:
            logging.error(f"Unexpected error loading configuration: {e}")
            logging.warning("Falling back to default configuration due to unexpected error.")
            default_config = cls()
            cls._ensure_dirs_exist(default_config)
            return default_config

    @staticmethod
    def _ensure_dirs_exist(config: 'AppConfig'):
        """Ensure that directories specified in the config exist."""
        dirs = [
            config.logging.log_dir,
            config.paths.memory,
            config.paths.temp,
        ]
        if config.task_details and config.task_details.output_path:
            dirs.append(config.task_details.output_path.parent)

        for d in dirs:
            if d:
                os.makedirs(d, exist_ok=True)

# Add logging setup and exception class
class ConfigError(Exception):
    """Exception raised for errors in the configuration process."""
    pass


def setup_logging(config: AppConfig) -> None:
    """Configures Python logging based on AppConfig settings."""
    level_name = config.logging.level.upper() if hasattr(config.logging, 'level') else 'INFO'
    level = getattr(logging, level_name, logging.INFO)
    fmt = '%(asctime)s - [%(levelname)s] - %(name)s - %(message)s'
    logging.basicConfig(level=level, format=fmt)
    if config.logging.log_file:
        fh = logging.FileHandler(config.logging.log_file)
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter(fmt))
        logging.getLogger().addHandler(fh)

class Config:
    """Central configuration for Dream.OS Auto-Fix Loop"""
    AGENT_ID: str = "agent_001"
    COPY_REGION: Tuple[int, int] = (500, 300)    # width x height for screenshot
    CLIPBOARD_WAIT: float = 0.3                  # seconds to wait for clipboard update
    CHATGPT_URL: str = "http://127.0.0.1:8000/patch"
    CURSOR_CLI: str = "cursor"
    USE_GUI: bool = False                        # toggle headless CLI vs GUI automation
    # Named spots: text_input, send_button, response_area, scroll_up, status_indicator 
