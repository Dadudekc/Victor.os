# Victor.os (Dream.OS)

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

Victor.os is an **experimental** attempt at an AI-native operating system for orchestrating swarms of LLM‑powered agents. Many parts are half-finished research experiments, so expect to do a fair amount of manual setup and tinkering. Agents communicate through a file-based message bus and a PyQt dashboard provides basic monitoring.

### Current Status
- Many directories contain early experiments or archived work.
- Full end‑to‑end automation is *not* guaranteed to run smoothly.
- Expect manual steps when coordinating agents or launching tools.
- Configuration files under `runtime/` often need to be created or edited by hand.
- Several utilities reference API keys or credentials not included in the repo.
- UI automation scripts rely on **PyAutoGUI** and may need manual coordinate calibration.

> **Note**: The project is in flux and should be considered a research prototype rather than a production-ready system.

## Key Features
- **Multi-agent coordination** via a mailbox/message-bus protocol
- **Self‑healing loops** that retry, verify, and auto‑patch workflows
- **PyQt5 dashboard** for real‑time monitoring and task management
- **Cursor/ChatGPT bridge** to automate the IDE and gather responses
- **PyAutoGUI-based automation** for simulating mouse/keyboard actions
- **Project scanner** that analyzes the codebase and generates context files for AI assistants
- **Universal bootstrap runner** to launch and monitor any agent
- **Semantic search tool** combining embeddings with fuzzy matching
- **Metrics subsystem** for tracking agent performance and resource use
- **Social media integration** for lead discovery and task generation
- **Swarm controller** with tests to orchestrate coordinated agent cycles

## Setup
1. Clone the repository
2. Install core dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Install dashboard extras:
   ```bash
   cd apps/dashboard
   pip install -r requirements.txt
   ```
4. Run the test suite:
   ```bash
   pytest
   ```

## Usage
Launch the bootstrapper to start agents or run the dashboard directly:
```bash
python run_bootstrapper.py
# or
cd apps/dashboard && python agent_dashboard.py
```

## Architecture
```
User -> [PyQt Dashboard] -> [Message Bus] -> [Agent Loops] -> [Cursor/LLM Bridge]
                                 ^                 |
                                 |                 v
                           [Project Scanner]   [Verification]
```
Agents maintain `inbox.json` and `devlog.md` files inside `runtime/agent_comms/`. The message bus coordinates tasks and status updates, while the bridge handles ChatGPT/Cursor interactions. The project scanner provides structured context for the agents and for human oversight.

## Project Structure
The repository is quite large and still evolving.  Below is a trimmed view of the
top‑level layout, followed by a peek inside a few key directories:
```
.
├── ai_docs/               - architecture diagrams and planning docs
├── apps/                  - small apps including the PyQt dashboard
├── archive/               - old snapshots and experiments
├── basicbot/              - minimal agent prototypes
├── docs/                  - additional documentation
├── dreamos/               - core library code
├── dreamos_ai_organizer/  - planning tool for agent coordination
├── dreamos_clean/         - cleaned-up experimental variant
├── episodes/              - logs of development sessions
├── frontend/              - experimental UI prototypes
├── logins/                - credentials and tokens (local use only)
├── prompts/               - prompt templates and system messages
├── runtime/               - runtime state (mailboxes, logs, task boards)
├── sandbox/               - throwaway experiments and demos
├── scripts/               - helper scripts
├── specs/                 - design specifications
├── spin_offs/             - microtool templates
├── src/                   - main Python packages
├── tests/                 - unit tests
└── tools/                 - command line utilities
```

Expanded view of some important directories:
```
apps/
    dashboard/
src/
    apps/
        agent_004/
    bridge/
    dreamos/
        agents/
        automation/
        tools/
    runtime/
        config/
        prompts/
runtime/
    agent_comms/
    logs/
tests/
    agents/
    core/
```

## What This Demonstrates
- End-to-end automation with Python and LLM-based agents
- Design of resilient, verifiable agent loops and a monitoring dashboard
- Experience building tooling around AI-driven workflows

## License
MIT – see [LICENSE](./LICENSE)
