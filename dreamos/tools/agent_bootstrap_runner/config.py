"""
Configuration settings for Agent Bootstrap Runner
"""

import os
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Get project root
PROJECT_ROOT = Path(__file__).resolve().parents[4]  # src/dreamos/tools/agent2_bootstrap_runner -> Dream.os

# Default agent identity - can be overridden via CLI args
AGENT_ID: str = "Agent-1"  # Default agent for universal runner

# Validate agent number is in valid range
def validate_agent_id(agent_id: str) -> bool:
    """Validate agent ID is in the correct format and range."""
    try:
        if not agent_id.startswith("Agent-"):
            return False
        agent_num = int(agent_id.split("-")[1])
        return 1 <= agent_num <= 8  # Agent-0 is not valid
    except (ValueError, IndexError):
        return False

# Runtime configuration with env var overrides
# ... existing code ...

# Agent-specific traits and charters
AGENT_TRAITS = {
    "Agent-1": "Analytical, Logical, Methodical, Precise",
    "Agent-2": "Vigilant, Proactive, Methodical, Protective",
    "Agent-3": "Creative, Innovative, Intuitive, Exploratory",
    "Agent-4": "Communicative, Empathetic, Diplomatic, Persuasive",
    "Agent-5": "Knowledgeable, Scholarly, Thorough, Informative",
    "Agent-6": "Strategic, Visionary, Decisive, Forward-thinking",
    "Agent-7": "Adaptive, Resilient, Practical, Resourceful",
    "Agent-8": "Ethical, Balanced, Principled, Thoughtful"
}

AGENT_CHARTERS = {
    "Agent-1": "SYSTEM ARCHITECTURE",
    "Agent-2": "ESCALATION WATCH",
    "Agent-3": "CREATIVE SOLUTIONS",
    "Agent-4": "USER INTERACTION",
    "Agent-5": "KNOWLEDGE INTEGRATION",
    "Agent-6": "STRATEGIC PLANNING",
    "Agent-7": "IMPLEMENTATION",
    "Agent-8": "GOVERNANCE & ETHICS"
}

# ... existing code ... 