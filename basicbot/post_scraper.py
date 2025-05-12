"""
-- D:\\TradingRobotPlug\\basicbot\\post_scraper.py --

Description:
------------
This module contains functions for scraping posts from various social media platforms.
It uses Selenium for browser automation to scroll pages and extract content.
Configuration values (such as log directories and credentials) and logging are handled
via the centralized `config.py` and `setup_logging.py` modules.

Supported Platforms:
  - LinkedIn: Scrapes posts from the feed.
  - Twitter (X): Scrapes tweets from the home feed.
  - Reddit: Scrapes top posts from a specified subreddit.
  - Facebook: Scrapes posts from the news feed.

Additionally, scraped posts can be stored into a vectorized database via `db_handler.py`.

Usage:
    After logging in (handled by social_scraper.py), call these functions with a Selenium driver.
    For example:
        posts = scrape_linkedin_posts(driver)
        # Aggregate posts from all platforms and store:
        from basicbot.db_handler import DatabaseHandler
        db = DatabaseHandler(logger)
        db.save_posts(posts)
        db.close()
"""

import time
from selenium.webdriver.common.by import By
from basicbot.config import config
from basicbot.setup_logging import setup_logging
from basicbot.db_handler import DatabaseHandler

# Initialize logger for this module using centralized logging.
logger = setup_logging("post_scraper", log_dir=config.get_env("LOG_DIR", "logs/social"))

def scroll_down(driver, times=3, wait_time=2):
    """
    Scrolls down the page to load additional dynamic content.
    
    :param driver: Selenium webdriver instance.
    :param times: Number of scrolls to perform.
    :param wait_time: Seconds to wait between scrolls.
    """
    for _ in range(times):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(wait_time)
    logger.debug("Scrolled down %d times.", times)

def scrape_linkedin_posts(driver, max_posts=5):
    """
    Scrapes posts from the LinkedIn feed.
    
    :param driver: Selenium webdriver instance.
    :param max_posts: Maximum number of posts to extract.
    :return: List of dictionaries with keys 'platform', 'text', and 'link' (if available).
    """
    driver.get("https://www.linkedin.com/feed/")
    time.sleep(5)
    scroll_down(driver, times=3)
    
    posts = []
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "div.feed-shared-update-v2")
        for element in elements[:max_posts]:
            try:
                text = element.find_element(By.CSS_SELECTOR, "span.break-words").text
                # Attempt to extract a link if available.
                link = None
                try:
                    link_elem = element.find_element(By.TAG_NAME, "a")
                    link = link_elem.get_attribute("href")
                except Exception:
                    pass
                posts.append({"platform": "LinkedIn", "text": text, "link": link})
            except Exception as e:
                logger.error("Error scraping LinkedIn post: %s", e)
    except Exception as e:
        logger.error("Failed to locate LinkedIn post elements: %s", e)
    
    logger.info("Scraped %d LinkedIn posts.", len(posts))
    return posts

def scrape_twitter_posts(driver, max_posts=5):
    """
    Scrapes tweets from Twitter's home feed.
    
    :param driver: Selenium webdriver instance.
    :param max_posts: Maximum number of tweets to extract.
    :return: List of dictionaries with keys 'platform' and 'text'.
    """
    driver.get("https://twitter.com/home")
    time.sleep(5)
    scroll_down(driver, times=3)
    
    tweets = []
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "article")
        for element in elements[:max_posts]:
            try:
                text = element.find_element(By.CSS_SELECTOR, "div[lang]").text
                tweets.append({"platform": "Twitter", "text": text})
            except Exception as e:
                logger.error("Error scraping tweet: %s", e)
    except Exception as e:
        logger.error("Failed to locate tweet elements: %s", e)
    
    logger.info("Scraped %d tweets.", len(tweets))
    return tweets

def scrape_reddit_posts(driver, subreddit="popular", max_posts=5):
    """
    Scrapes top posts from a specified subreddit.
    
    :param driver: Selenium webdriver instance.
    :param subreddit: Subreddit to scrape (default is 'popular').
    :param max_posts: Maximum number of posts to extract.
    :return: List of dictionaries with keys 'platform', 'text', and 'link'.
    """
    driver.get(f"https://www.reddit.com/r/{subreddit}/")
    time.sleep(5)
    scroll_down(driver, times=3)
    
    posts = []
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "div[data-click-id='background']")
        for element in elements[:max_posts]:
            try:
                title = element.find_element(By.TAG_NAME, "h3").text
                link = element.find_element(By.TAG_NAME, "a").get_attribute("href")
                posts.append({"platform": "Reddit", "text": title, "link": link})
            except Exception as e:
                logger.error("Error scraping Reddit post: %s", e)
    except Exception as e:
        logger.error("Failed to locate Reddit post elements: %s", e)
    
    logger.info("Scraped %d Reddit posts from r/%s.", len(posts), subreddit)
    return posts

def scrape_facebook_posts(driver, max_posts=5):
    """
    Scrapes posts from Facebook's news feed.
    
    :param driver: Selenium webdriver instance.
    :param max_posts: Maximum number of posts to extract.
    :return: List of dictionaries with keys 'platform' and 'text'.
    """
    driver.get("https://www.facebook.com/")
    time.sleep(5)
    scroll_down(driver, times=3)
    
    posts = []
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "div[data-ad-comet-preview='message']")
        for element in elements[:max_posts]:
            try:
                text = element.text
                posts.append({"platform": "Facebook", "text": text})
            except Exception as e:
                logger.error("Error scraping Facebook post: %s", e)
    except Exception as e:
        logger.error("Failed to locate Facebook post elements: %s", e)
    
    logger.info("Scraped %d Facebook posts.", len(posts))
    return posts

def store_scraped_posts(posts):
    """
    Uses the unified database handler to store scraped posts.
    
    :param posts: List of post dictionaries.
    """
    from basicbot.db_handler import DatabaseHandler  # Import here to avoid circular dependencies
    db = DatabaseHandler(logger)
    try:
        db.save_posts(posts)
        logger.info("Stored %d posts in the database.", len(posts))
    except Exception as e:
        logger.error("Error storing posts: %s", e)
    finally:
        db.close()

if __name__ == "__main__":
    # For manual testing, initialize the Selenium driver.
    # Note: The driver is expected to be created by social_scraper.py.
    from basicbot.social_scraper import get_driver
    driver = get_driver()
    
    # Scrape posts from each platform.
    linkedin_posts = scrape_linkedin_posts(driver)
    twitter_posts = scrape_twitter_posts(driver)
    reddit_posts = scrape_reddit_posts(driver)
    facebook_posts = scrape_facebook_posts(driver)
    
    driver.quit()
    
    # Aggregate all posts.
    all_posts = linkedin_posts + twitter_posts + reddit_posts + facebook_posts
    
    # Optionally store posts in the database.
    store_scraped_posts(all_posts)
    
    # Print results for verification.
    print("LinkedIn Posts:", linkedin_posts)
    print("Twitter Posts:", twitter_posts)
    print("Reddit Posts:", reddit_posts)
    print("Facebook Posts:", facebook_posts)
