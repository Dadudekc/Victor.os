# ChatCycleController (`src/dreamos/chat_engine/chat_cycle_controller.py`)

## Overview

The `ChatCycleController` serves as the master orchestrator for automated chat interaction cycles. It manages the workflow of scraping chat information, executing a series of prompts against chats, handling responses, updating memory systems, and dispatching information (e.g., to Discord).

## Key Responsibilities

*   Initializing and configuring dependent services (`ChatScraperService`, `PromptExecutionService`, `FeedbackEngine`, `DiscordDispatcher`).
*   Managing the overall chat processing loop (`start()` method).
*   Retrieving a list of chats to process via `ChatScraperService`, now including enhanced metadata (`title`, `link`, `last_active_time`, `snippet`).
*   Iterating through each chat and processing it (`process_chat()` method).
*   Loading individual chats using `ChatScraperService`.
*   Retrieving and executing a sequence of prompts for each chat using `PromptExecutionService`, now passing scraped chat context metadata.
*   Saving prompt responses and run summaries.
*   Interacting with `FeedbackEngine` to parse responses and update memory.
*   Dispatching results or specific content via `DiscordDispatcher`.
*   Optionally archiving chats after processing.
*   Providing a method to run a single prompt on a single chat (`run_single_chat()`).

## Core Methods

### `__init__(...)`
*   Initializes the controller, setting up configuration and instantiating required services (or using provided instances).

### `start(self)`
*   The main entry point to begin the automated chat processing cycle.
*   Calls `ChatScraperService.get_all_chats()` to get the list of chats (including new metadata).
*   Iterates through the `chat_list`, calling `process_chat()` for each.

### `process_chat(self, chat)`
*   Handles the processing for a single chat item (received as a dictionary from `ChatScraperService`).
*   Extracts chat `title`, `link`, `last_active_time`, and `snippet`.
*   Logs this metadata.
*   Loads the chat using `ChatScraperService.load_chat()`.
*   Iterates through a configured list of prompt names (`prompt_cycle`):
    *   Retrieves prompt text using `PromptExecutionService.get_prompt()`.
    *   Constructs a `scraper_chat_context` dictionary containing the scraped metadata for the current chat.
    *   Calls `PromptExecutionService.send_prompt_and_wait(prompt_text, chat_context=scraper_chat_context)` to execute the prompt, now passing the context.
    *   Saves the response.
    *   Updates memory via `FeedbackEngine`.
    *   Dispatches via `DiscordDispatcher`.
*   Saves an aggregated `run_metadata` summary for the chat, now including the scraped `chat_last_active` and `chat_snippet` fields.
*   Optionally archives the chat.

### `run_single_chat(self, chat_link, prompt_name)`
*   Allows execution of a single named prompt on a specified chat link.
*   Constructs a `scraper_chat_context` (with placeholders for `last_active_time` and `snippet` as it doesn't have the full list context by default) and passes it to `PromptExecutionService.send_prompt_and_wait()`.

### `_save_prompt_response(...)`, `_save_run_summary(...)`
*   Internal helper methods for saving data to files.

### `shutdown(self)`
*   Placeholder for any cleanup operations.

## Metadata Integration (PIPE-003)

*   The controller now expects richer chat objects from `ChatScraperService` (including `last_active_time`, `snippet`).
*   It extracts this metadata and packages it into a `chat_context` dictionary.
*   This `chat_context` is passed to `PromptExecutionService` when executing prompts, enabling the execution service to be aware of the broader context of the chat it's interacting with.
*   The scraped metadata is also included in the per-chat run summary logs.
*   Refer to `ai_docs/api_docs_and_integrations/README.md` for the full data flow and schema.

## Configuration

Relies on a configuration mechanism (e.g., `chat_mate_config.Config` or a stubbed version) to get settings like model name, output directory, excluded chats, prompt cycle list, etc.
