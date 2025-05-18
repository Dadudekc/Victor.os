"""
Dream.OS Lead Episode Generator - Turn social media leads into agent episodes

This module converts social media leads captured by the SocialScout into
structured agent episodes and tasks. It allows the agent swarm to respond
to opportunities discovered on social platforms.

The module can:
1. Generate complete episodes from lead collections
2. Create targeted tasks for specific agents
3. Assign research goals to the swarm
4. Prioritize leads based on relevance and timing

Typical usage:
```
from dreamos.integrations.social.lead_episode_generator import LeadEpisodeGenerator

# Create new episode from Twitter leads about React jobs
generator = LeadEpisodeGenerator()
generator.create_episode_from_leads(
    platform="twitter",
    keywords=["react", "hiring"],
    episode_name="React Job Opportunities",
    captain_agent="Agent-5"
)
```
"""

import os
import json
import logging
import yaml
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import uuid

from dreamos.integrations.social.social_scout import SocialScout

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dreamos.integrations.social.lead_episode_generator")

# Constants
RUNTIME_DIR = Path("runtime")
EPISODE_DIR = Path("episodes")
TASK_DIR = RUNTIME_DIR / "tasks"
AGENT_MAILBOX_DIR = RUNTIME_DIR / "agent_mailboxes"

# Ensure directories exist
TASK_DIR.mkdir(parents=True, exist_ok=True)
EPISODE_DIR.mkdir(parents=True, exist_ok=True)

class LeadEpisodeGenerator:
    """
    Generates episodes and tasks for agents based on social media leads.
    """
    
    def __init__(self):
        """
        Initialize the lead episode generator.
        """
        pass
        
    def create_episode_from_leads(self, platform: str, keywords: List[str],
                               episode_name: str, captain_agent: str = "Agent-5",
                               max_leads: int = 10) -> str:
        """
        Create a complete episode from social media leads.
        
        Args:
            platform: Social platform to search ("twitter", "linkedin", etc.)
            keywords: Keywords to search for
            episode_name: Name of the episode to create
            captain_agent: Agent assigned as captain for the episode
            max_leads: Maximum number of leads to include
            
        Returns:
            Path to the created episode file
        """
        # Generate episode ID
        timestamp = datetime.now().strftime("%Y%m%d")
        episode_id = f"episode-lead-{platform}-{timestamp}"
        
        # Collect leads using SocialScout
        with SocialScout(platform=platform) as scout:
            leads = scout.find_leads(keywords=keywords, max_results=max_leads)
            
        if not leads:
            logger.warning(f"No leads found on {platform} for keywords: {keywords}")
            return ""

        # Create episode structure
        episode = {
            "episode_id": episode_id,
            "title": episode_name,
            "description": f"Respond to {platform} leads related to: {', '.join(keywords)}",
            "captain": captain_agent,
            "task_breakdown": "distributed",
            "context": {
                "platform": platform,
                "keywords": keywords,
                "created_at": datetime.now().isoformat(),
                "lead_count": len(leads)
            },
            "tasks": self._generate_tasks_from_leads(leads, platform, episode_id)
        }
        
        # Write episode file
        episode_path = EPISODE_DIR / f"{episode_id}.yaml"
        with open(episode_path, 'w') as f:
            yaml.dump(episode, f, default_flow_style=False)
            
        logger.info(f"Created lead episode at {episode_path}")
        
        # Notify captain agent
        self._notify_captain(captain_agent, episode_id, episode_name, platform, keywords, len(leads))
        
        return str(episode_path)
    
    def _generate_tasks_from_leads(self, leads: List[Dict[str, Any]], 
                               platform: str, episode_id: str) -> List[Dict[str, Any]]:
        """
        Generate tasks from lead data.
        
        Args:
            leads: List of lead dictionaries
            platform: Social platform name
            episode_id: ID of the parent episode
            
        Returns:
            List of task dictionaries for the episode
        """
        tasks = []
        
        # Create research task
        research_task = {
            "task_id": f"RESEARCH-{platform.upper()}-{uuid.uuid4().hex[:8]}",
            "name": f"Research context for {platform} leads",
            "description": f"Analyze {len(leads)} leads from {platform} to identify common themes, opportunities, and action strategies.",
            "priority": "HIGH",
            "assigned_to": None,  # Will be dynamically assigned
            "type": "RESEARCH",
            "dependencies": [],
            "data": {
                "platform": platform,
                "lead_count": len(leads),
                "episode_id": episode_id
            }
        }
        tasks.append(research_task)
        
        # Create individual lead tasks
        for i, lead in enumerate(leads):
            lead_task = {
                "task_id": f"LEAD-{platform.upper()}-{lead['id'][:8]}",
                "name": f"Analyze {platform} lead: {lead['query']}",
                "description": f"Analyze and craft response to lead from {lead['username']}: '{lead['match'][:100]}...'",
                "priority": "MEDIUM",
                "assigned_to": None,  # Will be dynamically assigned
                "type": "LEAD_ANALYSIS",
                "dependencies": [research_task["task_id"]],
                "data": {
                    "lead_data": lead,
                    "platform": platform,
                    "episode_id": episode_id
                }
            }
            tasks.append(lead_task)
            
        # Create summary task
        summary_task = {
            "task_id": f"SUMMARY-{platform.upper()}-{uuid.uuid4().hex[:8]}",
            "name": f"Summarize {platform} lead findings",
            "description": f"Create a comprehensive summary of all lead analyses and propose concrete next steps.",
            "priority": "HIGH",
            "assigned_to": None,  # Will be dynamically assigned
            "type": "SUMMARY",
            "dependencies": [task["task_id"] for task in tasks if task["type"] == "LEAD_ANALYSIS"],
            "data": {
                "platform": platform,
                "lead_count": len(leads),
                "episode_id": episode_id
            }
        }
        tasks.append(summary_task)
        
        return tasks
    
    def _notify_captain(self, captain_agent: str, episode_id: str, 
                    episode_name: str, platform: str, 
                    keywords: List[str], lead_count: int) -> None:
        """
        Notify the captain agent about the new lead episode.
        
        Args:
            captain_agent: Agent to notify (e.g., "Agent-5")
            episode_id: ID of the created episode
            episode_name: Name of the episode
            platform: Social platform
            keywords: Keywords used for search
            lead_count: Number of leads found
        """
        # Create notification message
        notification = {
            "type": "SOCIAL_LEADS_EPISODE",
            "timestamp": datetime.now().isoformat(),
            "from": "LeadEpisodeGenerator",
            "to": captain_agent,
            "subject": f"New {platform} Lead Episode: {episode_name}",
            "content": {
                "episode_id": episode_id,
                "episode_name": episode_name,
                "platform": platform,
                "keywords": keywords,
                "lead_count": lead_count,
                "created_at": datetime.now().isoformat(),
                "instructions": "Please review this lead-based episode and coordinate agent task assignments."
            }
        }
        
        # Write notification to captain's inbox
        inbox_path = AGENT_MAILBOX_DIR / captain_agent / "inbox"
        inbox_path.mkdir(parents=True, exist_ok=True)
        
        message_path = inbox_path / f"social_leads_episode_{episode_id}.json"
        with open(message_path, 'w') as f:
            json.dump(notification, f, indent=2)
            
        logger.info(f"Notified {captain_agent} about new lead episode: {episode_id}")
        
    def create_task_from_lead(self, lead: Dict[str, Any], 
                          assign_to: Optional[str] = None) -> str:
        """
        Create a single task from a lead and optionally assign to a specific agent.
        
        Args:
            lead: Lead dictionary
            assign_to: Optional agent to assign task to
            
        Returns:
            Task ID of the created task
        """
        # Create task ID from lead
        task_id = f"LEAD-{lead['platform'].upper()}-{lead['id'][:8]}"
        
        # Create task data
        task = {
            "task_id": task_id,
            "name": f"Analyze lead from {lead['platform']}: {lead['query']}",
            "description": f"Analyze and respond to potential lead: '{lead['match'][:100]}...' from {lead['username']} on {lead['platform']}.",
            "priority": "MEDIUM",
            "status": "PENDING",
            "assigned_to": assign_to,  # May be None
            "task_type": "LEAD_ANALYSIS",
            "created_by": "LeadEpisodeGenerator",
            "created_at": datetime.now().isoformat(),
            "tags": ["lead", lead['platform'], "social_scout", lead['query'].replace(" ", "_")],
            "dependencies": [],
            "lead_data": lead,
            "history": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "agent": "LeadEpisodeGenerator",
                    "action": "CREATED",
                    "details": f"Lead task created from {lead['platform']} lead."
                }
            ]
        }
        
        # Save task to file
        task_path = TASK_DIR / f"{task_id}.json"
        with open(task_path, 'w') as f:
            json.dump(task, f, indent=2)
            
        logger.info(f"Created task {task_id} for lead analysis")
        
        # If assigned to an agent, notify them
        if assign_to:
            self._notify_agent_about_task(assign_to, task_id, lead)
            
        return task_id
    
    def _notify_agent_about_task(self, agent: str, 
                             task_id: str, lead: Dict[str, Any]) -> None:
        """
        Notify an agent about a new lead task.
        
        Args:
            agent: Agent to notify (e.g., "Agent-3")
            task_id: ID of the created task
            lead: Lead dictionary
        """
        # Create notification message
        notification = {
            "type": "SOCIAL_LEAD_TASK",
            "timestamp": datetime.now().isoformat(),
            "from": "LeadEpisodeGenerator",
            "to": agent,
            "subject": f"New Lead Task: {lead['query']} on {lead['platform']}",
            "content": {
                "task_id": task_id,
                "platform": lead['platform'],
                "query": lead['query'],
                "username": lead['username'],
                "match_excerpt": lead['match'][:150] + ("..." if len(lead['match']) > 150 else ""),
                "link": lead['link'],
                "instructions": "Please analyze this lead and determine appropriate follow-up actions."
            }
        }
        
        # Write notification to agent's inbox
        inbox_path = AGENT_MAILBOX_DIR / agent / "inbox"
        inbox_path.mkdir(parents=True, exist_ok=True)
        
        message_path = inbox_path / f"social_lead_task_{task_id}.json"
        with open(message_path, 'w') as f:
            json.dump(notification, f, indent=2)
            
        logger.info(f"Notified {agent} about new lead task: {task_id}")
        
    def search_and_generate_tasks(self, platform: str, keywords: List[str],
                                assign_to: Optional[str] = None,
                                max_results: int = 5) -> List[str]:
        """
        Search for leads and immediately generate tasks.
        
        Args:
            platform: Social platform to search
            keywords: Keywords to search for
            assign_to: Optional agent to assign tasks to
            max_results: Maximum number of tasks to create
            
        Returns:
            List of created task IDs
        """
        # Use SocialScout to find leads
        with SocialScout(platform=platform) as scout:
            leads = scout.find_leads(keywords=keywords, max_results=max_results)
            
        if not leads:
            logger.warning(f"No leads found on {platform} for keywords: {keywords}")
            return []
            
        # Create tasks from leads
        task_ids = []
        for lead in leads:
            task_id = self.create_task_from_lead(lead, assign_to)
            task_ids.append(task_id)
            
        return task_ids 