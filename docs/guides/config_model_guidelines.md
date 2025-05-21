# Dream.OS Configuration Model Guidelines

This document outlines the best practices for defining and using configuration models (like `AppConfig`, `GuiAutomationConfig`, etc.) within the Dream.OS framework. Following these guidelines helps prevent complex circular import errors and ensures a stable, predictable configuration loading process.

## 🧠 Dream.OS Engineering Principle: Config Isolation Rule

> **Dream.OS configs (`AppConfig`, `GuiAutomationConfig`, `DreamscapeConfig`) must never depend on runtime services or agent classes.**
> Configs define the system — they must not *load* the system.

Configuration models should be simple data structures. They represent the *settings* for the system, but they should not trigger the loading or execution of the services, agents, or tools they configure during their own import or definition phase.

## 🚫 Violations to Avoid

To adhere to the Config Isolation Rule, strictly avoid the following patterns:

*   ❌ **`AppConfig` importing any agent or orchestrator modules**: The core application configuration should not depend on the specific implementations of agents or runtime services it configures.
*   ❌ **`GuiAutomationConfig` triggering runtime logic during import**: Configuration models for subsystems (like GUI automation) must not execute file I/O, environment checks, or other runtime logic simply by being imported.
*   ❌ **`DreamscapeConfig` indirectly referencing any scanner or tool-based utility**: Subsystem configurations should not import or depend on utilities from other parts of the system, especially tools, as this creates tight coupling and risks import cycles.

## ✅ Best Practices for `dreamos.core.config` and siblings

Follow these best practices when defining configuration models:

| ✅ Practice                                                                                                     | Reason                                       |
| -------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| Define Pydantic models **purely with primitives or local types**                                               | Prevents hidden dependency chains            |
| Use **`TYPE_CHECKING` + forward references** for any delayed types                                             | Avoids circular runtime references           |
| **Isolate dynamic logic** (e.g., loading files, parsing env) into `load_config()` functions — not class bodies | Keeps models declarative                     |
| **Run `model_rebuild()` only in one place**, and after all models are guaranteed to exist                      | Ensures forward references resolve correctly |

## 📜 Code Snippet (Safe Pattern)

This example demonstrates using `TYPE_CHECKING` and forward references (`\'GuiAutomationConfig\'`) to safely link configuration models without creating runtime import dependencies. The `model_rebuild()` call is deferred until all necessary models are defined.

```python
# core/config.py
from pydantic import BaseModel
from typing import TYPE_CHECKING

# Use TYPE_CHECKING block for imports needed only for type hints
if TYPE_CHECKING:
    # Assuming GuiAutomationConfig is defined elsewhere, e.g., in automation/config.py
    # This import only happens during static type checking, not at runtime.
    from dreamos.automation.config import GuiAutomationConfig

class AppConfig(BaseModel):
    # Use a string literal (forward reference) for the type hint
    gui: 'GuiAutomationConfig'
    version: str
    # ... other primitive fields ...

# Safe deferred rebuild after everything potentially needed by AppConfig
# (including GuiAutomationConfig in this example) has been imported/defined.
# This call should ideally happen at a point where all relevant modules
# have completed their top-level imports.
AppConfig.model_rebuild()
```

Adhering to these guidelines will significantly reduce the risk of encountering circular import errors related to configuration and contribute to a more robust and maintainable Dream.OS codebase. 