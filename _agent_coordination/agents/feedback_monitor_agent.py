#!/usr/bin/env python3
"""
FeedbackMonitorAgent

A background agent that monitors tasks for failures or stale claims,
and requeues them safely back into the task pipeline.
"""

import asyncio
import logging
from datetime import datetime, timezone

from dream_mode.task_nexus.task_nexus import TaskNexus
from dream_mode.local_blob_channel import LocalBlobChannel

class FeedbackMonitorAgent:
    def __init__(
        self,
        agent_id: str = "AgentFeedbackMonitor",
        check_interval: float = 10.0,
        stale_after: float = 60.0,
        task_file: str = "runtime/task_list.json",
    ):
        self.agent_id = agent_id
        self.check_interval = check_interval
        self.stale_after = stale_after
        self.nexus = TaskNexus(task_file=task_file)
        self.channel = LocalBlobChannel()
        self.running = False

        # Set up logger (external logging config assumed in production)
        self.logger = logging.getLogger(self.agent_id)

    async def start(self):
        """Starts the feedback monitor loop."""
        self.logger.info("Starting FeedbackMonitorAgent...")
        self.running = True
        while self.running:
            try:
                await self._heartbeat()
                await self._reclaim_stale_tasks()
                await self._retry_failed_tasks()
            except Exception as e:
                self.logger.error(f"Error during monitoring loop: {e}", exc_info=True)

            await asyncio.sleep(self.check_interval)

    async def _heartbeat(self):
        """Record this agent's heartbeat for monitoring."""
        try:
            self.nexus.record_heartbeat(self.agent_id)
        except Exception as e:
            self.logger.warning(f"Failed to record heartbeat: {e}")

    async def _reclaim_stale_tasks(self):
        """Reclaim tasks abandoned by dead agents."""
        try:
            reclaimed = self.nexus.reclaim_stale_tasks(stale_after=self.stale_after)
            for task in reclaimed:
                task_id = task.get("id")
                if not task_id:
                    continue
                self.logger.info(f"Reclaimed stale task {task_id}")

                # Push a structured requeue event
                self.channel.push_result({
                    "id": task_id,
                    "status": "requeued",
                    "agent": self.agent_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        except Exception as e:
            self.logger.error(f"Error reclaiming stale tasks: {e}", exc_info=True)

    async def _retry_failed_tasks(self):
        """Retry any tasks that failed previously."""
        try:
            all_tasks = self.nexus.get_all_tasks()
            for task in all_tasks:
                if task.get("status") == "failed":
                    task_id = task.get("id")
                    if not task_id:
                        continue
                    self.logger.info(f"Resetting failed task {task_id} to 'pending'")
                    self.nexus.update_task_status(task_id, "pending")
        except Exception as e:
            self.logger.error(f"Error retrying failed tasks: {e}", exc_info=True)

    async def stop(self):
        """Stops the agent loop gracefully."""
        self.logger.info("Stopping FeedbackMonitorAgent...")
        self.running = False

# Bootstrap for standalone running
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    agent = FeedbackMonitorAgent()

    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        # Allow graceful shutdown on Ctrl+C
        asyncio.run(agent.stop())
