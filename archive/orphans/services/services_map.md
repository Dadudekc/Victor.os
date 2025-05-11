# Dream.OS Services Map

This document outlines the modules within the `src/dreamos/services/` package.

## Top-Level Services

- **`config.py`**: Handles loading and accessing application configuration.
- **`failed_prompt_archive.py`**: Service to archive prompts that have failed execution.

## Sub-Packages

### `services/hooks/`

- Purpose: Contains modules for pluggable hooks or event listeners that extend core functionality.
- Contents: _(Requires further inspection)_

### `services/monitoring/`

- Purpose: Modules related to monitoring system health, performance, agent status, etc.
- Contents: _(Requires further inspection)_

### `services/utils/`

- Purpose: Shared utility modules used across various services or potentially other parts of the application.
- Contents:
    - **`common.py`**: General utilities and constants (e.g., retry decorator). Originated from `social` package.
    - **`config_loader.py`**: _(Purpose needs confirmation - might overlap with `services/config.py`)_
    - **`cursor.py`**: Utilities for Cursor interaction (originated from `social`).
    - **`devlog_analyzer.py`**: Analyzes development logs (originated from `social`).
    - **`devlog_dispatcher.py`**: Dispatches development logs (originated from `social`).
    - **`devlog_generator.py`**: Generates development logs (originated from `social`).
    - **`feedback_processor.py`**: Processes feedback (originated from `social`).
    - **`logging_utils.py`**: Provides JSON-based event logging wrappers (originated from `social`).
    - **`login_utils.py`**: Utilities potentially for web scraping login flows.
    - **`performance_logger.py`**: Utility class and decorator for tracking code execution time.
    - **`selenium_utils.py`**: Helper functions for Selenium WebDriver (originated from `social`).
    - **`chatgpt_scraper.py`**: Utility for scraping ChatGPT (originated from `social`).

## Archived Modules (in `src/dreamos/_archive/`)

- `event_logger.py`
- `voice_engine.py`
- `gui_utils.py`
- `file_manager.py`
