from enum import Enum, auto


class Event:
    # Minimal Event class stub for imports
    def __init__(self, type, data, source_id):
        self.type = type
        self.data = data
        self.source_id = source_id


class EventDispatcher:
    # Minimal EventDispatcher stub for imports
    def __init__(self, bus):
        pass

    async def start(self):
        pass

    def register_handler(self, event_type, handler):
        pass

    async def dispatch_event(self, event):
        pass


__all__ = ["Event", "EventDispatcher"]
