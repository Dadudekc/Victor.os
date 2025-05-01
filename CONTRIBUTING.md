# Contributing to Dream.OS

We welcome contributions from the community! Please follow these guidelines to
ensure a smooth development process.

## Core Concepts & Workflow (The "Dream.OS Way")

Before diving into the code, understand these core principles:

- **Agent Swarm:** Dream.OS often operates as a swarm of specialized agents
  collaborating on tasks.
- **Central Task List:** Tasks are typically defined and tracked in
  `_agent_coordination/task_list.json`. Use utilities like those in
  `src/dreamos/coordination/tasks/task_utils.py` (or potentially a central
  `TaskNexus`) to interact with this list (e.g., update status, claim tasks).
- **Agent Communication:** Agents communicate via message queues/mailboxes,
  often located in `runtime/agent_comms/`. Standard message formats are used for
  requests, responses, and review notifications (e.g., sending a JSON message to
  `Supervisor1/inbox/` for review).
- **Reuse Existing Utilities:** **Crucially**, before writing new code, explore
  existing utilities within `src/dreamos/core/` and `src/dreamos/coordination/`.
  Reusing established helpers for file I/O, task management, communication,
  logging, etc., ensures consistency and robustness.
- **Project Structure:** Familiarize yourself with key directories:
  - `src/dreamos/`: Core library code, agents, tools.
  - `_agent_coordination/`: Central configuration, task lists, shared state.
  - `runtime/`: Agent mailboxes, logs, temporary files during operation.
  - `scripts/`: Helper and utility scripts.
  - `docs/`: Project documentation.

Understanding and adhering to these patterns is key to successful contributions.

## Development Setup

1.  **Fork & Clone:**

    - Fork the repository on GitHub.
    - Clone your fork locally:
      ```bash
      git clone https://github.com/<your-username>/Dream.os.git
      cd Dream.os
      ```

2.  **Create a Virtual Environment:**

    - We recommend using a virtual environment to manage dependencies.
      ```bash
      python -m venv .venv
      # Activate the environment (Windows PowerShell)
      .venv\Scripts\Activate.ps1
      # Or (Linux/macOS)
      # source .venv/bin/activate
      ```

3.  **Install Dependencies:**

    - Install the required packages, including development dependencies:
      ```bash
      pip install -r requirements.txt
      # If a dev requirements file exists, install it too:
      # pip install -r requirements-dev.txt
      pip install -e . # Install project in editable mode
      ```
    - **Note:** Check for project-specific configuration files (e.g., in
      `_agent_coordination/config.py` or similar) that might need adjustment for
      your local environment.

4.  **Set up Pre-Commit Hooks (Optional but Recommended):**

    - If pre-commit is configured (check for `.pre-commit-config.yaml`), install
      the hooks:
      ```bash
      # pip install pre-commit
      # pre-commit install
      ```

5.  **Run Tests:**
    - Ensure the test suite passes in your local environment:
      ```bash
      pytest
      ```

## Branching Strategy

We follow a feature branch workflow:

1.  **Sync your `main` branch:**
    ```bash
    git checkout main
    git pull upstream main # Assuming 'upstream' points to the original repo
    ```
2.  **Create a Feature Branch:**
    - Branch off the `main` branch for new features or bug fixes. Use a
      descriptive name (e.g., `feat/add-new-agent`,
      `fix/resolve-broadcast-bug`).
    ```bash
    git checkout -b feat/your-feature-name
    ```
3.  **Develop & Commit:**
    - Make your changes on the feature branch.
    - Commit your work frequently using the format described below.
4.  **Push & Create Pull Request:**
    - Push your feature branch to your fork:
      ```bash
      git push origin feat/your-feature-name
      ```
    - Open a Pull Request (PR) against the `main` branch of the original
      repository.
    - Ensure your PR includes a clear description of the changes and links any
      relevant issues.
    - Make sure all automated checks (CI, tests) pass.
5.  **Code Review & Merge:**
    - Project maintainers will review your PR. Address any feedback.
    - Once approved, your PR will be merged into `main`.

## Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
format. This helps with automated changelog generation and keeps the commit
history clear.

The basic format is:

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

**Common Types:**

- `feat`: A new feature
- `fix`: A bug fix
- `chore`: Changes to the build process or auxiliary tools/libraries
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code (white-space,
  formatting, etc)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests

**Scope (Optional):**

The scope should be the name of the package/module affected (e.g., `agent-comm`,
`core-memory`, `task-utils`, `cli`, `docs`, `gui-tool`).

**Subject:**

- Use the imperative, present tense: "change" not "changed" nor "changes".
- Don't capitalize the first letter.
- No dot (.) at the end.
- Keep it short (max 50 characters).

**Example:**

```
feat(coordination): add dry-run mode to broadcast directive

Allows simulating broadcasts without modifying mailbox files.
Useful for testing and debugging coordination flows.
```

```
fix(cli): correct exit code for invalid global flags

Ensures the CLI exits with code 2 when an unknown top-level
flag is provided, matching expected behavior in smoke tests.

Closes #123
```

## Coding Style & Best Practices

- **PEP 8:** Follow the
  [PEP 8 Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/).
  Tools like `black` and `flake8` are recommended (check for project
  configuration).
- **Typing:** Use Python type hints (`typing` module) for function signatures
  and variables. Strive for type safety.
- **Docstrings:** Write clear and concise docstrings for modules, classes, and
  functions using a standard format (e.g., Google Style, reStructuredText).
- **Tests:** Include unit tests (`pytest`) for new features and bug fixes. Aim
  for reasonable test coverage, especially for core utilities and agent logic.
- **Logging:** Use the standard `logging` module configured for the project.
  Provide informative log messages with context (e.g., task IDs, agent IDs) to
  aid traceability. Avoid using `print()` for operational output.
- **Reuse Utilities:** (Reiteration for emphasis) Always check
  `src/dreamos/core` and `src/dreamos/coordination` for existing helpers before
  implementing new file operations, communication logic, configuration reading,
  etc.

**### Handler Parameter Validation (CRITICAL for Agent Reliability)**

Robust parameter validation within message handlers (agents, services, tool
functions) is **non-negotiable** for stable swarm behavior.

Handlers receive data parsed from messages or external inputs. **Assume this
data might be incomplete or incorrect.**

- **Check for Required Fields:** Explicitly ensure all expected keys/attributes
  are present.
- **Validate Types:** Verify data types match expectations (e.g., `str`, `int`,
  `bool`, specific `dataclass`).
- **Validate Values:** Check ranges, allowed options (enums), or formats where
  applicable.
- **Fail Fast & Clearly:** If validation fails, the handler **MUST NOT** proceed
  with flawed data. It must:
  - Log a detailed error message (including task ID, relevant context, and the
    validation failure).
  - Raise an appropriate exception (`ValueError`, `TypeError`, custom
    `InvalidParameterError`).
  - **OR** reliably communicate the failure (e.g., update task status to FAILED
    with error details, publish a failure event/response message).

This prevents cascading errors and ensures agent operations are predictable.

```python
# Example Agent Handler Validation (Illustrative)
from dreamos.core.models import TaskMessage # Assuming a model
# from dreamos.core.exceptions import InvalidParameterError # Assuming a custom exception

async def handle_some_command(self, task: TaskMessage):
    task_id = task.task_id
    input_data = task.input_data or {}

    required_param = input_data.get('required_param')
    optional_int_param = input_data.get('optional_int')

    # --- Validation ---
    if required_param is None:
        error_msg = f"Missing required parameter 'required_param'"
        self.logger.error(f"{error_msg} in task {task_id}")
        await self.report_failure(task_id, error_msg) # Assumes a failure reporting method
        return

    if optional_int_param is not None:
        try:
            optional_int_param = int(optional_int_param)
            if optional_int_param < 0:
                 raise ValueError("Value must be non-negative")
        except (TypeError, ValueError) as e:
            error_msg = f"Invalid value for parameter 'optional_int': {e}"
            self.logger.error(f"{error_msg} in task {task_id}")
            await self.report_failure(task_id, error_msg)
            return

    # --- Proceed with validated parameters ---
    self.logger.info(f"Processing task {task_id} with validated params...")
    try:
        # ... handler logic using required_param and optional_int_param ...
        await self.report_success(task_id, result_data="...")
    except Exception as e:
        self.logger.exception(f"Unexpected error during task {task_id} execution.")
        await self.report_failure(task_id, f"Internal error: {e}")

# Placeholder for agent's failure reporting method
async def report_failure(self, task_id, reason):
    # Example: Update task status via task_utils or nexus
    # update_task_status(..., task_id, "FAILED", error_message=reason)
    pass

# Placeholder for agent's success reporting method
async def report_success(self, task_id, result_data):
    # Example: Update task status via task_utils or nexus
    # update_task_status(..., task_id, "COMPLETED", result_data=result_data)
    pass
```

---

Thank you for contributing to Dream.OS!
