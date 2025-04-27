"""Re-export of the core coordination AgentBus and AgentStatus for convenience."""
from enum import Enum
from dreamos.coordination.agent_bus import AgentBus as _CoordAgentBus

class AgentStatus(Enum):
    IDLE = 'idle'
    BUSY = 'busy'
    ERROR = 'error'
    SHUTDOWN_READY = 'shutdown_ready'

# Expose the real AgentBus implementation
AgentBus = _CoordAgentBus 
