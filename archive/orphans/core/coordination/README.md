# DreamOS Core Coordination

This directory contains the core logic and data structures for agent coordination, communication, and lifecycle management within the DreamOS.

## Purpose

To provide the foundational mechanisms that enable agents to interact, share information, manage tasks, and operate cohesively as a swarm.

## Key Modules & Concepts

*   `agent_bus.py`: Implements the central message bus for inter-agent communication.
*   `base_agent.py`: Provides the base class and core lifecycle logic for all DreamOS agents.
*   `project_board_manager.py`: Manages the central task board and project state.
*   `event_payloads.py` & `event_types.py`: Define the structure and types of events and messages that flow through the system.
*   `message_patterns.py`: Likely defines common communication patterns or protocols.
*   `enums.py`: Contains enumerations used within the coordination logic.
*   `base_agent_lifecycle.py`: Likely defines or supports the lifecycle states and transitions for agents.
*   `schemas/`: Contains schemas for validating coordination-related data structures.

## Overview

The components in this directory are critical for the functioning of the DreamOS. They handle how agents are initialized, how they send and receive messages, how tasks are assigned and tracked, and the overall flow of information within the agent swarm.
