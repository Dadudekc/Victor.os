"""
Simple test script for task management functionality.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dreamos.coordination.tasks.test_simple_task_manager")

def create_test_task(task_id: str) -> Dict[str, Any]:
    """Create a test task."""
    return {
        "task_id": task_id,
        "status": "pending",
        "description": f"Test task {task_id}",
        "created_at": time.time()
    }

def test_basic_operations():
    """Test basic task board operations."""
    # Initialize test directory
    task_dir = Path("runtime/test/task_boards")
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # Test board name
    board_name = "test_board.json"
    board_path = task_dir / board_name
    
    try:
        # Test writing tasks
        tasks = [create_test_task(f"task-{i}") for i in range(3)]
        with open(board_path, 'w') as f:
            json.dump(tasks, f, indent=2)
        
        # Test reading tasks
        with open(board_path, 'r') as f:
            read_tasks = json.load(f)
        
        assert len(read_tasks) == 3, "Wrong number of tasks read"
        assert all(t["task_id"] in [f"task-{i}" for i in range(3)] for t in read_tasks), "Wrong tasks read"
        
        # Test updating a task
        read_tasks[0]["status"] = "completed"
        with open(board_path, 'w') as f:
            json.dump(read_tasks, f, indent=2)
        
        # Verify update
        with open(board_path, 'r') as f:
            updated_tasks = json.load(f)
        assert updated_tasks[0]["status"] == "completed", "Task not updated correctly"
        
        logger.info("Basic operations test passed")
        
    finally:
        # Clean up
        if board_path.exists():
            board_path.unlink()
        if task_dir.exists():
            task_dir.rmdir()

def main():
    """Run all tests."""
    try:
        test_basic_operations()
        logger.info("All tests passed successfully")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    main() 