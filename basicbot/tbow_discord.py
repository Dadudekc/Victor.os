"""
TBOW Tactics Discord Integration

This module provides Discord integration for the TBOW Tactics system:
1. Command processing (!tbow commands)
2. Trade plan formatting
3. Real-time status updates
4. Trade summary cards
5. Alert management with composite rules
6. Daily digest analytics
7. Historical backtesting with alert conditions
"""

import logging
import json
import asyncio
import uuid
import time
import csv
from collections import deque
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import discord
from discord.ext import commands
import os
import pytz

# --- signal handlers ---------------------------------------------------------
def macd_curl_down(data):    return data.macd_hist[-2] > 0 and data.macd_hist[-1] < 0
def macd_curl_up(data):      return data.macd_hist[-2] < 0 and data.macd_hist[-1] > 0
def rsi_below(thresh):       return lambda d: d.rsi[-1] < thresh
def rsi_above(thresh):       return lambda d: d.rsi[-1] > thresh
def price_below(level):      return lambda d: d.price[-1] < level
def price_above(level):      return lambda d: d.price[-1] > level
def vwap_above(data):        return data.price[-1] > data.vwap[-1]
def vwap_below(data):        return data.price[-1] < data.vwap[-1]

CONDITION_HANDLERS = {
    "MACD_curl_down": macd_curl_down,
    "MACD_curl_up":   macd_curl_up,
    "RSI_below_40":   rsi_below(40),
    "RSI_above_60":   rsi_above(60),
    "Price_below_500":price_below(500),
    "VWAP_above":     vwap_above,
    "VWAP_below":     vwap_below,
}

class PriceCache:
    """In-memory price cache for post-alert analysis."""
    
    def __init__(self, max_points: int = 120):
        """Initialize price cache."""
        self.cache: Dict[str, deque] = {}
        self.max_points = max_points
    
    def update(self, symbol: str, price: float, timestamp: datetime):
        """Update price cache for a symbol."""
        if symbol not in self.cache:
            self.cache[symbol] = deque(maxlen=self.max_points)
        self.cache[symbol].append((timestamp, price))
    
    def get_price_after(self, symbol: str, timestamp: datetime, minutes: int = 30) -> Optional[float]:
        """Get price after specified minutes from timestamp."""
        if symbol not in self.cache:
            return None
        
        target_time = timestamp + timedelta(minutes=minutes)
        for ts, price in self.cache[symbol]:
            if ts >= target_time:
                return price
        return None
    
    def get_price_range(self, symbol: str, start_time: datetime, end_time: datetime) -> List[float]:
        """Get all prices in a time range."""
        if symbol not in self.cache:
            return []
        
        return [price for ts, price in self.cache[symbol] if start_time <= ts <= end_time]

class AlertLogger:
    """Logs alert triggers for daily digest."""
    
    def __init__(self, log_file: str = "runtime/alert_log.csv"):
        """Initialize alert logger."""
        self.log_file = log_file
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """Ensure log file exists with headers."""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "alert_id", "symbol", "conditions", "fired_ts",
                    "price_at_fire", "price_after_30m"
                ])
    
    def log_alert(self, alert: AlertRule, price: float, price_after: Optional[float] = None):
        """Log an alert trigger."""
        with open(self.log_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                alert.alert_id,
                alert.symbol,
                " && ".join(alert.conditions),
                datetime.now().isoformat(),
                price,
                price_after
            ])
    
    def get_todays_alerts(self) -> List[Dict[str, Any]]:
        """Get all alerts triggered today."""
        today = datetime.now().date()
        alerts = []
        
        with open(self.log_file, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fired_ts = datetime.fromisoformat(row["fired_ts"])
                if fired_ts.date() == today:
                    alerts.append({
                        "alert_id": row["alert_id"],
                        "symbol": row["symbol"],
                        "conditions": row["conditions"],
                        "fired_ts": fired_ts,
                        "price_at_fire": float(row["price_at_fire"]),
                        "price_after_30m": float(row["price_after_30m"]) if row["price_after_30m"] else None
                    })
        
        return alerts

class DigestManager:
    """Manages daily digest generation and scheduling."""
    
    def __init__(self, bot: "TBOWDiscord", logger: Optional[logging.Logger] = None):
        """Initialize digest manager."""
        self.bot = bot
        self.logger = logger or logging.getLogger(__name__)
        self.alert_logger = AlertLogger()
        self.price_cache = PriceCache()
        self.digest_dir = "runtime/digests"
        os.makedirs(self.digest_dir, exist_ok=True)
        self.last_digest_date = None
    
    def _analyze_time_of_day(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze alert performance by time of day."""
        time_stats = {
            "morning": {"count": 0, "wins": 0, "avg_move": 0},
            "midday": {"count": 0, "wins": 0, "avg_move": 0},
            "afternoon": {"count": 0, "wins": 0, "avg_move": 0}
        }
        
        for alert in alerts:
            hour = alert["fired_ts"].hour
            if 9 <= hour < 11:
                period = "morning"
            elif 11 <= hour < 14:
                period = "midday"
            else:
                period = "afternoon"
            
            stats = time_stats[period]
            stats["count"] += 1
            
            if alert["price_after_30m"]:
                move = (alert["price_after_30m"] - alert["price_at_fire"]) / alert["price_at_fire"] * 100
                if move > 0:
                    stats["wins"] += 1
                stats["avg_move"] = (stats["avg_move"] * (stats["count"] - 1) + move) / stats["count"]
        
        return time_stats
    
    def _analyze_condition_effectiveness(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze effectiveness of different conditions."""
        condition_stats = {}
        
        for alert in alerts:
            conditions = alert["conditions"].split(" && ")
            for condition in conditions:
                if condition not in condition_stats:
                    condition_stats[condition] = {
                        "count": 0,
                        "wins": 0,
                        "avg_move": 0,
                        "max_move": 0,
                        "min_move": float("inf")
                    }
                
                stats = condition_stats[condition]
                stats["count"] += 1
                
                if alert["price_after_30m"]:
                    move = (alert["price_after_30m"] - alert["price_at_fire"]) / alert["price_at_fire"] * 100
                    if move > 0:
                        stats["wins"] += 1
                    stats["avg_move"] = (stats["avg_move"] * (stats["count"] - 1) + move) / stats["count"]
                    stats["max_move"] = max(stats["max_move"], move)
                    stats["min_move"] = min(stats["min_move"], move)
        
        return condition_stats
    
    def _analyze_market_context(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze alert performance in different market contexts."""
        context_stats = {
            "vix_ranges": {
                "low": {"count": 0, "wins": 0, "avg_move": 0},
                "medium": {"count": 0, "wins": 0, "avg_move": 0},
                "high": {"count": 0, "wins": 0, "avg_move": 0}
            },
            "volume_ranges": {
                "low": {"count": 0, "wins": 0, "avg_move": 0},
                "medium": {"count": 0, "wins": 0, "avg_move": 0},
                "high": {"count": 0, "wins": 0, "avg_move": 0}
            }
        }
        
        for alert in alerts:
            # Get market data for the alert time
            data = self.bot.tbow.strategy.fetch_historical_data(
                symbol=alert["symbol"],
                start_time=alert["fired_ts"] - timedelta(minutes=5),
                end_time=alert["fired_ts"]
            )
            
            if data is not None and not data.empty:
                vix = data["vix"].iloc[-1]
                volume = data["volume"].iloc[-1] / data["volume"].rolling(20).mean().iloc[-1]
                
                # Categorize VIX
                if vix < 15:
                    vix_range = "low"
                elif vix < 25:
                    vix_range = "medium"
                else:
                    vix_range = "high"
                
                # Categorize volume
                if volume < 0.8:
                    vol_range = "low"
                elif volume < 1.2:
                    vol_range = "medium"
                else:
                    vol_range = "high"
                
                # Update stats
                for range_type, range_name in [("vix_ranges", vix_range), ("volume_ranges", vol_range)]:
                    stats = context_stats[range_type][range_name]
                    stats["count"] += 1
                    
                    if alert["price_after_30m"]:
                        move = (alert["price_after_30m"] - alert["price_at_fire"]) / alert["price_at_fire"] * 100
                        if move > 0:
                            stats["wins"] += 1
                        stats["avg_move"] = (stats["avg_move"] * (stats["count"] - 1) + move) / stats["count"]
        
        return context_stats
    
    def _analyze_condition_correlations(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze correlations between different conditions."""
        condition_pairs = {}
        condition_moves = {}
        
        # First pass: collect moves for each condition
        for alert in alerts:
            if not alert["price_after_30m"]:
                continue
            
            move = (alert["price_after_30m"] - alert["price_at_fire"]) / alert["price_at_fire"] * 100
            conditions = alert["conditions"].split(" && ")
            
            for condition in conditions:
                if condition not in condition_moves:
                    condition_moves[condition] = []
                condition_moves[condition].append(move)
            
            # Track pairs
            for i, cond1 in enumerate(conditions):
                for cond2 in conditions[i+1:]:
                    pair = tuple(sorted([cond1, cond2]))
                    if pair not in condition_pairs:
                        condition_pairs[pair] = {
                            "count": 0,
                            "wins": 0,
                            "avg_move": 0,
                            "moves": []
                        }
                    
                    stats = condition_pairs[pair]
                    stats["count"] += 1
                    stats["moves"].append(move)
                    if move > 0:
                        stats["wins"] += 1
                    stats["avg_move"] = (stats["avg_move"] * (stats["count"] - 1) + move) / stats["count"]
        
        # Calculate correlations
        correlations = {}
        for pair, stats in condition_pairs.items():
            if len(stats["moves"]) < 2:
                continue
            
            # Calculate correlation coefficient
            moves1 = condition_moves[pair[0]]
            moves2 = condition_moves[pair[1]]
            
            # Ensure same length
            min_len = min(len(moves1), len(moves2))
            moves1 = moves1[:min_len]
            moves2 = moves2[:min_len]
            
            # Calculate correlation
            mean1 = sum(moves1) / len(moves1)
            mean2 = sum(moves2) / len(moves2)
            
            numerator = sum((m1 - mean1) * (m2 - mean2) for m1, m2 in zip(moves1, moves2))
            denominator1 = sum((m1 - mean1) ** 2 for m1 in moves1)
            denominator2 = sum((m2 - mean2) ** 2 for m2 in moves2)
            
            if denominator1 == 0 or denominator2 == 0:
                correlation = 0
            else:
                correlation = numerator / ((denominator1 * denominator2) ** 0.5)
            
            correlations[pair] = {
                "correlation": correlation,
                "count": stats["count"],
                "win_rate": (stats["wins"] / stats["count"] * 100) if stats["count"] > 0 else 0,
                "avg_move": stats["avg_move"]
            }
        
        return correlations
    
    def _analyze_price_action(self, prices: List[float], trigger_price: float) -> Dict[str, Any]:
        """Analyze price action after trigger."""
        if not prices:
            return {}
        
        # Calculate basic metrics
        max_price = max(prices)
        min_price = min(prices)
        final_price = prices[-1]
        
        # Calculate moves
        max_move = (max_price - trigger_price) / trigger_price * 100
        min_move = (min_price - trigger_price) / trigger_price * 100
        final_move = (final_price - trigger_price) / trigger_price * 100
        
        # Calculate volatility
        returns = [(p2 - p1) / p1 * 100 for p1, p2 in zip(prices[:-1], prices[1:])]
        volatility = (sum(r * r for r in returns) / len(returns)) ** 0.5 if returns else 0
        
        # Calculate drawdown
        peak = trigger_price
        max_drawdown = 0
        for price in prices:
            if price > peak:
                peak = price
            drawdown = (peak - price) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calculate time to max/min
        max_idx = prices.index(max_price)
        min_idx = prices.index(min_price)
        time_to_max = max_idx * 5  # 5-second intervals
        time_to_min = min_idx * 5
        
        return {
            "max_price": max_price,
            "min_price": min_price,
            "final_price": final_price,
            "max_move": max_move,
            "min_move": min_move,
            "final_move": final_move,
            "volatility": volatility,
            "max_drawdown": max_drawdown,
            "time_to_max": time_to_max,
            "time_to_min": time_to_min
        }
    
    def _analyze_market_impact(self, data: Any, trigger_time: datetime) -> Dict[str, Any]:
        """Analyze market impact and context."""
        if data is None or data.empty:
            return {}
        
        # Get pre and post trigger data
        pre_trigger = data[data.index < trigger_time]
        post_trigger = data[data.index >= trigger_time]
        
        if pre_trigger.empty or post_trigger.empty:
            return {}
        
        # Calculate volume profile
        pre_volume = pre_trigger["volume"].mean()
        post_volume = post_trigger["volume"].mean()
        volume_ratio = post_volume / pre_volume if pre_volume > 0 else 0
        
        # Calculate VWAP relationship
        vwap = data["vwap"].iloc[-1]
        price = data["close"].iloc[-1]
        vwap_distance = (price - vwap) / vwap * 100
        
        # Calculate momentum
        pre_momentum = (pre_trigger["close"].iloc[-1] - pre_trigger["close"].iloc[0]) / pre_trigger["close"].iloc[0] * 100
        post_momentum = (post_trigger["close"].iloc[-1] - post_trigger["close"].iloc[0]) / post_trigger["close"].iloc[0] * 100
        
        return {
            "volume_ratio": volume_ratio,
            "vwap_distance": vwap_distance,
            "pre_momentum": pre_momentum,
            "post_momentum": post_momentum,
            "vix": data["vix"].iloc[-1] if "vix" in data else None
        }
    
    async def generate_digest(self, channel_id: int) -> Optional[discord.Embed]:
        """Generate daily digest embed."""
        try:
            # Get today's alerts
            alerts = self.alert_logger.get_todays_alerts()
            if not alerts:
                return None
            
            # Generate analytics
            time_stats = self._analyze_time_of_day(alerts)
            condition_stats = self._analyze_condition_effectiveness(alerts)
            context_stats = self._analyze_market_context(alerts)
            correlations = self._analyze_condition_correlations(alerts)
            
            # Group by symbol
            symbol_stats = {}
            for alert in alerts:
                symbol = alert["symbol"]
                if symbol not in symbol_stats:
                    symbol_stats[symbol] = {
                        "fires": 0,
                        "first_price": float("inf"),
                        "last_price": 0,
                        "best_move": 0,
                        "wins": 0,
                        "total_moves": 0,
                        "avg_move": 0,
                        "max_drawdown": 0,
                        "conditions": set()
                    }
                
                stats = symbol_stats[symbol]
                stats["fires"] += 1
                price = alert["price_at_fire"]
                stats["first_price"] = min(stats["first_price"], price)
                stats["last_price"] = max(stats["last_price"], price)
                stats["conditions"].add(alert["conditions"])
                
                if alert["price_after_30m"]:
                    move = (alert["price_after_30m"] - price) / price * 100
                    stats["best_move"] = max(stats["best_move"], abs(move))
                    if move > 0:
                        stats["wins"] += 1
                    stats["total_moves"] += 1
                    stats["avg_move"] = (stats["avg_move"] * (stats["total_moves"] - 1) + move) / stats["total_moves"]
                    
                    # Calculate max drawdown
                    prices = self.price_cache.cache.get(symbol, [])
                    if prices:
                        trigger_idx = next((i for i, (ts, _) in enumerate(prices) if ts >= alert["fired_ts"]), None)
                        if trigger_idx is not None:
                            trigger_price = prices[trigger_idx][1]
                            min_price = min(p[1] for p in prices[trigger_idx:trigger_idx + 36])  # 30 min = 36 5s intervals
                            max_drawdown = (min_price - trigger_price) / trigger_price * 100
                            stats["max_drawdown"] = min(stats["max_drawdown"], max_drawdown)
            
            # Create embed
            embed = discord.Embed(
                title="TBOW Daily Alert Digest",
                description=f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                color=discord.Color.gold()
            )
            
            # Add summary stats
            total_alerts = sum(stats["fires"] for stats in symbol_stats.values())
            total_wins = sum(stats["wins"] for stats in symbol_stats.values())
            total_moves = sum(stats["total_moves"] for stats in symbol_stats.values())
            win_rate = (total_wins / total_moves * 100) if total_moves > 0 else 0
            
            embed.add_field(
                name="Summary",
                value=(
                    f"Total Alerts: {total_alerts}\n"
                    f"Win Rate: {win_rate:.1f}%\n"
                    f"Symbols: {len(symbol_stats)}"
                ),
                inline=False
            )
            
            # Add time of day analysis
            time_value = (
                "Morning (9-11):\n"
                f"Alerts: {time_stats['morning']['count']}\n"
                f"Win Rate: {(time_stats['morning']['wins'] / time_stats['morning']['count'] * 100) if time_stats['morning']['count'] > 0 else 0:.1f}%\n"
                f"Avg Move: {time_stats['morning']['avg_move']:.1f}%\n\n"
                "Midday (11-14):\n"
                f"Alerts: {time_stats['midday']['count']}\n"
                f"Win Rate: {(time_stats['midday']['wins'] / time_stats['midday']['count'] * 100) if time_stats['midday']['count'] > 0 else 0:.1f}%\n"
                f"Avg Move: {time_stats['midday']['avg_move']:.1f}%\n\n"
                "Afternoon (14-16):\n"
                f"Alerts: {time_stats['afternoon']['count']}\n"
                f"Win Rate: {(time_stats['afternoon']['wins'] / time_stats['afternoon']['count'] * 100) if time_stats['afternoon']['count'] > 0 else 0:.1f}%\n"
                f"Avg Move: {time_stats['afternoon']['avg_move']:.1f}%"
            )
            embed.add_field(name="Time of Day Analysis", value=time_value, inline=False)
            
            # Add condition effectiveness
            condition_value = ""
            for condition, stats in sorted(condition_stats.items(), key=lambda x: x[1]["count"], reverse=True):
                win_rate = (stats["wins"] / stats["count"] * 100) if stats["count"] > 0 else 0
                condition_value += (
                    f"{condition}:\n"
                    f"Count: {stats['count']}\n"
                    f"Win Rate: {win_rate:.1f}%\n"
                    f"Avg Move: {stats['avg_move']:.1f}%\n"
                    f"Range: {stats['min_move']:.1f}% to {stats['max_move']:.1f}%\n\n"
                )
            embed.add_field(name="Condition Effectiveness", value=condition_value, inline=False)
            
            # Add market context analysis
            context_value = (
                "VIX Context:\n"
                f"Low (<15): {context_stats['vix_ranges']['low']['count']} alerts, "
                f"{(context_stats['vix_ranges']['low']['wins'] / context_stats['vix_ranges']['low']['count'] * 100) if context_stats['vix_ranges']['low']['count'] > 0 else 0:.1f}% win rate\n"
                f"Medium (15-25): {context_stats['vix_ranges']['medium']['count']} alerts, "
                f"{(context_stats['vix_ranges']['medium']['wins'] / context_stats['vix_ranges']['medium']['count'] * 100) if context_stats['vix_ranges']['medium']['count'] > 0 else 0:.1f}% win rate\n"
                f"High (>25): {context_stats['vix_ranges']['high']['count']} alerts, "
                f"{(context_stats['vix_ranges']['high']['wins'] / context_stats['vix_ranges']['high']['count'] * 100) if context_stats['vix_ranges']['high']['count'] > 0 else 0:.1f}% win rate\n\n"
                "Volume Context:\n"
                f"Low (<0.8x): {context_stats['volume_ranges']['low']['count']} alerts, "
                f"{(context_stats['volume_ranges']['low']['wins'] / context_stats['volume_ranges']['low']['count'] * 100) if context_stats['volume_ranges']['low']['count'] > 0 else 0:.1f}% win rate\n"
                f"Medium (0.8-1.2x): {context_stats['volume_ranges']['medium']['count']} alerts, "
                f"{(context_stats['volume_ranges']['medium']['wins'] / context_stats['volume_ranges']['medium']['count'] * 100) if context_stats['volume_ranges']['medium']['count'] > 0 else 0:.1f}% win rate\n"
                f"High (>1.2x): {context_stats['volume_ranges']['high']['count']} alerts, "
                f"{(context_stats['volume_ranges']['high']['wins'] / context_stats['volume_ranges']['high']['count'] * 100) if context_stats['volume_ranges']['high']['count'] > 0 else 0:.1f}% win rate"
            )
            embed.add_field(name="Market Context Analysis", value=context_value, inline=False)
            
            # Add correlation analysis
            correlation_value = ""
            for (cond1, cond2), stats in sorted(correlations.items(), key=lambda x: abs(x[1]["correlation"]), reverse=True):
                correlation_value += (
                    f"{cond1} + {cond2}:\n"
                    f"Correlation: {stats['correlation']:.2f}\n"
                    f"Count: {stats['count']}\n"
                    f"Win Rate: {stats['win_rate']:.1f}%\n"
                    f"Avg Move: {stats['avg_move']:.1f}%\n\n"
                )
            embed.add_field(name="Condition Correlations", value=correlation_value, inline=False)
            
            # Add symbol stats
            for symbol, stats in sorted(symbol_stats.items(), key=lambda x: x[1]["fires"], reverse=True):
                win_rate = (stats["wins"] / stats["total_moves"] * 100) if stats["total_moves"] > 0 else 0
                price_change = (stats["last_price"] - stats["first_price"]) / stats["first_price"] * 100
                
                value = (
                    f"Fires: {stats['fires']}\n"
                    f"Price: ${stats['first_price']:.2f} → ${stats['last_price']:.2f} ({price_change:+.1f}%)\n"
                    f"Best Move: {stats['best_move']:.1f}%\n"
                    f"Avg Move: {stats['avg_move']:.1f}%\n"
                    f"Max DD: {abs(stats['max_drawdown']):.1f}%\n"
                    f"Win Rate: {win_rate:.1f}%\n"
                    f"Conditions: {', '.join(stats['conditions'])}"
                )
                
                # Highlight symbols with 3+ fires
                name = f"🔥 {symbol}" if stats["fires"] >= 3 else symbol
                embed.add_field(name=name, value=value, inline=False)
            
            # Save digest with analytics
            digest_file = os.path.join(self.digest_dir, f"{datetime.now().strftime('%Y-%m-%d')}.json")
            with open(digest_file, "w") as f:
                json.dump({
                    "embed": embed.to_dict(),
                    "analytics": {
                        "time_stats": time_stats,
                        "condition_stats": condition_stats,
                        "context_stats": context_stats,
                        "correlations": correlations
                    }
                }, f, indent=2)
            
            return embed
            
        except Exception as e:
            self.logger.error(f"Error generating digest: {e}")
            return None
    
    async def check_digest_schedule(self):
        """Check if it's time to generate digest."""
        try:
            now = datetime.now(pytz.timezone("US/Eastern"))
            
            # Check if we've already generated a digest today
            if self.last_digest_date == now.date():
                return
            
            # Check if it's 21:00 ET
            if now.hour == 21 and now.minute == 0:
                # Get digest role ID
                role_id = os.getenv("DIGEST_MENTION_ROLE_ID") or os.getenv("ALERT_MENTION_ROLE_ID")
                mention = f"<@&{role_id}>" if role_id else ""
                
                # Generate and send digest
                for channel_id in self.bot.alert_manager.get_alert_channels():
                    embed = await self.generate_digest(channel_id)
                    if embed:
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            await channel.send(
                                f"{mention} Daily Alert Digest",
                                embed=embed
                            )
                
                # Update last digest date
                self.last_digest_date = now.date()
        
        except Exception as e:
            self.logger.error(f"Error checking digest schedule: {e}")
    
    async def replay_alert(self, alert_id: str, channel_id: int) -> Optional[discord.Embed]:
        """Replay a specific alert with detailed analysis."""
        try:
            # Get alert details
            alert = next((a for a in self.alert_logger.get_todays_alerts() if a["alert_id"] == alert_id), None)
            if not alert:
                return None
            
            # Get price data
            prices = self.price_cache.get_price_range(
                alert["symbol"],
                alert["fired_ts"],
                alert["fired_ts"] + timedelta(minutes=30)
            )
            
            if not prices:
                return None
            
            # Analyze price action
            price_analysis = self._analyze_price_action(prices, alert["price_at_fire"])
            
            # Get market data
            data = self.bot.tbow.strategy.fetch_historical_data(
                symbol=alert["symbol"],
                start_time=alert["fired_ts"] - timedelta(minutes=5),
                end_time=alert["fired_ts"] + timedelta(minutes=30)
            )
            
            if data is None or data.empty:
                return None
            
            # Analyze market impact
            market_analysis = self._analyze_market_impact(data, alert["fired_ts"])
            
            # Create replay embed
            embed = discord.Embed(
                title=f"Alert Replay: {alert['symbol']}",
                description=f"Triggered at {alert['fired_ts'].strftime('%H:%M:%S')}",
                color=discord.Color.blue()
            )
            
            # Add price analysis
            embed.add_field(
                name="Price Analysis",
                value=(
                    f"Trigger: ${alert['price_at_fire']:.2f}\n"
                    f"High: ${price_analysis['max_price']:.2f} ({price_analysis['max_move']:+.1f}%)\n"
                    f"Low: ${price_analysis['min_price']:.2f} ({price_analysis['min_move']:+.1f}%)\n"
                    f"Final: ${price_analysis['final_price']:.2f} ({price_analysis['final_move']:+.1f}%)\n"
                    f"Volatility: {price_analysis['volatility']:.1f}%\n"
                    f"Max Drawdown: {price_analysis['max_drawdown']:.1f}%"
                ),
                inline=False
            )
            
            # Add timing analysis
            embed.add_field(
                name="Timing Analysis",
                value=(
                    f"Time to High: {price_analysis['time_to_max']}s\n"
                    f"Time to Low: {price_analysis['time_to_min']}s\n"
                    f"Total Duration: {len(prices) * 5}s"
                ),
                inline=True
            )
            
            # Add market context
            embed.add_field(
                name="Market Context",
                value=(
                    f"VIX: {market_analysis['vix']:.1f}\n"
                    f"Volume Ratio: {market_analysis['volume_ratio']:.1f}x\n"
                    f"VWAP Distance: {market_analysis['vwap_distance']:+.1f}%\n"
                    f"Pre-Momentum: {market_analysis['pre_momentum']:.1f}%\n"
                    f"Post-Momentum: {market_analysis['post_momentum']:.1f}%"
                ),
                inline=True
            )
            
            # Add conditions
            embed.add_field(
                name="Conditions",
                value=alert["conditions"],
                inline=True
            )
            
            return embed
            
        except Exception as e:
            self.logger.error(f"Error replaying alert: {e}")
            return None

@dataclass
class AlertRule:
    """Alert rule configuration."""
    symbol: str
    conditions: List[str]  # List of conditions to evaluate
    target: str  # Channel ID or user ID
    user_id: str
    created: datetime
    alert_id: str = None  # UUID for alert management
    cooldown_seconds: int = 300  # Default 5 minutes
    last_triggered: Optional[datetime] = None
    expires: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize alert ID if not provided."""
        if self.alert_id is None:
            self.alert_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        data = asdict(self)
        data["created"] = data["created"].isoformat()
        if data["last_triggered"]:
            data["last_triggered"] = data["last_triggered"].isoformat()
        if data["expires"]:
            data["expires"] = data["expires"].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlertRule":
        """Create from dictionary loaded from JSON."""
        data = data.copy()
        data["created"] = datetime.fromisoformat(data["created"])
        if data.get("last_triggered"):
            data["last_triggered"] = datetime.fromisoformat(data["last_triggered"])
        if data.get("expires"):
            data["expires"] = datetime.fromisoformat(data["expires"])
        return cls(**data)
    
    def can_trigger(self) -> bool:
        """Check if alert can trigger based on cooldown."""
        if not self.last_triggered:
            return True
        elapsed = (datetime.now() - self.last_triggered).total_seconds()
        return elapsed >= self.cooldown_seconds

class AlertManager:
    """Manages alert rules and triggers."""
    
    def __init__(self, bot: "TBOWDiscord", logger: Optional[logging.Logger] = None):
        """Initialize alert manager."""
        self.bot = bot
        self.logger = logger or logging.getLogger(__name__)
        self.rules: List[AlertRule] = []
        self.alerts_file = "runtime/alerts.json"
        self._load_rules()
    
    def _load_rules(self):
        """Load alert rules from JSON file."""
        try:
            if os.path.exists(self.alerts_file):
                with open(self.alerts_file, "r") as f:
                    data = json.load(f)
                    self.rules = [AlertRule.from_dict(rule) for rule in data]
                self.logger.info(f"Loaded {len(self.rules)} alert rules")
        except Exception as e:
            self.logger.error(f"Error loading alert rules: {e}")
    
    def _save_rules(self):
        """Save alert rules to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.alerts_file), exist_ok=True)
            with open(self.alerts_file, "w") as f:
                json.dump([rule.to_dict() for rule in self.rules], f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving alert rules: {e}")
    
    def add_rule(self, rule: AlertRule):
        """Add a new alert rule."""
        self.rules.append(rule)
        self._save_rules()
    
    def remove_rule(self, alert_id: str) -> bool:
        """Remove an alert rule by ID."""
        initial_count = len(self.rules)
        self.rules = [r for r in self.rules if r.alert_id != alert_id]
        if len(self.rules) < initial_count:
            self._save_rules()
            return True
        return False
    
    def modify_rule(self, alert_id: str, **kwargs) -> bool:
        """Modify an alert rule's properties."""
        for rule in self.rules:
            if rule.alert_id == alert_id:
                for key, value in kwargs.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                self._save_rules()
                return True
        return False
    
    def get_rule(self, alert_id: str) -> Optional[AlertRule]:
        """Get an alert rule by ID."""
        for rule in self.rules:
            if rule.alert_id == alert_id:
                return rule
        return None
    
    def get_user_rules(self, user_id: str) -> List[AlertRule]:
        """Get all rules for a user."""
        return [r for r in self.rules if r.user_id == user_id]
    
    def get_alert_channels(self) -> List[int]:
        """Get all channels with active alerts."""
        return list(set(int(r.target) for r in self.rules))
    
    def _all_conditions_met(self, rule: AlertRule, data: Any) -> bool:
        """Check if all conditions in a rule are met."""
        try:
            return all(CONDITION_HANDLERS[condition](data) for condition in rule.conditions)
        except Exception as e:
            self.logger.error(f"Error checking conditions for rule {rule.alert_id}: {e}")
            return False
    
    async def check_alerts(self):
        """Check for alert triggers."""
        try:
            # Remove expired rules
            now = datetime.now()
            self.rules = [r for r in self.rules if not r.expires or r.expires > now]
            
            # Group rules by symbol for efficient checking
            symbol_rules = {}
            for rule in self.rules:
                if rule.symbol not in symbol_rules:
                    symbol_rules[rule.symbol] = []
                symbol_rules[rule.symbol].append(rule)
            
            # Check each symbol
            for symbol, rules in symbol_rules.items():
                # Get market data
                data = self.bot.tbow.strategy.fetch_historical_data(symbol=symbol)
                if data is None or data.empty:
                    continue
                
                # Get analysis
                context = self.bot.tbow.scan_market_context(data)
                indicators = self.bot.tbow.analyze_indicators(data)
                
                # Update price cache
                latest = data.iloc[-1]
                self.bot.digest_manager.price_cache.update(
                    symbol,
                    latest["close"],
                    datetime.now()
                )
                
                # Check each rule
                for rule in rules:
                    if rule.can_trigger() and self._all_conditions_met(rule, data):
                        await self._trigger_alert(rule, data, context, indicators)
        
        except Exception as e:
            self.logger.error(f"Error checking alerts: {e}")
    
    async def _trigger_alert(
        self,
        rule: AlertRule,
        data: Any,
        context: Dict[str, Any],
        indicators: Dict[str, Any]
    ):
        """Trigger an alert."""
        try:
            # Create alert embed
            embed = discord.Embed(
                title=f"Alert: {rule.symbol}",
                description=f"Triggered at {datetime.now().strftime('%H:%M:%S')}",
                color=discord.Color.orange()
            )
            
            # Add price info
            latest = data.iloc[-1]
            price_change = (latest["close"] - data.iloc[-2]["close"]) / data.iloc[-2]["close"] * 100
            embed.add_field(
                name="Price",
                value=f"${latest['close']:.2f} ({price_change:+.2f}%)",
                inline=True
            )
            
            # Add conditions info
            conditions_text = "\n".join(f"✅ {condition}" for condition in rule.conditions)
            embed.add_field(
                name="Conditions Met",
                value=conditions_text,
                inline=False
            )
            
            # Send alert
            channel = self.bot.get_channel(int(rule.target))
            if channel:
                # Get role ID from config
                role_id = os.getenv("ALERT_MENTION_ROLE_ID")
                mention = f"<@&{role_id}>" if role_id else f"<@{rule.user_id}>"
                
                await channel.send(
                    f"{mention} Alert triggered!",
                    embed=embed
                )
            
            # Update last triggered time
            rule.last_triggered = datetime.now()
            self._save_rules()
            
            # Log alert for digest
            price_after = self.bot.digest_manager.price_cache.get_price_after(
                rule.symbol,
                datetime.now()
            )
            self.bot.digest_manager.alert_logger.log_alert(
                rule,
                latest["close"],
                price_after
            )
            
            # Remove one-time alerts
            if not rule.expires:
                self.remove_rule(rule.alert_id)
            
        except Exception as e:
            self.logger.error(f"Error triggering alert: {e}")

def parse_conditions(raw: str) -> List[str]:
    """Parse composite conditions from command input."""
    parts = [p.strip() for p in raw.split("&&")]
    invalid = [p for p in parts if p not in CONDITION_HANDLERS]
    if invalid:
        raise ValueError(f"Unknown condition(s): {', '.join(invalid)}")
    return parts

class TBOWDiscord(commands.Bot):
    """
    Discord bot for TBOW Tactics integration.
    
    Features:
    - Command processing
    - Trade plan formatting
    - Real-time updates
    - Summary cards
    - Alert management with composite rules
    - Daily digest analytics
    - Historical backtesting with alert conditions
    """
    
    def __init__(
        self,
        token: str,
        tbow_tactics: Any,  # TBOWTactics instance
        logger: Optional[logging.Logger] = None
    ):
        """Initialize Discord bot."""
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix="!",
            intents=intents
        )
        
        self.logger = logger or logging.getLogger(__name__)
        self.tbow = tbow_tactics
        self.token = token
        
        # Initialize managers
        self.alert_manager = AlertManager(self, logger)
        self.digest_manager = DigestManager(self, logger)
        
        # Register commands
        self.add_command(self.tbow_plan)
        self.add_command(self.tbow_status)
        self.add_command(self.tbow_stats)
        self.add_command(self.tbow_alert)
        self.add_command(self.tbow_alerts)
        self.add_command(self.tbow_digest)
        self.add_command(self.tbow_backtest)
    
    async def on_ready(self):
        """Handle bot ready event."""
        self.logger.info(f"TBOW Discord bot logged in as {self.user}")
        
        # Start alert checker
        self.alert_checker = asyncio.create_task(self._run_alert_checker())
    
    async def _run_alert_checker(self):
        """Run alert checker loop."""
        while True:
            try:
                await self.alert_manager.check_alerts()
                await self.digest_manager.check_digest_schedule()
                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception as e:
                self.logger.error(f"Error in alert checker: {e}")
                await asyncio.sleep(5)
    
    @commands.command(name="tbow")
    async def tbow_plan(self, ctx, action: str, *args):
        """
        Process TBOW Tactics commands.
        
        Commands:
        - !tbow plan <symbol> - Get trade plan
        - !tbow status <symbol> - Get current status
        - !tbow stats - Get performance stats
        - !tbow alert <symbol> <conditions> - Set alert
        - !tbow alert delete <id> - Delete alert
        - !tbow alert modify <id> <property> <value> - Modify alert
        - !tbow alerts - List alerts
        - !tbow digest today - Get today's alert digest
        - !tbow backtest <symbol> <conditions> [days] - Run backtest with alert conditions
        """
        try:
            if action.lower() == "backtest":
                if len(args) < 2:
                    await ctx.send(
                        "Please specify symbol and conditions:\n"
                        "!tbow backtest <symbol> <conditions> [days]\n"
                        "Example: !tbow backtest TSLA MACD_curl_up && RSI_below_40 30"
                    )
                    return
                
                symbol = args[0]
                try:
                    conditions = parse_conditions(" ".join(args[1:-1] if args[-1].isdigit() else args[1:]))
                except ValueError as e:
                    await ctx.send(str(e))
                    return
                
                # Get number of days (default: 30)
                days = int(args[-1]) if args[-1].isdigit() else 30
                
                # Run backtest
                await self._run_backtest(ctx, symbol, conditions, days)
            
            elif action.lower() == "plan":
                if not args:
                    await ctx.send("Please specify a symbol (e.g. !tbow plan TSLA)")
                    return
                
                symbol = args[0]
                # Get trade plan
                plan = await self._get_trade_plan(symbol)
                if plan:
                    await ctx.send(embed=plan)
                else:
                    await ctx.send(f"No trade plan available for {symbol}")
            
            elif action.lower() == "status":
                if not args:
                    await ctx.send("Please specify a symbol (e.g. !tbow status TSLA)")
                    return
                
                symbol = args[0]
                # Get current status
                status = await self._get_status(symbol)
                if status:
                    await ctx.send(embed=status)
                else:
                    await ctx.send(f"No status available for {symbol}")
            
            elif action.lower() == "stats":
                # Get performance stats
                stats = await self._get_stats()
                if stats:
                    await ctx.send(embed=stats)
                else:
                    await ctx.send("No performance stats available")
            
            elif action.lower() == "alert":
                if not args:
                    await ctx.send(
                        "Please specify alert action:\n"
                        "!tbow alert <symbol> <conditions> - Set alert\n"
                        "!tbow alert delete <id> - Delete alert\n"
                        "!tbow alert modify <id> <property> <value> - Modify alert"
                    )
                    return
                
                if args[0].lower() == "delete":
                    if len(args) != 2:
                        await ctx.send("Please specify alert ID to delete")
                        return
                    
                    alert_id = args[1]
                    if self.alert_manager.remove_rule(alert_id):
                        await ctx.send(f"Alert {alert_id} deleted")
                    else:
                        await ctx.send("Alert not found")
                
                elif args[0].lower() == "modify":
                    if len(args) != 4:
                        await ctx.send(
                            "Please specify alert ID, property, and value\n"
                            "Example: !tbow alert modify <id> cooldown 600"
                        )
                        return
                    
                    alert_id, property, value = args[1:]
                    try:
                        value = int(value)  # Convert to int for numeric properties
                    except ValueError:
                        pass
                    
                    if self.alert_manager.modify_rule(alert_id, **{property: value}):
                        await ctx.send(f"Alert {alert_id} modified")
                    else:
                        await ctx.send("Alert not found")
                
                else:
                    # Parse new alert
                    if len(args) < 2:
                        await ctx.send(
                            "Invalid alert format. Use: !tbow alert <symbol> <conditions>\n"
                            "Example: !tbow alert TSLA MACD_curl_up && RSI_below_40"
                        )
                        return
                    
                    symbol = args[0]
                    try:
                        conditions = parse_conditions(" ".join(args[1:]))
                    except ValueError as e:
                        await ctx.send(str(e))
                        return
                    
                    # Add alert rule
                    alert = AlertRule(
                        symbol=symbol,
                        conditions=conditions,
                        target=str(ctx.channel.id),
                        user_id=str(ctx.author.id),
                        created=datetime.now()
                    )
                    
                    self.alert_manager.add_rule(alert)
                    await ctx.send(
                        f"Alert set for {symbol}\n"
                        f"Conditions: {' && '.join(conditions)}\n"
                        f"Alert ID: {alert.alert_id}"
                    )
            
            elif action.lower() == "alerts":
                # List user's alerts
                rules = self.alert_manager.get_user_rules(str(ctx.author.id))
                if not rules:
                    await ctx.send("You have no active alerts")
                    return
                
                # Create alert list embed
                embed = discord.Embed(
                    title="Your Alerts",
                    description="Active alert rules",
                    color=discord.Color.blue()
                )
                
                for rule in rules:
                    cooldown = f" (Cooldown: {rule.cooldown_seconds}s)" if rule.cooldown_seconds != 300 else ""
                    embed.add_field(
                        name=f"{rule.symbol}",
                        value=(
                            f"ID: {rule.alert_id}\n"
                            f"Conditions: {' && '.join(rule.conditions)}\n"
                            f"Created: {rule.created.strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"Last Triggered: {rule.last_triggered.strftime('%H:%M:%S') if rule.last_triggered else 'Never'}{cooldown}"
                        ),
                        inline=False
                    )
                
                await ctx.send(embed=embed)
            
            elif action.lower() == "digest":
                if not args or args[0].lower() != "today":
                    await ctx.send("Please use: !tbow digest today")
                    return
                
                # Generate digest
                embed = await self.digest_manager.generate_digest(ctx.channel.id)
                if embed:
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("No alerts triggered today")
            
            else:
                await ctx.send(
                    "Unknown command. Available commands:\n"
                    "!tbow plan <symbol> - Get trade plan\n"
                    "!tbow status <symbol> - Get current status\n"
                    "!tbow stats - Get performance stats\n"
                    "!tbow alert <symbol> <conditions> - Set alert\n"
                    "!tbow alert delete <id> - Delete alert\n"
                    "!tbow alert modify <id> <property> <value> - Modify alert\n"
                    "!tbow alerts - List alerts\n"
                    "!tbow digest today - Get today's alert digest\n"
                    "!tbow backtest <symbol> <conditions> [days] - Run backtest with alert conditions"
                )
        
        except Exception as e:
            self.logger.error(f"Error processing command: {e}")
            await ctx.send("Error processing command. Please try again.")
    
    async def _get_trade_plan(self, symbol: str) -> Optional[discord.Embed]:
        """Generate trade plan embed."""
        try:
            # Get market data
            data = self.tbow.strategy.fetch_historical_data(symbol=symbol)
            if data is None or data.empty:
                return None
            
            # Get analysis
            context = self.tbow.scan_market_context(data)
            indicators = self.tbow.analyze_indicators(data)
            bias = self.tbow.generate_bias(context, indicators)
            checklist = self.tbow.check_compliance(context, indicators)
            
            # Create embed
            embed = discord.Embed(
                title=f"TBOW Trade Plan: {symbol}",
                description=f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                color=discord.Color.green() if bias["bias"] == "BULLISH" else discord.Color.red()
            )
            
            # Add bias section
            embed.add_field(
                name="Bias",
                value=f"**{bias['bias']}** ({bias['confidence']})",
                inline=False
            )
            
            # Add setup criteria
            setup_criteria = []
            for item, status in checklist.items():
                setup_criteria.append(f"{'✅' if status['status'] else '❌'} {item}")
            
            embed.add_field(
                name="Setup Criteria",
                value="\n".join(setup_criteria),
                inline=False
            )
            
            # Add entry/exit levels
            if "entry" in bias and "stop" in bias and "target" in bias:
                embed.add_field(
                    name="Levels",
                    value=(
                        f"Entry: ${bias['entry']:.2f}\n"
                        f"Stop: ${bias['stop']:.2f}\n"
                        f"Target: ${bias['target']:.2f}"
                    ),
                    inline=True
                )
            
            # Add risk metrics
            if "risk_reward" in bias:
                embed.add_field(
                    name="Risk/Reward",
                    value=f"{bias['risk_reward']:.2f}:1",
                    inline=True
                )
            
            # Add market context
            embed.add_field(
                name="Market Context",
                value=(
                    f"VIX: {context.get('vix', 'N/A')}\n"
                    f"Gap: {context['gaps'].get('direction', 'None').upper()}\n"
                    f"Volume: {context.get('volume_ratio', 0):.1f}x"
                ),
                inline=False
            )
            
            return embed
            
        except Exception as e:
            self.logger.error(f"Error generating trade plan: {e}")
            return None
    
    async def _get_status(self, symbol: str) -> Optional[discord.Embed]:
        """Generate status embed."""
        try:
            # Get current data
            data = self.tbow.strategy.fetch_historical_data(symbol=symbol)
            if data is None or data.empty:
                return None
            
            latest = data.iloc[-1]
            
            # Create embed
            embed = discord.Embed(
                title=f"TBOW Status: {symbol}",
                description=f"Updated at {datetime.now().strftime('%H:%M:%S')}",
                color=discord.Color.blue()
            )
            
            # Add price info
            price_change = (latest["close"] - data.iloc[-2]["close"]) / data.iloc[-2]["close"] * 100
            embed.add_field(
                name="Price",
                value=f"${latest['close']:.2f} ({price_change:+.2f}%)",
                inline=True
            )
            
            # Add volume info
            volume_ratio = latest["volume"] / data["volume"].rolling(20).mean().iloc[-1]
            embed.add_field(
                name="Volume",
                value=f"{volume_ratio:.1f}x average",
                inline=True
            )
            
            # Add indicator status
            indicators = self.tbow.analyze_indicators(data)
            
            macd = indicators["macd"]
            embed.add_field(
                name="MACD",
                value=f"{macd['trend'].upper()} ({'Curl' if macd.get('curl', False) else 'No Curl'})",
                inline=True
            )
            
            rsi = indicators["rsi"]
            embed.add_field(
                name="RSI",
                value=f"{rsi['value']:.1f} ({rsi['trend'].upper()})",
                inline=True
            )
            
            vwap = indicators["vwap"]
            embed.add_field(
                name="VWAP",
                value=f"Price {vwap['position'].upper()} VWAP",
                inline=True
            )
            
            return embed
            
        except Exception as e:
            self.logger.error(f"Error generating status: {e}")
            return None
    
    async def _get_stats(self) -> Optional[discord.Embed]:
        """Generate performance stats embed."""
        try:
            # Get trade history
            trades = self.tbow.get_trade_history()
            if not trades:
                return None
            
            # Calculate stats
            total_trades = len(trades)
            wins = sum(1 for t in trades if t.get("result") == "win")
            win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
            
            # Calculate average R:R
            rr_ratios = [t.get("rr_ratio", 0) for t in trades if "rr_ratio" in t]
            avg_rr = sum(rr_ratios) / len(rr_ratios) if rr_ratios else 0
            
            # Create embed
            embed = discord.Embed(
                title="TBOW Performance Stats",
                description=f"Last {total_trades} trades",
                color=discord.Color.gold()
            )
            
            # Add win rate
            embed.add_field(
                name="Win Rate",
                value=f"{win_rate:.1f}%",
                inline=True
            )
            
            # Add R:R
            embed.add_field(
                name="Avg R:R",
                value=f"{avg_rr:.2f}:1",
                inline=True
            )
            
            # Add checklist compliance
            compliance_scores = [t.get("checklist_score", 0) for t in trades if "checklist_score" in t]
            avg_compliance = sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0
            
            embed.add_field(
                name="Checklist Compliance",
                value=f"{avg_compliance:.1f}/6",
                inline=True
            )
            
            # Add emotion profile
            emotions = {
                "Hesitant": 0,
                "Confident": 0,
                "Rushed": 0,
                "Patient": 0
            }
            
            for trade in trades:
                if "emotions" in trade:
                    for emotion in trade["emotions"]:
                        if emotion in emotions:
                            emotions[emotion] += 1
            
            emotion_text = "\n".join(
                f"{emotion}: {count}" for emotion, count in emotions.items()
            )
            
            embed.add_field(
                name="Emotion Profile",
                value=emotion_text,
                inline=False
            )
            
            return embed
            
        except Exception as e:
            self.logger.error(f"Error generating stats: {e}")
            return None
    
    def run_bot(self):
        """Run the Discord bot."""
        try:
            self.run(self.token)
        except Exception as e:
            self.logger.error(f"Error running Discord bot: {e}")
    
    async def send_trade_alert(self, channel_id: int, trade_data: Dict[str, Any]):
        """Send trade alert to specified channel."""
        try:
            channel = self.get_channel(channel_id)
            if channel:
                embed = await self._get_trade_plan(trade_data["symbol"])
                if embed:
                    await channel.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Error sending trade alert: {e}")
    
    async def send_status_update(self, channel_id: int, symbol: str):
        """Send status update to specified channel."""
        try:
            channel = self.get_channel(channel_id)
            if channel:
                embed = await self._get_status(symbol)
                if embed:
                    await channel.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Error sending status update: {e}")
    
    async def _run_backtest(self, ctx, symbol: str, conditions: List[str], days: int):
        """Run backtest with alert conditions."""
        try:
            # Create loading message
            loading_msg = await ctx.send("🔄 Running backtest... This may take a few minutes.")
            
            # Initialize strategy
            strategy = self.tbow.strategy
            
            # Initialize backtester with alert conditions
            backtester = Backtester(
                strategy=strategy,
                logger=self.logger,
                symbol=symbol,
                timeframe="5Min",
                alert_conditions=conditions
            )
            
            # Fetch historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            data = self.tbow.strategy.fetch_historical_data(
                symbol=symbol,
                start_time=start_date,
                end_time=end_date
            )
            
            if data is None or data.empty:
                await loading_msg.edit(content="❌ No historical data available for backtest.")
                return
            
            # Run backtest
            results = backtester.run_backtest(data)
            
            # Generate plot
            plot_file = f"runtime/backtest_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            backtester.plot_results(results, plot_file)
            
            # Create results embed
            embed = discord.Embed(
                title=f"Backtest Results: {symbol}",
                description=f"Period: {days} days\nConditions: {' && '.join(conditions)}",
                color=discord.Color.blue()
            )
            
            # Add basic metrics
            metrics = backtester.metrics
            embed.add_field(
                name="Strategy Performance",
                value=(
                    f"Total Trades: {metrics.get('total_trades', 0)}\n"
                    f"Win Rate: {metrics.get('win_rate', 0):.1f}%\n"
                    f"Profit Factor: {metrics.get('profit_factor', 0):.2f}\n"
                    f"Max Drawdown: {metrics.get('max_drawdown', 0):.1f}%\n"
                    f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}\n"
                    f"Sortino Ratio: {metrics.get('sortino_ratio', 0):.2f}"
                ),
                inline=False
            )
            
            # Add alert metrics
            if "alert_metrics" in metrics:
                alert_metrics = metrics["alert_metrics"]
                embed.add_field(
                    name="Alert Performance",
                    value=f"Total Alerts: {alert_metrics['total_alerts']}",
                    inline=False
                )
                
                # Add condition stats
                condition_stats = alert_metrics["condition_stats"]
                for condition, stats in condition_stats.items():
                    embed.add_field(
                        name=condition,
                        value=(
                            f"Triggers: {stats['triggers']}\n"
                            f"Win Rate: {stats['win_rate']:.1f}%\n"
                            f"Avg Move: {stats['avg_move']:.1f}%\n"
                            f"Max Move: {stats['max_move']:.1f}%\n"
                            f"Min Move: {stats['min_move']:.1f}%"
                        ),
                        inline=True
                    )
                
                # Add correlations
                correlations = alert_metrics["correlations"]
                if correlations:
                    corr_text = ""
                    for (cond1, cond2), stats in sorted(
                        correlations.items(),
                        key=lambda x: abs(x[1]["correlation"]),
                        reverse=True
                    )[:5]:  # Show top 5 correlations
                        corr_text += (
                            f"{cond1} + {cond2}:\n"
                            f"Correlation: {stats['correlation']:.2f}\n"
                            f"Count: {stats['count']}\n\n"
                        )
                    
                    if corr_text:
                        embed.add_field(
                            name="Top Condition Correlations",
                            value=corr_text,
                            inline=False
                        )
            
            # Send results
            await loading_msg.edit(content=None, embed=embed)
            
            # Send plot
            with open(plot_file, "rb") as f:
                plot = discord.File(f, "backtest_plot.png")
                await ctx.send(file=plot)
            
            # Clean up
            try:
                os.remove(plot_file)
            except:
                pass
            
        except Exception as e:
            self.logger.error(f"Error running backtest: {e}")
            await loading_msg.edit(content=f"❌ Error running backtest: {str(e)}") 