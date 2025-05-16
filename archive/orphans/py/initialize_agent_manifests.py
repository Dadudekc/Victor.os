import json
import os
from datetime import datetime
from pathlib import Path


def create_agent_manifest(agent_id, domain, responsibilities):
    """Create a new agent manifest."""
    manifest = {
        "manifest_version": "1.0.0",
        "agent_id": agent_id,
        "role": {
            "title": "Senior Developer & Co-Founder",
            "domain": domain,
            "responsibilities": responsibilities
        },
        "metrics": {
            "proposals_authored": 0,
            "votes_cast": 0,
            "bugs_fixed": 0,
            "points_earned": 0,
            "reputation_score": 0
        },
        "active_proposals": [],
        "pending_votes": [],
        "knowledge_base": {
            "articles": [],
            "contributions": []
        },
        "architecture_decisions": [],
        "last_updated": datetime.utcnow().isoformat()
    }
    return manifest

def initialize_agent_manifests():
    """Initialize manifests for all agents."""
    agent_dir = Path("runtime/agent_comms/agent_mailboxes")
    
    # Agent configurations
    agent_configs = {
        "Agent-1": {
            "domain": "Core Functionality",
            "responsibilities": [
                "System architecture",
                "Core implementation",
                "Performance optimization",
                "Code review"
            ]
        },
        "Agent-2": {
            "domain": "System Health",
            "responsibilities": [
                "Health monitoring",
                "Safety protocols",
                "Error recovery",
                "System stability"
            ]
        },
        "Agent-3": {
            "domain": "Task Management",
            "responsibilities": [
                "Task distribution",
                "Workflow optimization",
                "Resource allocation",
                "Progress tracking"
            ]
        },
        "Agent-4": {
            "domain": "Validation",
            "responsibilities": [
                "Quality assurance",
                "Compliance checking",
                "Validation protocols",
                "Standards enforcement"
            ]
        },
        "Agent-5": {
            "domain": "Coordination",
            "responsibilities": [
                "Operation coordination",
                "Resource management",
                "Progress tracking",
                "Escalation handling"
            ]
        },
        "Agent-6": {
            "domain": "Analysis",
            "responsibilities": [
                "Performance analysis",
                "Improvement identification",
                "Pattern recognition",
                "Learning documentation"
            ]
        },
        "Agent-7": {
            "domain": "Communication",
            "responsibilities": [
                "Communication management",
                "Message routing",
                "Connection maintenance",
                "Traffic monitoring"
            ]
        },
        "Agent-8": {
            "domain": "Knowledge",
            "responsibilities": [
                "Documentation",
                "Knowledge management",
                "Change tracking",
                "History preservation"
            ]
        },
        "commander-THEA": {
            "domain": "Command & Control",
            "responsibilities": [
                "System command",
                "Strategic decisions",
                "Resource allocation",
                "Mission control"
            ]
        },
        "Captain-THEA": {
            "domain": "Coordination",
            "responsibilities": [
                "High-level coordination",
                "Strategic planning",
                "Resource management",
                "Mission success"
            ]
        },
        "VALIDATOR": {
            "domain": "Validation",
            "responsibilities": [
                "System-wide validation",
                "Quality assurance",
                "Compliance checking",
                "Standards enforcement"
            ]
        },
        "ORCHESTRATOR": {
            "domain": "Orchestration",
            "responsibilities": [
                "Task orchestration",
                "Workflow management",
                "Resource coordination",
                "System harmony"
            ]
        },
        "JARVIS": {
            "domain": "Core Operations",
            "responsibilities": [
                "Core system operations",
                "Resource management",
                "Performance optimization",
                "System stability"
            ]
        },
        "general-victor": {
            "domain": "System Management",
            "responsibilities": [
                "General system management",
                "Resource allocation",
                "Performance monitoring",
                "System optimization"
            ]
        }
    }
    
    # Create manifests for each agent
    for agent_id, config in agent_configs.items():
        agent_path = agent_dir / agent_id
        if agent_path.exists():
            manifest = create_agent_manifest(
                agent_id,
                config["domain"],
                config["responsibilities"]
            )
            
            manifest_path = agent_path / "agent_manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            print(f"Created manifest for {agent_id}")

if __name__ == "__main__":
    initialize_agent_manifests() 