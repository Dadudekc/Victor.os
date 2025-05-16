import json
from datetime import datetime
from pathlib import Path


def get_agent_metrics():
    """Get metrics for all agents from their manifests."""
    agent_dir = Path("runtime/agent_comms/agent_mailboxes")
    metrics = []
    
    for agent_path in agent_dir.iterdir():
        if not agent_path.is_dir():
            continue
            
        manifest_path = agent_path / "agent_manifest.json"
        if not manifest_path.exists():
            continue
            
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
            
        metrics.append({
            "agent_id": manifest["agent_id"],
            "role": manifest["role"],
            "metrics": manifest["metrics"],
            "active_proposals": manifest["active_proposals"]
        })
    
    return metrics

def calculate_reputation_score(metrics):
    """Calculate reputation score based on agent metrics."""
    score = 0
    
    # Base points from metrics
    score += metrics["proposals_authored"] * 10
    score += metrics["votes_cast"] * 2
    score += metrics["bugs_fixed"] * 5
    score += metrics["points_earned"]
    
    # Bonus for active proposals
    score += len(metrics.get("active_proposals", [])) * 3
    
    return score

def update_scoreboard():
    """Update the scoreboard with latest agent metrics."""
    metrics = get_agent_metrics()
    
    # Calculate reputation scores
    for agent in metrics:
        agent["metrics"]["reputation_score"] = calculate_reputation_score(agent["metrics"])
    
    # Sort by reputation score
    metrics.sort(key=lambda x: x["metrics"]["reputation_score"], reverse=True)
    
    # Update scoreboard data
    scoreboard_path = Path("runtime/dashboard/scoreboard_data.json")
    scoreboard_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "last_updated": datetime.utcnow().isoformat(),
        "agents": metrics
    }
    
    with open(scoreboard_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    return data

def get_top_agents(limit=5):
    """Get top agents by reputation score."""
    metrics = get_agent_metrics()
    
    # Calculate reputation scores
    for agent in metrics:
        agent["metrics"]["reputation_score"] = calculate_reputation_score(agent["metrics"])
    
    # Sort and return top agents
    metrics.sort(key=lambda x: x["metrics"]["reputation_score"], reverse=True)
    return metrics[:limit]

def get_agent_stats():
    """Get aggregate statistics about agent activity."""
    metrics = get_agent_metrics()
    
    stats = {
        "total_agents": len(metrics),
        "total_proposals": sum(a["metrics"]["proposals_authored"] for a in metrics),
        "total_votes": sum(a["metrics"]["votes_cast"] for a in metrics),
        "total_bugs_fixed": sum(a["metrics"]["bugs_fixed"] for a in metrics),
        "total_points": sum(a["metrics"]["points_earned"] for a in metrics),
        "active_proposals": sum(len(a["active_proposals"]) for a in metrics)
    }
    
    return stats

if __name__ == "__main__":
    # Update scoreboard
    data = update_scoreboard()
    print(f"Scoreboard updated at {data['last_updated']}")
    
    # Print top agents
    print("\nTop Agents:")
    for agent in get_top_agents():
        print(f"{agent['agent_id']}: {agent['metrics']['reputation_score']} points")
    
    # Print stats
    stats = get_agent_stats()
    print("\nSystem Stats:")
    for key, value in stats.items():
        print(f"{key}: {value}") 