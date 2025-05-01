# Shim for backward compatibility: re-export BaseDispatcher from nested module
from dreamos.coordination.dispatchers.dispatchers.base_dispatcher import BaseDispatcher

__all__ = ["BaseDispatcher"]
