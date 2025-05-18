# Message Routing Quick Guide

**Version:** 1.0
**Purpose:** Fast reference for message handling across Dream.OS

## Quick Reference Table

| Message Type | Subtype | Action | GUI Required | Log Location | Metrics |
|--------------|---------|---------|--------------|--------------|---------|
| `inter_agent` | `task_handoff` | Check task pool, claim if capacity | ❌ | devlog | task_metrics.json |
| `inter_agent` | `status_update` | Update agent status files | ❌ | devlog | agent_metrics.json |
| `inter_agent` | `help_request` | Match responder with LLM | ✅ | devlog | help_metrics.json |
| `prompt` | `task_execution` | GUI interaction with LLM | ✅ | devlog | task_metrics.json |
| `prompt` | `help_response` | Route response with LLM | ✅ | devlog | help_metrics.json |

## Message Type Details

### 1. Inter-Agent Messages

#### task_handoff
```yaml
action: "Check task pool, claim if capacity"
files:
  - working_tasks.json
  - task_board.json
  - devlog.md
no_gui: true
metrics: task_metrics.json
```

#### status_update
```yaml
action: "Update agent status files"
files:
  - agent_status.json
  - devlog.md
no_gui: true
metrics: agent_metrics.json
```

#### help_request
```yaml
action: "Match responder with LLM"
files:
  - help_requests.json
  - devlog.md
gui_required: true
metrics: help_metrics.json
```

### 2. Prompt Messages

#### task_execution
```yaml
action: "GUI interaction with LLM"
files:
  - working_tasks.json
  - devlog.md
gui_required: true
metrics: task_metrics.json
```

#### help_response
```yaml
action: "Route response with LLM"
files:
  - help_responses.json
  - devlog.md
gui_required: true
metrics: help_metrics.json
```

## Response Format Conventions

### Inter-Agent Messages
```json
{
  "type": "inter_agent",
  "subtype": "<subtype>",
  "sender": "Agent-<n>",
  "timestamp": "ISO8601",
  "content": {
    // Message-specific content
  },
  "metadata": {
    "priority": "high|medium|low",
    "requires_ack": true|false
  }
}
```

### Prompt Messages
```json
{
  "type": "prompt",
  "subtype": "<subtype>",
  "sender": "Agent-<n>",
  "timestamp": "ISO8601",
  "content": {
    "prompt": "string",
    "context": "string"
  },
  "metadata": {
    "injection_type": "cursor|discord",
    "response_format": "markdown|json"
  }
}
```

## Logging Policy

1. **Devlog Entry Format**:
   ```markdown
   ## [TIMESTAMP] Message Processing
   - Type: <type>
   - Subtype: <subtype>
   - Action: <action_taken>
   - Status: <success|failure>
   - Details: <relevant_details>
   ```

2. **Metrics Update Format**:
   ```json
   {
     "timestamp": "ISO8601",
     "message_type": "<type>",
     "subtype": "<subtype>",
     "processing_time_ms": <number>,
     "status": "success|failure",
     "error": "<error_message_if_any>"
   }
   ```

## Error Handling

1. **Message Processing Errors**:
   - Log to devlog
   - Update metrics
   - Notify sender
   - Retry if appropriate

2. **GUI Interaction Errors**:
   - Log to devlog
   - Update metrics
   - Notify THEA
   - Attempt recovery

## Quick Commands

### For Discord Commander
```bash
# Check message type
!msgtype <message_content>

# Route message
!route <message_content>

# Get message status
!status <message_id>
```

### For Agents
```python
# Process message
process_message(message)

# Update metrics
update_metrics(message_type, status)

# Log to devlog
log_to_devlog(message, action, status)
```

## Best Practices

1. **Always validate** message schema before processing
2. **Check capacity** before claiming tasks
3. **Log immediately** after any action
4. **Update metrics** for all operations
5. **Notify THEA** of critical events
6. **Maintain queue** integrity at all times

## Recovery Procedures

1. **Message Queue Recovery**:
   - Check queue integrity
   - Requeue failed messages
   - Update status files

2. **Task State Recovery**:
   - Validate task states
   - Requeue stalled tasks
   - Update task board

3. **GUI Recovery**:
   - Reset CursorInjector
   - Clear response buffer
   - Retry failed injection 