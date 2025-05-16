Dream.OS Command Dashboard

A PyQt5-based mission control panel for supervising Cursor-based Dream.OS agents, verifying project progress, and enforcing system standards.

This dashboard doesn’t launch or manage agent processes. It monitors the behavior of 8 AI agents, each running in a separate Cursor IDE chat window, using filesystem-based status reports and activity logs.

⸻

System Architecture

Dream.OS agents are Cursor-based ChatGPT clients.
Each agent operates through a shared protocol:
	•	Their mailbox directory is their workspace — not a message queue.
	•	They claim tasks from shared project/task boards and store them in their own inbox.json to signal ownership.
	•	Each agent maintains a live devlog.md to record decisions, progress, and loop state.
	•	Agents must define verification steps with each task they complete.

The dashboard monitors this structure, enabling humans (or the swarm) to spot idle agents, verify task state, and identify stale loops.

⸻

Features

1. Agent Management Tab
	•	Displays all agents (Agent-1 through Agent-8)
	•	Checks last devlog.md entry to measure agent health
	•	Displays claimed tasks from inbox.json
	•	Resume automation via resume_controller.py using PyAutoGUI
	•	Trigger onboarding/init prompts into agent workspace

2. Project Analysis Tab
	•	Loads metadata from chatgpt_project_context.json
	•	Highlights file stats, orphan detection, and structural gaps
	•	Surfaces files lacking tests or runnable validation hooks
	•	Displays dependency map from dependency_cache.json

3. (Upcoming) Task Board Tab
	•	Shows the shared backlog and in-progress tasks
	•	Highlights who claimed what and verification status
	•	Scoreboard for point-based agent competition
	•	Tracks each task’s:
	•	Status
	•	Owner
	•	how_to_verify instructions

4. (Upcoming) Discord Commander Tab
	•	Trigger resume/onboard commands via Discord bot
	•	Edit prompt templates live from UI
	•	Monitor bridge outbox responses from agents

⸻

Agent Workspace Structure

Each agent has a dedicated folder:

runtime/agent_comms/agent_mailboxes/Agent-<N>/
│
├── inbox.json       # Tasks the agent has claimed (their to-do)
├── devlog.md        # Rolling log of actions, thoughts, and status
├── scratchpad/      # Optional: Notes, diagrams, drafts

	•	Inbox is agent-owned storage for their claimed work.
	•	Tasks must be moved here once claimed to prevent duplication.
	•	Every task must include a "how_to_verify" field so other agents (or the Captain) can confirm its validity.

⸻

Verification Protocol

Every task completion must:
	•	Include steps to verify success (how_to_verify)
	•	Reference runnable files, tests, or scripts
	•	Be self-contained and error-free, with zero tolerance for theoretical or broken contributions

Examples of valid task verification:
	•	"Run test suite: pytest tests/test_task_parser.py"
	•	"Open docs/dashboard/README.md and confirm all sections render in GUI"
	•	"Trigger THEA loop with task_id and confirm agent chain response"

⸻

Setup

pip install -r requirements.txt
python agent_dashboard.py


⸻

File Structure
	•	agent_dashboard.py – PyQt5 app entrypoint
	•	ui/ – All GUI widgets (per-tab)
	•	data_providers/ – File parsing and state checking
	•	runtime/agent_comms/ – Agent workspaces (inboxes, devlogs)
	•	chatgpt_project_context.json – Project architecture overview
	•	project_analysis.json – File-level stats and alerts
	•	dependency_cache.json – Import/dependency graph

⸻

Final Notes
	•	The dashboard doesn’t control agents — it monitors and nudges
	•	Agent workspaces are visible, shared, and subject to review
	•	All contributions must be provably valid, not just theoretical
	•	The devlog.md and inbox.json must be kept updated per agent loop cycle
