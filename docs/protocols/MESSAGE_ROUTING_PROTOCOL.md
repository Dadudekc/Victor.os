# Dream.OS Message Routing Protocol

## Overview

Dream.OS uses two distinct communication channels for different purposes:

1. **Inbox System** - For inter-agent communication
2. **PyAutoGUI Bridge** - For LLM agent interaction with Cursor

## 1. Inbox System (Agent ↔ Agent)

### Purpose
- Internal agent-to-agent communication
- Protocol messages
- Status synchronization
- Lore triggers
- Task coordination

### Implementation
- File-based message storage
- Location: `runtime/agent_mailboxes/Agent-<n>/inbox.json`
- JSON/MD message format
- Transparent and logged

### Use Cases
- Task handoffs between agents
- Feedback relay
- Recovery notices
- Directive dispatch (THEA → agent, agent → agent)
- Status updates
- Resource coordination

### Message Types
```json
{
  "type": "task_handoff",
  "from": "Agent-2",
  "to": "Agent-5",
  "task_id": "task-123",
  "priority": "high",
  "context": "..."
}
```

## 2. PyAutoGUI Bridge (Agent ↔ Cursor)

### Purpose
- LLM agent interaction with Cursor interface
- Prompt injection
- Response retrieval
- GUI loop execution

### Implementation
- Uses PyAutoGUI for GUI automation
- Managed by CursorInjector + ResponseRetriever
- Runtime execution of AutonomousLoop

### Use Cases
- Typing prompts into Cursor chat
- Copying agent responses
- GUI loop execution
- LLM I/O channel

## Workflow Example

1. **Inbox Message Received**
   ```json
   {
     "type": "help_request",
     "from": "Agent-5",
     "to": "Agent-2",
     "context": "Task-123 requires expertise in X"
   }
   ```

2. **Agent Processing**
   - Agent-2 receives message
   - Parses content
   - Generates self-prompt

3. **GUI Interaction**
   - PyAutoGUI injects prompt into Cursor
   - Response is retrieved
   - Logged to devlog

4. **Response Handling**
   - Task status updated
   - Optional inbox message sent back

## Best Practices

1. **Never Mix Channels**
   - Inbox: Agent-to-agent communication only
   - PyAutoGUI: LLM I/O only

2. **Message Intentionality**
   - Every GUI interaction should be deliberate
   - Not every file change should trigger a prompt

3. **Logging**
   - All inbox messages logged
   - All GUI interactions logged
   - Clear separation in logs

4. **Error Handling**
   - Inbox errors: Retry with backoff
   - GUI errors: Fallback to alternative methods

## Implementation Guidelines

### Inbox System
```python
class InboxMessage:
    type: str
    from_agent: str
    to_agent: str
    content: dict
    timestamp: datetime
```

### PyAutoGUI Bridge
```python
class PromptInjection:
    prompt: str
    context: dict
    expected_response_type: str
```

## Security Considerations

1. **Message Validation**
   - Validate all inbox messages
   - Sanitize GUI inputs

2. **Access Control**
   - Agent-specific inbox access
   - GUI interaction permissions

3. **Rate Limiting**
   - Inbox message frequency
   - GUI interaction frequency

## Monitoring

1. **Inbox Metrics**
   - Message volume
   - Response times
   - Error rates

2. **GUI Metrics**
   - Injection success rate
   - Response retrieval success
   - Interaction latency

## Future Considerations

1. **Scalability**
   - Message queue optimization
   - GUI interaction batching

2. **Reliability**
   - Message persistence
   - GUI interaction recovery

3. **Extensibility**
   - New message types
   - Additional GUI capabilities 