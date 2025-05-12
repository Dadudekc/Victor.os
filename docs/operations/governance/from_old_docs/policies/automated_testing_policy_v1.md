# Dream.OS Automated Testing Policy (v1.0)

**Effective Date:** {{iso_date_utc}}
**Mandated By:** Captain Agent 8 (Initiated under Task CAPTAIN8-MANDATE-TESTING-INFRA-001)
**Authored By:** Agent 3

## 1. Purpose

To ensure the stability, reliability, and maintainability of Dream.OS core systems and agent components through the consistent application of automated testing practices. This policy aims to prevent regressions, validate functionality, and increase confidence in code modifications.

## 2. Scope

This policy applies to modifications of:

*   **Core Systems:** Modules within `src/dreamos/core/`, `src/dreamos/coordination/`, `src/dreamos/supervisor_tools/`, `src/dreamos/utils/` (non-trivial utilities).
*   **Agent Implementations:** Core logic within individual agent classes (`src/dreamos/agents/`).
*   **Shared Tooling:** Standalone scripts or tools intended for use by multiple agents or system processes (`src/dreamos/tools/`, `scripts/`).

Simple configuration changes, documentation updates, or trivial refactoring (e.g., renaming variables) may be exempt at the discretion of the reviewer, but testing is encouraged where feasible.

## 3. Requirements

1.  **Unit Tests:**
    *   All new public functions/methods within the scope defined above MUST have corresponding unit tests.
    *   Modifications to existing functions/methods MUST ensure existing tests pass and add new tests covering the changed logic or behavior.
    *   Unit tests SHOULD use mocking (e.g., `unittest.mock`, `pytest-mock`) to isolate the unit under test from its dependencies (filesystem, network, other modules).
    *   Tests MUST cover standard success cases, expected error handling (e.g., specific exceptions raised), and relevant edge cases (e.g., empty inputs, boundary conditions).
    *   Target minimum code coverage for core modules (e.g., 80%) should be established and tracked (requires coverage tooling integration - See Section 5).
2.  **Integration Tests:**
    *   Significant new features or modifications impacting interactions between multiple core components (e.g., PBM + AgentBus, Agent + Tool Execution) SHOULD be accompanied by integration tests.
    *   Integration tests verify the collaboration between components, using minimal necessary mocking.
3.  **Test Framework:**
    *   `pytest` is the standard testing framework for the Dream.OS Python codebase.
    *   Tests SHOULD follow standard pytest conventions (e.g., `test_*.py` file naming, test function naming, use of fixtures).
4.  **Pre-Commit Validation:**
    *   The pre-commit hook (`MAINT-ADD-LINT-HOOK-001`) including linting (`flake8`) and potentially basic syntax checks is MANDATORY.
    *   Running relevant unit tests via the pre-commit hook is RECOMMENDED but may be deferred to CI/automated checks due to execution time.

## 4. Validation & Enforcement

1.  **Automated Checks (Target State):**
    *   A CI/CD pipeline or Supervisor-triggered process WILL be implemented to automatically run all unit and integration tests upon code commits/merges to critical branches.
    *   Test failures WILL block deployment or integration until resolved.
    *   Code coverage reports WILL be generated and monitored.
2.  **Manual Review:**
    *   Until fully automated checks are operational, code reviewers are RESPONSIBLE for verifying:
        *   Presence of adequate unit tests for new/modified code.
        *   Passing status of relevant tests (developers should confirm tests pass locally before submitting for review).
        *   Adherence to testing standards outlined in this policy.
    *   Tasks marked `COMPLETED_PENDING_REVIEW` involving code changes MUST include confirmation in the notes that required tests were added/updated and passed locally.
3.  **Self-Validation:**
    *   Agents performing code modifications MUST run relevant tests locally as part of their self-validation process before submitting work.

## 5. Infrastructure (Implementation Tasks)

*   **`CAPTAIN8-MANDATE-TESTING-INFRA-001` (This Task):** Define policy (this document), ensure pre-commit hooks active.
*   **`TESTINFRA-SETUP-CI-CD-001` (New - HIGH Priority):** Setup basic CI/CD pipeline (e.g., GitHub Actions) to run `pytest` automatically on commits/PRs to main branch.
*   **`TESTINFRA-ADD-COVERAGE-001` (New - MEDIUM Priority):** Integrate code coverage tooling (e.g., `pytest-cov`) into the CI/CD pipeline and configure reporting.
*   **`TESTINFRA-ENFORCE-POLICY-CHECKS-001` (New - MEDIUM Priority):** Explore automated ways to enforce policy (e.g., minimum coverage checks, detecting untested public methods) within the CI/CD pipeline.

## 6. Policy Review & Updates

This policy will be reviewed periodically (e.g., every 2-4 cycles) by the Captain and key technical agents to ensure its effectiveness and relevance. Updates will be proposed and communicated via standard governance protocols.
