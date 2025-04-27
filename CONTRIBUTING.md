# Contributing to Dream.OS

We welcome contributions from the community! Please follow these guidelines to ensure a smooth development process.

## Development Setup

1.  **Fork & Clone:**
    -   Fork the repository on GitHub.
    -   Clone your fork locally:
        ```bash
        git clone https://github.com/<your-username>/Dream.os.git
        cd Dream.os
        ```

2.  **Create a Virtual Environment:**
    -   We recommend using a virtual environment to manage dependencies.
        ```bash
        python -m venv .venv
        # Activate the environment (Windows PowerShell)
        .venv\Scripts\Activate.ps1
        # Or (Linux/macOS)
        # source .venv/bin/activate
        ```

3.  **Install Dependencies:**
    -   Install the required packages, including development dependencies:
        ```bash
        pip install -r requirements.txt
        # If a dev requirements file exists, install it too:
        # pip install -r requirements-dev.txt
        pip install -e . # Install project in editable mode
        ```

4.  **Set up Pre-Commit Hooks (Optional but Recommended):**
    -   If pre-commit is configured (check for `.pre-commit-config.yaml`), install the hooks:
        ```bash
        # pip install pre-commit
        # pre-commit install
        ```

5.  **Run Tests:**
    -   Ensure the test suite passes in your local environment:
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
    -   Branch off the `main` branch for new features or bug fixes. Use a descriptive name (e.g., `feat/add-new-agent`, `fix/resolve-broadcast-bug`).
    ```bash
    git checkout -b feat/your-feature-name
    ```
3.  **Develop & Commit:**
    -   Make your changes on the feature branch.
    -   Commit your work frequently using the format described below.
4.  **Push & Create Pull Request:**
    -   Push your feature branch to your fork:
        ```bash
        git push origin feat/your-feature-name
        ```
    -   Open a Pull Request (PR) against the `main` branch of the original repository.
    -   Ensure your PR includes a clear description of the changes and links any relevant issues.
    -   Make sure all automated checks (CI, tests) pass.
5.  **Code Review & Merge:**
    -   Project maintainers will review your PR. Address any feedback.
    -   Once approved, your PR will be merged into `main`.

## Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) format. This helps with automated changelog generation and keeps the commit history clear.

The basic format is:

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

**Common Types:**

-   `feat`: A new feature
-   `fix`: A bug fix
-   `chore`: Changes to the build process or auxiliary tools/libraries
-   `docs`: Documentation only changes
-   `style`: Changes that do not affect the meaning of the code (white-space, formatting, etc)
-   `refactor`: A code change that neither fixes a bug nor adds a feature
-   `perf`: A code change that improves performance
-   `test`: Adding missing tests or correcting existing tests

**Scope (Optional):**

The scope should be the name of the package/module affected (e.g., `coordination`, `memory`, `cli`, `docs`).

**Subject:**

-   Use the imperative, present tense: "change" not "changed" nor "changes".
-   Don't capitalize the first letter.
-   No dot (.) at the end.
-   Keep it short (max 50 characters).

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

---

Thank you for contributing to Dream.OS! 