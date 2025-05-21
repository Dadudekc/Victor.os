"""
Test script for StableTaskManager.

This script verifies the functionality of the StableTaskManager, including:
- File locking
- Transaction logging
- Task validation
- Corruption detection and repair
- Resilient IO integration
"""

import os
import json
import time
import threading
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any
import unittest
import tempfile
from datetime import datetime, timezone

from dreamos.coordination.tasks.task_manager_stable import TaskManagerStable, TaskValidationError, TaskBoardError

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dreamos.coordination.tasks.test_task_manager")

def create_test_task(task_id: str) -> Dict[str, Any]:
    """Create a test task."""
    return {
        "task_id": task_id,
        "status": "pending",
        "description": f"Test task {task_id}",
        "created_at": time.time()
    }

def setup_test_environment() -> Path:
    """Set up the test environment.
    
    Returns:
        Path to test directory
    """
    # Create test directory
    test_dir = Path("runtime/test/task_boards")
    
    # Remove existing test directory if it exists
    if test_dir.exists():
        try:
            shutil.rmtree(test_dir)
        except Exception as e:
            logger.warning(f"Failed to remove existing test directory: {e}")
    
    # Create fresh test directory
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create transaction log directory
    log_dir = test_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    
    return test_dir

def test_basic_operations():
    """Test basic task board operations."""
    # Initialize task manager
    task_dir = setup_test_environment()
    task_manager = TaskManagerStable(str(task_dir))
    
    # Test board name
    board_name = "test_board.json"
    
    try:
        # Test writing tasks
        tasks = [create_test_task(f"task-{i}") for i in range(3)]
        assert task_manager.write_task_board(board_name, tasks), "Failed to write tasks"
        
        # Test reading tasks
        read_tasks = task_manager.read_task_board(board_name)
        assert len(read_tasks) == 3, "Wrong number of tasks read"
        assert all(t["task_id"] in [f"task-{i}" for i in range(3)] for t in read_tasks), "Wrong tasks read"
        
        # Test updating a task
        updates = {"status": "completed"}
        assert task_manager.update_task(board_name, "task-0", updates), "Failed to update task"
        
        # Verify update
        updated_tasks = task_manager.read_task_board(board_name)
        updated_task = next(t for t in updated_tasks if t["task_id"] == "task-0")
        assert updated_task["status"] == "completed", "Task not updated correctly"
        
        logger.info("Basic operations test passed")
        
    finally:
        # Clean up
        if os.path.exists(task_dir / board_name):
            try:
                os.remove(task_dir / board_name)
            except Exception as e:
                logger.warning(f"Failed to remove test file: {e}")

def test_concurrent_access():
    """Test concurrent access to task boards."""
    task_dir = setup_test_environment()
    task_manager = TaskManagerStable(str(task_dir))
    board_name = "concurrent_test.json"
    
    def worker(task_id: str):
        """Worker function for concurrent access test."""
        try:
            # Read current tasks
            tasks = task_manager.read_task_board(board_name)
            
            # Add a new task
            new_task = create_test_task(task_id)
            tasks.append(new_task)
            
            # Write back
            task_manager.write_task_board(board_name, tasks)
            
        except Exception as e:
            logger.error(f"Worker {task_id} failed: {str(e)}")
    
    try:
        # Initialize with some tasks
        initial_tasks = [create_test_task(f"initial-{i}") for i in range(3)]
        task_manager.write_task_board(board_name, initial_tasks)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(f"concurrent-{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify results
        final_tasks = task_manager.read_task_board(board_name)
        assert len(final_tasks) == 8, "Wrong number of tasks after concurrent access"
        
        # Check for duplicates
        task_ids = [t["task_id"] for t in final_tasks]
        assert len(task_ids) == len(set(task_ids)), "Duplicate tasks found"
        
        logger.info("Concurrent access test passed")
        
    finally:
        # Clean up
        if os.path.exists(task_dir / board_name):
            try:
                os.remove(task_dir / board_name)
            except Exception as e:
                logger.warning(f"Failed to remove test file: {e}")

def test_corruption_detection():
    """Test corruption detection and repair."""
    task_dir = setup_test_environment()
    task_manager = TaskManagerStable(str(task_dir))
    board_name = "corruption_test.json"
    
    try:
        # Create a valid task board
        tasks = [create_test_task(f"task-{i}") for i in range(3)]
        task_manager.write_task_board(board_name, tasks)
        
        # Corrupt the file
        board_path = task_dir / board_name
        with open(board_path, 'w') as f:
            f.write("invalid json content")
        
        # Test corruption detection
        assert task_manager.detect_corruption(board_name), "Failed to detect corruption"
        
        # Test repair
        assert task_manager.repair_task_board(board_name), "Failed to repair corrupted board"
        
        # Verify repair
        repaired_tasks = task_manager.read_task_board(board_name)
        assert len(repaired_tasks) == 3, "Wrong number of tasks after repair"
        
        logger.info("Corruption detection test passed")
        
    finally:
        # Clean up
        if os.path.exists(task_dir / board_name):
            try:
                os.remove(task_dir / board_name)
            except Exception as e:
                logger.warning(f"Failed to remove test file: {e}")

def test_validation():
    """Test task validation."""
    task_dir = setup_test_environment()
    task_manager = TaskManagerStable(str(task_dir))
    board_name = "validation_test.json"
    
    try:
        # Test invalid task (missing required field)
        invalid_task = {
            "description": "Invalid task",
            "created_at": time.time()
        }
        
        try:
            task_manager.write_task_board(board_name, [invalid_task])
            assert False, "Should have raised TaskValidationError"
        except TaskValidationError:
            pass
        
        # Test duplicate task IDs
        tasks = [
            create_test_task("duplicate"),
            create_test_task("duplicate")
        ]
        
        try:
            task_manager.write_task_board(board_name, tasks)
            assert False, "Should have raised TaskValidationError for duplicates"
        except TaskValidationError:
            pass
        
        logger.info("Validation test passed")
        
    finally:
        # Clean up
        if os.path.exists(task_dir / board_name):
            try:
                os.remove(task_dir / board_name)
            except Exception as e:
                logger.warning(f"Failed to remove test file: {e}")

def main():
    """Run all tests."""
    try:
        # Run tests
        test_basic_operations()
        test_concurrent_access()
        test_corruption_detection()
        test_validation()
        
        logger.info("All tests passed successfully")
        
    finally:
        # Clean up test directory
        test_dir = Path("runtime/test/task_boards")
        if test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception as e:
                logger.warning(f"Failed to remove test directory: {e}")

class TestTaskManager(unittest.TestCase):
    def setUp(self):
        # Create temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.task_dir = Path(self.test_dir) / "tasks"
        self.task_dir.mkdir()
        
        # Initialize task manager
        self.manager = TaskManagerStable(self.task_dir)
        
        # Create test task board
        self.board_name = "test_board.json"
        self.test_tasks = [
            {
                "task_id": "TASK-001",
                "description": "Test task 1",
                "status": "PENDING",
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "task_id": "TASK-002",
                "description": "Test task 2",
                "status": "IN_PROGRESS",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        # Write test tasks
        self.manager.write_task_board(self.board_name, self.test_tasks)

    def tearDown(self):
        # Clean up test directory
        import shutil
        shutil.rmtree(self.test_dir)

    def test_resolve_duplicates(self):
        """Test duplicate task resolution."""
        # Add duplicate tasks
        duplicate_tasks = [
            {
                "task_id": "TASK-001",  # Duplicate
                "description": "Updated test task 1",
                "status": "COMPLETED",
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "task_id": "TASK-003",  # New task
                "description": "Test task 3",
                "status": "PENDING",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        # Write duplicate tasks
        self.manager.write_task_board(self.board_name, duplicate_tasks)
        
        # Resolve duplicates
        result = self.manager.resolve_duplicates(self.board_name)
        
        # Verify results
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["duplicates_resolved"], 1)
        
        # Read tasks back
        tasks = self.manager.read_task_board(self.board_name)
        
        # Verify task count
        self.assertEqual(len(tasks), 2)  # Should have 2 unique tasks
        
        # Verify task IDs
        task_ids = {task["task_id"] for task in tasks}
        self.assertEqual(task_ids, {"TASK-001", "TASK-003"})
        
        # Verify most recent version kept
        task_001 = next(task for task in tasks if task["task_id"] == "TASK-001")
        self.assertEqual(task_001["status"], "COMPLETED")

    def test_resolve_duplicates_no_duplicates(self):
        """Test duplicate resolution with no duplicates."""
        # Resolve duplicates
        result = self.manager.resolve_duplicates(self.board_name)
        
        # Verify results
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["duplicates_resolved"], 0)
        
        # Read tasks back
        tasks = self.manager.read_task_board(self.board_name)
        
        # Verify task count unchanged
        self.assertEqual(len(tasks), len(self.test_tasks))

    def test_resolve_duplicates_invalid_board(self):
        """Test duplicate resolution with invalid board."""
        # Resolve duplicates
        result = self.manager.resolve_duplicates("invalid_board.json")
        
        # Verify results
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["duplicates_resolved"], 0)

if __name__ == "__main__":
    unittest.main() 