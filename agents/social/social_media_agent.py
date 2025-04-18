import logging
import os
import json
import time
import random
import threading
# Removed queue import as message queue logic is replaced by AgentBus
# from queue import Queue, Empty
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
# Removed traceback import, relying on logger
# import traceback
from core.coordination.agent_bus import AgentBus # CANONICAL IMPORT
# Removed AgentStatus as it's not used here, replaced by EventType
# from core.coordination.bus_types import AgentStatus
from core.coordination.dispatcher import Event, EventType # NEW: Canonical Event model

# Updated import paths
from utils.browser_utils import get_undetected_driver
# from utils.content.post_context_generator import generate_context_from_governance # Assuming this exists and is correct
# Placeholder for context generation and template rendering - replace with actual imports if needed
def generate_context_from_governance(): return {"event_type": "PLACEHOLDER", "title": "Placeholder Title"}
def render_template(template_name, context): return f"Rendered: {template_name} with {context.get('title')}"
# Assume setup_logging is used elsewhere or handled globally
# from utils.logging_utils import setup_logging, log_event # Assuming log_event exists
# Placeholder for log_event - replace with actual import
def log_event(event_name, agent_id, details): logger.info(f"LOG_EVENT::{event_name} - {agent_id} - {details}")

# from utils.cursor_utils import export_prompt_for_cursor, CURSOR_QUEUE_DIR # cursor_utils may need review/relocation
# Placeholder for cursor util - replace with actual import
def export_prompt_for_cursor(payload): return f"/path/to/exported/{payload.get('objective', 'default')}.prompt"

from utils.feedback_processor import process_feedback # Updated path
# from strategies import FacebookStrategy, TwitterStrategy, LinkedInStrategy, RedditStrategy # Import from core.strategies now
# Assume strategies are correctly imported and instantiated (removed importlib logic for simplicity here)
from core.strategies import FacebookStrategy, TwitterStrategy, LinkedInStrategy # RedditStrategy maybe not implemented
# from strategy_exceptions import StrategyError, LoginError, PostError, ScrapeError, AuthenticationError, RateLimitError, ContentError
from core.exceptions.strategy_exceptions import StrategyError, LoginError, PostError, ScrapeError, AuthenticationError, RateLimitError, ContentError # Updated path
import importlib # Keep importlib if dynamic loading is still desired

# Define constants or import from core.constants
from core.constants import AGENT_ID_SOCIAL_MEDIA as AGENT_ID # Assuming constant exists
# Define placeholder paths if not in constants
DEFAULT_USER_DATA_DIR = "run/user_data/social"
CURSOR_QUEUE_DIR = "run/cursor_queue"
CONFIG_FILE = "config/social_media_config.json"
STRATEGIES_PACKAGE = "core.strategies" # Define package for dynamic loading
DEFAULT_MAX_MENTIONS = 20
LOG_SNIPPET_LENGTH = 100

logger = logging.getLogger(__name__)

# Removed old MSG_TYPE constants, will use EventType enum

class SocialMediaAgent:
    # Define default settings structure
    DEFAULT_CONFIG = {
        "common_settings": {
            "timeout_seconds": 30,
            "max_mentions": 20,
            "max_community_posts": 20,
            "log_snippet_length": 100,
        },
        "twitter": {
            "username": None,
            "password": None,
            "verification_email": None, # Or phone
            # Add other twitter-specific defaults here
        },
        "reddit": {
            "username": None,
            "password": None,
            "client_id": None, # Example API key default
            "client_secret": None,
             # Add other reddit-specific defaults here
       },
        "linkedin": {
            "username": None,
            "password": None,
             # Add other linkedin-specific defaults here
       },
       "facebook": {
            "username": None,
            "password": None,
             # Add other facebook-specific defaults here
       },
       "instagram": {
            "username": None,
            "password": None,
             # Add other instagram-specific defaults here
       },
        # Add sections for other platforms as needed
    }

    def __init__(self, agent_bus: AgentBus, config_path=CONFIG_FILE, user_data_dir=DEFAULT_USER_DATA_DIR):
        """Initializes the agent, loads config, registers with AgentBus."""
        self.agent_id = AGENT_ID
        self.bus = agent_bus # Store AgentBus instance
        self.config = self._load_config(config_path)
        self.user_data_dir = user_data_dir
        self.driver = None
        self.strategies = {} # Strategy instances will be loaded dynamically

        # Map EventType enum values (or their string representations) to handler methods
        # Assumes EventType has members like POST_CONTENT, GET_ANALYTICS, etc.
        # Using string keys for broader compatibility initially, map to EventType enums if available/required by bus
        self.COMMAND_HANDLERS = {
            EventType.POST_CONTENT.name: self._handle_post_command,
            EventType.GET_ANALYTICS.name: self._handle_get_analytics_command,
            EventType.AGENT_LOGIN.name: self._handle_login_command, # Assuming EventType.AGENT_LOGIN
            EventType.CHECK_AGENT_LOGIN_STATUS.name: self._handle_check_login_status_command, # Assuming EventType.CHECK_AGENT_LOGIN_STATUS
            # Specific scrape commands might be handled via GET_ANALYTICS type with payload differentiation
            # 'scrape_mentions': self._handle_scrape_mentions_command, # Merged into GET_ANALYTICS
            # 'scrape_trends': self._handle_scrape_trends_command, # Merged into GET_ANALYTICS
            # 'scrape_community': self._handle_scrape_community_command, # Merged into GET_ANALYTICS
            EventType.GET_AGENT_STATUS.name: self._handle_agent_status_command, # Assuming EventType.GET_AGENT_STATUS
            EventType.REQUEST_CURSOR_ACTION.name: self._handle_request_cursor_action_command, # Assuming EventType.REQUEST_CURSOR_ACTION
            EventType.PROCESS_FEEDBACK_ITEM.name: self._handle_process_feedback_item_command, # Assuming EventType.PROCESS_FEEDBACK_ITEM
        }

        # Register agent and message handler with AgentBus
        # Registering capabilities might be useful for discovery
        self.bus.register_agent(self.agent_id, capabilities=["social_media_posting", "social_media_scraping"])
        # Register a single handler for events directed to this agent
        # The bus dispatcher should route events with target_id=self.agent_id here
        self.bus.register_handler(self.agent_id, self.handle_bus_event) # Renamed handler method

        log_event("AGENT_INIT", self.agent_id, {"status": "initialized", "registered_handlers": list(self.COMMAND_HANDLERS.keys())})

    def _load_config(self, config_path):
        """Loads configuration with defaults, JSON file, and environment variable overrides."""
        # 1. Start with deep copy of defaults
        import copy
        final_config = copy.deepcopy(self.DEFAULT_CONFIG)
        log_event("AGENT_CONFIG_LOAD", self.agent_id, {"step": "Defaults loaded"})

        # 2. Load base config from JSON file
        base_config = {}
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                base_config = json.load(f)
            log_event("AGENT_CONFIG_LOAD", self.agent_id, {"step": "JSON file loaded", "path": config_path})
        except FileNotFoundError:
            log_event("AGENT_WARNING", self.agent_id, {"warning": "Config file not found, using defaults + env vars", "path": config_path})
        except json.JSONDecodeError as e:
            log_event("AGENT_ERROR", self.agent_id, {"error": f"Invalid JSON in config file: {e}. Using defaults + env vars.", "path": config_path})
        except Exception as e:
            log_event("AGENT_ERROR", self.agent_id, {"error": f"Failed to load config file: {e}. Using defaults + env vars.", "path": config_path, "details": str(e)})

        # 3. Merge base_config into final_config (deep merge needed for nested dicts)
        def deep_merge_dicts(source, destination):
            """Recursively merge source dict into destination dict."""
            for key, value in source.items():
                if isinstance(value, dict):
                    node = destination.setdefault(key, {})
                    deep_merge_dicts(value, node)
                else:
                    destination[key] = value
            return destination

        if base_config:
            final_config = deep_merge_dicts(base_config, final_config)
            log_event("AGENT_CONFIG_LOAD", self.agent_id, {"step": "JSON config merged"})
            
        # 4. Apply Environment Variable Overrides
        overridden_keys = []
        for section_key, section_value in final_config.items():
            if isinstance(section_value, dict):
                for setting_key in section_value:
                    env_var_name = f"{section_key.upper()}_{setting_key.upper()}"
                    env_var_value = os.environ.get(env_var_name)
                    
                    if env_var_value is not None:
                        original_value = final_config[section_key][setting_key]
                        default_type = type(self.DEFAULT_CONFIG.get(section_key, {}).get(setting_key))
                        try:
                            if default_type is bool:
                                converted_value = env_var_value.lower() in ('true', '1', 'yes')
                            elif default_type is int:
                                converted_value = int(env_var_value)
                            elif default_type is float:
                                converted_value = float(env_var_value)
                            else: # Assume string or NoneType
                                converted_value = env_var_value
                        except ValueError:
                            log_event("AGENT_WARNING", self.agent_id, {"warning": f"Failed to convert env var {env_var_name} ('{env_var_value}') to type {default_type}. Using raw string.", "key": f"{section_key}.{setting_key}"})
                            converted_value = env_var_value
                            
                        final_config[section_key][setting_key] = converted_value
                        if converted_value != original_value:
                             overridden_keys.append(f"{section_key}.{setting_key}")
                             
        if overridden_keys:
             log_event("AGENT_CONFIG_OVERRIDE", self.agent_id, {"overridden_keys": overridden_keys})
             
        # 5. Validation (Optional - Example)
        required_platform_keys = {
             'twitter': ['username', 'password'],
             'reddit': ['username', 'password'], # Add client_id/secret if using API later
             'linkedin': ['username', 'password'],
             'facebook': ['username', 'password'],
             'instagram': ['username', 'password']
        }
        missing_critical_keys = []
        for platform, keys in required_platform_keys.items():
            platform_config = final_config.get(platform, {})
            # Check requirements only if platform seems intended for use (e.g., has a username set)
            if platform_config.get('username'): 
                 for key in keys:
                      if not platform_config.get(key):
                           missing_critical_keys.append(f"{platform}.{key}")
                           
        if missing_critical_keys:
             log_event("AGENT_CRITICAL", self.agent_id, {"error": "Missing critical configuration values after load/override", "missing_keys": missing_critical_keys})
             # Depending on severity, either raise an error or allow to proceed with limited function
             raise ValueError(f"Missing critical configuration: {missing_critical_keys}")
             
        log_event("AGENT_CONFIG_LOAD", self.agent_id, {"step": "Final config ready"})
        return final_config

    def _initialize_driver(self):
        # Ensure driver is initialized only once
        if self.driver is None:
            # print("[SocialMediaAgent] Initializing browser driver...")
            log_event("AGENT_STEP", self.agent_id, {"step": "initialize_driver"})
            try:
                self.driver = get_undetected_driver(user_data_dir=self.user_data_dir)
                if self.driver is None:
                     raise RuntimeError("get_undetected_driver returned None.")
                # print("[SocialMediaAgent] Browser driver initialized successfully.")
            except Exception as e:
                 # print(f"[SocialMediaAgent] CRITICAL: Failed to initialize browser driver: {e}")
                 log_event("AGENT_ERROR", self.agent_id, {"error": "Driver initialization failed", "details": str(e)})
                 self.driver = None # Ensure driver is None on failure
                 raise # Re-raise the exception to potentially halt execution if driver is critical
        return self.driver

    def _get_or_load_strategy(self, platform_name: str):
        """Gets the strategy instance for the platform, loading it if necessary."""
        if platform_name in self.strategies:
            # print(f"[SocialMediaAgent] Using existing strategy instance for: {platform_name}")
            return self.strategies[platform_name]

        # print(f"[SocialMediaAgent] Attempting to load strategy for: {platform_name}...")
        strategy_module_name = f"{platform_name}_strategy"
        strategy_class_name = f"{platform_name.capitalize()}Strategy"
        full_module_path = f"{STRATEGIES_PACKAGE}.{strategy_module_name}"

        try:
            # Dynamically import the strategy module
            strategy_module = importlib.import_module(full_module_path)
            strategy_class = getattr(strategy_module, strategy_class_name)

            # Initialize driver if needed (only the first time a strategy requiring it is loaded)
            # Note: Strategies needing the driver should handle potential None driver if init fails
            driver_instance = None
            # Check if the strategy likely needs a driver (can be refined)
            # A simple check could be if it inherits from a base class that uses it,
            # or inspecting __init__ signature, but this is complex.
            # For now, we initialize it defensively if ANY strategy is loaded.
            # A better approach might be needed if some strategies are API-only.
            try:
                driver_instance = self._initialize_driver()
            except RuntimeError as driver_e:
                # print(f"[SocialMediaAgent] Warning: Driver initialization failed during strategy load for {platform_name}: {driver_e}. Strategy might not function.")
                log_event("AGENT_WARNING", self.agent_id, {"warning": "Driver init failed during strategy load", "platform": platform_name, "details": str(driver_e)})
                # Allow strategy loading to continue if driver is optional for it

            # Instantiate the strategy
            strategy_instance = strategy_class(self.config, driver_instance)
            self.strategies[platform_name] = strategy_instance # Store the instance
            # print(f"[SocialMediaAgent] Successfully loaded and initialized strategy for: {platform_name}")
            log_event("STRATEGY_LOADED", self.agent_id, {"platform": platform_name})
            return strategy_instance

        except ModuleNotFoundError:
            # print(f"[SocialMediaAgent] Error: Strategy module '{full_module_path}' not found.")
            log_event("AGENT_ERROR", self.agent_id, {"error": "Strategy module not found", "platform": platform_name, "module": full_module_path})
        except AttributeError:
            # print(f"[SocialMediaAgent] Error: Strategy class '{strategy_class_name}' not found in '{full_module_path}'.")
            log_event("AGENT_ERROR", self.agent_id, {"error": "Strategy class not found", "platform": platform_name, "class": strategy_class_name})
        except Exception as e:
            # print(f"[SocialMediaAgent] Error loading strategy for {platform_name}: {e}\n{traceback.format_exc()}")
            log_event("AGENT_ERROR", self.agent_id, {"error": "Strategy loading failed", "platform": platform_name, "details": str(e)})
            
        return None # Return None on failure

    # +++ NEW HELPER METHOD +++
    def _execute_strategy_action(self, platform_name: str, action_name: str, required_method_name: str | None = None, default_return_on_error: any = False, action_args: tuple = (), action_kwargs: dict = {}):
        """
        Helper to execute a method on a loaded strategy with common error handling.
        Now catches specific StrategyError subclasses.
        """
        method_to_call = required_method_name or action_name
        log_event(f"AGENT_ACTION_START", self.agent_id, {"action": action_name, "platform": platform_name, "method": method_to_call, "args": action_args, "kwargs": action_kwargs})

        strategy = self._get_or_load_strategy(platform_name)
        if not strategy:
            log_event("AGENT_ACTION_ERROR", self.agent_id, {"action": action_name, "platform": platform_name, "error": "Strategy loading failed"})
            return default_return_on_error, "Strategy loading failed"

        if not hasattr(strategy, method_to_call):
            log_event("AGENT_WARNING", self.agent_id, {"warning": f"Strategy does not support method '{method_to_call}'", "platform": platform_name, "action": action_name})
            log_event("AGENT_ACTION_ERROR", self.agent_id, {"action": action_name, "platform": platform_name, "error": "Method not supported by strategy"})
            return default_return_on_error, "Method not supported by strategy"

        try:
            strategy_method = getattr(strategy, method_to_call)
            result = strategy_method(*action_args, **action_kwargs)
            log_event(f"AGENT_ACTION_SUCCESS", self.agent_id, {"action": action_name, "platform": platform_name, "result_type": type(result).__name__})
            return result, None
        except (AuthenticationError, LoginError, PostError, ScrapeError, RateLimitError, ContentError, StrategyError) as strat_e:
            error_type_name = type(strat_e).__name__
            error_details = f"{error_type_name} during {action_name}"
            log_level = "AGENT_WARNING" if isinstance(strat_e, (RateLimitError, ContentError)) else "AGENT_ERROR"
            log_event(log_level, self.agent_id, {"error": error_details, "action": action_name, "platform": platform_name, "exception_type": error_type_name, "details": str(strat_e)})
            log_event("AGENT_ACTION_ERROR", self.agent_id, {"action": action_name, "platform": platform_name, "error": error_details, "exception": str(strat_e)})
            return default_return_on_error, f"{error_details}: {str(strat_e)}"
        except Exception as e:
            error_details = f"Unexpected error executing strategy method '{method_to_call}'"
            log_event("AGENT_CRITICAL", self.agent_id, {"error": error_details, "action": action_name, "platform": platform_name, "exception_type": type(e).__name__, "details": str(e)})
            log_event("AGENT_ACTION_ERROR", self.agent_id, {"action": action_name, "platform": platform_name, "error": error_details, "exception": str(e)})
            return default_return_on_error, f"{error_details}: {str(e)}"
    # +++ END HELPER METHOD +++

    def login(self, platform_name: str):
        """Logs into the specified platform using its strategy. Returns (success_flag, error_message_or_none)."""
        result, error_msg = self._execute_strategy_action(
            platform_name=platform_name,
            action_name='login',
            default_return_on_error=False
        )
        # Assuming strategy's login returns True on success
        return bool(result), error_msg

    def _generate_post_content(self, platform_name: str) -> tuple[str | None, dict | None]:
        """Generates post text using governance context and templates."""
        # print(f"[{self.agent_id}] Generating post content for {platform_name} from governance context...")
        context = generate_context_from_governance()
        if not context or not isinstance(context, dict):
            # print(f"[{self.agent_id}] Warning: Received invalid context from governance: {context}")
            log_event("AGENT_WARNING", self.agent_id, {"warning": "Invalid context received", "context": context})
            return None, None # Return None for text and context

        template_name = "social/generic_event.j2"
        event_type = context.get("event_type", "GENERIC_EVENT").lower()
        
        # --- Template Mapping Logic --- 
        if event_type == "proposal_status_updated":
             template_name = "social/proposal_update.j2"
        # Add more template mappings here based on event_type...
        elif event_type == "some_other_event":
             # template_name = "social/some_other_template.j2"
             pass
        # --- End Template Mapping Logic --- 

        # print(f"[{self.agent_id}] Using template: {template_name}")
        # Ensure event_type key exists for template, even if generic
        if 'event_type' not in context: context['event_type'] = event_type.upper() 
            
        rendered_text = render_template(template_name, context)
        
        if rendered_text:
            # print(f"[{self.agent_id}] Rendered Text: {rendered_text[:LOG_SNIPPET_LENGTH]}...") # Log snippet
            return rendered_text, context # Return rendered text and the context used
        else:
             # print(f"[{self.agent_id}] Error: Failed to render template {template_name}. Generating fallback text.")
             log_event("AGENT_WARNING", self.agent_id, {"warning": "Template rendering failed", "template": template_name, "context": context})
             # Fallback text generation logic
             fallback_text = "[Fallback] A general update occurred."
             if context.get("governance_update"):
                 title = context.get("title", "Governance Update")
                 summary = context.get("proposal_summary") or context.get("reflection_snippet") or context.get("general_update", "N/A")
                 status = context.get("status_update")
                 fallback_text = f"[Fallback] {title}: {summary}" + (f" (Status: {status})" if status else "")
             
             # print(f"[{self.agent_id}] Fallback Text: {fallback_text[:LOG_SNIPPET_LENGTH]}...")
             return fallback_text, context # Return fallback text and the context used

    def post(self, platform_name: str, text: str | None = None, image_path: str | None = None, use_governance_context: bool = False, **kwargs):
        """Posts content to the specified social media platform. Returns (success_flag, error_message_or_none_or_result_dict)."""
        # --- REFACTORED (PARTIALLY) ---
        final_text = text
        context_used = None # For logging

        if use_governance_context:
            generated_text, context_used = self._generate_post_content(platform_name)
            if generated_text is not None:
                final_text = generated_text
            else:
                log_event("AGENT_WARNING", self.agent_id, {"warning": "Post content generation failed. Using provided text if available.", "platform": platform_name})
                if not final_text:
                    log_event("AGENT_ERROR", self.agent_id, {"error": "Post aborted - no content available (generation failed and no text provided)", "platform": platform_name})
                    return False, "Post aborted - no content available (generation failed and no text provided)"

        if not final_text and not image_path: # Allow image-only posts
            log_event("AGENT_WARNING", self.agent_id, {"warning": "Attempting to post with no text or image.", "platform": platform_name})
            # Proceed, strategy might handle image-only posts
            # return False # Old logic

        post_kwargs = {'text': final_text, 'image_path': image_path, **kwargs}
        # _execute_strategy_action returns (result, error_msg)
        post_result, error_msg = self._execute_strategy_action(
            platform_name=platform_name,
            action_name='post',
            action_kwargs=post_kwargs,
            default_return_on_error=None # Indicate error explicitly
        )

        # Additional logging specific to post outcome
        log_event("PLATFORM_POST", self.agent_id, {
            "platform": platform_name,
            "success": post_result is not None and error_msg is None, # Success if result exists and no error msg
            "text_length": len(final_text) if final_text else 0,
            "image_provided": bool(image_path),
            "governance_context_used": use_governance_context,
            "context_details": context_used, # Log context if generated
            "strategy_kwargs": kwargs, # Log any extra args passed
            "error": error_msg,
            "result_details": post_result # Log the raw result from strategy
        })
        return post_result is not None and error_msg is None, error_msg
        # --- END REFACTOR ---

    def check_login_status(self, platform_name: str):
        """Checks login status for the specified platform. Returns (status_bool_or_none, error_message_or_none)."""
        # --- REFACTORED ---
        # Returns status (True/False) or None on error checking
        result, error_msg = self._execute_strategy_action(
            platform_name=platform_name,
            action_name='check_login_status',
            default_return_on_error=None # Indicate failure to check status
        )
        # --- END REFACTOR ---
        return result, error_msg

    def scrape_mentions(self, platform_name: str, max_mentions: int = DEFAULT_MAX_MENTIONS):
        """Scrapes mentions using the specified platform's strategy. Returns (list_of_mentions_or_none, error_message_or_none)."""
        # --- REFACTORED ---
        # Returns list of mentions or [] on error/unsupported
        results_list, error_msg = self._execute_strategy_action(
            platform_name=platform_name,
            action_name='scrape_mentions',
            action_kwargs={'max_mentions': max_mentions},
            default_return_on_error=None # Return None on error
        )
        # --- END REFACTOR ---
        # ---> ADDED: Process feedback from mentions
        if results_list is not None and not error_msg:
            try:
                log_event("AGENT_INFO", self.agent_id, {"message": "Processing feedback from scraped mentions...", "count": len(results_list)})
                process_feedback(results_list) # Call feedback processor
            except Exception as feedback_e:
                log_event("AGENT_ERROR", self.agent_id, {"error": "Error processing feedback from mentions", "details": str(feedback_e)}) # Add traceback
                # Don't overwrite original scrape error, just log feedback error
        return results_list, error_msg

    def scrape_trends(self, platform_name: str, **kwargs):
        """Scrapes trends using the specified platform's strategy. Returns (list_of_trends_or_none, error_message_or_none)."""
        # --- REFACTORED ---
        # Returns list of trends or [] on error/unsupported
        return self._execute_strategy_action(
            platform_name=platform_name,
            action_name='scrape_trends',
            action_kwargs=kwargs, # Pass through kwargs like region
            default_return_on_error=None # Return None on error
        )
        # --- END REFACTOR ---

    def scrape_community(self, platform_name: str, **kwargs):
        """Scrapes community posts using the specified platform's strategy. Returns (list_of_posts_or_none, error_message_or_none)."""
        # --- REFACTORED ---
        # Returns list of posts or [] on error/unsupported
        results_list, error_msg = self._execute_strategy_action(
            platform_name=platform_name,
            action_name='scrape_community',
            action_kwargs=kwargs, # Pass through kwargs like community_id, max_posts
            default_return_on_error=None # Return None on error
        )
        # --- END REFACTOR ---
        # ---> ADDED: Process feedback from community posts
        if results_list is not None and not error_msg:
            try:
                log_event("AGENT_INFO", self.agent_id, {"message": "Processing feedback from scraped community posts...", "count": len(results_list)})
                process_feedback(results_list)
            except Exception as feedback_e:
                log_event("AGENT_ERROR", self.agent_id, {"error": "Error processing feedback from community posts", "details": str(feedback_e)}) # Add traceback
        return results_list, error_msg

    # --- NEW: Event Dispatch Helper ---
    def _dispatch_response_event(self, original_event: Event, status: EventType, results: Any = None, error_details: str | None = None):
        """Dispatches a response event back to the original sender via the AgentBus."""
        response_data = {
            "correlation_id": original_event.id, # Link response to request
            "original_event_type": original_event.type.name,
            "status": status.name, # e.g., TASK_COMPLETED, TASK_FAILED
        }
        if results is not None:
            response_data["results"] = results
        if error_details is not None:
            response_data["error"] = error_details

        # Determine the response EventType (typically TASK_COMPLETED or TASK_FAILED)
        response_type = status # Use the provided status EventType

        response_event = Event(
            type=response_type,
            source_id=self.agent_id,
            target_id=original_event.source_id, # Send back to the original sender
            data=response_data
        )

        log_event("AGENT_DISPATCH_RESPONSE", self.agent_id, {
            "response_type": response_type.name,
            "target": original_event.source_id,
            "correlation_id": original_event.id,
            "status": status.name,
            "has_results": results is not None,
            "has_error": error_details is not None
        })
        self.bus.dispatch(response_event)

    # --- Bus Event Handling ---
    def handle_bus_event(self, event: Event): # Renamed from handle_bus_message
        """Processes incoming events from the AgentBus."""
        log_event("AGENT_EVENT_RECEIVED", self.agent_id, {"event_id": event.id, "type": event.type.name, "source": event.source_id, "target": event.target_id})

        # Use event type name (string) to look up handler
        handler = self.COMMAND_HANDLERS.get(event.type.name)

        if handler:
            try:
                # Execute the command handler, passing the full event object
                handler(event=event)
            except Exception as e:
                error_msg = f"Unhandled exception in handler for event type '{event.type.name}': {e}"
                log_event("AGENT_HANDLER_ERROR", self.agent_id, {"event_id": event.id, "event_type": event.type.name, "error": error_msg}) # Add traceback
                # Send error response back via bus
                self._dispatch_response_event(original_event=event, status=EventType.TASK_FAILED, error_details=error_msg)
        else:
            error_msg = f"No handler found for event type: {event.type.name}"
            log_event("AGENT_HANDLER_NOT_FOUND", self.agent_id, {"event_id": event.id, "event_type": event.type.name, "error": error_msg})
            self._dispatch_response_event(original_event=event, status=EventType.TASK_FAILED, error_details=error_msg)

    # --- Adapting Command Handlers ---
    # Each _handle_... command needs to:
    # 1. Accept `event: Event` as argument.
    # 2. Extract details from `event.data`.
    # 3. Call the appropriate core action method (e.g., self.post, self.login).
    # 4. Use the result and error message from the core action method.
    # 5. Call `self._dispatch_response_event` with appropriate status (TASK_COMPLETED/TASK_FAILED).

    def _handle_post_command(self, event: Event):
        details = event.data
        platform = details.get("platform")
        if not platform:
            self._dispatch_response_event(event, EventType.TASK_FAILED, error_details="Missing 'platform' in event data")
            return
        
        text = details.get("text")
        image_path = details.get("image_path")
        use_governance = details.get("use_governance_context", False)
        kwargs = details.get("kwargs", {})
        
        try:
            # self.post now returns (success_flag, error_or_result)
            success, result_or_error = self.post(platform, text=text, image_path=image_path, use_governance_context=use_governance, **kwargs)
            if success:
                # Post ID or details might be in result_or_error
                result_data = {"status": "posted", "details": result_or_error}
                self._dispatch_response_event(event, EventType.TASK_COMPLETED, results=result_data)
            else:
                # result_or_error contains the error message
                self._dispatch_response_event(event, EventType.TASK_FAILED, error_details=result_or_error or "Post method returned failure")
        except Exception as e:
            # This catch block might be redundant if self.post handles exceptions via _execute_strategy_action
            error_msg = f"Unexpected exception during post command for platform {platform}: {e}"
            log_event("AGENT_HANDLER_ERROR", self.agent_id, {"event_id": event.id, "event_type": event.type.name, "error": error_msg}) # Add traceback
            self._dispatch_response_event(event, EventType.TASK_FAILED, error_details=error_msg)

    def _handle_get_analytics_command(self, event: Event):
        """Handles various analytics/scraping types based on event data."""
        details = event.data
        platform = details.get("platform")
        analytics_type = details.get("analytics_type") # e.g., "mentions", "trends", "community"
        if not platform or not analytics_type:
            self._dispatch_response_event(event, EventType.TASK_FAILED, error_details="Missing 'platform' or 'analytics_type' in event data")
            return

        results_data = None
        error_msg = None
        kwargs = details.get("kwargs", {})
        
        try:
            results = None # Initialize results
            if analytics_type == "mentions":
                max_mentions = kwargs.get('max_mentions', self.config.get('common_settings', {}).get('max_mentions', DEFAULT_MAX_MENTIONS))
                results, error_msg = self.scrape_mentions(platform, max_mentions=max_mentions)
                if results is not None: results_data = {"mention_count": len(results), "mentions": results}
            elif analytics_type == "trends":
                results, error_msg = self.scrape_trends(platform, **kwargs)
                if results is not None: results_data = {"trend_count": len(results), "trends": results}
            elif analytics_type == "community":
                community_id = kwargs.get('community_id')
                max_posts = kwargs.get('max_posts', self.config.get('common_settings', {}).get('max_community_posts', 20))
                if not community_id:
                    error_msg = "Missing 'community_id' in kwargs for scrape_community"
                else:
                    # Pass necessary kwargs explicitly
                    scrape_kwargs = {'community_id': community_id, 'max_posts': max_posts, **kwargs}
                    results, error_msg = self.scrape_community(platform, **scrape_kwargs)
                    if results is not None: results_data = {"post_count": len(results), "posts": results}
            else:
                error_msg = f"Unsupported analytics_type: {analytics_type}"

            # Check results and error message
            if error_msg:
                 self._dispatch_response_event(event, EventType.TASK_FAILED, error_details=error_msg)
            elif results_data is not None: # Success if we have data and no error
                 self._dispatch_response_event(event, EventType.TASK_COMPLETED, results=results_data)
            else: # Should not happen if error_msg is None, but as a fallback
                 self._dispatch_response_event(event, EventType.TASK_FAILED, error_details="Analytics/Scrape method returned unexpected empty result without error.")

        except Exception as e:
            error_msg = f"Unexpected exception during {analytics_type} command for platform {platform}: {e}"
            log_event("AGENT_HANDLER_ERROR", self.agent_id, {"event_id": event.id, "event_type": event.type.name, "error": error_msg}) # Add traceback
            self._dispatch_response_event(event, EventType.TASK_FAILED, error_details=error_msg)

    def _handle_login_command(self, event: Event):
        details = event.data
        platform = details.get("platform")
        if not platform:
            self._dispatch_response_event(event, EventType.TASK_FAILED, error_details="Missing 'platform' in event data")
            return
        try:
            success, error_msg = self.login(platform)
            results = {"login_attempted": True, "success": success}
            if success:
                self._dispatch_response_event(event, EventType.TASK_COMPLETED, results=results)
            else:
                self._dispatch_response_event(event, EventType.TASK_FAILED, results=results, error_details=error_msg or "Login failed")
        except Exception as e:
            error_msg = f"Unexpected exception during login command for platform {platform}: {e}"
            log_event("AGENT_HANDLER_ERROR", self.agent_id, {"event_id": event.id, "event_type": event.type.name, "error": error_msg}) # Add traceback
            self._dispatch_response_event(event, EventType.TASK_FAILED, error_details=error_msg)

    def _handle_check_login_status_command(self, event: Event):
        details = event.data
        platform = details.get("platform")
        if not platform:
            self._dispatch_response_event(event, EventType.TASK_FAILED, error_details="Missing 'platform' in event data")
            return
        try:
            status, error_msg = self.check_login_status(platform)
            if error_msg: # Error occurred during the check itself
                 self._dispatch_response_event(event, EventType.TASK_FAILED, results={"check_attempted": True, "logged_in": None}, error_details=error_msg)
            else: # Check completed, status is True/False/None
                 self._dispatch_response_event(event, EventType.TASK_COMPLETED, results={"check_attempted": True, "logged_in": status})
        except Exception as e:
            error_msg = f"Unexpected exception during check_login_status for platform {platform}: {e}"
            log_event("AGENT_HANDLER_ERROR", self.agent_id, {"event_id": event.id, "event_type": event.type.name, "error": error_msg}) # Add traceback
            self._dispatch_response_event(event, EventType.TASK_FAILED, error_details=error_msg)

    def _handle_agent_status_command(self, event: Event):
        try:
            # Gather status information
            loaded_strategies = list(self.strategies.keys())
            active_drivers = [p for p, s in self.strategies.items() if s.driver is not None] # Example check

            results = {
                "agent_id": self.agent_id,
                "loaded_strategies": loaded_strategies,
                "active_drivers": active_drivers,
                "config_loaded": self.config is not None,
                # Add more detailed status: platform login status (requires checking each)
            }
            # Consider making check_login_status calls for loaded strategies here if needed
            self._dispatch_response_event(event, EventType.TASK_COMPLETED, results=results)
        except Exception as e:
            error_msg = f"Unexpected exception during agent_status command: {e}"
            log_event("AGENT_HANDLER_ERROR", self.agent_id, {"event_id": event.id, "event_type": event.type.name, "error": error_msg}) # Add traceback
            self._dispatch_response_event(event, EventType.TASK_FAILED, error_details=error_msg)

    def _handle_request_cursor_action_command(self, event: Event):
        details = event.data
        log_context = {"command": "request_cursor_action", "event_id": event.id}
        # ... (Keep payload construction logic from original handler) ...
        objective = details.get("objective")
        instruction = details.get("prompt_instruction")
        if not objective or not instruction:
            error_msg = "Missing required fields ('objective', 'prompt_instruction') in request_cursor_action data."
            log_event("AGENT_COMMAND_ERROR", self.agent_id, {**log_context, "error": error_msg})
            self._dispatch_response_event(event, EventType.TASK_FAILED, error_details=error_msg)
            return
            
        try:
            # Construct payload dictionary for the cursor utility
            payload_to_export = {
                "objective": objective,
                "prompt_instruction": instruction,
                "context_data": details.get("context_data", {}), # Example
                "timestamp": datetime.now().isoformat(),
                "source_agent": self.agent_id,
                # Add any other relevant fields
            }
            # Export using utility
            exported_filepath = export_prompt_for_cursor(payload_to_export) # Assuming this util exists and works
            if exported_filepath:
                 log_event("AGENT_COMMAND_SUCCESS", self.agent_id, {**log_context, "result": "Prompt exported", "path": exported_filepath})
                 self._dispatch_response_event(event, EventType.TASK_COMPLETED, results={"exported_path": exported_filepath})
            else:
                 # Assume export_prompt_for_cursor returns None or raises error on failure
                 error_msg = "Failed to export prompt payload via cursor_utils (returned None/False)."
                 log_event("AGENT_COMMAND_ERROR", self.agent_id, {**log_context, "error": error_msg})
                 self._dispatch_response_event(event, EventType.TASK_FAILED, error_details=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error constructing or exporting Cursor prompt: {e}"
            log_event("AGENT_COMMAND_ERROR", self.agent_id, {**log_context, "error": error_msg}) # Add traceback
            self._dispatch_response_event(event, EventType.TASK_FAILED, error_details=error_msg)

    def _handle_process_feedback_item_command(self, event: Event):
        details = event.data
        feedback_item = details.get("feedback_item") # Assume feedback is passed directly
        feedback_id = details.get("feedback_id", f"item_{int(time.time())}") # Generate ID if needed

        if not feedback_item:
             error_msg = "Missing 'feedback_item' in event data."
             log_event("AGENT_COMMAND_ERROR", self.agent_id, {"event_id": event.id, "error": error_msg})
             self._dispatch_response_event(event, EventType.TASK_FAILED, error_details=error_msg)
             return

        try:
            # Call the actual feedback processor utility
            # process_feedback might take a list, adapt if it takes single items
            process_feedback([feedback_item]) # Assuming process_feedback takes a list

            log_event("AGENT_FEEDBACK_ITEM_PROCESSED", self.agent_id, {
                "event_id": event.id,
                "feedback_id": feedback_id,
                "status": "processed",
                "action_taken": "processed_by_utility" # Update if utility returns info
            })
            self._dispatch_response_event(event, EventType.TASK_COMPLETED, results={"processed_feedback_id": feedback_id})
        except Exception as e:
            error_msg = f"Unexpected exception processing feedback item {feedback_id}: {e}"
            log_event("AGENT_HANDLER_ERROR", self.agent_id, {"event_id": event.id, "feedback_id": feedback_id, "error": error_msg}) # Add traceback
            self._dispatch_response_event(event, EventType.TASK_FAILED, error_details=error_msg)

    # --- REMOVED Mailbox processing logic ---
    # def process_incoming_message(self, message: dict): ...
    # def run_operational_loop(...): ...

    # --- Shutdown Logic ---
    def shutdown(self):
        """Cleans up resources like strategies and the browser driver."""
        log_event("AGENT_SHUTDOWN", self.agent_id, {"status": "starting"})
        # Shutdown strategies
        for platform, strategy in self.strategies.items():
            if hasattr(strategy, 'quit') and callable(getattr(strategy, 'quit')):
                try:
                    log_event("AGENT_SHUTDOWN", self.agent_id, {"message": f"Quitting strategy for {platform}..."})
                    strategy.quit()
                except Exception as e:
                     log_event("AGENT_ERROR", self.agent_id, {"error": "Strategy shutdown failed", "platform": platform, "details": str(e)})

        # Quit the browser driver
        if self.driver:
            try:
                log_event("AGENT_SHUTDOWN", self.agent_id, {"message": "Quitting browser driver..."})
                self.driver.quit()
                self.driver = None
                log_event("AGENT_SHUTDOWN", self.agent_id, {"message": "Browser driver quit successfully."})
            except Exception as e:
                log_event("AGENT_ERROR", self.agent_id, {"error": "Driver shutdown failed", "details": str(e)})

        log_event("AGENT_SHUTDOWN", self.agent_id, {"status": "complete"})