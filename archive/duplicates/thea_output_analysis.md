# THEA Output Extraction Analysis (Passive Mode - Cycles 13, 16, 17, 18)

**Goal:** Automate capturing THEA's reply text from the Cursor interface.

**Current Manual Process (Assumed):**
1. User/Agent sends prompt to THEA (via some mechanism, possibly external script or direct interaction).
2. THEA processes and generates a reply.
3. THEA's reply appears within the Cursor chat interface (specific UI element TBD).
4. User/Agent manually selects and copies this text.
5. Copied text is pasted elsewhere (e.g., back into a script, log file, or another prompt).

**Potential Automation Strategies (Memory/Theory + Codebase Scan Results):**

1.  **Existing GUI Automation Tools (Confirmed):**
    *   `src/dreamos/automation/cursor_orchestrator.py`: High-level manager.
    *   `src/dreamos/tools/functional/gui_interaction.py`: Contains **`copy_cursor_response()`**. **Potential Reliability Issue:** Comments in this file indicate the response waiting mechanism is a simple, fixed `time.sleep(RESPONSE_WAIT_TIMEOUT)`, described as "unreliable". This fixed delay won't account for variable response times from THEA, leading to premature copy attempts (missing data) or excessive waiting (inefficiency).
    *   `src/dreamos/core/bots/orchestrator_bot.py`: Base class.
    *   *Assessment:* The existence of `copy_cursor_response()` is promising, but its reliance on a fixed sleep timer is a major concern for robustness. Improving the wait mechanism (e.g., image detection of a 'finished' state, OCR polling, or ideally event-based notification if possible) is critical.

2.  **Cursor API/Hooks (Ideal - Still Unknown):**
    *   *Assessment:* Remains the best potential solution if an event or API exists for detecting when a response is fully rendered.

3.  **Accessibility APIs (Alternative):**
    *   *Assessment:* Good alternative if GUI automation proves too fragile. Might offer ways to check UI state changes indicative of response completion.

4.  **Log File Monitoring (Fallback):**
    *   *Assessment:* Last resort.

**Updated Recommendation (Passive):**
Analyze `copy_cursor_response()` in `gui_interaction.py` when tools are stable. Primary focus: Assess and propose improvements to the unreliable fixed-delay waiting mechanism before attempting extraction. Consider image recognition (`pyautogui.locateOnScreen`) for a UI element indicating completion, or explore Accessibility API events.

**Coordination Notes (from Devlog):**
- Widespread, intermittent tool timeouts reported (Agents 1, 3, 7, 8), primarily affecting `list_dir` and `read_file`.
- Agent-8 hypothesis: Issue may lie with specific tool implementations or external provider, as `grep_search` often succeeds where others fail.
- Agent-8 escalated issue to Captain THEA.
- Agent-4 is also analyzing Cursor interaction tools.

**Proposed Wait Mechanism Improvements (Cycle 2 - Reset):**

Instead of the fixed `time.sleep(RESPONSE_WAIT_TIMEOUT)` (currently 30s) in `interact_with_cursor`, consider these alternatives:

1.  **Visual Cue Detection (Image Recognition) - Preferred Initial Approach:**
    *   **Step 1: Identify Cue:** Manually observe Cursor during THEA responses. Identify a stable visual element indicating completion (e.g., a specific icon, button state change, disappearance of a progress indicator). Save a screenshot snippet as `thea_response_complete_cue.png` (location TBD, maybe `runtime/assets/gui_templates/`).
    *   **Step 2: Implement Wait Loop:** Replace `time.sleep(RESPONSE_WAIT_TIMEOUT)` in `interact_with_cursor` with a loop.
        *   Inside the loop, use `pyautogui.locateOnScreen('path/to/thea_response_complete_cue.png', confidence=0.8)` (adjust confidence as needed).
        *   Sleep for a short interval (e.g., `RESPONSE_CHECK_INTERVAL` = 1s, defined in the file) between checks.
        *   Implement a total timeout (e.g., `RESPONSE_WAIT_TIMEOUT` * 2 = 60s) to prevent infinite loops if the cue never appears.
        *   If the cue is found, break the loop and proceed to `copy_cursor_response()`.
        *   If the loop times out, log an error and return `None`.
    *   *Pros:* More dynamic than fixed wait. Directly tied to UI state. Leverages existing `pyautogui`.
    *   *Cons:* Brittle to UI visual changes. `locateOnScreen` performance/reliability needs testing. Requires a reliable visual cue.

2.  **Accessibility API Event Monitoring:**
    *   If Cursor uses standard UI frameworks, it might emit accessibility events when the chat content changes or updates.
    *   Use platform-specific accessibility libraries (`pywinauto`, `pyatomac`, AT-SPI for Linux) to listen for events related to the chat output area.
    *   Wait for a specific event pattern (e.g., content update finished, focus change) before triggering the copy.
    *   *Pros:* Potentially more robust to visual changes than image recognition. Can be event-driven rather than polling.
    *   *Cons:* Steeper learning curve. Platform-specific. Depends on Cursor implementing accessibility features correctly.

3.  **OCR Polling (Less Ideal):**
    *   Periodically take screenshots of the response area.
    *   Use Optical Character Recognition (OCR - e.g., `pytesseract`) to extract text.
    *   Wait until the extracted text stops changing for a certain duration (indicating completion).
    *   *Pros:* Doesn't rely on specific UI elements.
    *   *Cons:* Very slow, CPU-intensive, prone to OCR errors. Complex to implement reliably.

**Recommendation:** Implement and test Visual Cue Detection first. If unstable, investigate Accessibility APIs.

**Coordination Notes (from Devlog):**
...

**Next Steps (Active):**
- **Implement Visual Cue Detection logic** within a copy of `interact_with_cursor` or as a new helper function.
- Manually identify and capture the `thea_response_complete_cue.png`.
- Test the new wait mechanism robustly.
- If successful, propose replacing the old wait logic in `gui_interaction.py`.
