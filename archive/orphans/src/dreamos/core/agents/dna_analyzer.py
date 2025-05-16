from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
from textblob import TextBlob

from ..memory import AgentMemory
from ..utils.logging import get_logger

logger = get_logger(__name__)


class DNAAnalyzer:
    """Analyzes agent behavior patterns and personality traits from logs."""

    def __init__(self, memory: AgentMemory):
        self.memory = memory
        self.trait_definitions = {
            "empathy": {
                "description": "Ability to understand and respond to emotional cues",
                "indicators": [
                    "emotional_understanding",
                    "compassion",
                    "perspective_taking",
                ],
            },
            "adaptability": {
                "description": "Flexibility in handling new situations and changes",
                "indicators": ["task_switching", "novelty_handling", "recovery_speed"],
            },
            "consistency": {
                "description": "Reliability and stability in behavior patterns",
                "indicators": ["pattern_stability", "commitment", "follow_through"],
            },
            "creativity": {
                "description": "Novel problem-solving and innovative thinking",
                "indicators": [
                    "solution_novelty",
                    "lateral_thinking",
                    "experimentation",
                ],
            },
            "resilience": {
                "description": "Ability to recover from setbacks and maintain performance",
                "indicators": ["error_recovery", "stress_handling", "persistence"],
            },
            "collaboration": {
                "description": "Effectiveness in working with other agents",
                "indicators": [
                    "team_coordination",
                    "knowledge_sharing",
                    "conflict_resolution",
                ],
            },
            "efficiency": {
                "description": "Resource optimization and task completion speed",
                "indicators": ["resource_usage", "completion_speed", "optimization"],
            },
            "learning": {
                "description": "Ability to improve from experience and feedback",
                "indicators": [
                    "skill_improvement",
                    "feedback_integration",
                    "knowledge_acquisition",
                ],
            },
        }

        self.pattern_categories = {
            "task_management": ["task_abandonment", "task_completion", "task_restart"],
            "interaction": ["help_seeking", "knowledge_sharing", "conflict_handling"],
            "problem_solving": [
                "solution_exploration",
                "error_handling",
                "optimization_attempts",
            ],
            "adaptation": ["strategy_change", "tool_usage", "approach_modification"],
        }

    async def analyze_agent_dna(self, agent_id: str) -> Dict:
        """Analyzes an agent's DNA profile from their logs and behavior patterns."""
        try:
            # Fetch recent logs
            logs = await self.memory.get_agent_logs(agent_id, limit=1000)

            # Calculate trait scores
            trait_scores = await self._calculate_trait_scores(logs)

            # Detect behavioral patterns
            patterns = await self._detect_behavioral_patterns(logs)

            # Calculate drift score
            drift_score = await self._calculate_drift_score(logs, trait_scores)

            # Generate DNA profile
            dna_profile = {
                "agentId": agent_id,
                "traits": [
                    {
                        "name": trait,
                        "value": score,
                        "trend": await self._calculate_trait_trend(
                            agent_id, trait, score
                        ),
                        "description": self.trait_definitions[trait]["description"],
                    }
                    for trait, score in trait_scores.items()
                ],
                "driftScore": drift_score,
                "lastUpdated": datetime.utcnow().isoformat(),
                "confidence": await self._calculate_confidence(logs),
                "behavioralPatterns": patterns,
            }

            # Store DNA profile
            await self.memory.store_agent_dna(agent_id, dna_profile)

            return dna_profile

        except Exception as e:
            logger.error(f"Error analyzing agent DNA: {str(e)}")
            raise

    async def _calculate_trait_scores(self, logs: List[Dict]) -> Dict[str, float]:
        """Calculates trait scores from agent logs."""
        trait_scores = {trait: 0.0 for trait in self.trait_definitions}

        for log in logs:
            # Analyze log content using NLP
            content = log.get("content", "")
            sentiment = TextBlob(content).sentiment

            # Update trait scores based on log content and metrics
            for trait, definition in self.trait_definitions.items():
                indicators = definition["indicators"]
                for indicator in indicators:
                    # Calculate indicator score based on log content and metrics
                    indicator_score = await self._calculate_indicator_score(
                        indicator, log, sentiment
                    )
                    trait_scores[trait] += indicator_score

        # Normalize scores to 0-1 range
        for trait in trait_scores:
            trait_scores[trait] = min(1.0, max(0.0, trait_scores[trait] / len(logs)))

        return trait_scores

    async def _detect_behavioral_patterns(
        self, logs: List[Dict]
    ) -> List[Dict[str, any]]:
        """Detects behavioral patterns from agent logs."""
        patterns = []

        # Group logs by category
        categorized_logs = {category: [] for category in self.pattern_categories}
        for log in logs:
            for category, pattern_types in self.pattern_categories.items():
                if any(pt in log.get("content", "").lower() for pt in pattern_types):
                    categorized_logs[category].append(log)

        # Analyze patterns in each category
        for category, category_logs in categorized_logs.items():
            if not category_logs:
                continue

            # Calculate pattern frequency
            frequency = len(category_logs) / len(logs)

            # Determine pattern impact
            impact = await self._determine_pattern_impact(category_logs)

            patterns.append(
                {"pattern": category, "frequency": frequency, "impact": impact}
            )

        return patterns

    async def _calculate_drift_score(
        self, logs: List[Dict], trait_scores: Dict[str, float]
    ) -> float:
        """Calculates the agent's drift score based on trait stability."""
        try:
            # Get historical trait scores
            historical_scores = await self.memory.get_agent_trait_history(
                logs[0]["agent_id"], limit=10
            )

            if not historical_scores:
                return 0.0

            # Calculate drift for each trait
            trait_drifts = []
            for trait, current_score in trait_scores.items():
                historical = [score[trait] for score in historical_scores]
                if historical:
                    drift = abs(current_score - np.mean(historical))
                    trait_drifts.append(drift)

            # Overall drift score is the average of trait drifts
            return np.mean(trait_drifts) if trait_drifts else 0.0

        except Exception as e:
            logger.error(f"Error calculating drift score: {str(e)}")
            return 0.0

    async def _calculate_trait_trend(
        self, agent_id: str, trait: str, current_score: float
    ) -> float:
        """Calculates the trend direction for a trait."""
        try:
            historical_scores = await self.memory.get_agent_trait_history(
                agent_id, limit=5
            )

            if not historical_scores:
                return 0.0

            trait_scores = [score[trait] for score in historical_scores]
            if len(trait_scores) < 2:
                return 0.0

            # Calculate trend using linear regression
            x = np.arange(len(trait_scores))
            slope = np.polyfit(x, trait_scores, 1)[0]

            return slope

        except Exception as e:
            logger.error(f"Error calculating trait trend: {str(e)}")
            return 0.0

    async def _calculate_confidence(self, logs: List[Dict]) -> float:
        """Calculates confidence score for the DNA analysis."""
        try:
            # Factors affecting confidence:
            # 1. Number of logs analyzed
            # 2. Log diversity
            # 3. Time span of logs

            if not logs:
                return 0.0

            # Log count factor
            count_factor = min(1.0, len(logs) / 1000)

            # Log diversity factor
            unique_types = len(set(log.get("type", "") for log in logs))
            diversity_factor = min(1.0, unique_types / 5)

            # Time span factor
            timestamps = [datetime.fromisoformat(log["timestamp"]) for log in logs]
            time_span = (max(timestamps) - min(timestamps)).total_seconds()
            time_factor = min(1.0, time_span / (7 * 24 * 3600))  # 7 days

            # Weighted average of factors
            confidence = 0.4 * count_factor + 0.3 * diversity_factor + 0.3 * time_factor

            return confidence

        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return 0.0

    async def _calculate_indicator_score(
        self, indicator: str, log: Dict, sentiment: Tuple[float, float]
    ) -> float:
        """Calculates score for a specific indicator based on log data."""
        try:
            # Base score from sentiment
            score = (sentiment.polarity + 1) / 2  # Normalize to 0-1

            # Adjust based on log metrics
            metrics = log.get("metrics", {})
            if metrics:
                # Weight different metrics based on indicator type
                if indicator in ["emotional_understanding", "compassion"]:
                    score *= metrics.get("empathy_score", 1.0)
                elif indicator in ["task_switching", "novelty_handling"]:
                    score *= metrics.get("adaptability_score", 1.0)
                elif indicator in ["pattern_stability", "commitment"]:
                    score *= metrics.get("consistency_score", 1.0)

            return score

        except Exception as e:
            logger.error(f"Error calculating indicator score: {str(e)}")
            return 0.0

    async def _determine_pattern_impact(self, logs: List[Dict]) -> str:
        """Determines the impact of a behavioral pattern."""
        try:
            # Analyze pattern impact based on:
            # 1. Success rate of actions
            # 2. Error frequency
            # 3. Resource usage

            success_count = sum(1 for log in logs if log.get("success", False))
            error_count = sum(1 for log in logs if log.get("error", False))
            total_count = len(logs)

            if total_count == 0:
                return "neutral"

            success_rate = success_count / total_count
            error_rate = error_count / total_count

            if success_rate > 0.7 and error_rate < 0.2:
                return "positive"
            elif success_rate < 0.3 or error_rate > 0.5:
                return "negative"
            else:
                return "neutral"

        except Exception as e:
            logger.error(f"Error determining pattern impact: {str(e)}")
            return "neutral"
