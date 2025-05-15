#!/usr/bin/env python3
"""
Launch Agent-2 using the universal bootstrap runner.
Provides a clean interface to start Agent-2 using the unified agent architecture.
"""

import subprocess
import sys
from pathlib import Path

# Import UI interaction components
from dreamos.utils.gui.injector import CursorInjector
from dreamos.utils.gui.retriever import ResponseRetriever

def main():
    """Launch Agent-2 using the universal bootstrap runner"""
    try:
        # The universal runner will handle UI interaction through AgentUIInteractor
        subprocess.run([
            sys.executable,
            "-m", "dreamos.tools.agent_bootstrap_runner",
            "--agent", "Agent-2",
            "--no-delay"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error launching Agent-2: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAgent-2 launcher terminated by user")
        sys.exit(0)

if __name__ == "__main__":
    main() 