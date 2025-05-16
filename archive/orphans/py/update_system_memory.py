import json
from datetime import datetime
from pathlib import Path


def log_architecture_decision(component, decision_type, rationale, agent_id):
    """Log an architecture decision to the system memory ledger."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": "architecture_decision",
        "component": component,
        "decision_type": decision_type,
        "rationale": rationale,
        "agent_id": agent_id
    }
    return entry

def log_proposal_origin(proposal_id, title, rationale, agent_id):
    """Log a proposal origin to the system memory ledger."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": "proposal_origin",
        "proposal_id": proposal_id,
        "title": title,
        "rationale": rationale,
        "agent_id": agent_id
    }
    return entry

def log_historical_reasoning(pattern, alternatives, outcome, agent_id):
    """Log historical reasoning to the system memory ledger."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": "historical_reasoning",
        "pattern": pattern,
        "alternatives_considered": alternatives,
        "outcome": outcome,
        "agent_id": agent_id
    }
    return entry

def append_to_ledger(entry):
    """Append an entry to the system memory ledger."""
    ledger_path = Path("runtime/governance/system_memory_ledger.jsonl")
    
    # Create directory if it doesn't exist
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Append entry to ledger
    with open(ledger_path, 'a') as f:
        f.write(json.dumps(entry) + '\n')

def update_agent_manifest(agent_id, entry_type, details):
    """Update agent manifest with new activity."""
    manifest_path = Path(f"runtime/agent_comms/agent_mailboxes/{agent_id}/agent_manifest.json")
    
    if not manifest_path.exists():
        return
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    # Update metrics based on entry type
    if entry_type == "architecture_decision":
        manifest["metrics"]["points_earned"] += 5
        manifest["architecture_decisions"].append(details)
    elif entry_type == "proposal_origin":
        manifest["metrics"]["proposals_authored"] += 1
        manifest["metrics"]["points_earned"] += 10
        manifest["active_proposals"].append(details)
    elif entry_type == "historical_reasoning":
        manifest["metrics"]["points_earned"] += 3
        manifest["knowledge_base"]["contributions"].append(details)
    
    # Update timestamp
    manifest["last_updated"] = datetime.utcnow().isoformat()
    
    # Save updated manifest
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

def record_activity(entry_type, agent_id, **details):
    """Record an activity in both the system memory ledger and agent manifest."""
    # Create appropriate entry
    if entry_type == "architecture_decision":
        entry = log_architecture_decision(
            details["component"],
            details["decision_type"],
            details["rationale"],
            agent_id
        )
    elif entry_type == "proposal_origin":
        entry = log_proposal_origin(
            details["proposal_id"],
            details["title"],
            details["rationale"],
            agent_id
        )
    elif entry_type == "historical_reasoning":
        entry = log_historical_reasoning(
            details["pattern"],
            details["alternatives"],
            details["outcome"],
            agent_id
        )
    else:
        raise ValueError(f"Unknown entry type: {entry_type}")
    
    # Append to ledger
    append_to_ledger(entry)
    
    # Update agent manifest
    update_agent_manifest(agent_id, entry_type, details)

if __name__ == "__main__":
    # Example usage
    record_activity(
        "architecture_decision",
        "Agent-1",
        component="Component X",
        decision_type="reuse",
        rationale="Reusing existing component to reduce code duplication"
    )
    
    record_activity(
        "proposal_origin",
        "Agent-2",
        proposal_id="PROP-001",
        title="System Improvement Proposal",
        rationale="Optimizing system performance"
    )
    
    record_activity(
        "historical_reasoning",
        "Agent-3",
        pattern="Pattern X",
        alternatives=["Alternative A", "Alternative B"],
        outcome="Successfully implemented with swarm approval"
    ) 