"""
DreamOS Reflection Engine
Manages milestone reflections, agent promotions, and system insights.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class ReflectionEngine:
    def __init__(self, state_dir: str = "runtime/state", docs_dir: str = "docs"):
        self.state_dir = state_dir
        self.docs_dir = docs_dir
        self.config_file = os.path.join(state_dir, "thea_reflection_config.json")
        self._load_config()

    def _load_config(self) -> None:
        """Load the reflection engine configuration."""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = self._initialize_config()
            self._save_config()

    def _save_config(self) -> None:
        """Save the reflection engine configuration."""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _initialize_config(self) -> Dict:
        """Initialize a new reflection engine configuration."""
        return {
            "episode": 5,
            "last_updated": datetime.utcnow().isoformat(),
            "reflection_triggers": {
                "milestone_completion": {
                    "enabled": True,
                    "output_path": "docs/episodes/episode-05/milestone_{number}_reflection.md",
                    "include_metrics": True,
                    "include_narrative": True
                },
                "agent_promotion": {
                    "enabled": True,
                    "output_path": "docs/episodes/episode-05/promotions/{agent}_{rank}_reflection.md",
                    "include_metrics": True,
                    "include_narrative": True
                },
                "violation_recovery": {
                    "enabled": True,
                    "output_path": "docs/episodes/episode-05/recovery/{timestamp}_reflection.md",
                    "include_metrics": True,
                    "include_narrative": True
                }
            },
            "reflection_components": {
                "agent_performance": {
                    "enabled": True,
                    "metrics": [
                        "loop_health",
                        "task_progress",
                        "compliance_score",
                        "promotion_status",
                        "key_contributions"
                    ]
                },
                "system_metrics": {
                    "enabled": True,
                    "metrics": [
                        "performance_indicators",
                        "loop_analytics",
                        "promotion_system"
                    ]
                },
                "narrative_arc": {
                    "enabled": True,
                    "components": [
                        "current_chapter",
                        "key_themes",
                        "notable_patterns",
                        "thea_insights"
                    ]
                },
                "progress_tracking": {
                    "enabled": True,
                    "metrics": [
                        "task_completion",
                        "agent_engagement",
                        "milestone_objectives",
                        "success_criteria"
                    ]
                }
            },
            "narrative_settings": {
                "tone": "professional_insightful",
                "style": "technical_narrative",
                "themes": [
                    "emergence_of_intelligence",
                    "collaborative_evolution",
                    "guardian_principles"
                ],
                "auto_update": True,
                "update_interval": 300
            },
            "output_format": {
                "markdown": True,
                "include_emoji": True,
                "include_timestamps": True,
                "include_metrics": True,
                "include_narrative": True
            },
            "system_metrics": {
                "total_reflections": 0,
                "last_reflection": datetime.utcnow().isoformat(),
                "reflection_types": {
                    "milestone": 0,
                    "promotion": 0,
                    "recovery": 0
                }
            }
        }

    def generate_milestone_reflection(self, milestone_number: int, data: Dict) -> str:
        """Generate a reflection for a milestone completion."""
        if not self.config["reflection_triggers"]["milestone_completion"]["enabled"]:
            return ""

        output_path = self.config["reflection_triggers"]["milestone_completion"]["output_path"].format(
            number=milestone_number
        )
        full_path = os.path.join(self.docs_dir, output_path)

        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Generate reflection content
        content = self._generate_reflection_content("milestone", data)
        
        # Write to file
        with open(full_path, 'w') as f:
            f.write(content)

        # Update metrics
        self.config["system_metrics"]["total_reflections"] += 1
        self.config["system_metrics"]["reflection_types"]["milestone"] += 1
        self.config["system_metrics"]["last_reflection"] = datetime.utcnow().isoformat()
        self._save_config()

        return full_path

    def _generate_reflection_content(self, reflection_type: str, data: Dict) -> str:
        """Generate the content for a reflection."""
        # This would be expanded to use templates and proper formatting
        # For now, return a basic structure
        return f"""# {reflection_type.title()} Reflection
*Generated by THEA on {datetime.utcnow().isoformat()}*

## Overview
{data.get('overview', 'No overview available')}

## Metrics
{self._format_metrics(data.get('metrics', {}))}

## Narrative
{data.get('narrative', 'No narrative available')}
"""

    def _format_metrics(self, metrics: Dict) -> str:
        """Format metrics for the reflection."""
        return "\n".join(f"- {k}: {v}" for k, v in metrics.items())

    def get_config(self) -> Dict:
        """Get the current configuration."""
        return self.config

    def update_config(self, updates: Dict) -> None:
        """Update the configuration."""
        self.config.update(updates)
        self._save_config() 