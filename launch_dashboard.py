#!/usr/bin/env python3
"""
Dream.OS Dashboard Launcher
--------------------------
A user-friendly interface for managing Dream.OS agents and operations.
"""

import sys
import os
from pathlib import Path

def main():
    # Ensure we're in the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Add src to Python path
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    # Import and run dashboard
    from dreamos.agent_dashboard.main import main as run_dashboard
    run_dashboard()

if __name__ == "__main__":
    main() 