"""
Start Cleanup Directive Broadcaster
Launches the cleanup directive broadcaster in the background.
"""

import subprocess
import sys
import os
from pathlib import Path

def start_broadcaster():
    """Start the cleanup directive broadcaster in the background."""
    try:
        # Get script directory
        script_dir = Path(__file__).parent
        
        # Build command
        broadcaster_script = script_dir / "cleanup_directive_broadcaster.py"
        log_file = script_dir / "cleanup_broadcast.log"
        
        # Start process in background
        with open(log_file, 'w') as f:
            process = subprocess.Popen(
                [sys.executable, str(broadcaster_script)],
                stdout=f,
                stderr=f,
                start_new_session=True
            )
        
        print(f"Started cleanup directive broadcaster (PID: {process.pid})")
        print(f"Logs will be written to: {log_file}")
        
    except Exception as e:
        print(f"Error starting broadcaster: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_broadcaster() 