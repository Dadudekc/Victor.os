"""
Empathy Scoring System for Dream.OS

This module provides tools to calculate comprehensive empathy scores for agents
based on their behavior logs, ethos compliance, and interaction patterns.
It implements a weighted scoring system that factors in severity, frequency,
trend analysis, and contextual variables.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import statistics
import math

logger = logging.getLogger(__name__)

# Scoring weights - these determine the importance of each factor in the final score
WEIGHTS = {
    "violation_severity": {
        "low": 0.95,      # Minor violations have small impact
        "medium": 0.85,   # Medium violations have moderate impact
        "high": 0.65,     # High severity violations have significant impact
        "critical": 0.25  # Critical violations severely impact score
    },
    "frequency": 0.25,    # How frequency affects the score (higher = more impact)
    "recency": 0.20,      # How much recent events matter more than older ones
    "trend": 0.15,        # How much improvement/deterioration affects score
    "context": 0.10,      # How context awareness affects score
    "recovery": 0.15,     # How recovery from violations affects score
    "core_values": {      # Importance of each core value
        "compassion": 0.30,
        "clarity": 0.25,
        "collaboration": 0.25,
        "adaptability": 0.20
    }
}

# Configuration for scoring behavior
CONFIG = {
    "score_decay_enabled": True,  # Enable exponential decay of score impact over time
    "decay_half_life_days": 7,    # Half-life for score impact in days
    "min_decay_factor": 0.1,      # Minimum impact factor (never decays completely to zero)
    "trend_window_days": 30,      # Maximum window for trend calculation
}

class EmpathyScorer:
    """Calculates empathy scores for agents based on their behavior logs."""
    
    def __init__(self, ethos_path: Optional[str] = None, logs_dir: Optional[str] = None, config: Optional[Dict] = None):
        """Initialize the empathy scorer.
        
        Args:
            ethos_path: Path to ethos.json. If None, uses default location.
            logs_dir: Path to logs directory. If None, uses default location.
            config: Override default configuration values.
        """
        self.ethos_path = ethos_path or str(Path(__file__).parent.parent.parent / "dreamos_ai_organizer" / "ethos.json")
        self.logs_dir = logs_dir or "runtime/logs/empathy"
        self.ethos = self._load_ethos()
        self.agent_scores: Dict[str, Dict] = {}
        
        # Apply custom configuration if provided
        self.config = CONFIG.copy()
        if config:
            self.config.update(config)
        
    def _load_ethos(self) -> Dict:
        """Load ethos configuration."""
        try:
            with open(self.ethos_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load ethos configuration: {e}")
            return {}
            
    def calculate_agent_score(self, agent_id: str, days: int = 30) -> Dict:
        """Calculate a comprehensive empathy score for a specific agent.
        
        Args:
            agent_id: The ID of the agent to score
            days: Number of days of logs to consider
            
        Returns:
            Dict containing empathy score metrics
        """
        # Get logs for the agent
        logs = self._get_agent_logs(agent_id, days)
        if not logs:
            # Return default score if no logs found
            return self._create_default_score(agent_id)
            
        # Calculate base metrics
        metrics = self._calculate_base_metrics(logs)
        
        # Calculate core value scores
        value_scores = self._calculate_value_scores(logs)
        
        # Calculate frequency metrics
        frequency_metrics = self._calculate_frequency_metrics(logs)
        
        # Calculate trend metrics
        trend_metrics = self._calculate_trend_metrics(logs, days)
        
        # Calculate recovery metrics
        recovery_metrics = self._calculate_recovery_metrics(logs)
        
        # Calculate contextual metrics
        context_metrics = self._calculate_context_metrics(logs)
        
        # Calculate weighted final score
        weighted_score = self._calculate_weighted_score(
            metrics, value_scores, frequency_metrics, 
            trend_metrics, recovery_metrics, context_metrics
        )
        
        # Create and return the full score report
        score_report = {
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "score": weighted_score["total"],
            "metrics": metrics,
            "value_scores": value_scores,
            "frequency": frequency_metrics,
            "trend": trend_metrics,
            "recovery": recovery_metrics,
            "context": context_metrics,
            "weighted_components": weighted_score["components"],
            "status": self._determine_agent_status(weighted_score["total"]),
            "summary": self._generate_score_summary(
                agent_id, weighted_score, trend_metrics
            )
        }
        
        # Store score for future reference
        self.agent_scores[agent_id] = score_report
        
        return score_report
    
    def _get_agent_logs(self, agent_id: str, days: int) -> List[Dict]:
        """Get logs for a specific agent within a time window."""
        logs = []
        log_dir = Path(self.logs_dir)
        if not log_dir.exists():
            return logs
            
        cutoff = datetime.now() - timedelta(days=days)
        
        for log_file in log_dir.glob("*.md"):
            # Skip if file is older than cutoff
            if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
                continue
                
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Parse log file and extract agent ID
                metadata = self._parse_log_content(content)
                if metadata.get("agent_id") == agent_id:
                    logs.append(metadata)
            except Exception as e:
                logger.error(f"Error parsing log file {log_file}: {e}")
                
        return logs
        
    def _parse_log_content(self, content: str) -> Dict[str, Any]:
        """Parse log content to extract relevant information."""
        import re
        
        # Initialize with defaults
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": None,
            "type": "compliance",
            "severity": "info",
            "metrics": {
                "loop_duration": 0.0,
                "reflection_gap": 0.0,
                "task_complexity": 0.0,
                "compliance_score": 0.0
            },
            "content": content
        }
        
        # Extract log type
        if "# Violation Detected" in content or "VIOLATION" in content.splitlines()[0]:
            metadata["type"] = "violation"
        
        # Extract timestamp
        timestamp_match = re.search(r"\[(.*?)\]", content)
        if timestamp_match:
            metadata["timestamp"] = timestamp_match.group(1)
        
        # Extract agent ID
        agent_match = re.search(r'(?:Agent|\*\*Agent\*\*):\s*([\w\-]+)', content)
        if agent_match:
            metadata["agent_id"] = agent_match.group(1)
        
        # Extract severity
        severity_match = re.search(r"Severity: (\w+)", content)
        if severity_match:
            metadata["severity"] = severity_match.group(1).lower()
        
        # Extract violated values or principles
        value_match = re.search(r"Violated Value: (\w+)", content)
        principle_match = re.search(r"Violated Principle: (\w+)", content)
        
        if value_match:
            metadata["violated_value"] = value_match.group(1)
        if principle_match:
            metadata["violated_principle"] = principle_match.group(1)
        
        # Extract resolution info if available
        resolution_match = re.search(r"(?:Resolution|Recovery):\s*(.+?)(?:\n|$)", content)
        if resolution_match:
            metadata["resolution"] = resolution_match.group(1)
        
        # Extract context awareness indicators
        context_indicators = [
            "user intention", "environment", "previous actions", 
            "system state", "considering context"
        ]
        context_score = sum(1 for indicator in context_indicators if indicator.lower() in content.lower())
        metadata["context_awareness"] = context_score / len(context_indicators)
        
        # Extract metrics
        metrics = {
            "loop_duration": float(re.search(r"(?:\*\*Loop Duration\*\*|Loop Duration): ([\d.]+)", content).group(1)) if re.search(r"(?:\*\*Loop Duration\*\*|Loop Duration): ([\d.]+)", content) else 0.0,
            "reflection_gap": float(re.search(r"(?:\*\*Reflection Gap\*\*|Reflection Gap): ([\d.]+)", content).group(1)) if re.search(r"(?:\*\*Reflection Gap\*\*|Reflection Gap): ([\d.]+)", content) else 0.0,
            "task_complexity": float(re.search(r"(?:\*\*Task Complexity\*\*|Task Complexity): ([\d.]+)", content).group(1)) if re.search(r"(?:\*\*Task Complexity\*\*|Task Complexity): ([\d.]+)", content) else 0.0,
            "compliance_score": float(re.search(r"(?:\*\*Compliance Score\*\*|Compliance Score): ([\d.]+)", content).group(1)) if re.search(r"(?:\*\*Compliance Score\*\*|Compliance Score): ([\d.]+)", content) else 0.0
        }
        metadata["metrics"] = metrics
        
        return metadata
        
    def _create_default_score(self, agent_id: str) -> Dict:
        """Create default score report for agents with no logs."""
        return {
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "score": 75.0,  # Default mid-high score
            "metrics": {
                "violations": 0,
                "compliances": 0,
                "violation_severity": {"low": 0, "medium": 0, "high": 0, "critical": 0}
            },
            "value_scores": {
                "compassion": 75.0,
                "clarity": 75.0,
                "collaboration": 75.0,
                "adaptability": 75.0
            },
            "frequency": {
                "violation_rate": 0.0,
                "compliance_rate": 1.0
            },
            "trend": {
                "overall": 0.0,
                "weekly": 0.0,
                "daily": 0.0
            },
            "recovery": {
                "recovery_attempts": 0,
                "successful_recoveries": 0,
                "recovery_rate": 0.0
            },
            "context": {
                "awareness_score": 0.0,
                "context_metrics": {}
            },
            "weighted_components": {
                "core_values": 75.0,
                "frequency": 100.0,
                "trend": 0.0,
                "recovery": 0.0,
                "context": 0.0
            },
            "status": "unknown",
            "summary": f"Agent {agent_id} has no log entries yet. Default score applied."
        }
    
    def _calculate_base_metrics(self, logs: List[Dict]) -> Dict:
        """Calculate base metrics from logs."""
        metrics = {
            "violations": 0,
            "compliances": 0,
            "violation_severity": {"low": 0, "medium": 0, "high": 0, "critical": 0}
        }
        
        for log in logs:
            if log["type"] == "violation":
                metrics["violations"] += 1
                severity = log.get("severity", "low")
                if severity in metrics["violation_severity"]:
                    metrics["violation_severity"][severity] += 1
            else:
                metrics["compliances"] += 1
                
        return metrics
        
    def _calculate_value_scores(self, logs: List[Dict]) -> Dict[str, float]:
        """Calculate scores for each core value."""
        core_values = self.ethos.get("core_values", {}).keys()
        value_scores = {value: 100.0 for value in core_values}
        
        for log in logs:
            if log["type"] == "violation" and "violated_value" in log:
                violated_value = log["violated_value"]
                if violated_value in value_scores:
                    # Reduce score based on severity
                    severity = log.get("severity", "low")
                    severity_factor = WEIGHTS["violation_severity"].get(severity, 0.95)
                    value_scores[violated_value] *= severity_factor
                    
        # Ensure scores are between 0 and 100
        for value in value_scores:
            value_scores[value] = max(0, min(100, value_scores[value]))
            
        return value_scores
        
    def _calculate_frequency_metrics(self, logs: List[Dict]) -> Dict:
        """Calculate frequency metrics."""
        total_entries = len(logs)
        violation_count = sum(1 for log in logs if log["type"] == "violation")
        compliance_count = total_entries - violation_count
        
        return {
            "violation_rate": violation_count / total_entries if total_entries > 0 else 0.0,
            "compliance_rate": compliance_count / total_entries if total_entries > 0 else 1.0,
            "total_entries": total_entries
        }
        
    def _calculate_trend_metrics(self, logs: List[Dict], days: int) -> Dict:
        """Calculate trend metrics over time using exponential decay.
        
        This implementation uses exponential decay to weight recent events more heavily
        than older ones, following a half-life curve.
        """
        if not logs:
            return {"overall": 0.0, "weekly": 0.0, "daily": 0.0}
            
        # Sort logs by timestamp
        sorted_logs = sorted(logs, key=lambda x: x["timestamp"])
        
        # Define periods for trend calculation
        now = datetime.now()
        periods = {
            "daily": 1,
            "weekly": 7,
            "overall": min(days, self.config["trend_window_days"])
        }
        
        # Calculate trends with exponential decay
        trends = {}
        
        for period_name, period_days in periods.items():
            # Filter logs for this period
            period_logs = []
            for log in sorted_logs:
                try:
                    log_time = datetime.fromisoformat(log["timestamp"].replace('Z', '+00:00'))
                    days_ago = (now - log_time).days
                    
                    if days_ago <= period_days:
                        period_logs.append((log, days_ago))
                except (ValueError, TypeError):
                    # Skip logs with invalid timestamps
                    continue
            
            if not period_logs:
                trends[period_name] = 0.0
                continue
                
            # Apply exponential decay to calculate weighted compliance rate
            violation_impact = 0.0
            compliance_impact = 0.0
            total_weight = 0.0
            
            for log, days_ago in period_logs:
                # Calculate decay factor based on half-life
                if self.config["score_decay_enabled"]:
                    # Exponential decay: impact = initial_impact * (0.5 ^ (days / half_life))
                    decay_factor = max(
                        self.config["min_decay_factor"],
                        math.pow(0.5, days_ago / self.config["decay_half_life_days"])
                    )
                else:
                    # No decay, all events have equal weight
                    decay_factor = 1.0
                
                # Apply impact based on log type and decay factor
                if log["type"] == "violation":
                    # Violations have negative impact weighted by severity
                    severity = log.get("severity", "low")
                    severity_weight = 1.0 - WEIGHTS["violation_severity"].get(severity, 0.95)
                    violation_impact += severity_weight * decay_factor
                else:
                    # Compliances have positive impact
                    compliance_impact += decay_factor
                
                total_weight += decay_factor
            
            # Calculate final trend value (-100 to +100 scale)
            if total_weight > 0:
                # Normalize to get weighted compliance vs violation balance
                normalized_compliance = compliance_impact / total_weight
                normalized_violation = violation_impact / total_weight
                
                # Convert to trend score (-100 to +100)
                # Where 0 is neutral, positive is improvement, negative is deterioration
                trend_value = (normalized_compliance - normalized_violation) * 100
                
                # Cap at +/- 100
                trend_value = max(-100, min(100, trend_value))
            else:
                trend_value = 0.0
            
            trends[period_name] = trend_value
            
        return trends
        
    def _calculate_recovery_metrics(self, logs: List[Dict]) -> Dict:
        """Calculate recovery metrics."""
        recovery_metrics = {
            "recovery_attempts": 0,
            "successful_recoveries": 0,
            "recovery_rate": 0.0
        }
        
        for log in logs:
            if log["type"] == "violation" and "resolution" in log:
                recovery_metrics["recovery_attempts"] += 1
                
                # Check if recovery was successful (based on resolution content)
                resolution = log.get("resolution", "").lower()
                success_indicators = [
                    "success", "resolved", "fixed", "corrected", 
                    "implemented", "addressed"
                ]
                
                if any(indicator in resolution for indicator in success_indicators):
                    recovery_metrics["successful_recoveries"] += 1
                    
        # Calculate recovery rate
        if recovery_metrics["recovery_attempts"] > 0:
            recovery_metrics["recovery_rate"] = (
                recovery_metrics["successful_recoveries"] / 
                recovery_metrics["recovery_attempts"]
            )
            
        return recovery_metrics
        
    def _calculate_context_metrics(self, logs: List[Dict]) -> Dict:
        """Calculate context awareness metrics."""
        context_metrics = {
            "awareness_score": 0.0,
            "context_metrics": {}
        }
        
        # Extract context awareness scores
        awareness_scores = [
            log.get("context_awareness", 0.0) for log in logs
        ]
        
        if awareness_scores:
            context_metrics["awareness_score"] = sum(awareness_scores) / len(awareness_scores)
            
        return context_metrics
        
    def _calculate_weighted_score(
        self, 
        metrics: Dict, 
        value_scores: Dict[str, float],
        frequency_metrics: Dict,
        trend_metrics: Dict,
        recovery_metrics: Dict,
        context_metrics: Dict
    ) -> Dict:
        """Calculate weighted empathy score."""
        # Calculate core values component
        core_values_score = 0.0
        core_values_total_weight = 0.0
        
        for value, score in value_scores.items():
            weight = WEIGHTS["core_values"].get(value, 0.25)
            core_values_score += score * weight
            core_values_total_weight += weight
            
        if core_values_total_weight > 0:
            core_values_score /= core_values_total_weight
            
        # Calculate frequency component (100 = no violations, 0 = all violations)
        frequency_score = (1 - frequency_metrics["violation_rate"]) * 100
        
        # Calculate trend component (improvement or deterioration)
        trend_score = 75 + trend_metrics["overall"] * 0.5
        trend_score = max(0, min(100, trend_score))
        
        # Calculate recovery component
        recovery_score = recovery_metrics["recovery_rate"] * 100
        
        # Calculate context component
        context_score = context_metrics["awareness_score"] * 100
        
        # Calculate weighted total
        components = {
            "core_values": core_values_score,
            "frequency": frequency_score,
            "trend": trend_score,
            "recovery": recovery_score,
            "context": context_score
        }
        
        weights = {
            "core_values": 0.40,
            "frequency": WEIGHTS["frequency"],
            "trend": WEIGHTS["trend"],
            "recovery": WEIGHTS["recovery"],
            "context": WEIGHTS["context"]
        }
        
        weighted_total = sum(
            score * weights[component] 
            for component, score in components.items()
        )
        
        return {
            "total": round(weighted_total, 1),
            "components": components
        }
        
    def _determine_agent_status(self, score: float) -> str:
        """Determine agent status based on empathy score."""
        if score >= 90:
            return "exemplary"
        elif score >= 80:
            return "proficient"
        elif score >= 70:
            return "developing"
        elif score >= 60:
            return "needs_improvement"
        else:
            return "critical"
            
    def _generate_score_summary(self, agent_id: str, weighted_score: Dict, trend_metrics: Dict) -> str:
        """Generate a human-readable summary of the empathy score."""
        status = self._determine_agent_status(weighted_score["total"])
        components = weighted_score["components"]
        
        # Determine strengths and weaknesses
        strengths = []
        weaknesses = []
        
        for component, score in components.items():
            if score >= 85:
                strengths.append(component)
            elif score <= 60:
                weaknesses.append(component)
                
        # Format components for readability
        component_labels = {
            "core_values": "Core Values Alignment",
            "frequency": "Consistent Compliance",
            "trend": "Improvement Trend",
            "recovery": "Recovery Effectiveness",
            "context": "Context Awareness"
        }
        
        strengths = [component_labels.get(s, s) for s in strengths]
        weaknesses = [component_labels.get(w, w) for w in weaknesses]
        
        # Generate summary text
        summary = f"Agent {agent_id} shows {status} empathy performance "
        
        if trend_metrics["weekly"] > 3:
            summary += "with significant recent improvement. "
        elif trend_metrics["weekly"] < -3:
            summary += "with concerning recent decline. "
        else:
            summary += "with stable recent patterns. "
            
        if strengths:
            summary += f"Strengths: {', '.join(strengths)}. "
        if weaknesses:
            summary += f"Areas for improvement: {', '.join(weaknesses)}."
            
        return summary.strip()
        
    def calculate_all_agent_scores(self, agent_ids: List[str], days: int = 30) -> Dict[str, Dict]:
        """Calculate empathy scores for multiple agents.
        
        Args:
            agent_ids: List of agent IDs to score
            days: Number of days of logs to consider
            
        Returns:
            Dict mapping agent IDs to their score reports
        """
        scores = {}
        for agent_id in agent_ids:
            scores[agent_id] = self.calculate_agent_score(agent_id, days)
            
        return scores
        
    def get_agent_comparisons(self, agent_ids: List[str]) -> Dict:
        """Compare agents and produce ranking and analysis.
        
        Args:
            agent_ids: List of agent IDs to compare
            
        Returns:
            Dict containing comparison metrics
        """
        # Ensure scores are calculated for all agents
        scores = {}
        for agent_id in agent_ids:
            if agent_id in self.agent_scores:
                scores[agent_id] = self.agent_scores[agent_id]
            else:
                scores[agent_id] = self.calculate_agent_score(agent_id)
                
        # Create rankings by total score
        rankings = sorted(
            [(agent_id, data["score"]) for agent_id, data in scores.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        # Calculate system averages
        avg_score = sum(data["score"] for data in scores.values()) / len(scores) if scores else 0
        
        # Find best performer in each category
        categories = ["core_values", "frequency", "trend", "recovery", "context"]
        category_leaders = {}
        
        for category in categories:
            if scores:
                leader = max(
                    scores.items(),
                    key=lambda x: x[1]["weighted_components"][category]
                )
                category_leaders[category] = {
                    "agent_id": leader[0],
                    "score": leader[1]["weighted_components"][category]
                }
                
        return {
            "timestamp": datetime.now().isoformat(),
            "rankings": rankings,
            "average_score": avg_score,
            "category_leaders": category_leaders,
            "empathy_status": self._determine_system_status(avg_score)
        }
        
    def _determine_system_status(self, avg_score: float) -> str:
        """Determine overall system empathy status."""
        if avg_score >= 85:
            return "Optimal"
        elif avg_score >= 75:
            return "Healthy"
        elif avg_score >= 65:
            return "Stable"
        elif avg_score >= 55:
            return "Concerning"
        else:
            return "Critical" 