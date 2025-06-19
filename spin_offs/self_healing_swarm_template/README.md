# Self-Healing Agent Swarm Starter Template

This starter template helps teams running multiple Cursor-based agents quickly spin up a
minimal Dream.OS swarm with built-in self-healing features. It demonstrates how to use the
`StableAutonomousLoop` from `dreamos.skills.lifecycle` so each agent can recover from
interruptions and continue processing tasks.

## Features
- **Cursor Integration** – Each agent communicates via a Cursor chat window and monitors its
  status through local log files.
- **Stable Loop** – Agents run on the `StableAutonomousLoop` to detect drift, enforce
  watchdog timeouts and automatically enter degraded mode when errors occur.
- **Simplified Configuration** – A sample `config.yaml` defines agent IDs and workspaces so
you can expand the swarm quickly.

## Quick Start
1. Copy this directory into your project.
2. Run `python agent_swarm_template.py` to launch a small swarm of agents (default: 3).
3. Each agent creates a local `logs/agent-<n>.log` file where you can monitor health and
   self-healing actions.

## Extending
- Modify `agent_swarm_template.py` to hook into your existing task board or messaging system.
- Use Cursor’s chat history to debug individual agents when they enter degraded mode.

This template is intentionally small so you can adapt it to your organization’s workflow.
