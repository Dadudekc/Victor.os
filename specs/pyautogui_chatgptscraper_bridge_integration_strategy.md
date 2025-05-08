# PyAutoGUI to ChatGPTScraper Bridge: Integration Strategy

## 1. Current State Analysis

*   **`src/dreamos/agents/chatgpt_web_agent.py`**:
    *   Interacts directly with the live ChatGPT website using Selenium for UI automation (launching browser, navigation, login, injecting prompts, and scraping replies).
    *   Uses `html_parser.extract_latest_reply` for scraping, suggesting a focus on text-based replies.
    *   Communicates via a C2 channel and interacts with `TaskNexus`.
*   **`src/dreamos/bridge/bridge_loop.py`**:
    *   A file-based polling loop.
    *   Monitors `cursor_to_gpt.jsonl` for incoming prompts from the "Cursor" side of the system.
    *   Crucially, **it currently *simulates* GPT API calls** via its `call_gpt_api` function. It does not interact with the live ChatGPT service or `chatgpt_web_agent.py`.
    *   Writes simulated responses to `gpt_to_cursor.jsonl`.
    *   Attempts to import and use a `log_interaction` function from a `runtime/modules/chatgpt_scraper/scraper.py` module, implying an intention for interaction logging.
*   **Identified Disconnect**: The primary issue is that `bridge_loop.py` (which seems to be the intended interface for the broader system to access GPT functionalities) is not connected to `chatgpt_web_agent.py` (the component that actually interacts with live ChatGPT). The "GPT" interaction in the bridge is currently faked.

## 2. Proposed Bridge Architecture & Workflow

The core idea is to make `bridge_loop.py` utilize `chatgpt_web_agent.py` to process prompts against the live ChatGPT service.

1.  **Prompt Ingestion**: `bridge_loop.py` continues to monitor `cursor_to_gpt.jsonl` for new prompts.
2.  **Delegation to `chatgpt_web_agent.py`**:
    *   When `bridge_loop.py` picks up a new prompt, instead of calling its local `call_gpt_api` simulation, it will make a request to an instance of `ChatGPTWebAgent`.
    *   This request could be facilitated through an inter-agent communication mechanism (e.g., AgentBus, if available and appropriate, or a dedicated message queue/API if `chatgpt_web_agent.py` is run as a separate service/process). For simplicity, initially, this might involve `bridge_loop.py` directly instantiating or invoking methods on `ChatGPTWebAgent` if they run in the same process space, or using the existing C2 channel/TaskNexus if suitable.
3.  **Live ChatGPT Interaction via `chatgpt_web_agent.py`**:
    *   `ChatGPTWebAgent` receives the prompt.
    *   It uses its Selenium-based (and PyAutoGUI-enhanced, see section 3) mechanisms to:
        *   Navigate to the correct conversation URL.
        *   Inject the prompt text into the ChatGPT UI.
        *   Trigger the send action.
        *   Wait for and scrape the reply from the ChatGPT UI.
4.  **Response Return**: `ChatGPTWebAgent` returns the scraped reply to `bridge_loop.py`.
5.  **Output Generation**: `bridge_loop.py` takes the actual reply and writes it to `gpt_to_cursor.jsonl` for the "Cursor" side to consume.
6.  **Logging**: The `log_interaction` function (from `runtime/modules/chatgpt_scraper/scraper.py`) should be called by `bridge_loop.py` or `chatgpt_web_agent.py` with the *actual* prompt and *actual* response.

## 3. Role of PyAutoGUI

PyAutoGUI will be integrated into `chatgpt_web_agent.py` to enhance its UI automation capabilities, particularly where Selenium might be less reliable or unable to perform certain actions:

*   **Robust Prompt Injection**: If Selenium's `send_keys` to the textarea proves flaky (e.g., due to UI changes, focus issues), PyAutoGUI can be used as a fallback or primary method for typing text and simulating "Enter" presses.
*   **Complex UI Navigation**: For any UI elements that are difficult to target with Selenium selectors (e.g., dynamic elements without stable IDs/classes, elements within iframes if not handled well by Selenium, custom UI controls).
*   **Ensuring Visibility/Focus**: PyAutoGUI can be used to programmatically scroll the window or click specific parts of the UI to ensure elements are visible and active before Selenium attempts to interact with them.
*   **Handling Non-Standard Interactions**: If the "scraping" process requires interacting with browser dialogs (though unlikely for ChatGPT text scraping), or specific browser extension UIs that are part of the workflow, PyAutoGUI would be necessary.
*   **Error Recovery**: If Selenium encounters an unexpected state, PyAutoGUI could potentially perform actions like refreshing the page, closing pop-ups, or attempting to re-focus the input area.

## 4. Role of "ChatGPTScraper" Module

*   **Current Functionality**: Based on `bridge_loop.py`'s import attempt, `runtime/modules/chatgpt_scraper/scraper.py` provides a `log_interaction(prompt, response, tags)` function. Its primary role appears to be logging interaction pairs.
*   **Enhanced Scraping (If Required)**: The term "ChatGPTScraper" in the project priority suggests that the scraping needs might go beyond simply extracting the last text reply (which `html_parser.extract_latest_reply` currently does).
    *   If more structured data needs to be scraped (e.g., code blocks with their language, specific formatted outputs, user/assistant turn distinctions beyond the last reply), the scraping logic within `chatgpt_web_agent.py` will need to be enhanced.
    *   PyAutoGUI might assist here by navigating the UI to ensure all relevant parts of a conversation are loaded/visible for a more comprehensive scrape by Selenium or a dedicated HTML parsing utility.

## 5. Proposed Sub-Tasks for Implementation

1.  **Task 1: Refactor `bridge_loop.py` for Real GPT Interaction.**
    *   **Description**: Modify `bridge_loop.py` to remove the simulated `call_gpt_api`. Implement a mechanism for it to send prompts to `chatgpt_web_agent.py` and receive real responses. This might involve defining an interface/API or using an existing agent communication bus.
    *   **Key activities**: Define communication protocol, modify `relay_prompt_to_gpt` in `bridge_loop.py`.
2.  **Task 2: Enhance `chatgpt_web_agent.py` to Service `bridge_loop.py` Requests.**
    *   **Description**: Add methods/endpoints to `chatgpt_web_agent.py` to accept prompts from `bridge_loop.py`, orchestrate the UI interaction (injection and scraping), and return the scraped response. Ensure it can handle multiple requests if `bridge_loop.py` processes prompts in batches or quickly.
    *   **Key activities**: Design request handling, ensure proper state management if multiple conversations/prompts are handled.
3.  **Task 3: Integrate PyAutoGUI into `chatgpt_web_agent.py` for Robust UI Automation.**
    *   **Description**: Identify specific Selenium interaction points in `chatgpt_web_agent.py` (e.g., prompt injection, button clicks) that could benefit from PyAutoGUI's robustness. Implement PyAutoGUI alternatives or fallbacks for these actions.
    *   **Key activities**: Develop utility functions using PyAutoGUI for common UI actions (typing, clicking, scrolling, focus management), integrate into existing Selenium workflow.
4.  **Task 4: Investigate and Verify `chatgpt_scraper` Module and `log_interaction`.**
    *   **Description**: Locate and review `runtime/modules/chatgpt_scraper/scraper.py`. Ensure `log_interaction` is functional and correctly integrated to log the actual prompt/response pairs from the live ChatGPT interactions.
    *   **Key activities**: Test `log_interaction`, ensure logs are being saved in a useful format and location.
5.  **Task 5 (Conditional): Enhance Scraping Logic in `chatgpt_web_agent.py`.**
    *   **Description**: Based on a clearer definition of "ChatGPTScraper" requirements, if more than the latest text reply is needed, enhance the scraping capabilities of `chatgpt_web_agent.py`. This may involve more sophisticated HTML parsing or using PyAutoGUI to navigate/expose specific data elements on the page.
    *   **Key activities**: Define detailed scraping requirements, implement new parsing logic, integrate PyAutoGUI for UI manipulation if needed for advanced scraping.
6.  **Task 6: End-to-End Testing and Documentation.**
    *   **Description**: Perform comprehensive testing of the entire bridge from `cursor_to_gpt.jsonl` through live ChatGPT interaction via the enhanced `chatgpt_web_agent.py` (with PyAutoGUI) and back to `gpt_to_cursor.jsonl`. Document the new architecture and operational procedures.
    *   **Key activities**: Develop test cases, execute tests, document setup and usage.

This strategy aims to create a functional, robust bridge by leveraging existing components and enhancing them with PyAutoGUI where necessary. 