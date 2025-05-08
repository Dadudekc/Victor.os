# Agent-2: Reorganization Build, CI/CD Analysis - Phase 1

This document outlines the findings of the build system, CI/CD, and testing configuration analysis performed by Agent-2 as part of `TASK: AGENT2-REORG-BUILD-ANALYSIS-001`, supporting the project reorganization outlined in `specs/reorganization_proposal_phase1.md`.

## Scope
Analysis focused on:
- `setup.py`
- `package.json`
- `Makefile` (if present)
- `pyproject.toml`
- CI workflow files in `.github/workflows/` (specifically `ci.yml`)
- `pytest.ini`

## Key Findings & Reorganization Impact

### 1. `setup.py`
- **Exists**: Yes.
- **Content**: Minimal, points to `src/` as package root (`packages=find_packages(where="src")`, `package_dir={"": "src"}`). States that configuration is primarily in `pyproject.toml`.
- **Reorg Impact**: Aligns with the `src`-layout. The proposed reorganization of moving `app/` and `apps/` contents into `src/apps/` is compatible. **No changes to `setup.py` are anticipated due to this reorganization.**

### 2. `package.json`
- **Exists**: Yes.
- **Content**: Defines project name `dream.os`, scripts (`scan:dup` using `jscpd`), `devDependencies` (`jscpd`, `prettier`), and a long list of `dependencies` (Node.js modules, likely for JS tooling, linting, or potential UI components).
- **Reorg Impact**: Minimal if reorganization primarily affects Python code structure. The `scan:dup` script uses broad ignores for common generated directories. If JavaScript/TypeScript code within `app/`, `apps/`, or `bridge/` is significantly moved, and `jscpd` relied on specific paths (though it appears to scan broadly), those might need checking. However, the main proposed moves are within a Python `src` layout.

### 3. `Makefile`
- **Exists**: No (not found at project root).
- **Reorg Impact**: N/A.

### 4. `pyproject.toml` (Poetry)
- **Exists**: Yes.
- **Content**:
    - Defines `packages = [{ include = "dreamos", from = "src" }, { include = "dreamscape", from = "src" }]`.
    - Extensive list of Python dependencies managed by Poetry.
    - Defines `[tool.poetry.scripts]` for `dream-cli`.
    - Contains configurations for `mypy`, `ruff`, `black`, `isort`.
- **Reorg Impact**:
    - The existing `packages` definition correctly identifies `dreamos` and `dreamscape` within the `src/` layout.
    - **Decision Point for Reorg Plan**: When code from `app/` and `apps/` is moved into `src/apps/`, a decision is needed:
        - If subdirectories within `src/apps/` (e.g., `src/apps/automation`, `src/apps/sky_viewer`) are intended to be new, independently importable/installable Python packages, they **must be added to the `packages` list** in `pyproject.toml` (e.g., `{ include = "apps/automation", from = "src" }`).
        - If they are simply submodules of an existing package (e.g., `dreamos.apps.automation`), then no change to the `packages` list in `pyproject.toml` might be necessary, assuming correct import paths are used in the code.
    - The current structure of `pyproject.toml` strongly supports the `src`-layout.

### 5. `.github/workflows/ci.yml`
- **Exists**: Yes.
- **Content**: Defines a CI job that runs on push/pull_request to `main`, tests against a matrix of Python versions (3.8-3.11), installs dependencies using `pip install -r requirements.txt`, and runs `pytest`.
- **Reorg Impact**:
    - **Action Required: Align with Poetry**: The CI workflow uses `pip install -r requirements.txt`. Since `pyproject.toml` (Poetry) is the primary source of truth for dependencies, the CI should be updated to use `poetry install`. This typically involves installing Poetry itself as a step, then running `poetry install`.
    - `pytest` execution should continue to work correctly if `pytest.ini` (`pythonpath = src`) is respected, which is standard.

### 6. `pytest.ini`
- **Exists**: Yes.
- **Content**:
    - Defines `testpaths` for test collection (e.g., `tests/integration`, `tests/utils`).
    - **Crucially, sets `pythonpath = src`**. This ensures tests can import modules from the `src/` directory.
- **Reorg Impact**:
    - The `pythonpath = src` setting is ideal for the `src`-layout and the proposed reorganization. It will allow tests to find code moved into `src/apps/`.
    - **Potential Update Needed**: If the test directory structure is updated to mirror the reorganized `src/` structure (e.g., creating `tests/apps/automation/`), the `testpaths` in `pytest.ini` may need to be updated to include these new test locations (e.g., add `tests/apps` or more specific paths if not covered by existing broad paths).

## Summary of Recommendations/Actions for Reorganization:
1.  **Clarify Package Structure in `src/apps/`**: Decide if modules moved to `src/apps/` will be new installable packages (requiring `pyproject.toml` updates) or submodules of existing packages.
2.  **Update `ci.yml`**: Modify the CI workflow to use `poetry install` for dependency management instead of `pip install -r requirements.txt`.
3.  **Update `pytest.ini` `testpaths`**: If test directories are restructured to mirror `src/` changes (e.g., new `tests/apps/` subdirectories), update `testpaths` accordingly.

This concludes the build, CI/CD, and testing configuration analysis for task `AGENT2-REORG-BUILD-ANALYSIS-001`. 