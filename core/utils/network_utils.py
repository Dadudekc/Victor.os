import random
import time
import logging

logger = logging.getLogger(__name__)

def random_delay(min_delay: float = 0.5, max_delay: float = 1.5):
    """Pauses execution for a random duration between min_delay and max_delay seconds."""
    delay = random.uniform(min_delay, max_delay)
    logger.debug(f"Sleeping for {delay:.2f} seconds...")
    time.sleep(delay)

def get_random_user_agent() -> str:
    """
    Returns a random user agent string from a predefined list.
    (Consider externalizing this list or using a library for more comprehensive options)
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0"
        # Add more realistic and diverse user agents if needed
    ]
    return random.choice(user_agents) 