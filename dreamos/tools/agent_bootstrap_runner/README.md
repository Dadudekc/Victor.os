# Dream.OS Universal Agent Bootstrap Runner

A modular implementation of the agent bootstrap process that works with any agent (1-8).

## Features

- **Universal Agent Support**: Works with any agent (Agent-1 through Agent-8)
- **Modular Architecture**: Clean separation of concerns for maintainability
- **Robust Error Handling**: Comprehensive validation and error recovery
- **Protocol Enforcement**: Follows Dream.OS agent protocols
- **Flexible Configuration**: Via environment variables and CLI arguments
- **Comprehensive Logging**: Structured logging with agent-specific files

## Installation

The agent bootstrap runner is part of the Dream.OS toolkit. No additional installation is required.

## Usage

### Basic Usage

```python
from dreamos.tools.agent_bootstrap_runner import AgentConfig, AgentBootstrapRunner

# Create config for any agent (1-8)
config = AgentConfig(agent_id="Agent-2")

# Create and run the bootstrap runner
runner = AgentBootstrapRunner(config)
await runner.run()
```

### Command Line Usage

```bash
# Run Agent-2 bootstrap
python -m dreamos.tools.agent_bootstrap_runner --agent Agent-2

# Run Agent-3 with custom prompt
python -m dreamos.tools.agent_bootstrap_runner --agent Agent-3 --prompt "Custom prompt"

# Run Agent-4 once and exit
python -m dreamos.tools.agent_bootstrap_runner --agent Agent-4 --once

# List available prompts
python -m dreamos.tools.agent_bootstrap_runner --list-prompts
```

## Configuration

### Environment Variables

- `AGENT_HEARTBEAT_SEC`: Heartbeat interval (default: 30)
- `AGENT_LOOP_DELAY_SEC`: Delay between cycles (default: 5)
- `AGENT_RESPONSE_WAIT_SEC`: Wait time for responses (default: 15)
- `AGENT_RETRIEVE_RETRIES`: Number of retrieval attempts (default: 3)
- `AGENT_RETRY_DELAY_SEC`: Delay between retries (default: 2)
- `AGENT_STARTUP_DELAY_SEC`: Initial startup delay (default: 30)
- `AGENT_LOG_LEVEL`: Logging level (default: INFO) 