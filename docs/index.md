# Dream.OS Documentation

## Core Components

### Integrations
- [Cursor Integration](api/integrations/cursor_chatgpt_bridge.md)
  - Bridge functionality for Cursor-ChatGPT communication
  - [Module Diagram](architecture/diagrams/cursor_bridge_module_diagram.md)
  - [API Reference](api/integrations/cursor_chatgpt_bridge.md)

### Architecture
- [System Overview](architecture/overview.md)
- [Component Diagrams](architecture/diagrams/)
  - [Cursor Bridge Module](architecture/diagrams/cursor_bridge_module_diagram.md)

### Development
- [Getting Started](dev_guides/getting_started.md)
- [Testing](dev_guides/testing.md)
  - [Bridge E2E Tests](dev_guides/testing.md#bridge-end-to-end-tests)

### API Reference
- [Integrations](api/integrations/)
  - [Cursor-ChatGPT Bridge](api/integrations/cursor_chatgpt_bridge.md)

## Quick Links

- [Contributing Guide](CONTRIBUTING.md)
- [Task Management](TASKS.md)
- [Recent Changes](recent_changes.txt)

## Module Structure

```
src/dreamos/
├── integrations/
│   └── cursor/
│       ├── bridge/
│       │   ├── relay/
│       │   ├── feedback/
│       │   ├── schemas/
│       │   └── tests/
│       ├── config/
│       └── utils/
└── ...
```

## Testing

### Running Tests
```bash
# Run all tests
pytest

# Run bridge tests specifically
pytest src/dreamos/integrations/cursor/bridge/tests/

# Run with coverage
pytest --cov=dreamos.integrations.cursor
``` 