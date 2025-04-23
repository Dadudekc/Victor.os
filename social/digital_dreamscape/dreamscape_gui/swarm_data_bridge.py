from PySide6.QtCore import QObject, QThread, Signal, Slot
from dream_mode.task_nexus.task_nexus import TaskNexus
from dream_mode.local_blob_channel import LocalBlobChannel
import time
import os
import json
import logging

logger = logging.getLogger(__name__)

class SwarmDataBridge(QObject):
    # Signals to emit updated data
    tasks_updated = Signal(list)
    agents_updated = Signal(list)
    stats_updated = Signal(dict)
    lore_updated = Signal(str)

    def __init__(self, nexus=None, channel=None, parent=None):
        super().__init__(parent)
        # Initialize core services
        self.nexus = nexus or TaskNexus(task_file="runtime/task_list.json")
        self.channel = channel or LocalBlobChannel()
        # Move self to worker thread
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._run)
        self._thread.start()

    @Slot()
    def _run(self):
        # Poll loop
        while True:
            # Fetch and emit tasks
            tasks = self.nexus.get_all_tasks()
            self.tasks_updated.emit(tasks)
            # Emit agent statuses based on heartbeats
            raw_agents = self.nexus.get_all_registered_agents()
            now = time.time()
            agent_list = []
            for name, last_hb in raw_agents.items():
                delta = now - last_hb
                if delta < 15:
                    state = "active"
                elif delta < 60:
                    state = "idle"
                else:
                    state = "dead"
                agent_list.append((name, state))
            self.agents_updated.emit(agent_list)
            # Emit stats
            stats = dict(self.nexus.stats())
            self.stats_updated.emit(stats)
            # Write per-agent metrics to runtime/agent_stats.json
            try:
                stats_path = os.path.join(os.getcwd(), 'runtime', 'agent_stats.json')
                os.makedirs(os.path.dirname(stats_path), exist_ok=True)
                with open(stats_path, 'w', encoding='utf-8') as sf:
                    json.dump(stats, sf, indent=2)
            except Exception as e:
                logger.error(f"Failed to write agent stats file: {e}")
            # Pull and emit recent lore entries (if any)
            # For now, emit empty or placeholder
            lore = ""
            self.lore_updated.emit(lore)
            time.sleep(2)  # poll every 2s 