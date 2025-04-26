import os
import sys
import shutil
import time
import pickle
import tempfile
import logging
import threading
from typing import Optional, Dict, Any, List
import errno
import stat

import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------
# Logger Setup - REMOVED Custom Setup
# ---------------------------
# Rely on root logger configured elsewhere (e.g., basicConfig in main script)
logger = logging.getLogger(__name__) # Get logger instance
# Set level here if needed, but basicConfig usually covers it
# logger.setLevel(logging.INFO)

# ---------------------------
# UnifiedDriverManager Class
# ---------------------------
class UnifiedDriverManager:
    """
    Singleton class for managing an undetected Chrome WebDriver instance.
    Features:
      - Persistent profile support (or temporary profiles in headless mode)
      - Cookie saving and loading for session persistence
      - Mobile emulation and headless mode support
      - Context management for automatic cleanup
      - Ability to update driver options dynamically
    """
    _instance: Optional['UnifiedDriverManager'] = None
    _lock = threading.Lock()

    CHATGPT_URL = "https://chat.openai.com/" # Centralize URL

    # Use __new__ for singleton pattern
    def __new__(cls, *args, **kwargs) -> 'UnifiedDriverManager':
        if cls._instance is None:
            with cls._lock:
                # Double-check locking
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False 
                    cls._instance = instance
        return cls._instance

    # __init__ to set attributes only once
    def __init__(self,
                 profile_dir: Optional[str] = None,
                 driver_cache_dir: Optional[str] = None,
                 headless: bool = False,
                 cookie_file: Optional[str] = None,
                 wait_timeout: int = 15, # Default timeout
                 mobile_emulation: bool = False,
                 additional_arguments: Optional[List[str]] = None):
        
        # Ensure init runs only once per singleton instance
        if hasattr(self, '_initialized') and self._initialized:
             # Update parameters if re-initialized? Or ignore? Let's log and ignore.
             logger.debug(f"UnifiedDriverManager already initialized. Ignoring new params: headless={headless}, etc.")
             return

        with self._lock:
            # Final check inside lock
            if hasattr(self, '_initialized') and self._initialized:
                return

            # Determine paths relative to the project structure
            # Assuming this file is in src/core
            script_dir = os.path.dirname(__file__)
            project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Up two levels

            self.profile_dir = profile_dir or os.path.join(project_root, "chrome_profile", "default")
            self.driver_cache_dir = driver_cache_dir or os.path.join(project_root, "drivers")
            self.cookie_file = cookie_file or os.path.join(project_root, "cookies", "chatgpt_default.pkl") # More specific name
            
            self.headless = headless
            self.wait_timeout = wait_timeout
            self.mobile_emulation = mobile_emulation
            self.additional_arguments = additional_arguments or []
            self.driver: Optional[uc.Chrome] = None
            self.temp_profile: Optional[str] = None  # For headless mode temporary profile

            # Ensure directories exist
            os.makedirs(self.driver_cache_dir, exist_ok=True)
            # Profile dir might be created by uc.Chrome, but cookie dir needs checking
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)

            logger.info(f"UnifiedDriverManager initializing: Headless={self.headless}, Profile='{self.profile_dir if not self.headless else 'TEMP'}', Cookies='{self.cookie_file}'")
            
            # Initialize driver immediately? Or lazily in get_driver? Let's do lazy.
            # self.get_driver() # Optional: initialize on creation
            
            self._initialized = True


    # ---------------------------
    # Context Manager Support
    # ---------------------------
    def __enter__(self) -> uc.Chrome:
        """Allows using the manager with 'with' statement, returns the driver."""
        return self.get_driver()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensures driver cleanup when exiting 'with' block."""
        self.quit_driver()

    # ---------------------------
    # Driver Download and Caching
    # ---------------------------
    def _get_cached_driver_path(self) -> str:
        """Returns the expected path for the cached chromedriver."""
        return os.path.join(self.driver_cache_dir, "chromedriver.exe")

    def _download_driver_if_needed(self) -> Optional[str]:
        """Checks for cached driver, downloads if missing using webdriver-manager."""
        cached_driver = self._get_cached_driver_path()
        if not os.path.exists(cached_driver):
            logger.warning("No cached ChromeDriver found. Attempting download...")
            try:
                # Specify cache path for webdriver-manager if possible, or copy after
                driver_path = ChromeDriverManager().install()
                # If install() returns the path inside .wdm cache, we need to copy it
                # Check if the driver_path is within the desired cache_dir
                abs_cache_dir = os.path.abspath(self.driver_cache_dir)
                abs_driver_path = os.path.abspath(driver_path)
                if not abs_driver_path.startswith(abs_cache_dir):
                     # Ensure target dir exists
                     os.makedirs(os.path.dirname(cached_driver), exist_ok=True)
                     logger.info(f"Copying driver from '{driver_path}' to '{cached_driver}'")
                     shutil.copyfile(driver_path, cached_driver)
                     logger.info(f"Copied downloaded driver to cache: {cached_driver}")
                     return cached_driver
                else:
                     logger.info(f"Downloaded driver to cache: {driver_path}")
                     return driver_path # Already in target dir
            except Exception as e:
                 logger.error(f"Failed to download/cache ChromeDriver: {e}", exc_info=True)
                 return None # Indicate failure
        else:
             logger.info(f"Using cached ChromeDriver: {cached_driver}")
             return cached_driver

    # ---------------------------
    # Driver Initialization (Lazy)
    # ---------------------------
    def get_driver(self, force_new: bool = False) -> Optional[uc.Chrome]:
        """Gets the WebDriver instance. Initializes it if needed or if force_new is True."""
        with self._lock:
            if self.driver and not force_new:
                # Basic check if driver is still alive
                try:
                    _ = self.driver.window_handles # Simple command to check connection
                    logger.debug("Returning existing driver instance.")
                    return self.driver
                except Exception:
                     logger.warning("Existing driver seems dead. Reinitializing.")
                     self.driver = None # Force reinitialization

            # If forcing new or driver is None/dead, create a new one
            if self.driver is None or force_new:
                if force_new and self.driver:
                    logger.info("Forcing new driver instance...")
                    self.quit_driver() # Clean up old one first

                driver_path = self._download_driver_if_needed()
                if not driver_path:
                     logger.error("Cannot get driver: ChromeDriver executable path not found/downloaded.")
                     return None # Failed to get driver path

                options = uc.ChromeOptions()
                options.add_argument("--start-maximized")
                # Add user-specified args
                for arg in self.additional_arguments:
                    options.add_argument(arg)
                # Default args for stability/stealth
                options.add_argument("--log-level=3") # Suppress console noise
                options.add_argument("--disable-logging")
                options.add_argument("--no-first-run")
                options.add_argument("--password-store=basic") # Avoid OS prompts
                options.add_argument("--disable-blink-features=AutomationControlled")


                # Mobile emulation settings
                if self.mobile_emulation:
                    # Simplified mobile settings
                    options.add_argument("--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 13_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1")
                    logger.info("Mobile emulation enabled via User-Agent.")
                    # Note: uc.Chrome might not support add_experimental_option directly

                profile_path_to_use = self.profile_dir
                # Headless mode adjustments
                if self.headless:
                    # Create a temp profile for headless to avoid conflicts
                    if self.temp_profile and os.path.exists(self.temp_profile):
                         shutil.rmtree(self.temp_profile) # Clean up old temp profile first
                    self.temp_profile = tempfile.mkdtemp(prefix="uc_chrome_temp_")
                    profile_path_to_use = self.temp_profile
                    options.add_argument(f"--user-data-dir={profile_path_to_use}")
                    options.add_argument("--headless=new") # Modern headless
                    options.add_argument("--disable-gpu") # Often needed
                    options.add_argument("--no-sandbox") # Sometimes needed
                    options.add_argument("--disable-dev-shm-usage") # Sometimes needed
                    logger.info(f"Headless mode enabled with NEW temp profile: {profile_path_to_use}")
                else:
                     # Ensure persistent profile dir exists for non-headless
                    os.makedirs(self.profile_dir, exist_ok=True)
                    options.add_argument(f"--user-data-dir={profile_path_to_use}")
                    logger.info(f"Non-headless mode using profile: {profile_path_to_use}")


                service = ChromeService(executable_path=driver_path)
                
                logger.info("Launching undetected Chrome driver...")
                try:
                    new_driver = uc.Chrome(
                        service=service, 
                        options=options,
                        version_main=self._get_chrome_major_version() # Help uc find correct version
                    )
                    logger.info("Undetected Chrome driver initialized.")
                    self.driver = new_driver
                    
                    # Attempt to load cookies for the session if not headless
                    if not self.headless:
                         self.load_cookies() # Load cookies after driver is up

                except Exception as e:
                     logger.error(f"Failed to launch uc.Chrome: {e}", exc_info=True)
                     # Cleanup temp profile if created
                     if self.headless and self.temp_profile and os.path.exists(self.temp_profile):
                           try:
                               shutil.rmtree(self.temp_profile)
                               self.temp_profile = None
                           except Exception as cleanup_err:
                                logger.error(f"Error cleaning up temp profile during launch failure: {cleanup_err}")
                     self.driver = None # Ensure driver is None on failure
            
            return self.driver


    def _get_chrome_major_version(self) -> Optional[int]:
         """Attempts to get the installed Chrome major version for uc.Chrome."""
         try:
              # This relies on uc's internal find_chrome_executable, which might be brittle
              # Alternative: Use winreg on Windows, dpkg/rpm on Linux, plist on Mac
              executable_path = uc.find_chrome_executable()
              if not executable_path: return None
              
              # Try getting version using uc's helper if available and reliable
              # Or implement platform-specific checks
              # For now, let uc.Chrome handle it if possible, return None otherwise
              logger.debug("Skipping explicit Chrome version detection for now.")
              return None 
         except Exception as e:
              logger.warning(f"Could not determine Chrome major version: {e}")
              return None

    # ---------------------------
    # Driver Termination and Cleanup
    # ---------------------------
    def quit_driver(self):
        """Quits the driver and cleans up temporary profiles."""
        with self._lock:
            if self.driver:
                # Save cookies before quitting if not headless
                if not self.headless: 
                    self.save_cookies()

                logger.info("Quitting Chrome driver session...")
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.warning(f"Error during driver quit: {e}", exc_info=True) # Log but continue cleanup
                finally:
                    self.driver = None
                    logger.info("Driver session variable cleared.")
            
            # Cleanup temp profile if it exists
            if self.temp_profile and os.path.exists(self.temp_profile):
                logger.info(f"Cleaning up temp profile: {self.temp_profile}")
                try:
                    shutil.rmtree(self.temp_profile, onerror=_on_rm_error)
                    self.temp_profile = None
                except Exception as e:
                     logger.error(f"Error removing temp profile directory: {e}", exc_info=True)

    # ---------------------------
    # Cookie Management
    # ---------------------------
    def save_cookies(self):
        """Saves browser cookies to the specified file."""
        if not self.driver:
            logger.warning("Driver not initialized. Cannot save cookies.")
            return
        if self.headless:
             logger.debug("Skipping cookie save in headless mode (using temp profile).")
             return # Don't save cookies from temp profile normally
        try:
            cookies = self.driver.get_cookies()
            # Filter essential cookies if needed
            with open(self.cookie_file, "wb") as f:
                pickle.dump(cookies, f)
            logger.info(f"Cookies saved to {self.cookie_file}")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}", exc_info=True)

    def load_cookies(self) -> bool:
        """Loads cookies from the file into the current browser session."""
        if not self.driver:
            logger.warning("Driver not initialized. Cannot load cookies.")
            return False
        if self.headless:
             logger.debug("Skipping cookie load in headless mode (using temp profile).")
             return False # Don't load persistent cookies into temp profile
        
        cookie_path = self.cookie_file
        if not os.path.exists(cookie_path):
            logger.info(f"No cookie file found at {cookie_path}. Need to login manually first?")
            return False
        
        try:
            with open(cookie_path, "rb") as f:
                cookies = pickle.load(f)
            
            # Navigate to the domain before adding cookies
            self.driver.get(self.CHATGPT_URL) 
            time.sleep(2) # Allow page load
            
            logger.info(f"Loading {len(cookies)} cookies from {cookie_path}")
            count = 0
            for cookie in cookies:
                # Remove incompatible keys if necessary (depends on browser/driver version)
                # cookie.pop('sameSite', None) 
                try:
                     self.driver.add_cookie(cookie)
                     count += 1
                except Exception as add_err:
                     logger.warning(f"Could not add cookie: {cookie.get('name')}. Error: {add_err}")

            self.driver.refresh()
            time.sleep(3) # Allow refresh
            logger.info(f"Successfully loaded {count} cookies and refreshed session.")
            return True
        except pickle.UnpicklingError:
             logger.error(f"Error unpickling cookie file: {cookie_path}. It might be corrupt.")
             return False
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}", exc_info=True)
            return False

    # ---------------------------
    # Login Verification (using nav bar selector)
    # ---------------------------
    def is_logged_in(self, retries: int = 2) -> bool:
        """Checks if logged in by looking for the chat history nav bar."""
        if not self.driver:
            logger.warning("Driver not initialized for login check.")
            return False
            
        logger.info("Performing login check...")
        login_check_selector = 'nav[aria-label="Chat history"]' # From ResponseHandler
        
        for attempt in range(1, retries + 1):
            try:
                # Ensure we are on the correct page first
                if self.CHATGPT_URL not in self.driver.current_url:
                     self.driver.get(self.CHATGPT_URL)
                     time.sleep(3) # Wait for potential redirect

                logger.debug(f"Login check attempt {attempt}: Waiting for '{login_check_selector}'")
                WebDriverWait(self.driver, self.wait_timeout).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, login_check_selector))
                )
                logger.info("Login check successful: Chat history navigation element found.")
                return True
            except Exception as e:
                logger.warning(f"Login check attempt {attempt} failed: {e.__class__.__name__}")
                # On the last attempt, log the full error if needed
                if attempt == retries:
                     logger.warning(f"Final login check failed.", exc_info=False) # Set True for full trace
                time.sleep(2) # Wait before retry
                
        logger.warning("Login check failed after multiple attempts.")
        return False

    # --- Other methods (scroll, update_options) would go here ---
    # (Removed for brevity in this example)

    # --- Destructor to ensure cleanup ---
    # def __del__(self):
    #     """Ensure cleanup happens even if context manager isn't used."""
    #     # Removing __del__ as it can cause issues with multiprocessing/gc timing
    #     # Rely on explicit quit_driver() or context manager __exit__
    #     # self.quit_driver()

# ---------------------------
# Example Execution / Test
# ---------------------------
def main():
    """Example usage of the UnifiedDriverManager."""
    logger.info("--- Starting UnifiedDriverManager Example ---")
    
    # Initialize with desired settings (non-headless for first run)
    manager = UnifiedDriverManager(headless=False) 
    
    try:
        # Get the driver (initializes if needed)
        driver = manager.get_driver()
        if not driver:
             logger.error("Failed to get driver. Exiting.")
             return

        # Check login status
        if not manager.is_logged_in():
            logger.warning("Not logged in. Navigating to login page.")
            driver.get("https://chat.openai.com/auth/login")
            # Prompt user for manual login
            input(">> Please complete login in the browser, then press ENTER here... <<")
            # Save cookies after successful manual login
            manager.save_cookies() 
            # Verify login again after manual step
            if not manager.is_logged_in():
                 logger.error("Login still not detected after manual attempt. Exiting.")
                 return
            else:
                 logger.info("Manual login successful and detected.")
        else:
            logger.info("Already logged in based on session/cookies.")

        # Example interaction (optional)
        logger.info("Example: Fetching page title...")
        logger.info(f"Current Page Title: {driver.title}")
        time.sleep(5) # Keep browser open for a bit
        
        logger.info("✅ UnifiedDriverManager example finished successfully.")

    except Exception as e:
         logger.error(f"An error occurred during the example execution: {e}", exc_info=True)
    finally:
         # Ensure cleanup regardless of how the block exits
         manager.quit_driver() 
         logger.info("--- UnifiedDriverManager Example Complete ---")


if __name__ == "__main__":
    main() 

def _on_rm_error(func, path, exc_info):
    """Handle shutil.rmtree permission errors: retry or skip locked files."""
    # Retry once by setting write permission
    if not os.access(path, os.W_OK):
        try:
            os.chmod(path, stat.S_IWUSR)
            func(path)
        except Exception:
            logger.warning(f"Could not delete locked path: {path}")
    else:
        logger.warning(f"Skipping deletion error for path: {path}") 
