# Discord Bot Usage Guide

## Basic Commands

### Task Management
```
!task create <description> - Create new task
!task list - Show active tasks
!task complete <id> - Mark task complete
```

### Agent Control
```
!agent status - Check agent status
!agent resume - Resume agent operation
!agent pause - Pause agent (non-blocking)
```

### Monitoring
```
!monitor cycles - Show cycle count
!monitor health - Check system health
!monitor logs - View recent logs
```

## Integration Example

```python
from dreamos.bots.discord import DiscordBot

bot = DiscordBot()
bot.start()

# Non-blocking event handling
@bot.event
async def on_message(message):
    if message.content.startswith('!task'):
        await bot.handle_task_command(message)
    # Continue processing other messages
```

## Error Recovery
- Bot continues operation on command failure
- Logs errors without stopping
- Auto-retries failed commands 