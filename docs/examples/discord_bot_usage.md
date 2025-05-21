# Discord Bot Usage Examples

## Overview
The Dream.OS Discord bot provides integration for agent communication and system monitoring through Discord.

## Setup

1. Configure Discord Bot Token:
```python
# config.yaml
discord_bot_token: "your-bot-token-here"
```

2. Initialize Bot:
```python
from dreamos.tools.discord_bot import DiscordBot
from dreamos.core.config import AppConfig
from dreamos.automation.cursor_orchestrator import CursorOrchestrator

config = AppConfig()
orchestrator = CursorOrchestrator(config)
bot = DiscordBot(config, orchestrator)

# Start bot
await bot.start_bot()
```

## Available Commands

### Agent Status
```
!agent_status <agent_id>
```
Example:
```
!agent_status Agent-7
```
Response:
```
Status for Agent-7: Active - Processing task TASK-123
```

### Agent Task
```
!agent_task <agent_id>
```
Example:
```
!agent_task Agent-7
```
Response:
```
Current task for Agent-7: Implement documentation for semantic scanner
```

### System Status
```
!system_status
```
Example:
```
!system_status
```
Response:
```
System Status:
- Active Agents: 5
- Pending Tasks: 3
- System Load: 45%
- Memory Usage: 2.3GB
```

### Code Search
```
!search_code <query>
```
Example:
```
!search_code class SemanticScanner
```
Response:
```
Search results for 'class SemanticScanner':
- src/dreamos/tools/scanner/semantic_scanner.py:42
  class SemanticScanner(BaseScanner):
  """Semantic scanner for enhanced code search capabilities."""
```

## Error Handling

The bot handles errors gracefully and provides user-friendly error messages:

```
Error getting status for Agent-7: Agent not found
Error getting task for Agent-7: Task not found
Error getting system status: System unavailable
Error performing code search: Invalid query
```

## Best Practices

1. Use agent IDs consistently (e.g., "Agent-7", "Agent-5")
2. Keep queries concise and specific
3. Monitor system status regularly
4. Use code search for quick reference
5. Handle errors appropriately

## Integration Example

```python
import asyncio
from dreamos.tools.discord_bot import DiscordBot
from dreamos.core.config import AppConfig
from dreamos.automation.cursor_orchestrator import CursorOrchestrator

async def main():
    config = AppConfig()
    orchestrator = CursorOrchestrator(config)
    bot = DiscordBot(config, orchestrator)
    
    try:
        await bot.start_bot()
    except Exception as e:
        print(f"Error starting bot: {e}")
    finally:
        await bot.stop_bot()

if __name__ == "__main__":
    asyncio.run(main())
``` 