# unified_driver_manager.py

import os
import sys
import shutil
import time
import pickle
import tempfile
import logging
import threading
from typing import Optional, Dict, Any, List

import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import SessionNotCreatedException, TimeoutException

# ---------------------------
# Logger Setup
# ---------------------------
def setup_logger(name="UnifiedDriverManager",
                 log_dir: str = os.path.join(os.getcwd(), "logs", "core")) -> logging.Logger:
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    file_path = os.path.join(log_dir, f"{name}.log")
    fh = logging.FileHandler(file_path)
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    if not logger.hasHandlers():
        logger.addHandler(fh)
        logger.addHandler(sh)
    return logger

logger = setup_logger()


class UnifiedDriverManager:
    """
    Singleton for managing an undetected Chrome WebDriver with:
      - self‑healing retry logic
      - cached driver download
      - headless vs persistent profiles
      - cookie persistence
      - mobile emulation
      - context‑manager support
    """
    _instance: Optional['UnifiedDriverManager'] = None
    _lock = threading.Lock()
    CHATGPT_URL = "https://chat.openai.com/"

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._initialized = False
                cls._instance = inst
        return cls._instance

    def __init__(self,
                 profile_dir: Optional[str] = None,
                 driver_cache_dir: Optional[str] = None,
                 headless: bool = False,
                 cookie_file: Optional[str] = None,
                 wait_timeout: int = 10,
                 mobile_emulation: bool = False,
                 additional_arguments: Optional[List[str]] = None):
        with self._lock:
            if getattr(self, "_initialized", False):
                return

            cwd = os.getcwd()
            self.profile_dir = profile_dir or os.path.join(cwd, "chrome_profile", "default")
            self.driver_cache_dir = driver_cache_dir or os.path.join(cwd, "drivers")
            self.cookie_file = cookie_file or os.path.join(cwd, "cookies", "default.pkl")
            self.headless = headless
            self.wait_timeout = wait_timeout
            self.mobile_emulation = mobile_emulation
            self.additional_arguments = additional_arguments or []

            self.driver = None
            self.temp_profile = None

            os.makedirs(self.driver_cache_dir, exist_ok=True)
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)

            logger.info(f"Initialized: Headless={self.headless}, Mobile={self.mobile_emulation}, "
                        f"Profile={'temp' if self.headless else self.profile_dir}")
            self._initialized = True

    # Context‑manager
    def __enter__(self):
        logger.debug("Entering context: getting driver")
        self.get_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.debug("Exiting context: quitting driver")
        self.quit_driver()
        return False

    # ---------------------------
    # Driver Initialization
    # ---------------------------
    # Core: get or (re)create driver with retry
    def get_driver(self, force_new: bool = False):
        with self._lock:
            if self.driver and not force_new:
                return self.driver
            if self.driver and force_new:
                self.quit_driver()

            opts = uc.ChromeOptions()
            opts.add_argument("--start-maximized")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_argument("--disable-infobars")
            opts.add_argument("--disable-extensions")
            for a in self.additional_arguments:
                opts.add_argument(a)

            if self.mobile_emulation:
                opts.add_experimental_option("mobileEmulation", {"deviceName": "iPhone X"})
                logger.info("Mobile emulation ON")

            profile_dir = None
            if self.headless:
                if self.temp_profile and os.path.exists(self.temp_profile):
                    shutil.rmtree(self.temp_profile, ignore_errors=True)
                self.temp_profile = tempfile.mkdtemp(prefix="uc_chrome_profile_")
                profile_dir = self.temp_profile
                opts.add_argument(f"--user-data-dir={profile_dir}")
                opts.add_argument("--headless=new")
                opts.add_argument("--no-sandbox")
                opts.add_argument("--disable-dev-shm-usage")
                opts.add_argument("--disable-gpu")
                logger.info(f"Headless ON (temp profile: {profile_dir})")
            else:
                profile_dir = self.profile_dir
                os.makedirs(profile_dir, exist_ok=True)
                opts.add_argument(f"--user-data-dir={profile_dir}")
                logger.info(f"Headful ON (profile: {profile_dir})")

            last_exc = None
            for attempt in range(1, 3):
                try:
                    logger.info(f"Launch attempt {attempt} using uc.Chrome internal driver handling")
                    
                    # ---> Specify main browser version explicitly <--- 
                    # Ensure this matches your installed Chrome version!
                    chrome_major_version = 135 
                    driver = uc.Chrome(options=opts, version_main=chrome_major_version)
                    
                    self.driver = driver
                    logger.info(f"Successfully launched uc.Chrome (version_main={chrome_major_version})")
                    return driver
                except SessionNotCreatedException as e:
                    logger.warning(f"SessionNotCreatedException: {e}")
                    last_exc = e
                    if attempt < 2:
                        self._delete_cached_driver()
                        time.sleep(2)
                    else:
                        logger.critical("Persistent driver creation error")
                except Exception as e:
                    logger.error(f"Unexpected launch error: {e}", exc_info=True)
                    last_exc = e
                    break

            raise last_exc or RuntimeError("Failed to initialize WebDriver after retries")

    # Quit + cleanup
    def quit_driver(self):
        with self._lock:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.warning(f"Error quitting driver: {e}")
                finally:
                    self.driver = None
                    logger.info("Driver closed")
            if self.temp_profile and os.path.isdir(self.temp_profile):
                try:
                    shutil.rmtree(self.temp_profile, ignore_errors=True)
                    logger.info("Cleaned headless temp profile")
                except Exception as e:
                    logger.error(f"Error cleaning temp profile: {e}")
                self.temp_profile = None

    # Cookie ops
    def save_cookies(self):
        if not self.driver:
            logger.warning("No driver: cannot save cookies")
            return
        if self.headless:
            logger.warning("Headless mode: temp profile—cookies ephemeral")
        try:
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
            with open(self.cookie_file, "wb") as f:
                pickle.dump(self.driver.get_cookies(), f)
            logger.info(f"Cookies saved to {self.cookie_file}")
        except Exception as e:
            logger.exception(f"save_cookies failed: {e}")

    def load_cookies(self) -> bool:
        if not self.driver:
            logger.warning("No driver: cannot load cookies")
            return False
        if not os.path.isfile(self.cookie_file):
            logger.warning(f"No cookie file at {self.cookie_file}")
            return False
        try:
            with open(self.cookie_file, "rb") as f:
                cookies = pickle.load(f)
            self.driver.get(self.CHATGPT_URL)
            time.sleep(2)
            loaded = 0
            for c in cookies:
                c.pop("sameSite", None)
                try:
                    self.driver.add_cookie(c)
                    loaded += 1
                except Exception:
                    logger.debug(f"Skipped cookie: {c.get('name')}")
            logger.info(f"Loaded {loaded}/{len(cookies)} cookies")
            self.driver.refresh()
            time.sleep(2)
            return True
        except Exception as e:
            logger.exception(f"load_cookies failed: {e}")
            return False

    # Login check
    def is_logged_in(self, retries: int = 1) -> bool:
        # ---> Use the more robust nav selector <--- 
        # sel = 'textarea[id="prompt-textarea"]'
        sel = 'nav[aria-label="Chat history"]' 
        for i in range(retries):
            try:
                if not self.driver.current_url.startswith(self.CHATGPT_URL):
                    self.driver.get(self.CHATGPT_URL)
                    time.sleep(2)
                # ---> Wait for visibility of the element <--- 
                WebDriverWait(self.driver, self.wait_timeout).until(
                    # EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                    EC.visibility_of_element_located((By.CSS_SELECTOR, sel))
                )
                logger.info("Login check successful (nav element found).") # Updated log
                return True
            except TimeoutException:
                logger.info(f"is_logged_in attempt {i+1} failed")
            except Exception as e:
                logger.warning(f"is_logged_in error: {e}")
            time.sleep(2)
        return False

    # Scrolling
    def scroll_into_view(self, element):
        if not self.driver: return
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", element)
            time.sleep(1)
        except Exception as e:
            logger.debug(f"scroll_into_view error: {e}")

    def manual_scroll(self, scroll_pause_time: float = 1.0, max_scrolls: int = 10):
        if not self.driver: return
        last = self.driver.execute_script("return document.body.scrollHeight")
        for _ in range(max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)
            new = self.driver.execute_script("return document.body.scrollHeight")
            if new == last:
                break
            last = new

    # Update options at runtime
    def update_options(self, new_opts: Dict[str, Any]):
        with self._lock:
            if "headless" in new_opts:
                self.headless = new_opts["headless"]
            if "mobile_emulation" in new_opts:
                self.mobile_emulation = new_opts["mobile_emulation"]
            if "additional_arguments" in new_opts:
                self.additional_arguments.extend(new_opts["additional_arguments"])
            logger.info(f"Options updated: {new_opts}")
            self.quit_driver()
            self.get_driver(force_new=True)

    def __del__(self):
        self.quit_driver()


# Example usage (for manual testing only)
def main():
    with UnifiedDriverManager(headless=True) as mgr:
        drv = mgr.get_driver()
        if not mgr.is_logged_in():
            print("Please log in manually, then hit ENTER.")
            input()
            mgr.save_cookies()
        mgr.manual_scroll(max_scrolls=3)
        time.sleep(5)

if __name__ == "__main__":
    main()
