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
import threading
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cachetools import LRUCache
from jinja2 import Environment, FileSystemLoader

###########################################################################
# Logging
###########################################################################
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

###########################################################################
# Base paths (project-relative, no hard-coding)
###########################################################################
PROJECT_ROOT = Path.cwd()
RUNTIME_DIR  = PROJECT_ROOT / "runtime"
MEMORY_DIR   = RUNTIME_DIR / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

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
        self.file_path: Path = file_path or MEMORY_DIR / "core_fragments.json"
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

    def __init__(self, db_path: Path | None = None, lock: threading.Lock | None = None) -> None:
        self.lock      = lock or threading.Lock()
        self.db_path   = db_path or MEMORY_DIR / "engagement_memory.db"
        self.conn      = sqlite3.connect(self.db_path, check_same_thread=False)
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

    def initialize_conversation(self, interaction_id: str, metadata: Dict[str, Any]) -> None:
        with self.lock:
            ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
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

    SEGMENTS = ("system", "context", "prompts", "feedback", "interactions")

    def __init__(
        self,
        cache_size: int = 500,
        segment_dir: Path | None = None,
        db_path: Path | None = None,
        template_dir: Path | None = None,
    ) -> None:
        self.lock        = threading.Lock()
        self.cache       = LRUCache(maxsize=cache_size)
        self.segment_dir = segment_dir or MEMORY_DIR
        self.segment_dir.mkdir(parents=True, exist_ok=True)
        self.segments: Dict[str, Dict[str, bytes]] = {s: {} for s in self.SEGMENTS}

        # load existing segment files
        self._load_segments()

        # DB
        self.db = DatabaseManager(db_path or MEMORY_DIR / "engagement_memory.db", self.lock)

        # Jinja2 env
        tmpl_root      = template_dir or PROJECT_ROOT / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(str(tmpl_root)),
                                     trim_blocks=True, lstrip_blocks=True)

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
    def set(self, key: str, value: Any, seg: str = "system") -> None:
        comp = zlib.compress(json.dumps(value).encode("utf-8"))
        with self.lock:
            self.cache[f"{seg}:{key}"] = comp
            self.segments[seg][key] = comp
            self._save_segment(seg)

    def get(self, key: str, seg: str = "system") -> Optional[Any]:
        cache_key = f"{seg}:{key}"
        try:
            if cache_key in self.cache:
                comp = self.cache[cache_key]
            else:
                comp = self.segments[seg].get(key)
                if comp:
                    self.cache[cache_key] = comp
            if comp is None:
                return None
            return json.loads(zlib.decompress(comp).decode("utf-8"))
        except Exception as exc:
            logger.error("get %s:%s failed (%s)", seg, key, exc, exc_info=True)
            return None

    def delete(self, key: str, seg: str = "system") -> bool:
        with self.lock:
            cache_key = f"{seg}:{key}"
            self.cache.pop(cache_key, None)
            existed = self.segments[seg].pop(key, None) is not None
            if existed:
                self._save_segment(seg)
            return existed

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
                        logger.error(f"optimize {seg}:{k} failed ({exc})", exc_info=True)
                try:
                    self._save_segment(seg)
                except Exception as exc:
                    logger.error(f"optimize save segment {seg} failed ({exc})", exc_info=True)
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
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
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

    def initialize_conversation(self, interaction_id: str, metadata: Dict[str, Any]) -> None:
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
                                    {"role": "user", "content": f"Interaction on {row['timestamp']}"},
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
            logger.error("render_narrative %s failed (%s)", template_name, exc, exc_info=True)
            return ""

    # ────────────────────────────────────────────────────────────────── #
    # Cleanup
    # ────────────────────────────────────────────────────────────────── #
    def close(self) -> None:
        self.db.close()
