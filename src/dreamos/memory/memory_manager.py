"""
Unified memory subsystem for Dream.OS
-------------------------------------

* MemoryManager   – lightweight JSON fragments (human-readable)
* DatabaseManager – SQLite interaction / conversation store
* UnifiedMemoryManager
    • LRU-compressed cache per segment
    • JSON segment persistence
    • DB bridge for interactions
    • Jinja2 narrative helpers
"""

###########################################################################
# Imports
###########################################################################
from __future__ import annotations  # noqa: I001

import asyncio
import json
import logging
import os
import sqlite3
import tempfile
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cachetools import LRUCache
from jinja2 import Environment, FileSystemLoader

from ..core.config import AppConfig

###########################################################################
# Logging
###########################################################################
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

###########################################################################
# Base paths (project-relative, no hard-coding)
###########################################################################
# PROJECT_ROOT = Path.cwd() # REMOVED - Use AppConfig
# RUNTIME_DIR = PROJECT_ROOT / "runtime" # REMOVED - Use AppConfig
# MEMORY_DIR = RUNTIME_DIR / "memory" # REMOVED - Use AppConfig
# MEMORY_DIR.mkdir(parents=True, exist_ok=True) # Initialization should use AppConfig

# Load config to get paths - MODIFIED: Load lazily or pass config in __init__
# _config = AppConfig.load() # COMMENTED OUT: Causes issues during test import
# _memory_base_path = _config.paths.memory # COMMENTED OUT
# _memory_base_path.mkdir(parents=True, exist_ok=True)  # COMMENTED OUT: Ensure path exists in __init__

###########################################################################
# Default Compaction Config
###########################################################################
DEFAULT_COMPACTION_CONFIG = {
    "enabled": True,
    "check_on_write": True,
    "default_policy": "time_based",  # or 'keep_n'
    "default_max_age_days": 30,
    "default_keep_n": 500,
    "threshold_max_size_mb": 1.0,
    "threshold_max_entries": 1000,
}


###########################################################################
# ------------------------------------------------------------------------
# 1)  Fragment JSON store  – MemoryManager
# ------------------------------------------------------------------------
###########################################################################
class MemoryManager:
    """
    Lightweight dict-of-dicts persisted to a single JSON file.
    Good for small, human-inspectable fragments. Now async-friendly.
    """

    def __init__(self, file_path: Optional[Path] = None, config: Optional[AppConfig] = None) -> None:
        self._lock = asyncio.Lock() # Add an asyncio.Lock for operations

        # Determine memory base path
        if config:
            memory_base_path = config.paths.memory
        else:
            # FIXME: AppConfig.load() fallback is problematic. Config should be explicitly passed.
            # This can lead to issues in testing or when default config path is not appropriate.
            logger.warning("MemoryManager initialized without explicit AppConfig. Attempting fallback load.")
            try:
                fallback_config = AppConfig.load() # Load with default path
                memory_base_path = fallback_config.paths.memory
            except Exception as e:
                logger.error(f"Failed to load fallback config for MemoryManager path: {e}. Using default 'runtime/memory'.")
                # Last resort fallback path
                memory_base_path = Path("runtime/memory")

        # Ensure the determined base path exists (synchronous part of init is fine for mkdir)
        try:
            memory_base_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create memory base directory {memory_base_path}: {e}")

        self.file_path: Path = file_path or (memory_base_path / "core_fragments.json")
        self.memory: Dict[str, Dict[str, Any]] = {}
        # _ensure_store and load_memory are now async, cannot be called directly from sync __init__
        # They should be called by an explicit async initialization method if needed upon creation,
        # or the first operation will handle it. For simplicity, let's assume they are called as needed.
        # Consider adding an async factory or an explicit async_init() method.
        # For now, ensure store on first write, and load lazily or via explicit call.

    # ────────────────────────────────────────────────────────────────── #
    # Internals
    # ────────────────────────────────────────────────────────────────── #
    async def _ensure_store(self) -> None:
        async with self._lock: # Protect directory and file creation
            target_dir = self.file_path.parent
            if not await asyncio.to_thread(target_dir.exists):
                await asyncio.to_thread(target_dir.mkdir, parents=True, exist_ok=True)
            if not await asyncio.to_thread(self.file_path.exists):
                await asyncio.to_thread(self.file_path.write_text, "{}")
                logger.info("Created fragment store → %s", self.file_path)

    # ────────────────────────────────────────────────────────────────── #
    # Public API
    # ────────────────────────────────────────────────────────────────── #
    async def load_memory(self) -> bool:
        """Load fragments from JSON file; ensure stored memory is a dict. Async."""
        await self._ensure_store() # Ensure file exists before reading
        async with self._lock:
            self.memory = {} # Reset memory first
            try:
                raw = await asyncio.to_thread(self.file_path.read_text)
                parsed = json.loads(raw) if raw.strip() else {}
                if not isinstance(parsed, dict):
                    logger.error("Fragment JSON must be an object, found %s", type(parsed))
                    # Optionally, reset to empty or raise more specific error
                    await asyncio.to_thread(self.file_path.write_text, "{}") # Attempt to fix by resetting
                    return False
                self.memory = parsed
                logger.info("Loaded %d fragments from %s", len(self.memory), self.file_path)
                return True
            except FileNotFoundError:
                logger.warning("Fragment store not found at %s during load. Will be created on next save.", self.file_path)
                # This is fine, _ensure_store should have created it, but if it vanished...
                self.memory = {} # Ensure memory is empty
                return True # Considered successful if file not found, starts empty
            except json.JSONDecodeError as exc:
                logger.error("Fragment load failed – JSON decode error from %s (%s). Store might be corrupted.", self.file_path, exc)
                # Attempt to reset the corrupted file
                try:
                    await asyncio.to_thread(self.file_path.write_text, "{}")
                    logger.info("Corrupted fragment store %s reset to empty.", self.file_path)
                except Exception as reset_exc:
                    logger.error("Failed to reset corrupted fragment store %s: %s", self.file_path, reset_exc)
                self.memory = {} # Reset in-memory
                return False
            except Exception as exc:
                logger.error("Fragment load failed from %s (%s)", self.file_path, exc, exc_info=True)
                self.memory = {} # Reset in-memory
                return False

    async def save_memory(self) -> bool:
        """Saves the current memory state to the JSON file. Async."""
        await self._ensure_store() # Ensure directory and file exist
        async with self._lock:
            try:
                # Create a defensive copy for serialization
                memory_to_save = dict(self.memory)
                await asyncio.to_thread(self.file_path.write_text, json.dumps(memory_to_save, indent=2))
                logger.info("Saved %d fragments to %s", len(self.memory), self.file_path)
                return True
            except Exception as exc:
                logger.error("Fragment save failed to %s (%s)", self.file_path, exc, exc_info=True)
                return False

    # CRUD helpers
    async def save_fragment(self, fragment_id: str, data: Dict[str, Any]) -> bool:
        """Saves a fragment. Async."""
        if not fragment_id or not isinstance(data, dict):
            logger.error("save_fragment: invalid id or data type (%s)", type(data))
            return False
        # Ensure memory is loaded before modifying, if not already
        if not self.memory:
            await self.load_memory() # load_memory handles its own lock
        # No separate lock needed for read if self.memory is up-to-date
        async with self._lock: # Lock for modifying self.memory then saving
            self.memory[fragment_id] = data
        return await self.save_memory() # save_memory handles its own lock for file write

    async def load_fragment(self, fragment_id: str) -> Optional[Dict[str, Any]]:
        """Loads a fragment. Async."""
        # Ensure memory is loaded if it hasn't been
        if not self.memory: # Simple check, could be more robust
            await self.load_memory() # load_memory handles its own lock
        # No separate lock needed for read if self.memory is up-to-date
        return self.memory.get(fragment_id)

    async def delete_fragment(self, fragment_id: str) -> bool:
        """Deletes a fragment. Async."""
        if not self.memory:
            await self.load_memory() # load_memory handles its own lock
        # No separate lock needed for read if self.memory is up-to-date
        if fragment_id in self.memory:
            async with self._lock: # Lock for modifying self.memory then saving
                del self.memory[fragment_id]
                # save_memory will be called next, which handles its own lock for file write
        else: # Fragment not in memory
            return False
        return await self.save_memory()

    async def list_fragment_ids(self) -> List[str]:
        """Lists fragment IDs. Async."""
        if not self.memory:
            await self.load_memory()
        return list(self.memory.keys())


###########################################################################
# ------------------------------------------------------------------------
# 2)  Interaction SQLite store  – DatabaseManager
# ------------------------------------------------------------------------
###########################################################################
class DatabaseManager:
    """
    Async wrapper around SQLite for long-term interaction storage.
    Uses asyncio.Lock for safe concurrent access from async contexts.
    """

    # TODO comment updated
    # NOTE: Uses asyncio.Lock. Assumes usage within an async context.
    # Requires an async-compatible SQLite library (like aiosqlite) for true non-blocking DB ops.
    # Current implementation uses asyncio.to_thread for sync DB calls.

    def __init__(self, db_path: Optional[Path] = None, config: Optional[AppConfig] = None) -> None:
        # REMOVED threading.Lock parameter
        self.lock = asyncio.Lock()  # Use asyncio.Lock

        # Determine memory base path (similar logic as MemoryManager)
        if config:
            memory_base_path = config.paths.memory
        else:
            # FIXME: AppConfig.load() fallback is problematic. Config should be explicitly passed.
            # This can lead to issues in testing or when default config path is not appropriate.
            logger.warning("DatabaseManager initialized without explicit AppConfig. Attempting fallback load.")
            try:
                fallback_config = AppConfig.load()
                memory_base_path = fallback_config.paths.memory
            except Exception as e:
                logger.error(f"Failed to load fallback config for DatabaseManager path: {e}. Using default 'runtime/memory'.")
                memory_base_path = Path("runtime/memory")

        try:
            memory_base_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create memory base directory {memory_base_path}: {e}")

        self.db_path = db_path or (memory_base_path / "engagement_memory.db")

        # Initial connection can be sync, operations will be async
        try:
            # Ensure directory exists
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._init_schema()  # Initial schema setup can be sync
        except Exception as e:
            logger.critical(
                f"Failed to initialize DatabaseManager at {self.db_path}: {e}",
                exc_info=True,
            )
            raise

    def _init_schema(self) -> None:
        # This runs synchronously during __init__ before async loop starts
        # No need for async lock here if only called from __init__.
        # If called elsewhere, it would need `async def` and `async with self.lock`.
        c = self.conn.cursor()
        c.execute(
            """
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
           """
        )
        c.execute(
            """
           CREATE TABLE IF NOT EXISTS conversations_metadata (
               interaction_id TEXT PRIMARY KEY,
               initialized_at TEXT,
               metadata TEXT
           )
           """
        )
        self.conn.commit()

    # --- Write helpers (now async) ---
    async def record_interaction(self, row: Dict[str, Any]) -> None:
        def _sync_record():
            # This function runs in a separate thread via asyncio.to_thread
            conn = sqlite3.connect(
                self.db_path, check_same_thread=False
            )  # New conn per thread
            try:
                conn.execute(
                    """
                    INSERT INTO interactions (
                        platform, username, interaction_id, timestamp,
                        response, sentiment, success, chatgpt_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("platform"),
                        row.get("username"),
                        row.get("interaction_id"),
                        row.get("timestamp"),
                        row.get("response"),
                        row.get("sentiment"),
                        1 if row.get("success") else 0,
                        row.get("chatgpt_url"),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        async with self.lock:  # Use asyncio lock
            await asyncio.to_thread(
                _sync_record
            )  # Run sync DB operation in thread pool

    async def initialize_conversation(
        self, interaction_id: str, metadata: Dict[str, Any]
    ) -> None:
        def _sync_init():
            # This function runs in a separate thread via asyncio.to_thread
            conn = sqlite3.connect(self.conn, check_same_thread=False)
            try:
                ts = (
                    datetime.now(timezone.utc)
                    .isoformat(timespec="seconds")
                    .replace("+00:00", "Z")
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO conversations_metadata
                        (interaction_id, initialized_at, metadata)
                    VALUES (?, ?, ?)
                    """,
                    (interaction_id, ts, json.dumps(metadata)),
                )
                conn.commit()
            finally:
                conn.close()

        async with self.lock:  # Use asyncio lock
            await asyncio.to_thread(_sync_init)

    # --- Read helpers (now async) ---
    async def fetch_conversation(self, interaction_id: str) -> List[Dict[str, Any]]:
        def _sync_fetch():
            # This function runs in a separate thread via asyncio.to_thread
            conn = sqlite3.connect(self.conn, check_same_thread=False)
            try:
                cur = conn.cursor()
                cur.row_factory = sqlite3.Row  # Return rows as dict-like objects
                cur.execute(
                    """
                    SELECT * FROM interactions
                    WHERE interaction_id = ?
                    ORDER BY timestamp ASC
                    """,
                    (interaction_id,),
                )
                rows = cur.fetchall()
                # Convert sqlite3.Row objects to standard dicts
                return [dict(row) for row in rows]
            finally:
                conn.close()

        # Reading might not strictly need the lock depending on isolation level,
        # but using it ensures consistency if writes are happening.
        async with self.lock:  # Use asyncio lock
            return await asyncio.to_thread(_sync_fetch)

    async def close(self) -> None:
        # Close the initial connection if it exists
        # Active operations using asyncio.to_thread manage their own connections.
        if self.conn:
            self.conn.close()
            self.conn = None  # Indicate closed


###########################################################################
# ------------------------------------------------------------------------
# 3)  Unified memory facade  – UnifiedMemoryManager
# ------------------------------------------------------------------------
###########################################################################
class UnifiedMemoryManager:
    """
    • LRU + compressed JSON per segment (system / prompts / feedback / context / interactions)
    • SQLite long-term store
    • Jinja2 narrative helpers
    """  # noqa: E501

    # NOTE: This class coordinates segment managers and DatabaseManager.
    # DatabaseManager now uses asyncio.Lock and runs sync operations in threads.
    # Segment operations (_load_segments, _save_segment) are file I/O and
    # should also be run in threads or use aiofiles for async operation.
    # Internal lock `_internal_lock` should also be asyncio.Lock.

    SEGMENTS = ("system", "context", "prompts", "feedback", "interactions")

    def __init__(
        self,
        cache_size: int = 500,
        segment_dir: Optional[Path] = None,
        db_path: Optional[Path] = None,
        template_dir: Optional[Path] = None,
        compression_level: int = 6,
        config: Optional[AppConfig] = None,
    ) -> None:
        self.compression_level = compression_level
        self._internal_lock = asyncio.Lock()

        if config:
            memory_base_path = config.paths.memory
            # Ensure project_root is available for default_template_dir path construction
            project_root_for_templates = config.paths.project_root if hasattr(config.paths, 'project_root') else Path('.') # Fallback if not on paths
            default_template_dir = project_root_for_templates / "src/dreamos/memory/templates"
        else:
            # FIXME: AppConfig.load() fallback is problematic. Config should be explicitly passed.
            logger.warning("UnifiedMemoryManager initialized without explicit AppConfig. Attempting fallback load.")
            try:
                fallback_config = AppConfig.load()
                memory_base_path = fallback_config.paths.memory
                project_root_for_templates = fallback_config.paths.project_root if hasattr(fallback_config.paths, 'project_root') else Path('.')
                default_template_dir = project_root_for_templates / "src/dreamos/memory/templates"
            except Exception as e:
                logger.error(f"Failed to load fallback config for UnifiedMemoryManager paths: {e}. Using defaults.")
                memory_base_path = Path("runtime/memory")
                default_template_dir = Path("src/dreamos/memory/templates") # Potentially relative to CWD

        try:
            memory_base_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create memory base directory {memory_base_path}: {e}")

        self.segment_dir = segment_dir or (memory_base_path / "segments")
        # Ensure segment_dir exists (can be sync in __init__)
        try:
            self.segment_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create segment directory {self.segment_dir}: {e}")
            
        db_path_resolved = db_path or (memory_base_path / "engagement_memory.db")
        self.template_dir = template_dir or default_template_dir

        self.db = DatabaseManager(db_path=db_path_resolved, config=config)
        self._cache = {seg: LRUCache(maxsize=cache_size) for seg in self.SEGMENTS}
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        
        # NOTE: _load_segments() is async and should not be called directly from sync __init__.
        # Consider an async factory or an explicit async_init() method that awaits _load_segments().
        # For now, segments will be loaded lazily by operations like get/set if cache is empty,
        # or an explicit async_init() should be called by the user of this class.
        # self._load_segments() # REMOVED: Cannot await async method in sync __init__
        self._segments_loaded = False # Flag to indicate if initial load has occurred

    def _segment_file(self, seg_name: str) -> Path:
        """Helper to get the file path for a given memory segment."""
        return self.segment_dir / f"{seg_name}_memory.json.zlib"

    async def _ensure_segments_loaded(self):
        """Ensures segments are loaded if not already."""
        if not self._segments_loaded:
            await self._load_segments()
            self._segments_loaded = True

    async def _load_segments(self) -> None:
        # Needs to be async to use lock and async file ops
        async with self._internal_lock:
            for seg in self.SEGMENTS:
                # Load initial segment data
                try:
                    file_path = self._segment_file(seg)
                    if await asyncio.to_thread(file_path.exists):

                        def _sync_read():
                            return file_path.read_bytes()

                        compressed_data = await asyncio.to_thread(_sync_read)
                        data = json.loads(
                            zlib.decompress(compressed_data).decode("utf-8")
                        )
                        self._cache[seg].update(data)  # Populate cache
                    else:
                        # Initialize segment if file doesn't exist
                        await self._save_segment(seg)  # Save empty segment

                except Exception as e:
                    logger.error(
                        f"Failed to load memory segment '{seg}': {e}", exc_info=True
                    )

    async def _save_segment(self, seg: str) -> None:
        # Needs to be async to use lock and async file ops
        async with self._internal_lock:
            try:
                file_path = self._segment_file(seg)
                data_to_save = dict(self._cache[seg])  # Get current cache state
                encoded_data = json.dumps(data_to_save).encode("utf-8")
                compressed_data = zlib.compress(encoded_data, self.compression_level)

                # Atomic write using temp file
                temp_file_path = file_path.with_suffix(f".{os.getpid()}.tmp")

                def _sync_write():
                    with open(temp_file_path, "wb") as f:
                        f.write(compressed_data)
                    os.replace(temp_file_path, file_path)

                await asyncio.to_thread(_sync_write)
                logger.debug(f"Saved memory segment '{seg}'")
            except Exception as e:
                logger.error(
                    f"Failed to save memory segment '{seg}': {e}", exc_info=True
                )
                # Attempt cleanup
                if await asyncio.to_thread(temp_file_path.exists):
                    try:
                        await asyncio.to_thread(os.remove, temp_file_path)
                    except OSError:
                        pass

    # --- Core Key-Value Operations (now async) ---
    async def set(
        self, key: str, value: Any, seg: str = "system", source_agent_id: str = "System"
    ) -> None:
        if seg not in self.SEGMENTS:
            raise ValueError(f"Invalid segment: {seg}")
        
        await self._ensure_segments_loaded() # Ensure segments are loaded

        async with self._internal_lock:  # Lock for cache modification
            self._cache[seg][key] = value
            # Consider if save should happen immediately or be batched
            # Immediate save ensures persistence but can be slow.
            save_task = asyncio.create_task(self._save_segment(seg))
            # Optionally await save_task if synchronous persistence is needed

        # Publish memory update event (assuming AgentBus is available/injected)
        # self._publish_memory_event(EventType.MEMORY_UPDATE, ...)

    async def get(
        self, key: str, seg: str = "system", source_agent_id: str = "System"
    ) -> Optional[Any]:
        if seg not in self.SEGMENTS:
            raise ValueError(f"Invalid segment: {seg}")

        await self._ensure_segments_loaded() # Ensure segments are loaded

        # Cache check doesn't strictly need lock if LRUCache handles thread-safety
        # But locking ensures consistency if saves/loads modify cache structure.
        async with self._internal_lock:
            value = self._cache[seg].get(key)

        # Publish memory read event
        # self._publish_memory_event(EventType.MEMORY_READ, ...)
        return value

    async def delete(
        self, key: str, seg: str = "system", source_agent_id: str = "System"
    ) -> bool:
        if seg not in self.SEGMENTS:
            raise ValueError(f"Invalid segment: {seg}")

        await self._ensure_segments_loaded() # Ensure segments are loaded

        deleted = False
        async with self._internal_lock:
            if key in self._cache[seg]:
                del self._cache[seg][key]
                deleted = True
                # Schedule save after deletion
                save_task = asyncio.create_task(self._save_segment(seg))

        # Publish memory delete event
        # if deleted: self._publish_memory_event(EventType.MEMORY_DELETE, ...)
        return deleted

    # ... (other methods like clear_segment, get_stats need async lock if modifying cache) ...

    # --- DB Operations (Delegate to async DBManager methods) ---
    async def record_interaction(
        self,
        platform: str,
        username: str,
        response: str,
        sentiment: str,
        success: bool,
        interaction_id: Optional[str] = None,
        chatgpt_url: Optional[str] = None,
    ) -> None:
        ts = (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
        row = dict(
            platform=platform,
            username=username,
            interaction_id=interaction_id,
            timestamp=ts,
            response=response,
            sentiment=sentiment,
            success=success,
            chatgpt_url=chatgpt_url,
        )

        cache_key = f"{username}_{ts}"
        self.set(cache_key, row, "interactions")

        if interaction_id:
            conv_key = f"conversation_{interaction_id}"
            conv = self.get(conv_key, "interactions") or []
            conv.append(row)
            self.set(conv_key, conv, "interactions")

        await self.db.record_interaction(row)

    async def initialize_conversation(
        self, interaction_id: str, metadata: Dict[str, Any]
    ) -> None:
        await self.db.initialize_conversation(interaction_id, metadata)

    async def fetch_conversation(self, interaction_id: str) -> List[Dict[str, Any]]:
        return await self.db.fetch_conversation(interaction_id)

    async def export_conversation_finetune(
        self, interaction_id: str, out_path: Path
    ) -> bool:
        conv = await self.fetch_conversation(interaction_id)
        if not conv:
            return False

        try:
            # Ensure parent directory exists (async)
            target_dir = out_path.parent
            if not await asyncio.to_thread(target_dir.exists):
                await asyncio.to_thread(target_dir.mkdir, parents=True, exist_ok=True)
            
            # Synchronous file writing part
            def _sync_export():
                with out_path.open("w", encoding="utf-8") as fh:
                    for row in conv:
                        fh.write(
                            json.dumps(
                                {
                                    "messages": [
                                        {
                                            "role": "user",
                                            "content": f"Interaction on {row['timestamp']}",
                                        },
                                        {"role": "assistant", "content": row["response"]},
                                    ]
                                }
                            )
                            + "\n"
                        )
                return True # Indicate success of write operation

            return await asyncio.to_thread(_sync_export)
        except Exception as exc:
            logger.error("export %s failed (%s)", interaction_id, exc, exc_info=True)
            return False

    # ────────────────────────────────────────────────────────────────── #
    # Narrative helpers
    # ────────────────────────────────────────────────────────────────── #
    def render_narrative(self, template_name: str, context: Dict[str, Any]) -> str:
        try:
            tmpl = self.env.get_template(template_name)
            return tmpl.render(**context)
        except Exception as exc:
            logger.error(
                "render_narrative %s failed (%s)", template_name, exc, exc_info=True
            )
            return ""

    # ────────────────────────────────────────────────────────────────── #
    # Compaction methods
    # ────────────────────────────────────────────────────────────────── #
    # FIXME: These compaction methods are synchronous and perform file I/O.
    # If called from an async context where blocking is an issue,
    # they need to be refactored to be async and use asyncio.to_thread for file operations.
    def _rewrite_memory_safely(self, segment_id: str, data: Any):
        """Writes data to the segment file atomically using a temporary file."""
        segment_path = self._segment_file(segment_id)
        temp_file_path = ""
        try:
            # Create a temporary file in the same directory
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                delete=False,
                dir=os.path.dirname(segment_path),
                prefix=f"{segment_id}_compaction_",
            ) as temp_file:
                temp_file_path = temp_file.name
                json.dump(data, temp_file, indent=2)
                temp_file.flush()  # Ensure data is written to disk buffer
                os.fsync(temp_file.fileno())  # Ensure OS flushes buffer to disk

            # Atomically replace the original file with the temporary file
            os.replace(temp_file_path, segment_path)
            logger.info(
                f"Successfully compacted and rewrote memory segment '{segment_id}'."
            )

        except (IOError, OSError, json.JSONDecodeError) as e:
            logger.error(
                f"Error rewriting memory segment '{segment_id}': {e}", exc_info=True
            )
            # Clean up the temporary file if replacement failed
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError as rm_err:
                    logger.error(
                        f"Failed to remove temporary compaction file '{temp_file_path}': {rm_err}"  # noqa: E501
                    )
            raise  # Re-raise the exception after logging and cleanup attempt
        except Exception as e:  # Catch any other unexpected errors
            logger.error(
                f"Unexpected error during memory rewrite for segment '{segment_id}': {e}",  # noqa: E501
                exc_info=True,
            )
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError as rm_err:
                    logger.error(
                        f"Failed to remove temporary compaction file '{temp_file_path}' on unexpected error: {rm_err}"  # noqa: E501
                    )
            raise

    def _compact_segment(self, segment_id: str, data: Any):
        """Applies compaction policy to the data and rewrites the segment."""
        policy = self.compaction_config.get("default_policy", "keep_n")
        original_count = 0
        compacted_data = data

        if isinstance(data, list):
            original_count = len(data)
            if policy == "time_based":
                max_age = timedelta(
                    days=self.compaction_config.get("default_max_age_days", 30)
                )
                cutoff_time = datetime.now(timezone.utc) - max_age
                compacted_list = []
                timestamps_found = False
                for entry in data:
                    if isinstance(entry, dict) and "timestamp" in entry:
                        try:
                            ts_str = entry["timestamp"]
                            # Attempt to parse various ISO 8601 formats
                            entry_time = datetime.fromisoformat(
                                ts_str.replace("Z", "+00:00")
                            )
                            # Ensure timezone awareness for comparison
                            if entry_time.tzinfo is None:
                                entry_time = entry_time.replace(
                                    tzinfo=timezone.utc
                                )  # Assume UTC if naive
                            if entry_time >= cutoff_time:
                                compacted_list.append(entry)
                            timestamps_found = True
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Segment '{segment_id}': Could not parse timestamp '{entry.get('timestamp')}' in entry during time-based compaction. Entry kept."  # noqa: E501
                            )
                            compacted_list.append(entry)  # Keep if timestamp is bad
                    else:
                        # Keep entries without timestamps if policy is time_based (conservative)  # noqa: E501
                        compacted_list.append(entry)
                if not timestamps_found:
                    logger.warning(
                        f"Segment '{segment_id}': Time-based compaction policy applied, but no valid 'timestamp' fields found in list entries. Falling back to keep_n."  # noqa: E501
                    )
                    policy = "keep_n"  # Fallback if no timestamps
                else:
                    compacted_data = compacted_list

            if policy == "keep_n":  # Handles fallback or direct config
                keep_n = self.compaction_config.get("default_keep_n", 500)
                compacted_data = data[-keep_n:]

        elif isinstance(data, dict):
            original_count = len(data)
            if policy == "time_based":
                max_age = timedelta(
                    days=self.compaction_config.get("default_max_age_days", 30)
                )
                cutoff_time = datetime.now(timezone.utc) - max_age
                compacted_dict = {}
                timestamps_found = False
                for key, entry in data.items():
                    if isinstance(entry, dict) and "timestamp" in entry:
                        try:
                            ts_str = entry["timestamp"]
                            entry_time = datetime.fromisoformat(
                                ts_str.replace("Z", "+00:00")
                            )
                            if entry_time.tzinfo is None:
                                entry_time = entry_time.replace(tzinfo=timezone.utc)
                            if entry_time >= cutoff_time:
                                compacted_dict[key] = entry
                            timestamps_found = True
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Segment '{segment_id}': Could not parse timestamp '{entry.get('timestamp')}' in dict entry '{key}' during time-based compaction. Entry kept."  # noqa: E501
                            )
                            compacted_dict[key] = entry  # Keep if timestamp is bad
                    else:
                        # Keep entries without timestamps
                        compacted_dict[key] = entry
                if not timestamps_found:
                    logger.warning(
                        f"Segment '{segment_id}': Time-based compaction policy applied, but no valid 'timestamp' fields found in dict values. Falling back to keep_n."  # noqa: E501
                    )
                    policy = "keep_n"  # Fallback if no timestamps
                else:
                    compacted_data = compacted_dict

            if policy == "keep_n":
                logger.warning(
                    f"Segment '{segment_id}': Keep-N compaction policy is ambiguous for dictionaries. No compaction applied."  # noqa: E501
                )
                # Keep-N on dict is complex: sort keys? Keep random? For now, do nothing.  # noqa: E501
                compacted_data = data  # No change

        else:
            logger.warning(
                f"Segment '{segment_id}' compaction skipped: Data is not a list or dict."  # noqa: E501
            )
            return  # Cannot compact non-list/dict data with these policies

        compacted_count = (
            len(compacted_data)
            if isinstance(compacted_data, (list, dict))
            else original_count
        )
        if compacted_count < original_count:
            logger.info(
                f"Compacting segment '{segment_id}' ({policy} policy): Reduced from {original_count} to {compacted_count} entries."  # noqa: E501
            )
            self._rewrite_memory_safely(segment_id, compacted_data)
        else:
            logger.info(
                f"Segment '{segment_id}' checked for compaction, but no entries were removed based on policy '{policy}'."  # noqa: E501
            )

    def _check_and_compact(self, segment_id: str):
        """Checks if a segment exceeds thresholds and triggers compaction if needed."""
        if not self.compaction_config.get("enabled", False):
            return

        segment_path = self._segment_file(segment_id)
        if not os.path.exists(segment_path):
            return

        try:
            # Check size threshold
            size_mb = os.path.getsize(segment_path) / (1024 * 1024)
            size_threshold = self.compaction_config.get("threshold_max_size_mb", 1.0)
            triggered = size_mb > size_threshold

            # Check entry threshold if size threshold not met (avoid reading large file if already over size)  # noqa: E501
            data = None
            if not triggered:
                entry_threshold = self.compaction_config.get(
                    "threshold_max_entries", 1000
                )
                if entry_threshold > 0:  # Only check entries if threshold is set
                    with open(segment_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, (list, dict)):
                        entry_count = len(data)
                        if entry_count > entry_threshold:
                            triggered = True
                            logger.info(
                                f"Segment '{segment_id}' compaction triggered by entry count ({entry_count} > {entry_threshold})."  # noqa: E501
                            )
                    else:
                        # Cannot check entry count for non-list/dict types
                        pass

            if triggered:
                if size_mb > size_threshold:  # Log reason if size was the trigger
                    logger.info(
                        f"Segment '{segment_id}' compaction triggered by size ({size_mb:.2f} MB > {size_threshold:.2f} MB)."  # noqa: E501
                    )
                # Read data if not already read for entry check
                if data is None:
                    with open(segment_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                self._compact_segment(segment_id, data)

        except FileNotFoundError:
            logger.warning(
                f"Compaction check failed for segment '{segment_id}': File not found."
            )
        except json.JSONDecodeError:
            logger.error(
                f"Compaction check failed for segment '{segment_id}': Invalid JSON.",
                exc_info=True,
            )
        except Exception as e:
            logger.error(
                f"Error during compaction check for segment '{segment_id}': {e}",
                exc_info=True,
            )

    # ────────────────────────────────────────────────────────────────── #
    # Cleanup
    # ────────────────────────────────────────────────────────────────── #
    async def close(self) -> None:
        """Closes the DB connection and potentially saves segments."""
        # Ensure segments are saved before closing DB
        save_tasks = [self._save_segment(seg) for seg in self.SEGMENTS]
        await asyncio.gather(*save_tasks)
        await self.db.close()

    # Helper to publish memory events (needs AgentBus instance)
    # async def _publish_memory_event(self, event_type: EventType, key: str, seg: str, ...)
