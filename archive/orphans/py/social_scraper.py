"""
-- D:\\TradingRobotPlug\\basicbot\\social_scraper.py --

Description:
------------
This script automates the login process for several social media platforms
using Selenium. It retrieves credentials and settings from a centralized
configuration (config.py) and logs events via a structured logging setup
(setup_logging.py). It uses a persistent Chrome profile to retain session cookies
and allows manual login retries when automatic login isn’t sufficient (e.g., due to captchas).

Supported Platforms:
  - LinkedIn
  - Twitter (X)
  - Facebook
  - Instagram
  - Reddit
"""

import os
import pickle
import time

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# Load environment variables (if needed; config will also load these)
load_dotenv()

# Import centralized configuration and logging
from basicbot.config import config
from basicbot.setup_logging import setup_logging

# Initialize logger using centralized logging configuration
logger = setup_logging(
    "social_scraper", log_dir=os.path.join(os.getcwd(), "logs", "social")
)

# Retrieve social credentials from configuration (assumes config provides these)
SOCIAL_CREDENTIALS = {
    "linkedin": {
        "email": config.get_env("LINKEDIN_EMAIL"),
        "password": config.get_env("LINKEDIN_PASSWORD"),
    },
    "twitter": {
        "email": config.get_env("TWITTER_EMAIL"),
        "password": config.get_env("TWITTER_PASSWORD"),
    },
    "facebook": {
        "email": config.get_env("FACEBOOK_EMAIL"),
        "password": config.get_env("FACEBOOK_PASSWORD"),
    },
    "instagram": {
        "email": config.get_env("INSTAGRAM_EMAIL"),
        "password": config.get_env("INSTAGRAM_PASSWORD"),
    },
    "reddit": {
        "email": config.get_env("REDDIT_USERNAME"),
        "password": config.get_env("REDDIT_PASSWORD"),
    },
}

MAX_ATTEMPTS = 3  # Maximum manual login attempts


def get_driver(profile_path: str = None):
    """
    Returns a Selenium Chrome driver instance that uses a persistent profile.

    If profile_path is not provided, a new folder named "chrome_profile" in the
    current working directory will be used.

    :param profile_path: Path to the Chrome user data directory.
    :return: Configured Selenium Chrome driver.
    """
    options = Options()
    options.add_argument("--start-maximized")

    # Use a persistent profile directory (configured in config or default)
    if profile_path is None:
        profile_path = config.get_env(
            "CHROME_PROFILE_PATH", os.path.join(os.getcwd(), "chrome_profile")
        )
    options.add_argument(f"--user-data-dir={profile_path}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    logger.info("Chrome driver initialized using profile: %s", profile_path)
    return driver


def load_cookies(driver, platform):
    """
    Loads saved cookies for the given platform into the driver.
    """
    cookie_path = os.path.join("cookies", f"{platform}.pkl")
    if os.path.exists(cookie_path):
        with open(cookie_path, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                cookie.pop("sameSite", None)
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    logger.error("Error adding cookie for %s: %s", platform, e)
        logger.info("Loaded cookies for %s", platform)
    else:
        logger.info("No cookies found for %s.", platform)


def save_cookies(driver, platform):
    """
    Saves the current session cookies for the given platform.
    """
    os.makedirs("cookies", exist_ok=True)
    cookie_path = os.path.join("cookies", f"{platform}.pkl")
    with open(cookie_path, "wb") as file:
        pickle.dump(driver.get_cookies(), file)
    logger.info("Saved cookies for %s", platform)


def wait_for_manual_login(driver, check_func, platform):
    """
    Allows manual login by prompting the user until a check function returns True.

    :param driver: The Selenium driver.
    :param check_func: A callable that returns True if login succeeded.
    :param platform: Platform name.
    :return: True if login succeeded within MAX_ATTEMPTS; otherwise, False.
    """
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        input(f"Please complete the login for {platform} and press Enter when done...")
        if check_func(driver):
            logger.info("%s login detected.", platform.capitalize())
            save_cookies(driver, platform)
            return True
        else:
            logger.warning("%s login not detected. Try again.", platform.capitalize())
            attempts += 1
    logger.error("Maximum attempts reached for %s.", platform)
    return False


### LinkedIn Login
def login_linkedin(driver):
    platform = "linkedin"
    driver.get("https://www.linkedin.com/login")
    time.sleep(3)

    load_cookies(driver, platform)
    driver.refresh()
    time.sleep(3)

    if "feed" in driver.current_url:
        logger.info("Already logged into LinkedIn.")
        return

    creds = SOCIAL_CREDENTIALS.get(platform)
    if creds and creds["email"] and creds["password"]:
        try:
            driver.find_element(By.ID, "username").send_keys(creds["email"])
            driver.find_element(By.ID, "password").send_keys(
                creds["password"], Keys.RETURN
            )
        except Exception as e:
            logger.error("Automatic login error for %s: %s", platform, e)

    wait_for_manual_login(driver, lambda d: "feed" in d.current_url, platform)


### Twitter (X) Login
def login_twitter(driver):
    platform = "twitter"
    driver.get("https://twitter.com/login")
    time.sleep(5)  # Allow page to load

    load_cookies(driver, platform)
    driver.refresh()
    time.sleep(5)

    if "home" in driver.current_url:
        logger.info("Already logged into Twitter.")
        return

    creds = SOCIAL_CREDENTIALS.get(platform)
    if creds and creds["email"] and creds["password"]:
        try:
            email_field = driver.find_element(By.NAME, "text")
            email_field.send_keys(creds["email"], Keys.RETURN)
            time.sleep(3)
            try:
                driver.find_element(By.XPATH, "//span[contains(text(),'Next')]").click()
                time.sleep(3)
            except Exception:
                pass
            password_field = driver.find_element(By.NAME, "password")
            password_field.send_keys(creds["password"], Keys.RETURN)
        except Exception as e:
            logger.error("Automatic login error for %s: %s", platform, e)

    wait_for_manual_login(driver, lambda d: "home" in d.current_url, platform)


### Facebook Login
def login_facebook(driver):
    platform = "facebook"
    driver.get("https://www.facebook.com/login/")
    time.sleep(3)

    load_cookies(driver, platform)
    driver.refresh()
    time.sleep(3)

    def fb_logged_in(d):
        try:
            return (
                d.find_element(
                    By.XPATH, "//div[contains(@aria-label, 'Create a post')]"
                )
                is not None
            )
        except Exception:
            return False

    if fb_logged_in(driver):
        logger.info("Already logged into Facebook.")
        return

    creds = SOCIAL_CREDENTIALS.get(platform)
    if creds and creds["email"] and creds["password"]:
        try:
            driver.find_element(By.ID, "email").send_keys(creds["email"])
            driver.find_element(By.ID, "pass").send_keys(creds["password"], Keys.RETURN)
        except Exception as e:
            logger.error("Automatic login error for %s: %s", platform, e)

    wait_for_manual_login(driver, fb_logged_in, platform)


### Instagram Login
def login_instagram(driver):
    platform = "instagram"
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(5)

    load_cookies(driver, platform)
    driver.refresh()
    time.sleep(5)

    if "accounts/onetap" in driver.current_url or "instagram.com" in driver.current_url:
        logger.info("Already logged into Instagram.")
        return

    creds = SOCIAL_CREDENTIALS.get(platform)
    if creds and creds["email"] and creds["password"]:
        try:
            driver.find_element(By.NAME, "username").send_keys(creds["email"])
            driver.find_element(By.NAME, "password").send_keys(
                creds["password"], Keys.RETURN
            )
        except Exception as e:
            logger.error("Automatic login error for %s: %s", platform, e)

    wait_for_manual_login(driver, lambda d: "instagram.com" in d.current_url, platform)


### Reddit Login
def login_reddit(driver):
    platform = "reddit"
    driver.get("https://www.reddit.com/login/")
    time.sleep(5)

    load_cookies(driver, platform)
    driver.refresh()
    time.sleep(5)

    if "reddit.com" in driver.current_url and "login" not in driver.current_url:
        logger.info("Already logged into Reddit.")
        return

    creds = SOCIAL_CREDENTIALS.get(platform)
    if creds and creds["email"] and creds["password"]:
        try:
            time.sleep(3)
            username_field = driver.find_element(By.ID, "loginUsername")
            password_field = driver.find_element(By.ID, "loginPassword")
            username_field.send_keys(creds["email"])
            password_field.send_keys(creds["password"], Keys.RETURN)
        except Exception as e:
            logger.error("Automatic login error for %s: %s", platform, e)

    wait_for_manual_login(
        driver,
        lambda d: "reddit.com" in d.current_url and "login" not in d.current_url,
        platform,
    )


def run_all_logins():
    """
    Runs login procedures for all supported social media platforms.
    Uses a persistent Chrome profile to retain session data.
    """
    driver = get_driver()  # Uses persistent profile from config if available

    login_functions = [
        login_linkedin,
        login_twitter,
        login_facebook,
        login_instagram,
        login_reddit,
    ]

    for login_fn in login_functions:
        try:
            login_fn(driver)
        except Exception as e:
            logger.error("Error during %s: %s", login_fn.__name__, e)

    logger.info("All logins attempted.")
    driver.quit()


if __name__ == "__main__":
    run_all_logins()
