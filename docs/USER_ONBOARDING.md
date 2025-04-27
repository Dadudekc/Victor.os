# Dream.OS Quickstart Guide

## System Overview
Dream.OS is an extensible Python framework for orchestrating AI agents to perform complex development and analysis tasks. Core components reside within the `src/dreamos/` directory:

- **`src/dreamos/`**: Main source code package.
- **Agent Bus (`agent_bus.py`):** A central messaging system facilitating communication between agents and components.
- **Orchestrator (`orchestrator.py`):** Manages the overall workflow and agent lifecycle (high-level control).
- **Configuration (`config.py`):** Centralized application settings and parameters, typically loaded from `config/config.yaml`.
- **Core (`core/`):** Foundational utilities for coordination, agent base classes, utils, etc.
- **Agents (`agents/`):** Implementations of specific agent types.
- **Tools (`tools/`):** Reusable capabilities for agents:
    - **Project Scanner (`tools/analysis/scanner/`):** Analyzes codebase structure, dependencies, and complexity. Outputs `project_analysis.json`.
    - **File Tools (`tools/functional/file_tools.py`):** Read/write/manipulate files.
    - **Search Tools (`tools/functional/search_tools.py`):** Code search using Ripgrep.
- **Dashboard (`dashboard/`):** Optional PyQt-based GUI (`dashboard_ui.py`) for monitoring and interaction.
- **CLI (`cli/main.py`):** Command-line interface for running tasks and interacting with the system.

## Setup & Configuration

### Prerequisites
- Python 3.9+ (Verify compatibility if needed)
- Git
- (Optional) `tree-sitter` Python package (`pip install tree-sitter`) and compiled language grammars (`.so` or `.dll` files) for advanced code analysis in Rust/JS/TS via the Project Scanner. See `src/dreamos/tools/analysis/scanner/analyzer.py` for configuration paths.
- (Optional) GUI dependencies if using the Dashboard: `pip install pyqt5`.

### Installation
```bash
# 1. Clone the repository
# git clone <your-repo-url> Dream.os 
# cd Dream.os

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
# Linux/macOS:
# source .venv/bin/activate
# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1
# Windows CMD:
# .venv\Scripts\activate.bat

# 3. Install dependencies (from project root)
pip install -r requirements.txt 
# OR if using setup.py for editable install:
# pip install -e . 
# OR if using Poetry:
# poetry install
```

### Configuration
- Primary configuration is loaded from `config/config.yaml` (if it exists) and validated by models in `src/dreamos/config.py`. Review `config.py` for available settings.
- Create `config/config.yaml` if it doesn't exist, perhaps copying from an example.
- Sensitive keys (e.g., API keys) or environment-specific overrides can use a `.env` file (check for `.env.template` or `.env.example`).
- Adjust Tree-sitter grammar paths in `src/dreamos/tools/analysis/scanner/analyzer.py` if needed.

## Running Dream.OS

Dream.OS is typically run via its command-line interface.

**Via CLI (`cli/main.py`):**
Run commands from the project root directory.
```bash
# View available commands and options (verify exact command)
# python -m src.dreamos.cli.main --help 

# Example: Run the project scanner
# (Verify exact command, likely involves invoking the ProjectScanner class)
# python -m src.dreamos.cli scan --categorize-agents --generate-init # Example from scanner code

# Example: Run a specific task (hypothetical)
# python -m src.dreamos.cli run-task --name "Refactor core utils" --agent RefactorAgent 
```
*(Note: Verify exact CLI commands and arguments as `cli/main.py` content was incomplete)*

**Via Dashboard (`dashboard/dashboard_ui.py`):**
*(Note: Requires PyQt5. Verify launch mechanism - might be integrated into CLI or run standalone)*
```bash
# Example: Launch the dashboard (verify command)
# python -m src.dreamos.dashboard.dashboard_ui 
```

## Agent Interaction & Tasking
- Agents primarily communicate and coordinate actions via messages published to the **Agent Bus** (`agent_bus.py`).
- Tasks can be initiated via:
    - CLI commands.
    - Actions triggered from the Dashboard.
    - Internal triggers based on system events or schedules.
    - Predefined workflows loaded from configuration.
- Task status and results are often logged or stored in `runtime/` directories.

## Key Paths & Files
- **`src/dreamos/`**: Core source code package.
    - `agents/`: Agent implementations.
    - `core/`: Core utilities (coordination, utils, schemas).
    - `tools/`: Agent tools (analysis, file ops, search).
    - `dashboard/`: Optional GUI components (`dashboard_ui.py`).
    - `cli/main.py`: Command-line entry point.
    - `config.py`: Pydantic models for configuration.
    - `agent_bus.py`: Central message bus.
    - `orchestrator.py`: High-level workflow control.
- **`config/config.yaml`**: Main YAML configuration file (loaded by `src/dreamos/config.py`).
- **`runtime/`**: Directory for runtime data.
    - `logs/`: Log files (location configured in `config.py`).
    - `memory/`: Persistent agent memory (if used).
    - `local_blob/`: Task inputs/outputs (if used).
- **`docs/`**: Documentation.
- **`tests/`**: Unit and integration tests.
- **`project_analysis.json`**: Output of the project scanner tool.
- **`chatgpt_project_context.json`**: LLM-consumable context export from the scanner.
- **`dependency_cache.json`**: File hash cache used by the scanner.

## GUI Dashboard
- A PyQt-based dashboard UI is defined in `src/dreamos/dashboard/dashboard_ui.py`.
- **Launch:** Verify the exact command (e.g., might be a CLI flag like `python -m src.dreamos.cli --gui`).
- **Features:** Includes views for agent health (scrape success/failure), task monitoring, mailbox interaction, etc. (Refer to `dashboard_ui.py` for specifics).
- **Configuration:** Dashboard-specific settings might be in `config/config.yaml` or loaded separately.

## Agent Autonomy Concepts
Agents in Dream.OS achieve autonomy through various mechanisms:
- **Event-Driven:** Reacting to messages on the `AgentBus`.
- **Monitoring:** Watching filesystem locations or external resources.
- **Scheduled Execution:** Performing actions based on internal timers.
- **Proactive Analysis:** Utilizing the `ProjectScanner` output or other system state information to initiate tasks based on rules or heuristics.

## Tips & Support
- Check log files in the directory specified in your configuration (default `logs/`). Log format is typically JSON Lines.
- Configure logging levels in `config/config.yaml` or `src/dreamos/config.py`.
- Use the `--help` flag with the CLI (`python -m src.dreamos.cli.main --help` - verify) to see available commands.
- Remove `dependency_cache.json` to force a full project re-scan if analysis seems stale.
- Questions or issues? Open an issue in the project's GitHub repository.

## Contributing & Feedback
- Follow standard GitHub workflow: Fork, Branch, Commit, Pull Request.
- Ensure code changes adhere to project style guidelines (run linters/formatters).
- Update relevant documentation and add tests.
- Report bugs or suggest features via GitHub Issues.

Enjoy building with Dream.OS! 🚀