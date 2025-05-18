"""
Discord notification handler for social media leads and episodes.

This module sends notifications to Discord when:
- New leads are discovered
- Episodes are created
- Tasks are generated

It uses webhook URLs to post directly to channels.
"""

import json
import logging
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dreamos.integrations.social.discord_notifier")

# Default webhook URL - override with environment variable
DEFAULT_WEBHOOK_URL = None  # Set via DISCORD_WEBHOOK_URL environment variable

class DiscordNotifier:
    """Handles sending notifications to Discord about social leads and episodes."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize the Discord notifier.
        
        Args:
            webhook_url: The Discord webhook URL (optional, will use env var if not provided)
        """
        import os
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL") or DEFAULT_WEBHOOK_URL
        
    def is_configured(self) -> bool:
        """Check if the Discord notifier is properly configured."""
        return self.webhook_url is not None
        
    def notify_new_leads(self, platform: str, leads: List[Dict[str, Any]], 
                       keywords: List[str]) -> bool:
        """
        Send a notification about new leads discovered.
        
        Args:
            platform: The platform where leads were found
            leads: List of lead dictionaries
            keywords: Keywords used to find leads
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Discord notification skipped: webhook URL not configured")
            return False
            
        if not leads:
            return True  # Nothing to notify about
            
        # Create message
        message = {
            "content": f"🔍 Found {len(leads)} leads on {platform.capitalize()}",
            "embeds": [{
                "title": f"New {platform.capitalize()} Leads",
                "description": f"Found {len(leads)} leads matching: {', '.join(keywords)}",
                "color": 5814783,  # Blue
                "fields": [
                    {
                        "name": "Platform",
                        "value": platform.capitalize(),
                        "inline": True
                    },
                    {
                        "name": "Keywords",
                        "value": ', '.join(keywords),
                        "inline": True
                    },
                    {
                        "name": "Count",
                        "value": str(len(leads)),
                        "inline": True
                    }
                ],
                "footer": {
                    "text": f"Dream.OS Social Scout • {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                }
            }]
        }
        
        # Add sample leads (up to 3)
        for i, lead in enumerate(leads[:3]):
            message["embeds"][0]["fields"].append({
                "name": f"Lead #{i+1}: {lead['username']}",
                "value": f"{lead['match'][:100]}...\n[View Original]({lead['link']})"
            })
            
        return self._send_discord_message(message)
        
    def notify_new_episode(self, episode_id: str, episode_name: str, platform: str,
                        keywords: List[str], task_count: int, captain: str) -> bool:
        """
        Send a notification about a new episode created.
        
        Args:
            episode_id: The ID of the episode
            episode_name: The name of the episode
            platform: The platform where leads were found
            keywords: Keywords used to find leads
            task_count: Number of tasks in the episode
            captain: Captain agent assigned to the episode
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Discord notification skipped: webhook URL not configured")
            return False
            
        # Create message
        message = {
            "content": f"📑 New lead episode created: \"{episode_name}\"",
            "embeds": [{
                "title": episode_name,
                "description": f"A new leads episode has been created on {platform.capitalize()} with {task_count} tasks.",
                "color": 8311585,  # Purple
                "fields": [
                    {
                        "name": "Episode ID",
                        "value": episode_id,
                        "inline": True
                    },
                    {
                        "name": "Platform",
                        "value": platform.capitalize(),
                        "inline": True
                    },
                    {
                        "name": "Keywords",
                        "value": ', '.join(keywords),
                        "inline": True
                    },
                    {
                        "name": "Tasks",
                        "value": str(task_count),
                        "inline": True
                    },
                    {
                        "name": "Captain",
                        "value": captain,
                        "inline": True
                    }
                ],
                "footer": {
                    "text": f"Dream.OS Social Lead Generator • {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                }
            }]
        }
        
        return self._send_discord_message(message)
        
    def notify_task_completion(self, task_id: str, lead_data: Dict[str, Any],
                            agent: str, response_summary: str) -> bool:
        """
        Send a notification about a completed lead task.
        
        Args:
            task_id: The ID of the task
            lead_data: The original lead data
            agent: The agent who completed the task
            response_summary: A summary of the agent's response
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Discord notification skipped: webhook URL not configured")
            return False
            
        # Create message
        message = {
            "content": f"✅ Task completed by {agent}: {task_id}",
            "embeds": [{
                "title": f"Lead Task Completed",
                "description": response_summary[:1500] + ("..." if len(response_summary) > 1500 else ""),
                "color": 5763719,  # Green
                "fields": [
                    {
                        "name": "Task ID",
                        "value": task_id,
                        "inline": True
                    },
                    {
                        "name": "Agent",
                        "value": agent,
                        "inline": True
                    },
                    {
                        "name": "Platform",
                        "value": lead_data.get("platform", "unknown").capitalize(),
                        "inline": True
                    },
                    {
                        "name": "Original Lead",
                        "value": f"{lead_data.get('match', '')[:100]}...\n[View Original]({lead_data.get('link', '#')})",
                    }
                ],
                "footer": {
                    "text": f"Dream.OS Social Lead Response • {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                }
            }]
        }
        
        return self._send_discord_message(message)
        
    def _send_discord_message(self, message: Dict[str, Any]) -> bool:
        """
        Send a message to Discord via webhook.
        
        Args:
            message: The message payload to send
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 204:
                logger.info("Discord notification sent successfully")
                return True
            else:
                logger.error(f"Discord notification failed: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")
            return False


# Singleton instance
_discord_notifier = None

def get_discord_notifier(webhook_url: Optional[str] = None) -> DiscordNotifier:
    """
    Get the Discord notifier instance.
    
    Args:
        webhook_url: Optional webhook URL to use
        
    Returns:
        DiscordNotifier instance
    """
    global _discord_notifier
    if _discord_notifier is None:
        _discord_notifier = DiscordNotifier(webhook_url)
    elif webhook_url is not None:
        _discord_notifier.webhook_url = webhook_url
    return _discord_notifier 