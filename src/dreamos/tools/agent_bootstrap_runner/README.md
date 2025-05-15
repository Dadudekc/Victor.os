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

### Agent-Specific Traits

Each agent has specific traits that influence their behavior:

- **Agent-1**: Analytical, Logical, Methodical, Precise
- **Agent-2**: Vigilant, Proactive, Methodical, Protective
- **Agent-3**: Creative, Innovative, Intuitive, Exploratory
- **Agent-4**: Communicative, Empathetic, Diplomatic, Persuasive
- **Agent-5**: Knowledgeable, Scholarly, Thorough, Informative
- **Agent-6**: Strategic, Visionary, Decisive, Forward-thinking
- **Agent-7**: Adaptive, Resilient, Practical, Resourceful
- **Agent-8**: Ethical, Balanced, Principled, Thoughtful

## Directory Structure

```
runtime/
├── agent_comms/
│   └── agent_mailboxes/
│       └── Agent-N/           # N = 1-8
│           ├── inbox/         # New inbox directory
│           ├── processed/     # Processed messages
│           ├── state/         # Agent state
│           └── archive/       # Archived messages
├── config/
│   ├── cursor_agent_coords.json
│   └── cursor_agent_copy_coords.json
├── devlog/
│   └── agents/
│       └── agent-n.log       # Agent-specific logs
└── governance/
    └── protocols/            # Agent protocols
```

## Development

### Running Tests

```bash
pytest tests/tools/agent_bootstrap_runner
```

### Adding Support for New Agents

1. Add agent traits and charter to `config.py`
2. Update coordinate files with agent-specific positions
3. Create agent-specific prompt templates if needed

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

## License

Copyright © 2024 Dream.OS. All rights reserved. 