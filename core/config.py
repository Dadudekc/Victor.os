"""
Configuration loading and validation using Pydantic.
"""

import yaml
import logging
import os
from pydantic import BaseModel, Field, FilePath, validator, ValidationError
from typing import Optional, Literal
from pathlib import Path

logger = logging.getLogger(__name__)

# Define paths relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]

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
    target_files: list[FilePath] = []
    output_path: Optional[Path] = None

    @validator('target_files', pre=True, each_item=True)
    def resolve_target_files(cls, v):
        path = Path(v)
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        if not path.exists():
            # Allow non-existent files for write operations, maybe add check later?
            # raise ValueError(f"Target file does not exist: {path}")
            pass
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
                # Filter out keys not defined in the model before initialization
                # to avoid unexpected argument errors if config.yaml has extra keys
                model_fields = cls.model_fields.keys()
                filtered_data = {k: v for k, v in config_data.items() if k in model_fields}
                config = cls(**filtered_data)

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
        dirs_to_check = [
            config.logging.log_dir,
            config.paths.memory,
            config.paths.temp,
            # Removed paths related to screenshots, downloads, etc.
        ]
        if config.task_details and config.task_details.output_path:
            dirs_to_check.append(config.task_details.output_path.parent)

        for dir_path in dirs_to_check:
            if dir_path:
                os.makedirs(dir_path, exist_ok=True) 