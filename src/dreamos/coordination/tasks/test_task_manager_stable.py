"""
Test script for StableTaskManager.

This script verifies the functionality of the StableTaskManager, including:
- File locking
- Transaction logging
- Task validation
- Corruption detection and repair
- Resilient IO integration
- Performance optimizations and caching
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

from dreamos.coordination.tasks.task_manager_stable import TaskManager, TaskValidationError, TaskBoardError

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dreamos.coordination.tasks.test_task_manager")

def create_test_task(task_id: str) -> Dict[str, Any]:
    """Create a test task."""
    return {
        "task_id": task_id,
        "name": f"Test Task {task_id}",
        "description": "Test task description",
        "priority": "HIGH",
        "status": "PENDING",
        "task_type": "TESTING",
        "created_by": "test_agent",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tags": ["test"],
        "dependencies": [],
        "critical": False
    }

class TestTaskManager(unittest.TestCase):
    """Test cases for TaskManager."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.task_manager = TaskManager(self.test_dir)
        self.test_board = "test_board.json"
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
        
    def test_init(self):
        """Test initialization."""
        self.assertTrue(os.path.exists(self.test_dir))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "backups")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "transaction_log.jsonl")))
        
    def test_write_and_read_task_board(self):
        """Test writing and reading task board."""
        # Create test tasks
        tasks = [create_test_task(f"task_{i}") for i in range(3)]
        
        # Write tasks
        self.assertTrue(self.task_manager.write_task_board(self.test_board, tasks))
        
        # Read tasks
        read_tasks = self.task_manager.read_task_board(self.test_board)
        self.assertEqual(len(read_tasks), 3)
        self.assertEqual(read_tasks[0]["task_id"], "task_0")
        
    def test_task_validation(self):
        """Test task validation."""
        # Valid task
        valid_task = create_test_task("valid_task")
        self.assertTrue(self.task_manager._validate_task(valid_task))
        
        # Invalid task (missing required field)
        invalid_task = valid_task.copy()
        del invalid_task["name"]
        with self.assertRaises(TaskValidationError):
            self.task_manager._validate_task(invalid_task)
            
    def test_duplicate_task_detection(self):
        """Test duplicate task detection."""
        tasks = [
            create_test_task("duplicate_id"),
            create_test_task("duplicate_id")  # Same ID
        ]
        
        with self.assertRaises(TaskValidationError):
            self.task_manager.write_task_board(self.test_board, tasks)
            
    def test_corruption_detection_and_repair(self):
        """Test corruption detection and repair."""
        # Create valid tasks
        tasks = [create_test_task(f"task_{i}") for i in range(3)]
        self.task_manager.write_task_board(self.test_board, tasks)
        
        # Corrupt the file
        board_path = os.path.join(self.test_dir, self.test_board)
        with open(board_path, "w") as f:
            f.write("invalid json")
            
        # Detect corruption
        self.assertTrue(self.task_manager.detect_corruption(self.test_board))
        
        # Repair
        self.assertTrue(self.task_manager.repair_task_board(self.test_board))
        
        # Verify repair
        read_tasks = self.task_manager.read_task_board(self.test_board)
        self.assertEqual(len(read_tasks), 0)  # Should be empty after repair
        
    def test_backup_and_restore(self):
        """Test backup and restore functionality."""
        # Create test tasks
        tasks = [create_test_task(f"task_{i}") for i in range(3)]
        self.task_manager.write_task_board(self.test_board, tasks)
        
        # Create backup
        backup_path = self.task_manager.backup_task_board(self.test_board)
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))
        
        # Corrupt the file
        board_path = os.path.join(self.test_dir, self.test_board)
        with open(board_path, "w") as f:
            f.write("invalid json")
            
        # Restore from backup
        self.assertTrue(self.task_manager.restore_from_backup(self.test_board))
        
        # Verify restore
        read_tasks = self.task_manager.read_task_board(self.test_board)
        self.assertEqual(len(read_tasks), 3)
        
    def test_cache_operations(self):
        """Test caching operations."""
        # Create test tasks
        tasks = [create_test_task(f"task_{i}") for i in range(3)]
        
        # Write tasks
        self.task_manager.write_task_board(self.test_board, tasks)
        
        # First read (should miss cache)
        start_time = time.time()
        read_tasks = self.task_manager.read_task_board(self.test_board)
        first_read_time = time.time() - start_time
        
        # Second read (should hit cache)
        start_time = time.time()
        read_tasks = self.task_manager.read_task_board(self.test_board)
        second_read_time = time.time() - start_time
        
        # Cache hit should be faster
        self.assertLess(second_read_time, first_read_time)
        
        # Check metrics
        metrics = self.task_manager.get_metrics()
        self.assertEqual(metrics["cache_hits"], 1)
        self.assertEqual(metrics["cache_misses"], 1)
        
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        # Create test tasks
        tasks = [create_test_task(f"task_{i}") for i in range(3)]
        
        # Write tasks
        self.task_manager.write_task_board(self.test_board, tasks)
        
        # Read tasks (populates cache)
        self.task_manager.read_task_board(self.test_board)
        
        # Invalidate cache
        self.task_manager._invalidate_cache(self.test_board)
        
        # Read again (should miss cache)
        self.task_manager.read_task_board(self.test_board)
        
        # Check metrics
        metrics = self.task_manager.get_metrics()
        self.assertEqual(metrics["cache_misses"], 2)  # Two misses, no hits
        
    def test_concurrent_access(self):
        """Test concurrent access to task board."""
        # Create test tasks
        tasks = [create_test_task(f"task_{i}") for i in range(3)]
        self.task_manager.write_task_board(self.test_board, tasks)
        
        # Function to read tasks
        def read_tasks():
            try:
                self.task_manager.read_task_board(self.test_board)
            except Exception as e:
                logger.error(f"Error in read_tasks: {str(e)}")
                
        # Function to write tasks
        def write_tasks():
            try:
                new_tasks = [create_test_task(f"new_task_{i}") for i in range(3)]
                self.task_manager.write_task_board(self.test_board, new_tasks)
            except Exception as e:
                logger.error(f"Error in write_tasks: {str(e)}")
                
        # Create threads
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=read_tasks))
            threads.append(threading.Thread(target=write_tasks))
            
        # Start threads
        for thread in threads:
            thread.start()
            
        # Wait for threads to complete
        for thread in threads:
            thread.join()
            
        # Verify final state
        read_tasks = self.task_manager.read_task_board(self.test_board)
        self.assertEqual(len(read_tasks), 3)  # Should have 3 tasks
        
        # Check metrics
        metrics = self.task_manager.get_metrics()
        self.assertGreater(metrics["read_operations"], 0)
        self.assertGreater(metrics["write_operations"], 0)
        
    def test_metrics_reset(self):
        """Test metrics reset."""
        # Perform some operations
        tasks = [create_test_task(f"task_{i}") for i in range(3)]
        self.task_manager.write_task_board(self.test_board, tasks)
        self.task_manager.read_task_board(self.test_board)
        
        # Check metrics
        metrics = self.task_manager.get_metrics()
        self.assertGreater(metrics["read_operations"], 0)
        self.assertGreater(metrics["write_operations"], 0)
        
        # Reset metrics
        self.task_manager.reset_metrics()
        
        # Check metrics again
        metrics = self.task_manager.get_metrics()
        self.assertEqual(metrics["read_operations"], 0)
        self.assertEqual(metrics["write_operations"], 0)
        self.assertEqual(metrics["cache_hits"], 0)
        self.assertEqual(metrics["cache_misses"], 0)
        self.assertEqual(metrics["validation_errors"], 0)
        self.assertEqual(metrics["lock_timeouts"], 0)

if __name__ == "__main__":
    unittest.main() 