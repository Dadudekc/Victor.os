import unittest
import sys
from pathlib import Path
import datetime

# Add the scripts directory to sys.path to allow importing the migration script
SCRIPTS_DIR = Path(__file__).parent.parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

# Now import the function to test
try:
    from task_flow_migration import transform_task
except ImportError as e:
    print(f"Error importing task_flow_migration: {e}")
    print("Ensure scripts/task_flow_migration.py exists and SCRIPTS_DIR is correct.")
    # Define a dummy function if import fails, so tests can be defined but will fail clearly
    def transform_task(task_data: dict, source_file_type: str) -> dict | None:
        raise NotImplementedError("transform_task could not be imported")

class TestTaskTransformation(unittest.TestCase):

    def test_basic_future_task_transform(self):
        """Test transformation of a simple PENDING task from future_tasks."""
        old_task = {
            "task_id": "future-task-001",
            "name": "Future Task Example",
            "description": "A sample task for the future.",
            "priority": "MEDIUM",
            "status": "PENDING",
            "assigned_agent": None,
            "task_type": "PLANNING",
            "created_by": "Agent-Planner",
            "created_at": "2024-01-01T10:00:00Z",
            "tags": ["future", "example"],
            "dependencies": [],
            "estimated_duration": "1h",
            "history": []
        }
        transformed = transform_task(old_task, 'future_tasks.json')
        self.assertIsNotNone(transformed)
        self.assertEqual(transformed['task_id'], "future-task-001")
        self.assertEqual(transformed['action'], "PLANNING")
        self.assertEqual(transformed['status'], "PENDING")
        self.assertEqual(transformed['priority'], 10) # MEDIUM mapped to 10
        self.assertEqual(transformed['injected_by'], "Agent-Planner")
        self.assertEqual(transformed['injected_at'], "2024-01-01T10:00:00Z")
        self.assertIsNone(transformed['started_at'])
        self.assertIsNone(transformed['completed_at'])
        self.assertEqual(len(transformed['history']), 1) # Should have migration entry
        self.assertEqual(transformed['history'][0]['action'], "MIGRATED_FROM_future_tasks.json")
        self.assertEqual(transformed['params']['_migration_info']['original_name'], "Future Task Example")

    def test_basic_working_task_transform(self):
        """Test transformation of a simple IN_PROGRESS task from working_tasks."""
        old_task = {
            "task_id": "working-task-002",
            "name": "Working Task Example",
            "priority": "HIGH",
            "status": "IN_PROGRESS",
            "assigned_to": "Gemini", # Note: uses assigned_to
            "task_type": "IMPLEMENTATION",
            "created_by": "Agent-Assigner",
            "created_at": "2024-01-02T11:00:00Z",
            "tags": ["active", "example"],
            "dependencies": ["future-task-001"],
            "history": [
                {"timestamp": "2024-01-02T12:00:00Z", "agent": "Gemini", "action": "CLAIMED", "details": "Claimed task"}
            ]
        }
        transformed = transform_task(old_task, 'working_tasks.json')
        self.assertIsNotNone(transformed)
        self.assertEqual(transformed['task_id'], "working-task-002")
        self.assertEqual(transformed['action'], "IMPLEMENTATION")
        self.assertEqual(transformed['status'], "ACTIVE")
        self.assertEqual(transformed['priority'], 5) # HIGH mapped to 5
        self.assertEqual(transformed['depends_on'], ["future-task-001"])
        self.assertEqual(transformed['injected_by'], "Agent-Assigner")
        self.assertEqual(transformed['started_at'], "2024-01-02T12:00:00Z") # From CLAIMED history
        self.assertIsNone(transformed['completed_at'])
        self.assertEqual(len(transformed['history']), 2) # Original + migration entry
        self.assertEqual(transformed['history'][1]['action'], "MIGRATED_FROM_working_tasks.json")
        self.assertEqual(transformed['params']['_migration_info']['original_assigned_agent'], "Gemini")

    def test_completed_task_transform(self):
        """Test transformation of a COMPLETED task from future_tasks."""
        old_task = {
            "task_id": "done-task-003",
            "name": "Completed Task Example",
            "priority": "LOW",
            "status": "COMPLETED",
            "assigned_agent": "Agent-X",
            "task_type": "VERIFICATION",
            "created_by": "System",
            "created_at": "2024-01-03T09:00:00Z",
            "tags": ["done"],
            "dependencies": [],
            "notes": "Verified successfully.",
            "history": [
                 {"timestamp": "2024-01-03T10:00:00Z", "agent": "Agent-X", "action": "COMPLETED", "details": "All checks pass"}
            ]
        }
        transformed = transform_task(old_task, 'future_tasks.json')
        self.assertIsNotNone(transformed)
        self.assertEqual(transformed['task_id'], "done-task-003")
        self.assertEqual(transformed['action'], "VERIFICATION")
        self.assertEqual(transformed['status'], "COMPLETED")
        self.assertEqual(transformed['priority'], 20) # LOW mapped to 20
        self.assertEqual(transformed['injected_by'], "System")
        self.assertIsNotNone(transformed['completed_at']) # Should be set
        self.assertEqual(transformed['completed_at'], "2024-01-03T10:00:00Z") # From COMPLETED history
        self.assertEqual(transformed['result_status'], "SUCCESS")
        self.assertEqual(transformed['progress'], 1.0)
        self.assertEqual(len(transformed['history']), 2) # Original + migration entry
        self.assertEqual(transformed['params']['_migration_info']['original_notes'], "Verified successfully.")

    def test_missing_task_id(self):
        """Test that a task without a task_id is not transformed."""
        old_task = {
            # "task_id": "missing", 
            "name": "Task Without ID",
            "status": "PENDING"
        }
        transformed = transform_task(old_task, 'some_file.jsonl')
        self.assertIsNone(transformed)

    def test_missing_required_fields_defaulting(self):
        """Test handling of tasks missing fields that have defaults or can be inferred."""
        old_task = {
            "task_id": "minimal-task-004",
            "name": "Minimal Task",
            # Missing priority, status, task_type, created_by, created_at
        }
        transformed = transform_task(old_task, 'minimal_tasks.jsonl')
        self.assertIsNotNone(transformed)
        self.assertEqual(transformed['task_id'], "minimal-task-004")
        self.assertEqual(transformed['action'], "Minimal Task") # Defaulted from name
        self.assertEqual(transformed['status'], "PENDING") # Defaulted
        self.assertEqual(transformed['priority'], 10) # Defaulted
        self.assertIsNotNone(transformed['injected_at']) # Should be defaulted to now
        self.assertEqual(transformed['injected_by'], "TaskMigrationScript") # Defaulted
        self.assertEqual(len(transformed['history']), 1) # Migration entry

if __name__ == '__main__':
    unittest.main() 