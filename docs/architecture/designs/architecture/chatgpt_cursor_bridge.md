# Architecture: ChatGPT-Cursor Bridge

**Task:** `DEFINE-BRIDGE-ARCHITECTURE-001`
**Status:** Proposed

## 1. Overview

This document outlines the architecture for a bridge service that allows an external process (e.g., a script interacting with the ChatGPT API, another Dream.OS agent) to control and interact with a running instance of the Cursor IDE. The goal is to use Cursor as the execution environment and interface for prompts generated externally.

## 2. Components

1.  **External LLM Process:** Any process capable of generating prompts and consuming text responses.
2.  **Cursor Bridge Service:** A standalone Python process responsible for mediating interactions.
3.  **Cursor IDE:** The target application.
4.  **Communication Channel:** An interface between the External LLM Process and the Bridge Service.

## 3. Proposed Architecture

*   **Bridge Implementation:** Standalone Python script (`cursor_bridge.py`).
*   **Communication:** HTTP API hosted by the Bridge Service (using Flask or FastAPI).
    *   **Endpoint:** `/interact` (POST)
        *   Request Body: `{"prompt": "<instruction_text>"}`
        *   Response Body (Success): `{"response": "<extracted_response_text>"}`
        *   Response Body (Error): `{"error": "<error_description>"}`
    *   **Workflow:** The endpoint receives a prompt, performs the UI automation and response scraping cycle, and returns the result synchronously.
*   **UI Automation:** Primarily `pyautogui`.
    *   Identify coordinates or use image recognition (`locateOnScreen`) for:
        *   Cursor chat input field.
        *   Cursor "Send" button (or simulate Enter key).
        *   Cursor response output area.
    *   Actions: Focus window, click input, type/paste prompt, click send/press Enter.
*   **Response Extraction (Initial Strategy):**
    *   Monitor the defined response area of the Cursor window.
    *   Periodically capture screenshots of the area.
    *   Use OCR (`pytesseract`) to extract text from screenshots.
    *   Aggregate text captured over time.
    *   Detect response completion when extracted text remains unchanged for a defined period (e.g., 2-3 seconds).
    *   Return the aggregated text.
*   **Error Handling:** Implement timeouts for UI actions and response detection. Return error messages via the API.

## 4. Interaction Flow

1.  External LLM Process sends a POST request to the Bridge Service's `/interact` endpoint with the prompt.
2.  Bridge Service receives the request.
3.  Bridge Service uses PyAutoGUI to focus Cursor, inject the prompt into the chat input, and trigger send.
4.  Bridge Service enters a loop:
    a.  Wait a short interval (e.g., 500ms).
    b.  Capture screenshot of Cursor response area.
    c.  Perform OCR on the screenshot.
    d.  Compare extracted text with previous text.
    e.  If text has changed, update aggregated response and reset stability timer.
    f.  If text is stable for N seconds, consider response complete.
    g.  If timeout exceeded, return error.
5.  Bridge Service returns the aggregated response text (or error) in the HTTP response.
6.  External LLM Process receives the response.

## 5. Key Challenges & Mitigation Ideas

*   **UI Automation Brittleness:**
    *   Use image recognition instead of fixed coordinates where possible.
    *   Implement retry logic for focusing/clicking actions.
    *   Add configuration for key UI element locations/images.
*   **Response Extraction Reliability:**
    *   OCR limitations (accuracy, handling code, non-text elements).
    *   *Mitigation (Future):* Explore Accessibility APIs (platform-specific) for direct text access if OCR proves insufficient.
    *   *Mitigation (Future):* Investigate if Cursor has clipboard integration or logging that could be leveraged.
*   **Synchronization:** Synchronous API simplifies initial implementation.
*   **Cursor State:** Assume Cursor is running and the relevant chat is open. Manual setup required initially.

## 6. Next Steps (Implementation Tasks)

*   `IMPLEMENT-CURSOR-INJECTOR-002`: Focus on UI automation for input.
*   `IMPLEMENT-THEA-RESPONSE-READER-003`: Focus on screenshot, OCR, and completion detection logic.
*   Integrate both into the Flask/FastAPI service.

## Execution Protocol

This section outlines the rules governing the execution flow of the Cursor Bridge interaction.

### Retry Logic

*   **Connection/Focus Failure:** [TODO: Define retry attempts and backoff strategy for `find_and_focus_cursor_window` failures.]
*   **Injection Failure:** [TODO: Define if/how injection steps (click, paste, enter) are retried.]
*   **OCR Failure:** [TODO: Define retry attempts for `extract_text_from_image` if OCR returns errors or unusable text.]
*   **Timeout:** [TODO: Define behavior when `monitor_and_extract_response` times out.]

### Fail States

*   **Unrecoverable Focus Failure:** After exhausting retries, the bridge enters a failed state, logs the error, and potentially notifies orchestration.
*   **Persistent OCR Failure:** If OCR consistently fails (e.g., Tesseract not found, unreadable image), the bridge fails.
*   **Interaction Timeout:** If the overall interaction exceeds a maximum defined duration.

### Recovery Heuristics

*   **Window Check:** Before attempting interaction, verify the Cursor window exists and is potentially active.
*   **Input Field Verification:** Attempt to verify the input field location (e.g., using image recognition) before clicking/pasting.
*   **OCR Sanity Check:** Basic checks on OCR output (e.g., not empty, doesn't contain only error markers) before declaring success.
*   **Fallback Coordinates:** If image-based location fails, use pre-configured fallback coordinates for input/response areas.
*   **State Reset:** [TODO: Define conditions under which the bridge attempts to reset its state or the Cursor window state (e.g., closing/reopening - likely requires external process management).]

### Known Issues & Blockers
- See the maintained log for current bridge implementation blockers: [[runtime/logs/cursor_bridge_blockers.md]] 