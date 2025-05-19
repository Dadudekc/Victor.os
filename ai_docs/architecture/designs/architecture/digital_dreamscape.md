# Architecture: Digital Dreamscape Narrative Engine

**Task:** `DIGITAL-DREAMSCAPE-INIT-001`
**Status:** Proposed

## 1. Overview

This document outlines the architecture for the Digital Dreamscape, a system designed to automatically generate narrative content (episodes, lore) based on Dream.OS project activities and agent interactions, primarily leveraging Large Language Models (LLMs).

## 2. Core Concepts

*   **Episodes:** Self-contained narrative units summarizing events, task completions, or significant agent interactions.
*   **Lore:** Persistent background information (character bios, world details, project principles) used as context for generation.
*   **Data Sources:** Inputs for narrative generation, including task history, commit logs, agent logs, captain's logs, and onboarding documents.
*   **Narrative Engine:** The component responsible for gathering data, prompting the LLM, and processing/storing the output.
*   **Triggering:** Mechanism for initiating episode generation.

## 3. Proposed Architecture

1.  **Lore Repository (`runtime/dreamscape/lore/`)**
    *   Stores generated episodes as Markdown files (e.g., `episode_XXX_title.md`).
    *   May contain subdirectories for structured lore (e.g., `characters/`, `world/`).
    *   An `index.md` or `manifest.json` could track generated episodes.

2.  **Data Sources (Integration Required)**
    *   Task Board (Database via `DbTaskNexus`/`SQLiteAdapter`).
    *   Git History (`git log` command).
    *   Agent Logs (Filesystem: `runtime/logs/`).
    *   Captain's Logs (Filesystem: `runtime/governance/reports/`).
    *   Onboarding Docs (Filesystem: `runtime/governance/onboarding/` - contains subdirectories: `guides`, `protocols`, `prompts`, `contracts_and_configs`, `info`).

3.  **Narrative Engine (Implemented as Agent Capability)**
    *   **Capability ID:** `narrative.generate.episode`
    *   **Input:**
        *   `trigger_event_summary`: Text describing the main event (e.g., task completion details).
        *   `context_window`: Parameters to define the scope of data gathering (e.g., time range, related task IDs, commit range).
        *   `style_prompt`: Instructions for narrative tone/style.
    *   **Process:**
        1.  Parse `context_window` to identify relevant data points.
        2.  Fetch/read data from various sources (DB, git, logs, files).
        3.  Load relevant existing lore from the repository for context.
        4.  Synthesize gathered data and lore into a comprehensive prompt for an LLM.
        5.  Include instructions for narrative structure and style (`style_prompt`).
        6.  Call configured LLM API.
        7.  Parse response to extract the episode text.
        8.  Generate a suitable filename (e.g., based on trigger event or LLM suggestion).
        9.  Save episode to a new Markdown file in the Lore Repository.
        10. (Optional) Update index/manifest.
    *   **Output:** Path to the generated episode file.

4.  **Triggering Mechanism**
    *   **Initial:** Manual invocation (e.g., via CLI command calling the capability).
    *   **Future:** Automated triggers (Agent Bus event listeners for `TASK_COMPLETED`, periodic agent scans).

## 4. Key Implementation Details

*   **Data Gathering:** Requires functions to query the DB, run `git log`, parse log files, and read specific documentation files based on context.
*   **LLM Interaction:** Needs a configurable LLM client (`dreamos.core.llm.client`), prompt templating, and response parsing.
*   **Configuration:** LLM API details, style prompts, data source paths, lore repository path.

## 5. Next Steps (Implementation Tasks)

*   `DIGITAL-DREAMSCAPE-LORE-PARSER-002`: Focus on the data gathering and prompt construction logic.
*   Implement the `narrative.generate.episode` capability logic.
*   Implement LLM client interaction.
*   Develop initial manual trigger mechanism (e.g., CLI command).
*   Agent registers and uses the capability.
*   Agent Registry (Filesystem: `runtime/agent_registry/` - contains agent metadata, oaths, contracts).
*   Governance Docs:
    *   Protocols (Filesystem: `runtime/governance/protocols/`).
*   Logs (Filesystem: `runtime/logs/` - agent-specific, system, etc.).
*   Agent State (Filesystem: `runtime/agent_state/` - potentially JSON/pickle files). 