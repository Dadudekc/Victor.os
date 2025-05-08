# Dream.OS User Guide (Quickstart & Details)

## Introduction

Welcome to Dream.OS! This guide provides an overview of how to set up and use the framework.

Dream.OS is an extensible Python framework designed to orchestrate AI agents for complex development and analysis tasks, leveraging automated code analysis, task management, and inter-agent communication.

## System Overview & Core Concepts

Dream.OS is built around several key components, primarily located within the `src/dreamos/` directory:

- **`src/dreamos/`**: The main source code package.
- **Agents:** Specialized Python classes (`src/dreamos/agents/`) designed to perform specific tasks (e.g., code analysis, refactoring, testing, documentation).
- **Agent Bus (`agent_bus.py`):** The central nervous system and message broker (`src/dreamos/agent_bus.py`). Agents publish and subscribe to messages, enabling decoupled communication and event-driven workflows.
- **Orchestrator (`orchestrator.py`):** Manages the overall workflow, task assignment, and agent lifecycle (`src/dreamos/orchestrator.py`).
- **Configuration (`config.py`):** Centralized application settings and parameters, defined by Pydantic models in `src/dreamos/config.py` and typically loaded from `config/config.yaml`.
- **Tools (`tools/`):** Reusable modules providing core capabilities to agents (`src/dreamos/tools/`). Examples include file manipulation, code search, and project structure analysis.
- **Project Scanner (`tools/analysis/scanner/`):** A key tool that analyzes the codebase, identifies components, calculates complexity, and generates context files (`project_analysis.json`, `chatgpt_project_context.json`) used by agents and for observability. See [Understanding the Project Scanner](#understanding-the-project-scanner) below for more details.
- **Core (`core/`):** Foundational utilities for coordination, agent base classes, error handling, configuration, etc.
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

### Configuration In-Depth

- **`config/config.yaml`**: This YAML file defines the primary configuration overrides. Create it if it doesn't exist. It's loaded and validated against the Pydantic models in `src/dreamos/config.py`.
- **`src/dreamos/config.py`**: Defines the structure and default values for configuration using Pydantic models. Review this file to understand available settings:
  - `LoggingConfig`: Log level, directory, filename.
  - `PathsConfig`: Locations for runtime data like memory, temp files.
  - Agent-specific settings might be defined here or loaded separately.
- **`.env` File:** If needed for sensitive data (API keys, connection strings), check for a `.env.template`. Environment variables loaded from `.env` often override values from the YAML file or defaults.
- **Tree-sitter Paths:** If using Rust/JS/TS analysis, ensure the paths to your compiled `.so`/`.dll` grammar files are correctly set in `src/dreamos/tools/analysis/scanner/analyzer.py`.

## Running Dream.OS

Dream.OS is typically run via its command-line interface or the optional GUI dashboard.

### Command Line Interface (CLI)

The primary way to interact with Dream.OS is via the CLI defined in `src/dreamos/cli/main.py`. Run commands from the project root directory.

```bash
# View available commands and options
# (Verify exact command, e.g., python -m src.dreamos.cli.main --help)
# python -m src.dreamos.cli.main --help
```

_(Note: The exact command structure needs verification as the `cli/main.py` file may have evolved.)_

**Common CLI Tasks:**

- **Run Project Scan:** Update the codebase analysis, categorize agents, and generate `__init__.py` files.
  ```bash
  # Verify exact command, this is based on the scanner module's own CLI parser
  # python -m src.dreamos.cli scan --categorize-agents --generate-init
  ```
- **Execute a Specific Task:** (Verify command structure)
  ```bash
  # Hypothetical example:
  # python -m src.dreamos.cli run-task --name "Update documentation" --agent DocsAgent
  ```

### GUI Dashboard

An optional PyQt dashboard (`src/dreamos/dashboard/dashboard_ui.py`) provides visual monitoring.

```bash
# Ensure PyQt5 is installed: pip install pyqt5
# Verify the launch command (might be via CLI or direct script execution)
# python -m src.dreamos.dashboard.dashboard_ui
# OR perhaps: python -m src.dreamos.cli --gui
```

**Dashboard Features:** _(Based on `dashboard_ui.py` analysis - requires verification in running app)_

- Agent health monitoring (success/failure rates, thresholds).
- Task list display and management.
- Mailbox viewer for inter-agent messages.
- Interface for triggering specific agent actions or tasks.

## Agent Interaction & Tasking

- Agents primarily communicate and coordinate actions via messages published to the **Agent Bus** (`agent_bus.py`).
- Tasks can be initiated via:
  - CLI commands.
  - Actions triggered from the Dashboard.
  - Internal triggers based on system events or schedules.
  - Predefined workflows loaded from configuration.
- Task status and results are often logged or stored in `runtime/` directories.

## Understanding the Project Scanner

The scanner (`src/dreamos/tools/analysis/scanner/`) is crucial for context and automation.

- **Operation:** Walks the project (`src/`), identifies supported files (`.py`, `.rs`, `.js`, `.ts`), hashes them, ignores configured exclusions (like `.venv`, `node_modules`, `__pycache__`), and uses `ast` (Python) or `tree-sitter` (others) to extract structure (functions, classes, imports, complexity).
- **Caching:** Uses `dependency_cache.json` in the project root to store file hashes. Only changed files are re-analyzed. Delete this file to force a full re-scan.
- **Output Files (in project root):**
  - `project_analysis.json`: Detailed structural information for each analyzed file, merging results with previous runs (preserves info about files not currently scanned).
  - `chatgpt_project_context.json`: A potentially condensed or formatted version of the analysis suitable for large language models (also merges with previous content).
- **Agent Categorization (`--categorize-agents` flag for CLI):** Adds `maturity` and `agent_type` fields to Python class entries in `project_analysis.json` based on heuristics (docstrings, method names, base classes).
- **`__init__.py` Generation (`--generate-init` flag for CLI):** Automatically creates or updates `__init__.py` files in detected Python packages within `src/`, adding necessary imports and `__all__` lists.

## Working with Agents

- **Communication:** Agents primarily use the `AgentBus` (`src/dreamos/agent_bus.py`) to send and receive messages asynchronously.
- **Task Execution:** Agents subscribe to relevant message types (e.g., `TaskAssigned`) or monitor system state/events to trigger their core logic.
- **Using Tools:** Agents import and instantiate tools from `src/dreamos/tools/` to perform actions. They should leverage existing tools before implementing new overlapping functionality.

## Key Paths & Files

- **`src/dreamos/`**: Core source code package.
  - `agents/`: Agent implementations.
  - `core/`: Foundational utilities for coordination, agent base classes, error handling, configuration, etc.
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

## Agent Autonomy Concepts

Agents in Dream.OS achieve autonomy through various mechanisms:

- **Event-Driven:** Reacting to messages on the `AgentBus`.
- **Monitoring:** Watching filesystem locations or external resources.
- **Scheduled Execution:** Performing actions based on internal timers.
- **Proactive Analysis:** Utilizing the `ProjectScanner` output or other system state information to initiate tasks based on rules or heuristics.

## Troubleshooting

- **Check Logs:** The primary source for diagnosing issues is the log file configured in `config.yaml` (likely `logs/agent.log` or similar). Logs are typically structured JSON Lines.
- **Increase Log Verbosity:** Modify the `logging.level` setting in `config/config.yaml` to `DEBUG` for more detailed output.
- **Check Configuration:** Verify paths and settings in `config/config.yaml` and any `.env` file.
- **Scanner Issues:** If analysis (`project_analysis.json`) seems incorrect or stale, delete `dependency_cache.json` and re-run the scan via the CLI.
- **GUI Issues:** Ensure PyQt5 and other dashboard dependencies are installed in your virtual environment.
- **Tips & Support:** Use the `--help` flag with the CLI (`python -m src.dreamos.cli.main --help` - verify) to see available commands. Questions or issues? Open an issue in the project's GitHub repository.

## Contributing & Feedback

- Follow standard GitHub workflow: Fork, Branch, Commit, Pull Request.
- Ensure code changes adhere to project style guidelines (run linters/formatters).
- Update relevant documentation and add tests.
- Report bugs or suggest features via GitHub Issues.

Enjoy building with Dream.OS! 🚀
