import logging
import os
import pickle
import shutil
import sys
import tempfile
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Optional undetected_chromedriver support
try:
    import undetected_chromedriver as uc

    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False


# ---------------------------
# Logger Setup
# ---------------------------
def setup_logger(
    name="DriverManager", log_dir=os.path.join(os.getcwd(), "logs", "core")
):
    # Assuming log directory structure - adjust if needed relative to this file's location  # noqa: E501
    # Maybe use Path(__file__).parent.parent.parent / "logs" / "core" ?
    log_dir = os.path.abspath(log_dir)
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(name)
    # Prevent duplicate handlers if logger is already configured
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

        log_file_path = os.path.join(log_dir, f"{name}.log")
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        logger.propagate = False  # Prevent root logger from handling these messages too

    return logger


logger = setup_logger()


# ---------------------------
# Consolidated DriverManager Class
# ---------------------------
class DriverManager:
    """
    Unified DriverManager for Selenium-based browser automation.

    Features:
      - Singleton pattern to ensure a single active driver instance per configuration hash
      - Session management with automatic expiration (default 1 hour) and renewal
      - Persistent profile support (or temporary profiles in headless mode)
      - Cookie saving/loading for session persistence
      - Support for headless mode, mobile emulation, and optional undetected mode
      - Auto-downloading and caching of the ChromeDriver executable
      - Robust retry mechanisms for resilient browser operations
      - Utilities for waiting, scrolling, and option updates
    """  # noqa: E501

    # Changed to manage multiple instances based on config hash for flexibility
    _instances: Dict[int, "DriverManager"] = {}
    _lock = threading.Lock()

    # Default constants
    CHATGPT_URL = "https://chat.openai.com/"
    DEFAULT_TIMEOUT = 10
    DEFAULT_MAX_SESSION_DURATION = 3600  # seconds (1 hour)
    DEFAULT_RETRY_ATTEMPTS = 3
    DEFAULT_RETRY_DELAY = 5

    @classmethod
    def get_instance(
        cls, config_key: Optional[str] = "default", **kwargs
    ) -> "DriverManager":
        """
        Gets or creates a DriverManager instance based on a configuration key or kwargs.
        Using kwargs allows different scrapers/tasks to request drivers with different settings
        (e.g., different profiles, headless state).

        Args:
            config_key (Optional[str]): A simple key to retrieve a common configuration.
            **kwargs: Configuration options used to create/retrieve a specific instance.
                      If provided, they override any default associated with config_key.
                      Relevant keys: profile_dir, driver_cache_dir, headless, cookie_file, etc.

        Returns:
            DriverManager: The singleton instance for the given configuration.
        """  # noqa: E501
        config_hash = hash(frozenset(kwargs.items())) if kwargs else hash(config_key)

        with cls._lock:
            if config_hash not in cls._instances:
                logger.info(
                    f"Creating new DriverManager instance for config hash {config_hash} (key: {config_key}, kwargs: {kwargs})"  # noqa: E501
                )
                # Pass kwargs directly to init
                instance = cls(**kwargs)
                cls._instances[config_hash] = instance
            else:
                logger.debug(
                    f"Returning existing DriverManager instance for config hash {config_hash}"  # noqa: E501
                )
            return cls._instances[config_hash]

    # __new__ is removed as instance creation is handled by get_instance

    def __init__(
        self,
        profile_dir: Optional[str] = None,
        driver_cache_dir: Optional[str] = None,
        headless: bool = False,
        cookie_file: Optional[str] = None,
        wait_timeout: int = DEFAULT_TIMEOUT,
        mobile_emulation: bool = False,
        additional_arguments: Optional[List[str]] = None,
        undetected_mode: bool = True,
        max_session_duration: int = DEFAULT_MAX_SESSION_DURATION,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        retry_delay: int = DEFAULT_RETRY_DELAY,
        timeout: Optional[int] = None,
        **kwargs,
    ):
        """
        Initialize DriverManager instance. Should only be called via get_instance.
        """
        # Prevent direct re-initialization if called incorrectly
        # Note: This basic check assumes direct calls won't happen after get_instance logic.  # noqa: E501
        # A more robust check might involve a private class variable set by get_instance.  # noqa: E501
        if hasattr(self, "_initialized") and self._initialized:
            logger.warning(
                "DriverManager already initialized. Ignoring subsequent __init__ call."
            )
            return

        # Set configuration
        # Determine project root dynamically relative to this file
        # core/chat_engine/driver_manager.py -> Need to go up 3 levels
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

        self.profile_dir = profile_dir or os.path.join(
            project_root, "runtime", "chrome_profiles", "default"
        )
        self.driver_cache_dir = driver_cache_dir or os.path.join(
            project_root, "runtime", "drivers"
        )
        self.cookie_file = cookie_file or os.path.join(
            project_root, "runtime", "cookies", "default_driver.pkl"
        )
        self.headless = headless
        self.wait_timeout = (
            timeout or wait_timeout
        )  # Use timeout if provided, else wait_timeout
        self.mobile_emulation = mobile_emulation
        self.additional_arguments = additional_arguments or []
        self.undetected_mode = undetected_mode and UNDETECTED_AVAILABLE
        self.max_session_duration = max_session_duration
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        # Store additional kwargs for future use
        self.additional_options = kwargs

        # Runtime state
        self.driver: Optional[webdriver.Chrome] = None
        self.temp_profile: Optional[str] = None
        self.session_start_time: Optional[datetime] = None

        # Create necessary directories using absolute paths
        os.makedirs(self.driver_cache_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
        if not os.path.exists(self.profile_dir) and not self.headless:
            os.makedirs(self.profile_dir, exist_ok=True)

        logger.info(
            f"DriverManager initialized: Profile='{self.profile_dir}', Headless={self.headless}, Undetected={self.undetected_mode}"  # noqa: E501
        )
        self._initialized = True

    # ---------------------------
    # Context Manager Support
    # ---------------------------
    def __enter__(self):
        self.get_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release_driver()  # Changed from quit_driver to release

    # ---------------------------
    # ChromeDriver Caching
    # ---------------------------
    def _get_cached_driver_path(self) -> str:
        return os.path.join(self.driver_cache_dir, "chromedriver.exe")

    def _download_driver_if_needed(self) -> str:
        cached_driver = self._get_cached_driver_path()
        # Basic check if driver exists and is executable
        if not os.path.exists(cached_driver) or not os.access(cached_driver, os.X_OK):
            logger.warning(
                "Cached ChromeDriver not found or not executable. Downloading/installing..."  # noqa: E501
            )
            try:
                # Use webdriver-manager to handle download and installation
                driver_path = ChromeDriverManager(path=self.driver_cache_dir).install()
                # If install just returns the path, ensure it's copied/moved if needed
                # For simplicity, assume install places it correctly or returns the final path.  # noqa: E501
                cached_driver = (
                    driver_path  # Assume install gives the final usable path
                )
                logger.info(f"ChromeDriver installed/updated at: {cached_driver}")
            except Exception as e:
                logger.error(f"Failed to download/install ChromeDriver: {e}")
                # Consider raising an exception or returning a specific error state
                raise RuntimeError(f"ChromeDriver download failed: {e}") from e
        else:
            logger.info(f"Using cached ChromeDriver: {cached_driver}")
        return cached_driver

    # ---------------------------
    # Session Management
    # ---------------------------
    def _is_session_expired(self) -> bool:
        if not self.session_start_time:
            return True
        session_duration = (datetime.now() - self.session_start_time).total_seconds()
        expired = session_duration > self.max_session_duration
        if expired:
            logger.info(f"Session expired after {session_duration:.2f} seconds")
        return expired

    # Renamed from refresh_session to be clearer
    def _renew_driver_session(self) -> bool:
        """Internal method to renew the driver session."""
        if not self.driver:
            logger.warning("No active session to renew")
            return False
        try:
            self._quit_driver_instance()  # Quit the current instance
            return bool(self.get_driver(force_new=True))  # Get a new one
        except Exception as e:
            logger.error(f"Error renewing session: {e}")
            return False

    def get_session_info(self) -> Dict[str, Any]:
        if not self.driver or not self.session_start_time:
            return {
                "status": "inactive",
                "start_time": None,
                "duration": 0,
                "expired": True,
                "headless": self.headless,
                "undetected_mode": self.undetected_mode,
            }
        duration = (datetime.now() - self.session_start_time).total_seconds()
        return {
            "status": "active",
            "start_time": self.session_start_time.isoformat(),
            "duration": duration,
            "expired": self._is_session_expired(),
            "headless": self.headless,
            "undetected_mode": self.undetected_mode,
        }

    def set_session_timeout(self, timeout: int) -> None:
        self.max_session_duration = timeout
        logger.info(f"Session timeout set to {timeout} seconds")

    # ---------------------------
    # Chrome Options Creation
    # ---------------------------
    def _create_chrome_options(self) -> Options:
        options = uc.ChromeOptions() if self.undetected_mode else Options()
        # Common arguments
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        # Prevent automatic close on quit/crash
        options.add_experimental_option("detach", True)

        for arg in self.additional_arguments:
            options.add_argument(arg)

        # Mobile emulation
        if self.mobile_emulation:
            # Simplified example - Consider making configurable
            mobile_emulation_settings = {"deviceName": "Pixel 5"}
            # Check if using standard or UC options
            if isinstance(options, Options):  # Standard Selenium Options
                options.add_experimental_option(
                    "mobileEmulation", mobile_emulation_settings
                )
            else:  # UC Options might handle it differently or need direct argument
                # UC might not directly support mobileEmulation via options object easily.  # noqa: E501
                # May need workarounds or specific arguments.
                logger.warning(
                    "Mobile emulation with undetected_chromedriver might require manual argument setup."  # noqa: E501
                )
                # Example (might not work): options.add_argument('--user-agent=...')
            logger.info("Mobile emulation requested.")

        # Profile / User Data Directory
        effective_profile_dir = self.profile_dir
        if self.headless:
            # Always use a temporary profile in headless mode to avoid conflicts
            if not self.temp_profile or not os.path.exists(self.temp_profile):
                self.temp_profile = tempfile.mkdtemp(prefix="chrome_profile_headless_")
                logger.info(
                    f"Using temporary profile for headless: {self.temp_profile}"
                )
            effective_profile_dir = self.temp_profile
            options.add_argument("--headless=new")  # Use new headless mode
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")  # Often needed for headless

        options.add_argument(f"--user-data-dir={effective_profile_dir}")
        logger.debug(f"Using user-data-dir: {effective_profile_dir}")

        # Add other potential useful arguments
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument(
            "--ignore-certificate-errors"
        )  # If dealing with local https

        return options

    # ---------------------------
    # Driver Acquisition (Main Public Method)
    # ---------------------------
    def get_driver(self, force_new: bool = False) -> webdriver.Chrome:
        """
        Retrieves the managed WebDriver instance. Creates or renews it if necessary.

        Args:
            force_new (bool): If True, forces the creation of a new driver instance,
                              discarding any existing one.

        Returns:
            webdriver.Chrome: The active WebDriver instance.

        Raises:
            RuntimeError: If the driver cannot be initialized after retries.
        """
        with self._lock:
            if self.driver and force_new:
                logger.info("Forcing new driver instance.")
                self._quit_driver_instance()  # Quit existing before creating new

            if self.driver and not self._is_session_expired():
                logger.info("Returning existing active driver instance.")
                return self.driver

            if self.driver and self._is_session_expired():
                logger.info("Session expired, renewing driver session.")
                if not self._renew_driver_session():
                    raise RuntimeError("Failed to renew expired driver session.")
                return self.driver  # Return the newly created driver

            # If no driver exists, create one
            logger.info("No active driver instance found, creating new one...")
            for attempt in range(1, self.retry_attempts + 1):
                try:
                    driver_path = self._download_driver_if_needed()
                    options = self._create_chrome_options()

                    # Use absolute path for service executable
                    service = ChromeService(
                        executable_path=os.path.abspath(driver_path)
                    )

                    if self.undetected_mode:
                        logger.info(
                            f"Launching undetected Chrome driver (Attempt {attempt})..."
                        )
                        # Pass version_main if needed by UC for specific Chrome versions
                        # version = self._get_chrome_version() # Helper needed
                        # new_driver = uc.Chrome(service=service, options=options, version_main=version)  # noqa: E501
                        new_driver = uc.Chrome(service=service, options=options)
                    else:
                        logger.info(
                            f"Launching standard Chrome driver (Attempt {attempt})..."
                        )
                        new_driver = webdriver.Chrome(service=service, options=options)

                    logger.info("Chrome driver initialized successfully.")
                    self.session_start_time = datetime.now()
                    self.driver = new_driver
                    return new_driver

                except Exception as e:
                    logger.error(f"Driver initialization attempt {attempt} failed: {e}")
                    # Clean up potentially broken instance before retry
                    if "new_driver" in locals() and new_driver:
                        try:
                            new_driver.quit()
                        except:  # noqa: E722
                            pass
                    self.driver = None  # Ensure state is clean
                    if attempt < self.retry_attempts:
                        time.sleep(self.retry_delay)
                    else:
                        logger.error("All driver initialization attempts failed.")
                        raise RuntimeError(
                            "Failed to initialize WebDriver after multiple attempts."
                        ) from e

    # ---------------------------
    # Driver Release and Cleanup (Internal)
    # ---------------------------
    def _quit_driver_instance(self) -> None:
        """Attempts to safely quit and clean up the current WebDriver instance."""
        if not self.driver:
            logger.debug("_quit_driver_instance called but no active driver exists.")
            return

        quit_success = False
        try:
            logger.info("Attempting to quit WebDriver instance...")
            self.driver.quit()
            quit_success = True
            logger.info("WebDriver quit() method called successfully.")
        except Exception as e:
            # Log specific quit error, but continue to final cleanup
            logger.warning(
                f"Error during driver.quit(): {e}. Attempting final cleanup."
            )
        finally:
            # Final cleanup attempts
            if not quit_success and self.driver:
                logger.warning(
                    "Initial driver.quit() failed or was skipped. Making final attempt."
                )
                try:
                    # This might be redundant if the first quit worked but threw an error after closing  # noqa: E501
                    # Still, worth a try to ensure closure.
                    self.driver.quit()
                    logger.info("Final driver.quit() attempt completed.")
                except Exception as final_quit_error:
                    # Log error on final attempt but don't prevent clearing the reference  # noqa: E501
                    logger.error(
                        f"Error during final driver.quit() attempt: {final_quit_error}"
                    )

            driver_ref_before_clear = self.driver
            self.driver = None

            # Check if reference was cleared and log warning if not (though assignment should guarantee it)  # noqa: E501
            # This check is mostly theoretical; if self.driver is not None here, it's a deeper Python issue.  # noqa: E501
            if self.driver is not None:
                logger.critical(
                    "CRITICAL: self.driver reference is NOT None after assignment! Potential runtime issue."  # noqa: E501
                )
            elif driver_ref_before_clear is not None:
                logger.info("Successfully cleared internal driver reference.")

            # Clean up temporary profile if used
            # Adjusted logging and path check
            temp_profile_path_to_remove = getattr(self, "temp_profile_dir", None)
            if temp_profile_path_to_remove and os.path.exists(
                temp_profile_path_to_remove
            ):
                logger.info(
                    f"Attempting to remove temporary profile directory: {temp_profile_path_to_remove}"  # noqa: E501
                )
                try:
                    shutil.rmtree(temp_profile_path_to_remove, ignore_errors=True)
                    logger.info(
                        f"Temporary profile directory removed: {temp_profile_path_to_remove}"  # noqa: E501
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to remove temporary profile directory '{temp_profile_path_to_remove}': {e}"  # noqa: E501
                    )
            elif temp_profile_path_to_remove:
                logger.debug(
                    f"Temporary profile directory path set ('{temp_profile_path_to_remove}') but directory does not exist."  # noqa: E501
                )
            else:
                logger.debug("No temporary profile directory was used or tracked.")

    def release_driver(self) -> None:
        """
        Releases the driver instance managed by this DriverManager.
        In a simple singleton, this quits the driver. In a pooled scenario,
        it would return the driver to the pool.
        """
        with self._lock:
            if self.driver:
                logger.info("Releasing driver instance...")
                self._quit_driver_instance()  # For singleton, release means quit
            else:
                logger.info("No active driver instance to release.")

    # ---------------------------
    # Cookie Management
    # ---------------------------
    def save_cookies(self) -> bool:
        if not self.driver:
            logger.warning("Driver not initialized. Cannot save cookies.")
            return False
        try:
            cookies = self.driver.get_cookies()
            # Ensure directory exists before writing
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
            with open(self.cookie_file, "wb") as f:
                pickle.dump(cookies, f)
            logger.info(f"Cookies saved to {self.cookie_file}")
            return True
        except Exception as e:
            logger.exception(f"Failed to save cookies: {e}")
            return False

    def load_cookies(self, target_url: Optional[str] = None) -> bool:
        """
        Loads cookies from the configured file. Navigates to the target URL
        (or default CHATGPT_URL) before adding cookies, as required by WebDriver.
        """
        if not self.driver:
            logger.warning("Driver not initialized. Cannot load cookies.")
            return False
        if not os.path.exists(self.cookie_file):
            logger.warning(f"No cookie file found at {self.cookie_file}")
            return False

        navigate_url = target_url or self.CHATGPT_URL

        try:
            with open(self.cookie_file, "rb") as f:
                cookies = pickle.load(f)

            # Navigate to the domain first - REQUIRED before adding cookies
            logger.info(
                f"Navigating to {navigate_url} to set cookies for the correct domain."
            )
            self.driver.get(navigate_url)
            time.sleep(2)  # Allow page to load basics

            # Add cookies one by one, handling potential issues
            added_count = 0
            for cookie in cookies:
                # Clean cookie attributes that can cause issues
                if "expiry" in cookie:
                    # Ensure expiry is integer if present
                    cookie["expiry"] = int(cookie["expiry"])
                if "sameSite" in cookie and cookie["sameSite"] not in [
                    "Strict",
                    "Lax",
                    "None",
                ]:
                    logger.warning(
                        f"Removing invalid sameSite value '{cookie['sameSite']}' from cookie '{cookie.get('name','N/A')}'"  # noqa: E501
                    )
                    del cookie["sameSite"]
                # Domain might need adjustment based on target_url vs cookie domain,
                # but often removing it works if navigating to the right base domain.
                # if 'domain' in cookie: del cookie['domain']

                try:
                    self.driver.add_cookie(cookie)
                    added_count += 1
                except Exception as cookie_ex:
                    # Log specific cookie errors but continue trying others
                    logger.warning(
                        f"Could not add cookie '{cookie.get('name','N/A')}': {cookie_ex}"  # noqa: E501
                    )

            logger.info(
                f"Attempted to load {len(cookies)} cookies, successfully added {added_count}. Refreshing page."  # noqa: E501
            )
            self.driver.refresh()  # Refresh page to apply loaded cookies
            time.sleep(2)  # Allow refresh to complete
            return True

        except Exception as e:
            logger.exception(f"Failed to load cookies: {e}")
            return False

    def clear_cookies(self) -> bool:
        if not self.driver:
            logger.warning("No active session to clear cookies")
            return False
        try:
            self.driver.delete_all_cookies()
            logger.info("Cookies cleared successfully")
            # Optionally delete the cookie file
            # if os.path.exists(self.cookie_file):
            #     os.remove(self.cookie_file)
            return True
        except Exception as e:
            logger.error(f"Error clearing cookies: {e}")
            return False

    # ---------------------------
    # Login Verification (Example for ChatGPT)
    # ---------------------------
    def is_logged_in(
        self,
        check_url: str = CHATGPT_URL,
        element_locator: tuple = (By.ID, "prompt-textarea"),  # Example locator
        retries: int = 1,  # Reduce default retries for check
    ) -> bool:
        """
        Checks if a logged-in state is detected by looking for a specific element.

        Args:
            check_url (str): The URL to navigate to for the check.
            element_locator (tuple): Selenium locator (By, value) for an element
                                     that indicates a logged-in state.
            retries (int): Number of times to retry the check.

        Returns:
            bool: True if the element is found, False otherwise.
        """
        if not self.driver:
            logger.warning("Driver not initialized.")
            return False

        for attempt in range(
            1, retries + 2
        ):  # +1 for initial try, +retries for retries
            try:
                logger.info(
                    f"Checking login status at {check_url} (Attempt {attempt})..."
                )
                self.driver.get(check_url)
                # Use a shorter timeout for checks
                WebDriverWait(self.driver, max(5, self.wait_timeout // 2)).until(
                    EC.presence_of_element_located(element_locator)
                )
                logger.info("Login check successful (element found).")
                return True
            except Exception as e:
                # Log only if it's the last attempt or for debugging
                if attempt > retries:
                    logger.warning(f"Login check failed after {attempt} attempts: {e}")
                else:
                    logger.debug(
                        f"Login check attempt {attempt} failed: {e}. Retrying..."
                    )
                    time.sleep(1)  # Short delay before retry

        return False  # Failed all attempts

    # ---------------------------
    # Retry Execution Helper
    # ---------------------------
    def execute_with_retry(
        self, action: Callable, max_retries: Optional[int] = None
    ) -> Any:
        """
        Executes a given callable action, retrying on exceptions.
        Renews the driver session if it expires during retries.
        """
        retries = max_retries if max_retries is not None else self.retry_attempts
        last_exception = None

        for attempt in range(1, retries + 2):  # Initial try + retries
            try:
                if not self.driver or self._is_session_expired():
                    logger.info(
                        "Driver missing or session expired before action. Getting/Renewing..."  # noqa: E501
                    )
                    if not self.get_driver(force_new=self._is_session_expired()):
                        raise RuntimeError(
                            "Failed to get/renew driver before action execution."
                        )

                # --- Ensure driver is available before executing ---
                if not self.driver:
                    raise RuntimeError(
                        "Driver instance is None, cannot execute action."
                    )

                return action()  # Execute the provided callable

            except Exception as e:
                last_exception = e
                logger.warning(f"Action attempt {attempt} failed: {e}")
                if attempt > retries:
                    logger.error("All action attempts failed.")
                    break  # Exit loop after final attempt fails

                # Wait before retrying
                time.sleep(self.retry_delay)

                # Check and potentially renew session before next attempt
                if self._is_session_expired():
                    logger.info("Session expired during retries, renewing...")
                    if not self._renew_driver_session():
                        logger.error(
                            "Failed to renew session during retries, aborting action."
                        )
                        break  # Stop retrying if renewal fails

        # If loop finishes due to failures, raise the last exception
        raise RuntimeError("Action failed after multiple retries.") from last_exception

    # ---------------------------
    # Scrolling Utilities
    # ---------------------------
    def scroll_into_view(self, element: webdriver.remote.webelement.WebElement) -> None:
        """Scrolls the page to bring the specified element into view."""
        if not self.driver:
            logger.warning("Driver not initialized.")
            return
        try:
            # Use JavaScript for smoother scrolling if needed
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element,
            )
            time.sleep(1)  # Allow scroll animation
            logger.info(f"Scrolled element ({element.tag_name}) into view.")
        except Exception as e:
            logger.exception(f"Failed to scroll element into view: {e}")

    def scroll_page(
        self,
        direction: str = "down",
        pixels: Optional[int] = None,
        pause_time: float = 0.5,
    ) -> None:
        """Scrolls the page down, up, or by a specific pixel amount."""
        if not self.driver:
            logger.warning("Driver not initialized.")
            return
        try:
            if pixels:
                scroll_command = f"window.scrollBy(0, {pixels});"
            elif direction == "down":
                scroll_command = "window.scrollTo(0, document.body.scrollHeight);"
            elif direction == "up":
                scroll_command = "window.scrollTo(0, 0);"
            else:
                logger.warning(f"Invalid scroll direction: {direction}")
                return

            self.driver.execute_script(scroll_command)
            time.sleep(pause_time)
            logger.debug(
                f"Scrolled page {direction} {'by ' + str(pixels) + 'px' if pixels else ''}."  # noqa: E501
            )
        except Exception as e:
            logger.exception(f"Failed to scroll page: {e}")

    def scroll_to_bottom_smoothly(
        self, scroll_pause_time: float = 1.0, max_scrolls: int = 20
    ) -> None:
        """Scrolls down the page gradually until the bottom is reached or max_scrolls is hit."""  # noqa: E501
        if not self.driver:
            logger.warning("Driver not initialized.")
            return
        logger.info("Starting smooth scroll to bottom...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0

        while scroll_count < max_scrolls:
            # Scroll down by viewport height for smoother effect
            self.driver.execute_script("window.scrollBy(0, window.innerHeight);")
            time.sleep(scroll_pause_time)

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            current_scroll = self.driver.execute_script(
                "return window.pageYOffset + window.innerHeight"
            )

            logger.debug(
                f"Scroll {scroll_count+1}: Height={new_height}, ScrolledTo={current_scroll}"  # noqa: E501
            )

            # Check if height stopped changing or if we reached the bottom
            # Add a tolerance for dynamic content loading slightly changing height
            if new_height == last_height or current_scroll >= new_height - 10:
                logger.info("Reached bottom or height stabilized.")
                break

            last_height = new_height
            scroll_count += 1

        if scroll_count == max_scrolls:
            logger.warning(
                "Reached max scrolls limit before confirming bottom of page."
            )
        else:
            logger.info("Smooth scrolling to bottom completed.")

    # ---------------------------
    # Update Options & Restart if Needed
    # ---------------------------
    def update_options(self, **new_options) -> None:
        """
        Updates DriverManager configuration options.
        Restarts the driver if options requiring it are changed.
        """
        with self._lock:
            restart_needed = False
            # Options that require a driver restart when changed
            restart_options = [
                "headless",
                "mobile_emulation",
                "undetected_mode",
                "additional_arguments",
                "profile_dir",
            ]

            logger.info(f"Updating DriverManager options: {new_options}")

            for option, value in new_options.items():
                if hasattr(self, option):
                    current_value = getattr(self, option)
                    if option in restart_options and current_value != value:
                        logger.info(
                            f"Change detected in restart-required option '{option}': '{current_value}' -> '{value}'"  # noqa: E501
                        )
                        restart_needed = True
                    setattr(self, option, value)
                    logger.debug(f"Updated option '{option}' to '{value}'")
                else:
                    # Store unknown options in additional_options for potential future use  # noqa: E501
                    self.additional_options[option] = value
                    logger.warning(
                        f"Unknown option '{option}' stored in additional_options."
                    )

            if restart_needed and self.driver:
                logger.info("Restarting driver due to option changes...")
                self._quit_driver_instance()
                # get_driver will be called automatically on next access if needed
                # Or call explicitly if immediate restart is desired:
                # self.get_driver(force_new=True)

            logger.info("DriverManager options updated successfully.")

    def shutdown(self):
        """
        Cleanly shuts down the DriverManager instance, quits the driver,
        and cleans up temporary files.
        Also attempts to kill lingering browser processes.
        """
        logger.info("Shutting down DriverManager instance...")
        with self._lock:
            self._quit_driver_instance()  # Ensure driver is quit and temp profile removed  # noqa: E501

            # Remove this specific instance from the class-level dictionary
            # Find the hash corresponding to this instance's config (may need refinement)  # noqa: E501
            # This part is complex if config can change post-init via update_options
            # For simplicity, we might just clear the entire dictionary on global shutdown  # noqa: E501
            # Or require users to manage instances explicitly if they use multiple configs.  # noqa: E501

            # Simple approach: Find hash based on current config (might not be perfect)
            current_config = {
                "profile_dir": self.profile_dir,
                "headless": self.headless,
                "cookie_file": self.cookie_file,  # Add other key config items
            }
            # Recreate hash based on current state - this is imperfect
            instance_hash = hash(frozenset(current_config.items()))
            if instance_hash in DriverManager._instances:
                logger.debug(
                    f"Removing instance with hash {instance_hash} from registry."
                )
                del DriverManager._instances[instance_hash]
            else:
                logger.warning(
                    "Could not find current instance hash in registry during shutdown."
                )

        # Force kill browsers after quitting
        self._force_kill_browsers()
        logger.info("DriverManager shutdown complete.")

    def _force_kill_browsers(self):
        """
        Internal helper to force kill browser and WebDriver processes.
        Should be used cautiously, primarily during shutdown.
        """
        import platform
        import subprocess

        logger.info("Attempting to force-kill remaining browser processes...")

        try:
            processes_to_kill = {
                "Windows": [
                    ("chromedriver.exe",),
                    ("chrome.exe",),
                    ("msedgedriver.exe",),
                    ("msedge.exe",),
                ],
                "Linux": [
                    ("pkill", "-f", "chromedriver"),
                    ("pkill", "-f", "chrome"),
                    ("pkill", "-f", "chromium"),
                ],
                "Darwin": [
                    ("pkill", "-f", "chromedriver"),
                    ("pkill", "-f", "Google Chrome"),
                    ("pkill", "-f", "Microsoft Edge"),
                ],
            }
            system = platform.system()

            if system in processes_to_kill:
                for cmd_parts in processes_to_kill[system]:
                    logger.debug(f"Running cleanup command: {' '.join(cmd_parts)}")
                    # Run with timeout and capture output to avoid hanging/spam
                    try:
                        subprocess.run(
                            cmd_parts,
                            shell=(system == "Windows"),
                            capture_output=True,
                            timeout=5,
                            check=False,
                        )
                    except subprocess.TimeoutExpired:
                        logger.warning(
                            f"Timeout expired trying to kill {' '.join(cmd_parts)}"
                        )
                    except Exception as kill_err:
                        logger.error(
                            f"Error running kill command {' '.join(cmd_parts)}: {kill_err}"  # noqa: E501
                        )
            else:
                logger.warning(
                    f"Unsupported OS '{system}' for automatic process killing."
                )

            logger.info("Browser process cleanup attempt finished.")
        except Exception as e:
            logger.error(f"Error during browser process cleanup: {e}")

    def __del__(self):
        """
        Ensure cleanup happens when the object is garbage collected,
        although explicit shutdown() is preferred.
        """
        try:
            # Check if driver exists and needs quitting (less reliable in __del__)
            if hasattr(self, "driver") and self.driver:
                self._quit_driver_instance()
            # Attempt to clean lingering processes if possible
            # self._force_kill_browsers() # Generally avoid heavy ops like this in __del__  # noqa: E501
        except Exception:
            # Suppress exceptions during garbage collection
            pass


# ---------------------------
# Example Execution (main guard)
# ---------------------------
def example_main():
    """
    Example usage function, callable externally or via __main__.
    """
    logger.info("--- DriverManager Example Start ---")

    # Get default instance
    manager_default = DriverManager.get_instance()

    # Get potentially different instance (e.g., headless)
    manager_headless = DriverManager.get_instance(
        config_key="headless_config", headless=True
    )

    try:
        # Use default manager
        with manager_default as mgr:
            driver = mgr.get_driver()
            if not driver:
                logger.error("Default driver failed to initialize.")
                return

            logger.info("Using default (non-headless) driver.")
            driver.get(mgr.CHATGPT_URL)
            time.sleep(3)

            if not mgr.is_logged_in():
                logger.warning("Manual login required for default driver...")
                # input("Press ENTER once logged in...") # Requires interaction
                # mgr.save_cookies()
            else:
                logger.info("Default driver: Already logged in.")

            mgr.scroll_to_bottom_smoothly(max_scrolls=3)
            logger.info(f"Default session info: {mgr.get_session_info()}")
            mgr.release_driver()  # Explicitly release when done with this block

        logger.info("--- Default manager block finished ---")
        time.sleep(2)

        # Use headless manager
        with manager_headless as mgr_hl:
            driver_hl = mgr_hl.get_driver()
            if not driver_hl:
                logger.error("Headless driver failed to initialize.")
                return

            logger.info("Using headless driver.")
            driver_hl.get("https://httpbin.org/ip")  # Simple check
            time.sleep(2)
            logger.info(f"Headless driver content: {driver_hl.page_source[:100]}...")
            logger.info(f"Headless session info: {mgr_hl.get_session_info()}")
            # No need to call release_driver here, __exit__ handles it

        logger.info("--- Headless manager block finished ---")

    except Exception as e:
        logger.error(f"An error occurred during the example: {e}", exc_info=True)
    finally:
        # Explicitly shutdown all instances if needed (or let __del__ handle it)
        # For explicit cleanup:
        manager_default.shutdown()
        manager_headless.shutdown()
        logger.info("--- DriverManager Example End ---")


if __name__ == "__main__":
    example_main()
