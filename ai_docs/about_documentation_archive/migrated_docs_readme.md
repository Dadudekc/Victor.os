# Dream.os: An Agentic Automation Platform

**Dream.os** is an experimental platform designed for developing and
coordinating intelligent software agents. It functions as a specialized
environment or "Operating System" enabling agent swarms to automate complex
tasks, particularly those involving software development, LLM interaction, and
external tool integration (like the Cursor editor).

## Overview

The system features:

- **Core Coordination:** A central engine (`core/`) manages agent lifecycle,
  communication (via `AgentBus`), task execution, and shared services.
- **Agent Implementations:** A dedicated directory (`agents/`) holds various
  specialized agents built upon a base class
  (`core/coordination/base_agent.py`).
- **Modular Applications:** Higher-level applications or operational modes built
  on the core platform, including:
  - `social`: Focuses on marketing/social media tasks.
  - `dreamforge`: Potentially handles Discord integration and specific
    workflows.
  - `dream_mode`: Enables unattended execution, possibly managing multiple
    environments or Cursor instances.
- **Integrations:** Connects with external tools and services like LLMs
  (`core/llm`), web browsers (`core/utils/browser_controller`), and Cursor
  (`integrations/`).
- **Monitoring:** Includes UI components (`ui/`) for visualizing tasks.

## Project Status (As of 2025-04-18)

**Current Phase: Refactoring and Core System Stabilization**

Following initial development, the project has undergone significant refactoring
to:

- Consolidate core logic and services under the `core/` directory.
- Deduplicate utility functions.
- Organize integrations, UI components, documentation, and configuration more
  logically.
- Establish a clear structure for agent implementations.

The focus is currently on solidifying this improved architecture. Key next steps
likely involve:

- Implementing actual LLM calls in `core/llm/llm_bridge.py`.
- Ensuring seamless integration between the core system and specialized modules
  (`dream_mode`, `dreamforge`, `social`).
- Reviewing and potentially integrating or deprecating the legacy(?)
  `_agent_coordination` module.
- Refining agent capabilities and task execution workflows.

## Requirements

- Python 3.x
- Dependencies managed via Poetry in `pyproject.toml`. After installing Poetry
  (e.g., `pip install poetry`), run `poetry install` to set up the environment.

## Installation

1.  Clone the repository:

    ```bash
    git clone <repository-url>
    cd Dream.os
    ```

2.  Create and activate a virtual environment (recommended):

    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On Unix or MacOS
    source venv/bin/activate
    ```

3.  Install the required dependencies:
    ```bash
    poetry install
    ```

## Running the Application / Showcase

**NOTE:** The main PyQt5 GUI (`main.py`) launches a _basic placeholder window_.
The original GUI was affected by refactoring. Use the following commands to
showcase current functionality:

1.  **Run the Test & Simulation Mode:** This simulates agent actions within the
    placeholder GUI, logs events to the structured event log
    (`runtime/structured_events.jsonl`), and adds a test task to
    `task_list.json`.

    ```bash
    python main.py --test
    ```

2.  **Run the Task Visualizer:** This displays the contents of `task_list.json`
    (including the task added by the test mode) in a web interface. Requires
    `streamlit` and `pandas` installed (`pip install streamlit pandas`).

    ```bash
    streamlit run ui/task_visualizer_app.py
    ```

3.  **(Optional) Launch Basic GUI:** To see the placeholder main window:
    ```bash
    python main.py
    ```

_(Check other modules like `dreamforge/main.py` for potential entry points to
other functionalities.)_

## Project Structure Highlights

- `main.py`: Potential main entry point.
- `core/`: Foundational services, coordination, utilities, LLM bridge.
- `agents/`: Implementations of specific agents.
- `integrations/`: Code for interacting with external tools (Cursor, etc.).
- `ui/`: User interface components (e.g., task visualizer).
- `config/`: Configuration files, task definitions.
- `docs/`: Project documentation, planning, analysis reports.
- `scripts/`: Utility and helper scripts.
- `runtime/`: Directory for runtime files (logs, event files).
- `templates/`, `prompts/`: Default directories for Jinja templates and LLM
  prompts.
- `dreamforge/`, `social/`, `dream_mode/`: Specific application modules or
  operational modes.
- `_agent_coordination/`: Older(?) or parallel coordination system (requires
  review).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

_(Assuming MIT based on previous content - confirm or update)_ This project is
licensed under the MIT License - see the LICENSE file for details.
