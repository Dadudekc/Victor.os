# Architecture: Social Media Manager

**Task:** `SOCIAL-MEDIA-MANAGER-INIT-001`
**Status:** Design Phase

## 1. Overview

This document outlines the proposed architecture for a Social Media Manager agent capability within Dream.OS. The primary goal is to enable automated, stealthy interaction with social media platforms (initially X, Instagram, TikTok) for tasks like posting content, monitoring trends, and potentially managing interactions. A key requirement is to avoid detection as a bot, necessitating the use of tools like `undetected-chromedriver`.

## 2. Core Concepts

*   **Stealth Automation:** Utilizing browser automation techniques that mimic human behavior to avoid detection and blocking by social media platforms.
*   **Platform Adapters:** Modular components specific to each social media platform (X, Instagram, TikTok) handling login, posting, and other interactions via their respective web interfaces.
*   **Content Scheduler:** A system to manage and schedule posts across different platforms at specified times.
*   **Session Management:** Securely handling login credentials and maintaining persistent browser sessions using cookies.
*   **Job Queue:** A mechanism (likely integrated with the Dream.OS task system or a dedicated queue) to manage asynchronous social media tasks (e.g., "post this image to Instagram at 10 AM").
*   **Configuration:** Secure storage for platform credentials, scheduling parameters, and browser settings.

## 3. Proposed Architecture

1.  **Core Engine (`dreamos.core.social.manager`)**
    *   Orchestrates social media tasks.
    *   Manages the job queue (or interfaces with the main task system).
    *   Loads platform adapters and configurations.
    *   Provides an API or capability (`social.post`, `social.schedule`, `social.login`) for agents.

2.  **Browser Automation Layer (`dreamos.core.social.browser`)**
    *   Abstraction over `undetected-chromedriver`.
    *   Manages WebDriver instances (potentially pooled).
    *   Handles browser profiles, cookies, and proxy settings.
    *   Provides functions for common browser actions (navigation, clicks, typing, element finding) designed to appear human-like (e.g., incorporating random delays).

3.  **Platform Adapters (`dreamos.core.social.adapters.<platform>`)**
    *   Separate modules for each platform (e.g., `x_adapter.py`, `instagram_adapter.py`).
    *   Each adapter uses the Browser Automation Layer to interact with the specific platform's website.
    *   **Responsibilities:**
        *   `login(username, password)`: Handles platform-specific login flow, saving/loading cookies.
        *   `post(content, media_paths=None)`: Handles the creation and submission of posts (text, images, videos).
        *   `get_profile_info()`: (Optional) Fetches basic profile data.
        *   `search(query)`: (Optional) Performs searches.
        *   Other platform-specific actions.
    *   Requires robust CSS selectors or XPath expressions to locate web elements, which may need frequent updates if site structure changes.

4.  **Content Scheduler (`dreamos.core.social.scheduler`)**
    *   Stores scheduled posts (platform, content, media, time).
    *   Could leverage the main Dream.OS scheduling system or a dedicated scheduling library (e.g., APScheduler).
    *   Triggers jobs at the appropriate time, invoking the Core Engine to execute the post via the correct adapter.

5.  **Configuration (`config/social_media.yaml` or similar)**
    *   Secure storage (e.g., using environment variables or a secrets manager) for credentials.
    *   Paths to `chromedriver`.
    *   Browser profile locations.
    *   Proxy configurations.
    *   Platform-specific settings (e.g., timeouts, retry counts).

6.  **Error Handling & Monitoring**
    *   Robust error handling for WebDriver issues, element-not-found errors, login failures, and platform blocks.
    *   Logging of all actions and errors.
    *   Potential alerts for repeated failures or suspected detection.

## 4. Key Technologies

*   **`undetected-chromedriver`:** Python library to automate Chrome/Chromium while patching it to prevent detection by bot mitigation systems like Cloudflare, Akamai, etc.
*   **`selenium`:** Core browser automation library used by `undetected-chromedriver`.
*   **(Optional) `APScheduler`:** For implementing the content scheduler if a dedicated one is needed.
*   **(Dependency) `webdriver-manager`:** Useful for automatically downloading and managing the correct ChromeDriver executable.

## 5. Implementation Steps & Next Tasks

1.  **Setup Base Environment:** Add `undetected-chromedriver`, `selenium`, `webdriver-manager` dependencies (Requires fixing `pyproject.toml` editing). - **BLOCKER**
2.  **Implement Browser Automation Layer:** Create the core WebDriver management and interaction functions. (`SOCIAL-MEDIA-MANAGER-BROWSER-LAYER-001.1`)
3.  **Implement Initial Platform Adapter (e.g., X):** Focus on login (`SOCIAL-MEDIA-MANAGER-LOGIN-002`) and basic posting (`SOCIAL-MEDIA-MANAGER-X-POST-001.2`).
4.  **Develop Core Engine & Capability Interface:** Define how agents will trigger social media actions. (`SOCIAL-MEDIA-MANAGER-CORE-API-001.3`)
5.  **Implement Scheduler:** Build or integrate the scheduling mechanism. (`SOCIAL-MEDIA-MANAGER-SCHEDULER-003`)
6.  **Add Adapters for Other Platforms:** Implement Instagram, TikTok adapters. (`SOCIAL-MEDIA-MANAGER-IG-ADAPTER-001.4`, `SOCIAL-MEDIA-MANAGER-TIKTOK-ADAPTER-001.5`)
7.  **Testing & Refinement:** Extensive testing to ensure stealth and reliability.

## 6. Security & Ethical Considerations

*   **Credential Security:** Credentials must be stored securely, never hardcoded.
*   **Rate Limiting:** Respect platform terms of service; implement delays and avoid excessive automation to prevent account suspension.
*   **Ethical Use:** Ensure automation is used responsibly and not for spamming or malicious activities.
*   **Maintenance:** Platform website changes will require adapter updates. 