class Config:
    """Stub Config for chat_cycle_controller dependencies"""
    def __init__(self, path=None):
        self._data = {}
    def get(self, key, default=None):
        return default 