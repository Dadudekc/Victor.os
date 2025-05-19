# Dream.OS Architecture

## Core Components

### Coordination (`src/dreamos/coordination/`)
The central coordination package that handles all agent communication, task management, and system orchestration. This package consolidates all coordination-related functionality that was previously spread across multiple locations. Key components include:

- `AgentBus`: Central message bus for inter-agent communication
- `BaseAgent`: Foundation class for all agents
- `ProjectBoardManager`: Task and project state management
- Event system (types, payloads, patterns)
- JSON schemas for validation

All coordination code now lives in this central location. The `docs/agents/coordination` directory contains a symbolic link to this package for backward compatibility.

## Detailed Documentation

For complete architecture documentation, see the consolidated documentation in the [ai_docs/architecture](./ai_docs/architecture/) directory, including:

- [Proposals](./ai_docs/architecture/proposals/) - Architecture proposals and concepts
- [Designs](./ai_docs/architecture/designs/) - Detailed design documents
- [Diagrams](./ai_docs/architecture/diagrams/) - Visual representations of system architecture 