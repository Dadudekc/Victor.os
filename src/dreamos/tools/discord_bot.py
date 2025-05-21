"""
Discord bot integration for Dream.OS agent system.

This module provides the DiscordBot class that handles Discord integration
for agent communication and system monitoring.
"""

import asyncio
import logging
from typing import Optional, Dict
import time
import re
from functools import wraps

import discord
from discord.ext import commands

from dreamos.core.config import AppConfig
from dreamos.automation.cursor_orchestrator import CursorOrchestrator

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, rate_limit: int = 5, time_window: int = 60):
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.command_usage: Dict[str, Dict[int, list]] = {}
        
    def is_rate_limited(self, command: str, user_id: int) -> bool:
        current_time = time.time()
        if command not in self.command_usage:
            self.command_usage[command] = {}
        if user_id not in self.command_usage[command]:
            self.command_usage[command][user_id] = []
            
        # Clean old timestamps
        self.command_usage[command][user_id] = [
            t for t in self.command_usage[command][user_id]
            if current_time - t < self.time_window
        ]
        
        if len(self.command_usage[command][user_id]) >= self.rate_limit:
            return True
            
        self.command_usage[command][user_id].append(current_time)
        return False

class DiscordBot(commands.Bot):
    """Discord bot for Dream.OS agent system integration."""
    
    def __init__(
        self,
        config: AppConfig,
        orchestrator: CursorOrchestrator,
        command_prefix: str = "!",
    ):
        """Initialize Discord bot with configuration and orchestrator."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix=command_prefix,
            intents=intents
        )
        
        self.config = config
        self.orchestrator = orchestrator
        self.token = config.discord_bot_token
        
        if not self.token:
            logger.error("Discord bot token not found in configuration")
            return
            
        # Register commands
        self.add_command(self.agent_status)
        self.add_command(self.agent_task)
        self.add_command(self.system_status)
        self.add_command(self.search_code)
        
        self.rate_limiter = RateLimiter()
        self.command_patterns = {
            'addtrade': r'^!addtrade\s+[A-Za-z0-9]+\s+\d+(\.\d+)?$',
            'context': r'^!context\s+[A-Za-z0-9]+$',
            'assign': r'^!assign\s+[A-Za-z0-9]+\s+[A-Za-z0-9]+$'
        }
        
    async def setup_hook(self):
        # Add security headers
        self.http.headers.update({
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
        })
        
    def validate_command(self, command: str, content: str) -> bool:
        """Validate command format and content"""
        if command not in self.command_patterns:
            return False
        return bool(re.match(self.command_patterns[command], content))
        
    def rate_limit_check(self, command: str, user_id: int) -> bool:
        """Check if user is rate limited"""
        return self.rate_limiter.is_rate_limited(command, user_id)

    async def on_ready(self):
        """Handle bot ready event."""
        logger.info(f"Discord bot logged in as {self.user}")
        
    @commands.command(name="agent_status")
    async def agent_status(self, ctx, agent_id: str):
        """Get status of a specific agent."""
        try:
            status = await self.orchestrator.get_agent_status(agent_id)
            await ctx.send(f"Status for {agent_id}: {status}")
        except Exception as e:
            logger.error(f"Error getting agent status: {e}")
            await ctx.send(f"Error getting status for {agent_id}")
            
    @commands.command(name="agent_task")
    async def agent_task(self, ctx, agent_id: str):
        """Get current task for a specific agent."""
        try:
            task = await self.orchestrator.get_agent_task(agent_id)
            await ctx.send(f"Current task for {agent_id}: {task}")
        except Exception as e:
            logger.error(f"Error getting agent task: {e}")
            await ctx.send(f"Error getting task for {agent_id}")
            
    @commands.command(name="system_status")
    async def system_status(self, ctx):
        """Get overall system status."""
        try:
            status = await self.orchestrator.get_system_status()
            await ctx.send(f"System Status:\n{status}")
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            await ctx.send("Error getting system status")
            
    @commands.command(name="search_code")
    async def search_code(self, ctx, query: str):
        """Search codebase for specific query."""
        try:
            results = await self.orchestrator.search_code(query)
            if results:
                await ctx.send(f"Search results for '{query}':\n{results}")
            else:
                await ctx.send(f"No results found for '{query}'")
        except Exception as e:
            logger.error(f"Error searching code: {e}")
            await ctx.send("Error performing code search")
            
    async def start_bot(self):
        """Start the Discord bot."""
        if not self.token:
            logger.error("Cannot start bot: No token available")
            return
            
        try:
            await self.start(self.token)
        except discord.LoginFailure:
            logger.error("Failed to log in to Discord")
        except Exception as e:
            logger.error(f"Error starting Discord bot: {e}")
            
    async def stop_bot(self):
        """Stop the Discord bot."""
        try:
            await self.close()
        except Exception as e:
            logger.error(f"Error stopping Discord bot: {e}")

def command_with_validation():
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            # Rate limiting check
            if self.rate_limit_check(func.__name__, ctx.author.id):
                await ctx.send("Rate limit exceeded. Please try again later.")
                return
                
            # Input validation
            if not self.validate_command(func.__name__, ctx.message.content):
                await ctx.send("Invalid command format. Please check the syntax.")
                return
                
            # Execute command
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator

# Example command with validation
@commands.command(name='addtrade')
@command_with_validation()
async def add_trade(self, ctx, symbol: str, amount: float):
    """Add a trade with validated input"""
    # Command implementation
    await ctx.send(f"Trade added: {symbol} {amount}")

# ... existing code ... 