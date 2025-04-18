import os
import sys
import logging
from typing import Optional, Dict, Any

# Setup logger for this module
logger = logging.getLogger(__name__)

# Import necessary components from their new locations
try:
    from core.services.event_logger import log_structured_event
    from core.llm.llm_bridge import call_llm
except ImportError as e:
    logger.critical(f"Failed to import required core components (event_logger, llm_bridge): {e}", exc_info=True)
    # Define fallbacks ONLY if critical failure allows partial operation (unlikely here)
    # Or, more likely, raise the error to prevent startup
    raise ImportError(f"Could not import core dependencies for PromptService: {e}") from e

_SOURCE_ID = "PromptService"

def stage_and_execute_prompt(agent_id: str, 
                           prompt_subject: str, 
                           prompt_context: str, 
                           llm_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Stages, logs (using event_logger), executes (via LLM bridge), 
    and logs the response for a given prompt.

    Args:
        agent_id (str): The ID of the agent/component submitting the prompt.
        prompt_subject (str): A short description/subject for the prompt (for logging).
        prompt_context (str): The full text/content of the prompt to send to the LLM.
        llm_config (Optional[Dict[str, Any]]): Optional dictionary with specific configurations 
                                                for the LLM call (e.g., model, temperature).

    Returns:
        Optional[str]: The raw response string from the LLM, or None on failure.
    """
    event_data_staged = {
        "agent_source": agent_id,
        "prompt_subject": prompt_subject,
        "prompt_context_snippet": prompt_context[:150] + ("..." if len(prompt_context) > 150 else ""),
        "llm_config_keys": list(llm_config.keys()) if llm_config else []
    }
    log_structured_event("PROMPT_STAGED", event_data_staged, _SOURCE_ID)
    logger.info(f"Staged prompt '{prompt_subject}' from agent '{agent_id}'.")

    # --- Call the LLM Bridge --- 
    try:
        llm_response = call_llm(prompt_context, **(llm_config or {}))
        logger.debug(f"LLM call for prompt '{prompt_subject}' completed.")
    except Exception as e:
        logger.error(f"LLM bridge call failed for prompt '{prompt_subject}': {e}", exc_info=True)
        event_data_failed = {
             "agent_source": agent_id,
             "prompt_subject": prompt_subject,
             "error": f"LLM call failed: {e}"
         }
        log_structured_event("PROMPT_FAILED", event_data_failed, _SOURCE_ID)
        return None
    # --- End LLM Call ---

    if llm_response is not None:
        event_data_completed = {
            "agent_source": agent_id,
            "prompt_subject": prompt_subject,
            "response_snippet": llm_response[:150] + ("..." if len(llm_response) > 150 else "")
        }
        log_structured_event("PROMPT_COMPLETED", event_data_completed, _SOURCE_ID)
        logger.info(f"Prompt '{prompt_subject}' from agent '{agent_id}' completed successfully.")
    else:
        # This case might be hit if call_llm returns None without raising an exception (e.g., simulated failure)
        event_data_failed = {
            "agent_source": agent_id,
            "prompt_subject": prompt_subject,
            "error": "LLM call returned None (check LLMBridge logs for simulation details or actual errors)."
        }
        log_structured_event("PROMPT_FAILED", event_data_failed, _SOURCE_ID)
        logger.warning(f"Prompt '{prompt_subject}' from agent '{agent_id}' failed (LLM returned None).")

    return llm_response

# Example Usage (can be run directly: python -m core.llm.prompt_service)
if __name__ == '__main__':
    # Setup basic logging for the example
    # In a real app, logging configuration would be centralized
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Need to ensure the logger used by the imported modules is also configured if needed
    # logging.getLogger('core.llm.llm_bridge').setLevel(logging.DEBUG)
    # logging.getLogger('core.services.event_logger').setLevel(logging.DEBUG)

    logger.info(f"Running Prompt Service example...")
    
    test_agent = "TestAgent_Main"
    test_subject = "Generate Main Plan Example"
    test_prompt = "User Goal: Create a main test plan.\nInstructions: Output JSON list.\nFormat: [...]"
    test_config = {"model": "main-test-model-v1", "temperature": 0.75}

    # --- Test Success ---    
    print("\n--- Testing Prompt Execution (Success Expected) ---")
    response = stage_and_execute_prompt(test_agent, test_subject, test_prompt, test_config)
    print(f"Response Received:")
    if response:
        print(response)
    else:
        print("Execution failed.")

    # --- Test Failure (Simulated in LLM Bridge) ---    
    print("\n--- Testing Prompt Execution (Failure Expected) ---")
    fail_subject = "Generate Failing Plan"
    fail_prompt = "Please fail this request according to dummy logic."
    response_fail = stage_and_execute_prompt(test_agent, fail_subject, fail_prompt)
    print(f"Response Received:")
    if response_fail:
        print(response_fail)
    else:
        print("Execution failed as expected (returned None).")
        
    logger.info(f"Prompt Service example finished.")
    # Check the runtime/structured_events.jsonl file for logged events 