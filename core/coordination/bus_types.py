# TODO: Expand or reconnect to full version
from enum import Enum

class AgentStatus(Enum):
    INITIALIZING = "initializing"
    IDLE = "idle" # Added from agent_bus usage
    READY = "ready" # Kept original stub value, might be synonymous with IDLE
    BUSY = "busy" # Assuming BUSY state is needed
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN_READY = "shutdown_ready" # Added from agent_bus usage
    ERROR = "error" # Assuming ERROR state is needed
    OFFLINE = "offline" 