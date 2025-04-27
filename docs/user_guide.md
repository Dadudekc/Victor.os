# Dream.OS User Guide

## Introduction

Welcome to Dream.OS! This guide provides a more detailed overview of how to use the framework, building upon the [Quickstart Guide](./USER_ONBOARDING.md).

Dream.OS is designed to orchestrate AI agents for complex development tasks, leveraging automated code analysis, task management, and inter-agent communication.

## Core Concepts

- **Agents:** Specialized Python classes designed to perform specific tasks (e.g., code analysis, refactoring, testing, documentation). Located in `src/dreamos/agents/`.
- **Agent Bus:** The central nervous system (`src/dreamos/agent_bus.py`). Agents publish and subscribe to messages, enabling decoupled communication and event-driven workflows.
- **Tools:** Reusable modules providing core capabilities to agents (`src/dreamos/tools/`). Examples include file manipulation, code search, and project structure analysis (`tools/analysis/scanner/`).
- **Project Scanner:** A key tool (`src/dreamos/tools/analysis/scanner/`) that analyzes the codebase, identifies components, calculates complexity, and generates context files (`project_analysis.json`, `chatgpt_project_context.json`) used by agents and for observability.
- **Configuration:** Settings are primarily loaded from `config/config.yaml` and validated using Pydantic models in `src/dreamos/config.py`.
- **Orchestration:** High-level control flow, task assignment, and agent lifecycle management handled by `src/dreamos/orchestrator.py` and interaction points like the CLI (`src/dreamos/cli/main.py`) or Dashboard (`src/dreamos/dashboard/dashboard_ui.py`).

## Installation & Setup

(Refer to the [Quickstart Guide](./USER_ONBOARDING.md#setup--configuration) for detailed steps on cloning, setting up a virtual environment, and installing dependencies.)

**Key Dependencies:**
- Core Python libraries (check `requirements.txt` or `pyproject.toml`).
- `tree-sitter` (optional, for advanced multi-language analysis).
- `PyQt5` (optional, for the GUI Dashboard).

## Configuration In-Depth

- **`config/config.yaml`**: This YAML file defines the primary configuration overrides. Create it if it doesn't exist. It's loaded and validated against the Pydantic models in `src/dreamos/config.py`.
- **`src/dreamos/config.py`:** Defines the structure and default values for configuration using Pydantic models. Review this file to understand available settings:
    - `LoggingConfig`: Log level, directory, filename.
    - `PathsConfig`: Locations for runtime data like memory, temp files.
    - Agent-specific settings might be defined here or loaded separately.
- **`.env` File:** If needed for sensitive data (API keys, connection strings), check for a `.env.template`. Environment variables loaded from `.env` often override values from the YAML file or defaults.
- **Tree-sitter Paths:** If using Rust/JS/TS analysis, ensure the paths to your compiled `.so`/`.dll` grammar files are correctly set in `src/dreamos/tools/analysis/scanner/analyzer.py`.

## Running Dream.OS

### Command Line Interface (CLI)

The primary way to interact with Dream.OS is via the CLI defined in `src/dreamos/cli/main.py`. Run commands from the project root directory.

```bash
# View available commands and options 
# (Verify exact command, e.g., python -m src.dreamos.cli.main --help)
# python -m src.dreamos.cli.main --help 
```
*(Note: The exact command structure needs verification as the `cli/main.py` file appeared incomplete.)*

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

**Dashboard Features:**
*(Based on `dashboard_ui.py` analysis - requires verification in running app)*
- Agent health monitoring (success/failure rates, thresholds).
- Task list display and management.
- Mailbox viewer for inter-agent messages.
- Interface for triggering specific agent actions or tasks.

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

## Troubleshooting

- **Check Logs:** The primary source for diagnosing issues is the log file configured in `config.yaml` (likely `logs/agent.log` or similar). Logs are typically structured JSON Lines.
- **Increase Log Verbosity:** Modify the `logging.level` setting in `config/config.yaml` to `DEBUG` for more detailed output.
- **Check Configuration:** Verify paths and settings in `config/config.yaml` and any `.env` file.
- **Scanner Issues:** If analysis (`project_analysis.json`) seems incorrect or stale, delete `dependency_cache.json` and re-run the scan via the CLI.
- **GUI Issues:** Ensure PyQt5 and other dashboard dependencies are installed in your virtual environment.

## Contributing

Please refer to the [Quickstart Guide](./USER_ONBOARDING.md#contributing--feedback) for details on the standard GitHub workflow (Fork, Branch, PR) and reporting issues. 