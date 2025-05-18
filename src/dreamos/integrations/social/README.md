# Dream.OS Social Media Integration

A comprehensive system for integrating social media platforms into the Dream.OS agent ecosystem. This module allows agents to search for leads, extract information, and generate actionable episodes and tasks based on social media data.

## Features

- **Multi-platform Login Management**: Secure session handling for Twitter, LinkedIn, Facebook, Instagram, Reddit, and Stocktwits
- **Lead Discovery**: Find potential leads matching specific search criteria across platforms
- **Automated Episode Generation**: Convert leads into structured agent episodes
- **Task Generation**: Create fine-grained tasks for lead follow-up
- **Command-line Interface**: Easy access to functionality from the terminal

## Components

The integration consists of several components:

1. **Login Manager (`login_manager.py`)**: Handles authentication and session management
2. **Social Scout (`social_scout.py`)**: Searches and extracts lead data from platforms
3. **Lead Episode Generator (`lead_episode_generator.py`)**: Converts leads to agent episodes
4. **Command-line Interface (`scout_cli.py`)**: Terminal-based user interface
5. **Configuration (`config.py`)**: Centralized configuration management
6. **Logging Setup (`logging_setup.py`)**: Unified logging system

## Installation

The social media integration is installed as part of the Dream.OS system. Make sure you have the required dependencies:

```bash
pip install selenium webdriver-manager python-dotenv pyyaml undetected-chromedriver
```

## Usage

### Searching for Leads

```python
from dreamos.integrations.social.login_manager import PlatformLoginManager
from dreamos.integrations.social.social_scout import SocialScout

# Using a context manager for proper resource cleanup
with PlatformLoginManager() as manager:
    scout = SocialScout(login_manager=manager)
    
    # Search for AI startups on Twitter
    results = scout.search("AI startup", platforms=["twitter"])
    
    # Save the results
    scout.save_leads("ai_startup_leads.json")
```

### Creating Episodes

```python
from dreamos.integrations.social.lead_episode_generator import LeadEpisodeGenerator

# Load leads from a file
generator = LeadEpisodeGenerator("runtime/data/leads/ai_startup_leads.json")

# Create an episode
episode_path = generator.create_episode(
    episode_name="AI Startup Opportunities",
    priority="high"
)

# Notify an agent about the new episode
generator.notify_agent(
    "lead_manager",
    "New AI startup leads found on Twitter",
    {"episode_path": episode_path}
)
```

### Command-line Interface

The module includes a command-line interface for easy access:

```bash
# Search for AI startups on Twitter and LinkedIn
python -m dreamos.integrations.social.scout_cli search "AI startup" --save

# Create an episode from leads file
python -m dreamos.integrations.social.scout_cli episode runtime/data/leads/leads_20230615_121510.json --name "AI Startup Leads" --notify lead_manager

# Create individual tasks from leads file
python -m dreamos.integrations.social.scout_cli tasks runtime/data/leads/leads_20230615_121510.json
```

## Configuration

The module uses a configuration system that looks for settings in:

1. Environment variables
2. .env file in the root directory
3. Default values in the code

Key configuration variables:

- `LINKEDIN_EMAIL` / `LINKEDIN_PASSWORD`: LinkedIn credentials
- `TWITTER_EMAIL` / `TWITTER_PASSWORD`: Twitter credentials
- `CHROME_PROFILE_PATH`: Path to Chrome profile directory
- `COOKIE_STORAGE_PATH`: Path to cookie storage directory
- `SEARCH_LIMIT`: Maximum search results per platform
- `MIN_FOLLOWERS`: Minimum follower count for leads

## Extending the System

### Adding New Platforms

To add support for a new platform:

1. Add a new login method in `PlatformLoginManager`:

```python
def login_new_platform(self) -> bool:
    """Login to the new platform."""
    platform = "new_platform"
    self.driver.get("https://newplatform.com/login")
    # Implement login logic...
    return True
```

2. Add the method to the `login_methods` dictionary in `__init__`
3. Add search functionality in `SocialScout`

### Customizing Lead Processing

The `LeadEpisodeGenerator` class can be extended to create custom processing pipelines:

```python
class CustomLeadProcessor(LeadEpisodeGenerator):
    def analyze_leads(self):
        """Add custom lead analysis logic."""
        for lead in self.leads:
            # Custom analysis code...
            lead['score'] = calculate_score(lead)
            lead['category'] = determine_category(lead)
```

## License

This module is part of the Dream.OS project and is subject to the same license terms. 