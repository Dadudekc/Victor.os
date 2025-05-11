# PromptExecutionService (`src/dreamos/chat_engine/prompt_execution_service.py`)

## Overview

The `PromptExecutionService` is responsible for managing the direct interaction of sending prompts to a chat interface (via a `driver_manager`) and retrieving the responses. It can handle single prompt executions, sequential execution of multiple prompts on a single chat, and concurrent prompt executions.

## Key Responsibilities

*   Retrieving prompt text from a `prompt_manager`.
*   Sending prompts to the chat UI and waiting for responses.
*   Handling different wait times or post-processing based on the language model being used.
*   Optionally interacting with a `FeedbackEngine` to update memory based on responses.
*   Accepting and logging chat context metadata provided by an orchestrator (like `ChatCycleController`).

## Core Methods

### `__init__(self, driver_manager, prompt_manager, feedback_engine=None, model="gpt-4o-mini", ...)`
*   Initializes the service with necessary components like `driver_manager`, `prompt_manager`, and optional `feedback_engine`, along with configuration for the model and cycle timings.

### `get_prompt(self, prompt_name: str) -> str`
*   Retrieves the text of a named prompt from the `prompt_manager`.

### `send_prompt_and_wait(self, prompt_text: str, chat_context: dict = None) -> str`
*   **Public Interface**: This is the primary method intended to be called by external orchestrators (e.g., `ChatCycleController`).
*   **Functionality**: It wraps `execute_prompt_cycle`, passing through the `prompt_text` and the optional `chat_context` dictionary.
*   **Returns**: The text of the response from the chat, or an empty string/None if no response is detected.

### `execute_prompt_cycle(self, prompt_text: str, chat_context: dict = None) -> str`
*   **Internal Workhorse**: Manages the detailed steps of sending a prompt and getting a response.
*   **Parameters**:
    *   `prompt_text` (str): The actual text of the prompt to send.
    *   `chat_context` (dict, optional): A dictionary containing metadata about the chat being interacted with (e.g., title, link, last_active_time, snippet). Defaults to `None`.
*   **Actions**:
    *   Logs the received `chat_context` if provided.
    *   **Augments `prompt_text`**: If `chat_context` contains relevant fields (e.g., `last_active_time`, `snippet`), a `[Chat Context Summary]` prefix is prepended to `prompt_text` before sending. The original prompt is preserved internally for logging.
    *   Sends the (potentially augmented) prompt using an internal `_send_prompt` method. This method now logs the first 500 characters of the text being sent at DEBUG level.
    *   Waits for a model-specific duration for the response to stabilize.
    *   Fetches the response using an internal `_fetch_response` method.
    *   Performs any model-specific post-processing (e.g., for "jawbone" models).
    *   Optionally passes the response to `feedback_engine` for memory updates.
*   **Returns**: The processed response text.

### `execute_prompts_single_chat(self, prompt_list: list, chat_context: dict = None) -> list`
*   Executes a list of named prompts sequentially on the currently active chat.
*   Accepts an optional `chat_context` which is passed to each call of `execute_prompt_cycle` for every prompt in the list.
*   Returns a list of dictionaries, each containing the `prompt_name` and its corresponding `response`.

### `execute_prompts_concurrently(self, chat_link, prompt_list)`
*   (Assumes `_execute_single_prompt_thread` is updated to accept and pass context if this were to be fully integrated with the new context flow for concurrent operations).
*   Executes a list of prompts concurrently, each in its own thread, for a given `chat_link`.
    *   The internal `_execute_single_prompt_thread` method has been updated to accept and pass `chat_context` to `execute_prompt_cycle`.

### `_determine_wait_time(self)` and `_post_process_jawbone_response(self, response: str)`
*   Internal helpers for model-specific behaviors.

## Metadata Integration (PIPE-003)

*   The `send_prompt_and_wait`, `execute_prompt_cycle`, `execute_prompts_single_chat`, and `_execute_single_prompt_thread` methods now accept an optional `chat_context: dict` parameter.
*   This dictionary is expected to contain metadata scraped by `ChatScraperService` and passed through `ChatCycleController` (schema includes `title`, `link`, `last_active_time`, `snippet`).
*   `PromptExecutionService` now **actively uses** this context (if available and relevant fields are present) to **augment the prompt text** by prepending a formatted summary of the chat context before sending it to the LLM. See details in `execute_prompt_cycle`.
*   The service also logs the received context and details of any augmentation performed.
*   **Future Potential**: Further enhancements could include passing this context to `prompt_manager` to influence prompt selection or to `feedback_engine` for richer memory updates.
*   Refer to `ai_docs/api_docs_and_integrations/README.md` for the full data flow and schema, and `ai_docs/agent_coordination/PIPE-003_MetadataScout_Phase2_Report_PromptAugmentation.md` for implementation details of prompt augmentation.

## Dependencies

*   `driver_manager`: For browser interaction.
*   `prompt_manager`: For retrieving prompt texts.
*   `feedback_engine` (optional): For memory updates.
*   Logging, threading, time modules.
