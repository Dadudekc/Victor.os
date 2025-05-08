# API Documentation and Integrations

This directory contains documentation related to:
- Internal APIs within the project.
- External APIs the project interacts with.
- Integration guides and details.

## Existing Integrations & Clients

The following client implementations provide abstracted access to external services:

*   **OpenAI Client:**
    *   **File:** [src/dreamos/integrations/openai_client.py](../../src/dreamos/integrations/openai_client.py)
    *   **Purpose:** Interacts with OpenAI APIs for language model completions.
    *   **Key Methods:** `get_completion(prompt, model, **kwargs)` (async).
    *   **Configuration:** Requires `integrations.openai.api_key`, optionally `integrations.openai.api_base`.
    *   **Dependencies:** `openai`, `tenacity`.
    *   **Notes:** Uses `tenacity` for retries on common API errors. Handles authentication errors gracefully by disabling the client.

*   **Discord Client:**
    *   **File:** [src/dreamos/integrations/discord_client.py](../../src/dreamos/integrations/discord_client.py)
    *   **Purpose:** Sends messages via Discord Webhooks or Bot user.
    *   **Key Methods:** `send_webhook_message(content, username=None, avatar_url=None, **kwargs)` (async), `send_bot_message(channel_id, content, **kwargs)` (async), `close_session()` (async).
    *   **Configuration:** Optional `integrations.discord.webhook_url`, optional `integrations.discord.bot_token`. Client functionality depends on which are provided.
    *   **Dependencies:** `aiohttp`, `tenacity`.
    *   **Notes:** Uses `aiohttp` for async HTTP requests and `tenacity` for retries. Manages an `aiohttp.ClientSession` internally.

*   **Browser Client (Playwright):**
    *   **File:** [src/dreamos/integrations/browser_client.py](../../src/dreamos/integrations/browser_client.py)
    *   **Purpose:** Abstracts browser automation using Playwright.
    *   **Key Methods:** `connect()` (async), `close()` (async), `get_page_dom(url)` (async), `perform_action(url, action_details)` (async - supports click, type, get_text, get_attribute, wait_for_selector, screenshot).
    *   **Configuration:** `integrations.browser.type` (e.g., 'chromium', 'firefox', default 'chromium'), `integrations.browser.headless` (default True).
    *   **Dependencies:** `playwright` (requires `playwright install` post-setup).
    *   **Notes:** Manages Playwright connection and browser lifecycle. `perform_action` allows executing various interactions on a page.

*   **Azure Blob Storage Client:**
    *   **File:** [src/dreamos/integrations/azure_blob_client.py](../../src/dreamos/integrations/azure_blob_client.py)
    *   **Purpose:** Interacts with Azure Blob Storage for file uploads/downloads.
    *   **Key Methods:** `upload_blob(container_name, blob_name, data)` (async), `download_blob(container_name, blob_name)` (async), `close()` (async).
    *   **Configuration:** Requires `integrations.azure_blob.connection_string`.
    *   **Dependencies:** `azure-storage-blob`, `tenacity`.
    *   **Notes:** Uses the async `azure-storage-blob` client and `tenacity` for retries.

## Configuration & Error Handling

*   **Configuration:** API keys, connection strings, and other integration settings are typically managed via the `AppConfig` system, defined in [src/dreamos/core/config.py](../../src/dreamos/core/config.py) and loaded according to the [Configuration Management Standard](../../docs/standards/configuration.md). Secrets should ideally use environment variables.
*   **Error Handling:** Standard exception classes like `IntegrationError` and `APIError` are defined in [src/dreamos/integrations/__init__.py](../../src/dreamos/integrations/__init__.py) and used by the clients to signal integration-specific failures.

## Architectural Documents & Research

*   **ChatGPT-Cursor Bridge:** [cursor_chatgpt_bridge.md](./cursor_chatgpt_bridge.md) (Primary Documentation) outlines the architecture and operational details for bridging LLM interactions with the Cursor IDE using UI automation and the `chatgpt_web_agent.py`.
*   **Social Platform Research:** [docs/analysis_reports/social_platform_expansion_research.md](../../docs/analysis_reports/social_platform_expansion_research.md) details the feasibility and limitations of interacting with Twitter/X and LinkedIn APIs.

## Internal APIs

*   _(This section should be populated if internal REST/RPC APIs are developed within the project, e.g., for agent-to-agent communication beyond the AgentBus or for external access.)_

## Chat Engine Metadata Flow (PIPE-003)

This section describes the flow of chat context metadata from scraping to prompt execution.

**Objective**: To enrich the prompt execution process with contextual information about the chat being processed, allowing for more informed or tailored interactions.

**Services Involved**:

1.  `ChatScraperService` (`src/dreamos/chat_engine/chat_scraper_service.py`): Responsible for scraping chat information from the UI.
2.  `ChatCycleController` (`src/dreamos/chat_engine/chat_cycle_controller.py`): Orchestrates the chat processing cycle, including scraping and prompt execution.
3.  `PromptExecutionService` (`src/dreamos/chat_engine/prompt_execution_service.py`): Responsible for sending prompts to the chat UI and retrieving responses.

**Metadata Schema (`chat_context`)**:

The following dictionary structure is used to pass chat context metadata:

```json
{
  "title": "string | null",                 // The title of the chat
  "link": "string | null",                  // The direct URL/link to the chat
  "last_active_time": "string | null",      // Textual representation of last activity (e.g., "2 hours ago", "YYYY-MM-DD")
  "snippet": "string | null"                // A short preview or snippet of the last message in the chat
}
```
*Future potential fields include `char_count`, `estimated_topic`, `turn_count`.*

**Data Flow**:

1.  **Scraping (`ChatScraperService`)**:
    *   The `get_all_chats()` method in `ChatScraperService` is enhanced to attempt to scrape `last_active_time` and `snippet` in addition to `title` and `link` for each chat discovered in the sidebar.
    *   These fields are populated with `null` (or `None` in Python) if the corresponding UI elements are not found, ensuring graceful degradation.

2.  **Orchestration (`ChatCycleController`)**:
    *   `ChatCycleController` calls `ChatScraperService.get_all_chats()` to retrieve the list of chats, now including the new metadata fields.
    *   During the processing of each chat (in `process_chat()` or `run_single_chat()`):
        *   The controller extracts this metadata.
        *   It constructs a `chat_context` dictionary (as per the schema above).
        *   This `chat_context` dictionary is passed as an argument to `PromptExecutionService.send_prompt_and_wait()`.

3.  **Execution (`PromptExecutionService`)**:
    *   The `send_prompt_and_wait()` method (and its internal helper `execute_prompt_cycle()`) in `PromptExecutionService` now accepts an optional `chat_context: dict = None` parameter.
    *   Currently, the service logs this received `chat_context` for observability.
    *   **Future Enhancements**: This context can be used to:
        *   Modify or augment prompt text before sending it to the LLM.
        *   Inform a `PromptManager` to select more contextually appropriate prompts.
        *   Provide additional information to a `FeedbackEngine`.

**Error Handling**:
*   If `ChatScraperService` cannot find the DOM elements for `last_active_time` or `snippet`, these fields will be `null` in the `chat_context`. Downstream services should handle these `null` values appropriately (e.g., by not using them if null).

### Future Enhancements for Active Context Usage

While the initial implementation (PIPE-003 Phase 1) focused on plumbing the `chat_context` to `PromptExecutionService` for logging, and Phase 2 implemented direct prompt augmentation, further phases can leverage this context more actively:

1.  **Direct Prompt Augmentation in `PromptExecutionService` (Implemented in Phase 2)**:
    *   **Status**: Implemented.
    *   **Location**: Within `PromptExecutionService.execute_prompt_cycle()`, before calling `_send_prompt()`.
    *   **Method**: Modifies the `prompt_text` to include information from `chat_context` (e.g., `last_active_time`, `snippet`) using a `[Chat Context Summary]` prefix.
    *   **Details**: See `ai_docs/agent_coordination/PIPE-003_MetadataScout_Phase2_Report_PromptAugmentation.md` (formerly plan document) and `src/dreamos/chat_engine/prompt_execution_service.README.md`.

2.  **Context-Aware Prompt Selection/Generation via `PromptManager` (Future)**:
    *   **Location**: `PromptExecutionService` would pass `chat_context` to `self.prompt_manager.get_prompt()`.
    *   **Method**: The `PromptManager` (would require modification) could use the `chat_context` to:
        *   Select a more specific pre-defined prompt variant.
        *   Dynamically insert contextual information into a template-based prompt.
    *   **Pros**: Cleaner separation of concerns; `PromptManager` handles prompt logic. Allows for more sophisticated context use than simple prefixing.
    *   **Cons**: Requires significant modification to `PromptManager` and a well-defined strategy for how it utilizes various context fields.

3.  **Contextual Information for `FeedbackEngine` (Future)**:
    *   **Location**: `PromptExecutionService` would pass `chat_context` to `self.feedback_engine.parse_and_update_memory()` (or a similar method).
    *   **Method**: The `FeedbackEngine` (would require modification) could use `chat_context` to:
        *   Store feedback in relation to specific chat characteristics (e.g., "feedback for long-running chats", "feedback for chats on topic X").
        *   Enrich the memory entries with chat metadata.
    *   **Pros**: Enables more nuanced and context-rich feedback analysis and memory management.
    *   **Cons**: Requires modification to `FeedbackEngine`.

4.  **Considerations for Implementation**:
    *   **Token Limits**: Injecting verbose context directly into prompts can quickly consume token limits. Summarization or selective inclusion of context might be necessary.
    *   **Contextual Relevance**: Not all context metadata might be relevant for every prompt. Logic may be needed to determine what context to use.
    *   **User Control/Configuration**: It might be desirable to allow configuration of how (or if) chat context is used for different types of prompts or cycles. 