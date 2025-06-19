# Victor.os (Dream.OS) 🧠🐝

> **TL;DR**: Victor.os is an AI-native, multi-agent operating system for orchestrating LLM-powered agents—with self-healing automation, Cursor/ChatGPT integration, and a live PyQt dashboard.  
> **For**: Builders, automation architects, and AI toolmakers who want to go beyond “single agent” scripts and design swarms of collaborating AI workers.

---

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![LLM-integrated](https://img.shields.io/badge/LLM-integrated-brightgreen)](#)
[![Build Passing](https://img.shields.io/badge/build-passing-success)](#)
[![PyQt5 Dashboard](https://img.shields.io/badge/dashboard-PyQt5-informational)](#)

---

## 📦 What’s Inside

- **AI Agent Swarm**: Orchestrate 8+ agents (ChatGPT/Cursor) in parallel, each with its own workspace, devlog, and verification protocol.
- **Self-healing Loops**: Agents retry, verify, and auto-patch their own workflows.
- **Command Dashboard**: PyQt5 GUIs to monitor, nudge, and visualize the swarm.
- **Plug & Play Microtools**: Modular spin-offs and starter templates for scaling custom agents.
- **Protocol-Driven**: All communication follows hash-based integrity, chunked messaging, and verifiable task completion.

---

## 🏗️ Architecture Map

![diagram](ai_docs/architecture/diagrams/system_overview.png)

- **Agents**: Run in separate Cursor IDE chats, each with a unique mailbox/inbox, devlog, and scratchpad.
- **Dashboard**: Mission control for agent health, project analysis, and task board (PyQt5 GUI). See `apps/dashboard/`.
- **Event System**: Loops every 180s, tools in 5s chunks, resources wrap up every 1800s.
- **Verification**: All agent outputs must be verifiable—either via tests, file checks, or explicit step-by-step instructions.
- **Spin-offs**: Start with `spin_offs/self_healing_swarm_template/` or `spin_offs/auto_prompt_generator/` for rapid prototyping.

---

## 🚀 Quickstart

1. **Install requirements** (for dashboard):
   ```bash
   cd apps/dashboard
   pip install -r requirements.txt
   python agent_dashboard.py
   ```

2. **Agent Setup**:  
   Launch 8 Cursor (ChatGPT) sessions, each mapped to a mailbox directory (`runtime/agent_comms/agent_mailboxes/Agent-<N>/`).

3. **Monitor & Nudge**:  
   Use the dashboard for:
   - Agent health & progress
   - Project analysis (file stats, dependency map, orphan detection)
   - Task board (who owns what, status, verification steps)
   - (Upcoming) Discord integration for remote triggers

4. **Verification**:  
   All tasks must include a `how_to_verify` field. Examples:
   - “Run test suite: pytest tests/test_task_parser.py”
   - “Open docs/dashboard/README.md and confirm all sections render in GUI”
   - “Trigger THEA loop and confirm agent chain response”

---

## 🛠️ Feature Highlights

- **Self-Healing Agent Swarm**: Robust retries, hash checks, and error correction.
- **Live Dashboard (PyQt5)**: Real-time agent supervision, task claims, and health metrics.
- **LLM Patch Loop**: Agents can auto-improve workflow by analyzing failures and proposing code patches.
- **Cursor GUI Automation**: Resume or onboard agents via PyAutoGUI.
- **Plug-in Microtools**: Easily extend with new agent types or prompt generators.

---

## 🗂️ Project Structure (Partial)

```
/docs/                 # Project documentation
/runtime/              # Runtime configs, agent mailboxes
/src/                  # Source code
/apps/dashboard/       # PyQt5 dashboard
/ai_docs/architecture/ # Architecture maps, proposals, designs
/spin_offs/            # Microtools & starter templates
```

---

## 📸 Demo

> Want to record a demo?  
> 1. Launch dashboard and agent swarm  
> 2. Use OBS (free) to record “agent claims task → completes → dashboard updates”  
> 3. Save as demo.gif and drop here!

---

## 📚 More Docs

- **Architecture**: See [`ai_docs/architecture/`](ai_docs/architecture/README.md)
- **Dashboard Usage**: See [`apps/dashboard/README.md`](apps/dashboard/README.md)
- **Spin-Off Templates**: See [`spin_offs/`](spin_offs/)

---

## 🤝 Contributing

- PRs welcome!
- For architecture/design docs, follow conventions in `ai_docs/architecture/README.md`
- All code must pass verification protocols—no theoretical contributions.

---

## 🧑‍💻 Author

Built by Dadudekc — “AI-native automation architect. I build tools with ChatGPT to move faster than teams.”

---

## 🏷️ License

MIT — see [LICENSE](./LICENSE)
