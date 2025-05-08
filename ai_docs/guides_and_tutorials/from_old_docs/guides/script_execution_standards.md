# Python Utility Script Execution Standards

**Version:** 1.1 **Status:** Recommended Standard **Date:** [AUTO_DATE]
**Related Tasks:** STANDARDIZE-SCRIPT-EXECUTION-ENV-001,
INVESTIGATE-EDITABLE-INSTALL-IMPACT-001

## Overview

This document defines the standard procedures for executing Python utility
scripts located within the `src/dreamos/tools/` directory (and potentially other
utility locations) to ensure they can reliably import modules from the main
`src/dreamos` package, resolving common `ModuleNotFoundError` issues.

## Problem

Scripts located outside the main `src/dreamos` package directory (e.g., in
`src/dreamos/tools/`) cannot directly import modules like
`from dreamos.core.config import ...` when executed naively (e.g.,
`python src/dreamos/tools/my_script.py`) because the `src` directory containing
the `dreamos` package is not automatically included in Python's import search
path (`sys.path`).

## Recommended Solution: Editable Install

The **strongly recommended and most robust** method for enabling script
execution in development or agent environments is to perform an **editable
install** of the `dreamos` package. Analysis of `pyproject.toml` confirms the
project uses Poetry and is correctly configured for this approach.

**Procedure:**

1.  Navigate to the **project root directory** (the directory containing
    `pyproject.toml` and `setup.py`).
2.  Ensure you are in the correct Python environment (e.g., virtual environment
    managed by Poetry or manually).
3.  Run **one** of the following commands:
    - If using Poetry: `poetry install` (this handles dev dependencies as well)
    - If using pip directly: `pip install -e .`

**Benefits:**

- Makes the `dreamos` package directly importable from anywhere within the same
  Python environment.
- Aligns with standard Python development practices and the project's Poetry
  setup.
- Resolves import issues without needing manual path manipulation for each
  script execution.
- Changes made to the source code in `src/dreamos` are immediately reflected
  without needing reinstallation (due to the `-e` flag).

**Prerequisites:**

- `pip` or `poetry` must be installed in the environment.
- A valid `pyproject.toml` (and minimal `setup.py`) must exist in the project
  root. (Confirmed present and configured).

## Alternative Solution: Setting PYTHONPATH

If modifying the Python environment with an editable install is not feasible or
desirable (e.g., in highly restricted execution contexts), the `PYTHONPATH`
environment variable can be used _at the time of execution_.

**Procedure (PowerShell Example):**

```powershell
# Set PYTHONPATH temporarily for this command
$env:PYTHONPATH='/path/to/project/src'; python /path/to/project/src/dreamos/tools/your_script.py --args

# Unset (optional, if needed for cleanup in the same session)
# Remove-Item Env:\PYTHONPATH
```

**Procedure (Bash/Zsh Example):**

```bash
# Set PYTHONPATH temporarily for this command
PYTHONPATH=/path/to/project/src python /path/to/project/src/dreamos/tools/your_script.py --args
```

**Replace `/path/to/project/src` with the absolute path to the `src`
directory.**

**Benefits:**

- Does not require persistent changes to the Python environment.
- Useful for specific execution contexts or one-off runs.

**Drawbacks:**

- Must be set correctly _every time_ a script is executed.
- Prone to errors if the path is incorrect or the variable is not set.
- Less standard than using package installation mechanisms.

## Discouraged: Modifying `sys.path` within Scripts

Directly manipulating `sys.path` inside utility scripts (e.g., using
`sys.path.append(...)` with relative path calculations) is **strongly
discouraged**. This approach is fragile, harder to maintain, and less
transparent than environment-level solutions.

## Conclusion

Prioritize using an **editable install (`pip install -e .` or
`poetry install`)** for consistency and reliability, leveraging the project's
existing Poetry configuration. Use the `PYTHONPATH` method as a fallback when
necessary. Avoid script-internal `sys.path` modifications.
