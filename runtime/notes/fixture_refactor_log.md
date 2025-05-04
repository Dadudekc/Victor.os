## Fixture Refactor Log (REFACTOR-PBM-TEST-FIXTURES-001)

*   **[2025-05-02T21:30Z - Agent-2]:** Replaced usages of deprecated `pbm_instance` fixture with `pbm` in `tests/coordination/test_project_board_manager.py` test functions (initial block).
*   **[2025-05-02T21:35Z - Agent-2]:** Replaced usage of deprecated `pbm_instance_with_real_schema` fixture with type hint `ProjectBoardManager` in `test_load_schema_success`.
*   **Note:** Tests using `mock_pbm_with_schema` already used type hints and did not require parameter name changes.
*   **Status:** All direct usages of deprecated fixtures in parameters replaced. Ready for pytest validation.
