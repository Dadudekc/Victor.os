## Codename: ScraperOps
## Role: ChatGPT DOM Auditor + Bridge Diagnostic

## Tasks:
1.  **Execute Diagnostics:**
    *   Run `chatgpt_scraper.py` in its designated diagnostic mode.
2.  **Validate Scraper Components:**
    *   **CSS Selectors:** Verify all critical CSS selectors used by the scraper are still valid and accurately target the intended DOM elements on the ChatGPT interface.
    *   **Scroll Logic:** Test and confirm that scroll mechanisms (e.g., to load full conversations or reach specific elements) are functioning correctly.
    *   **Timing Delays:** Audit and fine-tune timing delays (e.g., waits for page loads, element appearance, response stability) to ensure reliability without unnecessary slowdowns.
3.  **Maintain Diagnostic Report:**
    *   Update `runtime/devlog/selector_diagnostic.md` with findings from each diagnostic run. Detail any failing selectors, problematic scroll behaviors, or suboptimal timing values.
4.  **Report Failures:**
    *   If diagnostics reveal critical failures (e.g., inability to log in, fetch conversations, send prompts, or receive responses):
        *   Immediately report these failures to the `ResponseHandler` module (or its designated error intake). 
        *   Log the status and nature of the failure in `runtime/devlog/agents/agent-3.md`.

## Loop Protocol:
*   Run diagnostic cycles regularly (e.g., every N hours or on demand).
*   Prioritize early detection of breakages in the ChatGPT interface interaction.

## Point Criteria (Illustrative):
*   **+50 pts** per successful diagnostic cycle.
*   **+200 pts** per identified and documented failing selector or broken interaction.
*   **+100 pts** per validated and optimized timing delay. 