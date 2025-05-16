import json
import os
from datetime import datetime
from pathlib import Path


def get_agent_metrics():
    """Get metrics for all agents from their manifests."""
    metrics = []
    agent_dir = Path("runtime/agent_comms/agent_mailboxes")
    
    # Get all agent directories
    agent_dirs = [d for d in agent_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    for agent_dir in agent_dirs:
        manifest_path = agent_dir / "agent_manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)
                metrics.append({
                    "agent_id": manifest["agent_id"],
                    "metrics": manifest["metrics"],
                    "active_proposals": manifest["active_proposals"]
                })
    
    return metrics

def update_agent_metrics(agent_id, metric_type, value):
    """Update metrics for a specific agent."""
    manifest_path = Path(f"runtime/agent_comms/agent_mailboxes/{agent_id}/agent_manifest.json")
    
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        # Update metric
        if metric_type in manifest["metrics"]:
            manifest["metrics"][metric_type] = value
        
        # Update timestamp
        manifest["last_updated"] = datetime.utcnow().isoformat()
        
        # Save updated manifest
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return True
    return False

def add_proposal(agent_id, proposal):
    """Add a new proposal to an agent's manifest."""
    manifest_path = Path(f"runtime/agent_comms/agent_mailboxes/{agent_id}/agent_manifest.json")
    
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        # Add proposal
        manifest["active_proposals"].append(proposal)
        
        # Update metrics
        manifest["metrics"]["proposals_authored"] += 1
        
        # Update timestamp
        manifest["last_updated"] = datetime.utcnow().isoformat()
        
        # Save updated manifest
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return True
    return False

def record_vote(agent_id, proposal_id, vote):
    """Record a vote in an agent's manifest."""
    manifest_path = Path(f"runtime/agent_comms/agent_mailboxes/{agent_id}/agent_manifest.json")
    
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        # Update metrics
        manifest["metrics"]["votes_cast"] += 1
        
        # Update timestamp
        manifest["last_updated"] = datetime.utcnow().isoformat()
        
        # Save updated manifest
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return True
    return False

def record_bug_fix(agent_id):
    """Record a bug fix in an agent's manifest."""
    manifest_path = Path(f"runtime/agent_comms/agent_mailboxes/{agent_id}/agent_manifest.json")
    
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        # Update metrics
        manifest["metrics"]["bugs_fixed"] += 1
        manifest["metrics"]["points_earned"] += 10  # Award points for bug fixes
        
        # Update timestamp
        manifest["last_updated"] = datetime.utcnow().isoformat()
        
        # Save updated manifest
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return True
    return False 