"""
Devlog Formatter for Dream.OS

This module provides formatting utilities for devlog entries, including
special formatting for ethos violations and compliance information.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

class DevlogFormatter:
    """Formats devlog entries with special handling for ethos-related content."""
    
    def __init__(self, devlog_path: Optional[str] = None):
        """Initialize the formatter.
        
        Args:
            devlog_path: Path to devlog directory. If None, uses default location.
        """
        self.devlog_path = Path(devlog_path or "runtime/logs/empathy")
        self.devlog_path.mkdir(parents=True, exist_ok=True)
        
    def format_violation(self, violation: Dict) -> str:
        """Format an ethos violation for devlog entry.
        
        Args:
            violation: Dictionary containing violation details
            
        Returns:
            str: Formatted violation message
        """
        severity = violation.get("severity", "low")
        principle = violation.get("principle", "unknown")
        details = violation.get("details", "")
        recommendation = violation.get("recommendation", "")
        
        # Format severity emoji
        severity_emoji = {
            "low": "⚠️",
            "medium": "🚨",
            "high": "🛑",
            "critical": "💥"
        }.get(severity, "⚠️")
        
        # Format message
        message = [
            f"{severity_emoji} ETHOS VIOLATION — {principle}",
            f"→ Details: {details}",
            f"→ Recommended action: {recommendation}"
        ]
        
        return "\n".join(message)
        
    def format_compliance_report(self, report: Dict) -> str:
        """Format an ethos compliance report for devlog entry.
        
        Args:
            report: Dictionary containing compliance report
            
        Returns:
            str: Formatted compliance report
        """
        timestamp = report.get("timestamp", datetime.now().isoformat())
        metrics = report.get("metrics", {})
        recommendations = report.get("recommendations", [])
        
        # Format message
        message = [
            "📊 ETHOS COMPLIANCE REPORT",
            f"Generated: {timestamp}",
            "\nAlignment Metrics:"
        ]
        
        # Add metrics
        for value, score in metrics.items():
            status = "✅" if score >= 0.7 else "⚠️"
            message.append(f"{status} {value}: {score:.2%}")
            
        # Add recommendations
        if recommendations:
            message.append("\nRecommendations:")
            for rec in recommendations:
                message.append(f"→ {rec}")
                
        return "\n".join(message)
        
    def format_identity_update(self, update: Dict) -> str:
        """Format an identity update for devlog entry.
        
        Args:
            update: Dictionary containing identity update details
            
        Returns:
            str: Formatted identity update message
        """
        agent_id = update.get("agent_id", "unknown")
        changes = update.get("changes", {})
        reason = update.get("reason", "")
        
        # Format message
        message = [
            "🔄 AGENT IDENTITY UPDATE",
            f"Agent: {agent_id}",
            f"Reason: {reason}",
            "\nChanges:"
        ]
        
        # Add changes
        for key, value in changes.items():
            message.append(f"→ {key}: {value}")
            
        return "\n".join(message)
        
    def write_devlog(self, content: str, category: str = "general") -> None:
        """Write formatted content to devlog.
        
        Args:
            content: Formatted content to write
            category: Category of the log entry
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.devlog_path / f"{category}_{timestamp}.md"
        
        with open(log_file, 'w') as f:
            f.write(content)
            
    def format_and_write_violation(self, violation: Dict) -> None:
        """Format and write a violation to devlog.
        
        Args:
            violation: Dictionary containing violation details
        """
        content = self.format_violation(violation)
        self.write_devlog(content, "violation")
        
    def format_and_write_compliance(self, report: Dict) -> None:
        """Format and write a compliance report to devlog.
        
        Args:
            report: Dictionary containing compliance report
        """
        content = self.format_compliance_report(report)
        self.write_devlog(content, "compliance")
        
    def format_and_write_identity(self, update: Dict) -> None:
        """Format and write an identity update to devlog.
        
        Args:
            update: Dictionary containing identity update details
        """
        content = self.format_identity_update(update)
        self.write_devlog(content, "identity")
        
    def get_recent_violations(self, limit: int = 10) -> list:
        """Get recent ethos violations from devlog.
        
        Args:
            limit: Maximum number of violations to return
            
        Returns:
            list: Recent violations
        """
        violations = []
        for log_file in sorted(
            self.devlog_path.glob("violation_*.md"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:limit]:
            with open(log_file) as f:
                violations.append(f.read())
        return violations
        
    def get_compliance_history(self, days: int = 7) -> list:
        """Get compliance history from devlog.
        
        Args:
            days: Number of days of history to return
            
        Returns:
            list: Compliance history
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        history = []
        
        for log_file in sorted(
            self.devlog_path.glob("compliance_*.md"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        ):
            if log_file.stat().st_mtime >= cutoff:
                with open(log_file) as f:
                    history.append(f.read())
                    
        return history 