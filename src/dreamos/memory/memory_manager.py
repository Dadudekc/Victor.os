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
from __future__ import annotations

import json
import logging
import os
import sqlite3
import tempfile
import threading
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cachetools import LRUCache
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field, validator

from dreamos.coordination.agent_bus import AgentBus
from dreamos.core.coordination.agent_bus import MemoryEvent
from dreamos.core.coordination.event_payloads import MemoryEventData
from dreamos.core.coordination.event_types import EventType

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

# Load config to get paths
_config = AppConfig.load()
_memory_base_path = _config.paths.memory
_memory_base_path.mkdir(parents=True, exist_ok=True)  # Ensure path exists

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
    Good for small, human-inspectable fragments.
    """

    def __init__(self, file_path: Path | None = None) -> None:
        # Use path from config by default
        self.file_path: Path = file_path or (_memory_base_path / "core_fragments.json")
        self.memory: Dict[str, Dict[str, Any]] = {}
        self._ensure_store()
        self.load_memory()

    # ────────────────────────────────────────────────────────────────── #
    # Internals
    # ────────────────────────────────────────────────────────────────── #
    def _ensure_store(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text("{}")
            logger.info("Created fragment store → %s", self.file_path)

    # ────────────────────────────────────────────────────────────────── #
    # Public API
    # ────────────────────────────────────────────────────────────────── #
    def load_memory(self) -> bool:
        """Load fragments from JSON file; ensure stored memory is a dict."""
        # Reset memory first
        self.memory = {}
        try:
            raw = self.file_path.read_text()
            parsed = json.loads(raw) if raw.strip() else {}
            if not isinstance(parsed, dict):
                raise ValueError("fragment JSON must be an object")
            # Valid memory loaded
            self.memory = parsed
            logger.info("Loaded %d fragments", len(self.memory))
            return True
        except Exception as exc:
            logger.error("Fragment load failed – resetting (%s)", exc, exc_info=True)
            return False

    def save_memory(self) -> bool:
        try:
            self.file_path.write_text(json.dumps(self.memory, indent=2))
            logger.info("Saved %d fragments", len(self.memory))
            return True
        except Exception as exc:
            logger.error("Fragment save failed (%s)", exc, exc_info=True)
            return False

    # CRUD helpers
    def save_fragment(self, fragment_id: str, data: Dict[str, Any]) -> bool:
        if not fragment_id or not isinstance(data, dict):
            logger.error("save_fragment: invalid id or data")
            return False
        self.memory[fragment_id] = data
        return self.save_memory()

    def load_fragment(self, fragment_id: str) -> Optional[Dict[str, Any]]:
        return self.memory.get(fragment_id)

    def delete_fragment(self, fragment_id: str) -> bool:
        if fragment_id in self.memory:
            del self.memory[fragment_id]
            return self.save_memory()
        return False

    def list_fragment_ids(self) -> List[str]:
        return list(self.memory.keys())


###########################################################################
# ------------------------------------------------------------------------
# 2)  Interaction SQLite store  – DatabaseManager
# ------------------------------------------------------------------------
###########################################################################
class DatabaseManager:
    """
    Thread-safe wrapper around SQLite for long-term interaction storage.
    """

    # TODO: Uses threading.Lock. Consider converting to async/await with
    # an async-compatible SQLite library (like aiosqlite) if used heavily
    # in async contexts to avoid blocking the event loop.
    def __init__(
        self, db_path: Path | None = None, lock: threading.Lock | None = None
    ) -> None:
        self.lock = lock or threading.Lock()
        # Use path from config by default
        self.db_path = db_path or (_memory_base_path / "engagement_memory.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        with self.lock:
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

    # ────────────────────────────────────────────────────────────────── #
    # Write helpers
    # ────────────────────────────────────────────────────────────────── #
    def record_interaction(self, row: Dict[str, Any]) -> None:
        with self.lock:
            self.conn.execute(
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
            self.conn.commit()

    def initialize_conversation(
        self, interaction_id: str, metadata: Dict[str, Any]
    ) -> None:
        with self.lock:
            ts = (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )
            self.conn.execute(
                """
                INSERT OR IGNORE INTO conversations_metadata
                    (interaction_id, initialized_at, metadata)
                VALUES (?, ?, ?)
                """,
                (interaction_id, ts, json.dumps(metadata)),
            )
            self.conn.commit()

    # ────────────────────────────────────────────────────────────────── #
    # Read helpers
    # ────────────────────────────────────────────────────────────────── #
    def fetch_conversation(self, interaction_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT platform, username, interaction_id, timestamp, response,
                   sentiment, success, chatgpt_url
            FROM interactions
            WHERE interaction_id = ?
            ORDER BY timestamp ASC
            """,
            (interaction_id,),
        )
        columns = [d[0] for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def close(self) -> None:
        self.conn.close()


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
    """

    # TODO: This class uses threading.Lock internally and manages DatabaseManager
    # which also uses threading.Lock. This makes the UnifiedMemoryManager synchronous
    # and potentially blocking in async contexts. Consider a full async refactor
    # using asyncio.Lock and async file/DB operations if performance is critical.

    SEGMENTS = ("system", "context", "prompts", "feedback", "interactions")

    def __init__(
        self,
        cache_size: int = 500,
        segment_dir: Path | None = None,
        db_path: Path | None = None,
        template_dir: Path | None = None,
        compression_level: int = 6,
    ) -> None:
        """Initialize memory manager.

        Args:
            cache_size: Max items per segment cache.
            segment_dir: Path to store JSON segments (defaults to config memory path).
            db_path: Path to SQLite DB (defaults to config memory path + db name).
            template_dir: Path to Jinja2 templates (defaults to config path + templates).
            compression_level: Zlib compression level (0-9).
        """
        self.lock = threading.Lock()
        self.compression_level = compression_level
        self._config = AppConfig.load()  # Load config for paths

        # Use config paths by default
        self.segment_dir = segment_dir or self._config.paths.memory
        self.db_path = db_path or (self.segment_dir / "engagement_memory.db")
        self.template_dir = template_dir or (
            self.segment_dir / "templates"
        )  # Example default

        self.segment_dir.mkdir(parents=True, exist_ok=True)
        self.template_dir.mkdir(
            parents=True, exist_ok=True
        )  # Ensure template dir exists

        self.cache: Dict[str, LRUCache] = {
            seg: LRUCache(maxsize=cache_size) for seg in self.SEGMENTS
        }
        self.db = DatabaseManager(db_path=self.db_path, lock=self.lock)

        # Jinja2 env
        tmpl_root = self.template_dir
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(tmpl_root)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        self.agent_bus = AgentBus()  # Get singleton instance

        # Compaction config
        self.compaction_config = DEFAULT_COMPACTION_CONFIG

    # ────────────────────────────────────────────────────────────────── #
    # Segment helpers
    # ────────────────────────────────────────────────────────────────── #
    def _segment_file(self, seg: str) -> Path:
        return self.segment_dir / f"{seg}_memory.json"

    def _load_segments(self) -> None:
        for seg in self.SEGMENTS:
            f = self._segment_file(seg)
            if not f.exists():
                continue
            try:
                raw = json.loads(f.read_text())
                for k, v in raw.items():
                    comp = zlib.compress(json.dumps(v).encode("utf-8"))
                    self.segments[seg][k] = comp
            except Exception as exc:
                logger.error("Segment %s corrupt (%s) – skipped", f, exc, exc_info=True)

    def _save_segment(self, seg: str) -> None:
        payload: Dict[str, Any] = {}
        for k, comp in self.segments[seg].items():
            try:
                raw = zlib.decompress(comp)
                payload[k] = json.loads(raw.decode("utf-8"))
            except Exception as exc:
                logger.error(f"_save_segment {seg}:{k} failed ({exc})", exc_info=True)
                # skip corrupt entry
        # Write remaining valid entries atomically
        seg_file = self._segment_file(seg)
        tmp_file = seg_file.with_suffix(seg_file.suffix + ".tmp")
        try:
            with tmp_file.open("w", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, indent=2))
            os.replace(str(tmp_file), str(seg_file))
        except Exception as exc:
            logger.error(f"_save_segment write {seg} failed ({exc})", exc_info=True)

    # ────────────────────────────────────────────────────────────────── #
    # Cache interface
    # ────────────────────────────────────────────────────────────────── #
    def set(
        self, key: str, value: Any, seg: str = "system", source_agent_id: str = "System"
    ) -> None:
        """Store data, triggering MEMORY_UPDATE event."""
        comp = zlib.compress(json.dumps(value).encode("utf-8"))
        with self.lock:
            self.cache[f"{seg}:{key}"] = comp
            self.segments[seg][key] = comp
            self._save_segment(seg)
            logger.debug(f"Memory set → {seg}/{key}")

        # Dispatch event
        event_data = MemoryEventData(
            agent_id=source_agent_id, segment_id=seg, content={key: value}, success=True
        )
        self.agent_bus.dispatch_event(
            MemoryEvent(
                event_type=EventType.MEMORY_UPDATE,
                source_id=source_agent_id,
                data=event_data,
            )
        )

        # {{START: Trigger Compaction Check}}
        if self.compaction_config.get("check_on_write", False):
            try:
                self._check_and_compact(seg)
            except Exception as e:
                # Log error but don't let compaction failure break the main operation
                logger.error(
                    f"Compaction check failed after writing to segment '{seg}': {e}",
                    exc_info=True,
                )
        # {{END: Trigger Compaction Check}}

    def get(
        self, key: str, seg: str = "system", source_agent_id: str = "System"
    ) -> Optional[Any]:
        """Retrieve data, triggering MEMORY_READ event."""
        value = None
        status = "FAILURE"
        message = f"Key '{key}' not found in segment '{seg}'"
        try:
            if seg not in self.segments:
                self._load_segments()

            if key in self.segments[seg]:
                value = json.loads(
                    zlib.decompress(self.segments[seg][key]).decode("utf-8")
                )
                logger.debug(f"Memory get ← {seg}/{key}")
                status = "SUCCESS"
                message = None  # Clear message on success
            else:
                logger.debug(f"Memory get miss ← {seg}/{key}")
                # Keep status as FAILURE and the message

        except Exception as e:
            logger.error(f"Error during get for {seg}/{key}: {e}", exc_info=True)
            status = "FAILURE"
            message = str(e)
            value = None  # Ensure value is None on error
        finally:
            # Dispatch event regardless of success/failure
            event_data = MemoryEventData(
                agent_id=source_agent_id,
                segment_id=seg,
                query=key,
                content=value,
                success=True,
            )
            self.agent_bus.dispatch_event(
                MemoryEvent(
                    event_type=EventType.MEMORY_READ,
                    source_id=source_agent_id,
                    data=event_data,
                )
            )

        return value

    def delete(
        self, key: str, seg: str = "system", source_agent_id: str = "System"
    ) -> bool:
        """Delete data, triggering MEMORY_DELETE event."""
        deleted = False
        status = "FAILURE"
        message = f"Key '{key}' not found for deletion in segment '{seg}'"
        try:
            if seg not in self.segments:
                self._load_segments()

            if key in self.segments[seg]:
                del self.segments[seg][key]
                self._save_segment(seg)
                logger.debug(f"Memory delete 🗑️ {seg}/{key}")
                deleted = True
                status = "SUCCESS"
                message = None  # Clear message on success
            else:
                logger.debug(f"Memory delete miss ← {seg}/{key}")
                # Keep status FAILURE and message

        except Exception as e:
            logger.error(f"Error during delete for {seg}/{key}: {e}", exc_info=True)
            status = "FAILURE"
            message = str(e)
            deleted = False  # Ensure flag is False on error
        finally:
            # Dispatch event
            event_data = MemoryEventData(
                agent_id=source_agent_id,
                segment_id=seg,
                content={key: None},
                success=True,
            )
            # Only dispatch if something was potentially acted upon or error occurred
            # Alternatively, always dispatch? Let's always dispatch for observability.
            self.agent_bus.dispatch_event(
                MemoryEvent(
                    event_type=EventType.MEMORY_DELETE,
                    source_id=source_agent_id,
                    data=event_data,
                )
            )

        return deleted

    def clear_segment(self, seg: str) -> None:
        with self.lock:
            self.segments[seg].clear()
            for k in [k for k in self.cache.keys() if k.startswith(f"{seg}:")]:
                del self.cache[k]
            self._save_segment(seg)

    # ────────────────────────────────────────────────────────────────── #
    # Stats / housekeeping
    # ────────────────────────────────────────────────────────────────── #
    def get_stats(self) -> Dict[str, Any]:
        return {
            "cache": {"items": len(self.cache), "max": self.cache.maxsize},
            "segments": {
                s: {"items": len(d), "bytes": sum(len(c) for c in d.values())}
                for s, d in self.segments.items()
            },
        }

    def optimize(self) -> None:
        with self.lock:
            self.cache.clear()
            for seg, data in self.segments.items():
                for k, comp in list(data.items()):
                    try:
                        raw = zlib.decompress(comp)
                        data[k] = zlib.compress(raw, level=9)
                    except Exception as exc:
                        logger.error(
                            f"optimize {seg}:{k} failed ({exc})", exc_info=True
                        )
                try:
                    self._save_segment(seg)
                except Exception as exc:
                    logger.error(
                        f"optimize save segment {seg} failed ({exc})", exc_info=True
                    )
            logger.info("Memory optimize complete – stats: %s", self.get_stats())

    # ────────────────────────────────────────────────────────────────── #
    # Interaction helpers
    # ────────────────────────────────────────────────────────────────── #
    def record_interaction(
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

        self.db.record_interaction(row)

        # {{START: Trigger Compaction Check}}
        if self.compaction_config.get("check_on_write", False):
            try:
                self._check_and_compact(conv_key)
            except Exception as e:
                logger.error(
                    f"Compaction check failed after recording interaction to segment '{conv_key}': {e}",
                    exc_info=True,
                )
        # {{END: Trigger Compaction Check}}

    def initialize_conversation(
        self, interaction_id: str, metadata: Dict[str, Any]
    ) -> None:
        self.db.initialize_conversation(interaction_id, metadata)

    def fetch_conversation(self, interaction_id: str) -> List[Dict[str, Any]]:
        return self.db.fetch_conversation(interaction_id)

    def export_conversation_finetune(self, interaction_id: str, out_path: Path) -> bool:
        conv = self.fetch_conversation(interaction_id)
        if not conv:
            return False

        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
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
            return True
        except Exception as exc:
            logger.error("export %s failed (%s)", interaction_id, exc, exc_info=True)
            return False

    # ────────────────────────────────────────────────────────────────── #
    # Narrative helpers
    # ────────────────────────────────────────────────────────────────── #
    def render_narrative(self, template_name: str, context: Dict[str, Any]) -> str:
        try:
            tmpl = self.jinja_env.get_template(template_name)
            return tmpl.render(**context)
        except Exception as exc:
            logger.error(
                "render_narrative %s failed (%s)", template_name, exc, exc_info=True
            )
            return ""

    # ────────────────────────────────────────────────────────────────── #
    # Compaction methods
    # ────────────────────────────────────────────────────────────────── #
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
                        f"Failed to remove temporary compaction file '{temp_file_path}': {rm_err}"
                    )
            raise  # Re-raise the exception after logging and cleanup attempt
        except Exception as e:  # Catch any other unexpected errors
            logger.error(
                f"Unexpected error during memory rewrite for segment '{segment_id}': {e}",
                exc_info=True,
            )
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError as rm_err:
                    logger.error(
                        f"Failed to remove temporary compaction file '{temp_file_path}' on unexpected error: {rm_err}"
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
                                f"Segment '{segment_id}': Could not parse timestamp '{entry.get('timestamp')}' in entry during time-based compaction. Entry kept."
                            )
                            compacted_list.append(entry)  # Keep if timestamp is bad
                    else:
                        # Keep entries without timestamps if policy is time_based (conservative)
                        compacted_list.append(entry)
                if not timestamps_found:
                    logger.warning(
                        f"Segment '{segment_id}': Time-based compaction policy applied, but no valid 'timestamp' fields found in list entries. Falling back to keep_n."
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
                                f"Segment '{segment_id}': Could not parse timestamp '{entry.get('timestamp')}' in dict entry '{key}' during time-based compaction. Entry kept."
                            )
                            compacted_dict[key] = entry  # Keep if timestamp is bad
                    else:
                        # Keep entries without timestamps
                        compacted_dict[key] = entry
                if not timestamps_found:
                    logger.warning(
                        f"Segment '{segment_id}': Time-based compaction policy applied, but no valid 'timestamp' fields found in dict values. Falling back to keep_n."
                    )
                    policy = "keep_n"  # Fallback if no timestamps
                else:
                    compacted_data = compacted_dict

            if policy == "keep_n":
                logger.warning(
                    f"Segment '{segment_id}': Keep-N compaction policy is ambiguous for dictionaries. No compaction applied."
                )
                # Keep-N on dict is complex: sort keys? Keep random? For now, do nothing.
                compacted_data = data  # No change

        else:
            logger.warning(
                f"Segment '{segment_id}' compaction skipped: Data is not a list or dict."
            )
            return  # Cannot compact non-list/dict data with these policies

        compacted_count = (
            len(compacted_data)
            if isinstance(compacted_data, (list, dict))
            else original_count
        )
        if compacted_count < original_count:
            logger.info(
                f"Compacting segment '{segment_id}' ({policy} policy): Reduced from {original_count} to {compacted_count} entries."
            )
            self._rewrite_memory_safely(segment_id, compacted_data)
        else:
            logger.info(
                f"Segment '{segment_id}' checked for compaction, but no entries were removed based on policy '{policy}'."
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

            # Check entry threshold if size threshold not met (avoid reading large file if already over size)
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
                                f"Segment '{segment_id}' compaction triggered by entry count ({entry_count} > {entry_threshold})."
                            )
                    else:
                        # Cannot check entry count for non-list/dict types
                        pass

            if triggered:
                if size_mb > size_threshold:  # Log reason if size was the trigger
                    logger.info(
                        f"Segment '{segment_id}' compaction triggered by size ({size_mb:.2f} MB > {size_threshold:.2f} MB)."
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
    def close(self) -> None:
        self.db.close()
