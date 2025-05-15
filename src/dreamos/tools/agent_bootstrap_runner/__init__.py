"""
Dream.OS Universal Agent Bootstrap Runner

A modular implementation of the agent bootstrap process that works with any agent (0-8).
This runner handles:
- Agent-specific configuration and validation
- UI interaction (cursor injection and response retrieval)
- Message processing and archiving
- Logging and monitoring
- Protocol enforcement
- Autonomy management and monitoring
- Dry-run simulation capabilities

Usage:
    from dreamos.tools.agent_bootstrap_runner import AgentConfig, agent_loop
    
    config = AgentConfig(agent_id="Agent-N")  # N = 0-8
    await agent_loop(config)
"""

from .config import AgentConfig
from .runner import AgentBootstrapRunner, agent_loop
from .messaging import publish_event, archive_inbox, load_inbox
from .validation import validate_coords, validate_json_file, validate_all_files, ValidationResult
from .ui_interaction import CursorInjector, ResponseRetriever
from .logging_setup import setup_logging
from .dry_run_simulator import simulate_agent_bootstrap
from .resume_autonomy_loop import AgentStatus, resume_agent, monitor_agent_status
from .onboarding import AgentOnboardingManager
from .cursor_messaging import CursorAgentMessenger
from .inbox_management import create_seed_inbox, update_inbox_with_prompt

__version__ = "1.0.0"
__all__ = [
    "AgentConfig",
    "AgentBootstrapRunner",
    "agent_loop",
    "publish_event",
    "archive_inbox",
    "load_inbox",
    "validate_coords",
    "validate_json_file", 
    "validate_all_files",
    "ValidationResult",
    "CursorInjector",
    "ResponseRetriever",
    "setup_logging",
    "simulate_agent_bootstrap",
    "AgentStatus",
    "resume_agent",
    "monitor_agent_status",
    "AgentOnboardingManager",
    "CursorAgentMessenger",
    "create_seed_inbox",
    "update_inbox_with_prompt"
] 