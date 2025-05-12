# PIPE-003: MetadataScout - Phase 3 Plan: Context-Aware PromptManager

**Agent**: Agent-4 (MetadataScout)
**Date**: {{AUTO_TIMESTAMP_ISO_DATE}}
**Task**: PIPE-003 (Phase 3 Planning) - Detail implementation for context-aware prompt selection/generation via `PromptManager`.

## 1. Objective

To enhance the `PromptManager` service to utilize `chat_context` metadata, enabling it to select or generate more contextually relevant prompts. This moves beyond simple prefix-based augmentation to a more intelligent prompt adaptation strategy.

## 2. Overview of Changes

This phase involves modifying both `PromptManager` (assuming its existence and a certain interface, or defining one if it's new) and `PromptExecutionService`.

*   **`PromptManager`**:
    *   Its `get_prompt` method will be updated to accept an optional `chat_context` dictionary.
    *   Internally, it will use this context to:
        *   Select from different versions of a base prompt (e.g., based on presence of a snippet, or type of last interaction).
        *   Or, dynamically fill placeholders in a master prompt template using context data.
*   **`PromptExecutionService`**:
    *   Will be updated to pass the `chat_context` it receives to `PromptManager.get_prompt()`.

## 3. `PromptManager` - Interface and Logic (Speculative)

**(Note: This section assumes a `PromptManager` exists. If not, its creation would be part of this phase. The following is a conceptual design.)**

### 3.1. Interface Modification

The primary method `get_prompt` in `PromptManager` would change:

*   **Current (Assumed)**: `get_prompt(self, prompt_name: str) -> str`
*   **New**: `get_prompt(self, prompt_name: str, chat_context: dict = None) -> str`

### 3.2. Internal Logic for Contextualization

Two main strategies could be employed internally by `PromptManager`:

**Strategy A: Prompt Variant Selection**

*   **Prompt Storage**: Prompts could be organized with variants.
    *   Example structure:
        ```
        prompts/
        ├── summarize_chat/
        │   ├── default.txt  # Generic summarization
        │   ├── with_snippet.txt # Variant if a snippet is available
        │   └── short_chat.txt # Variant if chat is very short (hypothetical based on future metadata)
        └── analyze_tone/
            └── default.txt
        ```
*   **Logic**:
    ```python
    # In PromptManager.get_prompt(prompt_name, chat_context):
    base_path = f"prompts/{prompt_name}/"
    selected_variant_path = base_path + "default.txt" # Default

    if chat_context:
        if chat_context.get("snippet"):
            variant_path = base_path + "with_snippet.txt"
            if os.path.exists(variant_path): # Check if specific variant exists
                selected_variant_path = variant_path
        # Add more rules based on other chat_context fields (e.g., last_active_time, future turn_count)
        # Example:
        # if chat_context.get("turn_count", 0) < 3:
        #    variant_path = base_path + "short_chat.txt"
        #    if os.path.exists(variant_path):
        #        selected_variant_path = variant_path
    
    # Load and return content from selected_variant_path
    # ...
    ```

**Strategy B: Template-Based Prompt Generation**

*   **Prompt Storage**: A single template file per prompt_name, with placeholders for context.
    *   Example `prompts/summarize_chat/template.txt`:
        ```
        {{#if chat_context.snippet}}
        Considering the previous turn ended with: "{{chat_context.snippet}}"
        {{/if}}
        {{#if chat_context.last_active_time}}
        (This chat was last active: {{chat_context.last_active_time}})
        {{/if}}

        Please summarize the key points of the current chat.
        {{#if chat_context.title}}
        The title of this chat is "{{chat_context.title}}".
        {{/if}}
        ```
*   **Logic**:
    *   Use a templating engine (e.g., Jinja2) to render the prompt template with the `chat_context`.
    ```python
    # In PromptManager.get_prompt(prompt_name, chat_context):
    template_path = f"prompts/{prompt_name}/template.txt"
    # Load template content
    # Initialize templating engine (e.g., Jinja2)
    # Render template with chat_context (if provided, else an empty context)
    # Return rendered prompt string
    # ...
    ```

**Hybrid Approach**: A combination could also be used (e.g., select a base template variant, then fill it).

### 3.3. Default Behavior
If `chat_context` is `None` or contains no usable fields for the given `prompt_name`, `PromptManager` should return a default/generic version of the prompt.

## 4. `PromptExecutionService` Modifications

*   **File**: `src/dreamos/chat_engine/prompt_execution_service.py`
*   **Method**: `execute_prompt_cycle` (and consequently `execute_prompts_single_chat`, `_execute_single_prompt_thread` which call it).
*   **Change**:
    *   Currently, `prompt_text` is retrieved via `self.prompt_manager.get_prompt(prompt_name)` *before* the direct augmentation logic.
    *   This needs to change so that `chat_context` is passed to `self.prompt_manager.get_prompt()`.
    *   The direct prompt augmentation logic (Phase 2) might then become redundant if `PromptManager` handles all contextualization, or it could be a fallback/additional step. This needs careful consideration to avoid double-contextualization or conflicting logic. **Decision for now: Phase 3 `PromptManager` contextualization will *replace* the Phase 2 direct augmentation in `PromptExecutionService` to avoid complexity.** `PromptExecutionService` will simply pass context to `PromptManager`.

    Revised logic snippet in `PromptExecutionService.execute_prompt_cycle`:
    ```python
    # In PromptExecutionService.execute_prompt_cycle:
    # ... (logging of received chat_context) ...

    # Get prompt from PromptManager, now passing context
    prompt_text = self.prompt_manager.get_prompt(prompt_name_from_cycle_or_list, context=chat_context) # Assuming prompt_name is available

    # The direct augmentation logic from Phase 2 would be removed or disabled if
    # PromptManager is now fully responsible for contextualization.

    # ... (rest of the method: _send_prompt(prompt_text), _fetch_response, etc.) ...
    ```
    (This assumes `prompt_name_from_cycle_or_list` is passed into `execute_prompt_cycle` or accessible, which it is in calling methods like `execute_prompts_single_chat`).

## 5. Configuration

*   Structure of `prompts/` directory for variants or templates needs to be standardized.
*   Choice of templating engine (if Strategy B is used).
*   Rules for selecting variants or filling templates could potentially be configurable.

## 6. Impact and Next Steps

*   This change centralizes prompt contextualization logic within `PromptManager`.
*   Requires careful design of the prompt file structure and/or templating language.
*   Implementation will involve significant work in `PromptManager` and minor adjustments in `PromptExecutionService`.
*   Testing will need to verify correct prompt selection/generation for various context scenarios.

## 7. Open Questions/Considerations:
*   Which strategy (A, B, or Hybrid) for `PromptManager` is preferable? (Strategy B with Jinja2 is powerful but adds a dependency).
*   How to handle missing prompt variants or malformed templates gracefully?
*   How to manage the complexity of many prompt variants if Strategy A is chosen extensively?

</rewritten_file> 