"""
Validation utilities for Dream.OS bootstrap process.
"""

import logging
from pathlib import Path
from typing import List, Optional, NamedTuple

logger = logging.getLogger(__name__)

class ValidationResult(NamedTuple):
    """Result of validation check."""
    passed: bool
    error: Optional[str] = None

def validate_all_files(log: logging.Logger, config: 'AgentConfig', is_onboarding: bool = False) -> ValidationResult:
    """
    Validate all required files and directories exist.
    
    Args:
        log: Logger instance
        config: Agent configuration
        is_onboarding: Whether this is an onboarding validation
        
    Returns:
        ValidationResult: Result of validation check
    """
    # Base paths that must exist
    required_paths = [
        Path("runtime"),
        Path("runtime/devlog"),
        Path("runtime/devlog/agents"),
        Path("runtime/agent_comms"),
        Path("runtime/agent_comms/agent_mailboxes"),
    ]
    
    # Agent-specific paths
    agent_base_dir = Path(f"runtime/agent_comms/agent_mailboxes/{config.agent_id}")
    agent_paths = [
        agent_base_dir,
        agent_base_dir / "inbox",
        agent_base_dir / "processed",
        agent_base_dir / "state",
        agent_base_dir / "archive",
    ]
    
    # Add agent paths to required paths
    required_paths.extend(agent_paths)
    
    # For onboarding, also check the actual prompt source that will be used
    if is_onboarding:
        if config.prompt: # Direct prompt string provided
            log.info(f"Using direct prompt string for {config.agent_id}. No prompt file to validate.")
        elif config.prompt_file: # Specific prompt file provided
            prompt_path_to_validate = Path(config.prompt_file)
            log.info(f"Validating configured prompt_file for {config.agent_id}: {prompt_path_to_validate}")
            required_paths.append(prompt_path_to_validate)
        else: # Default agent-specific prompt file expected
            prompt_path_to_validate = Path(config.prompt_dir) / f"{config.agent_id.lower()}.txt"
            log.info(f"Validating default agent-specific prompt file for {config.agent_id}: {prompt_path_to_validate}")
            required_paths.append(prompt_path_to_validate)
    
    missing_paths: List[Path] = []
    
    for path in required_paths:
        if not path.exists():
            missing_paths.append(path)
            log.error(f"Required path missing: {path}")
            
    if missing_paths:
        error_msg = f"Validation failed. Missing {len(missing_paths)} required paths."
        log.error(error_msg)
        return ValidationResult(passed=False, error=error_msg)
        
    log.info("All required paths validated successfully.")
    return ValidationResult(passed=True) 