import os
from pathlib import Path

def fix_imports():
    """Fix import paths in restored agent files."""
    restored_path = Path("src/dreamos/agents/restored")
    
    # Files to process
    files_to_fix = [
        "py/agent_lore_writer.py",
        "py/task_promoter_agent.py",
        "py/tool_executor_agent.py",
        "py/offline_validation_agent.py"
    ]
    
    for file_path in files_to_fix:
        full_path = restored_path / file_path
        if not full_path.exists():
            print(f"Warning: File not found: {file_path}")
            continue
            
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix imports
        content = content.replace(
            "from dreamos.core.coordination.base_agent import BaseAgent",
            "from src.dreamos.agents.restored.src.dreamos.core.coordination.base_agent import BaseAgent"
        )
        content = content.replace(
            "from dreamos.core.coordination.agent_bus import AgentBus",
            "from src.dreamos.agents.restored.src.dreamos.core.coordination.agent_bus import AgentBus"
        )
        content = content.replace(
            "from dreamos.core.config import Config",
            "from src.dreamos.core.config import Config"
        )
        
        # Write back the fixed content
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed imports in: {file_path}")

if __name__ == "__main__":
    fix_imports() 