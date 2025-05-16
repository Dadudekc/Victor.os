#!/usr/bin/env python3
"""
Run the Dream.OS Universal Agent Bootstrap Runner.
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Run the bootstrap runner."""
    try:
        # Ensure runtime directories exist
        runtime_dir = Path("runtime")
        devlog_dir = runtime_dir / "devlog" / "agents"
        prompts_dir = runtime_dir / "prompts"
        
        for dir_path in [devlog_dir, prompts_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        # Run the bootstrap runner
        subprocess.run(
            [
                sys.executable,
                "-m",
                "dreamos.tools.agent_bootstrap_runner",
                "--agent",
                "Agent-0",
                "--no-delay"
            ],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running bootstrap: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nBootstrap runner terminated by user")
        sys.exit(0)

if __name__ == "__main__":
    main() 