import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable

# Correct imports based on identified structure
from ..coordination.agent_bus import SimpleEventBus as AgentBus, BaseEvent, EventType

logger = logging.getLogger("ConversationLogger")
DATABASE_PATH = Path("runtime/logs/conversation_log.db")

class ConversationLogger:
    """Logs conversation turns (prompts/replies) to an SQLite database via AgentBus events."""

    def __init__(self, agent_bus: AgentBus, db_path: Path = DATABASE_PATH):
        self.agent_bus = agent_bus
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._setup_database()
        logger.info(f"ConversationLogger initialized. Logging to: {self.db_path}")

    def _get_db_connection(self) -> sqlite3.Connection:
        """Establishes or returns the SQLite connection."""
        if self.conn is None:
            try:
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                # isolation_level=None enables autocommit for simplicity here,
                # consider explicit transactions for more complex operations.
                self.conn = sqlite3.connect(self.db_path, isolation_level=None, check_same_thread=False)
                self.conn.execute("PRAGMA journal_mode=WAL;") # Improve concurrency
                logger.info(f"Connected to conversation log database: {self.db_path}")
            except sqlite3.Error as e:
                logger.error(f"Error connecting to database {self.db_path}: {e}", exc_info=True)
                raise
        return self.conn

    def _setup_database(self):
        """Creates the necessary table if it doesn't exist."""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_turns (
                turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT, -- Optional: Link turns in a single logical conversation
                task_id TEXT,         -- Link to the specific task being worked on
                timestamp TEXT NOT NULL, -- ISO8601 Format
                actor TEXT NOT NULL,     -- Who generated the content (e.g., 'user', 'agent_id', 'system')
                turn_type TEXT NOT NULL, -- e.g., 'prompt', 'reply', 'thought', 'tool_call', 'tool_result'
                content TEXT NOT NULL,   -- The actual text content
                metadata TEXT          -- Optional JSON blob for extra context
            )
            """)
            # Optional: Create indexes for faster querying
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversation_id ON conversation_turns (conversation_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_id ON conversation_turns (task_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON conversation_turns (timestamp);")
            logger.info("Database table 'conversation_turns' verified/created.")
        except sqlite3.Error as e:
            logger.error(f"Error setting up database table: {e}", exc_info=True)

    def register_event_handlers(self):
        """Registers handlers for agent prompt/response events."""
        # Use the string values from the EventType enum
        # Assuming AGENT_PROMPT_REQUEST contains the prompt sent *to* an agent
        # Assuming AGENT_PROMPT_RESPONSE contains the reply *from* an agent
        # Note: Adjust event_type strings if the actual enum values are different
        self.agent_bus.register_handler(EventType.AGENT_PROMPT_REQUEST.value, self._handle_agent_prompt_request)
        self.agent_bus.register_handler(EventType.AGENT_PROMPT_RESPONSE.value, self._handle_agent_prompt_response)
        # Consider logging other relevant events like TOOL_CALL, TOOL_RESULT?
        # self.agent_bus.register_handler(EventType.TOOL_CALL.value, self._handle_tool_call)
        # self.agent_bus.register_handler(EventType.TOOL_RESULT.value, self._handle_tool_result)
        logger.info("Registered conversation log event handlers for prompt requests and responses.")

    def _log_turn(
        self,
        conversation_id: Optional[str],
        task_id: Optional[str],
        actor: str,
        turn_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Inserts a single turn into the database."""
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds') + "Z"
        metadata_json = json.dumps(metadata) if metadata else None
        
        sql = """INSERT INTO conversation_turns 
                 (conversation_id, task_id, timestamp, actor, turn_type, content, metadata)
                 VALUES (?, ?, ?, ?, ?, ?, ?)"""
        
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute(sql, (conversation_id, task_id, timestamp, actor, turn_type, content, metadata_json))
            # logger.debug(f"Logged turn: Actor={actor}, Type={turn_type}, Task={task_id}")
        except sqlite3.Error as e:
            logger.error(f"Error logging conversation turn to database: {e}", exc_info=True)
            # Potential issue: DB connection might be lost. Add reconnection logic? 
        except Exception as e:
             logger.error(f"Unexpected error logging conversation turn: {e}", exc_info=True)

    # --- Updated Event Handlers ---

    def _handle_agent_prompt_request(self, event: BaseEvent):
        """Handles AGENT_PROMPT_REQUEST event."""
        try:
            logger.debug(f"Received AGENT_PROMPT_REQUEST data: {event.data}") # Verify payload
            # Extract data based on expected BaseEvent structure
            # We need to KNOW what fields are in event.data for this event type
            task_id = event.data.get("task_id")
            conversation_id = event.data.get("conversation_id") # If available
            prompt_content = event.data.get("prompt")
            target_agent_id = event.data.get("target_agent_id") # Assuming this field exists
            # Who is sending the prompt? The event source or someone else?
            initiator = event.source_id # Or event.data.get("initiator")?
            metadata = event.data.get("metadata", {})
            # Add event details to metadata for context
            metadata["event_id"] = event.event_id
            metadata["event_source_id"] = event.source_id
            metadata["target_agent_id"] = target_agent_id

            if not prompt_content:
                logger.warning(f"Skipping prompt request logging, missing prompt content in event: {event.event_type.value}")
                return
            
            # Actor is who initiated the prompt
            self._log_turn(
                conversation_id=conversation_id,
                task_id=task_id,
                actor=initiator,
                turn_type="prompt_request", # More specific type
                content=prompt_content,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Error handling {EventType.AGENT_PROMPT_REQUEST.value} event: {e}", exc_info=True)

    def _handle_agent_prompt_response(self, event: BaseEvent):
        """Handles AGENT_PROMPT_RESPONSE event."""
        try:
            logger.debug(f"Received AGENT_PROMPT_RESPONSE data: {event.data}") # Verify payload
            # Extract data based on expected BaseEvent structure
            # We need to KNOW what fields are in event.data for this event type
            task_id = event.data.get("task_id")
            conversation_id = event.data.get("conversation_id") # If available
            reply_content = event.data.get("response") # Assuming field name is 'response'
            agent_id = event.source_id # Agent providing the response
            metadata = event.data.get("metadata", {})
            # Add event details to metadata for context
            metadata["event_id"] = event.event_id
            metadata["request_event_id"] = event.data.get("request_event_id") # Link to prompt if available
            metadata["processing_time_ms"] = event.data.get("processing_time_ms")

            if not reply_content or not agent_id:
                logger.warning(f"Skipping prompt response logging, missing response content or source_id in event: {event.event_type.value}")
                return

            # Actor is the agent who generated the response
            self._log_turn(
                conversation_id=conversation_id,
                task_id=task_id,
                actor=agent_id,
                turn_type="prompt_response", # More specific type
                content=reply_content,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Error handling {EventType.AGENT_PROMPT_RESPONSE.value} event: {e}", exc_info=True)

    def close(self):
        """Closes the database connection if open."""
        if self.conn:
            try:
                self.conn.close()
                self.conn = None
                logger.info("Conversation log database connection closed.")
            except sqlite3.Error as e:
                logger.error(f"Error closing database connection: {e}", exc_info=True) 