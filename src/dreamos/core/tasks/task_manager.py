import asyncio
from typing import Dict, Any

class TaskManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.task_queue = PriorityTaskQueue(
            max_size=config.get('queue_size', 1000),
            priority_levels=config.get('priority_levels', ['HIGH', 'MEDIUM', 'LOW'])
        )
        self.load_balancer = LoadBalancer(
            max_workers=config.get('max_workers', 5),
            max_tasks_per_worker=config.get('max_tasks_per_worker', 10)
        )
        self.resource_allocator = ResourceAllocator(
            max_memory=config.get('max_memory', 1024),
            max_cpu=config.get('max_cpu', 80)
        )
        self._setup_optimization()
        
    def _setup_optimization(self):
        """Configure optimization settings."""
        self.optimization_config = {
            'task_scheduling': {
                'batch_size': 10,
                'max_retries': 3,
                'retry_delay': 1
            },
            'load_balancing': {
                'worker_pool_size': 5,
                'max_tasks_per_worker': 10,
                'rebalance_interval': 60
            },
            'resource_allocation': {
                'memory_limit': 1024,
                'cpu_limit': 80,
                'io_limit': 1000
            }
        }
        
    async def schedule_task(self, task: Dict[str, Any]):
        """Schedule a task with priority and resource allocation."""
        try:
            # Validate task
            if not self._validate_task(task):
                raise ValueError("Invalid task format")
                
            # Allocate resources
            resources = await self.resource_allocator.allocate(task)
            
            # Get worker from load balancer
            worker = await self.load_balancer.get_worker()
            
            # Add task to queue with priority
            await self.task_queue.add_task(
                task=task,
                priority=task.get('priority', 'MEDIUM'),
                worker=worker,
                resources=resources
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling task: {e}")
            return False
            
    async def process_tasks(self):
        """Process tasks with load balancing and resource management."""
        while True:
            try:
                # Get batch of tasks
                tasks = await self.task_queue.get_batch(
                    self.optimization_config['task_scheduling']['batch_size']
                )
                
                if not tasks:
                    await asyncio.sleep(0.1)
                    continue
                    
                # Process tasks in parallel
                tasks_to_process = []
                for task in tasks:
                    if self._can_process_task(task):
                        tasks_to_process.append(task)
                        
                if tasks_to_process:
                    results = await asyncio.gather(
                        *[self._process_task(task) for task in tasks_to_process],
                        return_exceptions=True
                    )
                    
                    # Handle results
                    for task, result in zip(tasks_to_process, results):
                        if isinstance(result, Exception):
                            await self._handle_task_error(task, result)
                        else:
                            await self._handle_task_success(task, result)
                            
            except Exception as e:
                logger.error(f"Error in task processing: {e}")
                await asyncio.sleep(1)
                
    def _can_process_task(self, task: Dict[str, Any]) -> bool:
        """Check if task can be processed based on resource availability."""
        return (
            self.resource_allocator.has_available_resources(task) and
            self.load_balancer.has_available_worker()
        )
        
    async def _process_task(self, task: Dict[str, Any]):
        """Process a single task with resource management."""
        async with self.resource_allocator.acquire(task) as resources:
            try:
                # Execute task
                result = await self._execute_task(task, resources)
                
                # Update metrics
                self._update_task_metrics(task, result)
                
                return result
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                raise 