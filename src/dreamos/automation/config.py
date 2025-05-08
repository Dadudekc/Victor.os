# src/dreamos/automation/config.py
from typing import Optional
from pathlib import Path
from pydantic import BaseModel, Field, FilePath

# Determine Project Root (simplified for this module, assumes it's discoverable)
# In a real scenario, this might come from a shared utility or AppConfig's root
# For now, assume PROJECT_ROOT is available if needed for resolving relative paths in defaults
# If not, FilePath will expect absolute paths or paths relative to PWD when models are used.
# As GuiAutomationConfig uses PROJECT_ROOT, we need a way to provide it.
# Placeholder: This might need a more robust way to get PROJECT_ROOT if this config
# is loaded independently before the main AppConfig sets its own PROJECT_ROOT.
# For now, we'll define it locally for the default values, assuming this module is part of the larger structure.

def _find_project_root_marker_for_automation(marker: str = ".git") -> Path:
    current_dir = Path(__file__).resolve().parent
    while current_dir != current_dir.parent:
        if (current_dir / marker).exists():
            return current_dir
        current_dir = current_dir.parent
    # Fallback if marker not found (e.g. running in a very detached context)
    # This is a basic fallback, might not be correct in all deployment scenarios.
    return Path(__file__).resolve().parents[3] # Adjust depth as needed

_AUTOMATION_PROJECT_ROOT = _find_project_root_marker_for_automation()

class GuiAutomationConfig(BaseModel):
    target_window_title: str = "Cursor"  # Default to common IDE name
    input_coords_file_path: FilePath = Field(
        _AUTOMATION_PROJECT_ROOT / "runtime/config/cursor_agent_coords.json"
    )
    copy_coords_file_path: FilePath = Field(
        _AUTOMATION_PROJECT_ROOT / "runtime/config/cursor_agent_copy_coords.json"
    )
    recalibration_retries: int = 1
    min_pause_seconds: float = 0.10
    max_pause_seconds: float = 0.25
    random_offset_pixels: int = 3
    type_interval_seconds: float = 0.01  # Add typing interval
    retry_attempts: int = 3  # Add retry attempts
    retry_delay_seconds: float = 0.5  # Add retry delay
    copy_attempts: int = 2  # Add copy attempts config (for TASK_AGENT8-CONFIG-CURSORORCH-COPYATTEMPTS-001)

    class TheaCopyConfig(BaseModel):
        anchor_image_path: str = "assets/thea_reply_anchor.png" # Path relative to project root typically
        click_offset_x: int = 50
        click_offset_y: int = 50
        confidence: float = 0.9
        retries: int = 2
        delay_between_actions: float = 0.1

    thea_copy: TheaCopyConfig = Field(default_factory=TheaCopyConfig) 