# Dream.OS Project

## Project Structure
- `docs/`: Project documentation
- `runtime/`: Runtime files and configurations
- `src/`: Source code

## Infrastructure
- Event System: 180s loop
- Tools: 5s chunks
- Board: Active
- Resources: 1800s wrap-up
- Channels: Chunked

## Communication Protocol
### Response Format
```
[AGENT-3] [SYNC] Status:
1) Event: 180s loop
2) Tools: 5s chunks
3) Board: Active
4) Resources: 1800s wrap-up
5) Channels: Chunked

WE ARE THE SWARM
```

### Input Protocol
1. Double-click input field
2. 0.2s delay
3. Paste chunk
4. Verify content
5. Retry if failed

### Message Format
```
[CHUNK X/Y HASH:abc123]
Message content...
```

### Verification
- Hash-based integrity checks
- Retry mechanism (3 attempts)
- 5s delay between retries
- 0.2s verification delay

## Task Status
### ORGANIZE-001
- Project Structure: Active
- Documentation: Active
- Coordination: Active
- Monitoring: Active
- Maintenance: Active

## Coordination
- Agent-2: Infrastructure management
- Agent-3: Project organization and coordination

## Micro Spin-Offs

- **Self-Healing Agent Swarm Starter Template** – see `spin_offs/self_healing_swarm_template/`. Provides a minimal setup for running Cursor-based agents on the `StableAutonomousLoop`.
- **Auto-Prompt Script Generator** – see `spin_offs/auto_prompt_generator/`. Generates prompt files from a YAML spec to bootstrap multi-agent workflows.
