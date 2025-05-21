# Task System Performance Tuning Guide

## Performance Optimization Techniques

### 1. Batch Operations

#### Bulk Task Creation
```python
def create_tasks_bulk(descriptions: List[str]) -> bool:
    """Create multiple tasks efficiently."""
    # Prepare all tasks
    tasks = [
        {
            "task_id": f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{i}",
            "description": desc,
            "status": "PENDING",
            "created_at": datetime.now().isoformat()
        }
        for i, desc in enumerate(descriptions)
    ]
    
    # Single write operation
    return task_manager.write_task_board("active_tasks.json", tasks)
```

#### Batch Status Updates
```python
def update_status_bulk(task_ids: List[str], new_status: str) -> bool:
    """Update multiple task statuses efficiently."""
    # Read once
    tasks = task_manager.read_task_board("active_tasks.json")
    
    # Create lookup
    task_map = {t["task_id"]: t for t in tasks}
    
    # Update in memory
    updated = False
    for task_id in task_ids:
        if task_id in task_map:
            task_map[task_id]["status"] = new_status
            updated = True
    
    # Write once if any updates
    if updated:
        return task_manager.write_task_board("active_tasks.json", list(task_map.values()))
    return False
```

### 2. Caching Strategies

#### Task Status Cache
```python
from functools import lru_cache
from typing import Dict, Optional

class TaskStatusCache:
    def __init__(self, maxsize: int = 1000):
        self._cache = {}
        self._maxsize = maxsize
    
    def get(self, task_id: str) -> Optional[str]:
        """Get task status from cache."""
        return self._cache.get(task_id)
    
    def set(self, task_id: str, status: str):
        """Set task status in cache."""
        if len(self._cache) >= self._maxsize:
            # Remove oldest entry
            self._cache.pop(next(iter(self._cache)))
        self._cache[task_id] = status
    
    def invalidate(self, task_id: str):
        """Remove task from cache."""
        self._cache.pop(task_id, None)

# Usage
status_cache = TaskStatusCache()
```

#### Board Cache
```python
class BoardCache:
    def __init__(self, ttl: int = 60):
        self._cache = {}
        self._timestamps = {}
        self._ttl = ttl
    
    def get(self, board_name: str) -> Optional[List[dict]]:
        """Get board from cache if not expired."""
        if board_name in self._cache:
            if time.time() - self._timestamps[board_name] < self._ttl:
                return self._cache[board_name]
            else:
                self.invalidate(board_name)
        return None
    
    def set(self, board_name: str, tasks: List[dict]):
        """Set board in cache."""
        self._cache[board_name] = tasks
        self._timestamps[board_name] = time.time()
    
    def invalidate(self, board_name: str):
        """Remove board from cache."""
        self._cache.pop(board_name, None)
        self._timestamps.pop(board_name, None)

# Usage
board_cache = BoardCache()
```

### 3. Indexing

#### Task ID Index
```python
class TaskIndex:
    def __init__(self):
        self._index = {}
    
    def build(self, tasks: List[dict]):
        """Build index from tasks."""
        self._index = {t["task_id"]: t for t in tasks}
    
    def get(self, task_id: str) -> Optional[dict]:
        """Get task by ID."""
        return self._index.get(task_id)
    
    def update(self, task: dict):
        """Update task in index."""
        self._index[task["task_id"]] = task
    
    def remove(self, task_id: str):
        """Remove task from index."""
        self._index.pop(task_id, None)

# Usage
task_index = TaskIndex()
```

#### Status Index
```python
class StatusIndex:
    def __init__(self):
        self._index = {}
    
    def build(self, tasks: List[dict]):
        """Build index from tasks."""
        self._index = {}
        for task in tasks:
            status = task["status"]
            if status not in self._index:
                self._index[status] = []
            self._index[status].append(task)
    
    def get_by_status(self, status: str) -> List[dict]:
        """Get tasks by status."""
        return self._index.get(status, [])
    
    def update(self, task: dict, old_status: Optional[str] = None):
        """Update task in index."""
        if old_status and old_status in self._index:
            self._index[old_status] = [
                t for t in self._index[old_status]
                if t["task_id"] != task["task_id"]
            ]
        
        status = task["status"]
        if status not in self._index:
            self._index[status] = []
        self._index[status].append(task)

# Usage
status_index = StatusIndex()
```

### 4. Memory Management

#### Task Pool
```python
class TaskPool:
    def __init__(self, max_size: int = 10000):
        self._pool = []
        self._max_size = max_size
    
    def add(self, task: dict):
        """Add task to pool."""
        if len(self._pool) >= self._max_size:
            # Remove oldest task
            self._pool.pop(0)
        self._pool.append(task)
    
    def get_all(self) -> List[dict]:
        """Get all tasks."""
        return self._pool
    
    def clear(self):
        """Clear pool."""
        self._pool.clear()

# Usage
task_pool = TaskPool()
```

#### Memory Monitor
```python
class MemoryMonitor:
    def __init__(self, threshold_mb: int = 1000):
        self._threshold = threshold_mb * 1024 * 1024
        self._last_check = time.time()
    
    def check(self) -> bool:
        """Check if memory usage is below threshold."""
        import psutil
        process = psutil.Process()
        memory_usage = process.memory_info().rss
        
        if memory_usage > self._threshold:
            print(f"Memory usage {memory_usage / 1024 / 1024:.2f} MB exceeds threshold")
            return False
        return True
    
    def monitor(self, interval: int = 60):
        """Monitor memory usage periodically."""
        while True:
            if not self.check():
                # Trigger cleanup
                gc.collect()
            time.sleep(interval)

# Usage
memory_monitor = MemoryMonitor()
```

### 5. Concurrency Control

#### Task Queue
```python
from queue import Queue
from threading import Thread

class TaskQueue:
    def __init__(self, max_size: int = 1000):
        self._queue = Queue(maxsize=max_size)
        self._worker = Thread(target=self._process_queue)
        self._running = True
    
    def start(self):
        """Start queue processing."""
        self._worker.start()
    
    def stop(self):
        """Stop queue processing."""
        self._running = False
        self._worker.join()
    
    def add(self, task: dict):
        """Add task to queue."""
        self._queue.put(task)
    
    def _process_queue(self):
        """Process queued tasks."""
        while self._running:
            try:
                task = self._queue.get(timeout=1)
                # Process task
                self._queue.task_done()
            except Queue.Empty:
                continue

# Usage
task_queue = TaskQueue()
```

#### Lock Manager
```python
class LockManager:
    def __init__(self, timeout: int = 30):
        self._locks = {}
        self._timeout = timeout
    
    def acquire(self, resource: str) -> bool:
        """Acquire lock for resource."""
        if resource in self._locks:
            if time.time() - self._locks[resource] > self._timeout:
                # Lock expired
                self._locks[resource] = time.time()
                return True
            return False
        
        self._locks[resource] = time.time()
        return True
    
    def release(self, resource: str):
        """Release lock for resource."""
        self._locks.pop(resource, None)
    
    def cleanup(self):
        """Remove expired locks."""
        current_time = time.time()
        expired = [
            resource for resource, timestamp in self._locks.items()
            if current_time - timestamp > self._timeout
        ]
        for resource in expired:
            self._locks.pop(resource)

# Usage
lock_manager = LockManager()
```

## Performance Monitoring

### 1. Operation Timing

```python
class OperationTimer:
    def __init__(self):
        self._timings = {}
    
    def start(self, operation: str):
        """Start timing operation."""
        self._timings[operation] = time.time()
    
    def stop(self, operation: str) -> float:
        """Stop timing operation and return duration."""
        if operation in self._timings:
            duration = time.time() - self._timings[operation]
            del self._timings[operation]
            return duration
        return 0.0
    
    def get_average(self, operation: str) -> float:
        """Get average duration for operation."""
        if operation in self._timings:
            return sum(self._timings[operation]) / len(self._timings[operation])
        return 0.0

# Usage
timer = OperationTimer()
```

### 2. Resource Usage

```python
class ResourceMonitor:
    def __init__(self):
        self._metrics = {}
    
    def measure(self):
        """Measure resource usage."""
        import psutil
        process = psutil.Process()
        
        self._metrics = {
            "memory": process.memory_info().rss / 1024 / 1024,  # MB
            "cpu": process.cpu_percent(),
            "threads": process.num_threads(),
            "open_files": len(process.open_files()),
            "connections": len(process.connections())
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """Get current metrics."""
        return self._metrics
    
    def log_metrics(self):
        """Log current metrics."""
        print("Resource Usage:")
        for metric, value in self._metrics.items():
            print(f"{metric}: {value}")

# Usage
monitor = ResourceMonitor()
```

### 3. Performance Reports

```python
class PerformanceReporter:
    def __init__(self):
        self._reports = []
    
    def add_report(self, operation: str, duration: float, resources: Dict[str, float]):
        """Add performance report."""
        self._reports.append({
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "duration": duration,
            "resources": resources
        })
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate performance summary."""
        if not self._reports:
            return {}
        
        operations = {}
        for report in self._reports:
            op = report["operation"]
            if op not in operations:
                operations[op] = {
                    "count": 0,
                    "total_duration": 0,
                    "avg_duration": 0,
                    "max_duration": 0,
                    "min_duration": float("inf")
                }
            
            ops = operations[op]
            ops["count"] += 1
            ops["total_duration"] += report["duration"]
            ops["max_duration"] = max(ops["max_duration"], report["duration"])
            ops["min_duration"] = min(ops["min_duration"], report["duration"])
        
        # Calculate averages
        for op in operations.values():
            op["avg_duration"] = op["total_duration"] / op["count"]
        
        return operations
    
    def save_report(self, filename: str):
        """Save performance report to file."""
        with open(filename, "w") as f:
            json.dump(self._reports, f, indent=2)

# Usage
reporter = PerformanceReporter()
```

## Optimization Guidelines

### 1. Task Board Size

- Keep task boards under 10,000 tasks
- Split large boards into multiple smaller ones
- Archive old tasks regularly
- Use pagination for large result sets

### 2. Operation Frequency

- Batch related operations
- Use appropriate timeouts
- Implement rate limiting
- Cache frequently accessed data

### 3. Resource Usage

- Monitor memory usage
- Implement cleanup routines
- Use connection pooling
- Optimize file I/O

### 4. Concurrency

- Use appropriate lock timeouts
- Implement retry mechanisms
- Handle deadlocks
- Use thread pools

### 5. Caching

- Cache task status
- Cache board contents
- Use appropriate TTL
- Implement cache invalidation

### 6. Indexing

- Index by task ID
- Index by status
- Index by date
- Update indexes efficiently

## Performance Testing

### 1. Load Testing

```python
def load_test(num_tasks: int = 1000):
    """Test system under load."""
    # Create tasks
    tasks = [
        {
            "task_id": f"TASK-{i}",
            "description": f"Test task {i}",
            "status": "PENDING",
            "created_at": datetime.now().isoformat()
        }
        for i in range(num_tasks)
    ]
    
    # Measure write time
    timer.start("write")
    task_manager.write_task_board("test_tasks.json", tasks)
    write_time = timer.stop("write")
    
    # Measure read time
    timer.start("read")
    task_manager.read_task_board("test_tasks.json")
    read_time = timer.stop("read")
    
    # Measure update time
    timer.start("update")
    update_status_bulk([t["task_id"] for t in tasks], "COMPLETED")
    update_time = timer.stop("update")
    
    return {
        "write_time": write_time,
        "read_time": read_time,
        "update_time": update_time
    }
```

### 2. Stress Testing

```python
def stress_test(duration: int = 300):
    """Test system under stress."""
    end_time = time.time() + duration
    operations = 0
    
    while time.time() < end_time:
        # Random operation
        op = random.choice(["read", "write", "update"])
        
        if op == "read":
            task_manager.read_task_board("test_tasks.json")
        elif op == "write":
            task = {
                "task_id": f"TASK-{operations}",
                "description": f"Stress test task {operations}",
                "status": "PENDING",
                "created_at": datetime.now().isoformat()
            }
            task_manager.write_task_board("test_tasks.json", [task])
        else:
            update_status_bulk([f"TASK-{operations}"], "COMPLETED")
        
        operations += 1
    
    return {
        "duration": duration,
        "operations": operations,
        "ops_per_second": operations / duration
    }
```

### 3. Concurrency Testing

```python
def concurrency_test(num_threads: int = 10, duration: int = 60):
    """Test system under concurrent load."""
    def worker():
        end_time = time.time() + duration
        while time.time() < end_time:
            # Random operation
            op = random.choice(["read", "write", "update"])
            
            if op == "read":
                task_manager.read_task_board("test_tasks.json")
            elif op == "write":
                task = {
                    "task_id": f"TASK-{uuid.uuid4()}",
                    "description": "Concurrent test task",
                    "status": "PENDING",
                    "created_at": datetime.now().isoformat()
                }
                task_manager.write_task_board("test_tasks.json", [task])
            else:
                update_status_bulk([f"TASK-{uuid.uuid4()}"], "COMPLETED")
    
    # Start threads
    threads = []
    for _ in range(num_threads):
        thread = Thread(target=worker)
        thread.start()
        threads.append(thread)
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    return {
        "threads": num_threads,
        "duration": duration
    }
``` 