# Dream.OS CLI Tool Design Guidelines

This document outlines best practices for designing Command Line Interface (CLI) tools within the Dream.OS project. Adhering to these guidelines will help prevent common issues like circular imports, improve maintainability, and ensure a clear separation of concerns.

## Core Principle: Isolate CLI Scripts from Full System Imports

The most critical principle is to **treat CLI scripts as lightweight entry points** that are decoupled from the full Dream.OS runtime initialization, unless the script's explicit purpose is to launch or interact with that full runtime.

**Avoid directly importing core runtime classes or extensive parts of the system** (e.g., `BaseAgent`, `SwarmController`, `AppConfig` singletons, complex service modules) from a simple CLI utility. Such imports can lead to:
*   **Circular Dependencies:** As seen with tools that try to import `AppConfig` while `AppConfig` itself might be part of a larger initialization chain.
*   **Initialization Order Problems:** Core components might expect a certain system state or a fully loaded configuration that a standalone CLI script doesn't (and shouldn't have to) provide.
*   **Slow Execution:** Pulling in large parts of the system can make simple CLI tools slow to start.
*   **Reduced Reusability:** Tightly coupling a tool to the full system state makes it harder to test in isolation or reuse in different contexts.

## Best Practices

1.  **Define Clear Inputs:**
    *   CLI tools should primarily receive their operational parameters via command-line arguments (e.g., using `click` or `argparse`).
    *   For complex configurations, the CLI can accept a path to a dedicated configuration file (e.g., a YAML or JSON file) that it parses itself. This config file should be specific to the tool's needs or a well-defined subset of the main application config.

2.  **Pass Dependencies Explicitly:**
    *   If a CLI tool needs to interact with a system component (e.g., a specific service or a data access layer), it should ideally be designed to have these dependencies passed to its core logic functions or classes as arguments.
    *   The CLI entry point script would be responsible for instantiating and providing these dependencies.

3.  **Separate CLI Logic from Core Logic:**
    *   **CLI Script (e.g., `my_tool_cli.py`):** Handles argument parsing, basic input validation, help messages, and orchestrating the execution of the core logic. It should have minimal imports from the main system.
    *   **Core Logic Module (e.g., `my_tool_processor.py`):** Contains the actual functionality of the tool. This module can be imported by the CLI script. If this core logic needs access to system-wide configurations or services, these should be passed into its functions/classes from the CLI script.

4.  **Configuration Handling:**
    *   **Standalone Tools:** If a tool operates largely independently of the main Dream.OS application (e.g., a code scanner, a documentation generator), it should manage its own configuration or accept all necessary parameters via CLI arguments.
    *   **Integrated Tools (requiring `AppConfig`):** If a tool *must* operate with the full application context (e.g., a script that interacts with running agents or the live system state):
        *   The script should clearly indicate that it initializes and uses the main `AppConfig`.
        *   Be mindful of the import chain. The script itself becomes part of the application's import graph.
        *   Consider if the functionality could be refactored into a service that is then invoked by a very thin CLI wrapper, rather than the CLI tool itself containing complex system interactions.

5.  **Example: `AppConfig` Usage in Tools**
    *   **Problematic:** A simple utility in `dreamos.tools.utils.some_helper` directly imports and uses `dreamos.core.config.AppConfig` at the module level. This creates a direct dependency from a low-level tool to a high-level configuration component, risking circular imports if `AppConfig` or its dependencies eventually need something from `dreamos.tools`.
    *   **Better:**
        ```python
        # dreamos/tools/my_scanner/scanner_logic.py
        class ProjectScanner:
            def __init__(self, config_data: dict): # Or a specific Pydantic model for tool config
                self.root_path = config_data.get("project_root")
                # ...
            def scan(self):
                # ... use self.root_path ...
                pass

        # dreamos/tools/my_scanner_cli.py
        import click
        from dreamos.core.config import AppConfig # Only if loading the full config to pass parts
        from .scanner_logic import ProjectScanner

        @click.command()
        @click.option('--config-path', type=click.Path(exists=True), help="Path to AppConfig YAML.")
        @click.option('--project-root', type=click.Path(exists=True), help="Project root (overrides config).")
        def main(config_path, project_root_override):
            effective_project_root = None
            if project_root_override:
                effective_project_root = project_root_override
            elif config_path:
                # Load the *full* AppConfig only to extract necessary parts
                # This is acceptable if the CLI tool's purpose is to act upon the system defined by AppConfig
                full_config = AppConfig.load(config_path) # Assuming AppConfig.load is safe
                effective_project_root = full_config.paths.project_root
            else:
                # Get project_root by other means or default
                effective_project_root = "." # Example default

            if not effective_project_root:
                click.echo("Error: Project root could not be determined.", err=True)
                return

            # Pass only necessary, simple data to the scanner logic
            scanner_config_data = {"project_root": str(effective_project_root)}
            scanner = ProjectScanner(scanner_config_data)
            scanner.scan()
            click.echo("Scan complete.")

        if __name__ == "__main__":
            main()
        ```

6.  **Testing:**
    *   Decoupled core logic is much easier to unit test, as you can pass mock dependencies and configurations directly.

By following these guidelines, we can build more robust, maintainable, and scalable CLI tools within Dream.OS. 