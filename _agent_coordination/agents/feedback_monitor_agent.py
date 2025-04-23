#!/usr/bin/env python3
"""
FeedbackMonitorAgent

A simple agent that watches for tasks marked as 'failed' or stale,
resets them to 'pending', and logs requeues to the LocalBlobChannel and TaskNexus.
"""
import time
import threading
from dream_mode.task_nexus.task_nexus import TaskNexus
from dream_mode.local_blob_channel import LocalBlobChannel
import logging

class FeedbackMonitorAgent:
    def __init__(self, agent_id: str, check_interval: float = 10.0, stale_after: float = 60.0):
        self.agent_id = agent_id
        self.check_interval = check_interval
        self.stale_after = stale_after
        self.nexus = TaskNexus(task_file="runtime/task_list.json")
        self.channel = LocalBlobChannel()
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    def run(self):
        logging.info(f"[{self.agent_id}] FeedbackMonitorAgent started.")
        while True:
            # Record heartbeat
            self.nexus.record_heartbeat(self.agent_id)

            # Reclaim stale tasks claimed by dead agents
            reclaimed = self.nexus.reclaim_stale_tasks(stale_after=self.stale_after)
            for task in reclaimed:
                logging.info(f"[{self.agent_id}] Reclaimed stale task {task.get('id')}")
                # Push a result event indicating reinjection
                self.channel.push_result({
                    'id': task.get('id'),
                    'status': 'requeued',
                    'agent': self.agent_id,
                    'timestamp': time.time()
                })

            # Retry explicitly failed tasks
            all_tasks = self.nexus.get_all_tasks()
            for task in all_tasks:
                if task.get('status') == 'failed':
                    task_id = task.get('id')
                    logging.info(f"[{self.agent_id}] Resetting failed task {task_id} to pending.")
                    self.nexus.update_task_status(task_id, 'pending')

            time.sleep(self.check_interval)

if __name__ == '__main__':
    agent = FeedbackMonitorAgent(agent_id="AgentFeedbackMonitor")
    agent.run() 