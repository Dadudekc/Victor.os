import discord
from discord.ext import commands
import yaml
import os
from pathlib import Path
from datetime import datetime

# --- Configuration ---
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # IMPORTANT: Replace with your actual bot token
JOURNAL_FILE_PATH = Path("logs/trading_journal.yaml")
COMMAND_PREFIX = "!"

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent for commands
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# --- Helper Functions ---
def ensure_journal_dir_exists():
    """Ensures the directory for the journal file exists."""
    JOURNAL_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

def append_to_journal(data: dict, author: str = "Unknown"):
    """Appends data to the YAML trading journal."""
    ensure_journal_dir_exists()
    
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "author": author,
        "data": data
    }
    
    if not JOURNAL_FILE_PATH.exists():
        with open(JOURNAL_FILE_PATH, "w") as f:
            yaml.dump([entry], f, indent=2, sort_keys=False)
    else:
        with open(JOURNAL_FILE_PATH, "r") as f:
            try:
                journal = yaml.safe_load(f) or []
            except yaml.YAMLError:
                journal = [] # If file is corrupted or not valid YAML, start fresh
        journal.append(entry)
        with open(JOURNAL_FILE_PATH, "w") as f:
            yaml.dump(journal, f, indent=2, sort_keys=False)

# --- Bot Events ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print(f"Command prefix: {COMMAND_PREFIX}")
    print("Discord Bot Core is ready to receive commands.")
    print("------")

# --- Bot Commands ---
@bot.command(name="addtrade", help="Adds a YAML formatted trade or note to the trading journal. Usage: !addtrade \nkey: value\nkey2: value2")
async def add_trade_command(ctx, *, yaml_text: str):
    """
    Parses YAML input and adds it to the trading journal.
    Example:
    !addtrade
    symbol: TSLA
    strategy: Lotto
    entry: 348
    notes: "Weekend catalyst play"
    """
    try:
        # Basic sanitization/check for common issues
        if not yaml_text.strip():
            await ctx.send("❌ Error: YAML input cannot be empty.")
            return
        
        data = yaml.safe_load(yaml_text)
        
        if not isinstance(data, dict):
            await ctx.send("❌ Error: The top-level YAML structure must be a dictionary (key-value pairs).")
            return
            
        append_to_journal(data, author=str(ctx.author))
        await ctx.send(f"✅ Entry added to your journal by {ctx.author.mention}.")
        
        # Optionally, log the raw YAML and who added it to console for auditing
        print(f"Journal entry added by {ctx.author}:\n{yaml_text}")
        
    except yaml.YAMLError as e:
        await ctx.send(f"❌ YAML Parsing Error: ```{e}``` Please check your YAML syntax.")
    except Exception as e:
        await ctx.send(f"❌ An unexpected error occurred: {e}")
        print(f"Error in addtrade command: {e}")

@bot.command(name="showtrades", help="Shows the last N trades from the journal. Usage: !showtrades [number_of_trades]")
async def show_trades_command(ctx, num_trades: int = 3):
    """
    Displays the last N trades from the trading_journal.yaml.
    Defaults to showing the last 3 trades if no number is specified.
    """
    if not JOURNAL_FILE_PATH.exists():
        await ctx.send("ℹ️ Your trading journal is currently empty.")
        return

    try:
        with open(JOURNAL_FILE_PATH, "r") as f:
            journal_entries = yaml.safe_load(f) or []
        
        if not journal_entries:
            await ctx.send("ℹ️ Your trading journal is currently empty.")
            return

        # Get the most recent entries
        recent_entries = journal_entries[-num_trades:]
        
        if not recent_entries:
            await ctx.send(f"ℹ️ No trades to show for the specified number: {num_trades}.")
            return

        response_message = f"🗓️ **Last {len(recent_entries)} Trade(s) from Your Journal:**\n---\n"
        
        for i, entry in enumerate(reversed(recent_entries)): # Show newest first
            author = entry.get("author", "N/A")
            timestamp = entry.get("timestamp", "N/A")
            raw_data = entry.get("data", {})
            
            entry_label = "Event"
            title_display = ""
            description_display = ""

            # Check if it's an agent event from journal_api.py
            if isinstance(raw_data, dict) and raw_data.get("log_source") == "agent_internal":
                agent_id_display = raw_data.get("event_agent_id", author) # Fallback to author if specific agent_id not in data
                entry_label = f"🤖 Agent Event ({agent_id_display})"
                title_display = raw_data.get("event_title", "N/A")
                description_display = raw_data.get("event_description", "No description.")
                response_message += f"**{entry_label} (Entry {len(journal_entries) - recent_entries.index(entry)})**\n"
                response_message += f"  `Logged by`: {author}\n"
                response_message += f"  `Timestamp`: {timestamp}\n"
                response_message += f"  `Title    `: {title_display}\n"
                response_message += f"  `Details  `: {description_display}\n"
            # Check for manual !addtrade like entries (heuristic: has 'symbol' or more generic key-value data)
            elif isinstance(raw_data, dict) and ("symbol" in raw_data or len(raw_data) > 0 and raw_data.get("log_source") != "agent_internal"):
                entry_label = f"📈 Manual Entry ({author})"
                response_message += f"**{entry_label} (Entry {len(journal_entries) - recent_entries.index(entry)})**\n"
                response_message += f"  `Logged by`: {author}\n"
                response_message += f"  `Timestamp`: {timestamp}\n"
                for key, value in raw_data.items():
                    response_message += f"  `{key}`: `{value}`\n"
            # Fallback for other structures
            else:
                response_message += f"**Generic Entry {len(journal_entries) - recent_entries.index(entry)}:** (Logged by: {author} at {timestamp})\n"
                response_message += f"  `Content`: `{str(raw_data)}`\n"

            response_message += "---\n"
            
            # Discord message length limit awareness
            if len(response_message) > 1800: # Leave some buffer
                await ctx.send(response_message)
                response_message = "" # Reset for next chunk
        
        if response_message: # Send any remaining part
            await ctx.send(response_message)
            
    except yaml.YAMLError as e:
        await ctx.send(f"❌ YAML Parsing Error while reading journal: ```{e}```")
    except Exception as e:
        await ctx.send(f"❌ An unexpected error occurred while retrieving trades: {e}")
        print(f"Error in showtrades command: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ERROR: Please replace 'YOUR_BOT_TOKEN_HERE' with your actual bot token in the script.")
    else:
        ensure_journal_dir_exists() # Ensure log directory exists at startup
        print(f"Attempting to connect to Discord with token prefix: {BOT_TOKEN[:5]}...")
        bot.run(BOT_TOKEN) 