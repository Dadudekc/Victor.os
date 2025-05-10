# CSS Selector Diagnostic Guide for ChatGPT Scraper

This guide provides tips for inspecting the ChatGPT DOM and identifying correct CSS selectors if the scraper fails to extract information.

## 1. Using Browser Developer Tools

1.  **Open Developer Tools:**
    *   In the browser window opened by the interactive test script (`tools/test_scraper_interactively.py`) displaying ChatGPT, right-click on the element you want to inspect (e.g., the assistant's latest reply, the prompt input box).
    *   Select "Inspect" or "Inspect Element" from the context menu. This will open the developer tools, usually docked to the side or bottom of the browser window.

2.  **Identify Elements:**
    *   **Elements Panel:** You should see the HTML structure of the page. As you hover over HTML elements in the Elements panel, the corresponding part of the webpage will often be highlighted.
    *   **Selector Arrow:** Most developer tools have a selector icon (often looks like a mouse pointer in a box). Click this, then click on the desired element on the webpage. The Elements panel will jump to that element's HTML.

3.  **Finding a Good Selector:**
    *   **Look for `id` attributes:** IDs are unique and make for very stable selectors (e.g., `#prompt-textarea`).
    *   **Look for `data-testid` attributes:** Modern web apps often use these for testing, and they tend to be stable (e.g., `textarea[data-testid='prompt-textarea']`).
    *   **Look for descriptive `class` names:** Classes can be used, but be mindful if they are very generic or appear on many unrelated elements. Sometimes a combination of classes is needed (e.g., `div.message-bubble.assistant-reply`).
    *   **Consider element hierarchy:** If an element doesn't have a unique ID or good classes, you can select it based on its relationship to a parent element that *is* easier to select (e.g., `div#chat-container > div.latest-message > p`).
    *   **Avoid overly complex or brittle selectors:** Selectors that rely on very specific order (e.g., `div:nth-child(5) > span:nth-child(3)`) can break easily if the page structure changes slightly. Aim for selectors that are as simple and direct as possible while still being unique.

4.  **Testing Selectors:**
    *   **Console:** Most developer tools have a Console tab. You can test CSS selectors there using JavaScript:
        *   `document.querySelector("YOUR_SELECTOR_HERE")` (returns the first matching element)
        *   `document.querySelectorAll("YOUR_SELECTOR_HERE")` (returns a list of all matching elements)
    *   **Search in Elements Panel:** The Elements panel usually has a search box (Ctrl+F or Cmd+F) where you can type a CSS selector to see how many elements it matches and highlight them.

## 2. Key Selectors in `src/dreamos/services/utils/chatgpt_scraper.py`

Refer to these when inspecting. If the scraper fails, one or more of these likely needs updating:

*   **`PROMPT_BOX`**: For the main text area where prompts are typed.
    *   Current: `(By.CSS_SELECTOR, "textarea[data-testid='prompt-textarea']")`

*   **`SEND_BTN`**: For the button used to send the typed prompt.
    *   Current: `(By.CSS_SELECTOR, "button[data-testid='send-button']")`

*   **`ASSISTANT_MARKDOWN`**: For the container(s) holding the assistant's replies. The scraper typically looks for the *last* one.
    *   Current: `(By.CSS_SELECTOR, "main div[data-testid='conversation-turns'] div.markdown")`
    *   *This is the most likely candidate for changes if reply extraction is failing.* Look for the element that directly wraps the text content of the latest AI response. It might have classes related to "prose", "message", "text content", etc.

*   **`SPINNER_SELECTOR`**: For a loading spinner that might indicate the AI is still generating a response.
    *   Current: `(By.CSS_SELECTOR, "svg.animate-spin")`

*   **`SIDEBAR_CONVERSATION_LINK`**: Used if scrolling through chat history (less relevant for the immediate bridge task but good to have).
    *   Current: `(By.CSS_SELECTOR, "nav a[href*='/c/']")`


## 3. Example: Finding a new selector for `ASSISTANT_MARKDOWN`

1.  After a response appears in the interactive browser, right-click on the response text and "Inspect".
2.  Look at the selected HTML element and its parents. You are looking for a container that uniquely identifies assistant messages, and ideally the latest one or all of them so the scraper can pick the last.
3.  Common patterns:
    *   `div[class*="message-assistant"]`
    *   `div[data-role="assistant"] div.content`
    *   `div.prose` (if a general class for markdown formatted text)
4.  Test your candidate selector in the console: `document.querySelectorAll("YOUR_NEW_SELECTOR")`. It should return one or more elements. If it returns multiple, ensure the scraper's logic correctly identifies the *last* one as the latest reply.

Remember to provide the **exact new CSS selector string** if you find an update is needed. 