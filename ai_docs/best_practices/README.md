# Best Practices

This section documents coding standards, style guides, preferred libraries, and other best practices specific to this project to ensure consistency and quality.

## Key Principles Summary

*   **Reuse First:** **Crucially**, before writing new code, explore existing utilities within `src/dreamos/core/` and `src/dreamos/coordination/`. Reusing established helpers ensures consistency and robustness.
*   **Python Standards:** Follow PEP 8 (enforced via `black`, `flake8`), use Python type hints (`typing`), and write clear docstrings (Google/reST style).
*   **Parameter Validation:** Robust validation of inputs (required fields, types, values) in message handlers and tool functions is **non-negotiable** for agent reliability. Fail fast and clearly on invalid data.
*   **Testing:** Include `pytest` unit tests for new features and fixes, especially for core utilities and agent logic.
*   **Logging:** Use the standard `logging` module with contextual information (task/agent IDs). Avoid `print()` for operational output.
*   **Conventional Commits:** Use the `<type>(<scope>): <subject>` format for commit messages.
*   **Git Workflow:** Follow the feature branch workflow (branch from `main`, commit, push, create PR).

## Detailed Documentation Links

The following documents contain more detailed information on project best practices:

*   **General Contribution and Workflow:**
    *   [CONTRIBUTING.md](../../CONTRIBUTING.md): Core principles, development setup, commit message format, coding style (PEP 8, typing, docstrings, tests, logging), and crucial guidelines on reusing existing utilities and parameter validation.
    *   [Developer Guide](../../docs/DEVELOPER_GUIDE.md): Best practices for agent development, communication (AgentBus), message patterns, hooks, agent registration, and project structure.
    *   [Pull Request Template](../../.github/PULL_REQUEST_TEMPLATE.md): Checklist reinforcing style, self-review, commenting, documentation, testing, and conventional commits.

*   **Coding Standards & Conventions:**
    *   [Naming Conventions](../../docs/standards/naming_conventions.md): Standard naming for files, variables, classes, functions, and components.
    *   [Error Handling Standard](../../docs/standards/error_handling_standard.md): Guidelines for raising, catching, logging, and retrying errors, including a proposed exception hierarchy.
    *   [Script Execution Standards](../../docs/standards/script_execution_standards.md): Standard procedures for executing Python utility scripts, recommending editable installs.
    *   [Configuration Management Standard](../../docs/standards/configuration.md): Standard approach for managing configuration via `AppConfig`.

*   **Processes & Protocols:**
    *   [Peer Review Protocol](../../docs/protocols/peer_review_protocol_v1.md): Standard review criteria and process.
    *   [Automated Testing Policy](../../docs/policies/automated_testing_policy_v1.md): Standards for unit and integration testing using `pytest`.
    *   [Task Management Standards](../../docs/standards/task_management.md): Practices for defining and managing tasks.
    *   [Devlog Reporting Standard](../../docs/standards/devlog_reporting_standard.md): Format for agent development logs.

*   **Asset Management:**
    *   [Asset Management Guide](../../docs/guides/asset_management.md): Practices for managing non-code assets (images, templates, data files).

This document serves as a central reference. Please familiarize yourself with these guidelines. 