# src/dreamos/feedback/FeedbackEngineV2.py

"""
Enhanced Feedback Engine for Dream.OS.

This engine is responsible for:
- Capturing and analyzing product quality metrics
- Processing user feedback
- Generating quality improvement recommendations
- Monitoring performance and reliability
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import jsonschema

from dreamos.utils.resilient_io import read_file, write_file

logger = logging.getLogger(__name__)

class FeedbackEngineV2:
    """Enhanced feedback engine for product quality tracking."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the feedback engine.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.feedback_data = {}  # Store feedback data in memory
        self.quality_metrics = {}  # Store quality metrics
        self.analysis_reports = []  # Store analysis reports
        self.retry_strategies = {}  # Store retry strategies
        
        # Initialize feedback directory
        self.feedback_dir = Path("runtime/feedback")
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing feedback data if available
        self._load_feedback_data()
    
    def _load_feedback_data(self) -> None:
        """Load existing feedback data from disk."""
        try:
            feedback_file = self.feedback_dir / "feedback_data.json"
            if feedback_file.exists():
                data = json.loads(read_file(feedback_file))
                self.feedback_data = data.get("feedback_data", {})
                self.quality_metrics = data.get("quality_metrics", {})
                self.analysis_reports = data.get("analysis_reports", [])
                self.retry_strategies = data.get("retry_strategies", {})
                logger.info("Loaded existing feedback data")
        except Exception as e:
            logger.error(f"Failed to load feedback data: {str(e)}")
    
    def _save_feedback_data(self) -> None:
        """Save feedback data to disk."""
        try:
            data = {
                "feedback_data": self.feedback_data,
                "quality_metrics": self.quality_metrics,
                "analysis_reports": self.analysis_reports,
                "retry_strategies": self.retry_strategies
            }
            feedback_file = self.feedback_dir / "feedback_data.json"
            write_file(feedback_file, json.dumps(data, indent=2))
            logger.info("Saved feedback data")
        except Exception as e:
            logger.error(f"Failed to save feedback data: {str(e)}")
    
    def ingest_feedback(self, feedback: Dict[str, Any]) -> None:
        """Ingest feedback data for analysis.
        
        Args:
            feedback: Feedback data to ingest
        """
        try:
            # Validate feedback structure
            self._validate_feedback(feedback)
            
            # Store feedback data
            feedback_id = feedback.get("id", str(len(self.feedback_data)))
            self.feedback_data[feedback_id] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": feedback
            }
            
            # Process feedback based on type
            feedback_type = feedback.get("type")
            if feedback_type == "quality_metrics":
                self._process_quality_metrics(feedback)
            elif feedback_type == "user_feedback":
                self._process_user_feedback(feedback)
            elif feedback_type == "task_failure":
                self._process_task_failure(feedback)
            
            # Generate analysis report
            self._generate_analysis_report(feedback_id)
            
            # Save updated data
            self._save_feedback_data()
            
            logger.info(f"Ingested feedback of type {feedback_type}")
            
        except Exception as e:
            logger.error(f"Failed to ingest feedback: {str(e)}")
    
    def _validate_feedback(self, feedback: Dict[str, Any]) -> None:
        """Validate feedback data structure.
        
        Args:
            feedback: Feedback data to validate
            
        Raises:
            ValueError: If feedback is invalid
        """
        required_fields = {"type", "task_id"}
        missing_fields = required_fields - set(feedback.keys())
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
    
    def _process_quality_metrics(self, feedback: Dict[str, Any]) -> None:
        """Process quality metrics feedback.
        
        Args:
            feedback: Quality metrics feedback
        """
        task_id = feedback["task_id"]
        metrics = feedback.get("metrics", {})
        
        if task_id not in self.quality_metrics:
            self.quality_metrics[task_id] = []
        
        self.quality_metrics[task_id].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics
        })
    
    def _process_user_feedback(self, feedback: Dict[str, Any]) -> None:
        """Process user feedback.
        
        Args:
            feedback: User feedback data
        """
        task_id = feedback["task_id"]
        user_feedback = feedback.get("feedback", {})
        
        # Store user feedback
        if task_id not in self.feedback_data:
            self.feedback_data[task_id] = {"user_feedback": []}
        
        self.feedback_data[task_id]["user_feedback"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "feedback": user_feedback
        })
    
    def _process_task_failure(self, feedback: Dict[str, Any]) -> None:
        """Process task failure feedback.
        
        Args:
            feedback: Task failure feedback
        """
        task_id = feedback["task_id"]
        error = feedback.get("error", "")
        
        # Store failure data
        if task_id not in self.feedback_data:
            self.feedback_data[task_id] = {"failures": []}
        
        self.feedback_data[task_id]["failures"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": error,
            "agent_id": feedback.get("agent_id", "unknown")
        })
        
        # Generate retry strategy
        self._generate_retry_strategy(task_id, error)
    
    def _generate_analysis_report(self, feedback_id: str) -> None:
        """Generate analysis report for feedback.
        
        Args:
            feedback_id: ID of the feedback to analyze
        """
        feedback = self.feedback_data[feedback_id]
        feedback_type = feedback["data"].get("type")
        
        report = {
            "feedback_id": feedback_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": feedback_type,
            "analysis": {}
        }
        
        if feedback_type == "quality_metrics":
            report["analysis"] = self._analyze_quality_metrics(feedback["data"])
        elif feedback_type == "user_feedback":
            report["analysis"] = self._analyze_user_feedback(feedback["data"])
        elif feedback_type == "task_failure":
            report["analysis"] = self._analyze_task_failure(feedback["data"])
        
        self.analysis_reports.append(report)
    
    def _analyze_quality_metrics(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze quality metrics.
        
        Args:
            feedback: Quality metrics feedback
            
        Returns:
            Analysis results
        """
        metrics = feedback.get("metrics", {})
        task_id = feedback["task_id"]
        
        # Calculate trends
        task_metrics = self.quality_metrics.get(task_id, [])
        if len(task_metrics) > 1:
            current = metrics.get("quality_score", 0)
            previous = task_metrics[-2]["metrics"].get("quality_score", 0)
            trend = "improving" if current > previous else "degrading" if current < previous else "stable"
        else:
            trend = "initial"
        
        return {
            "quality_score": metrics.get("quality_score", 0),
            "trend": trend,
            "recommendations": self._generate_quality_recommendations(metrics)
        }
    
    def _analyze_user_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user feedback.
        
        Args:
            feedback: User feedback data
            
        Returns:
            Analysis results
        """
        user_feedback = feedback.get("feedback", {})
        
        return {
            "satisfaction": user_feedback.get("satisfaction", 0),
            "sentiment": self._analyze_sentiment(user_feedback.get("comments", "")),
            "action_items": self._extract_action_items(user_feedback.get("comments", ""))
        }
    
    def _analyze_task_failure(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze task failure.
        
        Args:
            feedback: Task failure feedback
            
        Returns:
            Analysis results
        """
        error = feedback.get("error", "")
        
        return {
            "error_type": self._classify_error(error),
            "severity": self._assess_severity(error),
            "retry_strategy": self.retry_strategies.get(feedback["task_id"])
        }
    
    def _generate_quality_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate quality improvement recommendations.
        
        Args:
            metrics: Quality metrics
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Check quality score
        quality_score = metrics.get("quality_score", 0)
        if quality_score < 0.8:
            recommendations.append("Consider improving code quality and test coverage")
        
        # Check error count
        error_count = metrics.get("error_count", 0)
        if error_count > 0:
            recommendations.append("Address reported errors to improve reliability")
        
        # Check warning count
        warning_count = metrics.get("warning_count", 0)
        if warning_count > 5:
            recommendations.append("Review and address warnings to improve code quality")
        
        return recommendations
    
    def _analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment analysis result
        """
        # Placeholder for sentiment analysis
        # In a real implementation, this would use NLP or ML
        return "neutral"
    
    def _extract_action_items(self, text: str) -> List[str]:
        """Extract action items from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of action items
        """
        # Placeholder for action item extraction
        # In a real implementation, this would use NLP
        return []
    
    def _classify_error(self, error: str) -> str:
        """Classify error type.
        
        Args:
            error: Error message
            
        Returns:
            Error classification
        """
        # Placeholder for error classification
        # In a real implementation, this would use pattern matching or ML
        return "unknown"
    
    def _assess_severity(self, error: str) -> str:
        """Assess error severity.
        
        Args:
            error: Error message
            
        Returns:
            Severity level
        """
        # Placeholder for severity assessment
        # In a real implementation, this would use rules or ML
        return "medium"
    
    def _generate_retry_strategy(self, task_id: str, error: str) -> None:
        """Generate retry strategy for failed task.
        
        Args:
            task_id: ID of failed task
            error: Error message
        """
        # Placeholder for retry strategy generation
        # In a real implementation, this would use rules or ML
        self.retry_strategies[task_id] = {
            "max_retries": 3,
            "backoff_factor": 2,
            "timeout": 300
        }
    
    def get_quality_metrics(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Get quality metrics.
        
        Args:
            task_id: Optional specific task ID
            
        Returns:
            Quality metrics
        """
        if task_id:
            return self.quality_metrics.get(task_id, {})
        return self.quality_metrics
    
    def get_analysis_reports(self, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get analysis reports.
        
        Args:
            task_id: Optional specific task ID
            
        Returns:
            Analysis reports
        """
        if task_id:
            return [r for r in self.analysis_reports if r.get("task_id") == task_id]
        return self.analysis_reports
    
    def get_retry_strategy(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get retry strategy for task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Retry strategy if available
        """
        return self.retry_strategies.get(task_id)

# Example Usage (for testing purposes):
if __name__ == '__main__':
    engine = FeedbackEngineV2()
    engine.launch()
    engine.connect_data_source("agent_errors", {"type": "log_stream", "path": "/logs/agent_errors.log"})
    
    sample_feedback_error = {
        "id": "err_123",
        "agent_id": "Agent-Alpha",
        "timestamp": "2024-05-17T10:00:00Z",
        "event_type": "error",
        "severity": "high",
        "data": {
            "message": "Critical component failed to initialize.",
            "stack_trace": "..."
        }
    }
    engine.ingest_feedback(sample_feedback_error)

    sample_feedback_perf = {
        "id": "perf_456",
        "agent_id": "Agent-Beta",
        "timestamp": "2024-05-17T10:05:00Z",
        "event_type": "performance_degradation",
        "severity": "medium",
        "data": {
            "metric": "response_time_p95",
            "value": "5000ms",
            "threshold": "1000ms"
        }
    }
    engine.ingest_feedback(sample_feedback_perf)

    reports = engine.get_analysis_reports()
    print("\nAnalysis Reports:")
    for report in reports:
        print(report)

    strategy = engine.get_retry_strategy(sample_feedback_error)
    if strategy:
        print("\nSuggested Retry Strategy:")
        print(strategy) 