"""
Bridge Integrity Monitor

Periodically checks critical configuration files and paths for the 
THEA-Cursor bridge agent and logs anomalies.
"""

import logging
import time
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Adjust path to import AppConfig if needed, assuming it's accessible
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

try:
    from src.dreamos.core.config import AppConfig, load_config, ConfigurationError
except ImportError:
    print("CRITICAL: Cannot import AppConfig/load_config. Ensure src directory is in PYTHONPATH.")
    # Define dummy classes/functions if needed for basic structure, though checks will fail
    class AppConfig:
        pass
    def load_config():
        raise ConfigurationError("Dummy load_config cannot function.")
    class ConfigurationError(Exception):
        pass

# Logging Setup
LOG_FILE = project_root / "runtime" / "logs" / "bridge_integrity_monitor.md"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BridgeIntegrityMonitor")

# File handler for markdown log
# Ensure log directory exists
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.INFO)
# Simple format for markdown - actual logging content controls format
md_formatter = logging.Formatter('%(message)s') # Just log the message directly
file_handler.setFormatter(md_formatter)
# Add handler to logger used for markdown logging
md_logger = logging.getLogger("BridgeIntegrityMarkdownLogger")
md_logger.addHandler(file_handler)
md_logger.setLevel(logging.INFO)
md_logger.propagate = False # Prevent duplication to console/root logger

# Constants
CHECK_INTERVAL_SECONDS = 300 # 5 minutes
MAX_CONSECUTIVE_FAILURES = 3

# State
consecutive_failures: Dict[str, int] = {}

def log_anomaly(check_name: str, message: str, is_failure: bool = True):
    """Logs an anomaly to console and the markdown file."""
    global consecutive_failures
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_level = logging.ERROR if is_failure else logging.WARNING
    
    logger.log(log_level, f"Check '{check_name}': {message}")
    
    md_log_entry = f"*   **{timestamp}** - **Check:** `{check_name}` - **Status:** {'FAIL' if is_failure else 'WARN'} - **Details:** {message}\n"
    md_logger.info(md_log_entry) # Use the dedicated markdown logger

    if is_failure:
        consecutive_failures[check_name] = consecutive_failures.get(check_name, 0) + 1
        if consecutive_failures[check_name] >= MAX_CONSECUTIVE_FAILURES:
            escalation_message = f"Check '{check_name}' failed {consecutive_failures[check_name]} consecutive times. Escalation required!"
            logger.critical(escalation_message)
            md_logger.info(f"    - **ESCALATION:** {escalation_message}\n")
            # Placeholder for actual escalation action (e.g., sending alert)
            # Reset counter after escalation log
            consecutive_failures[check_name] = 0 
    else:
        # Reset counter on success/warning
        if check_name in consecutive_failures:
            if consecutive_failures[check_name] > 0:
                 logger.info(f"Check '{check_name}' succeeded after {consecutive_failures[check_name]} failures. Resetting counter.")
                 md_logger.info(f"    - **INFO:** Check '{check_name}' resolved after previous failures.\n")
            consecutive_failures[check_name] = 0

def check_bridge_mode_config():
    """Checks the bridge_mode.json file."""
    check_name = "bridge_mode_config"
    config_file = project_root / "runtime" / "config" / "bridge_mode.json"
    if not config_file.exists():
        log_anomaly(check_name, f"File not found: {config_file}")
        return
    try:
        with open(config_file, 'r') as f:
            data = json.load(f)
        mode = data.get("mode")
        if mode not in ["gui", "scraper", "hybrid"]:
            log_anomaly(check_name, f"Invalid mode '{mode}' found in {config_file}. Allowed: gui, scraper, hybrid.")
        else:
            logger.info(f"Check '{check_name}': OK (Mode: {mode})")
            # Reset failure counter on success
            log_anomaly(check_name, f"Mode '{mode}' is valid.", is_failure=False)
    except json.JSONDecodeError as e:
        log_anomaly(check_name, f"JSON decode error in {config_file}: {e}")
    except Exception as e:
        log_anomaly(check_name, f"Error reading {config_file}: {e}")

def check_chatgpt_cookies():
    """Checks for the chatgpt_cookies.json file (presence only)."""
    check_name = "chatgpt_cookies"
    # Path depends on ChatGPTScraper internal logic or AppConfig
    # Assume path from AppConfig if possible, otherwise hardcode default
    cookie_file = project_root / "runtime" / "config" / "chatgpt_cookies.json"
    # TODO: Improve this by loading AppConfig if available to get the actual path
    
    if not cookie_file.exists():
        # This might be normal before first scraper run/login
        log_anomaly(check_name, f"Cookie file not found: {cookie_file}. This may be normal before first scraper login.", is_failure=False) # Log as WARN
    else:
        logger.info(f"Check '{check_name}': OK (File exists: {cookie_file})")
        log_anomaly(check_name, f"File exists: {cookie_file}.", is_failure=False)

def check_config_yaml_paths(config: Optional[AppConfig]):
    """Checks critical paths defined within config.yaml via AppConfig."""
    check_name = "config_yaml_paths"
    if not config:
        log_anomaly(check_name, "AppConfig could not be loaded. Cannot check paths.")
        return

    required_paths: List[Path] = []
    if config.paths:
        if config.paths.gui_snippets:
             # Resolve the path based on project root stored in config
             try: 
                 gui_path = config.paths.resolve_relative_path("gui_snippets")
                 required_paths.append(gui_path)
             except Exception as e:
                  log_anomaly(check_name, f"Error resolving gui_snippets path: {e}")
        else:
             log_anomaly(check_name, "Config paths.gui_snippets is not defined.")
    else:
        log_anomaly(check_name, "Config 'paths' section is missing.")
        return # Cant check further

    all_ok = True
    for path in required_paths:
        if not path.exists():
            log_anomaly(check_name, f"Required path does not exist: {path}")
            all_ok = False
        elif not path.is_dir(): # Assuming gui_snippets should be a directory
            log_anomaly(check_name, f"Path exists but is not a directory: {path}")
            all_ok = False
        else:
             logger.debug(f"Path OK: {path}")
             
    if all_ok:
        logger.info(f"Check '{check_name}': OK")
        log_anomaly(check_name, "Required paths exist.", is_failure=False)

def watchdog_loop():
    """Main watchdog loop."""
    logger.info("Starting Bridge Integrity Monitor watchdog loop.")
    while True:
        logger.info("Running integrity checks...")
        
        # Try to load config for path checks
        app_config: Optional[AppConfig] = None
        try:
            app_config = load_config()
        except ConfigurationError as e:
            log_anomaly("app_config_load", f"Failed to load AppConfig: {e}")
        except Exception as e:
            log_anomaly("app_config_load", f"Unexpected error loading AppConfig: {e}")

        # Run checks
        check_bridge_mode_config()
        check_chatgpt_cookies()
        check_config_yaml_paths(app_config)
        
        logger.info(f"Integrity checks complete. Sleeping for {CHECK_INTERVAL_SECONDS} seconds.")
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    try:
        watchdog_loop()
    except KeyboardInterrupt:
        logger.info("Bridge Integrity Monitor stopped by user.")
    except Exception as e:
        logger.critical(f"Bridge Integrity Monitor encountered fatal error: {e}", exc_info=True) 