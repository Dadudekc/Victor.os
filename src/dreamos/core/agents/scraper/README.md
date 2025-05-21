# Scraper State Machine and Integration

This module provides a state machine implementation for the ChatGPT scraper, along with integration components to connect it with other system parts.

## Components

### 1. State Machine (`scraper_state_machine.py`)

The state machine manages the lifecycle of the scraper, handling:
- State transitions
- Error recovery
- Response stabilization
- Resource management

#### States
- `INITIALIZING`: Initial setup phase
- `AUTHENTICATING`: Login and session management
- `READY`: Ready to accept prompts
- `SENDING_PROMPT`: Sending a prompt to ChatGPT
- `WAITING_FOR_RESPONSE`: Waiting for ChatGPT's response
- `STABILIZING_RESPONSE`: Ensuring response is complete
- `ERROR`: Error state
- `SHUTDOWN`: Cleanup and shutdown

### 2. Integration (`scraper_integration.py`)

The integration layer provides:
- Unified interface for system components
- Operation tracking
- Error handling
- Session management

## Usage

### Basic Usage

```python
from dreamos.core.agents.scraper import ScraperIntegration, ScraperIntegrationConfig
from dreamos.core.io import FileManager, AgentBus

# Initialize components
file_manager = FileManager()
agent_bus = AgentBus()
config = ScraperIntegrationConfig()

# Create integration
integration = ScraperIntegration(file_manager, agent_bus, config)

# Initialize
if integration.initialize():
    # Send prompt
    response = integration.send_prompt("Hello, how are you?")
    print(response)
    
    # Get conversation content
    content = integration.get_conversation_content()
    
    # Shutdown
    integration.shutdown()
```

### Operation Tracking

```python
# Send prompt with operation tracking
response = integration.send_prompt(
    "What is the weather?",
    operation_id="weather_query_1"
)

# Check operation status
if "weather_query_1" in integration.active_operations:
    operation = integration.active_operations["weather_query_1"]
    print(f"Operation started at: {operation['start_time']}")
    print(f"Response: {operation['response']}")
```

## Error Handling

The integration provides robust error handling:

```python
try:
    response = integration.send_prompt("Test prompt")
except Exception as e:
    print(f"Error: {e}")
    print(f"Current state: {integration.get_state()}")
    print(f"Error message: {integration.get_error_message()}")
```

## Configuration

The `ScraperIntegrationConfig` class allows customization of:

- `timeout`: Maximum time to wait for responses (default: 30s)
- `stable_period`: Time to wait for response stabilization (default: 5s)
- `poll_interval`: Time between response checks (default: 0.5s)
- `max_retries`: Maximum retry attempts (default: 3)
- `retry_delay`: Delay between retries (default: 1.0s)

## Testing

Run the test suite:

```bash
python -m unittest discover src/dreamos/core/agents/scraper/tests
```

## Integration Points

The scraper integrates with:

1. `prompt_dispatcher.py`: Handles prompt routing
2. `chat_cycle_controller.py`: Manages conversation flow
3. `social_scout.py`: Social media integration
4. `thea_to_cursor_agent.py`: Agent communication

## State Machine Flow

1. **Initialization**
   - Create state machine
   - Initialize scraper
   - Transition to AUTHENTICATING

2. **Authentication**
   - Handle login
   - Manage session
   - Transition to READY

3. **Prompt Handling**
   - Accept prompt
   - Transition to SENDING_PROMPT
   - Send to ChatGPT
   - Transition to WAITING_FOR_RESPONSE

4. **Response Processing**
   - Wait for response
   - Check stability
   - Transition to STABILIZING_RESPONSE
   - Return to READY

5. **Error Recovery**
   - Detect error
   - Transition to ERROR
   - Attempt recovery
   - Return to READY or SHUTDOWN

6. **Shutdown**
   - Clean up resources
   - Close connections
   - Transition to SHUTDOWN 