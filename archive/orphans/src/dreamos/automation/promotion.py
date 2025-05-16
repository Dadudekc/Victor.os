"""
DreamOS Promotion System
Manages agent ranks, points, and achievements.
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional


class PromotionSystem:
    def __init__(self, state_dir: str = "runtime/state"):
        self.state_dir = state_dir
        self.scores_file = os.path.join(state_dir, "agent_scores.json")
        self._load_state()

    def _load_state(self) -> None:
        """Load the current promotion state."""
        if os.path.exists(self.scores_file):
            with open(self.scores_file, "r") as f:
                self.state = json.load(f)
        else:
            self.state = self._initialize_state()
            self._save_state()

    def _save_state(self) -> None:
        """Save the current promotion state."""
        os.makedirs(os.path.dirname(self.scores_file), exist_ok=True)
        with open(self.scores_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def _initialize_state(self) -> Dict:
        """Initialize a new promotion state."""
        return {
            "episode": 5,
            "last_updated": datetime.utcnow().isoformat(),
            "agents": {
                "JARVIS": self._create_agent_state("Primary Assistant"),
                "ORCHESTRATOR": self._create_agent_state("Task Manager"),
                "VALIDATOR": self._create_agent_state("Quality Assurance"),
            },
            "point_rules": {
                "drift_free_streak": {
                    "points_per_hour": 10,
                    "bonus_at_24h": 50,
                    "bonus_at_7d": 200,
                },
                "task_completion": {
                    "base_points": 50,
                    "bonus_for_quality": 25,
                    "bonus_for_speed": 15,
                },
                "reflection_quality": {
                    "thea_approved": 30,
                    "insightful": 20,
                    "standard": 10,
                },
                "compliance_bonus": {
                    "perfect_loop": 15,
                    "no_drift": 10,
                    "pattern_improvement": 20,
                },
            },
            "promotion_thresholds": {
                "captain": 1000,
                "commander": 2500,
                "general": 5000,
            },
            "system_metrics": {
                "total_points_awarded": 0,
                "promotions_granted": 0,
                "highest_rank_achieved": "Primary Assistant",
            },
        }

    def _create_agent_state(self, initial_rank: str) -> Dict:
        """Create initial state for an agent."""
        return {
            "current_rank": initial_rank,
            "points": {
                "total": 0,
                "drift_free_streak": 0,
                "task_completion": 0,
                "reflection_quality": 0,
                "compliance_bonus": 0,
            },
            "promotion_metrics": {
                "eligible_for_promotion": False,
                "promotion_threshold": 1000,
                "current_streak": 0,
                "highest_streak": 0,
            },
            "achievements": {
                "drift_free_days": 0,
                "perfect_loops": 0,
                "thea_commendations": 0,
                "milestone_contributions": 0,
            },
            "history": [],
        }

    def award_points(self, agent: str, category: str, points: int, reason: str) -> bool:
        """Award points to an agent."""
        if agent not in self.state["agents"]:
            return False

        agent_state = self.state["agents"][agent]
        agent_state["points"][category] += points
        agent_state["points"]["total"] += points

        # Record in history
        agent_state["history"].append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "category": category,
                "points": points,
                "reason": reason,
            }
        )

        # Check for promotion eligibility
        self._check_promotion_eligibility(agent)

        self._save_state()
        return True

    def _check_promotion_eligibility(self, agent: str) -> None:
        """Check if an agent is eligible for promotion."""
        agent_state = self.state["agents"][agent]
        total_points = agent_state["points"]["total"]

        # Check against promotion thresholds
        for rank, threshold in self.state["promotion_thresholds"].items():
            if total_points >= threshold and rank != agent_state["current_rank"]:
                agent_state["promotion_metrics"]["eligible_for_promotion"] = True
                return

        agent_state["promotion_metrics"]["eligible_for_promotion"] = False

    def get_agent_status(self, agent: str) -> Optional[Dict]:
        """Get the current status of an agent."""
        if agent not in self.state["agents"]:
            return None
        return self.state["agents"][agent]

    def get_system_metrics(self) -> Dict:
        """Get the current system metrics."""
        return self.state["system_metrics"]

    def update_streak(self, agent: str, hours: int) -> None:
        """Update an agent's streak."""
        if agent not in self.state["agents"]:
            return

        agent_state = self.state["agents"][agent]
        agent_state["promotion_metrics"]["current_streak"] = hours

        if hours > agent_state["promotion_metrics"]["highest_streak"]:
            agent_state["promotion_metrics"]["highest_streak"] = hours

        self._save_state()
