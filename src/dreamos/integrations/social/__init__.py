"""
Dream.OS Social Media Integration

A module for automated social media scanning, lead generation,
and task creation for the Dream.OS agent ecosystem.
"""

# Version
__version__ = "0.1.0"

# Export the core classes
from dreamos.integrations.social.social_scout import SocialScout
from dreamos.integrations.social.lead_episode_generator import LeadEpisodeGenerator
from dreamos.integrations.social.login_manager import get_social_browser

# Make imports easier
__all__ = [
    "SocialScout",
    "LeadEpisodeGenerator",
    "get_social_browser"
]
