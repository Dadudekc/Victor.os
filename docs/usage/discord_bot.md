# Discord Bot Usage Guide

## Overview
The Dream.OS Discord bot provides integration for agent communication and system monitoring through Discord.

## Setup

1. Configure bot token in `config.yaml`:
```yaml
discord_bot_token: "your-bot-token"
```

2. Initialize bot:
```python
from dreamos.tools.discord_bot import DiscordBot
from dreamos.core.config import AppConfig
from dreamos.automation.cursor_orchestrator import CursorOrchestrator

config = AppConfig()
orchestrator = CursorOrchestrator()
bot = DiscordBot(config, orchestrator)
await bot.start_bot()
```

## Commands

### Agent Status
```
!agent_status Agent-5
```
Returns current status of specified agent.

### Agent Task
```
!agent_task Agent-5
```
Returns current task for specified agent.

### System Status
```
!system_status
```
Returns overall system status.

### Code Search
```
!search_code "class Agent"
```
Searches codebase for specified query.

## Features
- Real-time agent monitoring
- Task management
- System status tracking
- Code search integration
- Error handling and logging 