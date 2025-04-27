# Dream.OS Quickstart Guide

## System Overview (DRAFT)
Dream.OS is an extensible framework for orchestrating AI agents to perform complex tasks. Core components include:
- **`src/dreamos/`**: Main source code directory.
- **Agent Bus (`agent_bus.py`):** Facilitates communication between agents and components.
- **Orchestrator (`orchestrator.py`?):** Manages the overall workflow and agent lifecycle (TBC).
- **Tools (`src/dreamos/tools/`):** Reusable utilities for agents, including:
    - **Project Scanner (`analysis/scanner/`):** Analyzes codebase structure.
    - **File Tools, Search Tools, etc.**
- **Configuration (`config.py`):** Centralized settings.
- **Dashboard (TBC):** GUI for monitoring and interaction.

## Setup & Configuration (DRAFT)

### Prerequisites
- Python 3.9+ (Verify exact version)
- Git
- (Optional) `tree-sitter` and language grammars for advanced code analysis (See `project_scanner.py`).
- (Optional) GUI dependencies if using Dashboard (e.g., PyQt5 - Verify)

### Installation
```bash
# 1. Clone the repository
git clone <repo-url> && cd Dream.os

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r requirements.txt
# OR potentially using Poetry or setup.py
# poetry install
# pip install -e .
```

### Configuration
- Primary configuration is likely managed in `src/dreamos/config.py`.
- Sensitive keys or environment-specific settings might use a `.env` file (check for `.env.template`).
- Adjust Tree-sitter grammar paths in `src/dreamos/tools/analysis/scanner/analyzer.py` if needed.

## Running Dream.OS (DRAFT)

*(Instructions TBC based on current entry point)*

**Example (Hypothetical CLI):**
```bash
python -m src.dreamos.main --config src/dreamos/config.py 
# Or potentially via a configured entry point in pyproject.toml
dreamos --task "Analyze src/dreamos/core/" 
```

**Example (Hypothetical Dashboard):**
```bash
# Verify path and command
python src/dreamos/dashboard/main.py # ?
```

## Agent Interaction & Tasking (DRAFT)
- Agents likely communicate via the `AgentBus`.
- Tasks might be defined in configuration, triggered by events, or assigned via API/Dashboard.
- *(Details needed on how tasks are created, assigned, and monitored in the current system)*

## Key Paths & Files (DRAFT)
- **`src/dreamos/`**: Core source code.
    - `agents/`: Agent implementations.
    - `core/`: Core utilities (coordination, utils, etc.).
    - `tools/`: Agent tools (analysis, file ops, search).
    - `config.py`: Main configuration.
    - `main.py` / `cli.py` / `orchestrator.py`: Potential entry points/controllers.
- **`runtime/`**: Runtime data (cache, state, logs - TBC).
    - `local_blob/processed/`: (If still used) Task results.
- **`logs/`**: Log files (e.g., `agent.log`).
- **`docs/`**: Documentation.
- **`tests/`**: Unit and integration tests.
- **`project_analysis.json`**: Output of the project scanner.
- **`chatgpt_project_context.json`**: Context export for LLMs.
- **`dependency_cache.json`**: File hash cache for the scanner.

## GUI Dashboard (DRAFT)
*(Verify existence, location, and features)*
- If a dashboard exists (e.g., in `src/dreamos/dashboard/` or `ui/`), update instructions for installation and launch.
- Describe current features and relevant configuration/data paths.

## Agent Autonomy Concepts (DRAFT)
- *(Explain how agents initiate actions or select tasks)*
- Examples:
    - Responding to specific messages on the `AgentBus`.
    - Monitoring filesystem locations for new inputs.
    - Following predefined schedules or triggers.
    - Proactive analysis based on system state.

## Tips & Support (DRAFT)
- Check `logs/agent.log` for detailed structured logs.
- Configure logging levels and settings in *(location TBC)*.
- *(Add current relevant tips)*
- Questions or issues? Open an issue in the repo.

## Contributing & Feedback (DRAFT)
- *(Describe current process for suggesting changes or reporting issues, likely via GitHub issues/PRs)*

Enjoy building with Dream.OS! 🚀