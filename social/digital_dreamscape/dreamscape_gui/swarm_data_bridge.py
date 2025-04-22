from PySide6.QtCore import QObject, QThread, Signal, Slot
from dream_mode.task_nexus.task_nexus import TaskNexus
from dream_mode.local_blob_channel import LocalBlobChannel

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
        import time
        while True:
            # Fetch and emit tasks
            tasks = self.nexus.get_all_tasks()
            self.tasks_updated.emit(tasks)
            # TODO: implement agent status tracking
            agents = []
            self.agents_updated.emit(agents)
            # Emit stats
            stats = dict(self.nexus.stats())
            self.stats_updated.emit(stats)
            # TODO: collect new lore log entries
            lore = ""
            self.lore_updated.emit(lore)
            time.sleep(2)  # poll every 2s 