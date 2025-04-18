# Supervisor Onboarding & Project Health Guide

Welcome! This guide outlines key processes for maintaining project health and managing agent tasks effectively within the Dream.os environment.

## 1. Project  & Task List

We utilize a custom `project_scanner` tool to analyze the codebase, identify areas for improvement, and extract actionable tasks directly from code comments. Regularly using this tool is crucial for project oversight.

**Running the Scanner:**

To get a snapshot of the project and generate reports, use the following command from the project root (`D:\Dream.os`):

```bash
python -m project_scanner.cli scan --project-root . [FLAGS]
```

**Common Flags:**

*   `--summarize`: Displays a summary snapshot in the console (including total files, complexity score, language breakdown, and *samples* of TODOs/FIXMEs).
*   `--save-task-list`: **(Recommended)** Generates/updates `TASKS.md` in the project root. This file contains the *complete* list of all `# TODO:` and `# FIXME:` comments found in the codebase, formatted as a checklist. This is your primary source for distributing granular tasks.
*   `--save-chatgpt-context`: Generates/updates `chatgpt_project_context.json`, providing detailed analysis data for potential use with LLMs.
*   `--ignore <path1> <path2> ...`: Excludes specific directories or files from the scan (e.g., `--ignore .venv temp_data`). *Currently, `.venv` is likely scanned and contains many vendor TODOs/FIXMEs; consider adding it to the ignore list for more focused project tasks.*

**Workflow:**

1.  Run the scanner regularly (e.g., daily or before planning agent work) with `--save-task-list`.
2.  Review the generated `TASKS.md`.
3.  Use this list to assign specific, actionable tasks to your agent team.

## 2. Maintaining Project Quality

Your primary responsibility is to ensure the project evolves professionally and avoids common pitfalls. Use the scanner outputs (`TASKS.md`, summary, complexity scores) to prioritize:

*   **Addressing TODOs/FIXMEs:** These are explicit tasks left by developers. Prioritize FIXMEs and high-impact TODOs.
*   **Reducing Complexity:** Investigate files listed with high complexity scores in the summary. Assign tasks to refactor or simplify these areas.
*   **Eliminating Placeholders:** Look for comments or code sections indicating temporary or incomplete implementations. Create tasks to replace them with robust solutions.
*   **Preventing Duplication:** Be vigilant for redundant code during reviews or when assigning related tasks. Encourage the use of shared modules and utilities.
*   **Ensuring Professionalism:** Guide agents towards writing clean, well-documented, and tested code. Discourage hacks or temporary workarounds.

## 3. Agent Task Management

*   **Assign Granular Tasks:** Use the items from `TASKS.md` to create specific, achievable tasks for individual agents.
*   **Keep Agents Busy:** Maintain a backlog of tasks derived from the scanner and project roadmap to ensure continuous progress.
*   **Track Progress:** Monitor the completion of tasks. As TODOs/FIXMEs are resolved in the code, subsequent runs of the scanner with `--save-task-list` will automatically update `TASKS.md`.

## 4. Key Project Focus: Mailbox System

*   **Status:** The previous supervisor began work on a new mailbox system, but it was left unfinished.
*   **Action:** This system needs assessment, planning, and development effort. Please familiarize yourself with any existing code or documentation related to the mailbox system and prioritize creating tasks to complete or revise it as necessary. Add relevant TODOs to the codebase for the scanner to pick up.

By consistently applying these processes, you can effectively guide the agent team and ensure the Dream.os project remains healthy, maintainable, and progresses towards a high-quality product. 