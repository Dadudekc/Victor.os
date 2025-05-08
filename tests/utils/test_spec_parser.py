import unittest
from unittest.mock import patch, mock_open
import logging
from pathlib import Path

# Assuming src is in PYTHONPATH or using relative imports if tests are run as a module
from dreamos.utils.spec_parser import parse_project_plan_tasks, ProjectPlanTableVisitor, _commonmark_available

# Disable logging for most tests to keep output clean, enable for specific debugs
logging.disable(logging.CRITICAL)

# Mock data for PROJECT_PLAN.md content
MOCK_MAIN_TASKS_TABLE = \
"""
## 3. Current Tasks & Priorities

| Task ID | Description                                     | Agent Assigned | Status      | Priority | Due Date   | Notes                                                                 |
|---------|-------------------------------------------------|----------------|-------------|----------|------------|-----------------------------------------------------------------------|
| ORG-001 | Create `specs/` directory and initial plan files | AI Assistant   | Done        | High     | 2023-10-01 | Initial setup.                                                        |
| DEV-001 | Implement core messaging bus                    | Agent Alpha    | In Progress | High     | 2023-10-15 | Basic pub/sub. <br>Needs retry.                                        |
"""

MOCK_LEGACY_TASKS_TABLE = \
"""
### TASKS.md Content

| Original Category | Task Description        | Status (from TASKS.md) | Priority (implied) | Notes        |
|-------------------|-------------------------|------------------------|--------------------|--------------|
| General           | Review old bug reports  | To Do                  | Medium             | From Q1 list |
| UI                | Mockup new dashboard    | Done                   | High               | Approved     |
"""

MOCK_NO_RECOGNIZED_TABLES = \
"""
# Some Document
This is a document with no task tables.

| Header A | Header B |
|----------|----------|
| Val 1    | Val 2    |
"""

MOCK_MALFORMED_ROW_TABLE = \
"""
## 3. Current Tasks & Priorities

| Task ID | Description | Agent Assigned | Status      | Priority | Due Date   | Notes        |
|---------|-------------|----------------|-------------|----------|------------|--------------|
| ORG-001 | Create specs  | AI Assistant   | Done        | High     | 2023-10-01 | Initial setup |
| DEV-001 | Implement bus | Agent Alpha    | In Progress | High     |            | Notes only   |
"""


class TestSpecParser(unittest.TestCase):

    @patch('dreamos.utils.spec_parser.Path.read_text')
    @patch('dreamos.utils.spec_parser.Path.is_file')
    def test_parse_project_plan_valid_main_tasks_table(self, mock_is_file, mock_read_text):
        if not _commonmark_available:
            self.skipTest("commonmarkextensions not available")
        mock_is_file.return_value = True
        mock_read_text.return_value = MOCK_MAIN_TASKS_TABLE
        
        result = parse_project_plan_tasks("dummy_path.md")
        self.assertIsNotNone(result)
        self.assertIn("main_tasks", result)
        self.assertEqual(len(result["main_tasks"]), 2)
        
        task1 = result["main_tasks"][0]
        self.assertEqual(task1["task id"], "ORG-001")
        self.assertEqual(task1["description"], "Create `specs/` directory and initial plan files")
        self.assertEqual(task1["status"], "Done")
        self.assertEqual(task1["notes"], "Initial setup.")

        task2 = result["main_tasks"][1]
        self.assertEqual(task2["task id"], "DEV-001")
        self.assertEqual(task2["description"], "Implement core messaging bus") # Soft break should be space
        self.assertEqual(task2["notes"], "Basic pub/sub. \nNeeds retry.") # <br> should be newline

    @patch('dreamos.utils.spec_parser.Path.read_text')
    @patch('dreamos.utils.spec_parser.Path.is_file')
    def test_parse_project_plan_valid_legacy_md_tasks_table(self, mock_is_file, mock_read_text):
        if not _commonmark_available:
            self.skipTest("commonmarkextensions not available")
        mock_is_file.return_value = True
        mock_read_text.return_value = MOCK_LEGACY_TASKS_TABLE

        result = parse_project_plan_tasks("dummy_path.md")
        self.assertIsNotNone(result)
        self.assertIn("legacy_tasks_md", result)
        self.assertEqual(len(result["legacy_tasks_md"]), 2)
        self.assertEqual(result["legacy_tasks_md"][0]["task description"], "Review old bug reports")

    @patch('dreamos.utils.spec_parser.Path.read_text')
    @patch('dreamos.utils.spec_parser.Path.is_file')
    def test_parse_project_plan_multiline_cell_content(self, mock_is_file, mock_read_text):
        # This is partially covered by test_parse_project_plan_valid_main_tasks_table
        # Can be expanded if more complex multiline scenarios are needed.
        self.skipTest("Covered by main tasks test, expand if needed.")

    @patch('dreamos.utils.spec_parser.Path.read_text')
    @patch('dreamos.utils.spec_parser.Path.is_file')
    def test_parse_project_plan_mixed_tables(self, mock_is_file, mock_read_text):
        if not _commonmark_available:
            self.skipTest("commonmarkextensions not available")
        mock_is_file.return_value = True
        mock_read_text.return_value = MOCK_MAIN_TASKS_TABLE + "\n\n" + MOCK_LEGACY_TASKS_TABLE
        
        result = parse_project_plan_tasks("dummy_path.md")
        self.assertIsNotNone(result)
        self.assertIn("main_tasks", result)
        self.assertEqual(len(result["main_tasks"]), 2)
        self.assertIn("legacy_tasks_md", result)
        self.assertEqual(len(result["legacy_tasks_md"]), 2)

    @patch('dreamos.utils.spec_parser.Path.read_text')
    @patch('dreamos.utils.spec_parser.Path.is_file')
    def test_parse_project_plan_no_recognized_tables(self, mock_is_file, mock_read_text):
        if not _commonmark_available:
            self.skipTest("commonmarkextensions not available")
        mock_is_file.return_value = True
        mock_read_text.return_value = MOCK_NO_RECOGNIZED_TABLES
        
        result = parse_project_plan_tasks("dummy_path.md")
        self.assertIsNotNone(result)
        self.assertEqual(len(result.get("main_tasks", [])), 0)
        self.assertEqual(len(result.get("legacy_tasks_md", [])), 0)

    @patch('dreamos.utils.spec_parser.Path.read_text')
    @patch('dreamos.utils.spec_parser.Path.is_file')
    def test_parse_project_plan_malformed_row_table(self, mock_is_file, mock_read_text):
        if not _commonmark_available:
            self.skipTest("commonmarkextensions not available")
        mock_is_file.return_value = True
        mock_read_text.return_value = MOCK_MALFORMED_ROW_TABLE

        result = parse_project_plan_tasks("dummy_path.md")
        self.assertIsNotNone(result)
        self.assertIn("main_tasks", result)
        self.assertEqual(len(result["main_tasks"]), 2)
        # DEV-001 has fewer cells than headers, check padding
        dev_task = next(t for t in result["main_tasks"] if t["task id"] == "DEV-001")
        self.assertEqual(dev_task["due date"], "") # Padded with empty string or None
        self.assertEqual(dev_task["notes"], "Notes only")


    @patch('dreamos.utils.spec_parser.Path.is_file')
    def test_parse_project_plan_file_not_found(self, mock_is_file):
        if not _commonmark_available:
            self.skipTest("commonmarkextensions not available")
        mock_is_file.return_value = False
        result = parse_project_plan_tasks("non_existent_path.md")
        self.assertIsNone(result)

    @patch('dreamos.utils.spec_parser._commonmark_available', False)
    def test_parse_project_plan_commonmark_not_installed(self):
        # Temporarily patch the module-level flag
        result = parse_project_plan_tasks("dummy_path.md")
        self.assertIsNone(result)
        # Add assertion for logging if possible

    def test_cell_content_extraction_various_inline_markdown(self):
        # This would require more direct testing of _extract_cell_content or a
        # more complex mock table setup.
        # For now, basic text, softbreak, linebreak (<br>) are covered.
        self.skipTest("Further inline markdown extraction needs dedicated test or expansion of existing.")


if __name__ == '__main__':
    logging.disable(logging.NOTSET) # Enable all logs for direct script run
    unittest.main() 