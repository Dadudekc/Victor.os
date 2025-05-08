# DreamOS Tools

This directory provides a collection of tools and utilities for DreamOS agents and system operations.

## Purpose

To offer a structured repository for various specialized tools that agents can leverage for tasks such as code analysis, system maintenance, discovery, coordination, and interaction with external systems (e.g., GUIs, APIs).

## Tool Categories (Subdirectories)

*   `_core/`: Base classes and registration for tools.
*   `analysis/`: Tools for codebase analysis (e.g., project scanning, dead code detection).
*   `calibration/`: Tools related to GUI calibration and coordinate management.
*   `code_analysis/`: (Purpose TBD - currently empty or contents unknown)
*   `coordination/`: Tools to facilitate inter-agent coordination or broadcast directives.
*   `cursor_bridge/`: Tools specifically for interacting with or managing the Cursor bridge.
*   `discovery/`: Tools for finding information within the codebase or system (e.g., finding TODOs, defunct tests).
*   `dreamos_utils/`: General utilities specific to DreamOS operations.
*   `functional/`: Tools providing higher-level functional capabilities (e.g., GUI interaction, context planning).
*   `maintenance/`: Scripts and tools for system maintenance tasks (e.g., archiving, log validation).
*   `scripts/`: General-purpose scripts (contents may vary).
*   `validation/`: Tools for validation tasks (e.g., dependency checks, GUI coordinate validation).

## Standalone Tools (Files)

*   `command_supervisor.py`: (Purpose TBD - likely supervises command execution)
*   `thea_relay_agent.py`: (Purpose TBD - likely related to THEA integration or relaying)

## Contribution

New tools should be placed in an appropriate subdirectory or a new one if a suitable category doesn't exist. Ensure tools are well-documented and, where applicable, include test cases. 