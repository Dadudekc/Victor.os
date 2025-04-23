import os
import json
import zlib
import base64
import logging
import threading
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from cachetools import LRUCache
from jinja2 import Environment, FileSystemLoader

# Configure module-level logger
# Logs will be handled by the application's root logger configuration
logger = logging.getLogger(__name__)

###############################################################################
# Database Manager for Long-Term Storage
###############################################################################
class DatabaseManager:
    """
    DatabaseManager stores interactions and conversation metadata for
    long-term retention using SQLite.
    """

    def __init__(self, db_file: str = "memory/engagement_memory.db"):
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        self.db_file = db_file
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        self._initialize_db()
        logger.info(f"DatabaseManager initialized with db file: {self.db_file}")

    def _initialize_db(self):
        try:
            with self.conn: # Use context manager for transactions
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS interactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        platform TEXT,
                        username TEXT,
                        interaction_id TEXT,
                        timestamp TEXT,
                        response TEXT,
                        sentiment TEXT,
                        success INTEGER,
                        chatgpt_url TEXT
                    )
                """)
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversations_metadata (
                        interaction_id TEXT PRIMARY KEY,
                        initialized_at TEXT,
                        metadata TEXT
                    )
                """)
            logger.debug("Database schema initialized successfully.")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}", exc_info=True)
            raise # Re-raise critical initialization errors

    def record_interaction(self, record: Dict[str, Any]):
        sql = """
            INSERT INTO interactions (
                platform, username, interaction_id, timestamp, response, sentiment, success, chatgpt_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            record.get("platform"),
            record.get("username"),
            record.get("interaction_id"),
            record.get("timestamp", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")), # Default timestamp
            record.get("response"),
            record.get("sentiment"),
            1 if record.get("success") else 0,
            record.get("chatgpt_url")
        )
        try:
            with self.conn:
                self.conn.execute(sql, params)
            logger.debug(f"Recorded interaction for ID: {record.get('interaction_id')}")
        except sqlite3.Error as e:
            logger.error(f"Failed to record interaction: {e}", exc_info=True)

    def initialize_conversation(self, interaction_id: str, metadata: Dict[str, Any]):
        sql = """
            INSERT OR IGNORE INTO conversations_metadata (interaction_id, initialized_at, metadata)
            VALUES (?, ?, ?)
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        params = (interaction_id, timestamp, json.dumps(metadata))
        try:
            with self.conn:
                self.conn.execute(sql, params)
            logger.debug(f"Initialized conversation metadata for ID: {interaction_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize conversation: {e}", exc_info=True)

    def get_conversation(self, interaction_id: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT platform, username, interaction_id, timestamp, response, sentiment, success, chatgpt_url
            FROM interactions
            WHERE interaction_id = ?
            ORDER BY timestamp ASC
        """
        try:
            with self.conn:
                cursor = self.conn.execute(sql, (interaction_id,))
                rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Failed to get conversation {interaction_id}: {e}", exc_info=True)
            return []

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None # Indicate closed connection
            logger.info("Database connection closed.")


###############################################################################
# Unified Memory Manager (In-Memory + DB + Narrative)
###############################################################################
class UnifiedMemoryManager:
    """
    UnifiedMemoryManager combines features from an optimized memory manager with:
      - LRU caching and data compression (for fast short-term storage)
      - JSON file storage for ephemeral memory segments
      - SQLite-based long-term storage of interactions via DatabaseManager
      - Narrative generation via Jinja2 templates

    Memory is segmented by context (e.g. "system", "prompts", "interactions").
    """

    def __init__(self,
                 max_cache_size: int = 500,
                 memory_dir: Optional[str] = None,
                 db_file: str = "memory/engagement_memory.db",
                 template_dir: str = "templates"):
        # Setup cache and lock
        self.cache = LRUCache(maxsize=max_cache_size)
        self._lock = threading.Lock()
        # self.logger = logger # Using module logger

        # Setup memory directory
        self.memory_dir = memory_dir or os.path.join(os.getcwd(), "memory")
        os.makedirs(self.memory_dir, exist_ok=True)

        # Memory segments (loaded from files)
        self.memory_segments: Dict[str, Dict[str, bytes]] = {}
        self._load_all_segments()

        # Initialize database manager for long-term storage
        try:
            self.db_manager = DatabaseManager(db_file)
        except Exception as db_err:
             logger.critical(f"Failed to initialize DatabaseManager: {db_err}", exc_info=True)
             raise # Re-raise critical errors

        # Initialize Jinja2 environment for narrative generation
        try:
            self.jinja_env = Environment(loader=FileSystemLoader(template_dir),
                                         trim_blocks=True,
                                         lstrip_blocks=True)
            logger.info(f"Jinja environment initialized for templates in: {template_dir}")
        except Exception as jinja_err:
            logger.warning(f"Failed to initialize Jinja environment (template dir: {template_dir}): {jinja_err}")
            self.jinja_env = None # Indicate Jinja is unavailable

        logger.info(f"UnifiedMemoryManager initialized. Memory Dir: {self.memory_dir}")


    # -----------------------------
    # Segment Loading/Saving (Separate files)
    # -----------------------------
    def _get_segment_file_path(self, segment: str) -> str:
        """Constructs the file path for a given memory segment."""
        # Simple sanitization, consider more robust if needed
        safe_segment_name = "".join(c for c in segment if c.isalnum() or c in ('_', '-')).rstrip("_-")
        return os.path.join(self.memory_dir, f"{safe_segment_name}_memory.json.zlib")

    def _load_segment(self, segment: str):
        """Loads a single memory segment from its compressed file."""
        segment_file = self._get_segment_file_path(segment)
        segment_data: Dict[str, bytes] = {}
        if os.path.exists(segment_file):
            try:
                with open(segment_file, 'rb') as f:
                    # File contains zlib-compressed JSON of base64-encoded values
                    raw_data = f.read()
                    if raw_data:
                        text = zlib.decompress(raw_data).decode('utf-8')
                        loaded = json.loads(text)
                        # Decode base64 strings back to bytes for each key
                        segment_data = {k: base64.b64decode(v) if isinstance(v, str) else v
                                        for k, v in loaded.items()}
                self.memory_segments[segment] = segment_data
                logger.debug(f"Loaded segment '{segment}' ({len(segment_data)} items) from {segment_file}")
            except Exception as e:
                logger.error(f"Error loading segment '{segment}' from {segment_file}: {e}", exc_info=True)
                self.memory_segments[segment] = {} # Initialize empty on error
        else:
            logger.debug(f"Segment file not found for '{segment}', initializing empty.")
            self.memory_segments[segment] = {}

    def _load_all_segments(self):
        """Loads all known/expected segments or discovers segment files."""
        # Define expected segments or discover *.json.zlib files in memory_dir
        expected_segments = ["prompts", "feedback", "context", "system", "interactions"]
        for segment in expected_segments:
             self._load_segment(segment)
        # TODO: Optionally add discovery of other segment files in the directory

    def _save_segment(self, segment: str):
        """Saves a specific memory segment to its compressed file."""
        segment_file = self._get_segment_file_path(segment)
        segment_data = self.memory_segments.get(segment, {})
        try:
            # Convert binary values to base64-encoded strings for JSON
            serializable_data = {k: base64.b64encode(v).decode('ascii') if isinstance(v, (bytes, bytearray)) else v
                                  for k, v in segment_data.items()}
            serialized_data = json.dumps(serializable_data).encode('utf-8')
            compressed_blob = zlib.compress(serialized_data, level=6)
            with open(segment_file, 'wb') as f:
                f.write(compressed_blob)
            logger.debug(f"Saved segment '{segment}' ({len(segment_data)} items) to {segment_file}")
        except Exception as e:
            logger.error(f"Error saving segment '{segment}' to {segment_file}: {e}", exc_info=True)

    # -----------------------------
    # Optimized Storage Methods (Caching & Compression)
    # -----------------------------
    def set(self, key: str, data: Any, segment: str = "system") -> None:
        """
        Store JSON-serializable data with compression in a memory segment.
        Updates cache, in-memory segment dict, and saves segment file.
        """
        with self._lock:
            try:
                json_str = json.dumps(data)
                compressed = zlib.compress(json_str.encode('utf-8'))
                cache_key = f"{segment}:{key}"
                self.cache[cache_key] = compressed # Update cache

                # Ensure segment exists in memory_segments
                if segment not in self.memory_segments:
                    self._load_segment(segment) # Load if not present

                self.memory_segments.setdefault(segment, {})[key] = compressed # Update in-memory dict
                self._save_segment(segment) # Persist change to file
                logger.info(f"Stored data in '{segment}:{key}'")
            except TypeError as e:
                 logger.error(f"Data for key '{key}' in segment '{segment}' is not JSON serializable: {e}")
            except Exception as e:
                logger.error(f"Error storing data in '{segment}:{key}': {e}", exc_info=True)

    def get(self, key: str, segment: str = "system", default: Any = None) -> Optional[Any]:
        """
        Retrieve data from cache or memory segment storage.
        Returns default if key not found or error occurs.
        """
        cache_key = f"{segment}:{key}"
        compressed = None
        try:
            # 1. Check Cache
            if cache_key in self.cache:
                compressed = self.cache[cache_key]
                source = "cache"
            # 2. Check In-Memory Segments (load segment if necessary)
            else:
                if segment not in self.memory_segments:
                    self._load_segment(segment) # Attempt load on demand

                segment_data = self.memory_segments.get(segment, {})
                if key in segment_data:
                    compressed = segment_data[key]
                    self.cache[cache_key] = compressed # Add to cache on miss
                    source = "segment file"
                else:
                    # Key not found in cache or loaded segment
                    logger.debug(f"Key '{key}' not found in segment '{segment}'")
                    return default

            # 3. Decompress and Load JSON
            json_str = zlib.decompress(compressed).decode('utf-8')
            data = json.loads(json_str)
            logger.debug(f"Retrieved key '{key}' from segment '{segment}' (source: {source})")
            return data
        except Exception as e:
            logger.error(f"Error retrieving '{segment}:{key}': {e}", exc_info=True)
            # Invalidate cache if error occurred during retrieval?
            if cache_key in self.cache: del self.cache[cache_key]
            return default

    def delete(self, key: str, segment: str = "system") -> bool:
        """
        Delete a key from cache, in-memory segment, and segment file.
        """
        with self._lock:
            deleted = False
            try:
                cache_key = f"{segment}:{key}"
                if cache_key in self.cache:
                    del self.cache[cache_key]

                if segment in self.memory_segments and key in self.memory_segments[segment]:
                    del self.memory_segments[segment][key]
                    self._save_segment(segment) # Persist deletion
                    deleted = True

                if deleted:
                     logger.info(f"Deleted key '{key}' from segment '{segment}'")
                else:
                     logger.debug(f"Key '{key}' not found in segment '{segment}' for deletion.")
                return deleted
            except Exception as e:
                logger.error(f"Error deleting '{segment}:{key}': {e}", exc_info=True)
                return False

    def clear_segment(self, segment: str) -> None:
        """
        Clear all keys in a memory segment (cache, in-memory, file).
        """
        with self._lock:
            # Clear in-memory
            self.memory_segments[segment] = {}
            # Clear cache entries for this segment
            keys_to_remove = [k for k in self.cache if k.startswith(f"{segment}:")]
            for key in keys_to_remove:
                del self.cache[key]
            # Save the now-empty segment (effectively deleting the file content)
            self._save_segment(segment)
            logger.info(f"Cleared segment '{segment}'")

    def get_segment_keys(self, segment: str) -> List[str]:
        """Return all keys currently loaded in a memory segment."""
        if segment not in self.memory_segments:
             self._load_segment(segment) # Ensure segment is loaded
        return list(self.memory_segments.get(segment, {}).keys())

    # --- Getters for size and stats remain the same ---
    def get_segment_size(self, segment: str) -> int:
        """
        Return the number of items in a memory segment.
        """
        return len(self.memory_segments.get(segment, {}))

    def get_stats(self) -> Dict[str, Any]:
        """
        Return statistics about the memory manager.
        """
        stats = {
            "cache_size": len(self.cache),
            "cache_maxsize": self.cache.maxsize,
            "segments": {}
        }
        # Ensure all segment sizes are reported, loading if needed
        known_segments = list(self.memory_segments.keys())
        # Add any expected segments not yet loaded if desired
        # expected_segments = ["prompts", "feedback", "context", "system", "interactions"]
        # for seg in expected_segments:
        #     if seg not in known_segments: known_segments.append(seg)

        for segment in known_segments:
             if segment not in self.memory_segments: self._load_segment(segment)
             data = self.memory_segments.get(segment, {})
             stats["segments"][segment] = {
                 "items": len(data),
                 "compressed_size_bytes": sum(len(v) for v in data.values())
             }
        return stats

    def optimize(self) -> None:
        """
        Optimize memory usage by clearing the cache and recompressing data.
        """
        with self._lock:
            self.cache.clear()
            logger.info("Cache cleared for optimization.")
            for segment in list(self.memory_segments.keys()): # Iterate over keys copy
                 data = self.memory_segments.get(segment, {})
                 optimized_data = {}
                 recompressed_count = 0
                 for key, compressed in data.items():
                     try:
                         # Decompress, re-encode, re-compress with max level
                         json_str = zlib.decompress(compressed).decode('utf-8')
                         optimized_data[key] = zlib.compress(json_str.encode('utf-8'), level=9)
                         recompressed_count += 1
                     except Exception as e:
                         logger.error(f"Error optimizing '{segment}:{key}': {e}")
                         optimized_data[key] = compressed # Keep original if error
                 self.memory_segments[segment] = optimized_data
                 if recompressed_count > 0:
                    self._save_segment(segment)
                 logger.info(f"Optimized segment '{segment}' ({recompressed_count} items recompressed).")
            logger.info("Memory optimization completed.")


    # -----------------------------
    # Interaction Recording and Conversation Management (Using DB Manager)
    # -----------------------------
    def record_interaction(self,
                           platform: str,
                           username: str,
                           response: str,
                           sentiment: str,
                           success: bool,
                           interaction_id: Optional[str] = None,
                           chatgpt_url: Optional[str] = None):
        """
        Record an interaction primarily in the long-term DB storage.
        (Optionally could still cache/log recent ones in JSON segment if needed)
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        interaction_record = {
            "platform": platform,
            "username": username,
            "interaction_id": interaction_id,
            "timestamp": timestamp,
            "response": response,
            "sentiment": sentiment,
            "success": success,
            "chatgpt_url": chatgpt_url
        }
        self.db_manager.record_interaction(interaction_record)
        # Optionally, add to a short-term 'recent_interactions' segment/cache?
        # key = f"{username}_{timestamp}"
        # self.set(key, interaction_record, segment="interactions")

    def initialize_conversation(self, interaction_id: str, metadata: Dict[str, Any]):
        """
        Initialize a conversation with metadata in the database.
        """
        self.db_manager.initialize_conversation(interaction_id, metadata)

    def retrieve_conversation(self, interaction_id: str) -> List[Dict[str, Any]]:
        """Retrieve a conversation by its interaction_id from the database."""
        return self.db_manager.get_conversation(interaction_id)

    def export_conversation_for_finetuning(self, interaction_id: str, export_path: str) -> bool:
        """
        Export conversation data from the database for fine-tuning.
        Each interaction is transformed into a message pair.
        """
        conversation = self.retrieve_conversation(interaction_id)
        if not conversation:
            logger.warning(f"No conversation found with ID '{interaction_id}' for export.")
            return False

        # Simple user/assistant pair based on response - adjust if more complex roles needed
        fine_tuning_data = [
            {
                "messages": [
                    {"role": "user", "content": f"Context before interaction on {interaction['timestamp']}"}, # Placeholder user message
                    {"role": "assistant", "content": interaction["response"]}
                ]
            } for interaction in conversation if interaction.get("response") # Only include items with a response
        ]

        if not fine_tuning_data:
             logger.warning(f"No valid messages found in conversation '{interaction_id}' for export.")
             return False

        try:
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            with open(export_path, 'w', encoding='utf-8') as f:
                for entry in fine_tuning_data:
                    f.write(json.dumps(entry) + "\n")
            logger.info(f"Conversation '{interaction_id}' exported for fine-tuning to: {export_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting conversation '{interaction_id}': {e}", exc_info=True)
            return False

    # --- User History/Sentiment (Would need DB queries) ---
    # These methods would need rewriting to query the database instead of relying
    # on the deprecated self.data structure.
    def get_user_history(self, platform: str, username: str, limit: int = 5) -> List[Dict[str, Any]]:
        logger.warning("get_user_history currently requires database implementation.")
        # Example SQL (needs refinement):
        # SELECT ... FROM interactions WHERE platform = ? AND username = ? ORDER BY timestamp DESC LIMIT ?
        return []

    def user_sentiment_summary(self, platform: str, username: str) -> Dict[str, Any]:
        logger.warning("user_sentiment_summary currently requires database implementation.")
        # Example SQL (needs refinement):
        # SELECT sentiment, success, COUNT(*) FROM interactions WHERE platform = ? AND username = ? GROUP BY sentiment, success
        return {"message": "Not implemented using DB yet"}

    def clear_user_history(self, platform: str, username: str):
        logger.warning("clear_user_history currently requires database implementation.")
        # Example SQL (needs refinement): DELETE FROM interactions WHERE platform = ? AND username = ?

    def clear_platform_history(self, platform: str):
        logger.warning("clear_platform_history currently requires database implementation.")
        # Example SQL (needs refinement): DELETE FROM interactions WHERE platform = ?

    # -----------------------------
    # Narrative Generation via Jinja2
    # -----------------------------
    def generate_narrative(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a narrative using a Jinja template.
        Example: 'dreamscape_template.txt' in the templates directory.
        """
        if not self.jinja_env:
             logger.error("Jinja environment not available for narrative generation.")
             return "[ERROR: Jinja environment not configured]"
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except jinja2.TemplateNotFound:
            logger.error(f"Narrative template not found: {template_name}")
            return f"[ERROR: Template '{template_name}' not found]"
        except Exception as e:
            logger.error(f"Error generating narrative with template '{template_name}': {e}", exc_info=True)
            return f"[ERROR: Failed to render template '{template_name}']"

    # -----------------------------
    # Close Resources
    # -----------------------------
    def close(self):
        """Close the database connection."""
        if hasattr(self, 'db_manager') and self.db_manager:
            self.db_manager.close()

    def __del__(self):
         # Ensure cleanup even if close() isn't explicitly called
         self.close()


# ---------------------------------------------------
# Example Usage (Can be removed or kept for testing)
# ---------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger.info("--- Running UnifiedMemoryManager Example ---")

    # Ensure templates directory exists for the example
    if not os.path.exists("templates"): os.makedirs("templates")
    # Create a dummy template file
    dummy_template_path = "templates/dreamscape_template.txt"
    if not os.path.exists(dummy_template_path):
         with open(dummy_template_path, "w") as f:
             f.write("Dreamscape Log: {{ audit_title }}\nObjective: {{ objective }}")
         logger.info(f"Created dummy template: {dummy_template_path}")

    # Create an instance of the unified memory manager.
    mm = UnifiedMemoryManager(template_dir="templates") # Point to local templates dir

    # Record some interactions
    mm.record_interaction(
        platform="Discord", username="Alice", response="Task A complete.",
        sentiment="positive", success=True, interaction_id="conv_001"
    )
    mm.record_interaction(
        platform="Discord", username="Alice", response="Task B failed.",
        sentiment="negative", success=False, interaction_id="conv_001"
    )
    mm.record_interaction(
        platform="Web", username="Bob", response="Login successful.",
        sentiment="neutral", success=True, interaction_id="conv_002"
    )

    # Initialize conversations
    mm.initialize_conversation("conv_001", {"topic": "Task Updates", "user_level": 5})
    mm.initialize_conversation("conv_002", {"topic": "Authentication", "user_level": 1})

    # Retrieve and print a conversation
    alice_conv = mm.retrieve_conversation("conv_001")
    print("\n--- Alice's Conversation (conv_001) ---")
    for msg in alice_conv: print(msg)

    # Generate a narrative
    narrative_context = {
        "audit_title": "Example Audit",
        "objective": "Test narrative generation.",
    }
    narrative = mm.generate_narrative("dreamscape_template.txt", narrative_context)
    print("\n--- Generated Narrative ---")
    print(narrative)

    # Demonstrate segment storage
    mm.set("user_prefs", {"theme": "dark", "notifications": True}, segment="system")
    prefs = mm.get("user_prefs", segment="system")
    print("\n--- System Segment Example ---")
    print(f"User Prefs: {prefs}")
    print(f"Keys in system segment: {mm.get_segment_keys('system')}")

    # Export a conversation
    if mm.export_conversation_for_finetuning("conv_001", "exports/conv_001_finetune.jsonl"):
        print("\nConversation conv_001 exported successfully.")
    else:
        print("\nFailed to export conversation conv_001.")

    # Print stats
    print("\n--- Memory Stats ---")
    print(json.dumps(mm.get_stats(), indent=2))

    # Close resources
    mm.close()
    logger.info("--- UnifiedMemoryManager Example Finished ---") 