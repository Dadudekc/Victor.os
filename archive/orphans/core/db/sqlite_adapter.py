"""
SQLite adapter for Dream.OS persistence layers.

Replaces JSON file operations for Tasks, Agent Registry, Capabilities, etc.
"""

import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Assuming Pydantic models are defined elsewhere
# from dreamos.core.agents.capabilities.schema import AgentCapability
# from dreamos.core.tasks.models import Task

logger = logging.getLogger(__name__)

# Define placeholder types for models if not imported yet
AgentCapability = Dict[str, Any]
Task = Dict[str, Any]


class SQLiteAdapter:
    """Provides an interface to interact with the SQLite database for Dream.OS data."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.lock = (
            threading.RLock()
        )  # For thread safety on connection/cursor usage if needed
        self.connection: Optional[sqlite3.Connection] = None
        logger.info(f"Initializing SQLiteAdapter for database: {self.db_path}")
        self._connect()
        self._create_schema()

    def _connect(self):
        """Establishes a connection to the SQLite database."""
        with self.lock:
            try:
                # Ensure directory exists
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                self.connection = sqlite3.connect(
                    self.db_path, check_same_thread=False
                )  # Allow multithreaded access
                self.connection.row_factory = sqlite3.Row  # Access columns by name
                logger.info(
                    f"Successfully connected to SQLite database: {self.db_path}"
                )
            except sqlite3.Error as e:
                logger.critical(
                    f"Failed to connect to SQLite database {self.db_path}: {e}",
                    exc_info=True,
                )
                self.connection = None
                # Potentially raise an exception to halt initialization if connection fails
                raise ConnectionError(f"Failed to connect to SQLite DB: {e}") from e

    def _create_schema(self):
        """Creates the necessary tables and indexes if they don't exist."""
        if not self.connection:
            logger.error("Cannot create schema, no database connection.")
            return

        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.executescript("""
                    -- Table for Agent Heartbeats (Registry)
                    CREATE TABLE IF NOT EXISTS agent_heartbeats (
                        agent_id TEXT PRIMARY KEY NOT NULL,
                        last_heartbeat REAL NOT NULL
                    );

                    -- Table for Agent Capabilities
                    CREATE TABLE IF NOT EXISTS agent_capabilities (
                        agent_id TEXT NOT NULL,
                        capability_id TEXT NOT NULL,
                        capability_name TEXT NOT NULL,
                        description TEXT,
                        parameters_json TEXT,
                        input_schema_json TEXT,
                        output_schema_json TEXT,
                        registered_at TEXT NOT NULL,
                        PRIMARY KEY (agent_id, capability_id)
                    );

                    -- Unified Table for Tasks
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY NOT NULL,
                        description TEXT NOT NULL,
                        priority INTEGER NOT NULL DEFAULT 5,
                        status TEXT NOT NULL CHECK(status IN ('pending', 'claimed', 'in_progress', 'completed', 'failed', 'archived')) DEFAULT 'pending',
                        agent_id TEXT,
                        tags_json TEXT,
                        dependencies_json TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT,
                        completed_at TEXT,
                        result_summary TEXT,
                        payload_json TEXT
                    );

                    -- Table for Task Status History (Incorporating Feedback)
                    CREATE TABLE IF NOT EXISTS task_status_history (
                        task_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        changed_at TEXT NOT NULL, -- ISO timestamp
                        PRIMARY KEY (task_id, status, changed_at)
                    );

                    -- Table for Normalized Task Tags (Incorporating Feedback)
                    CREATE TABLE IF NOT EXISTS task_tags (
                        task_id TEXT NOT NULL,
                        tag TEXT NOT NULL,
                        PRIMARY KEY (task_id, tag)
                    );

                    -- Optional Indexes
                    CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                    CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
                    CREATE INDEX IF NOT EXISTS idx_tasks_agent_id ON tasks(agent_id);
                    CREATE INDEX IF NOT EXISTS idx_capabilities_agent_id ON agent_capabilities(agent_id);
                    CREATE INDEX IF NOT EXISTS idx_task_tags_tag ON task_tags(tag);
                    CREATE INDEX IF NOT EXISTS idx_task_status_history_task_id ON task_status_history(task_id);
                """)
                self.connection.commit()
                logger.info("Database schema created/verified successfully.")
            except sqlite3.Error as e:
                logger.error(
                    f"Failed to create/verify database schema: {e}", exc_info=True
                )
                # Consider rolling back or handling schema errors
            finally:
                if cursor:
                    cursor.close()

    def close(self):
        """Closes the database connection."""
        with self.lock:
            if self.connection:
                self.connection.close()
                self.connection = None
                logger.info(f"Closed SQLite database connection: {self.db_path}")

    # --- Agent Registry Methods (Heartbeats) ---
    def get_all_agents(self) -> Dict[str, float]:
        """Retrieves all agent IDs and their last heartbeat timestamp."""
        agents = {}
        if not self.connection:
            logger.error("Cannot get agents, no database connection.")
            return agents

        sql = "SELECT agent_id, last_heartbeat FROM agent_heartbeats;"
        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.execute(sql)
                rows = cursor.fetchall()
                for row in rows:
                    agents[row["agent_id"]] = row["last_heartbeat"]
                logger.debug(f"Retrieved {len(agents)} agent heartbeats.")
            except sqlite3.Error as e:
                logger.error(f"Failed to get all agents: {e}", exc_info=True)
            finally:
                if cursor:
                    cursor.close()
        return agents

    def update_agent_heartbeat(self, agent_id: str, timestamp: float):
        """Inserts or updates an agent's heartbeat timestamp."""
        if not self.connection:
            logger.error("Cannot update heartbeat, no database connection.")
            return

        sql = """
        INSERT INTO agent_heartbeats (agent_id, last_heartbeat)
        VALUES (?, ?)
        ON CONFLICT(agent_id) DO UPDATE SET last_heartbeat = excluded.last_heartbeat;
        """
        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.execute(sql, (agent_id, timestamp))
                self.connection.commit()
                logger.debug(f"Updated heartbeat for agent {agent_id}")
            except sqlite3.Error as e:
                logger.error(
                    f"Failed to update heartbeat for {agent_id}: {e}", exc_info=True
                )
                # Optionally rollback if needed, though commit happens automatically or on error
            finally:
                if cursor:
                    cursor.close()

    def get_stale_agents(self, ttl: int) -> List[str]:
        """Finds agents whose last heartbeat is older than the TTL."""
        stale_agents = []
        if not self.connection:
            logger.error("Cannot get stale agents, no database connection.")
            return stale_agents

        stale_threshold = time.time() - ttl
        sql = "SELECT agent_id FROM agent_heartbeats WHERE last_heartbeat < ?;"
        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.execute(sql, (stale_threshold,))
                rows = cursor.fetchall()
                stale_agents = [row["agent_id"] for row in rows]
                if stale_agents:
                    logger.debug(
                        f"Found {len(stale_agents)} stale agents (TTL: {ttl}s)."
                    )
            except sqlite3.Error as e:
                logger.error(f"Failed to get stale agents: {e}", exc_info=True)
            finally:
                if cursor:
                    cursor.close()
        return stale_agents

    # --- Capability Registry Methods ---
    def register_capability(self, agent_id: str, capability: AgentCapability):
        """Registers a new capability or updates an existing one for an agent."""
        if not self.connection:
            logger.error("Cannot register capability, no database connection.")
            return

        # Prepare data for insertion, serializing complex fields
        cap_id = capability.get("capability_id")
        if not cap_id:
            logger.error(
                f"Cannot register capability for {agent_id} without a capability_id."
            )
            return

        sql = """
        INSERT INTO agent_capabilities (
            agent_id, capability_id, capability_name, description,
            parameters_json, input_schema_json, output_schema_json, registered_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(agent_id, capability_id) DO UPDATE SET
            capability_name = excluded.capability_name,
            description = excluded.description,
            parameters_json = excluded.parameters_json,
            input_schema_json = excluded.input_schema_json,
            output_schema_json = excluded.output_schema_json,
            registered_at = excluded.registered_at;
        """
        params = (
            agent_id,
            cap_id,
            capability.get("capability_name", "Unknown Capability"),
            capability.get("description"),
            json.dumps(capability.get("parameters"))
            if capability.get("parameters")
            else None,
            json.dumps(capability.get("input_schema"))
            if capability.get("input_schema")
            else None,
            json.dumps(capability.get("output_schema"))
            if capability.get("output_schema")
            else None,
            capability.get("registered_at"),  # Assuming this is already ISO 8601 string
        )

        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.execute(sql, params)
                self.connection.commit()
                logger.debug(
                    f"Registered/Updated capability {cap_id} for agent {agent_id}"
                )
            except sqlite3.Error as e:
                logger.error(
                    f"Failed to register capability {cap_id} for {agent_id}: {e}",
                    exc_info=True,
                )
            finally:
                if cursor:
                    cursor.close()

    def unregister_capability(self, agent_id: str, capability_id: str):
        """Removes a specific capability registration for an agent."""
        if not self.connection:
            logger.error("Cannot unregister capability, no database connection.")
            return

        sql = "DELETE FROM agent_capabilities WHERE agent_id = ? AND capability_id = ?;"
        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.execute(sql, (agent_id, capability_id))
                self.connection.commit()
                if cursor.rowcount > 0:
                    logger.debug(
                        f"Unregistered capability {capability_id} for agent {agent_id}"
                    )
                else:
                    logger.warning(
                        f"No capability found with id {capability_id} for agent {agent_id} to unregister."
                    )
            except sqlite3.Error as e:
                logger.error(
                    f"Failed to unregister capability {capability_id} for {agent_id}: {e}",
                    exc_info=True,
                )
            finally:
                if cursor:
                    cursor.close()

    def get_capabilities_for_agent(self, agent_id: str) -> Dict[str, AgentCapability]:
        """Retrieves all capabilities registered for a specific agent."""
        capabilities = {}
        if not self.connection:
            logger.error("Cannot get capabilities, no database connection.")
            return capabilities

        sql = "SELECT * FROM agent_capabilities WHERE agent_id = ?;"
        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.execute(sql, (agent_id,))
                rows = cursor.fetchall()
                for row in rows:
                    cap_id = row["capability_id"]
                    try:
                        capability_data = {
                            "agent_id": row["agent_id"],
                            "capability_id": cap_id,
                            "capability_name": row["capability_name"],
                            "description": row["description"],
                            "parameters": json.loads(row["parameters_json"])
                            if row["parameters_json"]
                            else None,
                            "input_schema": json.loads(row["input_schema_json"])
                            if row["input_schema_json"]
                            else None,
                            "output_schema": json.loads(row["output_schema_json"])
                            if row["output_schema_json"]
                            else None,
                            "registered_at": row["registered_at"],
                        }
                        # TODO: Validate with Pydantic model if available
                        # capabilities[cap_id] = AgentCapability.model_validate(capability_data)
                        capabilities[cap_id] = capability_data  # Use dict for now
                    except json.JSONDecodeError as e:
                        logger.error(
                            f"Failed to decode JSON for capability {cap_id} for agent {agent_id}: {e}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed process capability row {cap_id} for agent {agent_id}: {e}"
                        )

                logger.debug(
                    f"Retrieved {len(capabilities)} capabilities for agent {agent_id}"
                )
            except sqlite3.Error as e:
                logger.error(
                    f"Failed to get capabilities for {agent_id}: {e}", exc_info=True
                )
            finally:
                if cursor:
                    cursor.close()
        return capabilities

    def get_all_capabilities(self) -> Dict[str, Dict[str, AgentCapability]]:
        """Retrieves all capabilities for all agents."""
        all_capabilities: Dict[str, Dict[str, AgentCapability]] = {}
        if not self.connection:
            logger.error("Cannot get all capabilities, no database connection.")
            return all_capabilities

        sql = "SELECT * FROM agent_capabilities ORDER BY agent_id, capability_id;"
        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.execute(sql)
                rows = cursor.fetchall()
                for row in rows:
                    agent_id = row["agent_id"]
                    cap_id = row["capability_id"]
                    if agent_id not in all_capabilities:
                        all_capabilities[agent_id] = {}
                    try:
                        capability_data = {
                            "agent_id": agent_id,
                            "capability_id": cap_id,
                            "capability_name": row["capability_name"],
                            "description": row["description"],
                            "parameters": json.loads(row["parameters_json"])
                            if row["parameters_json"]
                            else None,
                            "input_schema": json.loads(row["input_schema_json"])
                            if row["input_schema_json"]
                            else None,
                            "output_schema": json.loads(row["output_schema_json"])
                            if row["output_schema_json"]
                            else None,
                            "registered_at": row["registered_at"],
                        }
                        # TODO: Validate with Pydantic model
                        # all_capabilities[agent_id][cap_id] = AgentCapability.model_validate(capability_data)
                        all_capabilities[agent_id][cap_id] = capability_data  # Use dict
                    except json.JSONDecodeError as e:
                        logger.error(
                            f"Failed to decode JSON for capability {cap_id} for agent {agent_id}: {e}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed process capability row {cap_id} for agent {agent_id}: {e}"
                        )

                total_caps = sum(len(caps) for caps in all_capabilities.values())
                logger.debug(
                    f"Retrieved {total_caps} total capabilities for {len(all_capabilities)} agents."
                )
            except sqlite3.Error as e:
                logger.error(f"Failed to get all capabilities: {e}", exc_info=True)
            finally:
                if cursor:
                    cursor.close()
        return all_capabilities

    def find_agents_with_capability(self, capability_name: str) -> List[str]:
        """Finds agent IDs that have registered a capability with the given name."""
        agent_ids = []
        if not self.connection:
            logger.error("Cannot find agents, no database connection.")
            return agent_ids

        sql = "SELECT DISTINCT agent_id FROM agent_capabilities WHERE capability_name = ?;"
        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.execute(sql, (capability_name,))
                rows = cursor.fetchall()
                agent_ids = [row["agent_id"] for row in rows]
                logger.debug(
                    f"Found {len(agent_ids)} agents with capability '{capability_name}'."
                )
            except sqlite3.Error as e:
                logger.error(
                    f"Failed to find agents with capability {capability_name}: {e}",
                    exc_info=True,
                )
            finally:
                if cursor:
                    cursor.close()
        return agent_ids

    # --- Task Methods ---
    def add_task(self, task: Task):
        """Adds a new task to the database."""
        if not self.connection:
            logger.error("Cannot add task, no database connection.")
            return

        task_id = task.get("task_id")
        if not task_id:
            logger.error("Cannot add task without a task_id.")
            return

        # Ensure created_at and initial status exist
        now_iso = datetime.now(timezone.utc).isoformat()
        task["created_at"] = task.get("created_at", now_iso)
        task["status"] = task.get("status", "pending")
        task["updated_at"] = task.get("updated_at", now_iso)

        sql = """
        INSERT INTO tasks (
            task_id, description, priority, status, agent_id, tags_json,
            dependencies_json, created_at, updated_at, completed_at,
            result_summary, payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        tags_json = json.dumps(task.get("tags", []))
        deps_json = json.dumps(task.get("dependencies", []))
        payload_json = json.dumps(task.get("payload")) if task.get("payload") else None

        params = (
            task_id,
            task.get("description"),
            task.get("priority", 5),
            task["status"],
            task.get("agent_id"),
            tags_json,
            deps_json,
            task["created_at"],
            task["updated_at"],
            task.get("completed_at"),
            task.get("result_summary"),
            payload_json,
        )

        with self.lock:
            cursor = None  # Define cursor outside try for finally block
            try:
                cursor = self.connection.cursor()
                cursor.execute("BEGIN TRANSACTION;")
                cursor.execute(sql, params)
                self._log_status_change(
                    cursor, task_id, task["status"], task["updated_at"]
                )  # Pass cursor
                self._update_task_tags(
                    cursor, task_id, task.get("tags", [])
                )  # Pass cursor
                self.connection.commit()
                logger.debug(f"Added task {task_id}")
            except sqlite3.Error as e:
                logger.error(f"Failed to add task {task_id}: {e}", exc_info=True)
                if self.connection:
                    self.connection.rollback()
            finally:
                if cursor:
                    cursor.close()

    def update_task(self, task_id: str, updates: Dict[str, Any]):
        """Updates specific fields of an existing task."""
        if not self.connection:
            logger.error(f"Cannot update task {task_id}, no database connection.")
            return
        if not updates:
            logger.warning(f"No updates provided for task {task_id}. Nothing to do.")
            return

        # Add/update the updated_at timestamp
        now_iso = datetime.now(timezone.utc).isoformat()
        updates["updated_at"] = updates.get("updated_at", now_iso)

        # Prepare the SET clause dynamically
        set_clauses = []
        params = []
        allowed_fields = [  # Prevent updating primary key or created_at easily
            "description",
            "priority",
            "status",
            "agent_id",
            "tags_json",
            "dependencies_json",
            "updated_at",
            "completed_at",
            "result_summary",
            "payload_json",
        ]

        new_status = None
        new_tags = None

        for key, value in updates.items():
            if key in allowed_fields:
                # Handle JSON fields
                if key in ["tags_json", "dependencies_json", "payload_json"]:
                    if isinstance(value, (list, dict)):
                        params.append(json.dumps(value))
                    elif value is None:
                        params.append(None)
                    else:
                        # Assume already a JSON string if not list/dict/None
                        params.append(value)
                    if key == "tags_json":
                        new_tags = (
                            value
                            if isinstance(value, list)
                            else json.loads(value or "[]")
                        )
                else:
                    params.append(value)

                set_clauses.append(f"{key} = ?")

                if key == "status":
                    new_status = value
            else:
                logger.warning(
                    f"Attempted to update disallowed/unknown field '{key}' for task {task_id}. Skipping."
                )

        if not set_clauses:
            logger.warning(
                f"No valid fields to update for task {task_id}. Nothing to do."
            )
            return

        sql = f"UPDATE tasks SET {', '.join(set_clauses)} WHERE task_id = ?;"
        params.append(task_id)

        with self.lock:
            cursor = None
            try:
                cursor = self.connection.cursor()
                # Check if task exists before updating (optional, but good practice)
                cursor.execute("SELECT 1 FROM tasks WHERE task_id = ?", (task_id,))
                if cursor.fetchone() is None:
                    logger.error(f"Task {task_id} not found for update.")
                    return

                cursor.execute("BEGIN TRANSACTION;")
                cursor.execute(sql, tuple(params))

                # Log status change if status was updated
                if new_status is not None:
                    self._log_status_change(
                        cursor, task_id, new_status, updates["updated_at"]
                    )

                # Update tags if tags_json was updated
                if new_tags is not None:
                    self._update_task_tags(cursor, task_id, new_tags)

                self.connection.commit()
                logger.debug(f"Updated task {task_id}")
            except sqlite3.Error as e:
                logger.error(f"Failed to update task {task_id}: {e}", exc_info=True)
                if self.connection:
                    self.connection.rollback()
            finally:
                if cursor:
                    cursor.close()

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieves a single task by its ID."""
        if not self.connection:
            logger.error(f"Cannot get task {task_id}, no database connection.")
            return None

        sql = "SELECT * FROM tasks WHERE task_id = ?;"
        task = None
        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.execute(sql, (task_id,))
                row = cursor.fetchone()
                if row:
                    task = self._row_to_task(row)
                    logger.debug(f"Retrieved task {task_id}")
                else:
                    logger.debug(f"Task {task_id} not found.")
            except sqlite3.Error as e:
                logger.error(f"Failed to get task {task_id}: {e}", exc_info=True)
            finally:
                if cursor:
                    cursor.close()
        return task

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Helper function to convert a database row to a Task dictionary."""
        task_data = dict(row)
        try:
            task_data["tags"] = json.loads(task_data.get("tags_json") or "[]")
            task_data["dependencies"] = json.loads(
                task_data.get("dependencies_json") or "[]"
            )
            task_data["payload"] = json.loads(task_data.get("payload_json") or "null")
        except json.JSONDecodeError as e:
            task_id = task_data.get("task_id", "UNKNOWN")
            logger.error(f"Error decoding JSON for task {task_id}: {e}")
            # Keep raw json fields if decoding fails?

        # Remove the raw JSON fields if desired
        task_data.pop("tags_json", None)
        task_data.pop("dependencies_json", None)
        task_data.pop("payload_json", None)

        # TODO: Validate with Pydantic Task model if available
        return task_data

    def get_tasks_by_status(self, status: str | List[str]) -> List[Task]:
        """Retrieves tasks matching the given status or list of statuses."""
        tasks = []
        if not self.connection:
            logger.error("Cannot get tasks by status, no database connection.")
            return tasks

        if isinstance(status, str):
            statuses = [status]
        elif isinstance(status, list):
            statuses = status
        else:
            logger.error("Invalid status type provided.")
            return tasks

        if not statuses:
            return tasks

        placeholders = ", ".join("?" * len(statuses))
        sql = f"SELECT * FROM tasks WHERE status IN ({placeholders}) ORDER BY priority ASC, created_at ASC;"

        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.execute(sql, tuple(statuses))
                rows = cursor.fetchall()
                tasks = [self._row_to_task(row) for row in rows]
                logger.debug(
                    f"Retrieved {len(tasks)} tasks with status(es): {statuses}"
                )
            except sqlite3.Error as e:
                logger.error(
                    f"Failed to get tasks by status {statuses}: {e}", exc_info=True
                )
            finally:
                if cursor:
                    cursor.close()
        return tasks

    def get_pending_tasks(self, limit: Optional[int] = None) -> List[Task]:
        """Retrieves pending tasks, ordered by priority and creation time."""
        tasks = []
        if not self.connection:
            logger.error("Cannot get pending tasks, no database connection.")
            return tasks

        sql = "SELECT * FROM tasks WHERE status = 'pending' ORDER BY priority ASC, created_at ASC"
        params = ()
        if limit is not None and limit > 0:
            sql += " LIMIT ?"
            params = (limit,)
        sql += ";"

        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                tasks = [self._row_to_task(row) for row in rows]
                logger.debug(f"Retrieved {len(tasks)} pending tasks (limit: {limit}).")
            except sqlite3.Error as e:
                logger.error(f"Failed to get pending tasks: {e}", exc_info=True)
            finally:
                if cursor:
                    cursor.close()
        return tasks

    def claim_next_pending_task(self, agent_id: str) -> Optional[Task]:
        """Atomically finds the highest priority pending task and claims it."""
        if not self.connection:
            logger.error("Cannot claim task, no database connection.")
            return None

        claimed_task: Optional[Task] = None
        now_iso = datetime.now(timezone.utc).isoformat()

        with self.lock:
            cursor = None
            try:
                # Use IMMEDIATE transaction to acquire lock sooner
                cursor = self.connection.cursor()
                cursor.execute("BEGIN IMMEDIATE TRANSACTION;")

                # Find the highest priority pending task
                find_sql = """
                SELECT * FROM tasks
                WHERE status = 'pending'
                ORDER BY priority ASC, created_at ASC
                LIMIT 1;
                """
                cursor.execute(find_sql)
                row = cursor.fetchone()

                if row:
                    task_id = row["task_id"]
                    logger.debug(
                        f"Attempting to claim task {task_id} for agent {agent_id}"
                    )

                    # Claim the task
                    update_sql = """
                    UPDATE tasks
                    SET status = 'claimed', agent_id = ?, updated_at = ?
                    WHERE task_id = ? AND status = 'pending';
                    """
                    cursor.execute(update_sql, (agent_id, now_iso, task_id))

                    if cursor.rowcount == 1:
                        # Successfully claimed
                        self._log_status_change(cursor, task_id, "claimed", now_iso)
                        self.connection.commit()
                        # Fetch the updated row to return
                        claimed_task = self.get_task(task_id)
                        logger.info(f"Task {task_id} claimed by {agent_id}")
                    else:
                        # Task was claimed by another agent between SELECT and UPDATE
                        logger.warning(
                            f"Task {task_id} was claimed by another agent concurrently. Rolling back."
                        )
                        self.connection.rollback()
                else:
                    # No pending tasks found
                    logger.debug("No pending tasks available to claim.")
                    self.connection.rollback()  # Release transaction

            except sqlite3.Error as e:
                logger.error(
                    f"Error claiming next pending task for {agent_id}: {e}",
                    exc_info=True,
                )
                if self.connection:
                    self.connection.rollback()
            finally:
                if cursor:
                    cursor.close()

        return claimed_task

    def get_all_tasks(self) -> List[Task]:
        """Retrieves all tasks from the database."""
        tasks = []
        if not self.connection:
            logger.error("Cannot get all tasks, no database connection.")
            return tasks

        sql = "SELECT * FROM tasks ORDER BY priority ASC, created_at ASC;"
        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.execute(sql)
                rows = cursor.fetchall()
                tasks = [self._row_to_task(row) for row in rows]
                logger.debug(f"Retrieved {len(tasks)} total tasks.")
            except sqlite3.Error as e:
                logger.error(f"Failed to get all tasks: {e}", exc_info=True)
            finally:
                if cursor:
                    cursor.close()
        return tasks

    # --- Status History Methods ---
    def _log_status_change(
        self, cursor: sqlite3.Cursor, task_id: str, new_status: str, timestamp: str
    ):
        """Internal helper to log a task status change. Assumes called within a transaction."""
        # No need to check connection, should be called within a transaction
        sql = "INSERT INTO task_status_history (task_id, status, changed_at) VALUES (?, ?, ?);"
        try:
            cursor.execute(sql, (task_id, new_status, timestamp))
            logger.debug(
                f"Logged status '{new_status}' for task {task_id} at {timestamp}"
            )
        except sqlite3.Error as e:
            # Log error, but don't rollback here - let the calling function handle transaction
            logger.error(
                f"Failed to log status change for task {task_id}: {e}", exc_info=True
            )
            # Re-raise to potentially trigger rollback in caller?
            # raise

    # --- Tag Methods ---
    def _update_task_tags(self, cursor: sqlite3.Cursor, task_id: str, tags: List[str]):
        """Internal helper to update normalized tags. Assumes called within a transaction."""
        # Delete existing tags for the task
        del_sql = "DELETE FROM task_tags WHERE task_id = ?;"
        try:
            cursor.execute(del_sql, (task_id,))

            # Insert new tags
            if tags:
                insert_sql = "INSERT INTO task_tags (task_id, tag) VALUES (?, ?);"
                tag_params = [
                    (task_id, tag) for tag in tags if isinstance(tag, str)
                ]  # Basic validation
                if tag_params:
                    cursor.executemany(insert_sql, tag_params)
                    logger.debug(f"Updated tags for task {task_id}: {tags}")
                else:
                    logger.debug(f"No valid tags to insert for task {task_id}")
            else:
                logger.debug(
                    f"No tags provided for task {task_id}, existing tags cleared."
                )

        except sqlite3.Error as e:
            logger.error(
                f"Failed to update tags for task {task_id}: {e}", exc_info=True
            )
            # raise # Propagate error to caller for rollback

    def get_tasks_by_tag(self, tag: str) -> List[Task]:
        """Retrieves tasks associated with a specific tag."""
        tasks = []
        if not self.connection:
            logger.error(f"Cannot get tasks by tag '{tag}', no database connection.")
            return tasks

        sql = """
        SELECT t.* FROM tasks t
        JOIN task_tags tt ON t.task_id = tt.task_id
        WHERE tt.tag = ?
        ORDER BY t.priority ASC, t.created_at ASC;
        """
        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.execute(sql, (tag,))
                rows = cursor.fetchall()
                tasks = [self._row_to_task(row) for row in rows]
                logger.debug(f"Retrieved {len(tasks)} tasks with tag '{tag}'.")
            except sqlite3.Error as e:
                logger.error(f"Failed to get tasks by tag {tag}: {e}", exc_info=True)
            finally:
                if cursor:
                    cursor.close()
        return tasks

    # --- Additional Task Query Methods ---
    def get_tasks_by_agents_and_status(
        self, agent_ids: List[str], statuses: List[str]
    ) -> List[Task]:
        """Retrieves tasks assigned to specific agents with specific statuses."""
        tasks = []
        if not self.connection or not agent_ids or not statuses:
            logger.debug(
                "Cannot get tasks by agents/status, invalid input or no connection."
            )
            return tasks

        agent_placeholders = ", ".join("?" * len(agent_ids))
        status_placeholders = ", ".join("?" * len(statuses))
        sql = f"""
        SELECT * FROM tasks
        WHERE agent_id IN ({agent_placeholders})
          AND status IN ({status_placeholders})
        ORDER BY priority ASC, created_at ASC;
        """
        params = tuple(agent_ids) + tuple(statuses)

        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                tasks = [self._row_to_task(row) for row in rows]
                logger.debug(
                    f"Retrieved {len(tasks)} tasks for agents {agent_ids} with status(es): {statuses}"
                )
            except sqlite3.Error as e:
                logger.error(
                    f"Failed to get tasks by agents/status: {e}", exc_info=True
                )
            finally:
                if cursor:
                    cursor.close()
        return tasks


# Example usage (for testing or integration)
# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO)
#     db_file = Path('./runtime/db/dreamos_state.sqlite')
#     adapter = SQLiteAdapter(db_file)

#     # Example operations (implement methods first)
#     # adapter.update_agent_heartbeat('Agent1', time.time())
#     # print(adapter.get_all_agents())

#     adapter.close()
