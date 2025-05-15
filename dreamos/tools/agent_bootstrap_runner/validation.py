"""
Validation utilities for Agent Bootstrap Runner
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import AgentConfig

@dataclass
class ValidationResult:
    """Result of a validation check"""
    passed: bool
    error: Optional[str] = None

def validate_json_file(logger: logging.Logger, file_path: Path) -> ValidationResult:
    """
    Validate a JSON file can be parsed.
    
    Args:
        logger: Logger instance
        file_path: Path to JSON file
        
    Returns:
        ValidationResult: Validation result
    """
    try:
        if not file_path.exists():
            return ValidationResult(False, f"File not found: {file_path}")
            
        with file_path.open(encoding="utf-8") as f:
            json.load(f)
        return ValidationResult(True)
    except json.JSONDecodeError as e:
        return ValidationResult(False, f"Invalid JSON in {file_path}: {e}")
    except Exception as e:
        return ValidationResult(False, f"Error validating {file_path}: {e}")

def validate_coords(logger: logging.Logger, config: AgentConfig) -> ValidationResult:
    """
    Validate coordinate files exist and contain required entries.
    
    Args:
        logger: Logger instance
        config: Agent configuration
        
    Returns:
        ValidationResult: Validation result
    """
    try:
        if not config.coords_file.exists():
            return ValidationResult(False, f"Coordinates file not found: {config.coords_file}")
            
        if not config.copy_coords_file.exists():
            return ValidationResult(False, f"Copy coordinates file not found: {config.copy_coords_file}")
            
        # Load and validate coordinates
        with config.coords_file.open(encoding="utf-8") as f:
            coords = json.load(f)
            
        with config.copy_coords_file.open(encoding="utf-8") as f:
            copy_coords = json.load(f)
            
        # Check for required entries
        if config.agent_id not in coords:
            return ValidationResult(False, f"Missing coordinates for {config.agent_id}")
            
        if config.agent_id_for_retriever not in copy_coords:
            return ValidationResult(False, f"Missing copy coordinates for {config.agent_id}")
            
        return ValidationResult(True)
    except json.JSONDecodeError as e:
        return ValidationResult(False, f"Invalid JSON in coordinates file: {e}")
    except Exception as e:
        return ValidationResult(False, f"Error validating coordinates: {e}")

def validate_all_files(logger: logging.Logger, config: AgentConfig) -> ValidationResult:
    """
    Validate all required files and directories exist.
    
    Args:
        logger: Logger instance
        config: Agent configuration
        
    Returns:
        ValidationResult: Validation result
    """
    try:
        # Validate coordinates
        coords_result = validate_coords(logger, config)
        if not coords_result.passed:
            return coords_result
            
        # Validate state file if it exists
        if config.state_file.exists():
            state_result = validate_json_file(logger, config.state_file)
            if not state_result.passed:
                return state_result
                
        # Validate inbox file if it exists
        if config.inbox_file.exists():
            inbox_result = validate_json_file(logger, config.inbox_file)
            if not inbox_result.passed:
                return inbox_result
                
        # Check required directories exist
        required_dirs = [
            config.base_runtime,
            config.inbox_dir,
            config.processed_dir,
            config.state_dir,
            config.devlog_path.parent
        ]
        
        for directory in required_dirs:
            if not directory.exists():
                return ValidationResult(False, f"Required directory missing: {directory}")
                
        return ValidationResult(True)
    except Exception as e:
        return ValidationResult(False, f"Error during validation: {e}") 