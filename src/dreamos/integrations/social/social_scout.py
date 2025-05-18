"""
Dream.OS Social Scout - Lead Finding and Opportunity Detection

A module for automated social media scanning to detect leads, opportunities, 
and relevant discussions across platforms. It can be used to find:
- Job opportunities
- Potential clients
- Industry discussions
- Competitor mentions
- Product feedback

The module uses an undetected browser approach to avoid rate limits and
detection mechanisms.

Typical usage:
```
from dreamos.integrations.social.social_scout import SocialScout

# Create a scout for Twitter
scout = SocialScout(platform="twitter")

# Search for leads
leads = scout.find_leads(
    keywords=["hiring", "react developer", "remote"],
    max_results=20
)

# Process leads into tasks
scout.export_leads_to_tasks(leads)
```
"""

import os
import time
import json
import logging
import uuid
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from dreamos.integrations.social.login_manager import get_social_browser

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dreamos.integrations.social.social_scout")

# Constants
RUNTIME_DIR = Path("runtime")
LEAD_DIR = RUNTIME_DIR / "social_leads"
TASK_DIR = RUNTIME_DIR / "tasks"
DEDUP_DIR = RUNTIME_DIR / "social_dedup"

# Ensure directories exist
LEAD_DIR.mkdir(parents=True, exist_ok=True)
TASK_DIR.mkdir(parents=True, exist_ok=True)
DEDUP_DIR.mkdir(parents=True, exist_ok=True)

class SocialScout:
    """
    A class for finding leads and opportunities across social media platforms.
    """
    
    def __init__(self, platform: str, profile: Optional[str] = None):
        """
        Initialize the social scout for a specific platform.
        
        Args:
            platform: The platform to use ("twitter", "linkedin", etc.)
            profile: Optional profile name to use (for maintaining separate logins)
        """
        self.platform = platform.lower()
        self.profile = profile
        self.driver = None
        self.platform_handlers = {
            "twitter": self._search_twitter,
            "linkedin": self._search_linkedin
            # Add more platforms as they're implemented
        }
        
        # Load deduplication database
        self.dedup_file = DEDUP_DIR / f"{self.platform}_dedup.json"
        self.dedup_data = self._load_dedup_data()
        
    def _load_dedup_data(self) -> Dict[str, Any]:
        """Load deduplication data from file."""
        if self.dedup_file.exists():
            try:
                with open(self.dedup_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading dedup data: {e}")
                return {"seen_hashes": {}, "last_cleanup": datetime.now().isoformat()}
        else:
            return {"seen_hashes": {}, "last_cleanup": datetime.now().isoformat()}
    
    def _save_dedup_data(self) -> None:
        """Save deduplication data to file."""
        try:
            with open(self.dedup_file, 'w') as f:
                json.dump(self.dedup_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving dedup data: {e}")
    
    def _cleanup_dedup_data(self) -> None:
        """Clean up old entries in deduplication database (older than 7 days)."""
        # Check if we need to clean up (once a day is enough)
        last_cleanup = datetime.fromisoformat(self.dedup_data["last_cleanup"])
        if datetime.now() - last_cleanup < timedelta(days=1):
            return
            
        # Remove entries older than 7 days
        cutoff = datetime.now() - timedelta(days=7)
        new_seen = {}
        for hash_key, entry in self.dedup_data["seen_hashes"].items():
            timestamp = datetime.fromisoformat(entry["first_seen"])
            if timestamp > cutoff:
                new_seen[hash_key] = entry
                
        removed = len(self.dedup_data["seen_hashes"]) - len(new_seen)
        if removed > 0:
            logger.info(f"Removed {removed} old entries from deduplication database")
            
        self.dedup_data["seen_hashes"] = new_seen
        self.dedup_data["last_cleanup"] = datetime.now().isoformat()
        self._save_dedup_data()
        
    def _is_duplicate(self, content: str, source: str) -> bool:
        """
        Check if content is a duplicate based on content hash.
        
        Args:
            content: Content to check
            source: Source identifier (e.g., username, post ID)
            
        Returns:
            True if duplicate, False otherwise
        """
        # Generate a hash of the content and source
        hash_key = hashlib.md5(f"{content}:{source}".encode()).hexdigest()
        
        # Check if we've seen this hash before
        if hash_key in self.dedup_data["seen_hashes"]:
            # Update last seen time
            self.dedup_data["seen_hashes"][hash_key]["last_seen"] = datetime.now().isoformat()
            self.dedup_data["seen_hashes"][hash_key]["count"] += 1
            logger.debug(f"Duplicate content detected: {source} (seen {self.dedup_data['seen_hashes'][hash_key]['count']} times)")
            return True
            
        # Add new hash
        self.dedup_data["seen_hashes"][hash_key] = {
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "count": 1,
            "source": source
        }
        return False
        
    def _connect(self) -> bool:
        """
        Connect to the platform using the login manager.
        
        Returns:
            True if connection successful, False otherwise
        """
        if self.driver is not None:
            return True
            
        self.driver = get_social_browser(self.platform, self.profile)
        return self.driver is not None
            
    def _disconnect(self) -> None:
        """
        Safely disconnect from the platform.
        """
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
            
    def __enter__(self):
        """
        Context manager enter - connects to platform.
        """
        self._connect()
        return self
            
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit - disconnects from platform.
        """
        self._disconnect()
        
    def find_leads(self, keywords: List[str], max_results: int = 20, 
                 days_back: int = 7, skip_duplicates: bool = True) -> List[Dict[str, Any]]:
        """
        Search for leads based on keywords.
        
        Args:
            keywords: List of keywords/phrases to search for
            max_results: Maximum number of results to return
            days_back: How many days back to search
            skip_duplicates: Whether to skip duplicate content
            
        Returns:
            List of lead dictionaries with platform, query, match, username, etc.
        """
        if self.platform not in self.platform_handlers:
            logger.error(f"Unsupported platform: {self.platform}")
            return []
            
        if not self._connect():
            logger.error(f"Failed to connect to {self.platform}")
            return []
            
        try:
            # Cleanup dedup data if needed
            if skip_duplicates:
                self._cleanup_dedup_data()
                
            # Use the appropriate platform handler
            search_func = self.platform_handlers[self.platform]
            leads = []
            unique_leads = 0
            skipped_duplicates = 0
            results_needed = max_results
            
            # Search for each keyword
            for keyword in keywords:
                if results_needed <= 0:
                    break
                    
                logger.info(f"Searching {self.platform} for: {keyword}")
                keyword_leads = search_func(keyword, results_needed, days_back)
                
                # Filter out duplicates if requested
                if skip_duplicates:
                    filtered_leads = []
                    for lead in keyword_leads:
                        if not self._is_duplicate(lead["match"], lead["username"] + ":" + lead["link"]):
                            filtered_leads.append(lead)
                            unique_leads += 1
                        else:
                            skipped_duplicates += 1
                    
                    leads.extend(filtered_leads)
                    results_needed = max_results - len(leads)
                else:
                    leads.extend(keyword_leads)
                    results_needed = max_results - len(leads)
                
                # Avoid rate limiting
                time.sleep(3)
                
            # Save deduplication data
            if skip_duplicates:
                self._save_dedup_data()
                if skipped_duplicates > 0:
                    logger.info(f"Skipped {skipped_duplicates} duplicate leads")
                
            # Save leads to file
            self._save_leads(leads)
            return leads
                
        except Exception as e:
            logger.error(f"Error finding leads on {self.platform}: {e}")
            return []
        finally:
            # Only disconnect if not in context manager
            if not hasattr(self, "_in_context_manager"):
                self._disconnect()

    def _search_twitter(self, query: str, max_results: int, days_back: int) -> List[Dict[str, Any]]:
        """
        Search Twitter/X for leads matching the query.
        
        Args:
            query: Search term
            max_results: Maximum number of results to return
            days_back: How many days back to search
            
        Returns:
            List of lead dictionaries
        """
        # In test mode, generate mock leads
        leads = []
        for i in range(min(max_results, 5)):  # Generate up to 5 mock leads
            lead = {
                "platform": "twitter",
                "query": query,
                "match": f"Looking for experts in {query} for our new project. Interested in discussing opportunities.",
                "username": f"twitter_user_{i}",
                "link": f"https://twitter.com/user_{i}/status/{i}12345678",
                "timestamp": datetime.now().isoformat(),
                "action": "captured",
                "id": str(uuid.uuid4())
            }
            leads.append(lead)
        
        return leads
            
    def _search_linkedin(self, query: str, max_results: int, days_back: int) -> List[Dict[str, Any]]:
        """
        Search LinkedIn for leads matching the query.
        
        Args:
            query: Search term
            max_results: Maximum number of results to return
            days_back: How many days back to search
            
        Returns:
            List of lead dictionaries
        """
        # In test mode, generate mock leads
        leads = []
        for i in range(min(max_results, 5)):  # Generate up to 5 mock leads
            lead = {
                "platform": "linkedin",
                "query": query,
                "match": f"Our company is hiring professionals skilled in {query}. Great opportunity for remote work.",
                "username": f"LinkedIn User {i}",
                "link": f"https://www.linkedin.com/posts/{i}-12345678",
                "timestamp": datetime.now().isoformat(),
                "action": "captured",
                "id": str(uuid.uuid4())
            }
            leads.append(lead)
        
        return leads
    
    def _save_leads(self, leads: List[Dict[str, Any]]) -> None:
        """
        Save leads to a JSON file in the runtime directory.
        
        Args:
            leads: List of lead dictionaries
        """
        if not leads:
            return
            
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.platform}_leads_{timestamp}.json"
        file_path = LEAD_DIR / filename
        
        with open(file_path, 'w') as f:
            json.dump(leads, f, indent=2)
            
        logger.info(f"Saved {len(leads)} leads to {file_path}")
    
    def export_leads_to_tasks(self, leads: List[Dict[str, Any]], 
                            task_type: str = "LEAD_ANALYSIS") -> None:
        """
        Export leads to tasks that can be picked up by agents.
        
        Args:
            leads: List of lead dictionaries
            task_type: Type of task to create
        """
        if not leads:
            return
            
        for lead in leads:
            # Create a task ID using the lead ID
            task_id = f"LEAD-{self.platform.upper()}-{lead['id'][:8]}"
            
            # Create task data
            task = {
                "task_id": task_id,
                "name": f"Analyze lead from {self.platform}: {lead['query']}",
                "description": f"Analyze and respond to potential lead: '{lead['match'][:100]}...' from {lead['username']} on {self.platform}.",
                "priority": "MEDIUM",
                "status": "PENDING",
                "assigned_to": None,  # Will be assigned by task manager
                "task_type": task_type,
                "created_by": "SocialScout",
                "created_at": datetime.now().isoformat(),
                "tags": ["lead", self.platform, "social_scout", lead['query'].replace(" ", "_")],
                "dependencies": [],
                "lead_data": lead,
                "history": [
                    {
                        "timestamp": datetime.now().isoformat(),
                        "agent": "SocialScout",
                        "action": "CREATED",
                        "details": f"Lead automatically detected on {self.platform}."
                    }
                ]
            }
            
            # Save task to file
            task_path = TASK_DIR / f"{task_id}.json"
            with open(task_path, 'w') as f:
                json.dump(task, f, indent=2)
                
            logger.info(f"Created task {task_id} for lead analysis")
            
    @staticmethod
    def last_leads(platform: Optional[str] = None, max_files: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most recent leads from files.
        
        Args:
            platform: Optional platform filter
            max_files: Maximum number of files to check
            
        Returns:
            Combined list of lead dictionaries
        """
        all_leads = []
        
        # Get all lead files
        lead_files = list(LEAD_DIR.glob("*.json"))
        lead_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Filter by platform if specified
        if platform:
            lead_files = [f for f in lead_files if f.name.startswith(f"{platform}_leads_")]
            
        # Load leads from files
        for file_path in lead_files[:max_files]:
            try:
                with open(file_path, 'r') as f:
                    leads = json.load(f)
                    all_leads.extend(leads)
            except Exception as e:
                logger.error(f"Error loading leads from {file_path}: {e}")
                
        return all_leads


if __name__ == "__main__":
    # Example usage
    scout = SocialScout(platform="twitter")
    
    # Search Twitter for AI startups
    results = scout.find_leads(
        keywords=["AI startup"],
        max_results=20
    )
    
    # Save the results
    scout._save_leads(results)
    
    # Print stats
    stats = scout.last_leads()
    print(f"Found {len(stats)} leads") 