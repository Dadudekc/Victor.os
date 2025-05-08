# Configuration Management Standard

**Version:** 1.0
**Status:** ACTIVE
**Related Tasks:** ORG-CONFIG-STD-001

## Overview

This document outlines the standard approach for managing configuration within
the Dream.OS project.

## Standard Mechanism: `AppConfig`

The primary and **required** method for accessing configuration values is
through the central `AppConfig` class, defined in
`src/dreamos/config.py`.

**Key Features:**

- **Centralized Definition:** All core configuration settings (paths, logging
  levels, timeouts, feature flags, etc.) are defined using Pydantic models
  within `src/dreamos/config.py`.
- **Type Safety:** Pydantic enforces data types, provides validation, and helps
  prevent runtime errors due to incorrect configuration values.
- **Default Values:** Sensible defaults are defined directly in the models.
- **Loading Mechanism:** Configuration is loaded via the `AppConfig.load()`
  class method (which utilizes the `load_config()` utility).
- **File Location:** By default, `AppConfig.load()` attempts to load settings
  from `runtime/config/config.yaml` (path may vary, see `load` method logic).
- **Path Resolution:** Relative paths specified in the config file or defaults
  are automatically resolved relative to the project root directory.
- **Directory Creation:** Necessary directories specified in the configuration
  (e.g., log directory, memory paths) are automatically created on load if they
  don't exist (`_ensure_dirs_exist`).
- **Extensibility:** New configuration sections can be added by defining new
  Pydantic models and incorporating them into `AppConfig`.

## Loading Configuration

- The `AppConfig` object is typically loaded once at application startup (or agent initialization) using the `AppConfig.load()` class method.

  ```python
  from dreamos.config import AppConfig

  # Load the configuration (typically once at application/agent start)
  config = AppConfig.load()

  # Optionally, pass a specific path:
  # config = AppConfig.load('path/to/custom_config.yaml')
  ```
- The `load()` method handles finding the config file (e.g., in `runtime/config/` or project root), reading it, handling missing files, validating against the Pydantic models, and applying defaults.
- It may also incorporate logic to merge or override settings with environment variables (verify `load_config` utility if this behavior is critical).

## Accessing Configuration in Modules/Agents

- Modules, agents, or services that require configuration parameters **should receive** the fully loaded `AppConfig` instance (or relevant subsections/values derived from it) during their initialization (e.g., via the constructor `__init__`).

  ```python
  from dreamos.config import AppConfig # Assuming AppConfig holds all nested configs

  class MyAgent:
      def __init__(self, agent_id: str, config: AppConfig):
          self.agent_id = agent_id
          self.config = config
          # Access settings via the passed config object
          self.log_level = self.config.logging.level
          self.memory_path = self.config.paths.memory
          # ... get other needed settings ...

      # ... rest of agent logic ...
  ```

- **Avoid:** Accessing global state or re-loading configuration (`AppConfig.load()`) within individual modules after initial setup. Configuration should flow down from the application entry point via dependency injection.

## Exceptions: `os.getenv`

- Direct use of `os.getenv()` within core application logic (`src/dreamos/`) is **strongly discouraged** for accessing configuration settings.
- **Allowed Exceptions:**
  - Accessing secrets or credentials (e.g., API keys, tokens) that should _not_ be stored in configuration files. Use environment variables or a dedicated secrets management solution.
  - Accessing environment-specific variables needed _very early_ in the startup process, potentially *before* `AppConfig` is loaded (e.g., path to the config file itself, environment stage like `DEV`/`PROD`, port numbers). Use sparingly and document clearly.

## Rationale

Using a central `AppConfig` loaded via `AppConfig.load()` ensures:

- **Consistency:** All components access configuration the same way.
- **Predictability:** Loading order, validation, defaults, and overrides are defined in one place (`config.py` and the `load` method).
- **Testability:** Configuration can be easily mocked or injected during testing by passing a custom `AppConfig` instance.
- **Maintainability:** Changes to configuration structure are localized to `config.py`.
