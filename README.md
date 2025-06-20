# Victor.os (Dream.OS)

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

Victor.os is an AI-native operating system for orchestrating swarms of LLM-powered agents. Each agent runs in its own workspace, communicates through a file-based message bus, and follows a strict verification protocol. A PyQt dashboard lets you monitor progress, nudge agents, and visualize project metrics.
**Project Status**

This project is under active development and many components are experimental. Expect rough edges and frequent changes.


## Key Features
- **Multi-agent coordination** via a mailbox/message-bus protocol
- **Self‑healing loops** that retry, verify, and auto‑patch workflows
- **PyQt5 dashboard** for real‑time monitoring and task management
- **Cursor/ChatGPT bridge** to automate the IDE and gather responses
- **Project scanner** that analyzes the codebase and generates context files for AI assistants

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
```text
Victor.os/
├── apps/
│   └── dashboard/
├── docs/
├── runtime/
│   ├── agent_comms/
│   └── logs/
├── src/
│   ├── apps/
│   ├── bridge/
│   └── ...
├── tests/
├── spin_offs/
└── ...
```

## What This Demonstrates
- End-to-end automation with Python and LLM-based agents
- Design of resilient, verifiable agent loops and a monitoring dashboard
- Experience building tooling around AI-driven workflows

## License
MIT – see [LICENSE](./LICENSE)
