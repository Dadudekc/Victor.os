import os
import shutil
from pathlib import Path

def restore_agent_files():
    """Restore orphaned agent files from archive to the restored directory."""
    # Source and destination paths
    archive_path = Path("archive/orphans")
    restored_path = Path("src/dreamos/agents/restored")
    
    # Core agent files to restore
    agent_files = [
        "py/agent_lore_writer.py",
        "py/task_promoter_agent.py",
        "py/tool_executor_agent.py",
        "py/offline_validation_agent.py",
        "src/dreamos/core/coordination/base_agent.py",
        "src/dreamos/core/coordination/agent_bus.py",
        "src/dreamos/agents/agent_loop.py",
        "src/dreamos/agents/utils/agent_identity.py"
    ]
    
    # Create necessary directories
    for file_path in agent_files:
        dest_dir = restored_path / Path(file_path).parent
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy file if it exists
        src_file = archive_path / file_path
        if src_file.exists():
            dest_file = restored_path / file_path
            shutil.copy2(src_file, dest_file)
            print(f"Restored: {file_path}")
        else:
            print(f"Warning: Source file not found: {file_path}")

if __name__ == "__main__":
    restore_agent_files() 