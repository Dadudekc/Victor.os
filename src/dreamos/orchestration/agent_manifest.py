import json
import os
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, List, Optional

class AgentManifest:
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.manifest_path = self.workspace_root / "runtime" / "swarm" / "agent_manifest.json"
        self.mailbox_root = self.workspace_root / "runtime" / "agent_comms" / "agent_mailboxes"
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
    def _get_agent_metrics(self, agent_id: str) -> Dict:
        """Gather metrics for a specific agent."""
        agent_dir = self.mailbox_root / agent_id
        inbox_path = agent_dir / "inbox.json"
        devlog_path = agent_dir / "devlog.md"
        state_path = agent_dir / "state.json"
        
        metrics = {
            "agent_id": agent_id,
            "last_updated": datetime.utcnow().isoformat(),
            "inbox_count": 0,
            "devlog_freshness": None,
            "status": "unknown",
            "cycle_count": 0,
            "stopping_conditions": [],
            "last_stop_time": None,
            "recovery_attempts": 0,
            "autonomy_score": 0
        }
        
        # Check inbox
        if inbox_path.exists():
            try:
                with open(inbox_path, "r") as f:
                    inbox = json.load(f)
                    metrics["inbox_count"] = len(inbox)
                    
                    # Check for stopping conditions in messages
                    for msg in inbox:
                        if msg.get("type") in ["error", "stop", "idle"]:
                            metrics["stopping_conditions"].append({
                                "type": msg["type"],
                                "time": msg.get("timestamp"),
                                "content": msg.get("content")
                            })
                            metrics["last_stop_time"] = msg.get("timestamp")
            except Exception as e:
                logging.error(f"Error reading inbox for {agent_id}: {e}")
        
        # Check devlog freshness
        if devlog_path.exists():
            try:
                last_update = datetime.fromtimestamp(devlog_path.stat().st_mtime)
                metrics["devlog_freshness"] = last_update.isoformat()
                
                # Determine activity state
                minutes_diff = (datetime.now() - last_update).total_seconds() / 60
                if minutes_diff < 5:
                    metrics["status"] = "active"
                elif minutes_diff < 15:
                    metrics["status"] = "idle"
                else:
                    metrics["status"] = "stale"
            except Exception as e:
                logging.error(f"Error reading devlog for {agent_id}: {e}")
        else:
            metrics["status"] = "no_activity"
            
        # Check state file for cycle count
        if state_path.exists():
            try:
                with open(state_path, "r") as f:
                    state = json.load(f)
                    metrics["cycle_count"] = state.get("cycle_count", 0)
                    metrics["recovery_attempts"] = state.get("recovery_attempts", 0)
                    
                    # Calculate autonomy score (0-100)
                    # Based on cycle count, stopping conditions, and recovery success
                    cycle_score = min(metrics["cycle_count"] * 4, 40)  # Up to 40 points for cycles
                    stop_penalty = len(metrics["stopping_conditions"]) * 10  # -10 points per stop
                    recovery_bonus = min(metrics["recovery_attempts"] * 5, 20)  # Up to 20 points for recovery
                    
                    metrics["autonomy_score"] = max(0, min(100, cycle_score - stop_penalty + recovery_bonus))
            except Exception as e:
                logging.error(f"Error reading state for {agent_id}: {e}")
            
        return metrics
    
    def update_manifest(self) -> None:
        """Update the agent manifest with current metrics."""
        manifest = {
            "last_updated": datetime.utcnow().isoformat(),
            "agents": []
        }
        
        # Get all agent directories
        agent_dirs = [d for d in self.mailbox_root.glob("Agent-*") if d.is_dir()]
        
        for agent_dir in agent_dirs:
            agent_id = agent_dir.name
            metrics = self._get_agent_metrics(agent_id)
            manifest["agents"].append(metrics)
        
        # Write manifest
        try:
            with open(self.manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
            logging.info(f"Updated agent manifest at {self.manifest_path}")
        except Exception as e:
            logging.error(f"Error writing agent manifest: {e}")
    
    def get_manifest(self) -> Dict:
        """Read the current agent manifest."""
        if not self.manifest_path.exists():
            return {"last_updated": None, "agents": []}
        
        try:
            with open(self.manifest_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error reading agent manifest: {e}")
            return {"last_updated": None, "agents": []}
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict]:
        """Get status for a specific agent."""
        manifest = self.get_manifest()
        for agent in manifest["agents"]:
            if agent["agent_id"] == agent_id:
                return agent
        return None
        
    def update_agent_state(self, agent_id: str, state_updates: Dict) -> bool:
        """Update an agent's state file with new metrics."""
        state_path = self.mailbox_root / agent_id / "state.json"
        
        try:
            # Read existing state
            current_state = {}
            if state_path.exists():
                with open(state_path, "r") as f:
                    current_state = json.load(f)
            
            # Update state
            current_state.update(state_updates)
            current_state["last_updated"] = datetime.utcnow().isoformat()
            
            # Write back
            with open(state_path, "w") as f:
                json.dump(current_state, f, indent=2)
            
            # Update manifest
            self.update_manifest()
            return True
        except Exception as e:
            logging.error(f"Error updating state for {agent_id}: {e}")
            return False 