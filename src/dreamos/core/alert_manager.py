import logging
import json
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set
import discord
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)

class AlertAggregator:
    """Manages aggregation of similar alerts within a time window."""
    
    def __init__(self, window_seconds: int = 600):  # 10 minutes default
        self.window_seconds = window_seconds
        self.alert_groups: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count": 0,
            "agents": set(),
            "first_seen": None,
            "last_seen": None,
            "details": [],
            "recovery_count": 0,
            "recovered_agents": set()
        })
    
    def add_alert(self, alert_type: str, agent_id: Optional[str], details: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add an alert to the aggregation window.
        
        Returns:
            Aggregated alert if window is complete, None otherwise
        """
        now = datetime.utcnow()
        group = self.alert_groups[alert_type]
        
        # Initialize timestamps if first alert
        if group["first_seen"] is None:
            group["first_seen"] = now
        
        # Update group stats
        group["count"] += 1
        group["last_seen"] = now
        if agent_id:
            group["agents"].add(agent_id)
        
        # Track recovery status
        if alert_type == "RECOVERY" and agent_id:
            group["recovery_count"] += 1
            group["recovered_agents"].add(agent_id)
        
        # Store relevant details
        group["details"].append({
            "timestamp": now.isoformat(),
            "agent_id": agent_id,
            "details": details
        })
        
        # Check if window is complete
        if (now - group["first_seen"]).total_seconds() >= self.window_seconds:
            return self._create_aggregated_alert(alert_type, group)
        
        return None
    
    def _create_aggregated_alert(self, alert_type: str, group: Dict[str, Any]) -> Dict[str, Any]:
        """Create an aggregated alert from a completed group."""
        now = datetime.utcnow()
        duration = (now - group["first_seen"]).total_seconds()
        
        # Build summary message
        if alert_type == "DRIFT":
            message = f"🚨 {group['count']} agents drifted in the last {int(duration/60)} minutes"
            if group["recovery_count"] > 0:
                message += f"\n🛠️ Recovery succeeded for {group['recovery_count']} of them"
            message += f"\nAgents affected: {', '.join(sorted(group['agents']))}"
            
        elif alert_type == "ERROR":
            message = f"❌ {group['count']} errors occurred in the last {int(duration/60)} minutes"
            message += f"\nAffected agents: {', '.join(sorted(group['agents']))}"
            
        elif alert_type == "RECOVERY":
            message = f"✅ {group['count']} recovery attempts in the last {int(duration/60)} minutes"
            message += f"\nSuccess rate: {group['recovery_count']}/{group['count']}"
            message += f"\nAgents recovered: {', '.join(sorted(group['recovered_agents']))}"
            
        else:
            message = f"ℹ️ {group['count']} {alert_type} alerts in the last {int(duration/60)} minutes"
            message += f"\nAffected agents: {', '.join(sorted(group['agents']))}"
        
        return {
            "type": f"AGGREGATED_{alert_type}",
            "message": message,
            "severity": "warning",
            "details": {
                "count": group["count"],
                "agents": list(sorted(group["agents"])),
                "duration_seconds": duration,
                "recovery_count": group["recovery_count"],
                "recovered_agents": list(sorted(group["recovered_agents"])),
                "first_seen": group["first_seen"].isoformat(),
                "last_seen": group["last_seen"].isoformat()
            }
        }
    
    def cleanup_old_groups(self):
        """Remove alert groups older than the window."""
        now = datetime.utcnow()
        for alert_type in list(self.alert_groups.keys()):
            group = self.alert_groups[alert_type]
            if group["first_seen"] and (now - group["first_seen"]).total_seconds() > self.window_seconds:
                del self.alert_groups[alert_type]

class TrendDetector:
    """Analyzes swarm metrics to detect patterns, fatigue, and anomalies."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.trend_window = config.get("trend_detection", {}).get("window_days", 7)
        self.fatigue_threshold = config.get("trend_detection", {}).get("fatigue_threshold", 0.2)  # 20% degradation
        self.cluster_threshold = config.get("trend_detection", {}).get("cluster_threshold", 3)  # 3 similar events
        self.regression_threshold = config.get("trend_detection", {}).get("regression_threshold", 0.15)  # 15% regression
    
    def detect_trend_reversals(self, all_metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect when improving trends start to degrade.
        
        Args:
            all_metrics: List of daily metrics (historical + current day), newest entry is current day.
            
        Returns:
            List of trend reversal warnings
        """
        warnings = []
        if len(all_metrics) < 3:  # Need at least 3 days for trend detection
            return warnings
        
        # Analyze each metric type
        metric_types = {
            "task_executions": "Tasks completed",
            "recovery_success_rate_numeric": "Recovery success rate",
            "errors": "Error rate"
        }
        
        for metric_key, metric_name in metric_types.items():
            # Get last window_days of values, ensuring metric_key exists
            values = [m.get(metric_key, 0) for m in all_metrics[:self.trend_window] if m is not None and isinstance(m, dict)]
            
            # Calculate moving averages if enough data
            if len(values) >= 3:
                # Make sure values are numeric for sum/avg
                numeric_values = [v for v in values if isinstance(v, (int, float))]
                if len(numeric_values) < 3: continue

                recent_avg = sum(numeric_values[:3]) / 3
                # Ensure there are older values to compare against
                if len(numeric_values) > 3:
                    older_avg = sum(numeric_values[3:]) / (len(numeric_values) - 3)
                    # Check for significant reversal
                    # For error rates, an increase is a reversal (degradation)
                    if metric_key == "errors":
                        if older_avg > 0 and recent_avg > older_avg * (1 + self.regression_threshold):
                            warnings.append({
                                "type": "TREND_REVERSAL",
                                "metric": metric_name,
                                "severity": "warning",
                                "message": f"⚠️ {metric_name} showing regression (increase): {recent_avg:.1f} vs {older_avg:.1f} (avg)"
                            })
                    # For task_executions and recovery_success, a decrease is a reversal
                    else:
                        if older_avg > 0 and recent_avg < older_avg * (1 - self.regression_threshold):
                            warnings.append({
                                "type": "TREND_REVERSAL",
                                "metric": metric_name,
                                "severity": "warning",
                                "message": f"⚠️ {metric_name} showing regression (decrease): {recent_avg:.1f} vs {older_avg:.1f} (avg)"
                            })
                elif len(numeric_values) == 3 : # Not enough older data, but can check if recent is bad
                    pass
        
        return warnings
    
    def detect_clustered_failures(self, all_metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect clusters of similar failures across agents.
        
        Args:
            all_metrics: List of daily metrics (historical + current day), newest entry is current day.
            
        Returns:
            List of cluster warnings
        """
        warnings = []
        # Consider a shorter window for clusters, e.g., last 2-3 days including current
        cluster_window_metrics = all_metrics[:min(3, len(all_metrics))]
        if len(cluster_window_metrics) < 1:
            return warnings
        
        agent_failures: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            "drifts": 0,
            "errors": 0,
            "recovery_failures": 0 # Assuming this might be tracked directly or inferred
        })
        
        for day_metrics in cluster_window_metrics:
            if not isinstance(day_metrics, dict) or "agent_activity" not in day_metrics: continue
            for agent_id, stats in day_metrics.get("agent_activity", {}).items():
                if not isinstance(stats, dict): continue
                agent_failures[agent_id]["drifts"] += stats.get("drift_events", stats.get("drift_count",0)) # Use drift_events or drift_count
                agent_failures[agent_id]["errors"] += stats.get("errors", 0)
                # Infer recovery failures if not directly tracked:
                # recovery_attempts = stats.get("recovery_attempts", 0)
                # successful_recoveries = stats.get("successful_recoveries", 0)
                # agent_failures[agent_id]["recovery_failures"] += (recovery_attempts - successful_recoveries)
        
        for failure_type in ["drifts", "errors"]:
            affected_agents_counts = {agent_id: stats[failure_type] for agent_id, stats in agent_failures.items() if stats[failure_type] >= self.cluster_threshold}
            
            if len(affected_agents_counts) >= 2: # At least 2 agents showing clustered failures
                agents_involved_str = ", ".join([f"Agent-{aid} ({count})" for aid, count in affected_agents_counts.items()])
                warnings.append({
                    "type": "FAILURE_CLUSTER",
                    "failure_type": failure_type,
                    "agents_involved": agents_involved_str,
                    "severity": "warning",
                    "message": f"🔍 {failure_type.title()} cluster detected: {agents_involved_str}"
                })
        return warnings
    
    def detect_agent_fatigue(self, all_metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect signs of agent fatigue or degradation.
        
        Args:
            all_metrics: List of daily metrics (historical + current day), newest entry is current day.
            
        Returns:
            List of fatigue warnings
        """
        warnings = []
        if len(all_metrics) < 3:  # Need at least 3 days for fatigue detection
            return warnings
        
        # Get agent metrics for last window_days
        agent_daily_metrics: Dict[str, Dict[str, List[Any]]] = defaultdict(lambda: defaultdict(list))
        
        for day_data in all_metrics[:self.trend_window]:
            if not isinstance(day_data, dict) or "agent_activity" not in day_data: continue
            for agent_id, stats in day_data.get("agent_activity", {}).items():
                if not isinstance(stats, dict): continue
                agent_daily_metrics[agent_id]["tasks_completed"].append(stats.get("tasks_completed", 0))
                agent_daily_metrics[agent_id]["errors"].append(stats.get("errors", 0))
                agent_daily_metrics[agent_id]["drift_events"].append(stats.get("drift_events", stats.get("drift_count", 0)))
                agent_daily_metrics[agent_id]["total_drift_time_seconds"].append(stats.get("total_drift_time_seconds", 0))
        
        for agent_id, metrics_history in agent_daily_metrics.items():
            fatigue_signs = []
            
            # Check task output trend
            tasks = [v for v in metrics_history["tasks_completed"] if isinstance(v, (int,float))]
            if len(tasks) >= 3:
                recent_tasks_avg = sum(tasks[:3]) / 3
                if len(tasks) > 3:
                    older_tasks_avg = sum(tasks[3:]) / (len(tasks) - 3)
                    if older_tasks_avg > 0 and recent_tasks_avg < older_tasks_avg * (1 - self.fatigue_threshold):
                        fatigue_signs.append(f"Tasks completed: ▼ {recent_tasks_avg:.1f} vs {older_tasks_avg:.1f} (avg)")
            
            # Check error rate trend
            errors = [v for v in metrics_history["errors"] if isinstance(v, (int,float))]
            if len(errors) >= 3:
                recent_errors_avg = sum(errors[:3]) / 3
                if len(errors) > 3:
                    older_errors_avg = sum(errors[3:]) / (len(errors) - 3)
                    if recent_errors_avg > older_errors_avg * (1 + self.fatigue_threshold): # Errors increasing is bad
                        fatigue_signs.append(f"Errors: ▲ {recent_errors_avg:.1f} vs {older_errors_avg:.1f} (avg)")
            
            # Check drift frequency
            drifts = [v for v in metrics_history["drift_events"] if isinstance(v, (int,float))]
            if len(drifts) >= 3:
                recent_drifts_avg = sum(drifts[:3]) / 3
                if len(drifts) > 3:
                    older_drifts_avg = sum(drifts[3:]) / (len(drifts) - 3)
                    if recent_drifts_avg > older_drifts_avg * (1 + self.fatigue_threshold):
                        fatigue_signs.append(f"Drift events: ▲ {recent_drifts_avg:.1f} vs {older_drifts_avg:.1f} (avg)")
            
            # Check drift duration
            drift_durations = [v for v in metrics_history["total_drift_time_seconds"] if isinstance(v, (int,float))]
            if len(drift_durations) >= 3:
                recent_duration_avg = sum(drift_durations[:3]) / 3
                if len(drift_durations) > 3:
                    older_duration_avg = sum(drift_durations[3:]) / (len(drift_durations) - 3)
                    if older_duration_avg >= 0 and recent_duration_avg > older_duration_avg * (1 + self.fatigue_threshold): # Allow older_duration_avg to be 0
                        fatigue_signs.append(f"Drift duration: ▲ {int(recent_duration_avg/60)}m vs {int(older_duration_avg/60)}m (avg)")
            
            if fatigue_signs:
                warnings.append({
                    "type": "AGENT_FATIGUE",
                    "agent_id": agent_id,
                    "signs": fatigue_signs,
                    "severity": "warning",
                    "message": f"🚩 Performance Warning: Agent-{agent_id}\n" + "\n".join(fatigue_signs)
                })
        return warnings
    
    def analyze_trends(self, historical_metrics: List[Dict[str, Any]], current_day_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze metrics for trends, patterns, and anomalies.
        Combines historical data with current day's snapshot for analysis.
        
        Args:
            historical_metrics: List of past daily digest data, newest first (or oldest first, ensure consistency).
            current_day_snapshot: Digest-like snapshot for the current day being analyzed.
            
        Returns:
            Dict containing trend analysis results
        """
        # Ensure historical_metrics is sorted with newest first if it's not already guaranteed by caller
        # For this implementation, _load_historical_digests_up_to sorts oldest first.
        # So we reverse it here to have newest (most recent historical) first for combining.
        sorted_historical = sorted(historical_metrics, key=lambda x: x.get("date", ""), reverse=True)

        # Combine current day's snapshot with historical data
        # The current_day_snapshot is the most recent data point.
        all_metrics_for_analysis = [current_day_snapshot] + sorted_historical
        
        # To ensure correct numeric conversion for recovery_success_rate for detect_trend_reversals
        for metric_set in all_metrics_for_analysis:
            if isinstance(metric_set, dict) and "recovery_success" in metric_set and isinstance(metric_set["recovery_success"], str):
                try:
                    # Example: "1/1 (100.0%)" -> 100.0
                    # Example: "N/A" -> 0 or skip (handle potential ValueError)
                    rate_str = metric_set["recovery_success"].split('(')[-1].split('%')[0]
                    metric_set["recovery_success_rate_numeric"] = float(rate_str)
                except (ValueError, IndexError):
                    metric_set["recovery_success_rate_numeric"] = 0.0 # Default if parsing fails
            elif isinstance(metric_set, dict): # Ensure key exists even if not a rate string
                metric_set["recovery_success_rate_numeric"] = 0.0

        return {
            "trend_reversals": self.detect_trend_reversals(all_metrics_for_analysis),
            "failure_clusters": self.detect_clustered_failures(all_metrics_for_analysis),
            "agent_fatigue": self.detect_agent_fatigue(all_metrics_for_analysis)
        }

class DailyDigest:
    """Manages daily swarm performance digest generation and distribution."""
    
    def __init__(self, workspace_root: Path, config: Dict[str, Any]):
        self.workspace_root = workspace_root
        self.config = config
        self.digest_dir = workspace_root / "runtime" / "digests"
        self.digest_dir.mkdir(parents=True, exist_ok=True)
        
        self.trend_detector = TrendDetector(config)
        
        self.discord_enabled = config.get("discord", {}).get("enabled", False)
        self.discord_channel_id = config.get("discord", {}).get("channel_id")
        self.discord_client = None
        if self.discord_enabled:
            self._init_discord()
        
        self.stats = {
            "drift_events": [],
            "recovery_events": [],
            "error_events": [],
            "task_executions": [],
            "agent_activity": defaultdict(lambda: {
                "tasks_completed": 0,
                "errors": 0,
                "drift_count": 0,
                "total_drift_time_seconds": 0,
                "last_active": None,
                "recovery_attempts": 0,
                "successful_recoveries": 0
            })
        }
        
        self.digest_task_started = False

        if self.config.get("discord", {}).get("enabled"):
            self._init_discord()
    
    def _init_discord(self):
        """Initialize Discord client if configured."""
        try:
            token = self.config["discord"]["token"]
            self.discord_client = discord.Client()
            
            # Start Discord client in background
            asyncio.create_task(self.discord_client.start(token))
            
        except Exception as e:
            logger.error(f"Failed to initialize Discord client for digest: {e}")
            self.discord_client = None
    
    def _load_previous_digest(self, date: datetime) -> Optional[Dict[str, Any]]:
        """Load digest data from previous day."""
        try:
            prev_date = (date - timedelta(days=1)).strftime("%Y-%m-%d")
            digest_path = self.digest_dir / f"daily-{prev_date}.json"
            
            if not digest_path.exists():
                return None
            
            with open(digest_path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Error loading previous digest: {e}")
            return None
    
    def _calculate_metric_delta(self, current: Any, previous: Any, metric_type: str = "number") -> Tuple[str, str]:
        """Calculate and format metric delta.
        
        Returns:
            Tuple of (formatted_delta, trend_emoji)
        """
        if previous is None:
            return "N/A", "🆕"
        
        if metric_type == "number":
            try:
                current_num = float(current)
                previous_num = float(previous)
                delta = current_num - previous_num
                
                if delta > 0:
                    return f"+{delta}", "▲"
                elif delta < 0:
                    return f"{delta}", "▼"
                else:
                    return "0", "="
            except (ValueError, TypeError):
                return "N/A", "❓"
        
        elif metric_type == "percentage":
            try:
                current_pct = float(current.split("%")[0])
                previous_pct = float(previous.split("%")[0])
                delta = current_pct - previous_pct
                
                if delta > 0:
                    return f"+{delta:.1f}%", "▲"
                elif delta < 0:
                    return f"{delta:.1f}%", "▼"
                else:
                    return "0%", "="
            except (ValueError, TypeError, IndexError):
                return "N/A", "❓"
        
        elif metric_type == "duration":
            try:
                # Parse duration like "6m 42s"
                def parse_duration(dur: str) -> int:
                    parts = dur.split()
                    total_seconds = 0
                    for part in parts:
                        if "m" in part:
                            total_seconds += int(part.replace("m", "")) * 60
                        elif "s" in part:
                            total_seconds += int(part.replace("s", ""))
                    return total_seconds
                
                current_sec = parse_duration(current)
                previous_sec = parse_duration(previous)
                delta_sec = current_sec - previous_sec
                
                if delta_sec > 0:
                    return f"+{delta_sec//60}m {delta_sec%60}s", "▲"
                elif delta_sec < 0:
                    return f"{delta_sec//60}m {abs(delta_sec%60)}s", "▼"
                else:
                    return "0s", "="
            except (ValueError, TypeError):
                return "N/A", "❓"
        
        return "N/A", "❓"
    
    def _generate_comparison_section(self, current: Dict[str, Any], previous: Optional[Dict[str, Any]]) -> str:
        """Generate comparison section for digest."""
        if not previous:
            return "🆕 First day of tracking or previous day's data not available."
        
        comparison = ["🆚 **Compared to Yesterday**\n"]
        
        metrics = [
            ("Task executions", "task_executions", "number"),
            ("Drift events", "drift_events", "number"),
            ("Recovery success rate", "recovery_success", "percentage"),
            ("Errors", "errors", "number")
        ]
        
        for label, key, metric_type in metrics:
            current_val = current.get(key)
            prev_val = previous.get(key)
            if current_val is not None and prev_val is not None:
                delta, emoji = self._calculate_metric_delta(current_val, prev_val, metric_type)
                comparison.append(f"* {label}: {current_val} (vs {prev_val}) {emoji} {delta}")
            elif current_val is not None:
                comparison.append(f"* {label}: {current_val} (vs N/A) 🆕")
            else:
                comparison.append(f"* {label}: N/A")
        
        comparison.append("\n**Agent Changes**")
        
        current_drift = current.get("longest_drift")
        previous_drift = previous.get("longest_drift")
        
        if current_drift and previous_drift and current_drift.get("agent") and previous_drift.get("agent") and current_drift.get("agent") == previous_drift.get("agent"):
            delta, emoji = self._calculate_metric_delta(
                current_drift.get("duration", "0s"), 
                previous_drift.get("duration", "0s"), 
                "duration"
            )
            comparison.append(f"* Longest Drift (Agent-{current_drift['agent']}): {current_drift.get('duration','N/A')} (vs {previous_drift.get('duration','N/A')}) {emoji} {delta}")
        elif current_drift and current_drift.get("agent"):
            comparison.append(f"* Longest Drift: Agent-{current_drift['agent']} ({current_drift.get('duration','N/A')}) (Prev: N/A) 🆕")
        elif previous_drift and previous_drift.get("agent"):
             comparison.append(f"* Longest Drift: N/A (Prev: Agent-{previous_drift['agent']} ({previous_drift.get('duration','N/A')}))")
        else:
            comparison.append("* Longest Drift: N/A")

        current_top = current.get("top_performer")
        previous_top = previous.get("top_performer")

        if current_top and previous_top and current_top.get("agent") and previous_top.get("agent") and current_top.get("agent") == previous_top.get("agent"):
            delta, emoji = self._calculate_metric_delta(
                current_top.get("tasks", 0),
                previous_top.get("tasks", 0),
                "number"
            )
            comparison.append(f"* Top Performer (Agent-{current_top['agent']}): {current_top.get('tasks',0)} tasks (vs {previous_top.get('tasks',0)}) {emoji} {delta}")
        elif current_top and current_top.get("agent"):
            comparison.append(f"* Top Performer: Agent-{current_top['agent']} ({current_top.get('tasks',0)} tasks) (Prev: N/A) 🆕")
        elif previous_top and previous_top.get("agent"):
            comparison.append(f"* Top Performer: N/A (Prev: Agent-{previous_top['agent']} ({previous_top.get('tasks',0)} tasks))")
        else:
            comparison.append("* Top Performer: N/A")
            
        return "\n".join(comparison)
    
    async def _send_discord_digest(self, digest: Dict[str, Any], markdown: str):
        """Send digest to Discord channel and pin it."""
        try:
            if not self.discord_client or not self.discord_client.is_ready():
                logger.warning("Discord client not ready for digest")
                return
            
            channel = self.discord_client.get_channel(self.discord_channel_id)
            if not channel:
                logger.warning(f"Discord channel {self.discord_channel_id} not found")
                return
            
            # Load previous digest for comparison
            previous_digest = self._load_previous_digest(datetime.strptime(digest["date"], "%Y-%m-%d"))
            
            # Create rich embed for digest
            embed = discord.Embed(
                title=f"📊 Daily Swarm Digest - {digest['date']}",
                description="Daily performance report for Dream.OS swarm",
                color=0x3498db,  # Blue color
                timestamp=datetime.utcnow()
            )
            
            # Add swarm overview
            embed.add_field(
                name="🛰️ Swarm Overview",
                value=f"```\nTotal agents: {digest['total_agents']}\nDrift events: {digest['drift_events']}\nRecovery: {digest['recovery_success']}\nTasks: {digest['task_executions']}\nErrors: {digest['errors']}\n```",
                inline=False
            )
            
            # Add comparison section
            comparison = self._generate_comparison_section(digest, previous_digest)
            embed.add_field(
                name="📈 Performance Trends",
                value=f"```\n{comparison}\n```",
                inline=False
            )
            
            # Add trend analysis if available
            if "trend_analysis" in digest:
                trend_warnings = []
                
                # Add trend reversals
                for warning in digest["trend_analysis"]["trend_reversals"]:
                    trend_warnings.append(warning["message"])
                
                # Add failure clusters
                for warning in digest["trend_analysis"]["failure_clusters"]:
                    trend_warnings.append(warning["message"])
                
                # Add agent fatigue warnings
                for warning in digest["trend_analysis"]["agent_fatigue"]:
                    trend_warnings.append(warning["message"])
                
                if trend_warnings:
                    embed.add_field(
                        name="⚠️ Trend Analysis",
                        value="```\n" + "\n".join(trend_warnings) + "\n```",
                        inline=False
                    )
            
            # Add performance highlights
            embed.add_field(
                name="🏆 Performance Highlights",
                value=f"```\nLongest drift: Agent-{digest['longest_drift']['agent']} ({digest['longest_drift']['duration']})\nTop performer: Agent-{digest['top_performer']['agent']} ({digest['top_performer']['tasks']} tasks, {digest['top_performer']['errors']} errors)\n```",
                inline=False
            )
            
            # Add agent activity summary
            agent_summary = []
            for agent_id, stats in sorted(self.stats["agent_activity"].items()):
                agent_summary.append(
                    f"Agent-{agent_id}: {stats['tasks_completed']} tasks, "
                    f"{stats['errors']} errors, {stats['drift_count']} drifts"
                )
            
            embed.add_field(
                name="📊 Agent Activity Summary",
                value="```\n" + "\n".join(agent_summary) + "\n```",
                inline=False
            )
            
            # Add footer with link to full report
            embed.set_footer(text="Full report available in runtime/digests/")
            
            # Send message and pin it
            message = await channel.send(embed=embed)
            await message.pin()
            
            # Unpin previous digest if exists
            pins = await channel.pins()
            for pin in pins:
                if pin.id != message.id and "Daily Swarm Digest" in pin.embeds[0].title:
                    await pin.unpin()
            
            logger.info(f"Daily digest sent and pinned to Discord channel {self.discord_channel_id}")
            
        except Exception as e:
            logger.error(f"Error sending digest to Discord: {e}")
    
    def track_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Track an event for digest generation.
        
        Args:
            event_type: Type of event (DRIFT, RECOVERY, ERROR, TASK_COMPLETE)
            details: Event details including agent_id and other metrics
        """
        now = datetime.utcnow()
        agent_id = details.get("agent_id")
        
        if agent_id:
            agent_stats = self.stats["agent_activity"][agent_id]
            agent_stats["last_active"] = now.isoformat()
            
            if event_type == "TASK_COMPLETE":
                agent_stats["tasks_completed"] += 1
                self.stats["task_executions"].append({
                    "timestamp": now.isoformat(),
                    "agent_id": agent_id,
                    "task_id": details.get("task_id")
                })
            
            elif event_type == "DRIFT":
                agent_stats["drift_count"] += 1
                agent_stats["total_drift_time_seconds"] += details.get("duration", details.get("drift_duration_seconds",0))
                self.stats["drift_events"].append({
                    "timestamp": now.isoformat(),
                    "agent_id": agent_id,
                    "duration": details.get("duration", 0),
                    "drift_type": details.get("drift_type")
                })
            
            elif event_type == "RECOVERY":
                agent_stats["recovery_attempts"] += 1
                if details.get("recovery_successful", False):
                    agent_stats["successful_recoveries"] += 1
                self.stats["recovery_events"].append({
                    "timestamp": now.isoformat(),
                    "agent_id": agent_id,
                    "success": details.get("recovery_successful", False),
                    "duration": details.get("recovery_time_seconds", 0)
                })
            
            elif event_type == "ERROR":
                agent_stats["errors"] += 1
                self.stats["error_events"].append({
                    "timestamp": now.isoformat(),
                    "agent_id": agent_id,
                    "error_type": details.get("error_type"),
                    "details": details.get("details")
                })
    
    async def generate_digest(self, specific_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Generates a daily digest of swarm activity, performance, and trends.
        Uses specific_date for historical generation if provided, else today's date.
        """
        date_to_use = specific_date if specific_date is not None else date.today() # Explicitly check for None
        logger.info(f"Generating daily digest for {date_to_use.isoformat()}...")

        # If generating for a historical date, we should load that day's activity,
        # not use the live self.agent_activity which reflects current/ongoing activity.
        # For simulation purposes where we call generate_digest right after a day's events,
        # self.agent_activity IS the activity for date_to_use.
        # In a real-time system, you'd load agent_activity from a persistent store for specific_date.
        # For now, we assume self.agent_activity is correctly populated for date_to_use by the simulation.

        current_day_agent_activity = self.stats["agent_activity"] # This is fine for the simulation

        total_agents_active = len(current_day_agent_activity)
        total_drift_events = sum(data["drift_count"] for data in current_day_agent_activity.values())
        total_recovery_attempts = sum(data["recovery_attempts"] for data in current_day_agent_activity.values())
        total_successful_recoveries = sum(data["successful_recoveries"] for data in current_day_agent_activity.values())
        recovery_success_rate_str = f"{total_successful_recoveries}/{total_recovery_attempts} ({total_successful_recoveries/total_recovery_attempts*100:.1f}%)" if total_recovery_attempts > 0 else "N/A"
        total_task_executions = sum(data["tasks_completed"] for data in current_day_agent_activity.values())
        total_errors = sum(data["errors"] for data in current_day_agent_activity.values())

        longest_drift_agent = None
        max_drift_time = 0
        for agent_id, data in current_day_agent_activity.items():
            if data["total_drift_time_seconds"] > max_drift_time:
                max_drift_time = data["total_drift_time_seconds"]
                longest_drift_agent = agent_id
        
        longest_drift_str = f"Agent-{longest_drift_agent} ({max_drift_time//60}m {max_drift_time%60}s)" if longest_drift_agent else "None"

        top_performer_agent = None
        max_tasks = -1
        min_errors_for_max_tasks = float('inf')
        for agent_id, data in current_day_agent_activity.items():
            if data["tasks_completed"] > max_tasks:
                max_tasks = data["tasks_completed"]
                min_errors_for_max_tasks = data["errors"]
                top_performer_agent = agent_id
            elif data["tasks_completed"] == max_tasks:
                if data["errors"] < min_errors_for_max_tasks:
                    min_errors_for_max_tasks = data["errors"]
                    top_performer_agent = agent_id
        
        top_performer_str = f"Agent-{top_performer_agent} ({max_tasks} tasks, {min_errors_for_max_tasks} errors)" if top_performer_agent else "None"

        # Trend Analysis: Load historical data *before* date_to_use
        historical_digests_for_trend = self._load_historical_digests_up_to(date_to_use, days_limit=self.trend_detector.trend_window)
        
        # The TrendDetector needs the *current day's* agent activity as one of its inputs
        # to compare against the historical trend.
        # We also need to create a "digest-like" structure for today's raw numbers for trend input.
        current_day_snapshot_for_trend = {
            "date": date_to_use.isoformat(),
            "total_agents": total_agents_active,
            "drift_events": total_drift_events,
            "task_executions": total_task_executions,
            "errors": total_errors,
            "agent_activity": current_day_agent_activity # Pass the raw activity for date_to_use
        }
        # The analyze_trends might need to be adjusted if it expects full digest structures
        # For now, assume it can work with this snapshot + historical full digests
        trend_analysis_results = self.trend_detector.analyze_trends(historical_digests_for_trend, current_day_snapshot_for_trend)


        digest_data = {
            "date": date_to_use.isoformat(),
            "total_agents": total_agents_active,
            "drift_events": total_drift_events,
            "recovery_success": recovery_success_rate_str,
            "task_executions": total_task_executions,
            "errors": total_errors,
            "longest_drift": {"agent": longest_drift_agent, "duration": f"{max_drift_time//60}m {max_drift_time%60}s"} if longest_drift_agent else None,
            "top_performer": {"agent": top_performer_agent, "tasks": max_tasks, "errors": min_errors_for_max_tasks} if top_performer_agent else None,
            "trend_analysis": trend_analysis_results,
            "agent_activity": current_day_agent_activity 
        }

        markdown_report = f"# 📊 Daily Swarm Digest - {date_to_use.isoformat()}\\n\\n"
        markdown_report += "## 🛰️ Swarm Overview\\n"
        markdown_report += f"* Total agents active: {total_agents_active}\\n"
        markdown_report += f"* Drift events: {total_drift_events}\\n"
        markdown_report += f"* Recovery success: {recovery_success_rate_str}\\n"
        markdown_report += f"* Task executions: {total_task_executions}\\n"
        markdown_report += f"* Errors: {total_errors}\\n\\n"

        markdown_report += "## 📈 Performance Trends\\n"
        previous_digest_data = self._load_previous_digest(date_to_use)
        if previous_digest_data:
            markdown_report += self._generate_comparison_section(digest_data, previous_digest_data)
        else:
            markdown_report += "🆕 First day of tracking or previous day's data not available.\\n"
        markdown_report += "\\n"
        
        markdown_report += "## ⚠️ Trend Analysis\\n"
        if trend_analysis_results and any(trend_analysis_results.values()):
            for trend_type, findings in trend_analysis_results.items():
                if findings:
                    markdown_report += f"### {trend_type.replace('_', ' ').title()}\\n"
                    for finding in findings:
                        markdown_report += f"* {finding['message']}\\n"
            markdown_report += "\\n"
        else:
            markdown_report += "* No significant trends detected\\n\\n"

        markdown_report += "## 🏆 Performance Highlights\\n"
        markdown_report += f"* Longest drift: {longest_drift_str}\\n"
        markdown_report += f"* Top performer: {top_performer_str}\\n\\n"

        markdown_report += "## 📊 Agent Activity\\n\\n"
        for agent_id, data in sorted(current_day_agent_activity.items()):
            markdown_report += f"### Agent-{agent_id}\\n"
            markdown_report += f"* Tasks completed: {data['tasks_completed']}\\n"
            markdown_report += f"* Errors: {data['errors']}\\n"
            markdown_report += f"* Drift events: {data['drift_count']}\\n"
            if data['drift_count'] > 0:
                 markdown_report += f"* Total drift time: {data['total_drift_time_seconds']//60}m {data['total_drift_time_seconds']%60}s\\n"
            # Ensure last_active is a string, or handle if it's None or datetime object
            last_active_str = data.get('last_active')
            if isinstance(last_active_str, datetime):
                last_active_str = last_active_str.isoformat()
            elif last_active_str is None:
                last_active_str = "N/A"
            markdown_report += f"* Last active: {last_active_str}\\n\\n"

        json_path = self.digest_dir / f"daily-{date_to_use.isoformat()}.json"
        md_path = self.digest_dir / f"daily-{date_to_use.isoformat()}.md"

        try:
            with open(json_path, "w", encoding='utf-8') as f:
                json.dump(digest_data, f, indent=2)
            logger.info(f"Daily digest JSON saved to {json_path}")
            with open(md_path, "w", encoding='utf-8') as f:
                f.write(markdown_report)
            logger.info(f"Daily digest Markdown saved to {md_path}")
        except IOError as e:
            logger.error(f"Error saving digest files for {date_to_use.isoformat()}: {e}")
            return {}

        if self.discord_enabled and self.discord_channel_id:
            # self._send_discord_digest(digest_data, markdown_report, date_to_use) # Pass date_to_use
            pass

        # Reset daily counters only if generating for the current day (specific_date is None or today)
        if specific_date is None or date_to_use == date.today():
             self._reset_daily_counters()
        
        return digest_data

    def _reset_daily_counters(self):
        logger.info("Resetting daily event counters and agent activity for the new day.")
        self.stats["drift_events"] = []
        self.stats["recovery_events"] = []
        self.stats["error_events"] = []
        self.stats["task_executions"] = []
        self.stats["agent_activity"] = defaultdict(lambda: {
            "tasks_completed": 0,
            "errors": 0,
            "drift_count": 0,
            "total_drift_time_seconds": 0,
            "last_active": None,
            "recovery_attempts": 0,
            "successful_recoveries": 0
        })

    def _load_historical_digests_up_to(self, end_date: date, days_limit: int) -> List[Dict[str, Any]]:
        """Loads historical digests up to (but not including) end_date, for a given number of days."""
        historical_digests = []
        for i in range(1, days_limit + 1): # Start from 1 day ago
            date_to_load = end_date - timedelta(days=i)
            file_path = self.digest_dir / f"daily-{date_to_load.isoformat()}.json"
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding='utf-8') as f:
                        historical_digests.append(json.load(f))
                except Exception as e:
                    logger.warning(f"Could not load or parse historical digest {file_path}: {e}")
            # else:
                # logger.debug(f"Historical digest not found for {date_to_load.isoformat()}")
        
        # Sort by date ascending, so oldest is first
        return sorted(historical_digests, key=lambda x: x.get("date", ""))

    def _load_previous_digest(self, current_date: date) -> Optional[Dict[str, Any]]:
        """Loads the digest from the day immediately preceding current_date."""
        previous_date = current_date - timedelta(days=1)
        file_path = self.digest_dir / f"daily-{previous_date.isoformat()}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load or parse previous day's digest {file_path}: {e}")
        return None

class AlertManager:
    """Manages system alerts and notifications for Dream.OS."""
    
    def __init__(self, config: Dict[str, Any], workspace_root: str):
        """Initialize alert manager.
        
        Args:
            config: Alert configuration
            workspace_root: Workspace root directory (as a string or Path)
        """
        self.config = config
        self.workspace_root = Path(workspace_root)
        self.alert_log_path = self.workspace_root / "runtime" / "alerts.json"
        self._ensure_alert_log()
        self.cleanup_task_started = False
        
        # Initialize Discord client if configured
        self.discord_client = None
        if config.get("discord", {}).get("enabled"):
            self._init_discord()
        
        # Rate limiting state
        self.agent_cooldowns: Dict[str, Dict[str, datetime]] = defaultdict(dict)
        self.alert_counts: Dict[str, int] = defaultdict(int)
        self.last_reset = datetime.utcnow()
        
        # Load rate limiting config with defaults
        self.rate_limits = {
            "global": {
                "max_alerts_per_hour": config.get("rate_limits", {}).get("global", {}).get("max_alerts_per_hour", 100),
                "max_alerts_per_minute": config.get("rate_limits", {}).get("global", {}).get("max_alerts_per_minute", 20)
            },
            "per_agent": {
                "cooldown_seconds": config.get("rate_limits", {}).get("per_agent", {}).get("cooldown_seconds", 300),
                "max_alerts_per_hour": config.get("rate_limits", {}).get("per_agent", {}).get("max_alerts_per_hour", 30)
            },
            "alert_type": {
                "cooldown_seconds": config.get("rate_limits", {}).get("alert_type", {}).get("cooldown_seconds", 60)
            }
        }
        
        # Initialize alert aggregator
        self.aggregator = AlertAggregator(
            window_seconds=config.get("aggregation", {}).get("window_seconds", 600)
        )
        
        # Initialize daily digest
        self.digest = DailyDigest(workspace_root=self.workspace_root, config=self.config)
        
        # Start cleanup task
        # self._start_cleanup_task()
    
    async def _cleanup_loop_coroutine(self):
        """Background task to clean up old alert groups."""
        while True:
            try:
                self.aggregator.cleanup_old_groups()
                await asyncio.sleep(60)  # Run every minute
            except Exception as e:
                logger.error(f"Error in alert cleanup task: {e}")

    async def maybe_start_cleanup_task(self):
        if not self.cleanup_task_started:
            self.cleanup_task_started = True
            logger.info("Starting AlertManager cleanup background task...")
            asyncio.create_task(self._cleanup_loop_coroutine())
    
    def _ensure_alert_log(self):
        """Ensure alert log file exists."""
        if not self.alert_log_path.exists():
            default_log = {
                "version": "1.0",
                "alerts": [],
                "last_updated": datetime.utcnow().isoformat()
            }
            with open(self.alert_log_path, 'w') as f:
                json.dump(default_log, f, indent=2)
    
    def _init_discord(self):
        """Initialize Discord client if configured."""
        try:
            token = self.config["discord"]["token"]
            channel_id = self.config["discord"]["channel_id"]
            
            self.discord_client = discord.Client()
            self.discord_channel_id = channel_id
            
            # Start Discord client in background
            asyncio.create_task(self.discord_client.start(token))
            
        except Exception as e:
            logger.error(f"Failed to initialize Discord client: {e}")
            self.discord_client = None
    
    def _check_rate_limits(self, alert_type: str, agent_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Check if alert should be rate limited.
        
        Args:
            alert_type: Type of alert
            agent_id: Optional agent ID for per-agent limits
            
        Returns:
            Tuple of (should_alert, reason_if_limited)
        """
        now = datetime.utcnow()
        
        # Reset counters if hour has passed
        if (now - self.last_reset) > timedelta(hours=1):
            self.alert_counts.clear()
            self.last_reset = now
        
        # Check global limits
        self.alert_counts["global"] += 1
        if self.alert_counts["global"] > self.rate_limits["global"]["max_alerts_per_hour"]:
            return False, "Global hourly alert limit exceeded"
        
        # Check per-minute limit
        minute_key = f"global_{now.strftime('%Y%m%d%H%M')}"
        self.alert_counts[minute_key] = self.alert_counts.get(minute_key, 0) + 1
        if self.alert_counts[minute_key] > self.rate_limits["global"]["max_alerts_per_minute"]:
            return False, "Global per-minute alert limit exceeded"
        
        # Check per-agent limits if agent_id provided
        if agent_id:
            # Check agent cooldown
            if alert_type in self.agent_cooldowns[agent_id]:
                last_alert = self.agent_cooldowns[agent_id][alert_type]
                if (now - last_alert).total_seconds() < self.rate_limits["per_agent"]["cooldown_seconds"]:
                    return False, f"Agent {agent_id} cooldown active for {alert_type}"
            
            # Check agent hourly limit
            agent_key = f"agent_{agent_id}"
            self.alert_counts[agent_key] = self.alert_counts.get(agent_key, 0) + 1
            if self.alert_counts[agent_key] > self.rate_limits["per_agent"]["max_alerts_per_hour"]:
                return False, f"Agent {agent_id} hourly alert limit exceeded"
        
        # Check alert type cooldown
        type_key = f"type_{alert_type}"
        if type_key in self.alert_counts:
            last_type_alert = datetime.fromtimestamp(self.alert_counts[type_key])
            if (now - last_type_alert).total_seconds() < self.rate_limits["alert_type"]["cooldown_seconds"]:
                return False, f"Alert type {alert_type} cooldown active"
        
        return True, None
    
    def _update_cooldowns(self, alert_type: str, agent_id: Optional[str] = None):
        """Update cooldown timestamps after sending alert."""
        now = datetime.utcnow()
        
        if agent_id:
            self.agent_cooldowns[agent_id][alert_type] = now
        
        # Update alert type cooldown
        type_key = f"type_{alert_type}"
        self.alert_counts[type_key] = now.timestamp()
    
    async def send_alert(self, 
                        alert_type: str,
                        message: str,
                        severity: str = "warning",
                        details: Optional[Dict[str, Any]] = None) -> None:
        """Send an alert through configured channels.
        
        Args:
            alert_type: Type of alert (e.g. "DRIFT", "ERROR", "RECOVERY")
            message: Alert message
            severity: Alert severity (info, warning, error, critical)
            details: Additional alert details
        """
        try:
            # Extract agent_id from details if present
            agent_id = details.get("agent_id") if details else None
            
            # Check rate limits
            should_alert, limit_reason = self._check_rate_limits(alert_type, agent_id)
            if not should_alert:
                logger.debug(f"Alert rate limited: {limit_reason}")
                return
            
            # Add to aggregator
            aggregated = self.aggregator.add_alert(alert_type, agent_id, details)
            
            # Track event for digest
            self.digest.track_event(alert_type, details or {})
            
            # If we got an aggregated alert, send it
            if aggregated:
                await self._send_aggregated_alert(aggregated)
            else:
                # Send individual alert
                timestamp = datetime.utcnow().isoformat()
                alert = {
                    "timestamp": timestamp,
                    "type": alert_type,
                    "message": message,
                    "severity": severity,
                    "details": details or {}
                }
                
                # Log alert
                self._log_alert(alert)
                
                # Send to Discord if configured
                if self.discord_client and self.discord_client.is_ready():
                    await self._send_discord_alert(alert)
                
                # Log to console
                logger.warning(f"ALERT [{alert_type}] {message}")
            
            # Update cooldowns
            self._update_cooldowns(alert_type, agent_id)
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    async def _send_aggregated_alert(self, aggregated: Dict[str, Any]):
        """Send an aggregated alert."""
        try:
            # Log aggregated alert
            self._log_alert(aggregated)
            
            # Send to Discord if configured
            if self.discord_client and self.discord_client.is_ready():
                await self._send_discord_alert(aggregated)
            
            # Log to console
            logger.warning(f"AGGREGATED ALERT: {aggregated['message']}")
            
        except Exception as e:
            logger.error(f"Error sending aggregated alert: {e}")
    
    def _log_alert(self, alert: Dict[str, Any]):
        """Log alert to file."""
        try:
            with open(self.alert_log_path, 'r') as f:
                log_data = json.load(f)
            
            log_data["alerts"].append(alert)
            log_data["last_updated"] = datetime.utcnow().isoformat()
            
            # Keep last 1000 alerts
            log_data["alerts"] = log_data["alerts"][-1000:]
            
            with open(self.alert_log_path, 'w') as f:
                json.dump(log_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error logging alert: {e}")
    
    async def _send_discord_alert(self, alert: Dict[str, Any]):
        """Send alert to Discord channel."""
        try:
            channel = self.discord_client.get_channel(self.discord_channel_id)
            if not channel:
                return
            
            # Format message
            embed = discord.Embed(
                title=f"🚨 {alert['type']} Alert",
                description=alert['message'],
                color=self._get_severity_color(alert['severity']),
                timestamp=datetime.fromisoformat(alert['timestamp'])
            )
            
            # Add details if any
            if alert['details']:
                details_str = "\n".join(f"**{k}**: {v}" for k, v in alert['details'].items())
                embed.add_field(name="Details", value=details_str, inline=False)
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error sending Discord alert: {e}")
    
    def _get_severity_color(self, severity: str) -> int:
        """Get Discord embed color for severity."""
        colors = {
            "info": 0x3498db,      # Blue
            "warning": 0xf1c40f,   # Yellow
            "error": 0xe74c3c,     # Red
            "critical": 0x8b0000   # Dark Red
        }
        return colors.get(severity.lower(), 0x95a5a6)  # Default gray
    
    def get_aggregation_stats(self) -> Dict[str, Any]:
        """Get current aggregation statistics.
        
        Returns:
            Dict containing aggregation stats
        """
        stats = {
            "window_seconds": self.aggregator.window_seconds,
            "active_groups": {
                alert_type: {
                    "count": group["count"],
                    "agents": list(sorted(group["agents"])),
                    "duration": (datetime.utcnow() - group["first_seen"]).total_seconds() if group["first_seen"] else 0,
                    "recovery_count": group["recovery_count"]
                }
                for alert_type, group in self.aggregator.alert_groups.items()
            }
        }
        return stats

    def get_digest_stats(self) -> Dict[str, Any]:
        """Get current digest statistics.
        
        Returns:
            Dict containing digest stats
        """
        return {
            "active_agents": len(self.digest.stats["agent_activity"]),
            "events_today": {
                "drift": len(self.digest.stats["drift_events"]),
                "recovery": len(self.digest.stats["recovery_events"]),
                "error": len(self.digest.stats["error_events"]),
                "tasks": len(self.digest.stats["task_executions"])
            },
            "agent_stats": {
                agent_id: {
                    "tasks": stats["tasks_completed"],
                    "errors": stats["errors"],
                    "drift_count": stats["drift_count"],
                    "total_drift_time": stats["total_drift_time"]
                }
                for agent_id, stats in self.digest.stats["agent_activity"].items()
            }
        } 