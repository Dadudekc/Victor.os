# Dream.OS User Guide

## Introduction

Welcome to Dream.OS! This guide provides a more detailed overview of how to use the framework, building upon the [Quickstart Guide](./USER_ONBOARDING.md).

Dream.OS is designed to orchestrate AI agents for complex development tasks, leveraging automated code analysis, task management, and inter-agent communication.

## Core Concepts

- **Agents:** Specialized Python classes designed to perform specific tasks (e.g., code analysis, refactoring, testing, documentation). Located in `src/dreamos/agents/`.
- **Agent Bus:** The central nervous system (`src/dreamos/agent_bus.py`). Agents publish and subscribe to messages, enabling decoupled communication and event-driven workflows.
- **Tools:** Reusable modules providing core capabilities to agents (`src/dreamos/tools/`). Examples include file manipulation, code search, and project structure analysis.
- **Project Scanner:** A key tool (`src/dreamos/tools/analysis/scanner/`) that analyzes the codebase, identifies components, calculates complexity, and generates context files (`project_analysis.json`, `chatgpt_project_context.json`) used by agents and for observability.
- **Configuration:** Settings are primarily managed in `src/dreamos/config.py`, potentially augmented by `.env` files for environment specifics.
- **Orchestration:** High-level control flow, task assignment, and agent lifecycle management (likely handled by `src/dreamos/orchestrator.py` and/or the CLI/Dashboard).

## Installation & Setup

(Refer to the [Quickstart Guide](./USER_ONBOARDING.md#installation) for detailed steps on cloning, setting up a virtual environment, and installing dependencies.)

**Key Dependencies:**
- Core Python libraries (check `requirements.txt` or `pyproject.toml`).
- `tree-sitter` (optional, for advanced multi-language analysis).
- `PyQt5` (optional, for the GUI Dashboard).

## Configuration In-Depth

- **`src/dreamos/config.py`:** This is the primary configuration hub. Explore this file to understand:
    - Logging levels (Console, File)
    - Log rotation settings (size, backup count)
    - Agent-specific parameters
    - Default paths (runtime data, logs)
    - Feature flags
- **`.env` File:** If a `.env.template` exists, copy it to `.env` and fill in sensitive information like API keys or environment-specific paths. This file is typically loaded at startup and overrides defaults from `config.py`.
- **Tree-sitter Paths:** If using Rust/JS/TS analysis, ensure the paths to your compiled `.so`/`.dll` grammar files are correctly set in `src/dreamos/tools/analysis/scanner/analyzer.py` within the `_init_tree_sitter_language` method.

## Running Dream.OS

### Command Line Interface (CLI)

The primary way to interact with Dream.OS is via the CLI module.

```bash
# View available commands and options
python -m src.dreamos.cli --help
```

**Common CLI Tasks:**

- **Run Project Scan:** Update the codebase analysis.
  ```bash
  python -m src.dreamos.cli scan --categorize-agents --generate-init
  ```
  * `--categorize-agents`: Adds maturity/type info to `project_analysis.json`.
  * `--generate-init`: Automatically creates/updates `__init__.py` files in Python packages.

- **Execute a Specific Task:** (Verify exact command structure)
  ```bash
  # Hypothetical example
  # python -m src.dreamos.cli run --task "Update docs for module X" --agent DocsAgent
  ```

### GUI Dashboard

An optional PyQt dashboard provides visual monitoring and interaction.

```bash
# Ensure PyQt5 is installed (pip install pyqt5)
# Verify the exact launch command:
python -m src.dreamos.dashboard.main 
```

*(Add details about Dashboard features once verified: Task monitoring, agent status, logging view, interaction capabilities)*

## Understanding the Project Scanner

The scanner (`src/dreamos/tools/analysis/scanner/`) is crucial for context and automation.

- **Operation:** It walks the project tree, identifies supported files (`.py`, `.rs`, `.js`, `.ts`), hashes them, and uses `ast` (Python) or `tree-sitter` (others) to extract structure (functions, classes, complexity).
- **Caching:** Uses `dependency_cache.json` to store file hashes. Only changed files are re-analyzed, speeding up subsequent scans. Delete this file to force a full re-scan.
- **Output Files:**
    - `project_analysis.json`: Detailed structural information for each analyzed file. Used by agents for context.
    - `chatgpt_project_context.json`: A potentially condensed or formatted version of the analysis suitable for large language models.
- **Agent Categorization:** The `--categorize-agents` flag adds `maturity` and `agent_type` fields to Python class entries in `project_analysis.json` based on heuristics (docstrings, methods, base classes).
- **`__init__.py` Generation:** The `--generate-init` flag automatically creates or updates `__init__.py` files in detected Python packages, adding necessary imports and `__all__` lists.

## Working with Agents

- **Communication:** Agents use the `AgentBus` to send and receive messages. This allows for loose coupling and reactive behavior.
- **Task Execution:** Agents typically receive task assignments via the bus or perform actions based on monitored events.
- **Using Tools:** Agents import and use tools from `src/dreamos/tools/` to perform actions like searching code (`search_tools`), modifying files (`file_tools`), or analyzing structure (`scanner`).

## Troubleshooting

- **Check Logs:** The primary source for diagnosing issues is `logs/agent.log`. Use `tail -f logs/agent.log` or inspect the JSON content.
- **Increase Log Verbosity:** Modify `src/dreamos/config.py` (or use environment variables/CLI flags if available) to set the logging level to `DEBUG` for more detailed output.
- **Check Configuration:** Ensure `src/dreamos/config.py` and any `.env` files have correct paths and settings.
- **Scanner Issues:** If analysis seems incorrect, try deleting `dependency_cache.json` and re-running the scan.
- **GUI Issues:** Ensure PyQt5 and any other dashboard dependencies are correctly installed.

## Contributing

Please refer to the [Quickstart Guide](./USER_ONBOARDING.md#contributing--feedback) for details on contributing via GitHub Issues and Pull Requests. 