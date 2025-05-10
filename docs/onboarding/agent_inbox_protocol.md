# Agent Inbox Protocol: Understanding Your `inbox.json`

**Version:** 1.0
**Date:** {{CURRENT_DATE_YYYY-MM-DD}}
**Audience:** All Dream.OS Agents

## 1. Introduction: Your Inbox is Your Command Deck

Welcome, Agent! This document outlines the standard operating procedure for interacting with your assigned `inbox.json` file, located at `runtime/agent_comms/agent_mailboxes/Agent-<YourID>/inbox.json`.

Think of your `inbox.json` as your **Command Deck** or **Directives Feed**. It is your primary source for current tasks and assignments within an operational cycle or episode. It defines your *now-space*—what you need to focus on immediately.

It is **not** a ledger, a journal, or a place for you to permanently record task status or detailed logs. Those belong in designated logging systems or central task boards.

## 2. Key Characteristics of Your `inbox.json`

*   **Source of Truth for Current Tasks:** Your inbox contains an array of JSON objects, each representing a specific task or directive assigned to you.
*   **Auto-Generated & Refreshed:** Your `inbox.json` is automatically populated and managed by the `disperse_tasks.py` script. This script processes episode definitions (e.g., `episodes/episode-XX.yaml`) and distributes the relevant tasks to each agent.
*   **Subject to Overwrite:** Be aware that at the beginning of new episodes, or when task definitions are updated centrally, `disperse_tasks.py` will typically refresh (overwrite) your `inbox.json` with the new set of directives. **Do not rely on storing persistent agent-specific data or status modifications directly within this file.**

## 3. Understanding a Task Directive (Inbox Item Structure)

Each item in your `inbox.json` array is a task directive with the following key fields:

*   `prompt_id` / `id`: The unique identifier for this task.
*   `content`: The primary instruction; the description of what needs to be done.
*   `status`: The initial status of the task *as assigned* (e.g., "new", "Pending", or a status carried over from the episode definition like "Active"). You will report your *actual* progress externally.
*   `deps`: An array of task IDs that are prerequisites for this task.
*   `origin_episode`: The episode or mission this task belongs to, providing broader context.
*   `type`: Typically "instruction", indicating a task to be performed.
*   `timestamp`: When this task was dispersed into your inbox.
*   `owner`: Your Agent ID.
*   `points`: A relative measure of effort or priority.
*   *(Other custom fields as defined by the episode)*

## 4. Agent Operational Cycle with `inbox.json`

Follow this cycle for each operational loop:

1.  **Read `inbox.json`:** At the start of your work cycle, or when prompted by a `resume` signal, read the contents of your `runtime/agent_comms/agent_mailboxes/Agent-<YourID>/inbox.json` to understand your current directives.

2.  **Check Dependencies (`deps`):** For each task, review the `deps` field. Before starting a task, you must verify that all its prerequisite tasks have been completed. 
    *   **Verification Method:** Consult the central Project Plan (`specs/PROJECT_PLAN.md`) or any designated task board for the status of dependency tasks.
    *   **Blocked Tasks:** If dependencies are not met, report your task as "Blocked" (with reasons) to the central task tracking system and await resolution or further instructions. Do not proceed with a blocked task.

3.  **Execute `content` Directive:** Once dependencies are met (or if there are none), proceed to execute the task as described in the `content` field. Utilize your specialized skills, tools, and access to other system resources as required.

4.  **Report `status` Externally:** This is a critical step. After attempting or completing a task, you **MUST** report its final status (e.g., "Completed", "Failed", "In Progress if long-running and providing updates") to the **central task management system**. This is typically the `specs/PROJECT_PLAN.md` or an equivalent task board service.
    *   Your entry should clearly identify the task ID and its new status.
    *   This external reporting is vital because your `inbox.json` will be overwritten and does not serve as a persistent status log for the swarm.

5.  **Log Output/Lore:** Document your actions, observations, any significant data generated, errors encountered, and other relevant operational details (your "lore") in your designated agent-specific log file:
    *   Primary Log: `runtime/devlog/agents/Agent-<YourID>.md` (or as specified by current logging protocols).
    *   Ensure logs are timestamped and reference the relevant `prompt_id`.

6.  **Prepare for Overwrite/Refresh:** Once you have processed your current directives and reported their status, be prepared for your `inbox.json` to be refreshed by `disperse_tasks.py` in a subsequent cycle or with the start of a new episode. Your focus should then shift to the newly assigned tasks.

## 5. Summary: Your Role

*   **Receive & Understand:** Use `inbox.json` to understand your current orders.
*   **Execute Diligently:** Perform your tasks, respecting dependencies.
*   **Report Reliably:** Update the central system with your task outcomes.
*   **Log Thoroughly:** Maintain your agent-specific operational log.
*   **Adapt & Refresh:** Be ready for new directives in your inbox with each cycle.

By adhering to this protocol, you ensure smooth, coordinated operation within the Dream.OS swarm and contribute to overall mission success. 