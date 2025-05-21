from enum import Enum, auto
from typing import Optional, Dict, Any, Tuple, List
import logging
import time
from dataclasses import dataclass, field
from selenium.common.exceptions import StaleElementReferenceException
from ..io.file_manager import FileManager
from .chatgpt_scraper import ChatGPTScraper

logger = logging.getLogger(__name__)

class ScraperState(Enum):
    """Defines the possible states of the scraper."""
    INITIALIZING = auto()
    AUTHENTICATING = auto()
    READY = auto()
    SENDING_PROMPT = auto()
    WAITING_FOR_RESPONSE = auto()
    STABILIZING_RESPONSE = auto()
    ERROR = auto()
    SHUTDOWN = auto()

@dataclass
class ScraperMetadata:
    """Structured metadata for scraper operations."""
    operation_id: Optional[str] = None
    start_time: float = 0.0
    end_time: Optional[float] = None
    prompt: Optional[str] = None
    response: Optional[str] = None
    error: Optional[str] = None
    state_history: List[Tuple[ScraperState, float]] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    context_tags: List[str] = field(default_factory=list)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ScraperContext:
    """Holds the context data for the scraper state machine."""
    scraper: Optional[ChatGPTScraper] = None
    timeout: int = 180
    stable_period: int = 10
    poll_interval: int = 5
    last_msg_count: int = 0
    current_response: str = ""
    error_message: str = ""
    metadata: ScraperMetadata = field(default_factory=ScraperMetadata)
    start_time: float = 0.0
    last_stable_time: float = 0.0

class ScraperStateMachine:
    """
    State machine implementation for the ChatGPT scraper.
    Manages state transitions and coordinates the scraper's operations.
    """
    
    def __init__(self, file_manager: FileManager):
        self.state = ScraperState.INITIALIZING
        self.context = ScraperContext()
        self.file_manager = file_manager
        self._state_handlers = {
            ScraperState.INITIALIZING: self._handle_initializing,
            ScraperState.AUTHENTICATING: self._handle_authenticating,
            ScraperState.READY: self._handle_ready,
            ScraperState.SENDING_PROMPT: self._handle_sending_prompt,
            ScraperState.WAITING_FOR_RESPONSE: self._handle_waiting_for_response,
            ScraperState.STABILIZING_RESPONSE: self._handle_stabilizing_response,
            ScraperState.ERROR: self._handle_error,
            ScraperState.SHUTDOWN: self._handle_shutdown
        }
        
    def transition_to(self, new_state: ScraperState, **kwargs) -> None:
        """Transition to a new state with optional context updates."""
        logger.info(f"Transitioning from {self.state} to {new_state}")
        
        # Record state transition in metadata
        self.context.metadata.state_history.append((self.state, time.time()))
        
        # Update performance metrics
        if self.state != ScraperState.INITIALIZING:
            state_duration = time.time() - self.context.metadata.start_time
            self.context.metadata.performance_metrics[f"{self.state.name}_duration"] = state_duration
        
        self.state = new_state
        if kwargs:
            for key, value in kwargs.items():
                setattr(self.context, key, value)
                
    def process(self) -> None:
        """Process the current state and handle any necessary transitions."""
        handler = self._state_handlers.get(self.state)
        if handler:
            handler()
        else:
            logger.error(f"No handler found for state: {self.state}")
            self.transition_to(ScraperState.ERROR, error_message="Invalid state")
            
    def _handle_initializing(self) -> None:
        """Handle the initialization state."""
        try:
            # Initialize the ChatGPT scraper
            self.context.scraper = ChatGPTScraper(
                timeout=self.context.timeout,
                stable_period=self.context.stable_period,
                poll_interval=self.context.poll_interval
            )
            self.transition_to(ScraperState.AUTHENTICATING)
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            self.transition_to(ScraperState.ERROR, error_message=str(e))
            
    def _handle_authenticating(self) -> None:
        """Handle the authentication state."""
        try:
            if not self.context.scraper.ensure_login_session():
                raise Exception("Failed to establish login session")
            self.transition_to(ScraperState.READY)
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self.transition_to(ScraperState.ERROR, error_message=str(e))
            
    def _handle_ready(self) -> None:
        """Handle the ready state - waiting for next action."""
        pass  # Ready state is a waiting state, no action needed
        
    def send_prompt(self, prompt: str, operation_id: Optional[str] = None) -> None:
        """Send a prompt to ChatGPT."""
        if self.state != ScraperState.READY:
            raise RuntimeError(f"Cannot send prompt in state: {self.state}")
            
        # Initialize metadata for new operation
        self.context.metadata = ScraperMetadata(
            operation_id=operation_id,
            start_time=time.time(),
            prompt=prompt
        )
        
        self.transition_to(ScraperState.SENDING_PROMPT)
        
    def _handle_sending_prompt(self) -> None:
        """Handle sending a prompt to ChatGPT."""
        try:
            prompt = self.context.metadata.get("current_prompt")
            if not prompt:
                raise ValueError("No prompt provided")
                
            if not self.context.scraper.send_prompt(prompt):
                raise Exception("Failed to send prompt")
                
            self.context.start_time = time.time()
            self.context.last_stable_time = self.context.start_time
            self.transition_to(ScraperState.WAITING_FOR_RESPONSE)
        except Exception as e:
            logger.error(f"Failed to send prompt: {e}")
            self.transition_to(ScraperState.ERROR, error_message=str(e))
            
    def _handle_waiting_for_response(self) -> None:
        """Handle waiting for initial response from ChatGPT."""
        try:
            if self._check_for_response():
                self.transition_to(ScraperState.STABILIZING_RESPONSE)
            elif time.time() - self.context.start_time > self.context.timeout:
                raise TimeoutError("Timeout waiting for initial response")
        except Exception as e:
            logger.error(f"Error while waiting for response: {e}")
            self.transition_to(ScraperState.ERROR, error_message=str(e))
            
    def _handle_stabilizing_response(self) -> None:
        """Handle stabilizing the response from ChatGPT."""
        try:
            if self._is_response_stable():
                # Record successful response
                self.context.metadata.response = self.context.current_response
                self.context.metadata.end_time = time.time()
                
                # Calculate performance metrics
                total_duration = self.context.metadata.end_time - self.context.metadata.start_time
                self.context.metadata.performance_metrics["total_duration"] = total_duration
                
                self.transition_to(ScraperState.READY)
            elif time.time() - self.context.start_time > self.context.timeout:
                raise TimeoutError("Timeout waiting for stable response")
        except Exception as e:
            logger.error(f"Error while stabilizing response: {e}")
            self.context.metadata.error = str(e)
            self.transition_to(ScraperState.ERROR, error_message=str(e))
            
    def _handle_error(self) -> None:
        """Handle error state and recovery."""
        logger.error(f"Scraper in error state: {self.context.error_message}")
        
        # Record error in metadata
        self.context.metadata.error = self.context.error_message
        self.context.metadata.end_time = time.time()
        
        # Attempt recovery
        try:
            if self.context.scraper:
                self.context.scraper.ensure_login_session()
                self.transition_to(ScraperState.READY)
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            self.transition_to(ScraperState.SHUTDOWN)
        
    def _handle_shutdown(self) -> None:
        """Handle graceful shutdown of the scraper."""
        try:
            if self.context.scraper and self.context.scraper.driver:
                self.context.scraper.driver.quit()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            
    def _check_for_response(self) -> bool:
        """Check if a response has been received."""
        try:
            message_elements = self.context.scraper._get_message_elements()
            current_count = len(message_elements)
            
            if current_count > self.context.last_msg_count:
                self.context.current_response = message_elements[-1].text.strip()
                self.context.last_msg_count = current_count
                return True
                
            return False
        except Exception as e:
            logger.error(f"Error checking for response: {e}")
            return False
        
    def _is_response_stable(self) -> bool:
        """Check if the current response is stable."""
        try:
            message_elements = self.context.scraper._get_message_elements()
            if not message_elements:
                return False
                
            current_response = message_elements[-1].text.strip()
            
            if current_response != self.context.current_response:
                self.context.current_response = current_response
                self.context.last_stable_time = time.time()
                return False
                
            return (time.time() - self.context.last_stable_time) >= self.context.stable_period
        except Exception as e:
            logger.error(f"Error checking response stability: {e}")
            return False
            
    def get_current_response(self) -> str:
        """Get the current response from the scraper."""
        return self.context.current_response
        
    def shutdown(self) -> None:
        """Initiate graceful shutdown of the scraper."""
        self.transition_to(ScraperState.SHUTDOWN) 